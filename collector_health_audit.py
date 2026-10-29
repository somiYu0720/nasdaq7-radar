"""Read-only collector health audit. No API requests or production file writes."""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def audit(root=ROOT, now=None):
    now = now or datetime.now(timezone.utc)
    checks = {}
    for filename in ("discovery_latest.json", "v64_batch_meta.json", "toss_live.json"):
        path = root / filename
        if not path.exists():
            checks[filename] = {"status": "MISSING"}
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
            if not isinstance(payload, dict):
                raise ValueError("expected object")
            stamp = payload.get("updated_utc") or payload.get("generated_utc") or payload.get("checked_utc")
            age_minutes = None
            if stamp:
                dt = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
                if dt.tzinfo is not None:
                    age_minutes = round((now - dt.astimezone(timezone.utc)).total_seconds()/60, 1)
            status = "TIMESTAMP_UNKNOWN" if age_minutes is None else "FUTURE_TIMESTAMP" if age_minutes < -5 else "STALE_AGE_OVER_60M" if age_minutes > 60 else "RECENT_FILE"
            checks[filename] = {"status": status, "timestamp": stamp, "age_minutes": age_minutes}
            if filename == "discovery_latest.json":
                checks[filename].update({
                    "scanned": payload.get("scanned"),
                    "stale_count": payload.get("stale_count"),
                    "early_count": payload.get("early_count"),
                    "top10_count": len(payload.get("top10") or []),
                })
        except (ValueError, TypeError, OSError) as exc:
            checks[filename] = {"status": "INVALID", "error": str(exc)[:160]}
    return {"audit_utc": now.isoformat(), "checks": checks,
            "note": "File freshness is not market-feed latency. During closed markets, age alone does not prove feed failure."}

if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False, indent=2))
