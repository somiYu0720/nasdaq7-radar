#!/usr/bin/env python3
"""Conservative SEC form triage; never infer event facts from form alone."""
import json
from pathlib import Path
p=Path(__file__).resolve().parent/"sec_events.json"
if not p.exists():raise SystemExit("SEC snapshot missing; wait for first successful fetch")
d=json.loads(p.read_text(encoding="utf-8"))
mapping={"S-1":"자금조달·등록 검토","S-1/A":"자금조달·등록 검토","F-1":"자금조달·등록 검토","F-1/A":"자금조달·등록 검토","S-3":"자금조달·등록 검토","S-3/A":"자금조달·등록 검토","424B5":"증권 발행 조건 검토","424B3":"증권 등록·재판매 검토","EFFECT":"등록 효력 확인 필요","8-K":"주요 이벤트 원문 검토","8-K/A":"주요 이벤트 원문 검토","6-K":"해외기업 주요 공시 검토","6-K/A":"해외기업 주요 공시 검토","10-Q":"정기 재무공시","10-K":"정기 재무공시","20-F":"정기 재무공시","20-F/A":"정기 재무공시","DEF 14A":"주주총회·의결 검토","SC 13D":"주요주주 공시","SC 13G":"주요주주 공시"}
for ticker,record in d.get("tickers",{}).items():
    for filing in record.get("filings",[]):
        filing["triage"]=mapping.get(filing.get("form"),"기타 공시")
        filing["verified_event"]=False
        filing["dilution_active"]="UNKNOWN"
        filing["event_impact"]="UNASSESSED"
    record["classification_level"]="FORM_ONLY_NOT_CONTENT_VERIFIED"
    record["event_confirmed"]=False
    record["dilution_status"]="NOT_VERIFIED"
p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")
print("Classified form types only for",len(d.get("tickers",{})),"tickers")
