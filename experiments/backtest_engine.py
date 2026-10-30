"""Isolated research prototype. Does not modify production rankings or collectors.
Input CSV: ticker, timestamp (ISO8601 UTC), close, volume (1-minute bars).
Run: python experiments/backtest_engine.py history.csv
No lookahead: signals use only current/prior bars; outcomes use future bars.
"""
import csv, json, math, sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

HORIZONS = (30, 390, 1170, 1950)  # trading-minute proxies; requires continuous bars
def read(path):
    by = defaultdict(list)
    with open(path, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            try:
                t=datetime.fromisoformat(r["timestamp"].replace("Z","+00:00"))
                if t.tzinfo is None: continue
                p=float(r["close"]); v=float(r["volume"])
                if p>0 and v>=0 and math.isfinite(p) and math.isfinite(v):
                    by[r["ticker"].upper()].append((t.astimezone(timezone.utc),p,v))
            except (KeyError,ValueError,OverflowError): continue
    return {k:sorted(set(v)) for k,v in by.items()}
def run(data):
    signals=[]
    for ticker,bars in data.items():
        for i in range(15,len(bars)):
            window=bars[i-15:i+1]
            if any((window[j][0]-window[j-1][0])!=timedelta(minutes=1) for j in range(1,16)):continue
            baseline=sum(x[2] for x in window[:10])/10
            recent=sum(x[2] for x in window[-3:])/3
            if baseline<1000 or recent<3000:continue
            ratio=recent/baseline
            change=100*(bars[i][1]/bars[i-5][1]-1)
            if ratio<3 or change>10:continue
            outcome={}
            for h in HORIZONS:
                j=i+h
                if j>=len(bars) or bars[j][0]-bars[i][0]!=timedelta(minutes=h):continue
                outcome[str(h)]=round(100*(bars[j][1]/bars[i][1]-1),3)
            signals.append(dict(ticker=ticker,timestamp=bars[i][0].isoformat(),volume_ratio=round(ratio,2),price_change_5m=round(change,2),outcomes=outcome))
    # Avoid fabricated win rates: no score until independent, sufficient samples exist.
    result={"status":"RESEARCH_ONLY","signals":signals,"summary":{}}
    for h in HORIZONS:
        vals=[s["outcomes"][str(h)] for s in signals if str(h) in s["outcomes"]]
        result["summary"][str(h)]={"sample_count":len(vals),"win_rate":round(sum(x>0 for x in vals)/len(vals),4) if len(vals)>=30 else None,"mean_return_pct":round(sum(vals)/len(vals),3) if len(vals)>=30 else None,"status":"VALIDATION_REQUIRED" if len(vals)>=30 else "INSUFFICIENT_SAMPLE"}
    return result
if __name__=="__main__":
    if len(sys.argv)!=2:raise SystemExit("Usage: python experiments/backtest_engine.py history.csv")
    print(json.dumps(run(read(sys.argv[1])),ensure_ascii=False,indent=2))
