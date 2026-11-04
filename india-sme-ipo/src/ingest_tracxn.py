"""Normalise preserved Tracxn responses (data/raw/tracxn) into cleaned tables.

Raw files are never modified. Stage-1 files are aggregation responses.
Stage-2+ files (when approved and retrieved) are expected to be named
``*_ipo_events_page*.json`` and ``*_legal_entities_page*.json`` and to hold the
connector response verbatim; parsing is defensive because field shapes can vary.
"""
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw", "tracxn")


def _load(path):
    with open(path) as fh:
        d = json.load(fh)
    return d.get("response", d)


def listings_by_year_exchange():
    rows = []
    for p in glob.glob(os.path.join(RAW, "*_ipo_events_by_year_exchange.json")):
        for yb in _load(p)["result"]:
            year = int(yb["term"][:4])
            for ex in yb["values"]:
                rows.append({"year": year, "exchange": ex["term"], "listing_events": ex["value"],
                             "source_id": "S13", "raw_file": os.path.basename(p)})
    return sorted(rows, key=lambda r: (r["year"], r["exchange"]))


def listings_by_exchange():
    rows = []
    for p in glob.glob(os.path.join(RAW, "*_ipo_events_by_exchange.json")):
        for b in _load(p)["result"]:
            rows.append({"exchange": b["term"], "listing_events": b["value"], "source_id": "S13",
                         "raw_file": os.path.basename(p)})
    return rows


def _get(d, *path):
    for k in path:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def _inr_cr(amount_obj):
    """Tracxn amounts arrive as {currency, amount} or plain numbers; return INR crore if INR."""
    if amount_obj is None:
        return None
    if isinstance(amount_obj, (int, float)):
        return None  # currency unknown -> do not guess
    cur = amount_obj.get("currency") or amount_obj.get("baseCurrency")
    val = amount_obj.get("amount") if not isinstance(amount_obj.get("amount"), dict) else None
    if cur == "INR" and isinstance(val, (int, float)):
        return round(val / 1e7, 4)
    return None


def ipo_event_records():
    """Company-level IPO rows from stage-2 search pages (empty until retrieved)."""
    out = []
    for p in sorted(glob.glob(os.path.join(RAW, "*_ipo_events_page*.json"))):
        for r in _load(p).get("result", []) or []:
            ex = r.get("stockExchanges") or []
            out.append({
                "tracxn_ipo_id": r.get("id"), "company_name": _get(r, "company", "name"),
                "tracxn_company_id": _get(r, "company", "id"), "ipo_date": r.get("ipoDate"),
                "exchanges": "; ".join(str(e.get("name") or e.get("symbol") or e) if isinstance(e, dict) else str(e)
                                       for e in ex),
                "issue_size_cr": _inr_cr(_get(r, "amountRaised", "total")),
                "fresh_issue_cr": _inr_cr(_get(r, "amountRaised", "byCompany")),
                "ofs_cr": _inr_cr(_get(r, "amountRaised", "byShareholders")),
                "issue_price_inr": _get(r, "shareIssuePrice", "amount"),
                "market_cap_cr": _inr_cr(r.get("marketCap")),
                "pre_ipo_revenue_cr": _inr_cr(_get(r, "financialsClosestToIPO", "revenue")),
                "pre_ipo_pat_cr": _inr_cr(_get(r, "financialsClosestToIPO", "netProfit")),
                "pre_ipo_fin_as_on": _get(r, "financialsClosestToIPO", "asOnDate"),
                "board": "UNVERIFIED (needs exchange confirmation)",
                "source_id": "S13", "raw_file": os.path.basename(p)})
    return out
