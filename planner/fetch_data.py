#!/usr/bin/env python3
"""Extend cached 1m candles to ~90 days (public history-candles, no auth). Output data/{SYM}_1m.pkl"""
import time, requests, pandas as pd, sys
from pathlib import Path
BASE="https://api.bitget.com/api/v2/mix/market/history-candles"
OLD=Path("/workspace/bitget/backtest/cache"); OUT=Path(__file__).parent/"data"
DAYS=int(sys.argv[1]) if len(sys.argv)>1 else 90
def batch(sym,end):
    for a in range(6):
        try:
            j=requests.get(BASE,params=dict(symbol=sym,productType="USDT-FUTURES",granularity="1m",endTime=str(end),limit="200"),timeout=30).json()
            if j.get("code")=="00000": return j["data"] or []
        except Exception as e: pass
        time.sleep(1.5*(a+1))
    return []
def rng(sym,start,end):
    rows=[];cur=end
    while cur>start:
        d=batch(sym,cur)
        if not d: break
        rows+= [[int(x[0])]+[float(v) for v in x[1:6]] for x in d if int(x[0])>=start]
        o=min(int(x[0]) for x in d)
        if o>=cur: break
        cur=o; time.sleep(0.08)
    return pd.DataFrame(rows,columns=["ts_ms","open","high","low","close","volume"])
now=int(time.time()//60*60*1000); start=now-DAYS*86400000
for sym in ["BTCUSDT","ETHUSDT"]:
    old=pd.read_pickle(OLD/f"{sym}_1m.pkl")
    old=old[["ts_ms","open","high","low","close","volume"]] if "ts_ms" in old else old
    o0,o1=int(old.ts_ms.min()),int(old.ts_ms.max())
    parts=[old]
    if start<o0: parts.append(rng(sym,start,o0-1))
    parts.append(rng(sym,o1+1,now))
    df=pd.concat(parts).drop_duplicates("ts_ms").sort_values("ts_ms")
    df=df[df.ts_ms>=start].reset_index(drop=True)
    df.to_pickle(OUT/f"{sym}_1m.pkl")
    print(sym,len(df),pd.to_datetime(df.ts_ms.min(),unit='ms'),pd.to_datetime(df.ts_ms.max(),unit='ms'),"gaps>1m:",int((df.ts_ms.diff()>60000).sum()))
