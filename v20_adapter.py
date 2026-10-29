"""Read-only bridge from SEC metadata and keyword evidence to V20 review queue."""
import json
from pathlib import Path
from v20_sec_review import evaluate

def build(events, evidence):
    metadata = events.get("tickers", {})
    keywords = evidence.get("tickers", {})
    results = []
    for ticker in sorted(set(metadata) | set(keywords)):
        meta = metadata.get(ticker, {})
        raw = keywords.get(ticker, {})
        filings = meta.get("filings", [])
        sources = [
            {"form": f.get("form"), "filing_date": f.get("date"),
             "accession": f.get("accession"), "source_url": f.get("url"),
             "content_verified": False}
            for f in filings if isinstance(f, dict)
        ]
        item = evaluate({
            "ticker": ticker,
            "as_of": meta.get("checked_utc") or events.get("checked_utc"),
            "source_ledger": sources,
            "share_ledger": [],
            "financing_ledger": [],
            "event_ledger": [],
        })
        item["existing_supply_review_candidate"] = raw.get("supply_review_candidate")
        item["keyword_evidence_count"] = len(raw.get("evidence") or [])
        item["filing_metadata_count"] = len(sources)
        item["unresolved"].append("SEC content/exhibit and sale eligibility not legally verified")
        item["confidence"] = "D"
        results.append(item)
    return {
        "schema_version": 1,
        "stage": "V20_SECOND_STAGE_ONLY",
        "source_checked_utc": events.get("checked_utc"),
        "disclaimer": "Metadata/keywords only; no confirmed immediate supply or SEC score",
        "results": results,
    }

def main():
    root = Path(__file__).resolve().parent
    events = json.loads((root / "sec_events.json").read_text(encoding="utf-8"))
    evidence = json.loads((root / "sec_dilution_evidence.json").read_text(encoding="utf-8"))
    output = build(events, evidence)
    (root / "v20_review_queue.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("V20 provisional reviews:", len(output["results"]))

if __name__ == "__main__":
    main()
