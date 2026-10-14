#!/usr/bin/env python3
"""Read-only Yahoo minute-bar connectivity probe. No API credentials."""
import datetime as dt, json, urllib.request, urllib.parse
from pathlib import Path

out=[]
for symbol in ('AAPL','MSFT','SQQQ'):
    url='https://query1.finance.yahoo.com/v8/finance/chart/'+urllib.parse.quote(symbol)+'?interval=1m&range=1d'
    item={'ticker':symbol,'provider':'Yahoo unofficial 1m','received':False}
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(req,timeout=15) as response:
            data=json.load(response)
        result=data['chart']['result'][0]
        stamps=result.get('timestamp') or []
        vols=result['indicators']['quote'][0].get('volume') or []
        valid=[(s,v) for s,v in zip(stamps,vols) if v is not None]
        item.update(received=bool(valid),bars=len(valid),last_bar_utc=dt.datetime.fromtimestamp(valid[-1][0],dt.timezone.utc).isoformat() if valid else None)
    except Exception as e:
        item['error']=f'{type(e).__name__}: {str(e)[:180]}'
    out.append(item)
report={'checked_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'results':out,'caveat':'Yahoo data may be delayed, incomplete, or throttled; this is not continuous live coverage.'}
Path('nasdaq7_feed_check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
