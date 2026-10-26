#!/usr/bin/env python3
"""Refresh minute-bar candidates; never replace previous data if all requests fail."""
import datetime as dt, json, urllib.parse, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
HEADERS={"User-Agent":"Mozilla/5.0"}
def get(ticker):
    url="https://query1.finance.yahoo.com/v8/finance/chart/"+urllib.parse.quote(ticker)+"?interval=5m&range=5d"
    with urllib.request.urlopen(urllib.request.Request(url,headers=HEADERS),timeout=18) as resp:
        chart=json.load(resp)["chart"]["result"][0]
    stamps=chart.get("timestamp") or []
    q=chart["indicators"]["quote"][0]
    now=dt.datetime.now(dt.timezone.utc).timestamp()
    # Only completed 5-minute candles; Yahoo may expose an unfinished 0-volume bar.
    rows=[(ts,float(v)) for ts,v in zip(stamps,q["volume"])
          if v is not None and v>=0 and ts+300<=now-60]
    if len(rows)<15: raise ValueError("insufficient completed bars")
    positive=[(i,ts,v) for i,(ts,v) in enumerate(rows) if v>0]
    if not positive: raise ValueError("no traded bars")
    idx,ts,vol=positive[-1]
    prior=[v for _,v in rows[max(0,idx-12):idx] if v>0]
    if len(prior)<6: raise ValueError("insufficient positive-volume baseline")
    baseline=sum(prior)/len(prior)
    if baseline<=0: raise ValueError("zero baseline")
    rvol=round(vol/baseline,2)
    bar_time=dt.datetime.fromtimestamp(ts,dt.timezone.utc).isoformat()
    age_minutes=round((now-ts-300)/60,1)
    return {"ticker":ticker,"signal":"EARLY_PROVISIONAL" if rvol>=3 and age_minutes<=15 else "REVIEW",
            "rvol5":str(rvol),"bar_time":bar_time,
            "bar_age_minutes":age_minutes,
            "freshness":"FRESH" if age_minutes<=15 else "STALE",
            "fetched_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"source":"Yahoo unofficial 5m",
            "baseline":"previous 12 completed five-minute bars with positive volume; not time-of-day adjusted"}
def main():
    previous=json.loads((ROOT/"data.json").read_text(encoding="utf-8"))
    watchlist=json.loads((ROOT/"priority_watchlist.json").read_text(encoding="utf-8"))
    china=json.loads((ROOT/"china_verified_tickers.json").read_text(encoding="utf-8"))
    symbols=list(dict.fromkeys(str(t).upper() for t in watchlist["tickers"]+china.get("candidates",[])))
    rows=[]; errors={}
    for ticker in symbols:
        try: rows.append(get(ticker))
        except Exception as e: errors[ticker]=str(e)[:150]
    report={"checked_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"checked":len(symbols),
            "success":len(rows),"failed":errors,"mode":"unofficial delayed/incomplete minute data"}
    (ROOT/"minute_feed_status.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    if not rows: raise SystemExit("No successful updates; existing signals preserved")
    data={"updated_utc":report["checked_utc"],"rows":rows,
          "caveat":"Watchlist only, not full market; bars may be delayed; no SEC review"}
    (ROOT/"data.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Updated {len(rows)}/{len(symbols)} watchlist symbols")
if __name__=="__main__": main()
