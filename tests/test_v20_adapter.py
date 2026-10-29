import unittest
from v20_adapter import build

class AdapterTests(unittest.TestCase):
    def test_keyword_is_not_confirmed_supply(self):
        result = build(
            {"checked_utc": "2026-10-29T00:00:00Z", "tickers": {
                "XYZ": {"filings": [{"date": "2026-10-28", "form": "8-K",
                                     "accession": "0001", "url": "https://www.sec.gov/example"}]}}},
            {"tickers": {"XYZ": {"supply_review_candidate": "D",
                                  "evidence": [{"category": "WARRANT"}]}}})
        row = result["results"][0]
        self.assertEqual(row["classification"], "REVIEW_REQUIRED")
        self.assertEqual(row["existing_supply_review_candidate"], "D")
        self.assertIsNone(row["immediate_supply_shares"])
        self.assertIsNone(row["sec_score"])
        self.assertEqual(row["confidence"], "D")

    def test_missing_filing_is_unresolved(self):
        result = build({"checked_utc": "2026-10-29T00:00:00Z", "tickers": {}},
                       {"tickers": {"XYZ": {"evidence": []}}})
        self.assertTrue(result["results"][0]["unresolved"])

if __name__ == "__main__":
    unittest.main()
