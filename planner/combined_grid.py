"""Robustness: neighbourhood grid around the chosen plans, in the combined BTC+ETH 4-leg cross account, per 90d half + monthly."""
import numpy as np, pandas as pd, itertools, sim
from multiprocessing import Pool
E0=524.87; MMR=np.array([0.004,0.005]); LS=np.array([0,0,1,1],dtype=np.int64); SD=np.array([1,-1,1,-1],dtype=np.int64)
full=sim.load(ddir="data180"); ts=full[0]; mid=ts[0]+(ts[-1]-ts[0])//2
H={"A":sim.load(ddir="data180",t0=int(ts[0]),t1=int(mid)),"B":sim.load(ddir="data180",t0=int(mid),t1=int(ts[-1])+60000)}
def one(p):
    out={}
    for k,(ts_,O,Hh,L,C,I) in H.items():
        st,rec,*_=sim.run(ts_,O,Hh,L,C,I["atr1h"],I["ema1h"],I["adx4h"],I["pdi4h"],I["ndi4h"],I["FR"],LS,SD,np.array(p,float),E0,0.0002,0.0006,MMR,60)
        out[k+"_ret"]=(st[0]/E0-1)*100; out[k+"_dd"]=st[1]*100; out[k+"_liq"]=st[5]
        m=rec[:len(ts_[::60])][::720]  # 30d chunks
        out[k+"_worst30"]=min((m[i+1]/m[i]-1)*100 if m[i]>0 else -100 for i in range(len(m)-1)) if len(m)>1 else np.nan
    return out
G=list(itertools.product([5,8,10],[5,7,10],[0.6,1.0,1.5,2.0],[1.0,1.3],[0.5,0.8,1.2],[0,0.5],[0,1],[10,15,20]))
P=[[c,l,0,s,1.0,m,tp,pt,2.0,f,30,1.0,st,1,8.0] for c,l,s,m,tp,pt,f,st in G]
if __name__=="__main__":
    with Pool(7) as pool: R=pool.map(one,P,chunksize=20)
    df=pd.concat([pd.DataFrame(G,columns=["cap","layers","step","mult","tp","part","filt","stop"]),pd.DataFrame(R)],axis=1)
    df["min_ret"]=df[["A_ret","B_ret"]].min(axis=1); df["maxdd"]=df[["A_dd","B_dd"]].max(axis=1); df["worst30"]=df[["A_worst30","B_worst30"]].min(axis=1)
    df.to_csv("results/combined_grid.csv",index=False)
    print("sets",len(df),"liq any",int((df.A_liq+df.B_liq>0).sum()),"both halves >0:",round((df.min_ret>0).mean()*100,1),"%  median min_ret",round(df.min_ret.median(),1))
    for k in ["cap","layers","step","mult","tp","part","filt","stop"]:
        print(k,df.groupby(k).agg(pos=("min_ret",lambda x:round((x>0).mean()*100)),med=("min_ret","median"),dd=("maxdd","median"),w30=("worst30","median")).round(1).to_dict("index"))
    pd.set_option("display.width",250)
    print(df.sort_values("min_ret",ascending=False).head(15).round(1).to_string())
