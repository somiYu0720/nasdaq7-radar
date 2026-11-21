"""Isolated experimental early-signal engine. Never writes production files.
Input: CSV with ticker,timestamp,close,volume; timestamp must be timezone-aware.
Output: independent JSON only. No SEC or predictive-performance claims.
"""
import argparse, csv, json, math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

def ratio(a,b):
    return round(a/b,3) if b is not None and b>0 else None

def evaluate(rows, max_age=10):
    rows=sorted(rows,key=lambda x:x["time"])
    if len(rows)<31:
        return {"signal":"INSUFFICIENT_BARS","bars":len(rows)}
    latest=rows[-1]
    age=(datetime.now(timezone.utc)-latest["time"]).total_seconds()/60
    if age < -2 or age > max_age:
        return {"signal":"STALE","age_min":round(age,1)}
    # Prior 30 bars excluding the newest 5 bars; never use future data.
    base_rows=rows[-35:-5] if len(rows)>=35 else rows[:-5]
    if len(base_rows)<20:
        return {"signal":"INSUFFICIENT_BASELINE"}
    baseline=sum(x["volume"] for x in base_rows)/len(base_rows)
    if baseline<=0: return {"signal":"ZERO_BASELINE"}
    vol=lambda n:sum(x["volume"] for x in rows[-n:])
    r1=ratio(vol(1),baseline)
    r3=ratio(vol(3),3*baseline)
    r5=ratio(vol(5),5*baseline)
    previous3=sum(x["volume"] for x in rows[-6:-3])
    accel=ratio(vol(3),previous3)
    p0=rows[-6]["close"]
    pct=100*(latest["close"]/p0-1) if p0>0 else None
    lows=[x["close"] for x in rows[-10:-5]]
    recent=[x["close"] for x in rows[-5:]]
    higher_low=min(recent)>=min(lows)
    # Only completed, consecutive minute bars qualify for minute acceleration.
    consecutive=all(50 <= (rows[i]["time"]-rows[i-1]["time"]).total_seconds() <= 70
                    for i in range(len(rows)-5,len(rows)))
    score=0
    if r1 is not None: score+=min(30,max(0,(r1-1)*12))
    if r3 is not None: score+=min(25,max(0,(r3-1)*10))
    if accel is not None: score+=min(20,max(0,(accel-1)*10))
    if pct is not None and 0<=pct<=3: score+=15
    if higher_low: score+=10
    score=round(score)
    if not consecutive: signal="REVIEW_GAPPED_BARS"
    elif vol(3)<1000: signal="LOW_LIQUIDITY_REVIEW"
    elif pct is None: signal="REVIEW"
    elif pct>10: signal="ALREADY_UP"
    elif pct < -10: signal="SHARP_DROP"
    elif r3 is not None and r3>=3 and accel is not None and accel>=1.5 and score>=65: signal="IGNITION"
    elif r3 is not None and r3>=2 and score>=45: signal="EARLY"
    elif max(r1 or 0,r3 or 0,r5 or 0)>=1.5: signal="WATCH"
    else: signal="NO_SIGNAL"
    return {"signal":signal,"score_experimental":score,"rvol1":r1,"rvol3":r3,
            "rvol5":r5,"accel3":accel,"change5_pct":round(pct,2) if pct is not None else None,
            "higher_low_proxy":higher_low,"volume3":int(vol(3)),
            "bar_time_utc":latest["time"].isoformat(),"age_min":round(age,1),
            "baseline":"prior 20-30 1m bars excluding newest 5; not time-of-day adjusted",
            "sec_status":"NOT_CHECKED","backtest_verified":False}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True)
    ap.add_argument("--output",default="experiments/early_boost_comparison.json")
    ap.add_argument("--max-age-min",type=float,default=10)
    args=ap.parse_args()
    groups=defaultdict(list)
    with open(args.input,newline="",encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            try:
                t=datetime.fromisoformat(row["timestamp"].replace("Z","+00:00"))
                if t.tzinfo is None: continue
                v=float(row["volume"]); p=float(row["close"])
                if not (math.isfinite(v) and math.isfinite(p) and v>=0 and p>0): continue
                groups[row["ticker"].strip().upper()].append({"time":t.astimezone(timezone.utc),"volume":v,"close":p})
            except (KeyError,TypeError,ValueError): continue
    result={"engine":"EARLY_BOOST_ISOLATED","created_utc":datetime.now(timezone.utc).isoformat(),
            "production_modified":False,"not_in_live_radar":True,
            "note":"Experimental thresholds; requires genuine consecutive 1m bars and backtesting",
            "rows":[{"ticker":ticker,**evaluate(bars,args.max_age_min)} for ticker,bars in sorted(groups.items())]}
    dest=Path(args.output)
    if dest.name in {"data.json","toss_live.json","watchlist.json","discovery_latest.json"}:
        raise SystemExit("Refusing production output filename")
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Wrote independent comparison: {dest} ({len(result['rows'])} tickers)")

if __name__=="__main__":main()
