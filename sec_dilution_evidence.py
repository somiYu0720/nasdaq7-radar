#!/usr/bin/env python3
"""Collect conservative SEC filing evidence; never infer sellable supply from keywords."""
import os, json, re, time, html, datetime, urllib.request
from pathlib import Path
root=Path(__file__).resolve().parent
agent=os.environ.get("SEC_USER_AGENT","").strip()
if not agent or "@" not in agent:
    raise SystemExit("Missing SEC_USER_AGENT repository secret")
source=json.loads((root/"sec_events.json").read_text(encoding="utf-8"))
watch=json.loads((root/"watchlist.json").read_text(encoding="utf-8"))
calendar=json.loads((root/"event_calendar.json").read_text(encoding="utf-8"))
event_symbols=set(watch.get("categories",{}).get("event",[]))
event_symbols.update(x.get("ticker") for x in calendar.get("events",[]) if x.get("ticker"))
for symbol in sorted(event_symbols):
    if isinstance(symbol,str) and re.fullmatch(r"[A-Z0-9.-]{1,12}",symbol):
        source.setdefault("tickers",{}).setdefault(symbol,{"ticker":symbol,"status":"NOT_IN_SEC_SNAPSHOT","filings":[]})

result={"checked_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"method":"SEC filing text keyword screening; not legal verification","tickers":{}}
patterns={"ATM":r"at.the.market|sales agreement","ELOC":r"equity line of credit|equity purchase agreement","WARRANT":r"warrant.{0,25}exercise","CONVERTIBLE":r"convertible (?:note|debenture|preferred)","RESALE":r"selling stockholder|resale registration"}
# SEC official company ticker map, then submissions metadata for missing tickers.
try:
    req=urllib.request.Request("https://www.sec.gov/files/company_tickers.json",headers={"User-Agent":agent})
    with urllib.request.urlopen(req,timeout=20) as response:
        ticker_map=json.load(response)
    cik_map={str(x.get("ticker","")).upper():int(x["cik_str"]) for x in ticker_map.values() if x.get("ticker") and x.get("cik_str")}
except Exception as exc:
    print("CIK map unavailable:",str(exc)[:150])
    cik_map={}
for ticker,record in source.get("tickers",{}).items():
    if record.get("filings") or not cik_map.get(ticker):
        continue
    try:
        cik=cik_map[ticker]
        req=urllib.request.Request("https://data.sec.gov/submissions/CIK%010d.json"%cik,headers={"User-Agent":agent})
        with urllib.request.urlopen(req,timeout=20) as response:
            submission=json.load(response)
        recent=submission.get("filings",{}).get("recent",{})
        filings=[]
        for i,form in enumerate(recent.get("form",[])):
            if form not in ("8-K","6-K","S-1","S-3","F-1","F-3","424B3","424B5","EFFECT"):
                continue
            accession=recent.get("accessionNumber",[])[i].replace("-","")
            document=recent.get("primaryDocument",[])[i]
            url="https://www.sec.gov/Archives/edgar/data/%d/%s/%s"%(cik,accession,document)
            filings.append({"form":form,"date":recent.get("filingDate",[])[i],"url":url})
            if len(filings)>=5:
                break
        record["filings"]=filings
        record["status"]="SEC_SUBMISSIONS_FETCHED"
    except Exception as exc:
        record["status"]="SEC_SUBMISSIONS_ERROR"
        print(ticker,"submissions error",str(exc)[:120])
    time.sleep(0.3)
for ticker,record in source.get("tickers",{}).items():
    matches=[];errors=[]
    for filing in record.get("filings",[])[:5]:
        url=filing.get("url","")
        if not url.startswith("https://www.sec.gov/Archives/"):
            continue
        try:
            req=urllib.request.Request(url,headers={"User-Agent":agent})
            with urllib.request.urlopen(req,timeout=15) as response:
                raw=response.read(1200000).decode("utf-8","replace")
            plain=html.unescape(re.sub("<[^>]+>"," ",raw))
            plain=re.sub(r"\s+"," ",plain)
            for category,pattern in patterns.items():
                match=re.search(pattern,plain,re.I)
                if match:
                    matches.append({"category":category,"source_url":url,"form":filing.get("form"),"excerpt":plain[max(0,match.start()-80):match.end()+160]})
        except Exception as exc:
            errors.append({"source_url":url,"reason":str(exc)[:100]})
        time.sleep(0.3)
    result["tickers"][ticker]={"status":record.get("status") if record.get("status") in ("NOT_IN_SEC_SNAPSHOT","SEC_SUBMISSIONS_ERROR") else ("EVIDENCE_FOUND" if matches else ("SEC_SUBMISSIONS_FETCHED" if record.get("status")=="SEC_SUBMISSIONS_FETCHED" else "NOT_VERIFIED")),"evidence":matches,"errors":errors,"supply_type":None,"immediately_sellable_supply":None,"classification_level":"KEYWORD_ONLY"}
(root/"sec_dilution_evidence.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print("Reviewed",len(result["tickers"]),"tickers")
