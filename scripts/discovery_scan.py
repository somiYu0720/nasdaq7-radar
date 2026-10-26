"""NASDAQ 7.0 V3.1: on-demand provisional 1-minute volume scanner.
Free yfinance quotes can be delayed or unavailable; not a real-time feed.
"""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import time
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent


def universe(path):
    df = pd.read_csv(path, encoding='utf-8-sig')
    col = next((c for c in df if c.strip().lower() in ('ticker', 'symbol')), None)
    if col is None:
        raise ValueError('Universe CSV needs ticker or symbol column')
    return list(dict.fromkeys(s for s in df[col].dropna().astype(str).str.upper().str.strip() if s and s != 'NAN'))


def scan(ticker, max_age_min, min_volume):
    h = yf.download(ticker, period='5d', interval='1m', prepost=False,
                    auto_adjust=False, progress=False, threads=False, timeout=12)
    if h.empty:
        return dict(ticker=ticker, signal='NO_DATA', data_status='NO_DATA')
    if isinstance(h.columns, pd.MultiIndex):
        h.columns = h.columns.get_level_values(0)
    h = h.dropna(subset=['Close', 'Volume']).sort_index()
    if h.empty:
        return dict(ticker=ticker, signal='NO_DATA', data_status='NO_DATA')
    idx = h.index
    if idx.tz is None:
        raise ValueError('Intraday data has no timezone')
    dates = idx.tz_convert('America/New_York').date
    last_day = dates[-1]
    today = h.loc[dates == last_day]
    history = h.loc[dates < last_day]
    stamp = today.index[-1].to_pydatetime().astimezone(timezone.utc)
    age = (datetime.now(timezone.utc) - stamp).total_seconds() / 60
    if age < -2 or age > max_age_min:
        return dict(ticker=ticker, signal='STALE', age_min=round(age, 1),
                    bar_time_utc=stamp.isoformat(), data_status='STALE')
    if len(today) < 5:
        return dict(ticker=ticker, signal='INSUFFICIENT_BARS',
                    bars_today=len(today), data_status='INSUFFICIENT_BARS')

    v = today['Volume'].astype(float)
    if len(today) >= 46:
        base = float(v.iloc[-45:-15].mean())
        baseline_type = 'TODAY_PRIOR_30M'
    elif len(history) >= 30:
        base = float(history['Volume'].astype(float).mean())
        baseline_type = 'PREVIOUS_SESSIONS_PROVISIONAL'
    elif len(today) >= 10:
        base = float(v.iloc[:-5].mean())
        baseline_type = 'TODAY_SHORT_PROVISIONAL'
    else:
        return dict(ticker=ticker, signal='NO_BASELINE',
                    bars_today=len(today), data_status='NO_BASELINE')
    if not pd.notna(base) or base <= 0:
        return dict(ticker=ticker, signal='ZERO_BASE_VOLUME', data_status='ZERO_BASE_VOLUME')

    def window(n):
        if len(today) < n:
            return None, None
        volume = float(v.iloc[-n:].sum())
        return volume, volume / (n * base)

    v5, r5 = window(5)
    v10, r10 = window(10)
    v15, r15 = window(15)
    prev5 = float(v.iloc[-10:-5].sum()) if len(today) >= 10 else None
    acceleration = v5 / prev5 if prev5 and prev5 > 0 else None
    price = float(today['Close'].iloc[-1])
    lookback = min(15, len(today) - 1)
    price_before = float(today['Close'].iloc[-1-lookback])
    pct = 100 * (price / price_before - 1) if price_before > 0 else None
    high_rvol = max(x for x in (r5, r10, r15) if x is not None)
    if pct is None:
        signal = 'REVIEW'
    elif high_rvol >= 3 and pct > 10:
        signal = 'ALREADY_UP'
    elif high_rvol >= 3 and pct < -10:
        signal = 'SHARP_DROP'
    elif high_rvol >= 3 and v5 >= min_volume:
        signal = 'EARLY_PRE' if baseline_type == 'TODAY_PRIOR_30M' else 'EARLY_PROVISIONAL'
    elif high_rvol >= 3:
        signal = 'LOW_VOLUME_REVIEW'
    else:
        signal = 'WATCH'
    return dict(ticker=ticker, signal=signal, price=round(price, 5),
                change_window_pct=round(pct, 2) if pct is not None else None,
                change_window_minutes=lookback,
                rvol5=round(r5, 2),
                rvol10=round(r10, 2) if r10 is not None else None,
                rvol15=round(r15, 2) if r15 is not None else None,
                accel_5m=round(acceleration, 2) if acceleration is not None else None,
                volume_5m=int(v5),
                volume_10m=int(v10) if v10 is not None else None,
                volume_15m=int(v15) if v15 is not None else None,
                bars_today=len(today), baseline_type=baseline_type,
                age_min=round(age, 1), bar_time_utc=stamp.isoformat(),
                data_status='FREE_DELAY_POSSIBLE', sec_status='NOT_VERIFIED',
                atm_status='NOT_VERIFIED', dilution_status='NOT_VERIFIED',
                news_status='NOT_VERIFIED')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--universe', default=None)
    p.add_argument('--limit', type=int, default=50)
    p.add_argument('--max-age-min', type=float, default=10)
    p.add_argument('--min-volume', type=int, default=1000)
    args = p.parse_args()
    if args.universe:
        src = ROOT / args.universe
    else:
        matches = sorted(ROOT.glob('NASDAQ7_INTEGRATED_RADAR_*.csv'))
        if len(matches) != 1:
            raise SystemExit(f'Expected exactly one universe CSV, found: {[x.name for x in matches]}')
        src = matches[0]
    symbols = universe(src)[:args.limit]
    rows = []
    for i, ticker in enumerate(symbols, 1):
        try:
            item = scan(ticker, args.max_age_min, args.min_volume)
            rows.append(item if item else dict(ticker=ticker, signal='NO_DATA', data_status='NO_DATA'))
            print(f'{i}/{len(symbols)} {ticker}: {item["signal"] if item else "NO_DATA"}', flush=True)
        except Exception as exc:
            rows.append(dict(ticker=ticker, signal='ERROR', data_status='ERROR', error_detail=str(exc)[:150]))
            print(f'{i}/{len(symbols)} {ticker}: ERROR {str(exc)[:150]}', flush=True)
        time.sleep(0.2)
    if not rows:
        raise SystemExit('No usable rows; no fabricated results.')
    out = pd.DataFrame(rows)
    rank = {'EARLY_PRE': 0, 'EARLY_PROVISIONAL': 1, 'LOW_VOLUME_REVIEW': 2, 'ALREADY_UP': 3,
            'SHARP_DROP': 4, 'WATCH': 5, 'REVIEW': 6, 'STALE': 7, 'INSUFFICIENT_BARS': 8,
            'NO_BASELINE': 9, 'ZERO_BASE_VOLUME': 10, 'NO_DATA': 11, 'ERROR': 12}
    out['_rank'] = out['signal'].map(rank).fillna(13)
    # Missing RVOL is unknown, not zero. Sorting must still work when all rows are STALE/NO_DATA.
    if 'rvol5' not in out.columns:
        out['rvol5'] = float('nan')
    out = out.sort_values(['_rank', 'rvol5'], ascending=[True, False], na_position='last').drop(columns='_rank')
    dest = ROOT / 'NASDAQ7_EARLY_RESULT.csv'
    out.to_csv(dest, index=False, encoding='utf-8-sig')
    print(f'Saved {dest.name}: {len(out)} rows from {len(symbols)} attempted tickers')
    print(out.head(10).to_string(index=False))


if __name__ == '__main__':
    main()
