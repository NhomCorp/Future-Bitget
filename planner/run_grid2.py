#!/usr/bin/env python3
"""Stage-2 grid: wider / geometric ladders, lower caps. Same engine as run_grid."""
import itertools, os, time, pandas as pd
from multiprocessing import Pool
import run_grid as R
def grid():
    out=[]
    for cap,lay,(spm,step),grow,mult,tp,part,filt,stop in itertools.product([2,3,5],[5,7,10],[(0,1.5),(0,2.0),(0,2.5),(1,2.0),(1,3.0),(0,0.6),(0,1.0)],[1.0,1.25,1.5],[1.0,1.3,1.6],[.5,.8,1.2],[0,.5],[0,1,2,3],[10,20,30]):
        if step*grow**(lay-2)*(lay-1)>60 and spm==0: continue
        out.append([cap,lay,spm,step,grow,mult,tp,part,2.0,filt,30.0,1.0,stop,1,8.0])
    return out
if __name__=="__main__":
    G=grid(); jobs=[(s,m,p) for s in (0,1) for m in ("long","short","both") for p in G]
    print("jobs",len(jobs),flush=True); t0=time.time()
    with Pool(7) as pool: Rr=pool.map(R.one,jobs,chunksize=200)
    df=pd.DataFrame(Rr); df["grow"]=[j[2][4] for j in jobs]; df.to_csv(os.environ["OUTF"],index=False); print("done",time.time()-t0)
