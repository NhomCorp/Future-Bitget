import pandas as pd, numpy as np
pd.set_option("display.width",260); pd.set_option("display.max_columns",50)
keys=["mode","cap","layers","spm","step","mult","tp","part","filt","stop"]
def wide(f,tag):
    g=pd.read_csv(f); w=g.pivot_table(index=keys,columns="sym",values=["ret","mdd","liq","seg1","seg2","seg3","per_day","nstop","worst","fees","gross","tim"]).reset_index()
    w.columns=[("_".join([c for c in col if c])) for col in w.columns]
    w=w.set_index(keys); w.columns=[f"{tag}_{c}" for c in w.columns]; return w
A=wide("results/grid_A_bear.csv","A"); B=wide("results/grid_B_bull.csv","B"); F=wide("results/grid_full180.csv","F")
W=A.join(B).join(F)
for t in "ABF":
    W[f"{t}_liq"]=W[[f"{t}_liq_BTC",f"{t}_liq_ETH"]].max(axis=1); W[f"{t}_minret"]=W[[f"{t}_ret_BTC",f"{t}_ret_ETH"]].min(axis=1)
    W[f"{t}_maxdd"]=W[[f"{t}_mdd_BTC",f"{t}_mdd_ETH"]].max(axis=1)
W["F_minseg"]=W[[f"F_seg{i}_{s}" for i in (1,2,3) for s in ("BTC","ETH")]].min(axis=1)
W["robust"]=W[["A_minret","B_minret"]].min(axis=1)
W["noliq"]=(W.A_liq+W.B_liq+W.F_liq)==0
W.to_pickle("results/W.pkl")
R=W[W.noliq].reset_index()
print("total sets",len(W),"no-liq in A,B,F:",len(R),"profitable both coins in bear AND bull:",(R.robust>0).sum())
print(R.groupby("mode").agg(n=("robust","size"),pos=("robust",lambda x:(x>0).sum()),best=("robust","max")))
cols=keys+["A_ret_BTC","A_ret_ETH","B_ret_BTC","B_ret_ETH","F_ret_BTC","F_ret_ETH","F_maxdd","F_minseg","F_per_day_BTC","F_per_day_ETH","F_nstop_BTC","F_nstop_ETH"]
R["score"]=R.robust-0.3*R.F_maxdd
print(R[R.robust>0].sort_values("score",ascending=False)[cols].head(30).round(1).to_string())
