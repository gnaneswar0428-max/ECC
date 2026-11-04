"""Reference data for the India SME IPO research project.

Every rule carries a ``verification`` field. As of 2026-11-04 the official
NSE / BSE / SEBI / MSME websites are blocked from the research container,
so rules below were assembled from secondary sources found through web
search. They MUST be checked against the primary documents listed in
``SOURCES`` before any eligibility output is relied upon.
"""

RULES_AS_OF = "2026-11-04"

# ---------------------------------------------------------------------------
# MSME classification (composite investment + turnover test)
# Values in INR crore. Investment = plant & machinery / equipment.
# ---------------------------------------------------------------------------
MSME_CLASSIFICATION = [
    {"regime": "Notification S.O. 2119(E), 26-Jun-2020", "effective_from": "2020-07-01",
     "effective_to": "2025-03-31", "category": "Micro", "investment_max_cr": 1, "turnover_max_cr": 5,
     "source_id": "S03"},
    {"regime": "Notification S.O. 2119(E), 26-Jun-2020", "effective_from": "2020-07-01",
     "effective_to": "2025-03-31", "category": "Small", "investment_max_cr": 10, "turnover_max_cr": 50,
     "source_id": "S03"},
    {"regime": "Notification S.O. 2119(E), 26-Jun-2020", "effective_from": "2020-07-01",
     "effective_to": "2025-03-31", "category": "Medium", "investment_max_cr": 50, "turnover_max_cr": 250,
     "source_id": "S03"},
    {"regime": "Notification S.O. 1364(E), 21-Mar-2025", "effective_from": "2025-04-01",
     "effective_to": None, "category": "Micro", "investment_max_cr": 2.5, "turnover_max_cr": 10,
     "source_id": "S04"},
    {"regime": "Notification S.O. 1364(E), 21-Mar-2025", "effective_from": "2025-04-01",
     "effective_to": None, "category": "Small", "investment_max_cr": 25, "turnover_max_cr": 100,
     "source_id": "S04"},
    {"regime": "Notification S.O. 1364(E), 21-Mar-2025", "effective_from": "2025-04-01",
     "effective_to": None, "category": "Medium", "investment_max_cr": 125, "turnover_max_cr": 500,
     "source_id": "S04"},
]
MSME_NOTE = (
    "Classification needs BOTH the investment and the turnover test. Turnover alone "
    "cannot establish MSME status. Where plant/machinery investment is unknown, this "
    "project marks MSME classification as 'Unverified'. Official status comes only from "
    "Udyam registration. Verification: secondary sources (S04, S05); confirm against the "
    "Gazette notification."
)


def classify_msme(turnover_cr, investment_cr, as_of="2025-04-01"):
    """Return MSME category or 'Unverified' / 'Not MSME (exceeds Medium)'."""
    if turnover_cr is None:
        return "Unverified (turnover unknown)"
    regime = [r for r in MSME_CLASSIFICATION
              if r["effective_from"] <= as_of and (r["effective_to"] is None or as_of <= r["effective_to"])]
    if investment_cr is None:
        medium = [r for r in regime if r["category"] == "Medium"][0]
        if turnover_cr > medium["turnover_max_cr"]:
            return "Not MSME (turnover exceeds Medium limit)"
        return "Unverified (investment unknown)"
    for r in regime:  # ordered Micro -> Small -> Medium
        if investment_cr <= r["investment_max_cr"] and turnover_cr <= r["turnover_max_cr"]:
            return r["category"]
    return "Not MSME (exceeds Medium limits)"


# ---------------------------------------------------------------------------
# Legal entity types and the route to an IPO
# ---------------------------------------------------------------------------
ENTITY_IPO_ROUTES = [
    {"entity_type": "Public limited company", "can_ipo_directly": "Yes",
     "route": "Can file a DRHP directly if platform criteria are met.",
     "verification": "General company law; confirm with counsel"},
    {"entity_type": "Private limited company", "can_ipo_directly": "No",
     "route": "Must convert to a public limited company (Companies Act 2013, s.14 alteration of articles) "
              "before filing the offer document.",
     "verification": "General company law; confirm with counsel"},
    {"entity_type": "One Person Company", "can_ipo_directly": "No",
     "route": "Must convert to a private or public company first.",
     "verification": "General company law; confirm with counsel"},
    {"entity_type": "LLP", "can_ipo_directly": "No",
     "route": "Must convert or register as a company (Companies Act 2013, Part I Chapter XXI, s.366), "
              "then become public. Track record of the predecessor entity may count; check platform rules.",
     "verification": "Exchange rules on predecessor track record need primary-source check"},
    {"entity_type": "Partnership firm", "can_ipo_directly": "No",
     "route": "Must be registered as a company (s.366) or have its business taken over by a company.",
     "verification": "Exchange rules on predecessor track record need primary-source check"},
    {"entity_type": "Proprietorship", "can_ipo_directly": "No",
     "route": "Business must be transferred into a newly incorporated company.",
     "verification": "Exchange rules on predecessor track record need primary-source check"},
]

# ---------------------------------------------------------------------------
# Platform eligibility rules. "kind" drives the engine in eligibility.py.
# Thresholds in INR crore. None means not a numeric rule.
# ---------------------------------------------------------------------------
_SEBI_EBITDA = {"id": "SEBI-OP", "kind": "ebitda_n_of_3", "threshold_cr": 1.0, "n": 2,
                "text": "Operating profit (EBITDA) of at least INR 1 crore in at least 2 of the 3 financial "
                        "years preceding the DRHP (SEBI ICDR amendment, 2025).",
                "effective": "DRHPs filed on/after 19-Dec-2024 (NSE); ICDR notified Mar-2025 (date conflicts "
                             "across sources: 3, 4 or 8 March)",
                "verification": "Secondary sources (S06, S07, S08); EBITDA wording unconfirmed in one source",
                "source_id": "S06"}
_PAIDUP = {"id": "SEBI-PUC", "kind": "post_issue_paidup_max", "threshold_cr": 25.0,
           "text": "Post-issue paid-up capital (face value) not more than INR 25 crore for the SME route.",
           "effective": "Long-standing ICDR Chapter IX provision",
           "verification": "Secondary source (S09); confirm current ICDR Reg. 229",
           "source_id": "S09"}
_LEGAL = {"id": "LEGAL-PUB", "kind": "legal_public_company", "threshold_cr": None,
          "text": "Issuer must be a public limited company incorporated under the Companies Act when filing.",
          "effective": "Standing requirement", "verification": "Company law; confirm with counsel",
          "source_id": "S09"}

PLATFORM_RULES = {
    "NSE Emerge": [
        _LEGAL,
        {"id": "NSE-TR", "kind": "track_record_years", "threshold_cr": None, "years": 3,
         "text": "Operational track record of at least 3 years.",
         "effective": "Per NSE criteria page as summarised by secondary sources",
         "verification": "Secondary source (S01 summary); confirm on NSE criteria page",
         "source_id": "S01"},
        _SEBI_EBITDA,
        {"id": "NSE-NW", "kind": "networth_positive_latest", "threshold_cr": 0.0,
         "text": "Positive net worth.",
         "effective": "Per NSE criteria page as summarised by secondary sources",
         "verification": "Secondary source; confirm on NSE criteria page", "source_id": "S01"},
        {"id": "NSE-FCFE", "kind": "fcfe_n_of_3", "threshold_cr": 0.0, "n": 2,
         "text": "Positive free cash flow to equity (FCFE) in at least 2 of the 3 years before applying.",
         "effective": "Per NSE criteria page as summarised by secondary sources",
         "verification": "Secondary source; confirm on NSE criteria page and circular CML65739",
         "source_id": "S02"},
        _PAIDUP,
    ],
    "BSE SME": [
        _LEGAL,
        {"id": "BSE-TR", "kind": "track_record_years", "threshold_cr": None, "years": 3,
         "text": "Track record of at least 3 years (reported by one secondary source only).",
         "effective": "Unconfirmed", "verification": "UNCONFIRMED; single secondary source (S10)",
         "source_id": "S10"},
        _SEBI_EBITDA,
        {"id": "BSE-NW", "kind": "networth_min_each_of_last_n", "threshold_cr": 1.0, "n": 2,
         "text": "Net worth of at least INR 1 crore in each of the 2 preceding full financial years.",
         "effective": "Per BSE SME criteria as summarised by secondary sources",
         "verification": "Secondary sources conflict; confirm on BSE SME site", "source_id": "S10"},
        {"id": "BSE-NTA", "kind": "nta_min_latest", "threshold_cr": 3.0,
         "text": "Net tangible assets of at least INR 3 crore in the latest year (some sources say 1.5 crore).",
         "effective": "Conflicting", "verification": "CONFLICTING secondary sources; confirm on BSE SME site",
         "source_id": "S10"},
        _PAIDUP,
    ],
}

# Issue-structure rules (apply to the offer, not to the company's financials)
ISSUE_STRUCTURE_RULES = [
    {"id": "SEBI-OFS", "text": "Offer for sale capped at 20% of the issue size; no selling shareholder may sell "
                               "more than 50% of their holding.", "verification": "Secondary sources (S07, S08)",
     "source_id": "S07"},
    {"id": "SEBI-GCP", "text": "General corporate purposes capped at the lower of 15% of the issue or INR 10 crore.",
     "verification": "Secondary source (S08); confirm against Gazette", "source_id": "S08"},
    {"id": "SEBI-LOCKIN", "text": "Promoter holding above the minimum promoter contribution: lock-in released in "
                                  "phases (exact schedule not confirmed).",
     "verification": "Secondary source; schedule unconfirmed", "source_id": "S08"},
]

# ---------------------------------------------------------------------------
# Source register. URLs were returned by web search on 2026-11-04. Pages
# marked 'not fetched' could not be opened from the container (network policy).
# ---------------------------------------------------------------------------
SOURCES = [
    {"id": "S01", "title": "NSE Emerge eligibility criteria (official page)",
     "publisher": "National Stock Exchange of India", "type": "Primary - exchange",
     "url": "https://www.nseindia.com/companies-listing/raising-capital-public-issues-emerge-eligibility-criteria",
     "accessed": "2026-11-04", "status": "Not fetched (domain blocked); content known only via search summary"},
    {"id": "S02", "title": "NSE circular CML65739 (SME eligibility conditions)",
     "publisher": "National Stock Exchange of India", "type": "Primary - exchange circular",
     "url": "https://nsearchives.nseindia.com/content/circulars/CML65739.pdf",
     "accessed": "2026-11-04", "status": "Not fetched (domain blocked)"},
    {"id": "S03", "title": "MSME classification notification S.O. 2119(E), 26 June 2020",
     "publisher": "Ministry of MSME, Government of India", "type": "Primary - Gazette",
     "url": "", "accessed": "2026-11-04",
     "status": "Referenced by secondary sources; primary not fetched"},
    {"id": "S04", "title": "Revised MSME classification limits (S.O. 1364(E), 21 March 2025) - summary",
     "publisher": "Taxmann", "type": "Secondary - professional publisher",
     "url": "https://www.taxmann.com/post/blog/revised-msme-classification",
     "accessed": "2026-11-04", "status": "Search summary only"},
    {"id": "S05", "title": "Govt notifies revised criteria for classifying MSMEs",
     "publisher": "All India Radio News (newsonair.gov.in)", "type": "Secondary - government broadcaster",
     "url": "https://newsonair.gov.in/govt-notifies-revised-criteria-for-classifying-msmes",
     "accessed": "2026-11-04", "status": "Search summary only"},
    {"id": "S06", "title": "NSE imposes new eligibility conditions for SME IPOs day after Sebi nod",
     "publisher": "Business Standard", "type": "Secondary - news",
     "url": "https://www.business-standard.com/markets/news/nse-brings-in-new-eligibility-conditions-for-sme-ipos-into-effect-124122000887_1.html",
     "accessed": "2026-11-04", "status": "Search summary only"},
    {"id": "S07", "title": "Client Alert: SEBI ICDR Amendments (March 2025)",
     "publisher": "Cyril Amarchand Mangaldas", "type": "Secondary - law firm",
     "url": "https://www.cyrilshroff.com/wp-content/uploads/2025/03/Client-Alert-SEBI-ICDR-Amendments.pdf",
     "accessed": "2026-11-04", "status": "Search summary only"},
    {"id": "S08", "title": "SEBI ICDR amendments - a strategic step to streamline regulatory landscape",
     "publisher": "KPMG India", "type": "Secondary - advisory",
     "url": "https://assets.kpmg.com/content/dam/kpmgsites/in/pdf/2025/04/chapter-2-sebi-icdr-amendments-a-strategic-step-to-streamline-regulatory-landscape.pdf.coredownload.inline.pdf",
     "accessed": "2026-11-04", "status": "Search summary only"},
    {"id": "S09", "title": "SEBI (ICDR) Regulations 2018, Chapter IX (SME issues)",
     "publisher": "Securities and Exchange Board of India", "type": "Primary - regulation",
     "url": "", "accessed": "2026-11-04", "status": "Not fetched (sebi.gov.in blocked)"},
    {"id": "S10", "title": "BSE SME eligibility (secondary summaries: Upstox, Taxguru, Corporate Professionals)",
     "publisher": "Various", "type": "Secondary - mixed",
     "url": "https://taxguru.in/sebi/revised-eligibility-criteria-listing-sme-platform-bse.html",
     "accessed": "2026-11-04", "status": "Search summary only; sources conflict on NTA figure"},
    {"id": "S11", "title": "SME IPOs by year, number and funds raised",
     "publisher": "Chittorgarh.com", "type": "Secondary - IPO data aggregator",
     "url": "https://chittorgarh.com/report/list-of-sme-ipo-by-year-fund-raised/153/sme/?year=2020",
     "accessed": "2026-11-04", "status": "Search summary only; site's own pages mark some years partial"},
    {"id": "S12", "title": "RBI Bulletin article on SME IPO market",
     "publisher": "Reserve Bank of India", "type": "Primary - central bank publication",
     "url": "https://www.rbi.org.in/Scripts/BS_ViewBulletin.aspx?Id=23715",
     "accessed": "2026-11-04", "status": "Search summary only"},
    {"id": "S13", "title": "Tracxn MCP connector - IPO Transactions aggregation (India, 2018-2026)",
     "publisher": "Tracxn Technologies", "type": "Licensed database",
     "url": "data/raw/tracxn/2026-11-04_q01_ipo_events_by_exchange.json; ..._q02_...json",
     "accessed": "2026-11-04", "status": "Retrieved; raw response preserved read-only"},
    {"id": "S14", "title": "MSME state-wise Udyam registrations (Parliament replies; IBEF Aug-2025 infographic)",
     "publisher": "Sansad digital library; IBEF", "type": "Primary (Parliament) / Secondary (IBEF)",
     "url": "https://www.ibef.org/uploads/industry/Infrographics/large/msme-infographic-august-2025.pdf",
     "accessed": "2026-11-04", "status": "Search summary only; shares, not counts"},
]

# External cross-check of SME-only IPO counts (S11). Used ONLY to show that
# Tracxn NSE/BSE totals include mainboard listings. 2024 marked partial by source.
EXTERNAL_SME_IPO_COUNTS = [
    {"year": 2020, "sme_ipos": 27, "amount_cr": 168, "note": "", "source_id": "S11"},
    {"year": 2021, "sme_ipos": 59, "amount_cr": 787, "note": "", "source_id": "S11"},
    {"year": 2022, "sme_ipos": 109, "amount_cr": 1980, "note": "", "source_id": "S11"},
    {"year": 2023, "sme_ipos": 182, "amount_cr": 4967, "note": "", "source_id": "S11"},
    {"year": 2024, "sme_ipos": 117, "amount_cr": 3864, "note": "Source marks year as partial", "source_id": "S11"},
]

# State share of Udyam registrations, FY24 (S14, IBEF). Shares only.
STATE_MSME_SHARE_FY24 = [
    {"state": "Maharashtra", "share_pct": 13.17, "source_id": "S14"},
    {"state": "Uttar Pradesh", "share_pct": 10.84, "source_id": "S14"},
    {"state": "Tamil Nadu", "share_pct": 8.02, "source_id": "S14"},
]
