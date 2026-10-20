#!/usr/bin/env python3
"""Evaluate shortlisted plans in ONE cross account holding BTC+ETH ladders together (4 legs: BTC L/S, ETH L/S),
over 180d and each 90d half (bear Apr-Jul / bull Jul-Oct). Writes results/final_*.csv/json and equity PNG."""
import numpy as np, pandas as pd, json, sim, os
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
E0=524.87; VND=26000; MAKER=0.0002; TAKER=0.0006; MMR=np.array([0.004,0.005]); REC=60
def P(cap,lay,spm,step,grow,mult,tp,part,filt,stop,adx=30,z=1.0): return [cap,lay,spm,step,grow,mult,tp,part,2.0,filt,adx,z,stop,1,8.0]
# cap here = TOTAL account cap across all 4 legs (each leg gets cap/4)
CANDS={
 "DEFAULT cap 5x, 5 lop 1.5%, deu, TP1.2% (50%) rest 2.4%/BE, stop -7%/leg": P(5,5,0,1.5,1.0,1.0,1.2,0.5,0,7),
 "SAFER   cap 3x, same ladder, stop -5%/leg": P(3,5,0,1.5,1.0,1.0,1.2,0.5,0,5),
 "AGGR    cap 8x, same ladder, stop -7%/leg": P(8,5,0,1.5,1.0,1.0,1.2,0.5,0,7),
 "REF user-like micro grid cap 8x, 10 lop 0.2%, TP0.3%, stop -10%": P(8,10,0,0.2,1.0,1.0,0.3,0.0,0,10),
 "REF user-like micro grid cap 8x, NO stop": P(8,10,0,0.2,1.0,1.0,0.3,0.0,0,0),
}
LS=np.array([0,0,1,1],dtype=np.int64); SD=np.array([1,-1,1,-1],dtype=np.int64)
def evaluate(data,name,p):
    ts,O,H,L,C,I=data
    st,rec,cyc,cyct,cycd=sim.run(ts,O,H,L,C,I["atr1h"],I["ema1h"],I["adx4h"],I["pdi4h"],I["ndi4h"],I["FR"],LS,SD,np.array(p,float),E0,MAKER,TAKER,MMR,REC)
    days=O.shape[1]/1440; ix=ts[::REC]; rec=rec[:len(ix)]; eq=pd.Series(rec,index=pd.to_datetime(ts[::REC][:len(rec)],unit="ms",utc=True).tz_convert("Asia/Ho_Chi_Minh"))
    daily=eq.resample("1D").last().diff().dropna()
    gross=st[4]; fees=st[2]
    return dict(plan=name,final=round(st[0],1),ret_pct=round((st[0]/E0-1)*100,1),maxdd_pct=round(st[1]*100,1),liquidated=bool(st[5]),
        fees=round(fees,1),funding=round(st[3],1),gross_trading=round(gross,1),fee_share_pct=round(fees/gross*100,1) if gross>0 else None,
        cycles=int(st[7]),stops=int(st[8]),winrate=round(st[9]/max(st[7],1)*100,1),worst_cycle=round(st[10],1),best_cycle=round(st[11],1),
        time_in_mkt_pct=round(st[12]*100,1),max_notional_x_eq=round(st[13],1),max_mm_ratio_pct=round(st[14]*100,2),
        per_day_usdt=round((st[0]-E0)/days,2),per_day_vnd=int((st[0]-E0)/days*VND),
        days_pos_pct=round((daily>0).mean()*100,1),worst_day=round(daily.min(),1),best_day=round(daily.max(),1),
        days_ge_700k_pct=round((daily*VND>=700000).mean()*100,1)),eq
if __name__=="__main__":
    full=sim.load(ddir="data180"); ts=full[0]; m=ts[0]+(ts[-1]-ts[0])//2
    halves={"A_bear(04-22..07-21)":sim.load(ddir="data180",t0=int(ts[0]),t1=int(m)),"B_bull(07-21..10-20)":sim.load(ddir="data180",t0=int(m),t1=int(ts[-1])+60000)}
    rows=[]; curves={}
    for n,p in CANDS.items():
        r,eq=evaluate(full,n,p); r["period"]="180d"; rows.append(r); curves[n]=eq
        for hn,hd in halves.items():
            r2,_=evaluate(hd,n,p); r2["period"]=hn; rows.append(r2)
    df=pd.DataFrame(rows); os.makedirs("results",exist_ok=True); df.to_csv("results/final_eval.csv",index=False)
    pd.set_option("display.width",300); pd.set_option("display.max_columns",40)
    print(df.to_string())
    fig,ax=plt.subplots(2,1,figsize=(13,9),sharex=True,gridspec_kw=dict(height_ratios=[3,1]))
    btc=pd.Series(full[4][0][::REC],index=curves[list(curves)[0]].index[:len(full[4][0][::REC])])
    for n in list(CANDS)[:4]:
        ax[0].plot(curves[n].index,curves[n].values,label=n,lw=1.3 if not n.startswith("REF") else 0.9,ls="-" if not n.startswith("REF") else "--")
    ax[0].axhline(E0,color="k",lw=.6); ax[0].set_ylabel("Equity USDT (start 524.87)"); ax[0].legend(fontsize=8); ax[0].grid(alpha=.3)
    ax[0].set_title("DCA ladder plans – one cross account BTC+ETH hedge, 1m backtest 180d, fees+funding, stop & liq modelled")
    ax[1].plot(btc.index,btc.values/btc.values[0]*100,label="BTC",color="orange"); eth=full[4][1][::REC]; ax[1].plot(btc.index,eth[:len(btc)]/eth[0]*100,label="ETH",color="purple")
    ax[1].legend(fontsize=8); ax[1].set_ylabel("Price idx=100"); ax[1].grid(alpha=.3); ax[1].set_xlabel("Asia/Saigon (UTC+7)")
    plt.tight_layout(); plt.savefig("equity_top3.png",dpi=110); print("PNG saved")
