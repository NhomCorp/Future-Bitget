# Bitget USDT-M futures watcher: prints NO_CHANGE or a Vietnamese change report.
import os, json, time, hmac, hashlib, base64, urllib.request
K=os.environ["BITGET_API_KEY"]; S=os.environ["BITGET_API_SECRET"]; P=os.environ["BITGET_PASSPHRASE"]
ST=os.path.join(os.path.dirname(os.path.abspath(__file__)),"state.json")
def get(path, query=""):
    ts=str(int(time.time()*1000)); rp=path+("?"+query if query else "")
    sig=base64.b64encode(hmac.new(S.encode(),(ts+"GET"+rp).encode(),hashlib.sha256).digest()).decode()
    req=urllib.request.Request("https://api.bitget.com"+rp,headers={"ACCESS-KEY":K,"ACCESS-SIGN":sig,"ACCESS-TIMESTAMP":ts,"ACCESS-PASSPHRASE":P,"Content-Type":"application/json","locale":"en-US"})
    with urllib.request.urlopen(req,timeout=15) as r: d=json.load(r)
    if d.get("code")!="00000": raise RuntimeError(f"{path}: {d.get('code')} {d.get('msg')}")
    return d["data"]
f=lambda x:float(x or 0)
def fmt(x,n=2): return f"{f(x):,.{n}f}"
try:
    acc=get("/api/v2/mix/account/accounts","productType=USDT-FUTURES")[0]
    pos=get("/api/v2/mix/position/all-position","productType=USDT-FUTURES&marginCoin=USDT") or []
    orders=[]
    for q,kind in [("productType=USDT-FUTURES","limit"),]:
        for o in (get("/api/v2/mix/order/orders-pending",q).get("entrustedList") or []): o["_k"]="Lệnh chờ"; orders.append(o)
    for pt,name in [("normal_plan","Lệnh điều kiện"),("profit_loss","TP/SL")]:
        for o in (get("/api/v2/mix/order/orders-plan-pending","productType=USDT-FUTURES&planType="+pt).get("entrustedList") or []): o["_k"]=name; orders.append(o)
except Exception as e:
    print("ERROR", e); raise SystemExit(0)
old=json.load(open(ST)) if os.path.exists(ST) else {"pos":{},"ord":{},"warn":{}}
eq=f(acc.get("accountEquity")); mmr=f(acc.get("crossedRiskRate"))*100
lines=[]; newpos={}; neword={}; warn=dict(old.get("warn",{}))
def pdesc(p):
    side="Long" if p["holdSide"]=="long" else "Short"; mark=f(p.get("markPrice")); liq=f(p.get("liquidationPrice"))
    dist=abs(mark-liq)/mark*100 if mark and liq>0 else None
    s=f"{p['symbol']} {side} {p.get('leverage')}x {p.get('marginMode')}, size {p['total']}, giá vào {fmt(p.get('openPriceAvg'),2)}, giá hiện tại {fmt(mark,2)}, thanh lý {fmt(liq,2) if liq>0 else '—'}"
    if dist is not None: s+=f" (cách {dist:.2f}%)"
    s+=f", PnL chưa chốt {f(p.get('unrealizedPL')):+.2f} USDT"
    return s,dist
for p in pos:
    if f(p.get("total"))==0: continue
    key=p["symbol"]+"_"+p["holdSide"]; newpos[key]=p["total"]; d,dist=pdesc(p)
    if key not in old["pos"]: lines.append("🟢 Mở vị thế mới: "+d)
    elif old["pos"][key]!=p["total"]: lines.append(f"🔄 Đổi size ({old['pos'][key]} → {p['total']}): "+d)
    if dist is not None:
        if dist<2 and not warn.get(key): lines.append(f"⚠️ {p['symbol']} chỉ còn cách giá thanh lý {dist:.2f}%"); warn[key]=1
        elif dist>3: warn.pop(key,None)
for key,sz in old["pos"].items():
    if key not in newpos: lines.append(f"⚪ Đã đóng vị thế {key.replace('_',' ')} (size cũ {sz})"); warn.pop(key,None)
def odesc(o, short=False):
    ps=o.get("posSide") or ("long" if o.get("side")=="buy" else "short")
    PS="Long" if ps=="long" else "Short"
    ts=o.get("tradeSide") or ""; k=o["_k"]; pt=o.get("planType") or ""
    price=o.get("price") or o.get("triggerPrice") or o.get("stopSurplusTriggerPrice") or o.get("stopLossTriggerPrice")
    sz=o.get("size"); szt=f"size {sz}" if f(sz)>0 else "toàn bộ vị thế"
    if k=="TP/SL":
        kind="Chốt lời (TP)" if "profit" in pt else ("Cắt lỗ (SL)" if "loss" in pt else "TP/SL")
        return f"{kind} bảo vệ {PS} {o.get('symbol')}, {szt}, kích hoạt @ {price}"
    act=("Mở " if ts=="open" else "Chốt " if ts=="close" else "")+PS
    pre="Lệnh điều kiện: " if k=="Lệnh điều kiện" else ""
    return f"{pre}{act} {o.get('symbol')}, size {sz} @ {price}"
for o in orders:
    oid=o.get("orderId"); desc=odesc(o)
    neword[oid]=desc
    if oid not in old["ord"]: lines.append("📝 Lệnh mới: "+desc)
for oid,desc in old["ord"].items():
    if oid not in neword: lines.append("✖️ Lệnh không còn (đã khớp hoặc huỷ): "+desc)
if mmr>=50 and not warn.get("_mmr"): lines.append(f"⚠️ MMR tài khoản lên {mmr:.1f}%"); warn["_mmr"]=1
elif mmr<40: warn.pop("_mmr",None)
json.dump({"pos":newpos,"ord":neword,"warn":warn},open(ST,"w"),ensure_ascii=False)
try:
    import sys, io, contextlib
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "journal"))
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        import journal as _j
        _j.sync(acc=acc, pos=pos, pend=orders, budget_s=12)
except BaseException as _e:
    try:
        open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "journal", "errors.log"), "a").write("hook: " + repr(_e) + "\n")
    except Exception: pass
if not lines: print("NO_CHANGE")
else:
    print("\n".join(lines)); print(f"Số dư futures: {eq:,.2f} USDT, MMR {mmr:.1f}%, đang mở {len(newpos)} vị thế, {len(neword)} lệnh chờ")
    if neword: print("Đang chờ: "+"; ".join(neword.values()))
