/**
 * Guards the OpenCode plugin's runtime imports against packages that a
 * published install would not have (affaan-m/ECC#3745).
 *
 * `ecc-universal` ships .opencode/dist, and OpenCode loads it from the
 * installed package, where only `dependencies` exist. A value import of a
 * devDependency such as @opencode-ai/plugin compiles and passes repo tests
 * (the root node_modules has it) but fails to load for real users.
 *
 * Run with: node tests/opencode-runtime-deps.test.js
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { builtinModules } = require('module');

function test(name, fn) {
  try {
    fn();
    console.log(`  ✓ ${name}`);
    return true;
  } catch (err) {
    console.log(`  ✗ ${name}`);
    console.log(`    Error: ${err.message}`);
    return false;
  }
}

const repoRoot = path.join(__dirname, '..');
const opencodeDir = path.join(repoRoot, '.opencode');
const rootPackage = JSON.parse(fs.readFileSync(path.join(repoRoot, 'package.json'), 'utf8'));
const runtimeDeps = new Set(Object.keys(rootPackage.dependencies || {}));
const builtins = new Set(builtinModules.flatMap(name => [name, `node:${name}`]));

function listSources(dir, acc = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === 'node_modules' || entry.name === 'dist') continue;
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) listSources(fullPath, acc);
    else if (/\.(ts|js|mjs)$/.test(entry.name) && !entry.name.endsWith('.d.ts')) acc.push(fullPath);
  }
  return acc;
}

function packageName(specifier) {
  const parts = specifier.split('/');
  return specifier.startsWith('@') ? parts.slice(0, 2).join('/') : parts[0];
}

// Static imports/re-exports that survive compilation, plus dynamic import()
// and require(). `import type` / `export type` are erased by tsc, as is an
// import whose named bindings are all marked `type`.
function runtimeSpecifiers(source) {
  const found = [];
  const statement = /^\s*(import|export)\s+(type\s+)?([^;]*?)\s*from\s*['"]([^'"]+)['"]/gm;
  let match;
  while ((match = statement.exec(source))) {
    const [, , typeOnly, clause, specifier] = match;
    if (typeOnly) continue;
    const named = clause.match(/^\{([^}]*)\}$/);
    if (named && named[1].split(',').map(s => s.trim()).filter(Boolean).every(s => s.startsWith('type '))) continue;
    found.push(specifier);
  }
  for (const pattern of [/^\s*import\s+['"]([^'"]+)['"]/gm, /\b(?:import|require)\(\s*['"]([^'"]+)['"]\s*\)/g]) {
    while ((match = pattern.exec(source))) found.push(match[1]);
  }
  return found;
}

const sources = listSources(opencodeDir);

let passed = 0;
let failed = 0;

if (
  test('OpenCode plugin sources exist to scan', () => {
    assert.ok(sources.length > 0, `No sources found under ${opencodeDir}`);
  })
)
  passed++;
else failed++;

if (
  test('specifier scan treats type-only imports as erased and value imports as runtime', () => {
    const sample = [
      'import type { A } from "type-only-pkg"',
      'export type { B } from "type-only-reexport"',
      'import { type C, type D } from "all-inline-types"',
      'import { tool, type E } from "mixed-pkg/sub"',
      'import * as fs from "fs"',
      'export { x } from "@scope/reexported"',
      'import "side-effect"',
      'const m = await import("dynamic-pkg")',
    ].join('\n');
    assert.deepStrictEqual(runtimeSpecifiers(sample).sort(), [
      '@scope/reexported',
      'dynamic-pkg',
      'fs',
      'mixed-pkg/sub',
      'side-effect',
    ]);
  })
)
  passed++;
else failed++;

if (
  test('runtime imports resolve to Node builtins or package.json dependencies', () => {
    const violations = [];
    for (const file of sources) {
      for (const specifier of runtimeSpecifiers(fs.readFileSync(file, 'utf8'))) {
        if (specifier.startsWith('.') || specifier.startsWith('/')) continue;
        if (builtins.has(specifier) || runtimeDeps.has(packageName(specifier))) continue;
        violations.push(`${path.relative(repoRoot, file)}: ${specifier}`);
      }
    }
    assert.deepStrictEqual(
      violations,
      [],
      'These runtime imports are not in package.json "dependencies", so a published install cannot load them. ' +
        'Use `import type`, or move the package into "dependencies".'
    );
  })
)
  passed++;
else failed++;

console.log(`\nResults: Passed: ${passed}, Failed: ${failed}`);
process.exit(failed > 0 ? 1 : 0);
