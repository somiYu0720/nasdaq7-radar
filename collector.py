#!/usr/bin/env python3
"""NASDAQ 7.0 V6.2: no-key daily-data trial. Not real-time."""
import csv, io, json, time, urllib.request, datetime, html
from pathlib import Path
TICKERS = ["LOBO","AAPL","MSFT","SCNI","JBDI","FRGT","MOGU","CNET","HCTI","WETO"]
OUT=Path(__file__).resolve().parent
results=[]
for ticker in TICKERS:
    url=f"https://stooq.com/q/d/l/?s={ticker.lower()}.us&i=d"
    try:
        req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req,timeout=12) as resp:
            raw=resp.read(250000).decode("utf-8-sig")
        rows=list(csv.DictReader(io.StringIO(raw)))
        rows=[r for r in rows if r.get("Volume") and r.get("Close")]
        if len(rows)<22: raise ValueError("20일 비교에 필요한 일봉 부족")
        last, prev=rows[-1],rows[-2]
        baseline=sum(float(r["Volume"]) for r in rows[-21:-1])/20
        multiple=float(last["Volume"])/baseline if baseline else 0
        change=(float(last["Close"])/float(prev["Close"])-1)*100
        results.append(dict(ticker=ticker,date=last["Date"],close=last["Close"],volume=last["Volume"],rvol=round(multiple,2),change=round(change,2),status="PRE 후보" if multiple>=3 and -3<=change<=10 else "검토"))
    except Exception as e:
        results.append(dict(ticker=ticker,status="조회 실패",reason=str(e)[:120]))
    time.sleep(1.5)
(OUT/"v62_results.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
with (OUT/"v62_results.csv").open("w",newline="",encoding="utf-8-sig") as f:
    writer=csv.DictWriter(f,fieldnames=["ticker","date","close","volume","rvol","change","status","reason"])
    writer.writeheader()
    for r in results: writer.writerow(r)
rows="".join("<tr>"+"".join(f"<td>{html.escape(str(r.get(k,'')))}</td>" for k in ["ticker","date","close","volume","rvol","change","status","reason"])+"</tr>" for r in results)
page=f"""<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NASDAQ 7.0 V6.2</title><style>body{{font:15px system-ui;background:#f3f6fb;padding:20px;color:#183153}}main{{max-width:1000px;margin:auto;background:white;padding:20px;border-radius:16px}}table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{padding:8px;border-bottom:1px solid #ddd;text-align:left}}.scroll{{overflow:auto}}</style><main><h2>NASDAQ 7.0 V6.2 · 일봉 시험 수집</h2><p>생성: {datetime.datetime.now().astimezone().isoformat(timespec='minutes')}</p><p>API 키 불필요 · 실시간 아님 · 10종목 시험 · 데이터 소스 Stooq · SEC 미검증 · 투자 신호 아님</p><div class="scroll"><table><tr><th>티커</th><th>일자</th><th>종가</th><th>거래량</th><th>20일 대비 배수</th><th>등락률 %</th><th>분류</th><th>오류</th></tr>{rows}</table></div></main></html>"""
(OUT/"V62_RESULT.html").write_text(page,encoding="utf-8")
print("완료: V62_RESULT.html / v62_results.csv")
