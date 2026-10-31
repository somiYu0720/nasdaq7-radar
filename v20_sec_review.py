"""V20 isolated SEC evidence gate. Does NOT change first-stage rankings.
Input: a JSON evidence object; output: review-only decision.
No automatic legal conclusion from keyword matches.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any

BUCKETS = (
    "already_outstanding", "issuable_now", "issuable_conditional",
    "reserved_only", "resale_already_outstanding", "shelf_dollars",
    "sold_expired_cancelled",
)
REQUIRED = ("ticker", "as_of", "source_ledger", "share_ledger", "financing_ledger", "event_ledger")

def evaluate(evidence: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(evidence, dict):
        raise TypeError("Evidence must be a JSON object")
    missing = [k for k in REQUIRED if k not in evidence]
    ticker = str(evidence.get("ticker") or "").strip().upper()
    unresolved = []
    if not ticker:
        unresolved.append("Identity: ticker missing")
    if missing:
        unresolved.append("Missing required fields: " + ", ".join(missing))
    as_of = evidence.get("as_of")
    try:
        datetime.fromisoformat(str(as_of).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        unresolved.append("Freshness: valid as_of ISO timestamp missing")
    sources = evidence.get("source_ledger") or []
    if not isinstance(sources, list) or not sources:
        unresolved.append("Evidence: no primary filing/exhibit source entries")
    else:
        for i, item in enumerate(sources):
            if not isinstance(item, dict) or not all(item.get(k) for k in ("form", "filing_date", "accession", "source_url")):
                unresolved.append(f"Evidence: source_ledger[{i}] missing pinpoint")
    shares = evidence.get("share_ledger") or []
    if not isinstance(shares, list):
        unresolved.append("Share ledger must be a list")
        shares = []
    seen = set()
    for i, row in enumerate(shares):
        if not isinstance(row, dict):
            unresolved.append(f"Share ledger row {i}: invalid")
            continue
        bucket, instrument = row.get("bucket"), row.get("instrument_id")
        if bucket not in BUCKETS or not instrument:
            unresolved.append(f"Share ledger row {i}: invalid bucket/instrument_id")
        if instrument in seen:
            unresolved.append(f"Share ledger row {i}: repeated instrument_id; manual double-count review")
        seen.add(instrument)
        if row.get("quantity") is not None and (not isinstance(row["quantity"], (int, float)) or isinstance(row["quantity"], bool) or row["quantity"] < 0):
            unresolved.append(f"Share ledger row {i}: invalid quantity")
    return {
        "ticker": ticker,
        "as_of": as_of,
        "stage": "SEC_SECOND_STAGE_REVIEW",
        "first_stage_score_unchanged": True,
        "classification": "REVIEW_REQUIRED",
        "confidence": "D" if unresolved else "UNASSESSED_MANUAL_REVIEW",
        "unresolved": unresolved,
        "share_buckets": {b: sum(1 for x in shares if isinstance(x, dict) and x.get("bucket") == b) for b in BUCKETS},
        "immediate_supply_shares": None,
        "conditional_supply_shares": None,
        "sec_score": None,
        "note": "No automatic A/B/C/D supply confirmation or share summation. SEC/exhibit legal review required.",
    }
