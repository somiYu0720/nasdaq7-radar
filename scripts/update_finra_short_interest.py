#!/usr/bin/env python3
"""Merge FINRA bi-monthly short-interest positions into daily short-volume snapshot.
Requires FINRA_PUBLIC_API_TOKEN; never treats daily short volume as short interest.
"""
import datetime as dt
import json
import os
import pathlib
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "short_interest.json"
ENDPOINT = "https://api.finra.org/data/group/otcMarket/name/consolidatedShortInterest"

def main():
    token = os.getenv("FINRA_PUBLIC_API_TOKEN", "").strip()
    if not token:
        raise RuntimeError("FINRA_PUBLIC_API_TOKEN GitHub secret is missing; obtain a free FINRA Public API credential")
    if not PATH.exists():
        raise RuntimeError("Run FINRA daily short volume collector first")
    snapshot = json.loads(PATH.read_text(encoding="utf-8"))
    records = snapshot.get("tickers", {})
    if not records:
        raise RuntimeError("No ticker records")
    found = {}
    # Query recent settlement records by ticker. One request per symbol; low cadence only.
    for ticker in sorted(records):
        body = json.dumps({"limit": 12, "compareFilters": [{"compareType": "EQUAL", "fieldName": "symbolCode", "fieldValue": ticker}]}).encode()
        req = urllib.request.Request(ENDPOINT, data=body, headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "NASDAQ7-Radar/1.0"
        }, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=25) as res:
                raw = res.read()
            values = json.loads(raw.decode("utf-8")) if raw else []
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise RuntimeError("FINRA API authorization denied; check Public API credential permissions") from e
            print("Skipping", ticker, "HTTP", e.code)
            continue
        except Exception as e:
            print("Skipping", ticker, type(e).__name__)
            continue
        if not isinstance(values, list):
            continue
        matches = [v for v in values if isinstance(v, dict) and str(v.get("symbolCode", "")).upper() == ticker and v.get("settlementDate")]
        if not matches:
            continue
        latest = max(matches, key=lambda x: x["settlementDate"])
        try:
            shares = int(float(latest["currentShortPositionQuantity"]))
            dtc = float(latest["daysToCoverQuantity"])
            if shares < 0 or dtc < 0 or dtc >= 999:
                continue
        except (KeyError, ValueError, TypeError):
            continue
        found[ticker] = {
            "shares_short": shares,
            "days_to_cover": dtc,
            "short_interest_settlement_date": latest["settlementDate"],
            "short_interest_source": ENDPOINT,
            "short_float_pct": None,
            "short_interest_status": "FINRA_REPORTED"
        }
    if not found:
        raise RuntimeError("FINRA returned no usable short-interest records; prior file unchanged")
    for ticker, values in found.items():
        records[ticker].update(values)
    snapshot["short_interest_updated_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    snapshot["short_interest_note"] = "Semi-monthly FINRA reported short positions and DTC. Short float requires separately verified public float; no squeeze probability implied."
    PATH.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Merged FINRA short-interest positions for", len(found), "tickers")

if __name__ == "__main__":
    main()
