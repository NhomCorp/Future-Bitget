#!/usr/bin/env python3
"""DCA ladder planner for Bitget USDT-M (read-only; public market data only, never places orders).

Defaults = PLAN.md DEFAULT leg (cap 1.25x equity per leg, 5 layers, 1.5% fixed, equal size, TP1 1.2% 50%, TP2 2.4%, stop -7% eq).
Examples:
  python3 ladder.py --symbol ETHUSDT --side long --equity 525
  python3 ladder.py --symbol BTCUSDT --side short --equity 525 --anchor 83000
  python3 ladder.py --symbol ETHUSDT --side long --cap 2 --layers 7 --spacing atr --atr-mult 1.5 --mult 1.2 --tp 0.8 --stop 10
  python3 ladder.py --symbol BTCUSDT --side long --spacing geometric --step 1.0 --geo 1.25

Assumptions: cross margin, the WHOLE equity backs this one ladder (no other position open),
maintenance margin rate tier-1 (BTC 0.4%, ETH 0.5%; override --mmr), liq when equity+uPnL <= MMR*notional.
Fees: maker 0.02% entries & TP, taker 0.06% for stop. Funding ignored.
"""
import argparse, json, math, sys, urllib.request, csv, os, datetime as dt
API="https://api.bitget.com"
def pub(path):
    with urllib.request.urlopen(urllib.request.Request(API+path,headers={"locale":"en-US"}),timeout=15) as r: return json.load(r)
def atr(sym,gran,n=14):
    d=pub(f"/api/v2/mix/market/candles?symbol={sym}&productType=USDT-FUTURES&granularity={gran}&limit=200")["data"]
    d=sorted(d,key=lambda x:int(x[0])); h=[float(x[2]) for x in d]; l=[float(x[3]) for x in d]; c=[float(x[4]) for x in d]
    tr=[h[0]-l[0]]+[max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1])) for i in range(1,len(c))]
    a=sum(tr[1:n+1])/n
    for x in tr[n+1:]: a=(a*(n-1)+x)/n
    # EMA50 & ADX14 for regime info
    k=2/51; e=c[0]
    for x in c[1:]: e=x*k+e*(1-k)
    pdm=[0]+[max(h[i]-h[i-1],0) if h[i]-h[i-1]>l[i-1]-l[i] else 0 for i in range(1,len(c))]
    ndm=[0]+[max(l[i-1]-l[i],0) if l[i-1]-l[i]>h[i]-h[i-1] else 0 for i in range(1,len(c))]
    def w(v):
        s=sum(v[1:n+1]); o=[s]
        for x in v[n+1:]: s=s-s/n+x; o.append(s)
        return o
    T,Pp,Nn=w(tr),w(pdm),w(ndm); dx=[]
    for t,p,q in zip(T,Pp,Nn):
        pdi,ndi=100*p/t,100*q/t; dx.append(100*abs(pdi-ndi)/max(pdi+ndi,1e-9))
    adx=sum(dx[:n])/n
    for x in dx[n:]: adx=(adx*(n-1)+x)/n
    return a,e,adx,c[-1]
def contract(sym):
    try:
        d=pub(f"/api/v2/mix/market/contracts?symbol={sym}&productType=USDT-FUTURES")["data"][0]
        return float(d.get("sizeMultiplier",0.001)),float(d.get("minTradeNum",0.001)),int(d.get("pricePlace",2))
    except Exception: return (0.0001 if sym.startswith("BTC") else 0.01),0.0001,2
def liq_price(side,Q,A,E,mmr):
    if Q<=0: return float('nan')
    return (Q*A-E)/(Q*(1-mmr)) if side=="long" else (E+Q*A)/(Q*(1+mmr))
def main():
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--symbol",default="ETHUSDT"); ap.add_argument("--side",choices=["long","short"],default="long")
    ap.add_argument("--equity",type=float,default=525.0,help="futures equity USDT")
    ap.add_argument("--anchor",type=float,help="first-entry price (default: live last price)")
    ap.add_argument("--cap",type=float,default=1.25,help="max notional of THIS ladder as multiple of equity. Plan: account cap/4 legs (DEFAULT 5x -> 1.25)")
    ap.add_argument("--layers",type=int,default=5)
    ap.add_argument("--spacing",choices=["fixed","atr","geometric"],default="fixed")
    ap.add_argument("--step",type=float,default=1.5,help="fixed / first step %% (fixed & geometric)")
    ap.add_argument("--geo",type=float,default=1.25,help="geometric growth of step per layer")
    ap.add_argument("--atr-mult",type=float,default=0.8,help="step = atr_mult * ATR(tf)")
    ap.add_argument("--atr-tf",default="1H",choices=["1H","4H"])
    ap.add_argument("--atr-grow",type=float,default=1.0,help="multiply ATR step by this per deeper layer (1=flat)")
    ap.add_argument("--mult",type=float,default=1.0,help="size multiplier per layer (1=equal)")
    ap.add_argument("--tp",type=float,default=1.2,help="TP1 %% from average")
    ap.add_argument("--part",type=float,default=0.5,help="fraction closed at TP1 (1=all); rest at TP2 or breakeven")
    ap.add_argument("--tp2-mult",type=float,default=2.0,help="TP2 = avg +/- tp*tp2_mult")
    ap.add_argument("--stop",type=float,default=7.0,help="hard stop: max loss %% of equity at full ladder")
    ap.add_argument("--mmr",type=float,default=None); ap.add_argument("--maker",type=float,default=0.02); ap.add_argument("--taker",type=float,default=0.06)
    ap.add_argument("--vnd",type=float,default=26000); ap.add_argument("--csv",default=None)
    a=ap.parse_args()
    sym=a.symbol.upper(); mmr=a.mmr if a.mmr is not None else (0.004 if sym.startswith("BTC") else 0.005)
    info={}
    try:
        a1,e1,adx1,last=atr(sym,"1H"); a4,e4,adx4,_=atr(sym,"4H")
        info=dict(last=last,atr1h=a1,atr1h_pct=a1/last*100,atr4h=a4,atr4h_pct=a4/last*100,ema50_1h=e1,adx1h=adx1,ema50_4h=e4,adx4h=adx4)
    except Exception as ex:
        if a.anchor is None or a.spacing=="atr": sys.exit(f"cannot fetch market data: {ex}")
        last=a.anchor
    P0=a.anchor or last; E=a.equity; sg=1 if a.side=="long" else -1
    stepq,minq,pp=contract(sym)
    w=[a.mult**i for i in range(a.layers)]; tot=a.cap*E
    steps=[]
    for i in range(1,a.layers):
        if a.spacing=="fixed": s=a.step/100
        elif a.spacing=="geometric": s=a.step/100*a.geo**(i-1)
        else: s=a.atr_mult*(info["atr1h"] if a.atr_tf=="1H" else info["atr4h"])/P0*a.atr_grow**(i-1)
        steps.append(s)
    prices=[P0]
    for s in steps: prices.append(prices[-1]*(1-sg*s))
    rows=[];Q=0;C=0;fees=0
    for i,(p,wi) in enumerate(zip(prices,w)):
        q=math.floor(tot*wi/sum(w)/p/stepq)*stepq; q=max(q,minq)
        Q+=q;C+=q*p;fees+=q*p*a.maker/100; A=C/Q
        tp=A*(1+sg*a.tp/100); tp2=A*(1+sg*a.tp*a.tp2_mult/100); lq=liq_price(a.side,Q,A,E-fees,mmr)
        rows.append(dict(layer=i+1,price=round(p,pp),move_from_anchor_pct=round((p/P0-1)*100,2),qty=round(q,6),usdt=round(q*p,1),
            cum_qty=round(Q,6),cum_usdt=round(C,1),avg=round(A,pp),tp_price=round(tp,pp),tp2_price=round(tp2,pp) if a.part<1 else '',tp_profit_usdt=round(Q*A*a.tp/100*a.part-fees*a.part-Q*a.part*tp*a.maker/100,2),
            liq_price=round(lq,pp) if lq>0 else 0,dist_to_liq_pct=round(abs(lq/p-1)*100,2) if lq>0 else 999,
            notional_x_eq=round(C/E,2),fees_so_far=round(fees,3)))
    print(f"\n=== {sym} {a.side.upper()} DCA ladder | equity {E:.2f} USDT | cap {a.cap}x = {tot:.0f} USDT | layers {a.layers} | mult {a.mult} | TP1 {a.tp}% ({a.part*100:.0f}%) TP2 {a.tp*a.tp2_mult:.2f}% | MMR {mmr*100}% ===")
    if info: print(f"live {info['last']}  ATR14 1h {info['atr1h']:.2f} ({info['atr1h_pct']:.2f}%)  4h {info['atr4h']:.2f} ({info['atr4h_pct']:.2f}%)  "
                   f"EMA50 1h {info['ema50_1h']:.2f} ({(info['last']/info['ema50_1h']-1)*100:+.2f}%)  ADX 1h {info['adx1h']:.0f} 4h {info['adx4h']:.0f}")
    print("spacing:",a.spacing,"steps %:",", ".join(f"{s*100:.2f}" for s in steps),f"| anchor {P0}")
    hdr=["layer","price","move_from_anchor_pct","qty","usdt","cum_qty","cum_usdt","avg","tp_price","tp2_price","tp_profit_usdt","liq_price","dist_to_liq_pct","notional_x_eq","fees_so_far"]
    short=["L","price","Δanchor%","qty","USDT","cumQty","cumUSDT","avg","TP1","TP2","TP1+USDT","liq","→liq%","x eq","fees"]
    wd=[max(len(h),*(len(str(r[k])) for r in rows)) for h,k in zip(short,hdr)]
    print("  ".join(h.rjust(x) for h,x in zip(short,wd)))
    for r in rows: print("  ".join(str(r[k]).rjust(x) for k,x in zip(hdr,wd)))
    last_r=rows[-1]
    if a.stop:
        sp=last_r['avg']-sg*a.stop/100*E/last_r['cum_qty']
        loss=a.stop/100*E+last_r['cum_usdt']*a.taker/100+last_r['fees_so_far']
        print(f"HARD STOP (-{a.stop}% equity at full ladder): {sp:.{pp}f}  ({(sp/last_r['price']-1)*100:+.2f}% beyond last layer, {(sp/P0-1)*100:+.2f}% from anchor); "
              f"loss incl. fees ≈ {loss:.1f} USDT ≈ {loss*a.vnd/1e6:.2f}M VND; liq {last_r['liq_price']} is {abs(last_r['liq_price']/sp-1)*100:.2f}% further")
    print(f"Full-ladder liq ≈ {last_r['liq_price']} ({(last_r['liq_price']/P0-1)*100:+.2f}% from anchor). L1-only TP1 profit ≈ {rows[0]['tp_profit_usdt']} USDT "
          f"(~{rows[0]['tp_profit_usdt']*a.vnd:,.0f} VND); full-ladder TP1 ≈ {last_r['tp_profit_usdt']} USDT.")
    print("Assumes nothing else open; a 2nd ladder (other coin / hedge leg) shares the same equity → liq comes closer.")
    fn=a.csv or os.path.join(os.path.dirname(os.path.abspath(__file__)),"out",f"ladder_{sym}_{a.side}_{dt.datetime.now():%Y%m%d_%H%M}.csv")
    os.makedirs(os.path.dirname(fn),exist_ok=True)
    with open(fn,"w",newline="") as f: wr=csv.DictWriter(f,fieldnames=hdr); wr.writeheader(); wr.writerows(rows)
    print("CSV:",fn)
if __name__=="__main__": main()
