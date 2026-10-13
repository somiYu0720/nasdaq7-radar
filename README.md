# NASDAQ 7.0 V6.3 — automated daily-data trial

A GitHub Actions workflow fetches Stooq daily bars for a **fixed 10-ticker trial list**, calculates volume / prior 20-session average and price change, and publishes a static result file to the repository. No API key required. **Not real-time**, not a complete-market scanner, and no SEC analysis or alerts. Data availability and access are not guaranteed.

## Setup
1. Create a GitHub repository and upload `collector.py` and `.github/workflows/refresh.yml` preserving the directory structure.
2. In repository Settings > Actions > General, enable workflow permissions to **Read and write** if allowed by repository policy.
3. In Actions, select **Daily radar refresh** > **Run workflow**.
4. When completed, open `V62_RESULT.html` from the repository or enable GitHub Pages to host it (Settings > Pages > Deploy from a branch > main / root). Your Pages URL will depend on the repository name and account.

Scheduled workflows can be delayed or skipped; the cron time is UTC. Stooq may rate-limit or deny access. The collector pauses between requests. It is not a 5-minute market feed.
