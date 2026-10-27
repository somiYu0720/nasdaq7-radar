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
    result["tickers"][ticker]={"status":"NOT_IN_SEC_SNAPSHOT" if record.get("status")=="NOT_IN_SEC_SNAPSHOT" else ("EVIDENCE_FOUND" if matches else "NOT_VERIFIED"),"evidence":matches,"errors":errors,"supply_type":None,"immediately_sellable_supply":None,"classification_level":"KEYWORD_ONLY"}
(root/"sec_dilution_evidence.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print("Reviewed",len(result["tickers"]),"tickers")
