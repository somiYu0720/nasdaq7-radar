#!/usr/bin/env python3
"""Fetch FINRA daily consolidated off-exchange short-sale volume (NOT short interest)."""
import csv
import io
import json
import pathlib
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "short_interest.json"
WATCH = ROOT / "watchlist.json"
BASE = "https://cdn.finra.org/equity/regsho/daily/CNMSshvol{date}.txt"
HEADERS = {"User-Agent": "nasdaq7-radar-public-data/1.0", "Accept": "text/plain"}

def main():
    watch = json.loads(WATCH.read_text(encoding="utf-8")).get("categories", {})
    tickers = {str(t).upper() for values in watch.values() if isinstance(values, list) for t in values}
    now = datetime.now(ZoneInfo("America/New_York"))
    errors = []
    for offset in range(0, 8):
        day = (now - timedelta(days=offset)).date()
        if day.weekday() >= 5:
            continue
        url = BASE.format(date=day.strftime("%Y%m%d"))
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as response:
                raw = response.read().decode("utf-8-sig", errors="replace")
            rows = csv.reader(io.StringIO(raw), delimiter="|")
            header = next(rows, [])
            if not header or header[0].strip().lower() != "date":
                raise ValueError("Unexpected FINRA header")
            result = {}
            for row in rows:
                if len(row) < 5:
                    continue
                symbol = row[1].strip().upper()
                if symbol not in tickers:
                    continue
                try:
                    short_vol = float(row[2])
                    total_vol = float(row[4])
                except ValueError:
                    continue
                if total_vol <= 0:
                    continue
                result[symbol] = {
                    "short_volume_pct": round(short_vol / total_vol * 100, 2),
                    "short_volume": int(short_vol),
                    "reported_volume": int(total_vol),
                    "short_volume_date": day.isoformat(),
                    "short_volume_source": url,
                    "short_float_pct": None,
                    "days_to_cover": None,
                    "short_interest_status": "NOT_AVAILABLE_FROM_DAILY_VOLUME"
                }
            if not result:
                raise ValueError("No watchlist symbols in published file")
            payload = {
                "source": "FINRA Reg SHO consolidated NMS daily short sale volume",
                "source_url": url,
                "as_of": day.isoformat(),
                "updated_utc": datetime.now(timezone.utc).isoformat(),
                "note": "Short volume is NOT short interest, short float, or evidence of a squeeze. Includes only FINRA-reporting facilities.",
                "tickers": result
            }
            OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Saved {len(result)} symbols for {day}")
            return
        except Exception as exc:
            errors.append(f"{day}: {type(exc).__name__}: {exc}")
    raise RuntimeError("No valid FINRA daily file; preserving prior data. " + " | ".join(errors))

if __name__ == "__main__":
    main()
