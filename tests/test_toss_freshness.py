"""Regression tests for saved Toss samples and quote freshness rules."""
import unittest
from datetime import datetime, timezone
from toss_freshness_check import diagnose

class TestTossFreshness(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 29, 16, 45, tzinfo=timezone.utc)

    def test_separate_file_and_quote_freshness(self):
        sample = {
            "updated_utc": "2026-10-29T16:44:00+00:00",
            "nasdaq7": [
                {"ticker": "FRESH", "candle_time": "2026-10-29T16:42:00+00:00"},
                {"ticker": "OLD", "candle_time": "2026-07-21T00:00:00+00:00"},
            ],
            "china1": [
                {"ticker": "CHINA", "candle_time": "2026-10-29T16:43:00+00:00"},
            ],
        }
        result = diagnose(sample, self.now)
        self.assertEqual(result["row_count"], 3)
        self.assertEqual(result["fresh_quotes"], 2)
        self.assertEqual(result["stale_quotes"], 1)
        self.assertEqual(result["per_radar"], {"nasdaq7": 2, "china1": 1})

    def test_invalid_quote_is_not_fresh(self):
        result = diagnose({"rows": [{"ticker": "TEST", "quote_time": "bad"}]}, self.now)
        self.assertEqual(result["invalid_quotes"], 1)
        self.assertEqual(result["fresh_quotes"], 0)

    def test_future_quote_is_not_fresh(self):
        result = diagnose({"rows": [{"ticker": "TEST", "quote_time": "2026-10-29T17:00:00+00:00"}]}, self.now)
        self.assertEqual(result["stale_quotes"], 1)

if __name__ == "__main__":
    unittest.main()
