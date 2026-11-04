# India SME IPO Readiness Research

This project finds unlisted Indian companies that look financially ready for an SME IPO
(NSE Emerge or BSE SME). It compares them against the companies that have already listed.
It is independent financial research and does not cover media sales.

## Status (4 November 2026)

| Layer | State |
| --- | --- |
| Eligibility engine (NSE Emerge, BSE SME) | Built and tested |
| Readiness, intent and confidence scores, plus backtest harness | Built and tested |
| MSME classification (2020 and 2025 regimes), entity IPO routes | Populated (secondary sources) |
| Tracxn IPO activity, India 2018–2026 (aggregate counts) | Populated (raw responses preserved) |
| Company-level historical IPOs, pre-IPO financials, unlisted candidates | **Empty: Tracxn stages 2–4 await approval** |
| Backtest | Not run: needs stage 2–4 data |

No company names, financial figures or rankings have been estimated to fill the gaps.

## Access findings

- **Chrome / Tracxn web session:** not reachable. The work runs in a cloud container, not on
  your computer.
- **Tracxn connector (official MCP):** connected, and it consumes credits. 714 of 10,000 credits
  remained after three aggregation calls; credits reset on the 1st of the month. See the
  `Tracxn_Credit_Log` sheet in `Data_Quality_Report.xlsx`.
- **Public web:** official NSE, BSE, SEBI, MCA and MSME sites are blocked by the environment's
  network policy. Web search works but returns only summaries. Every regulatory rule is therefore
  marked "secondary source, verify". The domains to allow are listed in `Data_Quality_Report.xlsx`.

## Layout

```text
data/raw/tracxn/   Original Tracxn responses, read-only and never modified
data/cleaned/      Normalised tables (JSON)
data/modelled/     Dashboard dataset
src/reference.py   MSME thresholds, entity routes, platform rules, source register
src/eligibility.py Rule engine; uses only financial years closed before the as-of date
src/scoring.py     Readiness (A), intent (B), confidence (C), backtest()
src/ingest_tracxn.py  Parses Tracxn responses (aggregates now; record pages when approved)
src/build.py       Builds all workbooks, the PDF report and dashboard/data.js
dashboard/         index.html and data.js (static; open the HTML file directly)
outputs/           The eight Excel/PDF deliverables
tests/             Unit tests (hypothetical fixtures only)
```

## Run

```bash
python3 src/build.py
```

```bash
python3 -m unittest tests/test_models.py
```

To view the dashboard, open `dashboard/index.html` in a browser. It needs no server.

## Adding stage 2–4 data

Save each approved Tracxn response verbatim in `data/raw/tracxn/` with a name ending in
`_ipo_events_pageN.json` or `_legal_entities_pageN.json`, then rerun `build.py`.
Board classification (SME vs mainboard) is set only from exchange or DRHP records, never from issue size.

## Key caveats

- Tracxn's `exchangeSymbol` field mixes SME and mainboard listings, and a dual-listed IPO counts
  once per exchange. The 2,738 listing events are **not** SME IPO counts. `BOM` (7 events) is
  BSE's market code and is grouped with BSE.
- The BSE SME net-tangible-asset threshold is conflicting across sources (₹1.5 cr vs ₹3 cr),
  and the BSE track-record rule is unconfirmed.
- Scores are screening indices, not probabilities. The weights are initial hypotheses until the
  backtest runs.
- MSME status needs both the investment and the turnover test. It is marked "Unverified" when
  investment data is missing.
