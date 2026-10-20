import pandas as pd, numpy as np, sys
pd.set_option("display.width",260); pd.set_option("display.max_columns",50)
keys=["mode","cap","layers","spm","step","grow","mult","tp","part","filt","stop"]
def wide(f,tag):
    g=pd.read_csv(f); w=g.pivot_table(index=keys,columns="sym",values=["ret","mdd","liq","per_day","nstop","worst","fees","gross","tim","ncyc"]).reset_index()
    w.columns=[("_".join([c for c in col if c])) for col in w.columns]; w=w.set_index(keys); w.columns=[f"{tag}_{c}" for c in w.columns]; return w
W=wide(sys.argv[1],"A").join(wide(sys.argv[2],"B"))
for t in "AB":
    W[f"{t}_liq"]=W[[f"{t}_liq_BTC",f"{t}_liq_ETH"]].max(axis=1); W[f"{t}_maxdd"]=W[[f"{t}_mdd_BTC",f"{t}_mdd_ETH"]].max(axis=1)
W["rob"]=np.where((W.A_liq+W.B_liq)==0,W[["A_ret_BTC","A_ret_ETH","B_ret_BTC","B_ret_ETH"]].min(axis=1),-100)
W["avg"]=W[["A_ret_BTC","A_ret_ETH","B_ret_BTC","B_ret_ETH"]].mean(axis=1)
W["maxdd"]=W[["A_maxdd","B_maxdd"]].max(axis=1)
W=W.reset_index(); W.to_pickle(sys.argv[3])
print("sets",len(W),"rob>0",(W.rob>0).sum(), "by mode:",W[W.rob>0]["mode"].value_counts().to_dict())
for m in ["both","long","short"]:
    X=W[W["mode"]==m]; print("==",m,"median rob",X.rob.median(),"median avg",round(X.avg.median(),1))
    for k in ["cap","layers","step","grow","mult","tp","part","filt","stop"]:
        print("  ",k,X.groupby(k).agg(rob=("rob","median"),avg=("avg","median"),pos=("rob",lambda x:round((x>0).mean(),3))).round(1).to_dict("index"))
cols=keys+["rob","avg","maxdd","A_ret_BTC","A_ret_ETH","B_ret_BTC","B_ret_ETH","A_nstop_BTC","A_nstop_ETH","B_per_day_BTC","B_per_day_ETH"]
print(W[W.rob>0].sort_values("rob",ascending=False)[cols].head(25).round(1).to_string())
