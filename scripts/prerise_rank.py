"""Exploratory pre-rise signals. NOT a backtested predictive model."""
import json,math
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
src=json.loads((ROOT/'discovery_latest.json').read_text(encoding='utf-8'))
rows=src.get('top10',[])
out=[]
for x in rows:
    def n(k):
        try:
            v=float(x.get(k))
            return v if math.isfinite(v) else None
        except (ValueError,TypeError):return None
    r=n('rvol5');acc=n('accel_5m');pct=n('change_window_pct');v=n('volume_5m')
    if r is None or pct is None:continue
    # Exploratory 100-point screening, not historical prediction accuracy.
    volume=min(35,max(0,(r-1)*14))
    acceleration=min(25,max(0,((acc or 0)-1)*9))
    not_spiked=25 if -3<=pct<=3 else 12 if -6<=pct<=6 else 0
    liquidity=min(15,max(0,math.log10(1+(v or 0))*3))
    score=round(volume+acceleration+not_spiked+liquidity)
    out.append({'ticker':x.get('ticker'),'score':score,'rvol5':r,'accel_5m':acc,'change_pct':pct,
                'volume_5m':v,'signal':'잠정 관찰','backtest_verified':False,
                'news':'미검증','dilution':'미검증','source_updated_utc':src.get('updated_utc')})
out.sort(key=lambda x:-x['score'])
payload={'updated_utc':datetime.now(timezone.utc).isoformat(),'source_updated_utc':src.get('updated_utc'),
         'method':'Exploratory volume acceleration + non-spiked price + liquidity',
         'backtest_verified':False,'universe_note':'Latest independent discovery TOP10 only; not whole NASDAQ.',
         'top10':out[:10]}
(ROOT/'prerise_latest.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Candidate rankings:',len(out))
