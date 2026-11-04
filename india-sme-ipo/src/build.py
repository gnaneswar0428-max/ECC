"""Build all deliverables from reference data + preserved Tracxn responses.

    python3 src/build.py

Outputs go to outputs/ (Excel, PDF) and dashboard/data.js.
"""
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from openpyxl import Workbook  # noqa: E402
from openpyxl.styles import Alignment, Font, PatternFill  # noqa: E402
from openpyxl.utils import get_column_letter  # noqa: E402

import reference as ref  # noqa: E402
import ingest_tracxn as ing  # noqa: E402
from scoring import READINESS_WEIGHTS, INTENT_SIGNAL_WEIGHTS, DIRECT_SIGNALS, DEFAULT_BENCHMARK  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "outputs")
CLEAN = os.path.join(ROOT, "data", "cleaned")
MODEL = os.path.join(ROOT, "data", "modelled")
TODAY = "2026-11-04"
HEAD = PatternFill("solid", fgColor="1F3A5F")
NOTE = PatternFill("solid", fgColor="FFF4CE")

TRACXN_CREDIT_LOG = [
    {"call": 1, "tool": "search_ipo_events", "type": "aggregation", "purpose": "IPO listing events by exchange, India 2018-2026",
     "credits_before": None, "credits_after": 726, "cost": "unknown (first call)", "useful": "Yes"},
    {"call": 2, "tool": "search_ipo_events", "type": "aggregation", "purpose": "IPO listing events by year x exchange",
     "credits_before": 726, "credits_after": 725, "cost": 1, "useful": "Yes"},
    {"call": 3, "tool": "search_legal_entities", "type": "aggregation",
     "purpose": "Size candidate screen (EBITDA >= 1 cr, compliant, inc. <= 2022) bucketed by EBITDA",
     "credits_before": 725, "credits_after": 714, "cost": 11,
     "useful": "No - auto-bucketing used 1,000-unit bins; all buckets returned 0. Re-run as plain count."},
]

PENDING = {
    "stage_2": "Tracxn IPO Transactions record-level pull (India, 2018-2026, NSE/BSE): ~2,700 listing events; "
               "needed for company-level SME IPO database. Awaiting approval (credit cost per record unknown).",
    "stage_3": "Tracxn Legal Entities + time series for historical IPO companies (CIN, incorporation, 3-5 FY financials). "
               "Awaiting approval.",
    "stage_4": "Tracxn Legal Entities screen of unlisted companies. Awaiting approval.",
}

BLOCKED_DOMAINS = ["www.nseindia.com", "nsearchives.nseindia.com", "www.bseindia.com", "api.bseindia.com",
                   "www.sebi.gov.in", "www.chittorgarh.com", "chittorgarh.com", "ipocentral.in", "en.wikipedia.org",
                   "msme.gov.in", "udyamregistration.gov.in", "www.mca.gov.in", "www.screener.in"]


# ---------------------------------------------------------------------------
def sheet(wb, title, rows, cols=None, note=None, first=False):
    ws = wb.active if first else wb.create_sheet()
    ws.title = title[:31]
    r0 = 1
    if note:
        ws.cell(row=1, column=1, value=note).fill = NOTE
        ws.cell(row=1, column=1).alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[1].height = 15 * max(2, len(note) // 110 + 1)
        r0 = 3
    cols = cols or (list(rows[0].keys()) if rows else [])
    if note and cols:
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(len(cols), 6))
    for j, c in enumerate(cols, 1):
        cell = ws.cell(row=r0, column=j, value=c)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = HEAD
    for i, row in enumerate(rows, r0 + 1):
        for j, c in enumerate(cols, 1):
            v = row.get(c)
            ws.cell(row=i, column=j, value=json.dumps(v) if isinstance(v, (list, dict)) else v)
    for j, c in enumerate(cols, 1):
        width = max([len(str(c))] + [min(70, len(str(r.get(c, "")))) for r in rows])
        ws.column_dimensions[get_column_letter(j)].width = min(72, max(10, width + 2))
    ws.freeze_panes = ws.cell(row=r0 + 1, column=1)
    return ws


def status_sheet(wb, title, lines):
    rows = [{"Item": k, "Status / note": v} for k, v in lines]
    return sheet(wb, title, rows, first=True)


# ---------------------------------------------------------------------------
def build_tables():
    by_year = ing.listings_by_year_exchange()
    by_ex = ing.listings_by_exchange()
    years = sorted({r["year"] for r in by_year})
    recon = []
    ext = {e["year"]: e for e in ref.EXTERNAL_SME_IPO_COUNTS}
    for y in years:
        nse = sum(r["listing_events"] for r in by_year if r["year"] == y and r["exchange"] == "NSE")
        bse = sum(r["listing_events"] for r in by_year if r["year"] == y and r["exchange"] in ("BSE", "BOM"))
        e = ext.get(y)
        recon.append({"year": y, "tracxn_nse_events": nse, "tracxn_bse_events": bse,
                      "tracxn_nse_plus_bse": nse + bse,
                      "external_sme_ipo_count": e["sme_ipos"] if e else None,
                      "external_sme_amount_cr": e["amount_cr"] if e else None,
                      "note": "; ".join(n for n in (
                          "YTD to 04-Nov-2026" if y == 2026 else "",
                          ("external: " + e["note"]) if e and e["note"] else "",
                          "" if e else "no external SME count retrieved") if n)})
    ipo_records = ing.ipo_event_records()
    for name, data in (("tracxn_listings_by_year_exchange", by_year), ("tracxn_listings_by_exchange", by_ex),
                       ("listing_reconciliation", recon), ("historical_ipo_records", ipo_records)):
        with open(os.path.join(CLEAN, name + ".json"), "w") as fh:
            json.dump(data, fh, indent=1)
    return by_year, by_ex, recon, ipo_records


COMPANY_COLS = ["company_id", "company_name", "legal_name", "cin", "legal_form", "industry", "subsector",
                "business_model", "founders", "hq_city", "state", "incorporation_date", "website",
                "funding_total_cr", "investors", "employees", "listing_status", "company_status",
                "msme_category", "msme_basis", "match_method", "source_id"]
FIN_COLS = ["company_id", "cin", "fy", "revenue_cr", "ebitda_cr", "operating_profit_cr", "pat_cr",
            "net_worth_cr", "total_assets_cr", "total_debt_cr", "ocf_cr", "capex_cr", "paid_up_cr",
            "auditor", "audited", "source_id"]
IPO_COLS = ["tracxn_ipo_id", "company_name", "legal_name", "cin", "industry", "state", "hq_city",
            "incorporation_date", "drhp_date", "open_date", "ipo_date", "board", "exchanges", "issue_size_cr",
            "fresh_issue_cr", "ofs_cr", "issue_price_inr", "pre_issue_paidup_cr", "post_issue_paidup_cr",
            "market_cap_cr", "merchant_banker", "use_of_proceeds", "pre_ipo_revenue_cr", "pre_ipo_pat_cr",
            "pre_ipo_fin_as_on", "source_id", "raw_file"]
WATCH_COLS = ["rank", "company_id", "company_name", "state", "industry", "readiness_score", "intent_score",
              "confidence_score", "nse_emerge_class", "bse_sme_class", "intent_signals", "key_strengths",
              "key_risks", "comparable_ipos", "source_ids"]

PENDING_NOTE = ("NO RECORDS YET. Company-level data requires Tracxn stages 2-4, which are awaiting your approval "
                "because the connector consumes credits (714 of 10,000 left on 04-Nov-2026). No rows have been "
                "estimated or invented. Columns show the schema that will be populated.")


def build_workbooks(by_year, by_ex, recon, ipo_records):
    os.makedirs(OUT, exist_ok=True)
    # 1. Master database
    wb = Workbook()
    status_sheet(wb, "Status", [
        ("Built", TODAY), ("Company Master", "0 records - pending Tracxn stage 4"),
        ("Legal Entities", "0 records - pending Tracxn stages 3-4"),
        ("MSME classification", "Reference thresholds loaded (2020 and 2025 regimes)"),
        ("MSME note", ref.MSME_NOTE), ("Scope", "Independent financial research. No Network18, advertising or media-sales analysis.")])
    sheet(wb, "MSME_Classification", ref.MSME_CLASSIFICATION)
    sheet(wb, "Entity_IPO_Routes", ref.ENTITY_IPO_ROUTES)
    sheet(wb, "State_MSME_Share_FY24", ref.STATE_MSME_SHARE_FY24,
          note="Share of Udyam registrations, FY24 (IBEF, secondary). Shares only; official state counts not retrieved "
               "because msme.gov.in / udyamregistration.gov.in are blocked from the research container.")
    sheet(wb, "Company_Master", [], COMPANY_COLS, note=PENDING_NOTE)
    sheet(wb, "Legal_Entities", [], ["legal_entity_id", "cin", "legal_name", "incorporation_date", "state", "city",
                                     "status_at_registrar", "registrar_compliant", "paid_up_cr", "authorised_cr",
                                     "latest_auditor", "cirp_status", "company_id", "match_method", "source_id"],
          note=PENDING_NOTE)
    sheet(wb, "Historical_Financials", [], FIN_COLS, note=PENDING_NOTE)
    wb.save(os.path.join(OUT, "India_MSME_Master_Database.xlsx"))

    # 2. Historical SME IPO database
    wb = Workbook()
    status_sheet(wb, "Status", [
        ("Built", TODAY),
        ("What is real", "Tracxn aggregate counts of Indian IPO listing events by year and exchange, 2018 to 04-Nov-2026."),
        ("Critical caveat", "Tracxn's exchangeSymbol field does not separate SME from mainboard, and an IPO listed on "
                            "both NSE and BSE counts once per exchange. These are NOT SME IPO counts."),
        ("Cross-check", "External SME-only counts (Chittorgarh, secondary) are far lower, confirming the Tracxn totals "
                        "include mainboard listings."),
        ("Company-level records", f"{len(ipo_records)} - pending Tracxn stage 2"),
        ("Board classification", "Will be set only from exchange records or DRHP/RHP, never from issue size.")])
    sheet(wb, "Tracxn_By_Year_Exchange", by_year)
    sheet(wb, "Tracxn_By_Exchange", by_ex)
    sheet(wb, "Reconciliation", recon,
          note="Tracxn NSE+BSE listing events vs external SME-only IPO counts. The gap is mainboard listings plus "
               "dual-exchange double counting. 2024 external figure is marked partial by its source; 2018, 2019 and "
               "2025 external counts were not found.")
    sheet(wb, "IPO_Records", ipo_records, IPO_COLS, note=PENDING_NOTE if not ipo_records else None)
    sheet(wb, "Pre_IPO_Financials", [], ["tracxn_ipo_id", "cin"] + FIN_COLS[2:] + ["years_before_ipo"],
          note=PENDING_NOTE)
    sheet(wb, "Withdrawn_Delayed", [], ["company_name", "drhp_date", "status", "reason", "source_id"],
          note="Pending: SEBI DRHP-status pages are blocked from the container. Requires sebi.gov.in access.")
    wb.save(os.path.join(OUT, "Historical_SME_IPO_Database.xlsx"))

    # 3. Future IPO candidates
    wb = Workbook()
    status_sheet(wb, "Status", [
        ("Built", TODAY), ("List A (confirmed preparation)", "0 - pending company data and intent-signal research"),
        ("List B (financially strong, unannounced)", "0 - pending Tracxn stage 4"),
        ("Interpretation", "List B companies show financial readiness only. They are NOT described as planning an IPO."),
        ("Score meaning", "Scores are screening indices, not probabilities.")])
    sheet(wb, "List_A_Confirmed_Prep", [], WATCH_COLS, note=PENDING_NOTE)
    sheet(wb, "List_B_Unannounced", [], WATCH_COLS, note=PENDING_NOTE)
    sheet(wb, "Screen_Definition", [
        {"step": 1, "filter": "Indian legal entity, active, registrar-compliant, not listed, not struck off, no CIRP"},
        {"step": 2, "filter": "Latest revenue INR 10-500 crore (no MSME claim without investment data)"},
        {"step": 3, "filter": "EBITDA >= INR 1 crore in >= 2 of last 3 FY (SEBI SME test)"},
        {"step": 4, "filter": "Incorporated >= 3 years before assessment date"},
        {"step": 5, "filter": "Rank by Readiness score within sector, using sector benchmarks from historical cohort"},
        {"step": 6, "filter": "Split by Intent: direct signal -> List A; none -> List B"},
        {"step": 7, "filter": "Flag subsidiaries, acquired, inactive for separate review; keep bootstrapped/family firms"}])
    wb.save(os.path.join(OUT, "Future_IPO_Candidates.xlsx"))

    # 4. Eligibility
    wb = Workbook()
    status_sheet(wb, "Status", [
        ("Rules as of", ref.RULES_AS_OF),
        ("Verification", "All rule texts come from secondary sources. Official NSE/BSE/SEBI pages are blocked from "
                         "the container. Confirm each rule before relying on outputs."),
        ("Classes", "1 Appears to meet | 2 Potentially eligible, verify | 3 Fails a measurable test | 4 Insufficient info"),
        ("Assessments", "0 companies assessed - pending company data"),
        ("Not a legal opinion", "Measurable checks only.")])
    for p, rules in ref.PLATFORM_RULES.items():
        sheet(wb, "Rules_" + p.replace(" ", "_"), [{k: v for k, v in r.items()} for r in rules])
    sheet(wb, "Issue_Structure_Rules", ref.ISSUE_STRUCTURE_RULES)
    sheet(wb, "Assessments", [], ["company_id", "company_name", "platform", "as_of", "classification",
                                  "rule_id", "status", "evidence"], note=PENDING_NOTE)
    wb.save(os.path.join(OUT, "IPO_Eligibility_Assessment.xlsx"))

    # 5. Scoring model
    wb = Workbook()
    status_sheet(wb, "Status", [
        ("Model", "Three separate 0-100 indices: A Readiness, B Intent, C Data Confidence"),
        ("Weights", "Initial hypotheses from the brief; to be re-estimated after backtesting on the historical cohort"),
        ("Readiness withheld", "If components with data cover < 70% of total weight, readiness is not scored"),
        ("Not probabilities", "A score of 85 does NOT mean an 85% chance of IPO"),
        ("Backtest", "NOT RUN - needs historical pre-IPO financials (stage 3) and a non-IPO comparison pool (stage 4). "
                     "Until then this is a research-screening tool, not a validated prediction model.")])
    sheet(wb, "A_Readiness_Weights", [{"component": k, "weight": v, "metric": m} for (k, v), m in zip(
        READINESS_WEIGHTS.items(),
        ["3y revenue CAGR vs sector benchmark, penalty per YoY decline",
         "50% latest EBITDA margin vs benchmark + 50% share of last 3 FY with PAT > 0",
         "70% debt/equity (0.5 good, 2.0 bad) + 30% net worth growth",
         "60% share of last 3 FY with OCF > 0 + 40% OCF/EBITDA conversion",
         "0 at < 3 years since incorporation, linear to 1 at 10 years",
         "Capex / revenue vs 5% benchmark; headcount growth when available",
         "Registrar compliance, audited accounts, no insolvency, auditor known"])])
    sheet(wb, "A_Default_Benchmarks", [{"parameter": k, "value": v} for k, v in DEFAULT_BENCHMARK.items()],
          note="Placeholders until sector percentiles are computed from historical SME IPO issuers.")
    sheet(wb, "B_Intent_Signals", [{"signal": k, "points": v, "type": "Direct disclosure" if k in DIRECT_SIGNALS else "Indirect"}
                                   for k, v in INTENT_SIGNAL_WEIGHTS.items()],
          note="Points add up, capped at 100. Any direct signal puts the company on List A.")
    sheet(wb, "C_Confidence", [
        {"component": "Audited financials", "max_points": 25}, {"component": "History completeness (5y=20, 3y=12)", "max_points": 20},
        {"component": "Source credibility (MCA/DRHP 20, Tracxn LE 18, Tracxn company 14, news 8)", "max_points": 20},
        {"component": "Recency (latest FY <= 18 months old)", "max_points": 15},
        {"component": "Entity match (CIN 10, validated name+location 6, uncertain 2)", "max_points": 10},
        {"component": "Independent verification", "max_points": 10}])
    sheet(wb, "Backtest_Design", [
        {"snapshot": "2020-12-31", "uses_data_up_to": "FY2020 (31-Mar-2020)", "outcome_window": "2021-2023", "status": "Not run - data pending"},
        {"snapshot": "2021-12-31", "uses_data_up_to": "FY2021", "outcome_window": "2022-2024", "status": "Not run - data pending"},
        {"snapshot": "2022-12-31", "uses_data_up_to": "FY2022", "outcome_window": "2023-2025", "status": "Not run - data pending"},
        {"snapshot": "Metrics", "uses_data_up_to": "precision@50, lift over base rate, AUC, false-positive review",
         "outcome_window": "", "status": "Implemented in src/scoring.py: backtest()"},
        {"snapshot": "Biases", "uses_data_up_to": "Incomplete private-company coverage; survivorship; 2024-25 rule change "
                                                  "(EBITDA test) means pre-2025 issuers faced looser rules", "outcome_window": "", "status": ""}])
    wb.save(os.path.join(OUT, "IPO_Readiness_Scoring_Model.xlsx"))

    # 6. Source register
    wb = Workbook()
    sheet(wb, "Sources", ref.SOURCES, first=True)
    wb.save(os.path.join(OUT, "Source_Register.xlsx"))

    # 7. Data quality
    wb = Workbook()
    status_sheet(wb, "Status", [
        ("Overall", "Reference and aggregate layers built; company-level layers empty pending Tracxn approval."),
        ("Chrome / Tracxn web session", "Not reachable: research runs in a cloud container, not on your computer."),
        ("Tracxn connector", "Connected. Consumes credits: 714 / 10,000 remaining after 3 calls (resets on the 1st)."),
        ("Public web", "Shell and fetch access to official sites blocked by network policy; only web-search summaries available.")])
    sheet(wb, "Dataset_Status", [
        {"dataset": "MSME classification", "records": len(ref.MSME_CLASSIFICATION), "quality": "Secondary-verified", "gap": "Gazette text not fetched"},
        {"dataset": "Entity IPO routes", "records": len(ref.ENTITY_IPO_ROUTES), "quality": "General law", "gap": "Counsel review"},
        {"dataset": "Platform rules", "records": sum(len(v) for v in ref.PLATFORM_RULES.values()), "quality": "Secondary", "gap": "BSE NTA figure conflicting; BSE track record unconfirmed"},
        {"dataset": "Tracxn IPO aggregates", "records": len(by_year), "quality": "Licensed DB, raw preserved", "gap": "No SME/mainboard split"},
        {"dataset": "External SME IPO counts", "records": len(ref.EXTERNAL_SME_IPO_COUNTS), "quality": "Secondary aggregator", "gap": "2018, 2019, 2025 missing; 2024 partial"},
        {"dataset": "Historical IPO companies", "records": len(ipo_records), "quality": "-", "gap": PENDING["stage_2"]},
        {"dataset": "Pre-IPO financials", "records": 0, "quality": "-", "gap": PENDING["stage_3"]},
        {"dataset": "Unlisted candidates", "records": 0, "quality": "-", "gap": PENDING["stage_4"]},
        {"dataset": "State MSME statistics", "records": len(ref.STATE_MSME_SHARE_FY24), "quality": "Secondary (shares)", "gap": "Official counts blocked"}])
    sheet(wb, "Tracxn_Credit_Log", TRACXN_CREDIT_LOG)
    sheet(wb, "Blocked_Domains", [{"domain": d, "needed_for": "Primary-source verification / IPO lists"} for d in BLOCKED_DOMAINS],
          note="Add these under the environment's Network access -> Allowed domains to enable primary-source verification.")
    wb.save(os.path.join(OUT, "Data_Quality_Report.xlsx"))


def build_dashboard_data(by_year, by_ex, recon, ipo_records):
    data = {"built": TODAY, "rules_as_of": ref.RULES_AS_OF,
            "kpis": {"companies_identified": 0, "companies_verified_financials": 0, "companies_screened": 0,
                     "potential_candidates": 0, "confirmed_prep": 0, "historical_ipo_records": len(ipo_records),
                     "tracxn_listing_events": sum(r["listing_events"] for r in by_ex),
                     "tracxn_credits_left": 714},
            "by_year": by_year, "by_exchange": by_ex, "reconciliation": recon,
            "external_sme": ref.EXTERNAL_SME_IPO_COUNTS, "msme": ref.MSME_CLASSIFICATION,
            "state_share": ref.STATE_MSME_SHARE_FY24, "rules": ref.PLATFORM_RULES,
            "issue_rules": ref.ISSUE_STRUCTURE_RULES, "entity_routes": ref.ENTITY_IPO_ROUTES,
            "weights": READINESS_WEIGHTS, "intent_weights": INTENT_SIGNAL_WEIGHTS, "sources": ref.SOURCES,
            "pending": PENDING, "credit_log": TRACXN_CREDIT_LOG,
            "companies": [], "watchlist_a": [], "watchlist_b": [], "historical_ipos": ipo_records}
    with open(os.path.join(ROOT, "dashboard", "data.js"), "w") as fh:
        fh.write("// Generated by src/build.py - do not edit\nwindow.DATA = " + json.dumps(data, indent=1) + ";\n")
    with open(os.path.join(MODEL, "dashboard_data.json"), "w") as fh:
        json.dump(data, fh, indent=1)


if __name__ == "__main__":
    for d in (OUT, CLEAN, MODEL):
        os.makedirs(d, exist_ok=True)
    t = build_tables()
    build_workbooks(*t)
    build_dashboard_data(*t)
    import report  # noqa: E402
    report.build(*t, credit_log=TRACXN_CREDIT_LOG, pending=PENDING, blocked=BLOCKED_DOMAINS)
    print("Built:", sorted(os.listdir(OUT)))
