"""NASDAQ7 mobile collector v2: 117-symbol coverage and failure diagnostics.
Run in Pydroid. Reads existing ~/.nasdaq7/credentials.json; no secrets printed.
Never fabricates missing bars. Does not change watchlist or dashboard code.
"""
import base64, json, os, time, random
import urllib.request, urllib.parse, urllib.error
from pathlib import Path
from datetime import datetime, timezone

REPO="somiYu0720/nasdaq7-radar"
ROOT="https://api.github.com/repos/"+REPO+"/contents/"
TOSS="https://openapi.tossinvest.com"
CONFIG=Path.home()/".nasdaq7"/"credentials.json"
INTERVAL=60
def utc(): return datetime.now(timezone.utc).isoformat()
def request(url,token=None,body=None,method=None,form=False):
    headers={"Accept":"application/json","User-Agent":"nasdaq7-mobile-v2"}
    if token: headers["Authorization"]="Bearer "+token
    if body is not None: headers["Content-Type"]="application/x-www-form-urlencoded" if form else "application/json"
    req=urllib.request.Request(url,data=body,headers=headers,method=method)
    with urllib.request.urlopen(req,timeout=20) as res: return json.load(res)
def github(name,token):
    x=request(ROOT+name,token)
    return json.loads(base64.b64decode(x["content"])),x["sha"]
def upload(name,obj,token):
    for i in range(3):
        _,sha=github(name,token)
        data={"message":"Toss mobile verified minute snapshot v2","sha":sha,"content":base64.b64encode(json.dumps(obj,ensure_ascii=False).encode()).decode()}
        try: return request(ROOT+name,token,json.dumps(data).encode(),"PUT")
        except urllib.error.HTTPError as e:
            if e.code not in (409,422) or i==2: raise
            time.sleep(2)
def credential(c,*keys):
    for k,v in c.items():
        if k.lower() in [x.lower() for x in keys] and isinstance(v,str) and v.strip(): return v.strip()
    raise RuntimeError("Missing saved credential: "+keys[0])
def authorize(c):
    body=urllib.parse.urlencode({"grant_type":"client_credentials","client_id":credential(c,"toss_client_id","client_id"),"client_secret":credential(c,"toss_client_secret","client_secret")}).encode()
    return request(TOSS+"/oauth2/token",body=body,method="POST",form=True)["access_token"]
def market(path,token,params):
    return request(TOSS+path+"?"+urllib.parse.urlencode(params),token).get("result")
def dt(s):
    try:
        x=datetime.fromisoformat(str(s).replace("Z","+00:00"))
        return x.astimezone(timezone.utc) if x.tzinfo else None
    except: return None
def candles_of(result):
    if isinstance(result,list): return result
    if isinstance(result,dict):
        for key in ("candles","items","bars","data"):
            if isinstance(result.get(key),list): return result[key]
    return []
def run_once(gh,token):
    watch,_=github("watchlist.json",gh)
    cat=watch.get("categories",{})
    nas=list(dict.fromkeys(str(x).upper() for x in cat.get("nas",[])))
    china=list(dict.fromkeys(str(x).upper() for x in cat.get("china",[])))
    symbols=list(dict.fromkeys(nas+china))
    if not symbols: raise RuntimeError("Empty watchlist; upload cancelled")
    out={"nasdaq7":[],"china1":[]}
    failures={}
    for i,symbol in enumerate(symbols,1):
        error=None
        for attempt in range(3):
            try:
                result=market("/api/v1/candles",token,{"symbol":symbol,"interval":"1m","count":15})
                bars=candles_of(result)
                if not bars: error="NO_CANDLES";break
                parsed=[(dt(b.get("timestamp")),b) for b in bars if isinstance(b,dict)]
                parsed=[(t,b) for t,b in parsed if t is not None]
                if not parsed: error="INVALID_TIME";break
                stamp,b=max(parsed,key=lambda x:x[0])
                age=(datetime.now(timezone.utc)-stamp).total_seconds()
                if age < -120 or age > 300: error="STALE_OR_MARKET_CLOSED";break
                volume=b.get("volume")
                price=b.get("closePrice")
                if volume is None or price is None: error="MISSING_FIELDS";break
                price=float(price);volume=float(volume)
                if price<=0 or volume<0: error="INVALID_VALUES";break
                row={"ticker":symbol,"price_usd":price,"minute_volume":volume,"quote_time":b["timestamp"],"bar_time":b["timestamp"],"collected_utc":utc(),"low":b.get("lowPrice"),"high":b.get("highPrice"),"close":b.get("closePrice"),"source":"Toss 1m candle"}
                if symbol in nas: out["nasdaq7"].append(dict(row))
                if symbol in china: out["china1"].append(dict(row))
                error=None;break
            except urllib.error.HTTPError as e:
                error="HTTP_"+str(e.code)
                if e.code not in (429,500,502,503,504): break
                time.sleep(min(8,2**attempt))
            except Exception as e:
                error=type(e).__name__
                if attempt<2: time.sleep(1+attempt)
        if error: failures[symbol]=error
        if i%20==0: print("CHECKED",i,"/",len(symbols),"FAILED",len(failures),flush=True)
        time.sleep(0.1)
    from collections import Counter
    print("COVERAGE",len(symbols)-len(failures),"/",len(symbols),"NASDAQ",len(out["nasdaq7"]),"/",len(nas),"CHINA",len(out["china1"]),"/",len(china),flush=True)
    print("FAILURE_REASONS",dict(Counter(failures.values())),flush=True)
    report={"updated_utc":utc(),"watchlist_unique":len(symbols),"nasdaq_watchlist":len(nas),"china_watchlist":len(china),"success_unique":len(symbols)-len(failures),"failure_reasons":dict(Counter(failures.values())),"failures":failures,"note":"Stale/no-trade candles are not current market data"}
    if out["nasdaq7"] or out["china1"]:
        payload={"source":"Toss verified 1m","status":"partial" if failures else "ok","volume_verified":True,"updated_utc":utc(),"interval_seconds":INTERVAL,"unique_symbols":len(symbols)-len(failures),**out}
        upload("toss_live.json",payload,gh)
        print("UPLOAD_OK",flush=True)
    else: print("NO_VALID_BARS: existing live file preserved",flush=True)
    # Diagnostics are separate; never overwrite radar or watchlist.
    try:
        upload("toss_collection_status.json",report,gh)
        print("STATUS_UPDATED",flush=True)
    except urllib.error.HTTPError as e:
        if e.code==404:
            print("STATUS_FILE_NOT_CREATED: existing radar unaffected",flush=True)
        else: print("STATUS_UPLOAD_HTTP",e.code,flush=True)
    return report
def main():
    if not CONFIG.exists(): raise RuntimeError("First run existing nasdaq7_auto.py to save credentials")
    c=json.loads(CONFIG.read_text(encoding="utf-8"))
    gh=credential(c,"github_token","gh_token","github","github_pat")
    token=authorize(c);refreshed=time.monotonic()
    print("GITHUB + TOSS READY | 117 symbol diagnostics",flush=True)
    while True:
        started=time.monotonic()
        try:
            if started-refreshed>3000:
                token=authorize(c);refreshed=time.monotonic()
            run_once(gh,token)
        except KeyboardInterrupt: break
        except urllib.error.HTTPError as e:
            print("CYCLE_HTTP",e.code,flush=True)
            if e.code==401:
                try: token=authorize(c);refreshed=time.monotonic()
                except Exception as ex: print("AUTH_ERROR",type(ex).__name__,flush=True)
        except Exception as e: print("CYCLE_ERROR",type(e).__name__,str(e)[:120],flush=True)
        try: time.sleep(max(1,INTERVAL-(time.monotonic()-started)))
        except KeyboardInterrupt: break
if __name__=="__main__": main()
