#!/usr/bin/env python3
"""Bitget read-only order journal. GET endpoints only. Append-only event log + upserted SQLite tables."""
import os, sys, json, time, hmac, hashlib, base64, sqlite3, urllib.request, urllib.error, datetime, traceback
HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "journal.db"); CUR = os.path.join(HERE, "cursor.json")
RAWDIR = os.path.join(HERE, "raw"); ERRLOG = os.path.join(HERE, "errors.log")
PT = "USDT-FUTURES"
BACKFILL_FROM = "2026-09-19"          # Asia/Saigon midnight
TZ7 = datetime.timezone(datetime.timedelta(hours=7))
DAY = 86400000; WIN = 7 * DAY - 1000   # API window limit is 7 days for fill-history
OVERLAP = {"orders": 48 * 3600000, "plan_normal_plan": 48 * 3600000, "plan_profit_loss": 48 * 3600000,
           "plan_track_plan": 48 * 3600000, "fills": 6 * 3600000, "positions": 48 * 3600000}

def log_err(msg):
    with open(ERRLOG, "a") as f: f.write(f"{datetime.datetime.now(TZ7).isoformat()} {msg}\n")

def api(path, query=""):
    K = os.environ["BITGET_API_KEY"]; S = os.environ["BITGET_API_SECRET"]; P = os.environ["BITGET_PASSPHRASE"]
    ts = str(int(time.time() * 1000)); rp = path + ("?" + query if query else "")
    sig = base64.b64encode(hmac.new(S.encode(), (ts + "GET" + rp).encode(), hashlib.sha256).digest()).decode()
    req = urllib.request.Request("https://api.bitget.com" + rp, headers={"ACCESS-KEY": K, "ACCESS-SIGN": sig,
        "ACCESS-TIMESTAMP": ts, "ACCESS-PASSPHRASE": P, "Content-Type": "application/json", "locale": "en-US"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=12) as r: d = json.load(r)
        except urllib.error.HTTPError as e:
            d = {"code": f"http{e.code}", "msg": e.read().decode()[:200]}
        if d.get("code") == "00000": return d["data"]
        if str(d.get("code")) in ("429", "http429") and attempt < 2: time.sleep(1.5); continue
        raise RuntimeError(f"{path}: {d.get('code')} {d.get('msg')}")

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders(order_id TEXT PRIMARY KEY, client_oid TEXT, symbol TEXT, side TEXT, pos_side TEXT, trade_side TEXT,
 order_type TEXT, status TEXT, price REAL, price_avg REAL, size REAL, base_volume REAL, quote_volume REAL, fee REAL, total_profits REAL,
 leverage TEXT, margin_mode TEXT, order_source TEXT, reduce_only TEXT, force TEXT, preset_tp TEXT, preset_sl TEXT, entry_source TEXT,
 c_time INTEGER, u_time INTEGER, first_seen INTEGER, last_changed INTEGER, raw TEXT);
CREATE TABLE IF NOT EXISTS plan_orders(order_id TEXT PRIMARY KEY, client_oid TEXT, plan_type TEXT, plan_status TEXT, symbol TEXT, side TEXT,
 pos_side TEXT, trade_side TEXT, order_type TEXT, size REAL, price REAL, trigger_price REAL, trigger_type TEXT, execute_price REAL,
 tp_trigger REAL, sl_trigger REAL, execute_order_id TEXT, entry_source TEXT, c_time INTEGER, u_time INTEGER, first_seen INTEGER,
 last_changed INTEGER, raw TEXT);
CREATE TABLE IF NOT EXISTS fills(trade_id TEXT PRIMARY KEY, order_id TEXT, symbol TEXT, side TEXT, trade_side TEXT, price REAL,
 base_volume REAL, quote_volume REAL, fee REAL, profit REAL, trade_scope TEXT, entry_source TEXT, c_time INTEGER, first_seen INTEGER, raw TEXT);
CREATE TABLE IF NOT EXISTS positions(position_id TEXT PRIMARY KEY, symbol TEXT, hold_side TEXT, margin_mode TEXT, open_avg REAL, close_avg REAL,
 open_total REAL, close_total REAL, pnl REAL, net_profit REAL, funding REAL, open_fee REAL, close_fee REAL, c_time INTEGER, u_time INTEGER,
 first_seen INTEGER, last_changed INTEGER, raw TEXT);
CREATE TABLE IF NOT EXISTS pending(order_id TEXT PRIMARY KEY, kind TEXT, symbol TEXT, first_seen INTEGER, last_seen INTEGER, gone_at INTEGER, sig TEXT, raw TEXT);
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER, source TEXT, entity TEXT, kind TEXT, entity_id TEXT, symbol TEXT, detail TEXT);
CREATE TABLE IF NOT EXISTS snapshots(ts INTEGER PRIMARY KEY, equity REAL, mmr_pct REAL, positions TEXT, n_pending INTEGER);
CREATE INDEX IF NOT EXISTS ix_ev_ts ON events(ts); CREATE INDEX IF NOT EXISTS ix_orders_c ON orders(c_time);
CREATE INDEX IF NOT EXISTS ix_plan_c ON plan_orders(c_time); CREATE INDEX IF NOT EXISTS ix_fills_c ON fills(c_time);
CREATE INDEX IF NOT EXISTS ix_pos_c ON positions(c_time);
"""
def fl(x):
    try: return float(x) if x not in (None, "") else None
    except Exception: return None
def it(x):
    try: return int(x)
    except Exception: return None
def now_ms(): return int(time.time() * 1000)

def raw_append(entity, rec, ts):
    os.makedirs(RAWDIR, exist_ok=True)
    day = datetime.datetime.fromtimestamp(ts / 1000, TZ7).strftime("%Y-%m-%d")
    with open(os.path.join(RAWDIR, f"{day}.jsonl"), "a") as f:
        f.write(json.dumps({"seen": ts, "entity": entity, "rec": rec}, ensure_ascii=False) + "\n")

def event(db, ts, source, entity, kind, eid, symbol, detail=None):
    db.execute("INSERT INTO events(ts,source,entity,kind,entity_id,symbol,detail) VALUES(?,?,?,?,?,?,?)",
               (ts, source, entity, kind, eid, symbol, json.dumps(detail, ensure_ascii=False) if detail is not None else None))

def diff(old, new, skip=("uTime",)):
    return {k: [old.get(k), new.get(k)] for k in set(old) | set(new) if k not in skip and old.get(k) != new.get(k)}

# ---- row mappers ----
def m_order(o): return (o["orderId"], o.get("clientOid"), o.get("symbol"), o.get("side"), o.get("posSide"), o.get("tradeSide"),
    o.get("orderType"), o.get("status"), fl(o.get("price")), fl(o.get("priceAvg")), fl(o.get("size")), fl(o.get("baseVolume")),
    fl(o.get("quoteVolume")), fl(o.get("fee")), fl(o.get("totalProfits")), o.get("leverage"), o.get("marginMode"), o.get("orderSource"),
    o.get("reduceOnly"), o.get("force"), o.get("presetStopSurplusPrice"), o.get("presetStopLossPrice"), o.get("enterPointSource"),
    it(o.get("cTime")), it(o.get("uTime")))
def m_plan(o): return (o["orderId"], o.get("clientOid"), o.get("planType"), o.get("planStatus"), o.get("symbol"), o.get("side"),
    o.get("posSide"), o.get("tradeSide"), o.get("orderType"), fl(o.get("size")), fl(o.get("price")), fl(o.get("triggerPrice")),
    o.get("triggerType"), fl(o.get("executePrice")), fl(o.get("stopSurplusTriggerPrice")), fl(o.get("stopLossTriggerPrice")),
    o.get("executeOrderId"), o.get("enterPointSource"), it(o.get("cTime")), it(o.get("uTime")))
def m_fill(o):
    fee = sum(fl(x.get("totalFee")) or 0 for x in (o.get("feeDetail") or []))
    return (o["tradeId"], o.get("orderId"), o.get("symbol"), o.get("side"), o.get("tradeSide"), fl(o.get("price")), fl(o.get("baseVolume")),
            fl(o.get("quoteVolume")), fee, fl(o.get("profit")), o.get("tradeScope"), o.get("enterPointSource"), it(o.get("cTime")))
def m_pos(o): return (o["positionId"], o.get("symbol"), o.get("holdSide"), o.get("marginMode"), fl(o.get("openAvgPrice")), fl(o.get("closeAvgPrice")),
    fl(o.get("openTotalPos")), fl(o.get("closeTotalPos")), fl(o.get("pnl")), fl(o.get("netProfit")), fl(o.get("totalFunding")),
    fl(o.get("openFee")), fl(o.get("closeFee")), it(o.get("ctime")), it(o.get("utime")))

SPEC = {  # table: (id key, mapper, ncols placeholders, columns, kind field, mutable?)
 "orders": ("orderId", m_order, "order_id,client_oid,symbol,side,pos_side,trade_side,order_type,status,price,price_avg,size,base_volume,quote_volume,fee,total_profits,leverage,margin_mode,order_source,reduce_only,force,preset_tp,preset_sl,entry_source,c_time,u_time", "status", "order"),
 "plan_orders": ("orderId", m_plan, "order_id,client_oid,plan_type,plan_status,symbol,side,pos_side,trade_side,order_type,size,price,trigger_price,trigger_type,execute_price,tp_trigger,sl_trigger,execute_order_id,entry_source,c_time,u_time", "planStatus", "plan"),
 "fills": ("tradeId", m_fill, "trade_id,order_id,symbol,side,trade_side,price,base_volume,quote_volume,fee,profit,trade_scope,entry_source,c_time", None, "fill"),
 "positions": ("positionId", m_pos, "position_id,symbol,hold_side,margin_mode,open_avg,close_avg,open_total,close_total,pnl,net_profit,funding,open_fee,close_fee,c_time,u_time", None, "position"),
}
def upsert(db, table, rec, ts):
    idk, mapper, cols, _, ent = SPEC[table]
    eid = rec[idk]; row = mapper(rec); cl = cols.split(",")
    ex = db.execute(f"SELECT raw FROM {table} WHERE {cl[0]}=?", (eid,)).fetchone()
    rawj = json.dumps(rec, ensure_ascii=False, sort_keys=True)
    sym = rec.get("symbol")
    has_lc = table in ("orders", "plan_orders", "positions")
    if ex is None:
        extra_cols = ",first_seen,raw" + (",last_changed" if has_lc else "")
        extra_vals = [ts, rawj] + ([ts] if has_lc else [])
        db.execute(f"INSERT INTO {table}({cols}{extra_cols}) VALUES({','.join('?'*(len(cl)+len(extra_vals)))})", list(row) + extra_vals)
        raw_append(ent, rec, ts)
        event(db, ts, "history", ent, "recorded", eid, sym, {"status": rec.get("status") or rec.get("planStatus"), "cTime": rec.get("cTime") or rec.get("ctime")})
        return "new"
    if ex[0] != rawj:
        old = json.loads(ex[0])
        sets = ",".join(f"{c}=?" for c in cl[1:]) + ",raw=?" + (",last_changed=?" if has_lc else "")
        db.execute(f"UPDATE {table} SET {sets} WHERE {cl[0]}=?", list(row[1:]) + [rawj] + ([ts] if has_lc else []) + [eid])
        raw_append(ent, rec, ts)
        event(db, ts, "history", ent, "updated", eid, sym, diff(old, rec))
        return "upd"
    return "same"

def fetch_window(path, base_q, listkey, st, et, limit=100, deadline=None):
    out = []; last = None
    while True:
        if deadline and time.time() > deadline: raise TimeoutError("deadline")
        q = f"{base_q}&startTime={st}&endTime={et}&limit={limit}" + (f"&idLessThan={last}" if last else "")
        d = api(path, q) or {}
        lst = d.get(listkey) or []
        out += lst
        last = d.get("endId")
        if len(lst) < limit or not last: break
    return out

ENDPOINTS = [  # cursor key, table, path, query, listkey
 ("orders", "orders", "/api/v2/mix/order/orders-history", f"productType={PT}", "entrustedList"),
 ("plan_normal_plan", "plan_orders", "/api/v2/mix/order/orders-plan-history", f"productType={PT}&planType=normal_plan", "entrustedList"),
 ("plan_profit_loss", "plan_orders", "/api/v2/mix/order/orders-plan-history", f"productType={PT}&planType=profit_loss", "entrustedList"),
 ("plan_track_plan", "plan_orders", "/api/v2/mix/order/orders-plan-history", f"productType={PT}&planType=track_plan", "entrustedList"),
 ("fills", "fills", "/api/v2/mix/order/fill-history", f"productType={PT}", "fillList"),
 ("positions", "positions", "/api/v2/mix/position/history-position", f"productType={PT}", "list"),
]

def sync_history(db, cur, budget_s=14, only=None):
    deadline = time.time() + budget_s; counts = {}
    first_ms = int(datetime.datetime.strptime(BACKFILL_FROM, "%Y-%m-%d").replace(tzinfo=TZ7).timestamp() * 1000)
    for ck, table, path, q, lk in ENDPOINTS:
        if only and ck not in only: continue
        end = now_ms()
        start = first_ms if ck not in cur else max(first_ms, cur[ck] - OVERLAP[ck])
        n_new = n_upd = 0
        try:
            s = start
            while s < end:
                e = min(s + WIN, end)
                recs = fetch_window(path, q, lk, s, e, deadline=deadline)
                ts = now_ms()
                for r in recs:
                    res = upsert(db, table, r, ts)
                    n_new += res == "new"; n_upd += res == "upd"
                db.commit()
                cur[ck] = e   # advance per completed window
                s = e + 1
            cur[ck] = end
        except TimeoutError:
            db.commit(); counts[ck] = (n_new, n_upd, "partial"); continue
        except Exception as ex:
            db.commit(); log_err(f"{ck}: {ex}"); counts[ck] = (n_new, n_upd, f"err"); continue
        counts[ck] = (n_new, n_upd, "ok")
        json.dump(cur, open(CUR, "w"))
    json.dump(cur, open(CUR, "w"))
    return counts

PSIG = ("price", "size", "triggerPrice", "stopSurplusTriggerPrice", "stopLossTriggerPrice", "executePrice", "orderType", "planType")
def sync_pending(db, acc=None, pos=None, pend=None):
    """Snapshot pending/plan/TPSL orders + positions; append placed/modified/removed events."""
    ts = now_ms()
    if pend is None:
        pend = []
        for e in (api("/api/v2/mix/order/orders-pending", f"productType={PT}").get("entrustedList") or []): e["_k"] = "limit"; pend.append(e)
        for pt in ("normal_plan", "profit_loss"):
            for e in (api("/api/v2/mix/order/orders-plan-pending", f"productType={PT}&planType={pt}").get("entrustedList") or []): e["_k"] = pt; pend.append(e)
    seen = set()
    for o in pend:
        oid = o["orderId"]; seen.add(oid)
        kind = o.get("_k") or o.get("planType") or "limit"
        if kind in ("Lệnh chờ",): kind = "limit"
        elif kind == "Lệnh điều kiện": kind = "normal_plan"
        elif kind == "TP/SL": kind = "profit_loss"
        rec = {k: v for k, v in o.items() if k != "_k"}
        sig = json.dumps({k: rec.get(k) for k in PSIG}, sort_keys=True)
        ex = db.execute("SELECT sig,gone_at,raw FROM pending WHERE order_id=?", (oid,)).fetchone()
        if ex is None:
            db.execute("INSERT INTO pending VALUES(?,?,?,?,?,?,?,?)", (oid, kind, rec.get("symbol"), ts, ts, None, sig, json.dumps(rec, ensure_ascii=False)))
            event(db, ts, "pending", kind, "placed", oid, rec.get("symbol"), {k: rec.get(k) for k in ("side", "tradeSide", "posSide", "planType", "orderType", "price", "size", "triggerPrice", "stopSurplusTriggerPrice", "stopLossTriggerPrice", "cTime")})
            raw_append("pending_" + kind, rec, ts)
        else:
            if ex[0] != sig:
                old = json.loads(ex[2])
                event(db, ts, "pending", kind, "modified", oid, rec.get("symbol"), diff(old, rec, skip=("uTime", "baseVolume", "priceAvg", "fee", "status", "state")))
                raw_append("pending_" + kind, rec, ts)
            elif ex[1] is not None: pass
            db.execute("UPDATE pending SET last_seen=?,gone_at=NULL,sig=?,raw=? WHERE order_id=?", (ts, sig, json.dumps(rec, ensure_ascii=False), oid))
    for oid, kind, sym in db.execute("SELECT order_id,kind,symbol FROM pending WHERE gone_at IS NULL").fetchall():
        if oid not in seen:
            db.execute("UPDATE pending SET gone_at=? WHERE order_id=?", (ts, oid))
            event(db, ts, "pending", kind, "removed", oid, sym, None)   # filled or cancelled: resolved by history tables
    if acc is not None or pos is not None:
        ps = [{"symbol": p.get("symbol"), "side": p.get("holdSide"), "size": p.get("total"), "avg": p.get("openPriceAvg"), "lev": p.get("leverage"),
               "mark": p.get("markPrice"), "upl": p.get("unrealizedPL")} for p in (pos or []) if fl(p.get("total"))]
        db.execute("INSERT OR REPLACE INTO snapshots VALUES(?,?,?,?,?)", (ts, fl((acc or {}).get("accountEquity")),
                   (fl((acc or {}).get("crossedRiskRate")) or 0) * 100, json.dumps(ps), len(pend)))
    db.commit()

def sync(acc=None, pos=None, pend=None, budget_s=14):
    os.makedirs(HERE, exist_ok=True)
    db = sqlite3.connect(DB, timeout=20); db.executescript(SCHEMA)
    cur = json.load(open(CUR)) if os.path.exists(CUR) else {}
    try:
        try: sync_pending(db, acc, pos, pend)
        except Exception as e: log_err("pending: " + repr(e))
        return sync_history(db, cur, budget_s)
    finally: db.close()

if __name__ == "__main__":
    t = time.time()
    try:
        c = sync(budget_s=300 if "--backfill" in sys.argv else 14)
        print(json.dumps(c), f"{time.time()-t:.1f}s")
    except Exception:
        log_err(traceback.format_exc()); print("journal error, see errors.log")
