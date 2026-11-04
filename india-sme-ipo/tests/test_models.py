"""Unit tests. Fixtures are HYPOTHETICAL companies used only to test logic;
they are not research data and never appear in deliverables."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from eligibility import assess, usable_years, CLASS_MEETS, CLASS_POTENTIAL, CLASS_FAILS, CLASS_INSUFFICIENT  # noqa: E402
from scoring import readiness_score, intent_score, confidence_score, backtest  # noqa: E402
from reference import classify_msme  # noqa: E402


def fixture(form="Public limited company", ebitda=(3.0, 2.5, 2.0), fcfe=(1.0, 0.5, -0.2), nw=(12, 10, 8),
            inc="2012-05-01", ipo=None):
    fys = [2025, 2024, 2023]
    return {"name": "TEST-CO", "legal_form": form, "incorporation_date": inc, "ipo_listing_date": ipo,
            "financials": [{"fy": fy, "revenue_cr": r, "ebitda_cr": e, "pat_cr": e / 2, "net_worth_cr": n,
                            "nta_cr": n, "fcfe_cr": f, "total_debt_cr": n * 0.4, "ocf_cr": e * 0.8,
                            "capex_cr": r * 0.06}
                           for fy, r, e, f, n in zip(fys, (40, 32, 25), ebitda, fcfe, nw)],
            "governance": {"registrar_compliant": True, "audited_financials": True, "auditor_known": True,
                           "insolvency_proceedings": False}}


class Eligibility(unittest.TestCase):
    def test_public_company_meets(self):
        self.assertEqual(assess(fixture(), "NSE Emerge", "2025-10-01")["classification"], CLASS_MEETS)

    def test_private_company_needs_conversion(self):
        r = assess(fixture(form="Private limited company"), "NSE Emerge", "2025-10-01")
        self.assertEqual(r["classification"], CLASS_POTENTIAL)

    def test_ebitda_fail(self):
        r = assess(fixture(ebitda=(0.5, 0.4, 2.0)), "BSE SME", "2025-10-01")
        self.assertEqual(r["classification"], CLASS_FAILS)

    def test_missing_financials(self):
        c = fixture()
        c["financials"] = []
        self.assertEqual(assess(c, "NSE Emerge", "2025-10-01")["classification"], CLASS_INSUFFICIENT)

    def test_no_future_leakage(self):
        rows = usable_years(fixture()["financials"], "2024-06-30")
        self.assertEqual([r["fy"] for r in rows], [2024, 2023])

    def test_young_company_fails_track_record(self):
        r = assess(fixture(inc="2024-01-01"), "NSE Emerge", "2025-10-01")
        self.assertEqual(r["classification"], CLASS_FAILS)


class Scores(unittest.TestCase):
    def test_readiness_range(self):
        r = readiness_score(fixture(), "2025-10-01")
        self.assertIsNotNone(r["score"])
        self.assertTrue(0 <= r["score"] <= 100)

    def test_readiness_withheld_when_sparse(self):
        c = {"incorporation_date": "2010-01-01", "financials": []}
        self.assertIsNone(readiness_score(c, "2025-10-01")["score"])

    def test_intent_ignores_future_signals(self):
        sig = [{"type": "drhp_filed", "date": "2026-01-01"}, {"type": "recent_funding_round", "date": "2025-01-01"}]
        r = intent_score(sig, "2025-10-01")
        self.assertEqual(r["score"], 5)
        self.assertFalse(r["has_direct_signal"])

    def test_confidence_max(self):
        r = confidence_score({"audited": True, "years_of_financials": 5, "source_type": "MCA filing",
                              "latest_fy_end": "2025-03-31", "as_of": "2025-10-01", "match_method": "CIN",
                              "independently_verified": True})
        self.assertEqual(r["score"], 100)

    def test_backtest_runs(self):
        cos = [fixture(ipo="2026-02-01"), fixture(ebitda=(0.2, 0.1, 0.1), ipo=None)]
        r = backtest(cos, "2025-10-01", horizon_years=1, top_k=1)
        self.assertEqual(r["n"], 2)
        self.assertEqual(r["positives"], 1)


class Msme(unittest.TestCase):
    def test_revised_limits(self):
        self.assertEqual(classify_msme(80, 20, "2025-06-01"), "Small")
        self.assertEqual(classify_msme(80, 20, "2024-06-01"), "Medium")

    def test_unverified_without_investment(self):
        self.assertTrue(classify_msme(80, None).startswith("Unverified"))
        self.assertTrue(classify_msme(800, None).startswith("Not MSME"))


if __name__ == "__main__":
    unittest.main()
