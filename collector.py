#!/usr/bin/env python3
"""NASDAQ 7.0 V6.5: reuse historical batch; prioritize unseen symbols, then oldest refresh. Daily only."""
import csv, datetime as dt, html, io, json, re, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BATCH_SIZE = 50
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "*/*"}
FIELDS = ["ticker","date","close","volume","rvol","change","status","source","reason","baseline_date","baseline_rvol","baseline_lane","history_status"]

def download(url, timeout=20):
    req=urllib.request.Request(url,headers=HEADERS)
    with urllib.request.urlopen(req,timeout=timeout) as response:
        return response.read(2_000_000).decode("utf-8-sig",errors="replace")

def universe():
    raw=download("https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt")
    rows=csv.DictReader(io.StringIO(raw),delimiter="|")
    symbols=[]
    for row in rows:
        symbol=(row.get("Symbol") or "").strip().upper()
        name=(row.get("Security Name") or "").lower()
        if not re.fullmatch(r"[A-Z]{1,5}",symbol): continue
        if row.get("ETF")=="Y" or row.get("Test Issue")=="Y": continue
        if re.search(r"\b(units?|warrants?|rights?|preferred|depositary|notes?|debentures?)\b",name): continue
        symbols.append(symbol)
    # NYSE American is published in the Nasdaq Trader 'otherlisted' directory.
    # Exchange code A = NYSE American. Keep NASDAQ listings and add only
    # NYSE American common equity candidates; do not mix with China 1.0.
    raw_other=download("https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt")
    other_rows=csv.DictReader(io.StringIO(raw_other),delimiter="|")
    american=[]
    for row in other_rows:
        if (row.get("Exchange") or "").strip().upper()!="A": continue
        symbol=(row.get("ACT Symbol") or "").strip().upper()
        name=(row.get("Security Name") or "").lower()
        if not re.fullmatch(r"[A-Z]{1,5}",symbol): continue
        if row.get("ETF")=="Y" or row.get("Test Issue")=="Y": continue
        if re.search(r"\\b(units?|warrants?|rights?|preferred|depositary|notes?|debentures?)\\b",name): continue
        american.append(symbol)
    if len(american)<50:
        raise ValueError(f"NYSE American 종목 목록 비정상: {len(american)}")
    result=sorted(set(symbols)|set(american))
    if len(result)<100: raise ValueError(f"종목 목록 비정상: {len(result)}")
    print(f"NASDAQ {len(set(symbols))} + NYSE American {len(set(american))}; merged {len(result)}",flush=True)
    return result

def historical():
    path=ROOT/"nasdaq7_baseline.csv"
    if not path.exists(): raise FileNotFoundError("nasdaq7_baseline.csv 누락: 기존 배치 보존을 위해 실행 중단")
    with path.open(encoding="utf-8-sig",newline="") as f:
        data={r["ticker"].strip().upper():r for r in csv.DictReader(f) if r.get("ticker")}
    if len(data)<5000: raise ValueError(f"기존 배치 수가 비정상: {len(data)}")
    return data

def load_state():
    path=ROOT/"v65_refresh_ledger.json"
    if not path.exists(): return {}
    obj=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj,dict): raise ValueError("ledger 형식 오류")
    return obj

def stooq(ticker):
    end=dt.datetime.now(dt.timezone.utc).date()
    start=end-dt.timedelta(days=110)
    url=f"https://stooq.com/q/d/l/?s={ticker.lower()}.us&i=d&d1={start:%Y%m%d}&d2={end:%Y%m%d}"
    return [{"Date":r["Date"],"Close":float(r["Close"]),"Volume":float(r["Volume"])}
            for r in csv.DictReader(io.StringIO(download(url)))
            if r.get("Date") and r.get("Close") and r.get("Volume")]

def yahoo(ticker):
    sym=urllib.parse.quote(ticker,safe="")
    data=json.loads(download(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=3mo&interval=1d"))["chart"]["result"][0]
    quote=data["indicators"]["quote"][0]
    rows=[]
    for stamp,close,volume in zip(data["timestamp"],quote["close"],quote["volume"]):
        if close is None or volume is None: continue
        date=dt.datetime.fromtimestamp(stamp,dt.timezone.utc).date().isoformat()
        rows.append({"Date":date,"Close":float(close),"Volume":float(volume)})
    return rows

def inspect(ticker):
    errors=[]
    for source,fetch in (("Stooq",stooq),("Yahoo",yahoo)):
        try:
            rows=sorted(fetch(ticker),key=lambda r:r["Date"])
            if len(rows)<21: raise ValueError(f"일봉 {len(rows)}개")
            last,prev=rows[-1],rows[-2]
            avg=sum(r["Volume"] for r in rows[-21:-1])/20
            if avg<=0 or prev["Close"]<=0: raise ValueError("기준값 0")
            rvol=last["Volume"]/avg
            change=(last["Close"]/prev["Close"]-1)*100
            status="PRE 후보" if rvol>=3 and -3<=change<=10 else "거래량 이상" if rvol>=3 else "검토"
            return dict(ticker=ticker,date=last["Date"],close=round(last["Close"],4),
                        volume=int(last["Volume"]),rvol=round(rvol,2),change=round(change,2),
                        status=status,source=source,reason="")
        except Exception as e: errors.append(f"{source}: {str(e)[:90]}")
    return dict(ticker=ticker,status="조회 실패",source="",reason=" / ".join(errors))

def save(results,meta,ledger):
    (ROOT/"v62_results.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
    with (ROOT/"v62_results.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(results)
    (ROOT/"v64_batch_meta.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    (ROOT/"v65_refresh_ledger.json").write_text(json.dumps(ledger,ensure_ascii=False,indent=2,sort_keys=True),encoding="utf-8")
    headers="".join("<th>"+html.escape(x)+"</th>" for x in FIELDS)
    rows="".join("<tr>"+"".join("<td>"+html.escape(str(r.get(x,"")))+"</td>" for x in FIELDS)+"</tr>" for r in results)
    page=f"""<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NASDAQ 7.0 V6.5</title><style>body{{font:14px system-ui;background:#f3f6fb;padding:18px;color:#183153}}main{{max-width:1200px;margin:auto;background:white;padding:18px;border-radius:14px}}table{{border-collapse:collapse;width:100%;font-size:12px}}td,th{{padding:7px;border-bottom:1px solid #ddd;text-align:left}}.scroll{{overflow:auto}}</style>
<main><h2>NASDAQ 7.0 V6.5 · 기존 배치 재사용</h2><p>기존 분석: {meta['baseline_count']}개 · 신규 우선 조회: {meta['new_symbols_selected']}개 · 기존 종목 갱신: {meta['old_symbols_selected']}개</p>
<p>조회 성공: {meta['success']} / {meta['checked']} · 전체 목록: {meta['universe_size']} · 기존 데이터는 과거 기록이며 실시간 SEC 검증이 아님</p>
<p>일봉 기준 · 실시간 아님 · SEC/희석 재검증 필요 · 투자 신호 아님</p><div class="scroll"><table><tr>{headers}</tr>{rows}</table></div></main></html>"""
    (ROOT/"V62_RESULT.html").write_text(page,encoding="utf-8")

def main():
    base=historical()
    symbols=universe()
    ledger=load_state()
    # Never discard prior work: unseen in the historical batch and successful refresh ledger comes first.
    unseen=[t for t in symbols if t not in base and t not in ledger]
    # Older historical records are refreshed before recently refreshed names; failures are retried later.
    old=[t for t in symbols if t not in unseen]
    old.sort(key=lambda t:(ledger.get(t,{}).get("checked_at",""),t))
    selected=(unseen+old)[:BATCH_SIZE]
    results=[]
    success=0
    now=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    for ticker in selected:
        result=inspect(ticker)
        b=base.get(ticker)
        result.update(baseline_date=b.get("market_date","") if b else "",
                      baseline_rvol=b.get("rvol","") if b else "",
                      baseline_lane=b.get("lane7","") if b else "",
                      history_status="기존 분석 재사용" if b else "신규 후보")
        results.append(result)
        if result["status"]!="조회 실패":
            success+=1
            ledger[ticker]={"checked_at":now,"market_date":result["date"],"status":result["status"]}
        print(f"{ticker}: {result['status']}",flush=True)
        time.sleep(.35)
    meta=dict(version="6.5",baseline_count=len(base),universe_size=len(symbols),
              checked=len(selected),success=success,failed=len(selected)-success,
              new_symbols_selected=sum(t not in base for t in selected),
              old_symbols_selected=sum(t in base for t in selected),
              completed_full_universe=False,generated_utc=now)
    if success==0: raise SystemExit("수집 전체 실패: 기존 결과를 덮어쓰지 않음")
    save(results,meta,ledger)
    print(f"기존 기록 {len(base)}개 보존 / 이번 조회 {len(selected)}개 / 성공 {success}개",flush=True)

if __name__=="__main__": main()
