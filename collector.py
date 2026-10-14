#!/usr/bin/env python3
"""NASDAQ 7.0 trial: daily OHLCV, not a real-time scanner."""
import csv, io, json, time, urllib.request, datetime, html
from pathlib import Path

TICKERS = ['LOBO','AAPL','MSFT','SCNI','JBDI','FRGT','MOGU','CNET','HCTI','WETO']
OUT = Path(__file__).resolve().parent
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; NASDAQ7Trial/1.0)', 'Accept': 'text/csv,application/json,*/*'}

def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=18) as response:
        return response.read(1500000).decode('utf-8-sig')

def stooq(ticker):
    today = datetime.date.today()
    start = today - datetime.timedelta(days=100)
    url = f'https://stooq.com/q/d/l/?s={ticker.lower()}.us&i=d&d1={start:%Y%m%d}&d2={today:%Y%m%d}'
    raw = get(url)
    rows = list(csv.DictReader(io.StringIO(raw)))
    return [{'Date': r['Date'], 'Close': float(r['Close']), 'Volume': float(r['Volume'])} for r in rows if r.get('Date') and r.get('Close') and r.get('Volume')]

def yahoo(ticker):
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=3mo&interval=1d'
    obj = json.loads(get(url))['chart']['result'][0]
    quote = obj['indicators']['quote'][0]
    rows = []
    for stamp, close, volume in zip(obj['timestamp'], quote['close'], quote['volume']):
        if close is None or volume is None:
            continue
        date = datetime.datetime.fromtimestamp(stamp, datetime.timezone.utc).date().isoformat()
        rows.append({'Date': date, 'Close': float(close), 'Volume': float(volume)})
    return rows

def collect(ticker):
    errors = []
    for name, fetch in [('Stooq', stooq), ('Yahoo', yahoo)]:
        try:
            rows = fetch(ticker)
            rows.sort(key=lambda r: r['Date'])
            if len(rows) < 21:
                raise ValueError(f'유효 일봉 {len(rows)}개 (최소 21개 필요)')
            last, prev = rows[-1], rows[-2]
            baseline = sum(r['Volume'] for r in rows[-21:-1]) / 20
            if baseline <= 0 or prev['Close'] <= 0:
                raise ValueError('비교 기준값 0')
            multiple = last['Volume'] / baseline
            change = (last['Close'] / prev['Close'] - 1) * 100
            return {'ticker': ticker, 'date': last['Date'], 'close': round(last['Close'], 4),
                    'volume': int(last['Volume']), 'rvol': round(multiple, 2),
                    'change': round(change, 2), 'status': 'PRE 후보' if multiple >= 3 and -3 <= change <= 10 else '검토',
                    'source': name, 'reason': ''}
        except Exception as exc:
            errors.append(f'{name}: {str(exc)[:110]}')
    return {'ticker': ticker, 'status': '조회 실패', 'source': '', 'reason': ' / '.join(errors)}

results = []
for ticker in TICKERS:
    item = collect(ticker)
    results.append(item)
    print(f"{ticker}: {item['status']} / {item.get('source') or item.get('reason')}", flush=True)
    time.sleep(0.5)

fields = ['ticker','date','close','volume','rvol','change','status','source','reason']
(OUT / 'v62_results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
with (OUT / 'v62_results.csv').open('w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(results)

success = sum(r['status'] != '조회 실패' for r in results)
rows_html = ''.join('<tr>' + ''.join(f'<td>{html.escape(str(r.get(k, "")))}</td>' for k in fields) + '</tr>' for r in results)
page = f'''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NASDAQ 7.0 일봉 시험판</title><style>body{{font:15px system-ui;background:#f3f6fb;padding:20px;color:#183153}}main{{max-width:1100px;margin:auto;background:white;padding:20px;border-radius:16px}}table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{padding:8px;border-bottom:1px solid #ddd;text-align:left}}.scroll{{overflow:auto}}</style><main><h2>NASDAQ 7.0 · 일봉 시험 수집</h2><p>생성: {datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes")} / 성공: {success}/{len(results)}</p><p>API 키 불필요 · 실시간 아님 · 10종목 시험 · SEC 미검증 · 투자 신호 아님</p><div class="scroll"><table><tr>{''.join('<th>'+html.escape(k)+'</th>' for k in fields)}</tr>{rows_html}</table></div></main></html>'''
(OUT / 'V62_RESULT.html').write_text(page, encoding='utf-8')
print(f'데이터 수집 성공: {success}/{len(results)}', flush=True)
if success == 0:
    raise SystemExit('ERROR: 전 종목 데이터 수집 실패. Actions 로그에서 Stooq/Yahoo 오류 확인 필요')
