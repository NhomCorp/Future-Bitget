#!/usr/bin/env python3
"""Download Bitget USDT-M 1m history candles, paginate backwards, cache pickle+csv."""
import time
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone, timedelta

BASE = "https://api.bitget.com/api/v2/mix/market/history-candles"
DATA_DIR = Path("/workspace/bitget/backtest/data")
CACHE_DIR = Path("/workspace/bitget/backtest/cache")
SYMBOLS = ["BTCUSDT", "ETHUSDT"]
LIMIT = 200
SLEEP = 0.11
DAYS = 60


def fetch_batch(symbol: str, end_time_ms: int) -> list:
    params = {
        "symbol": symbol,
        "productType": "USDT-FUTURES",
        "granularity": "1m",
        "endTime": str(end_time_ms),
        "limit": str(LIMIT),
    }
    for attempt in range(6):
        try:
            r = requests.get(BASE, params=params, timeout=30)
            r.raise_for_status()
            j = r.json()
            if j.get("code") != "00000":
                raise RuntimeError(f"API error: {j}")
            return j.get("data") or []
        except Exception as e:
            wait = 1.5 * (attempt + 1)
            print(f"  retry {attempt+1}: {e}; sleep {wait}s")
            time.sleep(wait)
    return []


def download_symbol(symbol: str, start_ms: int, end_ms: int) -> pd.DataFrame:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    pkl = CACHE_DIR / f"{symbol}_1m.pkl"
    csv_path = DATA_DIR / f"{symbol}_1m.csv"

    if pkl.exists():
        df = pd.read_pickle(pkl)
        print(f"{symbol}: loaded cache {len(df)} rows {df['ts'].min()} .. {df['ts'].max()}")
        existing_min = int(df["ts"].min().timestamp() * 1000)
        if existing_min <= start_ms and len(df) > 1000:
            return df[df["ts"] >= pd.to_datetime(start_ms, unit="ms", utc=True)].copy()
        print(f"{symbol}: cache incomplete, re-downloading...")

    rows = []
    cursor = end_ms
    batches = 0
    while cursor > start_ms:
        data = fetch_batch(symbol, cursor)
        batches += 1
        if not data:
            print(f"{symbol}: empty batch at endTime={cursor}, stop")
            break
        for item in data:
            ts = int(item[0])
            if ts < start_ms:
                continue
            rows.append({
                "ts_ms": ts,
                "open": float(item[1]),
                "high": float(item[2]),
                "low": float(item[3]),
                "close": float(item[4]),
                "volume": float(item[5]),
            })
        oldest = min(int(x[0]) for x in data)
        next_cursor = oldest - 1
        if next_cursor >= cursor:
            print(f"{symbol}: cursor not advancing, stop")
            break
        cursor = next_cursor
        if batches % 50 == 0:
            print(f"{symbol}: batches={batches}, rows={len(rows)}, "
                  f"oldest={datetime.fromtimestamp(oldest/1000, tz=timezone.utc)}")
        time.sleep(SLEEP)
        if batches > 500:
            print(f"{symbol}: hit batch safety cap")
            break

    if not rows:
        raise RuntimeError(f"No data for {symbol}")

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["ts_ms"]).sort_values("ts_ms").reset_index(drop=True)
    df["ts"] = pd.to_datetime(df["ts_ms"], unit="ms", utc=True)
    df = df[["ts", "open", "high", "low", "close", "volume", "ts_ms"]]
    df.to_pickle(pkl)
    df.to_csv(csv_path, index=False)
    print(f"{symbol}: saved {len(df)} candles {df['ts'].iloc[0]} .. {df['ts'].iloc[-1]}")
    return df


def main():
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=DAYS)
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    print(f"Downloading {DAYS}d 1m candles from {start} to {end}")
    for sym in SYMBOLS:
        download_symbol(sym, start_ms, end_ms)
    print("Done.")


if __name__ == "__main__":
    main()
