import unittest
from v20_sec_review import evaluate

class V20ReviewTests(unittest.TestCase):
    def test_missing_sources_never_confirm_supply(self):
        result = evaluate({"ticker": "TEST", "as_of": "2026-10-30T00:00:00Z",
                           "source_ledger": [], "share_ledger": [],
                           "financing_ledger": [], "event_ledger": []})
        self.assertEqual(result["classification"], "REVIEW_REQUIRED")
        self.assertIsNone(result["immediate_supply_shares"])
        self.assertTrue(result["first_stage_score_unchanged"])
        self.assertEqual(result["confidence"], "D")

    def test_duplicate_instrument_flagged(self):
        evidence = {"ticker": "TEST", "as_of": "2026-10-30T00:00:00Z",
                    "source_ledger": [{"form": "8-K", "filing_date": "2026-10-29",
                                       "accession": "sample", "source_url": "https://www.sec.gov/"}],
                    "share_ledger": [
                        {"instrument_id": "x", "bucket": "already_outstanding", "quantity": 100},
                        {"instrument_id": "x", "bucket": "resale_already_outstanding", "quantity": 100}],
                    "financing_ledger": [], "event_ledger": []}
        result = evaluate(evidence)
        self.assertTrue(any("double-count" in s for s in result["unresolved"]))
        self.assertIsNone(result["sec_score"])

if __name__ == "__main__":
    unittest.main()
