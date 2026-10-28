#!/usr/bin/env python3
"""Non-invasive snapshot history builder. Does not modify Toss collector or live feed."""
import json, os, pathlib, urllib.request, datetime
ROOT=pathlib.Path(__file__).resolve().parents[1]
HISTORY=ROOT/"toss_history.json"
LIVE=ROOT/"toss_live.json"
def main():
    if not LIVE.exists(): return
    data=json.loads(LIVE.read_text(encoding="utf-8"))
    if not isinstance(data,dict) or not data.get("updated_utc"): return
    old=json.loads(HISTORY.read_text(encoding="utf-8")) if HISTORY.exists() else {"snapshots":[]}
    snaps=old.get("snapshots",[])
    stamp=data["updated_utc"]
    if not any(s.get("updated_utc")==stamp for s in snaps):
        snaps.append({"updated_utc":stamp,"nasdaq7":data.get("nasdaq7",[]),"china1":data.get("china1",[])})
    snaps=sorted(snaps,key=lambda x:x["updated_utc"])[-180:]
    HISTORY.write_text(json.dumps({"source":"toss_live.json","sampling":"GitHub Actions interval; not guaranteed one minute","snapshots":snaps},ensure_ascii=False,separators=(",",":")),encoding="utf-8")
if __name__=="__main__": main()
