"""Archive authentic Toss candle snapshots without modifying production data.
Snapshots are NOT assumed to be consecutive minute bars.
"""
import csv,json,pathlib,datetime
root=pathlib.Path(__file__).resolve().parents[1]
source=root/"toss_live.json"
out=root/"experiments"/"history.csv"
fields=["ticker","timestamp","close","volume"]
data=json.loads(source.read_text(encoding="utf-8"))
rows={}
if out.exists():
 with out.open(newline="",encoding="utf-8") as f:
  for r in csv.DictReader(f):
   if all(k in r for k in fields):rows[(r["ticker"],r["timestamp"])]=r
now=datetime.datetime.now(datetime.timezone.utc)
added=0
for group in ("nasdaq7","china1"):
 for r in data.get(group,[]):
  try:
   ts=datetime.datetime.fromisoformat(r["candle_time"].replace("Z","+00:00")).astimezone(datetime.timezone.utc)
   if not (datetime.timedelta(0)<=now-ts<=datetime.timedelta(minutes=15)):continue
   p=float(r["close"]);v=float(r["minute_volume"])
   if p<=0 or v<0:continue
   key=(str(r["ticker"]).upper(),ts.isoformat())
   if key not in rows:added+=1
   rows[key]=dict(zip(fields,[key[0],key[1],str(p),str(v)]))
  except (KeyError,ValueError,TypeError,OverflowError):continue
out.parent.mkdir(parents=True,exist_ok=True)
with out.open("w",newline="",encoding="utf-8") as f:
 writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
 writer.writerows(rows[k] for k in sorted(rows))
print(f"New authentic candle snapshots: {added}; total {len(rows)}. Continuity not guaranteed.")
