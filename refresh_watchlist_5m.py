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
    rows=[(ts,float(v)) for ts,v in zip(stamps,q["volume"]) if v is not None and v>=0]
    if len(rows)<15: raise ValueError("insufficient bars")
    ts,vol=rows[-1]
    prior=[v for _,v in rows[-13:-1]]
    baseline=sum(prior)/len(prior)
    if baseline<=0: raise ValueError("zero baseline")
    rvol=round(vol/baseline,2)
    return {"ticker":ticker,"signal":"EARLY_PROVISIONAL" if rvol>=3 else "REVIEW",
            "rvol5":str(rvol),"bar_time":dt.datetime.fromtimestamp(ts,dt.timezone.utc).isoformat(),
            "fetched_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"source":"Yahoo unofficial 5m",
            "baseline":"previous 12 five-minute bars, not time-of-day adjusted"}
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
