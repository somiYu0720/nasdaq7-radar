"""Read-only Toss freshness and dashboard compatibility diagnostic.

Usage: python toss_freshness_check.py
No credentials, network calls, or production file modifications.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except ValueError:
        return None

def diagnose(data, now=None):
    now = now or datetime.now(timezone.utc)
    rows = data.get("rows") if isinstance(data.get("rows"), list) else None
    if rows is None:
        rows = list(data.get("nasdaq7") or []) + list(data.get("china1") or [])
    updated = timestamp(data.get("updated_utc"))
    summary = {"file_updated_utc": data.get("updated_utc"), "file_age_minutes": None,
               "row_count": len(rows), "fresh_quotes": 0, "stale_quotes": 0,
               "invalid_quotes": 0, "per_radar": {"nasdaq7": 0, "china1": 0},
               "notes": ["A recent file does not prove each quote is current.",
                         "Market closures can make old quotes expected, not a collector failure."]}
    if updated:
        summary["file_age_minutes"] = round((now-updated).total_seconds()/60, 2)
    for radar in ("nasdaq7", "china1"):
        if isinstance(data.get(radar), list):
            summary["per_radar"][radar] = len(data[radar])
    for row in rows:
        if not isinstance(row, dict):
            summary["invalid_quotes"] += 1
            continue
        bar = timestamp(row.get("candle_time") or row.get("bar_time") or row.get("quote_time"))
        if not bar:
            summary["invalid_quotes"] += 1
            continue
        age = (now-bar).total_seconds()/60
        if -2 <= age <= 10:
            summary["fresh_quotes"] += 1
        else:
            summary["stale_quotes"] += 1
    return summary

if __name__ == "__main__":
    path = ROOT / "toss_live.json"
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    print(json.dumps(diagnose(payload), ensure_ascii=False, indent=2))
