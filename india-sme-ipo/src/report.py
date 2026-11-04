"""IPO_Research_Report.pdf (reportlab)."""
import os

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, PageBreak

import reference as ref
from scoring import READINESS_WEIGHTS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAVY = colors.HexColor("#1F3A5F")


def _tbl(rows, widths=None):
    t = Table(rows, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                           ("FONTSIZE", (0, 0), (-1, -1), 7.5), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B8C2CC")),
                           ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F6F9")])]))
    return t


def _chart(recon):
    d = Drawing(460, 190)
    c = VerticalBarChart()
    c.x, c.y, c.width, c.height = 40, 30, 400, 135
    c.data = [[r["tracxn_nse_plus_bse"] for r in recon],
              [r["external_sme_ipo_count"] or 0 for r in recon]]
    c.categoryAxis.categoryNames = [str(r["year"]) for r in recon]
    c.categoryAxis.labels.fontSize = 7
    c.valueAxis.labels.fontSize = 7
    c.valueAxis.valueMin = 0
    c.bars[0].fillColor = NAVY
    c.bars[1].fillColor = colors.HexColor("#E8A33D")
    c.barSpacing = 1
    d.add(c)
    d.add(String(40, 178, "Navy: Tracxn NSE+BSE listing events (all boards).  Amber: external SME-only IPO count "
                          "(0 = not retrieved)", fontSize=7))
    return d


def build(by_year, by_ex, recon, ipo_records, credit_log, pending, blocked):
    ss = getSampleStyleSheet()
    H1 = ParagraphStyle("h1", parent=ss["Heading1"], textColor=NAVY, fontSize=16)
    H2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=NAVY, fontSize=12)
    B = ParagraphStyle("b", parent=ss["BodyText"], fontSize=9, leading=12)
    P = lambda t: Paragraph(t, B)  # noqa: E731
    s = []
    s += [Paragraph("India SME IPO Readiness Research - Status Report", H1),
          P("Built 04 November 2026. Independent financial research; no media-sales analysis."), Spacer(1, 6)]
    s += [Paragraph("1. Executive summary", H2),
          P("<b>Where we are.</b> The analytical engine is built and tested: data model, NSE Emerge / BSE SME "
            "eligibility engine, three-score model (readiness, intent, data confidence), backtest harness, "
            "workbooks and dashboard. Reference layers (MSME definitions, entity IPO routes, platform rules) and "
            "Tracxn aggregate IPO activity are populated."),
          P("<b>What is not done.</b> No company has been scored or ranked yet. Company-level data requires Tracxn "
            "record pulls (stages 2-4), which are on hold for your approval because the connector consumes credits "
            "and only 714 of 10,000 remain this month. No company names, financials or rankings have been estimated "
            "to fill the gap."),
          P("<b>Access.</b> Your logged-in Chrome session is not reachable: this research runs in a cloud container, "
            "not on your computer. The official Tracxn connector is connected and works. Official NSE, BSE, SEBI and "
            "MSME websites are blocked by the container's network policy, so every regulatory rule here comes from "
            "secondary sources and is flagged for primary verification.")]
    s += [Paragraph("2. IPO activity in India, 2018 to 2026 (Tracxn)", H2),
          P("Tracxn counts %d IPO listing events on Indian exchanges since 1 January 2018 (NSE %d, BSE %d). "
            "<b>These are not SME counts.</b> Tracxn's exchange field does not separate SME platforms from the "
            "mainboard, and a dual-listed IPO is counted once per exchange. The external SME-only series "
            "(Chittorgarh, secondary) is much lower, which confirms the mix." % (
                sum(r["listing_events"] for r in by_ex),
                sum(r["listing_events"] for r in by_ex if r["exchange"] == "NSE"),
                sum(r["listing_events"] for r in by_ex if r["exchange"] in ("BSE", "BOM")))),
          _chart(recon),
          _tbl([["Year", "Tracxn NSE", "Tracxn BSE", "NSE+BSE", "Ext. SME IPOs", "Ext. SME Rs cr", "Note"]] +
               [[r["year"], r["tracxn_nse_events"], r["tracxn_bse_events"], r["tracxn_nse_plus_bse"],
                 r["external_sme_ipo_count"] if r["external_sme_ipo_count"] is not None else "n/a",
                 r["external_sme_amount_cr"] if r["external_sme_amount_cr"] is not None else "n/a",
                 r["note"].strip("; ")] for r in recon],
               [1.2 * cm, 1.7 * cm, 1.7 * cm, 1.6 * cm, 2 * cm, 2 * cm, 6.5 * cm]),
          Spacer(1, 4),
          P("Directional reading (verify): on the external series, SME IPO activity grew strongly from 2020 to 2023. "
            "An RBI Bulletin article reports SME IPO listings in 2024-25 were 87.2% above 2022-23 (secondary summary; "
            "not checked against the RBI text).")]
    s += [Paragraph("3. MSME definitions", H2),
          _tbl([["Regime", "Category", "Investment max (Rs cr)", "Turnover max (Rs cr)"]] +
               [[r["regime"], r["category"], r["investment_max_cr"], r["turnover_max_cr"]] for r in ref.MSME_CLASSIFICATION],
               [7 * cm, 2 * cm, 3.5 * cm, 3.5 * cm]),
          P(ref.MSME_NOTE)]
    s += [PageBreak(), Paragraph("4. Eligibility rules implemented", H2)]
    for p, rules in ref.PLATFORM_RULES.items():
        s += [P("<b>%s</b>" % p),
              _tbl([["ID", "Rule", "Verification"]] + [[r["id"], P(r["text"]), P(r["verification"])] for r in rules],
                   [2 * cm, 9.5 * cm, 5.5 * cm])]
    s += [P("<b>Issue-structure rules</b> (apply to the offer):"),
          _tbl([["ID", "Rule", "Verification"]] + [[r["id"], P(r["text"]), P(r["verification"])] for r in ref.ISSUE_STRUCTURE_RULES],
               [2 * cm, 9.5 * cm, 5.5 * cm]),
          P("Classification: 1 Appears to meet measurable requirements; 2 Potentially eligible, further verification "
            "required (for example, a private limited company that must convert); 3 Fails one or more measurable "
            "requirements; 4 Insufficient information. Only financial years closed before the assessment date are used.")]
    s += [Paragraph("5. Scoring methodology", H2),
          _tbl([["Readiness component", "Weight"]] + [[k.replace("_", " ").title(), v] for k, v in READINESS_WEIGHTS.items()],
               [8 * cm, 2 * cm]),
          P("Intent (0-100) adds points for evidence, weighting direct disclosures (DRHP filing 45, exchange "
            "in-principle approval 45, board approval 20, merchant banker 15, announcement 15) far above indirect signals "
            "(conversion to public limited 10, pre-IPO placement 10, funding round 5). Any direct signal places a company "
            "on List A. Data Confidence (0-100) scores audit status, years of history, source credibility, recency, "
            "entity-match quality and independent verification. <b>Scores are screening indices, not probabilities.</b>"),
          Paragraph("6. Backtesting", H2),
          P("Designed and implemented, not yet run. Snapshots at end-2020, end-2021 and end-2022 use only financial years "
            "closed by then, then check SME listings in the next three years against companies that stayed private "
            "(precision@50, lift, AUC, false-positive review). Until the historical cohort and a non-IPO comparison pool "
            "are loaded, the model is a research-screening tool, not a validated predictor. The 2025 EBITDA test also means "
            "earlier issuers faced looser rules, which biases any backtest.")]
    s += [PageBreak(), Paragraph("7. Decisions needed and next steps", H2),
          _tbl([["Stage", "What it unlocks"]] + [[k.replace("_", " ").title(), P(v)] for k, v in pending.items()],
               [2.5 * cm, 14.5 * cm]),
          Spacer(1, 4),
          P("<b>Tracxn credit log</b> (connector, 04-Nov-2026):"),
          _tbl([["#", "Tool", "Purpose", "Credits after", "Cost"]] +
               [[c["call"], c["tool"], P(c["purpose"]), c["credits_after"], c["cost"]] for c in credit_log],
               [0.7 * cm, 3.3 * cm, 8.5 * cm, 2 * cm, 2.5 * cm]),
          Spacer(1, 4),
          P("<b>Network domains to allow</b> for primary-source verification: " + ", ".join(blocked) + "."),
          Paragraph("8. Limitations", H2),
          P("Regulatory rules from secondary sources; BSE SME net-tangible-asset threshold conflicting (Rs 1.5 cr vs "
            "Rs 3 cr); BSE track-record rule unconfirmed; ICDR notification date differs across sources (3, 4 or 8 March "
            "2025). Tracxn private-company financial coverage is incomplete and favours entities with MCA filings. "
            "MSME status cannot be inferred from turnover alone."),
          Paragraph("9. Sources", H2),
          _tbl([["ID", "Title", "Publisher", "Status"]] + [[r["id"], P(r["title"]), P(r["publisher"]), P(r["status"])]
                                                          for r in ref.SOURCES],
               [1 * cm, 7 * cm, 4 * cm, 5 * cm])]
    path = os.path.join(ROOT, "outputs", "IPO_Research_Report.pdf")
    SimpleDocTemplate(path, pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm, topMargin=1.6 * cm,
                      bottomMargin=1.6 * cm, title="India SME IPO Readiness Research").build(s)
    return path
