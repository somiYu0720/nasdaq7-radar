#!/usr/bin/env python3
"""Non-destructive signal bridge: separate discovery from risk review."""
import csv, datetime as dt, json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def read_json(name, default):
    p=ROOT/name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default
def main():
    live=read_json("data.json",{})
    daily=read_json("v62_results.json",[])
    if isinstance(daily,dict): daily=daily.get("rows",daily.get("results",[]))
    if not isinstance(daily,list): daily=[]
    entries={}
    for row in daily:
        t=str(row.get("ticker","")).upper().strip()
        if t:
            entries[t]={"ticker":t,"daily":row,"intraday":None}
    for row in live.get("rows",[]):
        t=str(row.get("ticker","")).upper().strip()
        if t:
            entries.setdefault(t,{"ticker":t,"daily":None,"intraday":None})["intraday"]=row
    china=read_json("china_verified_tickers.json",{})
    verified={str(t).upper() for t in china.get("tickers",[])} if isinstance(china,dict) else set()
    out={"generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
         "source_updated_utc":live.get("updated_utc"),
         "data_mode":"mixed daily and cached intraday; not real-time",
         "nasdaq7":[],"china1":[],"china_unverified":[]}
    for t,v in sorted(entries.items()):
        intra=v["intraday"] or {}
        day=v["daily"] or {}
        signal=intra.get("signal") or day.get("status") or "REVIEW"
        item={"ticker":t,"signal":signal,"rvol5":intra.get("rvol5"),
              "bar_time":intra.get("bar_time"),"daily_date":day.get("date"),
              "daily_rvol":day.get("rvol"),"change_pct":day.get("change"),
              "source":"intraday" if intra else "daily",
              "risk_review":"NOT_CHECKED","sec_review":"NOT_CHECKED",
              "stage":"1_PROVISIONAL","price_currency":"USD"}
        out["nasdaq7"].append(item)
        if t in verified:
            out["china1"].append(dict(item,china_verified=True))
        else:
            out["china_unverified"].append(t)
    (ROOT/"radar_bridge.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"NASDAQ7 {len(out['nasdaq7'])}; verified China1 {len(out['china1'])}; unverified {len(out['china_unverified'])}")
if __name__=="__main__": main()
