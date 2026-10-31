#!/usr/bin/env python3
"""Persist the last valid US regular-session TOP10 on GitHub Pages.
Does not modify the Toss collector or primary ranking feed.
"""
import datetime as dt
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
LIVE=ROOT/"toss_live.json"
WATCH=ROOT/"watchlist.json"
OUT=ROOT/"last_close_top10.json"

def parse(s):
    try:
        d=dt.datetime.fromisoformat(str(s).replace("Z","+00:00"))
        return d.astimezone(dt.timezone.utc) if d.tzinfo else None
    except (ValueError,TypeError): return None

def main():
    if not LIVE.exists() or not WATCH.exists(): return
    data=json.loads(LIVE.read_text(encoding="utf-8"))
    watch=json.loads(WATCH.read_text(encoding="utf-8"))
    stamp=parse(data.get("updated_utc"))
    if not stamp: return
    ny=stamp.astimezone(ZoneInfo("America/New_York"))
    # Regular session only. Do not overwrite the close with pre/after-market rows.
    if ny.weekday()>4 or not (dt.time(9,30)<=ny.time()<dt.time(16,0)): return
    if abs((dt.datetime.now(dt.timezone.utc)-stamp).total_seconds())>900: return
    source=data.get("rows") or (data.get("nasdaq7",[]) + data.get("china1",[]))
    if not isinstance(source,list): return
    prior=json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    result={"source":"toss_live.json","label":"마지막 본장 관측 기록 (실시간 아님)","updated_utc":data["updated_utc"],"categories":{}}
    for cat in ("nas","china"):
        symbols=set(watch.get("categories",{}).get(cat,[]))
        entries=[]
        for x in source:
            if not isinstance(x,dict) or x.get("ticker") not in symbols: continue
            bar=parse(x.get("bar_time") or x.get("candle_time"))
            if not bar or abs((stamp-bar).total_seconds())>900: continue
            try:
                volume=float(x["minute_volume"])
                price=float(x.get("price",x.get("price_usd")))
                if not (math.isfinite(volume) and math.isfinite(price) and volume>=0 and price>0): continue
            except (ValueError,TypeError,KeyError): continue
            # Do not invent acceleration or 100-point score without prior distinct bars.
            entries.append({"ticker":x["ticker"],"price":price,"minute_volume":volume,"bar_time":x.get("bar_time") or x.get("candle_time"),"score":None,"accel":None,"pct":None})
        entries.sort(key=lambda x:(-x["minute_volume"],x["ticker"]))
        if entries: result["categories"][cat]=entries[:10]
        elif prior.get("categories",{}).get(cat): result["categories"][cat]=prior["categories"][cat]
    if not result["categories"]: return
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__": main()
