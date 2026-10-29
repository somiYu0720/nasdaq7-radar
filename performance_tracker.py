#!/usr/bin/env python3
"""Independent, conservative performance tracking from archived Toss snapshots.
No edits to detection scores or SEC risk. No backfilled entry prices.
"""
import json, os
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"performance_results.json"
EVENTS=ROOT/"gpt_monitor_events.json"
LIVE=ROOT/"toss_live.json"
HORIZONS={"15m":900,"1h":3600,"1d":86400,"3d":259200,"5d":432000}
MAX_AGE=300
def dt(s):
    if not s:return None
    try:
        x=datetime.fromisoformat(str(s).replace("Z","+00:00"))
        return x.astimezone(timezone.utc) if x.tzinfo else None
    except (ValueError,TypeError):return None
def load(p,default):
    try:return json.loads(p.read_text(encoding="utf-8"))
    except (OSError,ValueError):return default
def main():
    now=datetime.now(timezone.utc)
    old=load(OUT,{"schema_version":1,"records":{},"snapshots":{}})
    records=old.get("records",{})
    snaps=old.get("snapshots",{})
    events=load(EVENTS,{}).get("events",[])
    live=load(LIVE,{})
    updated=dt(live.get("updated_utc"))
    usable=bool(updated and abs((now-updated).total_seconds())<=MAX_AGE)
    quotes={}
    if usable:
        for radar,key in (("NASDAQ 7.0","nasdaq7"),("중국계 1.0","china")):
            for q in live.get(key,[]):
                ticker=str(q.get("ticker","")).upper()
                price=q.get("price_usd")
                stamp=dt(q.get("quote_time"))
                try:price=float(price)
                except (ValueError,TypeError):continue
                if not ticker or not stamp or price<=0 or abs((now-stamp).total_seconds())>MAX_AGE:continue
                quotes[(radar,ticker)]=(price,stamp)
    for e in events:
        eid=e.get("id")
        if not eid:continue
        radar=e.get("radar","")
        ticker=str(e.get("ticker","")).upper()
        detected=dt(e.get("detected_utc"))
        if not detected:continue
        r=records.setdefault(eid,{"ticker":ticker,"radar":radar,"detected_utc":e["detected_utc"],"entry_price_usd":None,"entry_time_utc":None,"status":"NO_ENTRY_PRICE","outcomes":{}})
        q=quotes.get((radar,ticker))
        if not q:continue
        price,stamp=q
        # Never claim a contemporaneous entry from a later quote.
        # Only qualify fresh detections with <=5m lag.
        if r.get("entry_price_usd") is None:
            lag=(stamp-detected).total_seconds()
            if 0<=lag<=300:
                r["entry_price_usd"]=price
                r["entry_time_utc"]=stamp.isoformat()
                r["status"]="TRACKING"
            else:continue
        anchor=dt(r.get("entry_time_utc"))
        if not anchor or stamp<anchor:continue
        history=snaps.setdefault(eid,[])
        point={"utc":stamp.isoformat(),"price_usd":price}
        if not history or dt(history[-1]["utc"])<stamp:
            history.append(point)
        history[:]=history[-2000:]
        entry=r["entry_price_usd"]
        for name,seconds in HORIZONS.items():
            end=anchor+timedelta(seconds=seconds)
            subset=[x["price_usd"] for x in history if (t:=dt(x["utc"])) and anchor<=t<=end]
            if not subset:continue
            r["outcomes"][name]={
                "sampled_max_pct":round((max(subset)/entry-1)*100,2),
                "sampled_min_pct":round((min(subset)/entry-1)*100,2),
                "sample_count":len(subset),
                "plus_10_observed":max(subset)>=entry*1.1,
                "complete":now>=end,
                "sampling_note":"Observed snapshots only; intraperiod extrema may be missed"
            }
        if now>=anchor+timedelta(days=5):r["status"]="WINDOW_ENDED"
    output={"schema_version":1,"updated_utc":now.isoformat(),"source":"toss_live.json snapshots; noncontinuous","records":records,"snapshots":snaps}
    OUT.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("records",len(records),"tracked",sum(v.get("entry_price_usd") is not None for v in records.values()),"fresh_source",usable)
if __name__=="__main__":main()
