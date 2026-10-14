NASDAQ 7.0 read-only connectivity test

Files to add to GitHub repository somiYu0720/nasdaq7-radar:
1. check_market_feed.py (repository root)
2. .github/workflows/feed-check.yml (preserve nested folders)

Then GitHub > Actions > NASDAQ7 feed connectivity check > Run workflow.
Inspect the job log or nasdaq7-feed-check artifact.

This test DOES NOT run a continuous live monitor, send alerts, verify SEC filings, or scan the full market.
It does not change collector.py, refresh.yml, historical baseline, or existing ledger.
No API key required.
