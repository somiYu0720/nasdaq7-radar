#!/usr/bin/env python3
"""Phone-IP Toss historical ranking; read-only, writes a local JSON report."""
import datetime as dt
import getpass, json, math, time
import urllib.parse as parse
import urllib.request as req
import urllib.error as err
from pathlib import Path

BASE="https://openapi.tossinvest.com"
WATCH_URL="https://raw.githubusercontent.com/somiYu0720/nasdaq7-radar/main/watchlist.json"
TARGET="2026-10-31T08:59"
BEFORE="2026-10-30T23:59:00Z"
OUT=Path("toss_top10_20261031_0859.json")
def request(url, token=None, payload=None):
    headers={"User-Agent":"nasdaq7-phone-history/1.0"}
    if token: headers["Authorization"]="Bearer "+token
    if payload is not None: headers["Content-Type"]="application/x-www-form-urlencoded"
    with req.urlopen(req.Request(url,data=payload,headers=headers),timeout=30) as res:
        return json.load(res)
def number(x):
    try:
        v=float(x)
        return v if math.isfinite(v) else None
    except (ValueError,TypeError): return None
def score(now,prev):
    v=number(now.get("volume")); oldv=number(prev.get("volume"))
    p=number(now.get("closePrice")); oldp=number(prev.get("closePrice"))
    if None in (v,oldv,p,oldp) or min(p,oldp)<=0 or min(v,oldv)<0: return None
    accel=v/oldv if oldv>0 else None
    pct=100*(p/oldp-1)
    base=min(45,round(12*math.log10(1+v)))
    speed=0 if accel is None or v<1000 or oldv<1000 else min(35,max(0,round(15*math.log2(max(1,accel)))))
    movement=20 if 0<=pct<=5 else 10 if 5<pct<=12 else 8 if pct>=-3 else 0
    return {"score":base+speed+movement,"price_usd":p,"minute_volume":v,"accel":accel,"pct":pct,"bar_time":now["timestamp"]}
def main():
    watch=request(WATCH_URL)["categories"]
    cid=input("TOSS CLIENT ID: ").strip()
    secret=getpass.getpass("TOSS CLIENT SECRET (hidden): ").strip()
    payload=parse.urlencode({"grant_type":"client_credentials","client_id":cid,"client_secret":secret}).encode()
    token=request(BASE+"/oauth2/token",payload=payload)["access_token"]
    print("AUTH_OK",flush=True)
    symbols=sorted(set(watch["nas"])|set(watch["china"]))
    result={"target_kst":TARGET,"source":"Toss historical 1m candles","categories":{"nas":[],"china":[]},"missing":[],"missing_detail":[],"raw_candles":{},"errors":[],"scanned":len(symbols)}
    result["coverage"]={"exact_pair":0,"target_missing":0,"previous_missing":0,"http_error":0}
    for i,symbol in enumerate(symbols,1):
        try:
            query=parse.urlencode({"symbol":symbol,"interval":"1m","count":100,"before":BEFORE})
            response=request(BASE+"/api/v1/candles?"+query,token=token)
            rows=response.get("result",{}).get("candles",[])
            result["raw_candles"][symbol]=[{"timestamp":x.get("timestamp"),"closePrice":x.get("closePrice"),"volume":x.get("volume")} for x in rows if isinstance(x,dict) and str(x.get("timestamp",""))[:10]=="2026-10-31" and str(x.get("timestamp",""))[:16]<="2026-10-31T08:59"][:100]
            bytime={str(x.get("timestamp",""))[:16]:x for x in rows if isinstance(x,dict)}
            now=bytime.get(TARGET); prev=bytime.get("2026-10-31T08:58")
            if now is None or prev is None:
                result["missing"].append(symbol)
                result["coverage"]["target_missing" if now is None else "previous_missing"]+=1
                result["missing_detail"].append({"ticker":symbol,"reason":"target_bar_missing" if now is None else "previous_bar_missing","available_bars":len(rows),"first_time":rows[0].get("timestamp") if rows else None,"last_time":rows[-1].get("timestamp") if rows else None})
            else:
                row=score(now,prev)
                if row:
                    result["coverage"]["exact_pair"]+=1
                    row["ticker"]=symbol
                    for cat in ("nas","china"):
                        if symbol in watch[cat]: result["categories"][cat].append(row.copy())
                else:
                    result["missing"].append(symbol)
                    result["missing_detail"].append({"ticker":symbol,"reason":"invalid_numeric_values"})
        except err.HTTPError as e:
            result["coverage"]["http_error"]+=1
            result["errors"].append({"ticker":symbol,"http":e.code})
        except Exception as e: result["errors"].append({"ticker":symbol,"error":type(e).__name__})
        if i%10==0 or i==len(symbols): print("PROGRESS",i,"/",len(symbols),flush=True)
        time.sleep(0.15)
    for cat in ("nas","china"):
        result["categories"][cat].sort(key=lambda x:(-x["score"],-x["minute_volume"],x["ticker"]))
        result["categories"][cat]=result["categories"][cat][:10]
        print("\n",cat.upper(),"TOP10")
        for rank,x in enumerate(result["categories"][cat],1):
            print(rank,x["ticker"],"SCORE",x["score"],"USD",x["price_usd"],"VOL",int(x["minute_volume"]))
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print("\nSAVED",OUT,"MISSING",len(result["missing"]),"ERRORS",len(result["errors"]))
    from collections import Counter
    print("MISSING_REASONS",dict(Counter(x["reason"] for x in result["missing_detail"])))
    print("COVERAGE",result["coverage"])
    print("NOTE: exact-minute TOP10 only; missing bars are not zero-volume bars")
    print("HTTP_ERRORS",result["errors"][:20])
    print("RAW_CANDLE_SYMBOLS",len(result["raw_candles"]))
    print("Local report only. Live dashboard not modified.")
if __name__=="__main__":
    try: main()
    except err.HTTPError as e: print("HTTP_ERROR",e.code)
    except Exception as e: print("ERROR",type(e).__name__,str(e)[:200])
