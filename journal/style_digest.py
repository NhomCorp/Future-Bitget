#!/usr/bin/env python3
"""Tóm tắt phong cách giao dịch theo ngày (Asia/Saigon UTC+7) từ journal.db. Usage: style_digest.py [YYYY-MM-DD]"""
import sys, os, json, sqlite3, datetime, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__))
TZ = datetime.timezone(datetime.timedelta(hours=7))
ND = "không có dữ liệu"
today = datetime.datetime.now(TZ).date()
day = datetime.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else today - datetime.timedelta(days=1)
t0 = int(datetime.datetime(day.year, day.month, day.day, tzinfo=TZ).timestamp() * 1000); t1 = t0 + 86400000
db = sqlite3.connect(os.path.join(HERE, "journal.db")); db.row_factory = sqlite3.Row
Q = lambda s, a=(): db.execute(s, a).fetchall()
prof = json.load(open(os.path.join(HERE, "..", "profile", "style_profile.json")))
tm = lambda ms: datetime.datetime.fromtimestamp(ms / 1000, TZ).strftime("%H:%M")
med = lambda l: st.median(l) if l else None
def dur(ms):
    h = ms / 3600000
    return f"{h*60:.0f} phút" if h < 1 else f"{h:.1f} giờ" if h < 48 else f"{h/24:.1f} ngày"

# ---- bills fallback for equity ----
bills = []
try: bills = sorted(((int(b["cTime"]), float(b["balance"])) for b in json.load(open(os.path.join(HERE, "..", "profile", "bills_raw.json")))))
except Exception: pass
snaps = [(r["ts"], r["equity"]) for r in Q("SELECT ts,equity FROM snapshots WHERE equity IS NOT NULL ORDER BY ts")]
def equity_at(t):
    c = [e for ts, e in snaps if ts <= t and t - ts < 6 * 3600000]
    if c: return c[-1], "snapshot"
    c = [b for ts, b in bills if ts <= t]
    if c: return c[-1], "bills"
    return None, None

# ---- reconstruct position cycles from all fills ----
fills = Q("SELECT * FROM fills ORDER BY c_time, trade_id")
size = {}; cyc = {}; cycles = []; last = {}; maxn = (0, None, None, None, None)
for f in fills:
    ps = "long" if f["side"] == "buy" else "short"; k = (f["symbol"], ps)
    last[f["symbol"]] = f["price"]
    if f["trade_side"] == "open":
        if size.get(k, 0) < 1e-12: cyc[k] = {"sym": k[0], "side": ps, "start": f["c_time"], "opens": {}, "end": None}
        size[k] = size.get(k, 0) + f["base_volume"]
        cyc[k]["opens"].setdefault(f["order_id"], []).append(f)
    else:
        size[k] = max(0, size.get(k, 0) - f["base_volume"])
        if size[k] < 1e-12 and k in cyc:
            cyc[k]["end"] = f["c_time"]; cycles.append(cyc.pop(k))
    if t0 <= f["c_time"] < t1:
        tot = sum(sz * last.get(kk[0], 0) for kk, sz in size.items())
        if tot > maxn[0]: maxn = (tot, f["c_time"], dict(size), dict(last), None)
cycles += list(cyc.values())
def size_at(sym, ps, t):
    s = 0
    for f in fills:
        if f["c_time"] > t: break
        if f["symbol"] == sym and ("long" if f["side"] == "buy" else "short") == ps:
            s += f["base_volume"] if f["trade_side"] == "open" else -f["base_volume"]
    return max(0, s)

L = []; P = L.append
orders = Q("SELECT * FROM orders WHERE c_time>=? AND c_time<?", (t0, t1))
nplan = Q("SELECT * FROM plan_orders WHERE plan_type='normal_plan' AND c_time>=? AND c_time<?", (t0, t1))
tpsl = Q("SELECT * FROM plan_orders WHERE plan_type!='normal_plan' AND c_time>=? AND c_time<?", (t0, t1))
dfills = [f for f in fills if t0 <= f["c_time"] < t1]
P(f"📒 Tóm tắt phong cách giao dịch ngày {day.isoformat()} (UTC+7)")
if not orders and not nplan and not tpsl and not dfills:
    P(f"Hôm nay/ngày này: {ND} (journal không có lệnh hay khớp nào)."); print("\n".join(L)); sys.exit()

# 1. orders
filled = [o for o in orders if o["status"] == "filled"]; canc = [o for o in orders if o["status"] in ("canceled", "cancelled")]
part = [o for o in orders if o["status"] == "partially_filled"]
cr = len(canc) / len(orders) * 100 if orders else None
n_mkt = sum(1 for o in orders if o["order_type"] == "market")
P(f"• Lệnh đặt: {len(orders)} (limit {len(orders)-n_mkt}, market {n_mkt}) + {len(nplan)} lệnh điều kiện | khớp {len(filled)}, khớp một phần {len(part)}, huỷ {len(canc)} → tỉ lệ huỷ {cr:.0f}%" if orders else f"• Lệnh đặt: 0 lệnh thường, {len(nplan)} lệnh điều kiện")
op = [o for o in orders if o["trade_side"] == "open"]; cl = [o for o in orders if o["trade_side"] == "close"]
P(f"  - Mở {len(op)} (Long {sum(o['pos_side']=='long' for o in op)}/Short {sum(o['pos_side']=='short' for o in op)}), chốt/đóng {len(cl)} (Long {sum(o['pos_side']=='long' for o in cl)}/Short {sum(o['pos_side']=='short' for o in cl)})")

# 2. TP/SL
is_tp = lambda p: "profit" in (p["plan_type"] or ""); is_sl = lambda p: "loss" in (p["plan_type"] or "")
tpn = sum(map(is_tp, tpsl)); sln = sum(map(is_sl, tpsl))
preset = sum(1 for o in orders if o["preset_tp"] or o["preset_sl"])
can_in_day = Q("SELECT * FROM plan_orders WHERE plan_type!='normal_plan' AND plan_status='cancelled' AND u_time>=? AND u_time<?", (t0, t1))
allp = Q("SELECT * FROM plan_orders WHERE plan_type!='normal_plan'")
moved = 0; removed = []; sys_closed = 0
for c in can_in_day:
    rep = [p for p in allp if p["order_id"] != c["order_id"] and p["symbol"] == c["symbol"] and p["pos_side"] == c["pos_side"]
           and (is_sl(p) == is_sl(c)) and 0 <= (p["c_time"] or 0) - c["u_time"] <= 120000 or
           p["order_id"] != c["order_id"] and p["symbol"] == c["symbol"] and p["pos_side"] == c["pos_side"] and is_sl(p) == is_sl(c) and 0 <= c["u_time"] - (p["c_time"] or 0) <= 0]
    if rep: moved += 1; continue
    open_sz = size_at(c["symbol"], c["pos_side"], c["u_time"])
    if open_sz > 1e-12: removed.append((c, open_sz))
    else: sys_closed += 1
ev_mod = Q("SELECT * FROM events WHERE source='pending' AND kind='modified' AND entity='profit_loss' AND ts>=? AND ts<?", (t0, t1))
snap_day = Q("SELECT COUNT(*) n FROM snapshots WHERE ts>=? AND ts<?", (t0, t1))[0]["n"]
rm_sl = [(c, s) for c, s in removed if is_sl(c)]; rm_tp = [(c, s) for c, s in removed if is_tp(c)]
P(f"• TP/SL: đặt mới {tpn} TP + {sln} SL" + (f" (+{preset} lệnh có TP/SL gắn kèm)" if preset else ""))
P(f"  - Dời (huỷ rồi đặt lại trong 2 phút): {moved}" + (f"; sửa trực tiếp ghi nhận bởi theo dõi 5 phút: {len(ev_mod)}" if snap_day else f"; sửa trực tiếp: {ND} (chưa có snapshot 5 phút trong ngày)"))
P(f"  - Gỡ khi vị thế còn mở: SL {len(rm_sl)}, TP {len(rm_tp)}; tự huỷ do vị thế đã đóng: {sys_closed}")
for c, s in rm_sl[:5]:
    P(f"    ⚠ SL {c['symbol']} {c['pos_side']} @ {c['trigger_price']} bị gỡ lúc {tm(c['u_time'])} khi còn size {s:g}")
sl_exec = [p for p in Q("SELECT * FROM plan_orders WHERE plan_status='executed' AND plan_type IN ('loss_plan','pos_loss') AND u_time>=? AND u_time<?", (t0, t1))]
P(f"  - SL đã kích hoạt trong ngày: {len(sl_exec)}")

# 3. notional vs equity
if maxn[1]:
    eq, src = equity_at(maxn[1])
    if eq:
        P(f"• Notional tổng lớn nhất: {maxn[0]:,.0f} USDT lúc {tm(maxn[1])} ≈ {maxn[0]/eq:.1f}× equity ({eq:,.0f} USDT, nguồn {src})")
    else: P(f"• Notional tổng lớn nhất: {maxn[0]:,.0f} USDT; equity: {ND}")
else: P(f"• Notional tổng lớn nhất: {ND}")

# 4. DCA
dc = []; spac = []
day_cycles = [c for c in cycles if any(t0 <= f["c_time"] < t1 for fl in c["opens"].values() for f in fl)]
for c in day_cycles:
    od = sorted(((fl[0]["c_time"], sum(x["price"]*x["base_volume"] for x in fl)/sum(x["base_volume"] for x in fl)) for fl in c["opens"].values()))
    dc.append((c, len(od)))
    for (_, a), (_, b) in zip(od, od[1:]):
        adv = (a - b) / a * 100 if c["side"] == "long" else (b - a) / a * 100
        spac.append(adv)
if dc:
    adds = sum(n - 1 for _, n in dc)
    adv = [s for s in spac if s > 0]
    P(f"• DCA: {len(dc)} vị thế (chu kỳ) có lệnh mở trong ngày, tổng {adds} lệnh DCA thêm; số lớp/vị thế: " + ", ".join(str(n) for _, n in dc))
    P("  - Khoảng cách giữa các lớp (ngược hướng): " + (f"trung vị {med(adv):.2f}% ({len(adv)} lần)" if adv else ND) + (f"; thuận hướng {len(spac)-len(adv)} lần" if len(spac) > len(adv) else ""))
else: P(f"• DCA: {ND}")

# 5. pnl
if dfills:
    gross = sum(f["profit"] or 0 for f in dfills); fee = sum(f["fee"] or 0 for f in dfills)
    P(f"• PnL đã chốt (từ khớp lệnh): gộp {gross:+.2f}, phí {fee:+.2f} → ròng {gross+fee:+.2f} USDT ({len(dfills)} lần khớp, maker {sum(f['trade_scope']=='maker' for f in dfills)})")
else: P(f"• PnL đã chốt: {ND}")

# 6. hold
now = int(datetime.datetime.now(TZ).timestamp() * 1000)
hl = [(((c["end"] or now) - c["start"]), c) for c in cycles if c["start"] < t1 and (c["end"] is None or c["end"] >= t0)]
closed_d = [(d, c) for d, c in hl if c["end"] and t0 <= c["end"] < t1]
if closed_d:
    d, c = max(closed_d, key=lambda x: x[0]); P(f"• Giữ lâu nhất (đóng trong ngày): {c['sym']} {c['side'].capitalize()} {dur(d)}; trung vị {dur(med([x for x, _ in closed_d]))} ({len(closed_d)} vị thế đóng)")
else: P(f"• Giữ lâu nhất: {ND} (không vị thế nào đóng trong ngày)")
openc = [(d, c) for d, c in hl if c["end"] is None]
if openc: P("  - Đang mở qua cuối ngày: " + ", ".join(f"{c['sym']} {c['side']} ({dur(d)})" for d, c in openc))

# ---- observations vs 30-day baseline ----
P("🔎 Nhận xét so với baseline 30 ngày:")
obs = []
try:
    bl = prof["dca"]["peak_notional_vs_equity"]["median"]; bp90 = prof["dca"]["peak_notional_vs_equity"]["p90"]
    if maxn[1] and eq:
        r = maxn[0] / eq
        obs.append(f"Size: notional tổng đỉnh {r:.0f}× equity; baseline mỗi vị thế trung vị {bl:.0f}× (p90 {bp90:.0f}×) và đỉnh tài khoản cũ {prof['dca']['max_simultaneous_total_notional_usdt']:,.0f} USDT → " + ("đang " + ("TĂNG (vượt đỉnh cũ)" if maxn[0] > prof['dca']['max_simultaneous_total_notional_usdt'] else "cao hơn mức trung vị" if r > bl else "thấp hơn mức trung vị")))
except Exception: pass
base_sl = prof["exits"]["stop_loss_order_count"]
obs.append(f"Kỷ luật SL: baseline chỉ {base_sl} lệnh SL kích hoạt/310 lệnh khớp (hiếm dùng). Hôm nay đặt {sln} SL, gỡ {len(rm_sl)} khi vị thế còn mở, kích hoạt {len(sl_exec)}" + (" → vẫn chủ yếu không dùng SL" if sln == 0 else ""))
prior = Q("SELECT status FROM orders WHERE c_time<?", (t0,))
if prior and cr is not None:
    pc = sum(1 for o in prior if o["status"] in ("canceled", "cancelled")) / len(prior) * 100
    obs.append(f"Huỷ lệnh: hôm nay {cr:.0f}% vs {pc:.0f}% trong các ngày trước ({len(prior)} lệnh)" + (" → huỷ nhiều hơn thường lệ" if cr > pc + 10 else " → huỷ ít hơn thường lệ" if cr < pc - 10 else " → tương đương"))
if adv and prof["dca"]["spacing_pct_adverse_only_positive"]["median"]:
    b = prof["dca"]["spacing_pct_adverse_only_positive"]["median"]
    obs.append(f"DCA: khoảng cách trung vị {med(adv):.2f}% vs baseline {b:.2f}%; số lớp trung vị {med([n for _, n in dc]):g} vs baseline {prof['dca']['layers_including_first']['median']:g}")
if closed_d:
    obs.append(f"Thời gian giữ trung vị {dur(med([x for x, _ in closed_d]))} vs baseline {dur(prof['risk']['hold_hours']['median']*3600000)}")
for o in obs[:3]: P("  - " + o)
P(f"(Nguồn: journal.db; equity {'từ snapshot 5 phút' if snap_day else 'ước lượng từ bills'})")
print("\n".join(L))
