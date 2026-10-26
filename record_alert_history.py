#!/usr/bin/env python3
"""Append newly observed radar signals. This is NOT a Telegram delivery receipt."""
import json,datetime as dt
from pathlib import Path
root=Path(__file__).resolve().parent
bridge=json.loads((root/"radar_bridge.json").read_text(encoding="utf-8"))
path=root/"alert_history.json"
try: data=json.loads(path.read_text(encoding="utf-8"))
except (OSError,ValueError):data={"history":[]}
history=data.get("history",[])
seen={(x.get("radar"),x.get("ticker"),x.get("bar_time")) for x in history}
now=dt.datetime.now(dt.timezone.utc)
for lane,key in (("NASDAQ7","nasdaq7"),("CHINA1","china1")):
    for x in bridge.get(key,[]):
        if x.get("signal")!="EARLY_PROVISIONAL":continue
        if lane=="CHINA1" and not x.get("china_verified"):continue
        stamp=x.get("bar_time")
        if not stamp:continue
        try: age=(now-dt.datetime.fromisoformat(stamp.replace("Z","+00:00"))).total_seconds()
        except (TypeError,ValueError):continue
        if not 0<=age<=15*60:continue
        ident=(lane,x.get("ticker"),stamp)
        if ident in seen:continue
        history.append({"radar":lane,"ticker":x.get("ticker"),"bar_time":stamp,
                        "rvol5":x.get("rvol5"),"signal":"EARLY_PROVISIONAL",
                        "detected_utc":now.isoformat(),"telegram_delivery":"UNVERIFIED",
                        "source":"public_radar_snapshot"})
        seen.add(ident)
data={"updated_utc":now.isoformat(),"history":history[-2000:]}
path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
print("Recorded radar observations:",len(history))
