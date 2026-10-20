import pandas as pd, numpy as np
pd.set_option("display.width",260); pd.set_option("display.max_columns",50)
W=pd.read_pickle("results/W.pkl").reset_index()
W["spc"]=W.spm.astype(str)+"_"+W.step.astype(str)
axes={"cap":[3,5,8,10],"layers":[5,7,10],"mult":[1.0,1.15,1.3],"tp":[.3,.5,.8],"stop":[0,10,15,20],"part":[0,.5],"filt":[0,1,2,3]}
spc_axes={"1":[.5,1.,1.5],"0":[.4,.8,1.2]}
W["rob"]=np.where(W.noliq,W[["A_minret","B_minret"]].min(axis=1),-100)
idx={tuple(r):i for i,r in enumerate(W[["mode","cap","layers","spm","step","mult","tp","part","filt","stop"]].itertuples(index=False))}
rob=W.rob.values; res=[]
for i,r in enumerate(W.itertuples(index=False)):
    if r.mode=="short": res.append((np.nan,np.nan,0)); continue
    base=dict(mode=r.mode,cap=r.cap,layers=r.layers,spm=r.spm,step=r.step,mult=r.mult,tp=r.tp,part=r.part,filt=r.filt,stop=r.stop)
    nb=[]
    def add(d):
        j=idx.get((d["mode"],d["cap"],d["layers"],d["spm"],d["step"],d["mult"],d["tp"],d["part"],d["filt"],d["stop"]))
        if j is not None: nb.append(rob[j])
    for k,vals in list(axes.items())+[("step",spc_axes[str(int(r.spm))])]:
        v=base[k]; vi=[x for x in vals if abs(x-v)<1e-9]
        if not vi: continue
        p=vals.index(vi[0])
        for q in (p-1,p+1):
            if 0<=q<len(vals): d=dict(base); d[k]=vals[q]; add(d)
    nb=np.array(nb); res.append((np.median(nb),np.mean(nb>0),np.mean(nb>-10)))
W[["nb_med","nb_pos","nb_okish"]]=pd.DataFrame(res,index=W.index)
W["final_score"]=0.5*W.rob.clip(upper=60)+0.5*W.nb_med.clip(upper=60)-0.25*W.F_maxdd
W.to_pickle("results/W2.pkl")
cols=["mode","cap","layers","spm","step","mult","tp","part","filt","stop","rob","nb_med","nb_pos","A_ret_BTC","A_ret_ETH","B_ret_BTC","B_ret_ETH","F_ret_BTC","F_ret_ETH","F_maxdd","F_per_day_BTC","F_per_day_ETH","F_nstop_BTC","F_nstop_ETH","F_worst_BTC","F_worst_ETH","F_tim_BTC"]
c=W[(W.rob>0)&(W.nb_med>-5)].sort_values("final_score",ascending=False)
print(c[cols].head(30).round(1).to_string())
print("\nlow-exposure (cap<=5):")
print(W[(W.rob>0)&(W.cap<=5)].sort_values("final_score",ascending=False)[cols].head(12).round(1).to_string())
print("\nlong-only:")
print(W[(W.rob>0)&(W["mode"]=="long")].sort_values("final_score",ascending=False)[cols].head(8).round(1).to_string())
