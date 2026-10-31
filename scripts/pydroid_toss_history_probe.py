#!/usr/bin/env python3
"""Pydroid 3: read-only Toss historical candle test from the registered phone IP.
Does not touch the running collector, GitHub, or dashboard.
"""
import datetime as dt
import getpass
import json
import urllib.error
import urllib.parse
import urllib.request

BASE="https://openapi.tossinvest.com"
TARGET="2026-10-30T23:59:00Z"  # 2026-10-31 08:59 KST
def call(path,token=None,body=None):
    headers={"User-Agent":"nasdaq7-history-probe/1.0"}
    if token: headers["Authorization"]="Bearer "+token
    if body is not None: headers["Content-Type"]="application/x-www-form-urlencoded"
    req=urllib.request.Request(BASE+path,data=body,headers=headers,method="POST" if body is not None else "GET")
    with urllib.request.urlopen(req,timeout=25) as response:
        return json.load(response)
def main():
    print("Toss historical 1m probe | INO | target 2026-10-31 08:59 KST")
    cid=input("TOSS_CLIENT_ID: ").strip()
    secret=getpass.getpass("TOSS_CLIENT_SECRET (hidden): ").strip()
    if not cid or not secret:
        print("MISSING_CREDENTIALS"); return
    body=urllib.parse.urlencode({"grant_type":"client_credentials","client_id":cid,"client_secret":secret}).encode()
    try:
        token=call("/oauth2/token",body=body)["access_token"]
    except urllib.error.HTTPError as e:
        print("AUTH_HTTP_ERROR",e.code); return
    except Exception as e:
        print("AUTH_ERROR",type(e).__name__); return
    print("AUTH_OK")
    query=urllib.parse.urlencode({"symbol":"INO","interval":"1m","count":100,"before":TARGET})
    try:
        data=call("/api/v1/candles?"+query,token=token)
    except urllib.error.HTTPError as e:
        print("CANDLES_HTTP_ERROR",e.code); return
    except Exception as e:
        print("CANDLES_ERROR",type(e).__name__); return
    print("CANDLES_RESPONSE_TYPE",type(data).__name__)
    if isinstance(data,dict):
        print("CANDLES_RESPONSE_KEYS",sorted(data))
        rows=data.get("result",data.get("data",data.get("candles",data.get("bars",[]))))
    else: rows=data
    if isinstance(rows,dict):
        print("CANDLES_DATA_KEYS",sorted(rows))
        rows=rows.get("candles",rows.get("items",[]))
    print("CANDLE_COUNT",len(rows) if isinstance(rows,list) else "UNKNOWN")
    if isinstance(rows,list) and rows and isinstance(rows[0],dict):
        print("CANDLE_FIELDS",sorted(rows[0]))
        print("FIRST_CANDLE_TIME",rows[0].get("timestamp"))
        print("FIRST_CANDLE_CLOSE",rows[0].get("closePrice"))
        print("FIRST_CANDLE_VOLUME",rows[0].get("volume"))
    print("NO_FILES_WRITTEN")
if __name__=="__main__":
    main()
