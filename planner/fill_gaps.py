import pandas as pd, requests, time
for s in ["BTCUSDT","ETHUSDT"]:
    d=pd.read_pickle(f"data/{s}_1m.pkl"); have=set(d.ts_ms); g=d.ts_ms.diff()
    miss=[int(t-60000) for t in d.ts_ms[g==120000]]; rows=[]
    for m in miss:
        j=requests.get("https://api.bitget.com/api/v2/mix/market/history-candles",params=dict(symbol=s,productType="USDT-FUTURES",granularity="1m",endTime=str(m+60000),limit="5"),timeout=20).json()
        for x in j.get("data") or []:
            if int(x[0])==m: rows.append([m]+[float(v) for v in x[1:6]])
        time.sleep(0.05)
    add=pd.DataFrame(rows,columns=["ts_ms","open","high","low","close","volume"])
    d=pd.concat([d,add]).drop_duplicates("ts_ms").sort_values("ts_ms").reset_index(drop=True)
    d.to_pickle(f"data/{s}_1m.pkl"); print(s,len(miss),"filled",len(add),"gaps now",int((d.ts_ms.diff()>60000).sum()))
