"""Non-invasive automated backtest from stored historical minute bars.
Does not modify live rankings. Missing history yields explicit pending status.
"""
import csv, json, pathlib, subprocess, sys
from datetime import datetime, timezone
ROOT=pathlib.Path(__file__).resolve().parents[1]
HISTORY=ROOT/"experiments"/"history.csv"
OUT=ROOT/"backtest_results.json"
result={"updated_at":datetime.now(timezone.utc).isoformat(),"status":"WAITING_FOR_HISTORICAL_MINUTE_BARS","source":"Toss minute bars (historical archive required)","production_rankings_unchanged":True,"summary":{}}
if HISTORY.exists():
    try:
        raw=subprocess.check_output([sys.executable,str(ROOT/"experiments"/"backtest_engine.py"),str(HISTORY)],text=True,timeout=120)
        data=json.loads(raw)
        result["summary"]=data.get("summary",{})
        result["signal_count"]=len(data.get("signals",[]))
        result["status"]="RESEARCH_RESULTS_NOT_VALIDATED"
    except Exception as exc:
        result["status"]="BACKTEST_ERROR"
        result["error"]=str(exc)[:300]
OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(result["status"])
