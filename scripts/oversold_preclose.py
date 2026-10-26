"""Pre-close oversold candidate scan. Technical screening only; not GPT research."""
import json
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import math
import pandas as pd
import yfinance as yf

ROOT=Path(__file__).resolve().parent.parent
watch=json.loads((ROOT/'watchlist.json').read_text(encoding='utf-8'))['categories']
symbols=list(dict.fromkeys(watch.get('nas',[])+watch.get('china',[])+watch.get('oversold',[])))
try:
    discovery=json.loads((ROOT/'discovery_latest.json').read_text(encoding='utf-8'))
    symbols+= [x['ticker'] for x in discovery.get('top10',[]) if x.get('ticker')]
except (FileNotFoundError,ValueError,KeyError): pass
symbols=list(dict.fromkeys(symbols))
now=datetime.now(timezone.utc)
results=[]
for i,ticker in enumerate(symbols):
    try:
        h=yf.download(ticker,period='2mo',interval='1d',auto_adjust=False,progress=False,threads=False,timeout=12)
        if h.empty: continue
        if isinstance(h.columns,pd.MultiIndex):h.columns=h.columns.get_level_values(0)
        h=h.dropna(subset=['Close','Volume'])
        if len(h)<16:continue
        last_date=h.index[-1].date()
        age=(now.astimezone(ZoneInfo('America/New_York')).date()-last_date).days
        if age>3 or age<0:continue
        close=h['Close'].astype(float)
        vol=h['Volume'].astype(float)
        last=float(close.iloc[-1]);prev=float(close.iloc[-2])
        if last<=0 or prev<=0:continue
        change=(last/prev-1)*100
        delta=close.diff()
        gain=delta.clip(lower=0).rolling(14).mean().iloc[-1]
        loss=(-delta.clip(upper=0)).rolling(14).mean().iloc[-1]
        rsi=100 if loss==0 else 100-100/(1+gain/loss)
        baseline=float(vol.iloc[-16:-1].mean())
        vol_ratio=float(vol.iloc[-1])/baseline if baseline>0 else None
        # Rank independently from dilution and SEC risks.
        drop_score=min(45,max(0,-change)*7.5)
        rsi_score=min(35,max(0,40-rsi)*2)
        activity_score=min(20,max(0,(vol_ratio or 0)-1)*10)
        score=round(drop_score+rsi_score+activity_score)
        if change<=-3 or rsi<=35:
            results.append({'ticker':ticker,'score':score,'change_pct':round(change,2),
              'rsi14':round(float(rsi),1),'volume_ratio':round(vol_ratio,2) if vol_ratio is not None else None,
              'price_usd':round(last,4),'bar_date':str(last_date),'signal':'OVERSOLD_CANDIDATE',
              'cause':'미검증','dilution':'미검증','sec':'미검증'})
    except Exception as exc:
        print(ticker, str(exc)[:110],flush=True)
results.sort(key=lambda x:(-x['score'],x['ticker']))
out={'updated_utc':now.isoformat(),'scan_type':'automated_technical_preclose',
     'market_timezone':'America/New_York','scanned':len(symbols),'candidate_count':len(results),
     'top10':results[:10],'method':'Daily change (45), RSI14 (35), volume ratio (20). SEC and event risk excluded from rank.',
     'disclaimer':'Automated technical scan, not GPT-written analysis. News/cause/SEC/dilution unverified. Delayed quotes possible.'}
(ROOT/'oversold_latest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('scanned',len(symbols),'candidates',len(results),'published',len(out['top10']))
