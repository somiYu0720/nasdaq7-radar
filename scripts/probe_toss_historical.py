#!/usr/bin/env python3
"""Read-only Toss historical candle probe. Never alters live rankings.
Credentials must be injected as environment variables, never committed.
"""
import datetime as dt
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

BASE="https://openapi.tossinvest.com"
TARGET=dt.datetime(2026,10,31,8,59,tzinfo=ZoneInfo("Asia/Seoul")).astimezone(dt.timezone.utc)
def request(path,headers=None,body=None):
    req=urllib.request.Request(BASE+path,data=body,headers=headers or {},method="POST" if body is not None else "GET")
    with urllib.request.urlopen(req,timeout=25) as r:
        return json.load(r)
def main():
    cid=os.environ.get("TOSS_CLIENT_ID")
    secret=os.environ.get("TOSS_CLIENT_SECRET")
    if not cid or not secret:
        print("NOT_RUN: GitHub Actions secrets TOSS_CLIENT_ID and TOSS_CLIENT_SECRET are required")
        return
    payload=urllib.parse.urlencode({"grant_type":"client_credentials","client_id":cid,"client_secret":secret}).encode()
    try:
        token=request("/oauth2/token",{"Content-Type":"application/x-www-form-urlencoded"},payload)["access_token"]
    except urllib.error.HTTPError as e:
        print("AUTH_HTTP_ERROR",e.code)
        return
    except Exception as e:
        print("AUTH_ERROR",type(e).__name__)
        return
    print("AUTH_OK")
    symbol=os.environ.get("PROBE_SYMBOL","INO").strip().upper()
    # The 'before' parameter and accepted timestamp format require live API verification.
    params={"symbol":symbol,"interval":"1m","count":"100","before":TARGET.isoformat().replace("+00:00","Z")}
    path="/api/v1/candles?"+urllib.parse.urlencode(params)
    try:
        result=request(path,{"Authorization":"Bearer "+token})
    except urllib.error.HTTPError as e:
        print("CANDLES_HTTP_ERROR",e.code)
        return
    except Exception as e:
        print("CANDLES_ERROR",type(e).__name__)
        return
    print("HISTORICAL_QUERY_RESPONSE_TYPE",type(result).__name__)
    if isinstance(result,dict):
        print("RESPONSE_KEYS",sorted(result.keys()))
        rows=result.get("data",result.get("candles",result.get("bars",[])))
    else: rows=result
    if isinstance(rows,dict): rows=rows.get("items",rows.get("candles",[]))
    print("CANDLE_COUNT",len(rows) if isinstance(rows,list) else "unrecognized")
    if isinstance(rows,list) and rows:
        print("CANDLE_FIELDS",sorted(rows[0].keys()) if isinstance(rows[0],dict) else "unrecognized")
        # Do not print account info, raw responses, or unverified prices.
if __name__=="__main__": main()
