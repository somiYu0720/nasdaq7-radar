#!/usr/bin/env python3
"""Fetch official SEC filing metadata for both watchlists; titles are NOT event verification."""
import datetime as dt, json, os, time, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
HEADERS={"User-Agent":os.getenv("SEC_USER_AGENT","NASDAQ7-Radar somiYu0720 41898282+github-actions[bot]@users.noreply.github.com"),"Accept-Encoding":"gzip, deflate","Accept":"application/json"}
FORMS={"8-K","8-K/A","6-K","6-K/A","20-F","20-F/A","10-Q","10-K","F-1","F-1/A","S-1","S-1/A","S-3","S-3/A","424B5","424B3","EFFECT","DEF 14A","SC 13D","SC 13G"}
def fetch(url):
    req=urllib.request.Request(url,headers=HEADERS)
    with urllib.request.urlopen(req,timeout=18) as response:return json.load(response)
def main():
    nas=json.loads((ROOT/"priority_watchlist.json").read_text())["tickers"]
    china=json.loads((ROOT/"china_verified_tickers.json").read_text()).get("candidates",[])
    symbols=list(dict.fromkeys(nas+china))
    old={}
    if (ROOT/"sec_events.json").exists():
        try:old=json.loads((ROOT/"sec_events.json").read_text()).get("tickers",{})
        except (ValueError,OSError):pass
    now=dt.datetime.now(dt.timezone.utc).isoformat()
    result={"checked_utc":now,"source":"SEC EDGAR submissions API","scope":"filing metadata only; no legal/dilution/event conclusion","tickers":{}}
    try:
        mapping=fetch("https://www.sec.gov/files/company_tickers.json")
        lookup={str(x["ticker"]).upper():x for x in mapping.values()}
    except Exception as e:
        result["mapping_error"]=type(e).__name__
        lookup={}
    for symbol in symbols:
        record={"ticker":symbol,"status":"NOT_CHECKED","filings":[],"checked_utc":now}
        match=lookup.get(symbol)
        if match:
            cik=int(match["cik_str"])
            record.update({"cik":cik,"company":match["title"]})
            try:
                data=fetch(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
                recent=data.get("filings",{}).get("recent",{})
                for i,form in enumerate(recent.get("form",[])):
                    if form not in FORMS:continue
                    date=recent.get("filingDate",[])[i]
                    accession=recent.get("accessionNumber",[])[i]
                    doc=recent.get("primaryDocument",[])[i]
                    record["filings"].append({"date":date,"form":form,"accession":accession,
                        "url":f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace('-','')}/{doc}"})
                    if len(record["filings"])>=8:break
                record["status"]="FILINGS_INDEXED"
                record["exchange_listed"]=symbol in data.get("tickers",[])
            except Exception as e:record["status"]="FETCH_FAILED";record["error"]=type(e).__name__
        else:record["status"]="CIK_UNRESOLVED"
        if record["status"]!="FILINGS_INDEXED" and symbol in old:
            record["last_successful_filings"]=old[symbol].get("filings",[])
        result["tickers"][symbol]=record
        time.sleep(0.15)
    (ROOT/"sec_events.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print("SEC indexed",sum(v["status"]=="FILINGS_INDEXED" for v in result["tickers"].values()),"of",len(symbols))
if __name__=="__main__":main()
