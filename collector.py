#!/usr/bin/env python3
"""NASDAQ 7.0 V6.4 - 50-symbol rotating daily-data batch trial, NOT realtime."""
import csv
import datetime as dt
import html
import io
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BATCH_SIZE = 50
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "*/*"}
FIELDS = ["ticker", "date", "close", "volume", "rvol", "change", "status", "source", "reason"]


def download(url, timeout=20):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read(2_000_000).decode("utf-8-sig", errors="replace")


def universe():
    url = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
    raw = download(url)
    rows = csv.DictReader(io.StringIO(raw), delimiter="|")
    symbols = []
    for row in rows:
        symbol = (row.get("Symbol") or "").strip().upper()
        name = (row.get("Security Name") or "").lower()
        if not re.fullmatch(r"[A-Z]{1,5}", symbol):
            continue
        if row.get("ETF") == "Y" or row.get("Test Issue") == "Y":
            continue
        if any(word in name for word in ("warrant", "rights", "unit ", "preferred", "depositary share")):
            continue
        symbols.append(symbol)
    symbols = sorted(set(symbols))
    if len(symbols) < 100:
        raise ValueError(f"상장 종목 목록 비정상: {len(symbols)}")
    return symbols


def stooq(ticker):
    end = dt.datetime.now(dt.timezone.utc).date()
    start = end - dt.timedelta(days=110)
    url = f"https://stooq.com/q/d/l/?s={ticker.lower()}.us&i=d&d1={start:%Y%m%d}&d2={end:%Y%m%d}"
    rows = csv.DictReader(io.StringIO(download(url)))
    return [
        {"Date": r["Date"], "Close": float(r["Close"]), "Volume": float(r["Volume"])}
        for r in rows if r.get("Date") and r.get("Close") and r.get("Volume")
    ]


def yahoo(ticker):
    symbol = urllib.parse.quote(ticker, safe="")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=3mo&interval=1d"
    data = json.loads(download(url))["chart"]["result"][0]
    quote = data["indicators"]["quote"][0]
    rows = []
    for stamp, close, volume in zip(data["timestamp"], quote["close"], quote["volume"]):
        if close is None or volume is None:
            continue
        date = dt.datetime.fromtimestamp(stamp, dt.timezone.utc).date().isoformat()
        rows.append({"Date": date, "Close": float(close), "Volume": float(volume)})
    return rows


def inspect(ticker):
    errors = []
    for source, fetch in (("Stooq", stooq), ("Yahoo", yahoo)):
        try:
            rows = sorted(fetch(ticker), key=lambda x: x["Date"])
            if len(rows) < 21:
                raise ValueError(f"유효 일봉 {len(rows)}개 / 21개 필요")
            last, prev = rows[-1], rows[-2]
            avg = sum(r["Volume"] for r in rows[-21:-1]) / 20
            if avg <= 0 or prev["Close"] <= 0:
                raise ValueError("비교 기준값이 0")
            rvol = last["Volume"] / avg
            change = (last["Close"] / prev["Close"] - 1) * 100
            status = (
                "PRE 후보" if rvol >= 3 and -3 <= change <= 10
                else "거래량 이상" if rvol >= 3
                else "검토"
            )
            return dict(
                ticker=ticker, date=last["Date"],
                close=round(last["Close"], 4),
                volume=int(last["Volume"]),
                rvol=round(rvol, 2),
                change=round(change, 2),
                status=status, source=source, reason=""
            )
        except Exception as exc:
            errors.append(f"{source}: {str(exc)[:90]}")
    return dict(
        ticker=ticker, status="조회 실패", source="",
        reason=" / ".join(errors)
    )


def write_outputs(results, meta):
    (ROOT / "v62_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    with (ROOT / "v62_results.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(results)

    (ROOT / "v64_batch_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    lines = "".join(
        "<tr>" + "".join(
            f"<td>{html.escape(str(row.get(field, '')))}</td>"
            for field in FIELDS
        ) + "</tr>"
        for row in results
    )
    columns = "".join(
        f"<th>{html.escape(field)}</th>" for field in FIELDS
    )
    generated = dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes")
    page = f'''<!doctype html><html lang="ko">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NASDAQ 7.0 V6.4</title>
<style>
body{{font:14px system-ui;background:#f3f6fb;padding:18px;color:#183153}}
main{{max-width:1100px;margin:auto;background:white;padding:18px;border-radius:14px}}
table{{border-collapse:collapse;width:100%;font-size:12px}}
td,th{{padding:7px;border-bottom:1px solid #ddd;text-align:left}}
.scroll{{overflow:auto}}
</style>
<main>
<h2>NASDAQ 7.0 V6.4 · 일봉 배치 시험</h2>
<p>생성(UTC): {generated}</p>
<p>이번 배치: {meta['checked']}종목 /
수집 성공: {meta['success']} /
조회 실패: {meta['failed']} /
후보 목록: {meta['universe_size']}종목 /
배치 시작 위치: {meta['start_index']}</p>
<p>전체시장 전수 완료 아님 · 소형주만 필터링한 목록 아님 ·
일봉 기준 · 실시간 아님 · SEC 미검증 · 투자 신호 아님</p>
<div class="scroll"><table>
<tr>{columns}</tr>{lines}
</table></div></main></html>'''
    (ROOT / "V62_RESULT.html").write_text(page, encoding="utf-8")


def main():
    try:
        tickers = universe()
        print(f"NASDAQ 종목 목록: {len(tickers)}개", flush=True)
    except Exception as exc:
        raise SystemExit(
            f"ERROR: 상장 종목 목록 다운로드 실패: {exc}"
        )

    state_path = ROOT / "v64_cursor.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        start = int(state.get("next_index", 0)) % len(tickers)
    except (FileNotFoundError, ValueError, TypeError, json.JSONDecodeError):
        start = 0

    batch = [
        tickers[(start + i) % len(tickers)]
        for i in range(min(BATCH_SIZE, len(tickers)))
    ]
    results = []
    for ticker in batch:
        result = inspect(ticker)
        results.append(result)
        print(
            f"{ticker}: {result['status']} / "
            f"{result.get('source') or result.get('reason')}",
            flush=True
        )
        time.sleep(0.35)

    success = sum(row["status"] != "조회 실패" for row in results)
    meta = dict(
        universe_size=len(tickers),
        start_index=start,
        checked=len(batch),
        success=success,
        failed=len(batch)-success,
        completed_full_universe=False
    )
    write_outputs(results, meta)

    if success == 0:
        raise SystemExit(
            "ERROR: 이번 배치 전체 수집 실패. 커서를 전진시키지 않음"
        )

    next_index = (start + len(batch)) % len(tickers)
    state_path.write_text(
        json.dumps(
            {"next_index": next_index, "universe_size": len(tickers)},
            indent=2
        ),
        encoding="utf-8"
    )
    print(
        f"배치 완료: {len(batch)}개 중 {success}개 성공 / "
        f"다음 시작 위치: {next_index}",
        flush=True
    )


if __name__ == "__main__":
    main()
