#!/usr/bin/env python3
"""Independent market-wide NASDAQ7 x V20 preliminary screen.
No writes to existing dashboard/radar/TOP10. No unverified SEC claims.
"""
import csv, io, json, os, re, time, urllib.request, datetime as dt
from pathlib import Path
import pandas as pd
import yfinance as yf

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/"v20_discovery"
OUT.mkdir(exist_ok=True)
UA={"User-Agent":"Mozilla/5.0 (NASDAQ7 V20 research screener)"}
def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=35) as r:
        return r.read().decode("utf-8-sig")
def universe():
    raw=fetch("https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt")
    rows=list(csv.DictReader(io.StringIO("\n".join(x for x in raw.splitlines() if not x.startswith("File Creation Time"))),delimiter="|"))
    out=[]
    for r in rows:
        t=(r.get("Symbol") or "").strip().upper()
        name=r.get("Security Name") or ""
        if not re.fullmatch("[A-Z]{1,5}",t) or r.get("ETF")!="N" or r.get("Test Issue")!="N": continue
        if re.search(r"warrants?|rights?|units?|preferred|depositary|notes due|debentures?|acquisition corp|blank check",name,re.I): continue
        out.append({"ticker":t,"name":name})
    return out
def num(x):
    try:
        v=float(x)
        return v if pd.notna(v) else None
    except (TypeError,ValueError): return None
def main():
    symbols=universe()
    batchsize=60
    results=[]; failures=[]
    for start in range(0,len(symbols),batchsize):
        batch=symbols[start:start+batchsize]
        tickers=[x["ticker"] for x in batch]
        try:
            data=yf.download(tickers,period="1mo",interval="1d",group_by="ticker",auto_adjust=False,threads=True,progress=False,timeout=35)
            for item in batch:
                t=item["ticker"]
                try:
                    frame=data[t] if isinstance(data.columns,pd.MultiIndex) else data
                    frame=frame.dropna(subset=["Close"])
                    if len(frame)<6: raise ValueError("insufficient_daily_history")
                    last=frame.iloc[-1]; prev=frame.iloc[-2]
                    price=num(last["Close"]); volume=num(last["Volume"])
                    base=num(frame["Volume"].iloc[-21:-1].median()) if len(frame)>1 else None
                    rvol=round(volume/base,2) if volume is not None and base and base>0 else None
                    change=round((price/float(prev["Close"])-1)*100,2) if price and float(prev["Close"])>0 else None
                    if price is None or volume is None: raise ValueError("missing_price_or_volume")
                    results.append({"ticker":t,"name":item["name"],"price_usd":round(price,4),"daily_volume":int(volume),"rvol_daily":rvol,"change_pct":change,"early_signal":bool(rvol and rvol>=2 and change is not None and -12<=change<=10),"quote_date":str(frame.index[-1].date()),"float_shares":None,"outstanding_shares":None,"cash_runway_months":None,"atm_status":"UNVERIFIED","warrants_status":"UNVERIFIED","dilution_pct":None,"future_catalyst":"UNVERIFIED","v20_status":"PENDING_SEC_REVIEW"})
                except Exception as e: failures.append({"ticker":t,"error":str(e)[:100]})
        except Exception as e:
            failures.extend({"ticker":t,"error":"batch_error:"+str(e)[:100]} for t in tickers)
        print(f"PROGRESS {min(start+batchsize,len(symbols))}/{len(symbols)} rows={len(results)} failures={len(failures)}",flush=True)
    early=[r for r in results if r["early_signal"]]
    early.sort(key=lambda x:(-(x["rvol_daily"] or 0),abs(x["change_pct"] or 0)))
    summary={"updated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"universe_count":len(symbols),"quotes_scanned":len(results),"quote_failures":len(failures),"early_signal_count":len(early),"sec_verified_count":0,"strict_v20_pass_count":0,"top10_preliminary_unverified":early[:10],"strict_v20_top10":[],"disclaimer":"Daily OHLCV preliminary signals only; not 1-minute acceleration. Float, O/S, SEC supply, runway and future events NOT verified. No confirmed V20 passes."}
    (OUT/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    with (OUT/"all_quotes.csv").open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=list(results[0]) if results else ["ticker"]);w.writeheader();w.writerows(results)
    (OUT/"failures.json").write_text(json.dumps(failures,ensure_ascii=False,indent=2))
    print("SUMMARY",json.dumps({k:v for k,v in summary.items() if not isinstance(v,list)},ensure_ascii=False),flush=True)
if __name__=="__main__": main()
