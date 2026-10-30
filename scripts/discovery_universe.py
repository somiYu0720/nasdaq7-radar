"""Independent NASDAQ 7.0 discovery universe builder.
Does not change watchlist.json, toss_live.json, or existing radars.
Nasdaq Trader directory is a symbol directory, NOT a real-time market scanner.
"""
import csv
import io
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIRECTORY = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
WATCHLIST = "https://raw.githubusercontent.com/somiYu0720/nasdaq7-radar/main/watchlist.json"
OUTPUT = ROOT / "NASDAQ7_DISCOVERY_UNIVERSE.csv"

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25) as response:
        return response.read().decode("utf-8-sig")

def main():
    watch = json.loads((ROOT / "watchlist.json").read_text(encoding="utf-8-sig"))
    existing = {s.upper() for names in watch["categories"].values() for s in names}
    # Include existing watchlist symbols: fresh volume signals must not be excluded.
    # Keep the independent China 1.0 lane separate from NASDAQ 7.0 discovery.
    china = {s.upper() for s in watch["categories"].get("china", [])}
    lines = [line for line in fetch(DIRECTORY).splitlines() if not line.startswith("File Creation Time")]
    reader = csv.DictReader(io.StringIO("\n".join(lines)), delimiter="|")
    candidates = []
    for item in reader:
        ticker = (item.get("Symbol") or "").strip().upper()
        if not ticker or ticker in china or not ticker.isascii() or not ticker.isalnum():
            continue
        if item.get("Test Issue", "").strip().upper() != "N":
            continue
        if item.get("ETF", "").strip().upper() == "Y":
            continue
        name = (item.get("Security Name") or "").strip()
        # Exclude non-common-share instruments; not a market-cap or float check.
        if re.search(r"\\b(warrants?|rights?|units?|preferred|depositary shares|notes? due|bonds?|debentures?)\\b", name, re.I):
            continue
        if re.search(r"\\b(acquisition corp|acquisition company|blank check)\\b", name, re.I):
            continue
        candidates.append({"ticker": ticker, "name": name})
    if not candidates:
        raise SystemExit("No candidate symbols. No file changed.")
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["ticker", "name"])
        writer.writeheader()
        writer.writerows(candidates)
    print("DISCOVERY_UNIVERSE_OK", len(candidates))
    print("EXCLUDED_CHINA_TICKERS", len(china))
    print("EXISTING_WATCHLIST_INCLUDED", sum(x["ticker"] in existing for x in candidates))
    print("Saved:", OUTPUT.name)
    print("Note: these are listing candidates, not validated early signals.")
    print("To scan a limited batch with the existing V3.1 scanner:")
    print("python NASDAQ7_EARLY_V31.py --universe NASDAQ7_DISCOVERY_UNIVERSE.csv --limit 50")

if __name__ == "__main__":
    main()
