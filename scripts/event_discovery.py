#!/usr/bin/env python3
"""Build independently labelled event discovery candidates; never claim filing metadata verifies catalysts."""
import json, datetime as dt, re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def read(name,default):
    try:return json.loads((ROOT/name).read_text(encoding="utf-8"))
    except (OSError,ValueError):return default
def main():
    now=dt.datetime.now(dt.timezone.utc)
    cutoff=(now-dt.timedelta(days=14)).date().isoformat()
    calendar=read("event_calendar.json",{}).get("events",[])
    known={(str(x.get("ticker","")).upper(),x.get("source_url","")) for x in calendar}
    monitor=read("gpt_monitor_events.json",{}).get("events",[])
    sec=read("sec_events.json",{}).get("tickers",{})
    candidates=[]
    for x in monitor:
        ticker=str(x.get("ticker","")).upper()
        url=x.get("source_url","")
        if not re.fullmatch(r"[A-Z0-9.-]{1,12}",ticker) or not isinstance(url,str) or not url.startswith("https://"):continue
        if (ticker,url) in known:continue
        detected=str(x.get("detected_utc",""))[:10]
        if detected<cutoff:continue
        radar=x.get("radar","")
        if radar not in ("NASDAQ 7.0","중국계 1.0"):continue
        candidates.append({"id":str(x.get("id","")),"ticker":ticker,"radar":radar,"source":"GPT_MONITOR","detected_utc":x.get("detected_utc"),"category":x.get("category"),"summary":x.get("summary"),"source_url":url,"verification":"NEEDS_PRIMARY_SOURCE_REVIEW","event_date":None,"schedule_status":"DATE_UNVERIFIED"})
    for ticker,entry in sec.items():
        radar="중국계 1.0" if ticker in set(read("china_verified_tickers.json",{}).get("candidates",[])) else "NASDAQ 7.0"
        for filing in entry.get("filings",[]):
            if filing.get("date","")<cutoff or filing.get("form") not in ("8-K","6-K","8-K/A","6-K/A"):continue
            url=filing.get("url","")
            if not url or (ticker,url) in known:continue
            candidates.append({"id":filing.get("accession"),"ticker":ticker,"radar":radar,"source":"SEC_FORM_INDEX","detected_utc":filing.get("date"),"category":"SEC filing review","summary":filing.get("form")+" filed; contents and event significance NOT verified","source_url":url,"verification":"FORM_ONLY_NOT_CONTENT_VERIFIED","event_date":None,"schedule_status":"DATE_UNVERIFIED"})
    dedup={}
    for x in candidates:
        key=(x["ticker"],x["source_url"],x["radar"])
        dedup[key]=x
    out={"updated_utc":now.isoformat(),"scope":"Candidates only. No automatically verified event dates or FDA approvals. NASDAQ and China independent.","events":list(dedup.values())[:600]}
    (ROOT/"event_discovery_candidates.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Event candidates",len(out["events"]))
if __name__=="__main__":main()
