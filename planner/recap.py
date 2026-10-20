#!/usr/bin/env python3
"""Performance recap 2026-10-09 00:00 Asia/Saigon -> now, excluding final ETH long (avg 2393.78/79).
Reconstructs per-minute exposure & equity from fills (read-only data already fetched), 1m candles adverse extremes."""
import json, datetime as dt, pandas as pd, numpy as np
TZ=dt.timezone(dt.timedelta(hours=7))
W0=int(dt.datetime(2026,10,9,0,0,tzinfo=TZ).timestamp()*1000)
E_NOW=524.87493901
MMR={"BTCUSDT":0.004,"ETHUSDT":0.005,"MAGICUSDT":0.01}
P=json.load(open("positions_window.json")); F=json.load(open("fills_window.json")); B=json.load(open("bills_full.json"))
f=lambda t: dt.datetime.fromtimestamp(int(t)/1000,TZ).strftime('%m-%d %H:%M')
excl=[p for p in P if p['symbol']=='ETHUSDT' and p['holdSide']=='long' and abs(float(p['openAvgPrice'])-2393.79)<0.05]
assert len(excl)==1; X=excl[0]
pos=[p for p in P if int(p['utime'])>=W0 and p is not X]
pos.sort(key=lambda p:int(p['ctime']))
rows=[]
for p in pos:
    fee=float(p['openFee'])+float(p['closeFee'])
    rows.append(dict(open=f(p['ctime']),close=f(p['utime']),sym=p['symbol'],side=p['holdSide'],avg_open=float(p['openAvgPrice']),avg_close=float(p['closeAvgPrice']),
        size=float(p['openTotalPos']),gross=float(p['pnl']),fees=fee,funding=float(p.get('totalFunding') or 0),net=float(p['netProfit']),
        hold_h=(int(p['utime'])-int(p['ctime']))/3.6e6))
df=pd.DataFrame(rows); df.to_csv("recap_positions.csv",index=False)
w=(df.net>0).sum(); l=(df.net<=0).sum()
S=dict(window_from="2026-10-09 00:00 UTC+7",n_positions=len(df),wins=int(w),losses=int(l),net=round(df.net.sum(),2),gross=round(df.gross.sum(),2),
       fees=round(df.fees.sum(),2),funding=round(df.funding.sum(),2),fee_share_of_gross=round(-df.fees.sum()/df.gross[df.gross>0].sum()*100,1),
       best=round(df.net.max(),2),worst=round(df.net.min(),2),excluded_eth_long_net=round(float(X['netProfit']),2))
S['worst_trade']=df.loc[df.net.idxmin()].to_dict()
# by symbol
S['by_symbol']=df.groupby('sym').net.agg(['count','sum']).round(2).to_dict('index')
# ---- exposure / liq reconstruction
c={s:pd.read_pickle(f"data/{s}_1m.pkl").set_index('ts_ms') for s in ["BTCUSDT","ETHUSDT"]}
xs,xe=int(X['ctime']),int(X['utime'])
ev=[]
for x in F:
    t=int(x['cTime']); s=x['symbol']; q=float(x['baseVolume']); pr=float(x['price'])
    ts=x['tradeSide']; sd=x['side']
    leg='long' if ((ts=='open' and sd=='buy') or (ts=='close' and sd=='buy')) else 'short'
    # Bitget v2 hedge: close+buy = close long, close+sell = close short
    if ts=='open': leg='long' if sd=='buy' else 'short'
    else: leg='long' if sd=='buy' else 'short'
    fee=sum(float(d.get('totalFee',0)) for d in x.get('feeDetail',[]))
    ev.append((t,s,leg,q if ts=='open' else -q,pr,float(x.get('profit') or 0)+fee))
ev.sort()
fund=[(int(b['cTime']),float(b['amount'])+float(b['fee'])) for b in B if b['businessType'] in('contract_settle_fee',) or 'trans' in b['businessType']]
# wallet(t) = E_NOW - sum(realized after t) - sum(funding/transfers after t)
lst=[(t,v) for (t,_,_,_,_,v) in ev]+fund; lst.sort()
times=np.array([t for t,_ in lst]); vals=np.array([v for _,v in lst]); suffix=np.cumsum(vals[::-1])[::-1]
def wallet(t):
    i=np.searchsorted(times,t,side='right'); return E_NOW-(suffix[i] if i<len(suffix) else 0)
state={}; # (s,leg)->[qty,cost]
mins=range(W0//60000*60000, (ev[-1][0]//60000+1)*60000, 60000)
ei=0; out=[]
while ei<len(ev) and ev[ei][0]<W0:
    t,s,leg,dq,pr,_=ev[ei]; k=(s,leg); q,cst=state.get(k,[0,0])
    if dq>0: q+=dq; cst+=dq*pr
    else: avg=cst/q if q>0 else pr; q=max(0,q+dq); cst=avg*q
    state[k]=[q,cst]; ei+=1
for m in mins:
    while ei<len(ev) and ev[ei][0]<m+60000:
        t,s,leg,dq,pr,_=ev[ei]; k=(s,leg); q,cst=state.get(k,[0,0])
        if dq>0: q+=dq; cst+=dq*pr
        else: avg=cst/q if q>0 else pr; q=max(0,q+dq); cst=avg*q
        state[k]=[q,cst]; ei+=1
    if xs<=m<=xe: continue  # skip final excluded ETH long period
    if not any(v[0]>1e-9 for v in state.values()): continue
    upw=0; notl=0; mm=0; netd=0; upc=0; mmc=0; notc=0
    for (s,leg),(q,cst) in state.items():
        if q<=1e-9 or s not in c or m not in c[s].index: continue
        r=c[s].loc[m]; adv=r.low if leg=='long' else r.high
        sg=1 if leg=='long' else -1
        upw+=sg*(adv*q-cst); notl+=adv*q; mm+=MMR[s]*adv*q; netd+=sg*r.close*q
        upc+=sg*(r.close*q-cst); mmc+=MMR[s]*r.close*q; notc+=r.close*q
    eq=wallet(m)+upw
    out.append((m,eq,notl,mm,netd,wallet(m)+upc,mmc,notc))
o=pd.DataFrame(out,columns=['t','eq_worst','notional','mm','net_delta','eq_close','mm_close','not_close'])
o['mmr_close']=o.mm_close/o.eq_close; o['lev_close']=o.not_close/o.eq_close
o['lev']=o.notional/o.eq_worst; o['mm_ratio']=o.mm/o.eq_worst
o['liq_move_pct']=(o.eq_worst-o.mm)/o.net_delta.abs().replace(0,np.nan)*100
o.to_csv("recap_exposure_1m.csv",index=False)
i=o.notional.idxmax(); j=o.mm_ratio.idxmax()
S['max_exposure']=dict(time=f(o.t[i]),notional=round(o.notional[i],0),equity=round(o.eq_worst[i],1),x_equity=round(o.lev[i],1))
S['max_eff_leverage']=dict(time=f(o.t[o.lev.idxmax()]),x=round(o.lev.max(),1))
S['closest_to_liq']=dict(time=f(o.t[j]),mm_ratio_pct=round(o.mm_ratio[j]*100,1),equity=round(o.eq_worst[j],1),notional=round(o.notional[j],0),move_to_liq_pct=round(o.liq_move_pct[j],2))
top=o.sort_values('mm_ratio',ascending=False); seen=[];tops=[]
for _,r in top.iterrows():
    if all(abs(r.t-s)>6*3600e3 for s in seen):
        seen.append(r.t); tops.append(dict(time=f(r.t),mm_ratio_pct=round(r.mm_ratio*100,1),eq=round(r.eq_worst,1),notional=round(r.notional),x_eq=round(r.lev,1),move_to_liq_pct=round(r.liq_move_pct,2)))
    if len(tops)==5: break
S['top5_closest_liq_episodes']=tops
jc=o.mmr_close.idxmax(); S['closest_to_liq_at_close_price']=dict(time=f(o.t[jc]),mm_ratio_pct=round(o.mmr_close[jc]*100,1),equity=round(o.eq_close[jc],1),notional=round(o.not_close[jc]),x_eq=round(o.lev_close[jc],1),move_to_liq_pct=round((o.eq_close[jc]-o.mm_close[jc])/abs(o.net_delta[jc])*100,2))
S['max_lev_close']=dict(time=f(o.t[o.lev_close.idxmax()]),x=round(o.lev_close.max(),1))
S['median_lev_close_when_in_market']=round(o.lev_close.median(),1)
d=o.copy(); d['day']=pd.to_datetime(d.t,unit='ms',utc=True).dt.tz_convert('Asia/Ho_Chi_Minh').dt.date
S['daily_peak_x_equity']={str(k):round(v,1) for k,v in d.groupby('day').lev_close.max().items()}
df['day']=df.close.str[:5]; S['daily_net']=df.groupby('day').net.sum().round(2).to_dict()
S['time_in_market_pct']=round(len(o)/len(mins)*100,1)
json.dump(S,open("recap.json","w"),indent=1,default=str); print(json.dumps(S,indent=1,default=str))
