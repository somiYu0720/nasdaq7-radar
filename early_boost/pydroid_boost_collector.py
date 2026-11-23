"""Standalone Pydroid3 enhanced radar collector. Does not alter production files."""
import sys, json, time, csv, tempfile, urllib.error
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import nasdaq7_auto_v2 as api
sys.path.insert(0,str(Path(__file__).resolve().parent))
from early_boost_isolated import evaluate

INTERVAL=60
DEST="early_boost/early_boost_live.json"
def collect(gh, token):
    watch,_=api.github("watchlist.json",gh)
    categories=watch.get("categories",{})
    symbols=list(dict.fromkeys(str(t).upper() for key in ("nas","china") for t in categories.get(key,[])))
    results=[]
    failures={}
    for ticker in symbols:
        try:
            raw=api.market("/api/v1/candles",token,{"symbol":ticker,"interval":"1m","count":40})
            parsed={}
            for b in api.candles_of(raw):
                if not isinstance(b,dict): continue
                stamp=api.dt(b.get("timestamp"))
                if stamp is None: continue
                try:
                    close=float(b.get("closePrice"))
                    volume=float(b.get("volume"))
                    if close<=0 or volume<0: continue
                except (ValueError,TypeError): continue
                parsed[stamp]={"time":stamp,"close":close,"volume":volume}
            bars=sorted(parsed.values(),key=lambda x:x["time"])
            outcome=evaluate(bars,max_age=5)
            results.append({"ticker":ticker,**outcome})
        except urllib.error.HTTPError as e:
            failures[ticker]="HTTP_"+str(e.code)
        except Exception as e:
            failures[ticker]=type(e).__name__
        time.sleep(0.1)
    payload={"engine":"EARLY_BOOST_PYDROID3","updated_utc":api.utc(),"source":"Toss 1m candles","interval_seconds":60,"symbols_checked":len(symbols),"symbols_returned":len(results),"failure_count":len(failures),"failures":failures,"rows":results}
    api.upload(DEST,payload,gh)
    print("BOOST_UPLOAD_OK",len(results),"failures",len(failures),flush=True)
def main():
    if not api.CONFIG.exists(): raise SystemExit("Saved credentials missing: first run original collector")
    c=json.loads(api.CONFIG.read_text(encoding="utf-8"))
    gh=api.credential(c,"github_token","gh_token","github","github_pat")
    token=api.authorize(c)
    authorized=time.monotonic()
    while True:
        start=time.monotonic()
        try:
            if start-authorized>3000:
                token=api.authorize(c);authorized=time.monotonic()
            collect(gh,token)
        except KeyboardInterrupt: break
        except urllib.error.HTTPError as e:
            print("BOOST_HTTP_ERROR",e.code,flush=True)
            if e.code==401:
                try: token=api.authorize(c);authorized=time.monotonic()
                except Exception as ex: print("BOOST_AUTH_ERROR",type(ex).__name__,flush=True)
        except Exception as e: print("BOOST_ERROR",type(e).__name__,str(e)[:150],flush=True)
        try: time.sleep(max(1,INTERVAL-(time.monotonic()-start)))
        except KeyboardInterrupt: break
if __name__=="__main__": main()
