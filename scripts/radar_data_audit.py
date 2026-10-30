"""Read-only audit of live radar input. Does not modify collectors or scores."""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
now=datetime.now(timezone.utc)
def read(name):
    try: return json.loads((ROOT/name).read_text(encoding="utf-8"))
    except (OSError,ValueError): return {}
def stamp(s):
    try:
        d=datetime.fromisoformat(str(s).replace("Z","+00:00"))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except (TypeError,ValueError): return None

live=read("toss_live.json")
watch=read("priority_watchlist.json")
disc=read("discovery_latest.json")
items=[(lane,x) for lane in ("nasdaq7","china1") for x in live.get(lane,[]) if isinstance(x,dict)]
by={}
for lane,x in items:
    by.setdefault(str(x.get("ticker","")).upper(),[]).append((lane,x))
targets=["AIOT","CRIS","NCPL","SHFS","XNCR","XXII","LUCD","CETX","LABT","RCT","CPRI"]
report={"checked_utc":now.isoformat(),"toss_updated_utc":live.get("updated_utc"),
        "discovery_updated_utc":disc.get("updated_utc"),"discovery_scanned":disc.get("scanned"),
        "targets":{}}
for t in targets:
    entries=[]
    for lane,x in by.get(t,[]):
        qt=stamp(x.get("quote_time"));ct=stamp(x.get("collected_utc"))
        entries.append({"lane":lane,"quote_time":x.get("quote_time"),"collected_utc":x.get("collected_utc"),
                        "quote_age_min":round((now-qt).total_seconds()/60,1) if qt else None,
                        "collection_age_min":round((now-ct).total_seconds()/60,1) if ct else None,
                        "minute_volume":x.get("minute_volume"),"price_usd":x.get("price_usd")})
    report["targets"][t]={"in_priority_watchlist":t in watch.get("tickers",[]),
                           "present_in_toss":bool(entries),"entries":entries,
                           "discovery_diagnostic":disc.get("diagnostics",{}).get(t)}
print(json.dumps(report,ensure_ascii=False,indent=2))
