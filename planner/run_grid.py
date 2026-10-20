#!/usr/bin/env python3
"""Grid backtest of DCA ladder variants on 90d 1m BTC & ETH. Output results/grid.csv"""
import numpy as np, pandas as pd, itertools, os, time, sys
from multiprocessing import Pool
import sim
E0=524.87; MAKER=0.0002; TAKER=0.0006; FUND=0.0001; REC=60
DDIR=os.environ.get('DDIR','/workspace/bitget/planner/data'); T0=os.environ.get('T0'); T1=os.environ.get('T1')
ts,O,H,L,C,I=sim.load(ddir=DDIR,t0=int(T0) if T0 else None,t1=int(T1) if T1 else None)
OUTF=os.environ.get('OUTF','results/grid.csv')
MMR=np.array([0.004,0.005])
T=O.shape[1]; seg_edges=[0,T//3,2*T//3,T]
def one(args):
    sym,mode,p=args
    legsym=np.array([sym]*(2 if mode=="both" else 1),dtype=np.int64)
    legside=np.array([1,-1] if mode=="both" else ([1] if mode=="long" else [-1]),dtype=np.int64)
    st,rec,cyc,cyct,cycd=sim.run(ts,O,H,L,C,I["atr1h"],I["ema1h"],I["adx4h"],I["pdi4h"],I["ndi4h"],I["FR"],legsym,legside,np.array(p,dtype=np.float64),E0,MAKER,TAKER,MMR,REC)
    segs=[]
    for a,b in zip(seg_edges[:-1],seg_edges[1:]):
        ra,rb=rec[min(a//REC,len(rec)-1)],rec[min(b//REC,len(rec)-1)]
        segs.append((rb/ra-1)*100 if ra>0 else -100)
    days=T/1440
    return dict(sym=["BTC","ETH"][sym],mode=mode,cap=p[0],layers=p[1],spm=p[2],step=p[3],grow=p[4],mult=p[5],tp=p[6],part=p[7],filt=p[9],stop=p[12],
        final=st[0],ret=(st[0]/E0-1)*100,mdd=st[1]*100,fees=st[2],fund=st[3],gross=st[4],liq=int(st[5]),ncyc=int(st[7]),nstop=int(st[8]),
        wr=st[9]/max(st[7],1)*100,worst=st[10],tim=st[12]*100,maxlev=st[13],mmrmax=st[14]*100,per_day=(st[0]-E0)/days,
        seg1=segs[0],seg2=segs[1],seg3=segs[2])
def grid():
    out=[]
    for cap,lay,(spm,step),grow,mult,tp,part,filt,stop in itertools.product([3,5,8,10],[5,7,10],[(1,.5),(1,1.),(1,1.5),(0,.4),(0,.8),(0,1.2)],[1.0],[1.0,1.15,1.3],[.3,.5,.8],[0,.5],[0,1,2,3],[0,10,15,20]):
        out.append([cap,lay,spm,step,grow,mult,tp,part,2.0,filt,30.0,1.0,stop,1,4.0])
    return out
if __name__=="__main__":
    os.makedirs("results",exist_ok=True)
    G=grid(); jobs=[(s,m,p) for s in (0,1) for m in ("long","short","both") for p in G]
    print("jobs",len(jobs),"bars",T, pd.to_datetime(ts[0],unit='ms'),pd.to_datetime(ts[-1],unit='ms'),flush=True)
    one(jobs[0]); t0=time.time()
    with Pool(7) as pool: R=pool.map(one,jobs,chunksize=200)
    pd.DataFrame(R).to_csv(OUTF,index=False); print("done",time.time()-t0)
