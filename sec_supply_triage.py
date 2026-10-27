#!/usr/bin/env python3
"""Conservative SEC supply review queue. No A/B/C/D class is confirmed by keyword matching."""
import json
from pathlib import Path
root=Path(__file__).resolve().parent
path=root/"sec_dilution_evidence.json"
data=json.loads(path.read_text(encoding="utf-8"))
sec=json.loads((root/"sec_events.json").read_text(encoding="utf-8"))
counts={}
for ticker,item in data.get("tickers",{}).items():
    evidence=item.get("evidence") or []
    kinds={e.get("category") for e in evidence}
    forms={f.get("form") for f in sec.get("tickers",{}).get(ticker,{}).get("filings",[])}
    if not evidence:
        candidate=None
        reason="공시 원문에서 해당 키워드 미검출; 위험 없음 의미 아님"
    elif kinds & {"WARRANT","CONVERTIBLE","ELOC"}:
        candidate="D"
        reason="워런트·전환·ELOC 문구 검토 필요; 행사 조건·리셋·현재 유효성 미확인"
    elif "EFFECT" in forms and ("RESALE" in kinds or "424B3" in forms or "424B5" in forms):
        candidate="C"
        reason="EFFECT 및 재판매 관련 문구 확인; 실제 등록 대상·즉시 매도 가능 여부 미확인"
    elif kinds & {"ATM","RESALE"} or forms & {"S-1","S-3","F-1","F-3"}:
        candidate="B"
        reason="자금조달·등록 관련 문구 확인; 효력·발행·매도 가능 시점 미확인"
    else:
        candidate=None
        reason="문구 발견; 공급 상태 분류 근거 부족"
    item["supply_review_candidate"]=candidate
    item["supply_review_reason"]=reason
    item["supply_type"]=None
    item["immediately_sellable_supply"]=None
    item["classification_level"]="REVIEW_CANDIDATE_NOT_VERIFIED"
    counts[candidate or "UNCLASSIFIED"]=counts.get(candidate or "UNCLASSIFIED",0)+1
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("Review candidates (not confirmed):",counts)
