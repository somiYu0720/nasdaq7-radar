import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]
def load(n): return json.loads((p/n).read_text())
def save(n,d): (p/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n")
w=load("watchlist.json")
n=load("radar_notes.json")
e=load("gpt_monitor_events.json")["events"]
for x in e:
    if x.get("verification")!="VERIFIED" or x.get("auto_add") is not True: continue
    cat={"NASDAQ 7.0":"nas","중국계 1.0":"china"}.get(x.get("radar"))
    t=str(x.get("ticker","")).upper()
    if not cat or not t.isascii() or not t.replace(".","").replace("-","").isalnum() or len(t)>12: continue
    if t not in w["categories"][cat]: w["categories"][cat].append(t)
    if not any(z.get("ticker")==t for z in n["notes"]):
        n["notes"].append({"ticker":t,"radar":cat,"category":x.get("category","GPT 감시"),"memo":x.get("summary","")[:200],"status":"자동 관찰"})
save("watchlist.json",w)
save("radar_notes.json",n)
