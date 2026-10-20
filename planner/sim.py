"""Numba DCA-ladder simulator, cross margin, multi-leg (long/short, BTC/ETH) sharing one equity.
Bar order (conservative): fills of adverse layers -> hard stop -> liquidation check at adverse extremes
(each leg at its own worst extreme) -> TP on favorable extreme -> funding -> new ladder entry at close."""
import numpy as np, pandas as pd
from numba import njit
MAXL=12
def load(syms=("BTCUSDT","ETHUSDT"),ddir="/workspace/bitget/planner/data",t0=None,t1=None):
    ds=[pd.read_pickle(f"{ddir}/{s}_1m.pkl").set_index("ts_ms") for s in syms]
    if t0 is not None: ds=[d[(d.index>=t0)&(d.index<t1)] for d in ds]
    idx=ds[0].index
    for d in ds[1:]: idx=idx.intersection(d.index)
    ds=[d.loc[idx] for d in ds]
    O=np.stack([d.open.values for d in ds]);H=np.stack([d.high.values for d in ds]);L=np.stack([d.low.values for d in ds]);C=np.stack([d.close.values for d in ds])
    ind=[indicators(d) for d in ds]
    import json; fj=json.load(open("/workspace/bitget/planner/data/funding.json"))
    FR=np.zeros((len(syms),len(idx)))
    pos={int(v):i for i,v in enumerate(idx)}
    for j,sy in enumerate(syms):
        for x in fj[sy]:
            i=pos.get(int(x["fundingTime"]))
            if i is not None: FR[j,i]=float(x["fundingRate"])
    I={k:np.stack([x[k] for x in ind]) for k in ind[0]}
    I['FR']=FR
    return np.asarray(idx,dtype=np.int64),O,H,L,C,I
def _wilder(x,n): return x.ewm(alpha=1/n,adjust=False).mean()
def indicators(d):
    t=pd.to_datetime(d.index,unit="ms")
    df=d.copy(); df.index=t
    out={}
    for tf,name in (("1h","1h"),("4h","4h")):
        r=df.resample(tf,label="left",closed="left").agg(dict(open="first",high="max",low="min",close="last")).dropna()
        pc=r.close.shift()
        tr=pd.concat([r.high-r.low,(r.high-pc).abs(),(r.low-pc).abs()],axis=1).max(axis=1)
        atr=_wilder(tr,14)
        up=r.high.diff(); dn=-r.low.diff()
        pdm=np.where((up>dn)&(up>0),up,0.0); ndm=np.where((dn>up)&(dn>0),dn,0.0)
        pdi=100*_wilder(pd.Series(pdm,r.index),14)/atr; ndi=100*_wilder(pd.Series(ndm,r.index),14)/atr
        adx=_wilder(100*(pdi-ndi).abs()/(pdi+ndi).replace(0,np.nan),14)
        ema=r.close.ewm(span=50,adjust=False).mean()
        f=pd.DataFrame(dict(atr=atr,pdi=pdi,ndi=ndi,adx=adx,ema=ema))
        # value known only after bar closes -> shift index to bar close time
        f.index=f.index+pd.Timedelta(tf)
        f=f.reindex(t,method="ffill").bfill()
        for k in f: out[f"{k}{name}"]=f[k].values.astype(np.float64)
    return out
# params vector indices
P_CAP,P_LAY,P_SPM,P_STEP,P_GROW,P_MULT,P_TP,P_PART,P_TP2,P_FILT,P_ADX,P_Z,P_STOP,P_CD,P_MAXSTEP=range(15)
@njit(cache=True)
def run(ts,O,H,L,C,atr1,ema1,adx4,pdi4,ndi4,FR,legsym,legside,par,E0,maker,taker,mmr,rec_every):
    K=legsym.shape[0]; T=O.shape[1]
    cap=par[0]; nl=int(par[1]); spm=int(par[2]); step=par[3]; grow=par[4]; mult=par[5]; tp=par[6]/100
    part=par[7]; tp2=par[8]; filt=int(par[9]); adxt=par[10]; z=par[11]; stop=par[12]/100; cd=int(par[13]); maxstep=par[14]/100
    act=np.zeros(K,np.int64); nf=np.zeros(K,np.int64); lv=np.zeros((K,MAXL)); lq=np.zeros((K,MAXL))
    Q=np.zeros(K); Cst=np.zeros(K); Es=np.zeros(K); pdone=np.zeros(K,np.int64); A0=np.zeros(K); last_exit=np.full(K,-10**9)
    cyc_pnl=np.zeros(K); cyc_start=np.zeros(K,np.int64)
    cash=E0; fees=0.0; fund=0.0; peak=E0; mdd=0.0; liq=0; liq_t=-1
    ncyc=0; nstop=0; nwin=0; worst=0.0; best=0.0; inmkt=0; maxlev=0.0; grossp=0.0; mmr_max=0.0
    nrec=T//rec_every+1; rec=np.zeros(nrec); ri=0
    cycs=np.zeros(20000); cyct=np.zeros(20000,np.int64); cycd=np.zeros(20000,np.int64)
    for t in range(T):
        any_act=False
        for k in range(K):
            if act[k]==0: continue
            any_act=True
            s=legsym[k]; sg=legside[k]
            blocked=False
            if (filt==1 or filt==3) and adx4[s,t]>adxt and ((sg==1 and ndi4[s,t]>pdi4[s,t]) or (sg==-1 and pdi4[s,t]>ndi4[s,t])): blocked=True
            if pdone[k]==0 and not blocked:
                while nf[k]<nl and ((sg==1 and L[s,t]<=lv[k,nf[k]]) or (sg==-1 and H[s,t]>=lv[k,nf[k]])):
                    p=lv[k,nf[k]]; q=lq[k,nf[k]]; Q[k]+=q; Cst[k]+=q*p; f=q*p*maker; cash-=f; fees+=f; cyc_pnl[k]-=f; nf[k]+=1
            # hard stop
            if stop>0 and Q[k]>0:
                A=Cst[k]/Q[k]; sp=A-sg*stop*Es[k]/Q[k]
                if (sg==1 and L[s,t]<=sp) or (sg==-1 and H[s,t]>=sp):
                    px=min(sp,O[s,t]) if sg==1 else max(sp,O[s,t])
                    pn=sg*(px-A)*Q[k]; f=px*Q[k]*taker; cash+=pn-f; fees+=f; cyc_pnl[k]+=pn-f; grossp+=pn
                    if ncyc<20000: cycs[ncyc]=cyc_pnl[k]; cyct[ncyc]=t; cycd[ncyc]=t-cyc_start[k]
                    ncyc+=1; nstop+=1; worst=min(worst,cyc_pnl[k]); act[k]=0; Q[k]=0; Cst[k]=0; last_exit[k]=t
        # liquidation check at adverse extremes
        up=0.0; mm=0.0; notl=0.0
        for k in range(K):
            if act[k]==0 or Q[k]==0: continue
            s=legsym[k]; sg=legside[k]; px=L[s,t] if sg==1 else H[s,t]
            up+=sg*(px*Q[k]-Cst[k]); mm+=mmr[s]*px*Q[k]; notl+=px*Q[k]
        eqw=cash+up
        if notl>0:
            if eqw>0: maxlev=max(maxlev,notl/eqw); mmr_max=max(mmr_max,mm/eqw)
            if eqw<=mm:
                liq=1; liq_t=t; cash=0.0; mdd=1.0
                for k in range(K):
                    if act[k]==1:
                        if ncyc<20000: cycs[ncyc]=-1e9; cyct[ncyc]=t
                        ncyc+=1
                break
        if eqw>peak: pass
        dd=(peak-eqw)/peak
        if dd>mdd: mdd=dd
        # TP / scale-out
        for k in range(K):
            if act[k]==0 or Q[k]==0: continue
            s=legsym[k]; sg=legside[k]; A=Cst[k]/Q[k]
            if pdone[k]==1:
                # remainder: breakeven stop (taker) adverse-first, else TP2 from original avg
                if (sg==1 and L[s,t]<=A0[k]) or (sg==-1 and H[s,t]>=A0[k]):
                    px=A0[k]; pn=sg*(px-A)*Q[k]; f=px*Q[k]*taker
                else:
                    tg=A0[k]*(1+sg*tp*tp2)
                    if (sg==1 and H[s,t]>=tg) or (sg==-1 and L[s,t]<=tg):
                        px=tg; pn=sg*(px-A)*Q[k]; f=px*Q[k]*maker
                    else: continue
                cash+=pn-f; fees+=f; cyc_pnl[k]+=pn-f; grossp+=pn
                if ncyc<20000: cycs[ncyc]=cyc_pnl[k]; cyct[ncyc]=t; cycd[ncyc]=t-cyc_start[k]
                ncyc+=1; worst=min(worst,cyc_pnl[k]); best=max(best,cyc_pnl[k])
                if cyc_pnl[k]>0: nwin+=1
                act[k]=0; Q[k]=0; Cst[k]=0; last_exit[k]=t; continue
            tg=A*(1+sg*tp)
            if (sg==1 and H[s,t]>=tg) or (sg==-1 and L[s,t]<=tg):
                fr=part if part>0 else 1.0
                q=Q[k]*fr; pn=sg*(tg-A)*q; f=tg*q*maker
                cash+=pn-f; fees+=f; cyc_pnl[k]+=pn-f; grossp+=pn
                if fr<1.0:
                    Q[k]-=q; Cst[k]=A*Q[k]; pdone[k]=1; A0[k]=A
                else:
                    if ncyc<20000: cycs[ncyc]=cyc_pnl[k]; cyct[ncyc]=t; cycd[ncyc]=t-cyc_start[k]
                    ncyc+=1; worst=min(worst,cyc_pnl[k]); best=max(best,cyc_pnl[k])
                    if cyc_pnl[k]>0: nwin+=1
                    act[k]=0; Q[k]=0; Cst[k]=0; last_exit[k]=t
        # funding at settlement minutes: actual historical rate, long pays / short receives
        for k in range(K):
            r=FR[legsym[k],t]
            if r!=0.0 and act[k]==1 and Q[k]>0:
                f=legside[k]*r*C[legsym[k],t]*Q[k]; cash-=f; fund+=f; cyc_pnl[k]-=f
        # equity at close
        eqc=cash
        for k in range(K):
            if act[k]==1: eqc+=legside[k]*(C[legsym[k],t]*Q[k]-Cst[k])
        if eqc>peak: peak=eqc
        # new ladders
        for k in range(K):
            if act[k]==1 or t-last_exit[k]<cd: continue
            s=legsym[k]; sg=legside[k]; c=C[s,t]; a=atr1[s,t]
            if a!=a or a<=0: continue
            if (filt==1 or filt==3) and adx4[s,t]>adxt and ((sg==1 and ndi4[s,t]>pdi4[s,t]) or (sg==-1 and pdi4[s,t]>ndi4[s,t])): continue
            if filt>=2:
                zz=(c-ema1[s,t])/a
                if (sg==1 and zz>-z) or (sg==-1 and zz<z): continue
            base=step/100 if spm==0 else step*a/c
            if base<0.0025: base=0.0025
            if maxstep>0 and base>maxstep: base=maxstep
            tot=cap*eqc/K; ws=0.0
            for i in range(nl): ws+=mult**i
            p=c
            for i in range(nl):
                if i>0: p=p*(1-sg*base*grow**(i-1))
                lv[k,i]=p; lq[k,i]=tot*(mult**i)/ws/p
            # first layer fills now at close (post-only at touch)
            q=lq[k,0]; Q[k]=q; Cst[k]=q*c; f=q*c*maker; cash-=f; fees+=f
            nf[k]=1; act[k]=1; pdone[k]=0; Es[k]=eqc; cyc_pnl[k]=-f; cyc_start[k]=t
        if any_act: inmkt+=1
        if t%rec_every==0 and ri<nrec: rec[ri]=eqc; ri+=1
    if liq==1:
        while ri<nrec: rec[ri]=0.0; ri+=1
    else:
        eqf=cash
        for k in range(K):
            if act[k]==1: eqf+=legside[k]*(C[legsym[k],T-1]*Q[k]-Cst[k])
        cash=eqf
    st=np.array([cash,mdd,fees,fund,grossp,liq,liq_t,ncyc,nstop,nwin,worst,best,inmkt/T,maxlev,mmr_max])
    n=min(ncyc,20000)
    return st,rec[:ri],cycs[:n],cyct[:n],cycd[:n]
