"""IPO Readiness (A), IPO Intent (B) and Data Confidence (C) scores, plus backtest.

Scores are screening indices on a 0-100 scale. They are NOT probabilities:
a readiness score of 85 does not mean an 85% chance of an IPO.

Weights below are initial hypotheses from the research brief, to be
re-estimated once the historical SME IPO cohort (Tracxn stages 2-3) is
loaded and backtested.
"""
from datetime import date

try:
    from .eligibility import usable_years, _d
except ImportError:
    from eligibility import usable_years, _d

READINESS_WEIGHTS = {"revenue_growth": 20, "profitability": 20, "financial_strength": 15,
                     "cash_flow_quality": 15, "operating_history": 10, "expansion": 10, "governance": 10}
MIN_WEIGHT_COVERAGE = 0.70  # below this share of weight with data, readiness is not scored

# Default benchmarks. Replace per sector with percentiles from the historical cohort
# (see analysis.sector_benchmarks). Values are placeholders, not findings.
DEFAULT_BENCHMARK = {"revenue_cagr_good": 0.30, "ebitda_margin_good": 0.15, "de_good": 0.5, "de_bad": 2.0,
                     "capex_intensity_good": 0.05, "label": "Default (not yet calibrated)"}

INTENT_SIGNAL_WEIGHTS = {
    # direct corporate / regulatory disclosures
    "drhp_filed": 45, "exchange_in_principle_approval": 45, "board_ipo_approval": 20,
    "merchant_banker_appointed": 15, "official_ipo_announcement": 15,
    # indirect signals
    "converted_to_public_limited": 10, "pre_ipo_placement": 10, "recent_funding_round": 5,
    "big_auditor_appointed": 5, "independent_directors_inducted": 5,
}
DIRECT_SIGNALS = {"drhp_filed", "exchange_in_principle_approval", "board_ipo_approval",
                  "merchant_banker_appointed", "official_ipo_announcement"}


def _clip(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def _cagr(first, last, years):
    if first is None or last is None or first <= 0 or years <= 0 or last <= 0:
        return None
    return (last / first) ** (1 / years) - 1


def readiness_components(company, as_of, bm=None):
    bm = bm or DEFAULT_BENCHMARK
    rows = usable_years(company.get("financials"), as_of)[:5]
    comp = {}
    rev = [r.get("revenue_cr") for r in rows]
    # Revenue growth: CAGR over available span (>=2 years of data) and consistency
    if len(rows) >= 3 and rev[0] is not None and rev[-1] is not None:
        span = rows[0]["fy"] - rows[-1]["fy"]
        cg = _cagr(rev[-1], rev[0], span)
        pairs = [(rev[i], rev[i + 1]) for i in range(len(rev) - 1) if rev[i] is not None and rev[i + 1] is not None]
        declines = sum(1 for a, b in pairs if a < b)
        if cg is not None:
            comp["revenue_growth"] = _clip(cg / bm["revenue_cagr_good"]) * (1 - 0.25 * min(declines, 2))
    # Profitability: EBITDA margin (latest) + PAT-positive years in last 3
    if rows and rows[0].get("ebitda_cr") is not None and rows[0].get("revenue_cr"):
        m = rows[0]["ebitda_cr"] / rows[0]["revenue_cr"]
        pats = [r.get("pat_cr") for r in rows[:3] if r.get("pat_cr") is not None]
        pat_part = (sum(1 for p in pats if p > 0) / 3) if pats else 0
        comp["profitability"] = 0.5 * _clip(m / bm["ebitda_margin_good"]) + 0.5 * pat_part
    # Financial strength: debt/equity and net worth trend
    if rows and rows[0].get("net_worth_cr") is not None:
        nw = rows[0]["net_worth_cr"]
        debt = rows[0].get("total_debt_cr")
        if nw <= 0:
            comp["financial_strength"] = 0.0
        elif debt is not None:
            de = debt / nw
            de_part = _clip((bm["de_bad"] - de) / (bm["de_bad"] - bm["de_good"]))
            grow = 1.0 if len(rows) > 1 and rows[1].get("net_worth_cr") is not None and nw > rows[1]["net_worth_cr"] else 0.0
            comp["financial_strength"] = 0.7 * de_part + 0.3 * grow
    # Cash-flow quality: OCF-positive years + OCF/EBITDA conversion
    ocf = [r.get("ocf_cr") for r in rows[:3] if r.get("ocf_cr") is not None]
    if ocf:
        conv = None
        if rows[0].get("ocf_cr") is not None and rows[0].get("ebitda_cr"):
            conv = _clip(rows[0]["ocf_cr"] / rows[0]["ebitda_cr"]) if rows[0]["ebitda_cr"] > 0 else 0.0
        comp["cash_flow_quality"] = 0.6 * (sum(1 for v in ocf if v > 0) / 3) + 0.4 * (conv or 0)
    # Operating history: 0 below 3 years, 1 at 10+ years
    if company.get("incorporation_date"):
        yrs = (_d(as_of) - _d(company["incorporation_date"])).days / 365.25
        comp["operating_history"] = _clip((yrs - 3) / 7)
    # Expansion: capex intensity + headcount growth when available
    parts = []
    if rows and rows[0].get("capex_cr") is not None and rows[0].get("revenue_cr"):
        parts.append(_clip((rows[0]["capex_cr"] / rows[0]["revenue_cr"]) / bm["capex_intensity_good"]))
    if company.get("employee_growth_1y") is not None:
        parts.append(_clip(company["employee_growth_1y"] / 0.2))
    if parts:
        comp["expansion"] = sum(parts) / len(parts)
    # Governance: registrar compliance, audited accounts, no insolvency, auditor known
    g = company.get("governance") or {}
    gparts = [v for v in (g.get("registrar_compliant"), g.get("audited_financials"),
                          (None if g.get("insolvency_proceedings") is None else not g["insolvency_proceedings"]),
                          g.get("auditor_known")) if v is not None]
    if gparts:
        comp["governance"] = sum(1 for v in gparts if v) / len(gparts)
    return comp


def readiness_score(company, as_of, bm=None):
    comp = readiness_components(company, as_of, bm)
    avail = sum(READINESS_WEIGHTS[k] for k in comp)
    coverage = avail / sum(READINESS_WEIGHTS.values())
    points = {k: round(v * READINESS_WEIGHTS[k], 2) for k, v in comp.items()}
    score = round(100 * sum(points.values()) / avail, 1) if avail else None
    return {"score": score if coverage >= MIN_WEIGHT_COVERAGE else None,
            "score_if_any": score, "weight_coverage": round(coverage, 2), "points": points,
            "missing_components": [k for k in READINESS_WEIGHTS if k not in comp],
            "benchmark": (bm or DEFAULT_BENCHMARK)["label"]}


def intent_score(signals, as_of):
    """signals: [{"type": <INTENT_SIGNAL_WEIGHTS key>, "date": "YYYY-MM-DD", "source_id": ..}]"""
    seen = {}
    for s in signals or []:
        if s.get("date") and _d(s["date"]) > _d(as_of):
            continue  # no future leakage
        t = s["type"]
        if t in INTENT_SIGNAL_WEIGHTS:
            seen[t] = INTENT_SIGNAL_WEIGHTS[t]
    score = min(100, sum(seen.values()))
    has_direct = bool(DIRECT_SIGNALS & set(seen))
    return {"score": score, "signals": sorted(seen), "has_direct_signal": has_direct,
            "watchlist": "A - Confirmed IPO preparation" if has_direct else None}


def confidence_score(meta):
    """meta keys: audited (bool), years_of_financials (int), source_type, latest_fy_end (date str),
    as_of, match_method ('CIN'|'name_location_validated'|'uncertain'), independently_verified (bool)."""
    pts = {}
    pts["audited_financials"] = 25 if meta.get("audited") else (10 if meta.get("audited") is None else 0)
    y = meta.get("years_of_financials") or 0
    pts["history_completeness"] = 20 if y >= 5 else 12 if y >= 3 else 6 if y >= 1 else 0
    pts["source_credibility"] = {"MCA filing": 20, "Tracxn legal entity": 18, "DRHP/RHP": 20,
                                 "Tracxn company": 14, "News": 8, "Estimate": 4}.get(meta.get("source_type"), 0)
    if meta.get("latest_fy_end") and meta.get("as_of"):
        age = (_d(meta["as_of"]) - _d(meta["latest_fy_end"])).days / 30.4
        pts["recency"] = 15 if age <= 18 else 8 if age <= 30 else 2
    else:
        pts["recency"] = 0
    pts["entity_match"] = {"CIN": 10, "name_location_validated": 6, "uncertain": 2}.get(meta.get("match_method"), 0)
    pts["independent_verification"] = 10 if meta.get("independently_verified") else 0
    return {"score": sum(pts.values()), "points": pts}


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------
def backtest(companies, snapshot, horizon_years=3, top_k=50, bm=None):
    """companies: list of dicts with financials plus 'ipo_listing_date' (None if never listed).

    Uses only data available at ``snapshot``. Companies already listed at the
    snapshot are excluded. Returns precision@k, base rate and AUC.
    """
    snap = _d(snapshot)
    end = date(snap.year + horizon_years, snap.month, snap.day)
    pool = []
    for c in companies:
        ipo = _d(c["ipo_listing_date"]) if c.get("ipo_listing_date") else None
        if ipo and ipo <= snap:
            continue
        r = readiness_score(c, snap, bm)
        if r["score"] is None:
            continue
        pool.append((r["score"], 1 if ipo and snap < ipo <= end else 0, c.get("name")))
    if not pool:
        return {"snapshot": str(snap), "n": 0, "note": "No scorable companies at snapshot"}
    pool.sort(key=lambda x: x[0], reverse=True)
    pos = sum(p[1] for p in pool)
    k = min(top_k, len(pool))
    prec = sum(p[1] for p in pool[:k]) / k
    # AUC via Mann-Whitney
    auc = None
    if 0 < pos < len(pool):
        ranks = {}
        ordered = sorted(pool, key=lambda x: x[0])
        for i, p in enumerate(ordered, 1):
            ranks.setdefault(p[0], []).append(i)
        rank_of = {s: sum(v) / len(v) for s, v in ranks.items()}
        rsum = sum(rank_of[p[0]] for p in pool if p[1])
        auc = (rsum - pos * (pos + 1) / 2) / (pos * (len(pool) - pos))
    return {"snapshot": str(snap), "horizon_end": str(end), "n": len(pool), "positives": pos,
            "base_rate": round(pos / len(pool), 4), f"precision_at_{k}": round(prec, 4),
            "lift": round(prec / (pos / len(pool)), 2) if pos else None,
            "auc": round(auc, 3) if auc is not None else None,
            "false_positives_in_top_k": [p[2] for p in pool[:k] if not p[1]][:20]}
