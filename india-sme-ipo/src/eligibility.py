"""SME IPO eligibility engine (NSE Emerge, BSE SME).

Company input (all amounts INR crore; fy = calendar year in which the
Indian financial year ends, e.g. FY2025 = Apr-2024..Mar-2025):

    {"legal_form": "Public limited company" | "Private limited company" | ...,
     "incorporation_date": "YYYY-MM-DD",
     "post_issue_paidup_cr": float | None,
     "financials": [{"fy": 2025, "revenue_cr": .., "ebitda_cr": .., "net_worth_cr": ..,
                     "nta_cr": .., "fcfe_cr": .., ...}, ...]}

Only financial years that closed on or before ``as_of`` are used, so a
historical assessment never sees later data.
"""
from datetime import date

try:
    from .reference import PLATFORM_RULES
except ImportError:  # run as script
    from reference import PLATFORM_RULES

PASS, FAIL, UNKNOWN = "Pass", "Fail", "Unknown"
CLASS_MEETS = "1 - Appears to meet measurable eligibility requirements"
CLASS_POTENTIAL = "2 - Potentially eligible, further verification required"
CLASS_FAILS = "3 - Fails one or more measurable requirements"
CLASS_INSUFFICIENT = "4 - Insufficient information"


def _d(s):
    return date.fromisoformat(s) if isinstance(s, str) else s


def usable_years(financials, as_of):
    """Financial years ending 31-Mar on or before as_of, newest first."""
    as_of = _d(as_of)
    rows = [f for f in financials or [] if date(int(f["fy"]), 3, 31) <= as_of]
    return sorted(rows, key=lambda f: f["fy"], reverse=True)


def _last3(rows, field):
    vals = [r.get(field) for r in rows[:3]]
    return vals if len(rows) >= 3 else vals + [None] * (3 - len(rows))


def _n_of_3(rows, field, threshold, n, strict=False):
    vals = _last3(rows, field)
    known = [v for v in vals if v is not None]
    hits = sum(1 for v in known if (v > threshold if strict else v >= threshold))
    if hits >= n:
        return PASS, vals
    if hits + (3 - len(known)) < n:
        return FAIL, vals
    return UNKNOWN, vals


def check_rule(rule, company, as_of):
    rows = usable_years(company.get("financials"), as_of)
    kind = rule["kind"]
    if kind == "legal_public_company":
        form = (company.get("legal_form") or "").lower()
        if not form:
            return UNKNOWN, "Legal form unknown"
        if "public" in form and "limited" in form:
            return PASS, company["legal_form"]
        # Not a hard fail: conversion is a routine pre-IPO step.
        return UNKNOWN, f"{company['legal_form']}: conversion to public limited required before filing"
    if kind == "track_record_years":
        inc = company.get("incorporation_date")
        if not inc:
            return UNKNOWN, "Incorporation date unknown"
        years = (_d(as_of) - _d(inc)).days / 365.25
        return (PASS if years >= rule["years"] else FAIL), f"{years:.1f} years since incorporation"
    if kind == "ebitda_n_of_3":
        st, vals = _n_of_3(rows, "ebitda_cr", rule["threshold_cr"], rule["n"])
        return st, f"EBITDA last 3 FY (cr): {vals}"
    if kind == "fcfe_n_of_3":
        st, vals = _n_of_3(rows, "fcfe_cr", rule["threshold_cr"], rule["n"], strict=True)
        return st, f"FCFE last 3 FY (cr): {vals}"
    if kind == "networth_positive_latest":
        v = rows[0].get("net_worth_cr") if rows else None
        if v is None:
            return UNKNOWN, "Latest net worth unknown"
        return (PASS if v > 0 else FAIL), f"Latest net worth {v} cr"
    if kind == "networth_min_each_of_last_n":
        vals = [r.get("net_worth_cr") for r in rows[:rule["n"]]]
        if len(vals) < rule["n"] or any(v is None for v in vals):
            if any(v is not None and v < rule["threshold_cr"] for v in vals):
                return FAIL, f"Net worth (cr): {vals}"
            return UNKNOWN, f"Net worth (cr): {vals}"
        return (PASS if all(v >= rule["threshold_cr"] for v in vals) else FAIL), f"Net worth (cr): {vals}"
    if kind == "nta_min_latest":
        v = rows[0].get("nta_cr") if rows else None
        if v is None:
            return UNKNOWN, "Net tangible assets unknown"
        return (PASS if v >= rule["threshold_cr"] else FAIL), f"Latest NTA {v} cr"
    if kind == "post_issue_paidup_max":
        v = company.get("post_issue_paidup_cr")
        if v is None:
            return UNKNOWN, "Post-issue paid-up capital depends on issue structure (not yet known)"
        return (PASS if v <= rule["threshold_cr"] else FAIL), f"Post-issue paid-up {v} cr"
    return UNKNOWN, f"Unsupported rule kind {kind}"


def assess(company, platform, as_of):
    """Return dict with per-rule results and an overall classification."""
    results = []
    for rule in PLATFORM_RULES[platform]:
        status, evidence = check_rule(rule, company, as_of)
        results.append({"rule_id": rule["id"], "rule": rule["text"], "status": status,
                        "evidence": evidence, "rule_verification": rule["verification"]})
    statuses = [r["status"] for r in results]
    core = [r for r in results if r["rule_id"] in ("SEBI-OP",)]
    if FAIL in statuses:
        cls = CLASS_FAILS
    elif core and core[0]["status"] == UNKNOWN:
        cls = CLASS_INSUFFICIENT
    elif all(s == PASS for s in statuses):
        cls = CLASS_MEETS
    else:
        # Post-issue paid-up capital depends on the (future) issue, so it is not held
        # against the company. Legal form must already be public for class 1.
        company_rules = [r for r in results if r["rule_id"] != "SEBI-PUC"]
        cls = CLASS_MEETS if all(r["status"] == PASS for r in company_rules) else CLASS_POTENTIAL
    return {"platform": platform, "as_of": str(as_of), "classification": cls, "results": results,
            "caveat": "Measurable checks only. Not a legal opinion; rule texts are from secondary "
                      "sources pending primary verification."}
