"""Multi-timeframe technical analysis for the ladder RISK FILTER (not a prediction).
Pure numpy so the same code runs live (public candles) and inside the backtest (sliced history).
Candles format per timeframe: dict(ts,o,h,l,c,v) numpy arrays ascending (ts ms, bar open time)."""
import numpy as np

TF_W = {"15m": 0.5, "1h": 1.0, "4h": 2.0, "1d": 3.0}   # level weight per timeframe

# ---------------- indicators ----------------
def ema(x, n):
    x = np.asarray(x, float); out = np.empty_like(x); a = 2 / (n + 1); e = x[0]
    for i, v in enumerate(x): e = v * a + e * (1 - a) if i else v; out[i] = e
    return out

def rma(x, n):
    x = np.asarray(x, float); out = np.empty_like(x)
    if len(x) == 0: return out
    e = np.mean(x[:n]) if len(x) >= n else x[0]
    for i, v in enumerate(x):
        if i < n: out[i] = np.mean(x[:i + 1])
        else: e = (e * (n - 1) + v) / n; out[i] = e
        if i == n - 1: e = out[i]
    return out

def true_range(h, l, c):
    pc = np.r_[c[0], c[:-1]]
    return np.maximum.reduce([h - l, np.abs(h - pc), np.abs(l - pc)])

def atr(h, l, c, n=14): return rma(true_range(h, l, c), n)

def adx_di(h, l, c, n=14):
    up = np.r_[0, np.diff(h)]; dn = np.r_[0, -np.diff(l)]
    pdm = np.where((up > dn) & (up > 0), up, 0.0); ndm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = rma(true_range(h, l, c), n); tr = np.where(tr == 0, 1e-12, tr)
    pdi = 100 * rma(pdm, n) / tr; ndi = 100 * rma(ndm, n) / tr
    dx = 100 * np.abs(pdi - ndi) / np.maximum(pdi + ndi, 1e-12)
    return rma(dx, n), pdi, ndi

def rsi(c, n=14):
    d = np.r_[0, np.diff(c)]; g = rma(np.maximum(d, 0), n); ls = rma(np.maximum(-d, 0), n)
    return 100 - 100 / (1 + g / np.maximum(ls, 1e-12))

def macd(c, f=12, s=26, sig=9):
    m = ema(c, f) - ema(c, s); sg = ema(m, sig); return m, sg, m - sg

def bollinger_width(c, n=20, k=2):
    if len(c) < n: return np.full(len(c), np.nan)
    w = np.full(len(c), np.nan)
    cs = np.lib.stride_tricks.sliding_window_view(c, n)
    m = cs.mean(1); sd = cs.std(1)
    w[n - 1:] = 2 * k * sd / m
    return w

def pct_rank(series, value):
    s = np.asarray(series, float); s = s[~np.isnan(s)]
    return float((s < value).mean() * 100) if len(s) else float("nan")

# ---------------- structure ----------------
def pivots(h, l, k=3):
    """swing highs/lows with k bars each side (confirmed only). returns lists of (idx, price)."""
    ph, pl = [], []
    n = len(h)
    for i in range(k, n - k):
        if h[i] == h[i - k:i + k + 1].max() and h[i] > h[i - k:i].max(): ph.append((i, h[i]))
        if l[i] == l[i - k:i + k + 1].min() and l[i] < l[i - k:i].min(): pl.append((i, l[i]))
    return ph, pl

def structure(ph, pl):
    if len(ph) < 2 or len(pl) < 2: return "n/a", 0
    hh = ph[-1][1] > ph[-2][1]; hl = pl[-1][1] > pl[-2][1]
    if hh and hl: return "HH/HL (tăng)", 1
    if not hh and not hl: return "LH/LL (giảm)", -1
    return ("HH/LL (mở rộng)" if hh else "LH/HL (tam giác/nén)"), 0

def divergence(c, r, ph, pl, lookback):
    """regular RSI divergence on last two pivots, newest pivot within lookback bars."""
    n = len(c); out = []
    if len(pl) >= 2 and n - 1 - pl[-1][0] <= lookback:
        (i1, p1), (i2, p2) = pl[-2], pl[-1]
        if p2 < p1 and r[i2] > r[i1] + 1: out.append("bullish (giá đáy thấp hơn, RSI đáy cao hơn)")
    if len(ph) >= 2 and n - 1 - ph[-1][0] <= lookback:
        (i1, p1), (i2, p2) = ph[-2], ph[-1]
        if p2 > p1 and r[i2] < r[i1] - 1: out.append("bearish (giá đỉnh cao hơn, RSI đỉnh thấp hơn)")
    return out

# ---------------- per-timeframe analysis ----------------
def analyze_tf(tf, K):
    o, h, l, c, v = (np.asarray(K[x], float) for x in "ohlcv")
    n = len(c); px = c[-1]
    e20, e50, e200 = ema(c, 20)[-1], ema(c, 50)[-1], (ema(c, 200)[-1] if n >= 200 else float("nan"))
    a = atr(h, l, c); A = a[-1]
    adx, pdi, ndi = adx_di(h, l, c)
    r = rsi(c); m, ms, mh = macd(c)
    bw = bollinger_width(c); bwp = pct_rank(bw[-120:], bw[-1])
    atrp = a / c * 100; atr_pct_rank = pct_rank(atrp[-180:], atrp[-1])
    k = 3 if tf in ("15m", "1h") else 2
    ph, pl = pivots(h, l, k)
    st, st_s = structure(ph, pl)
    div = divergence(c, r, ph, pl, lookback=12)
    # EMA alignment score
    if not np.isnan(e200):
        if px > e20 > e50 > e200: al, al_s = "tăng đầy đủ (giá>EMA20>50>200)", 2
        elif px < e20 < e50 < e200: al, al_s = "giảm đầy đủ (giá<EMA20<50<200)", -2
        else: al_s = (1 if px > e50 else -1) * (1 if (e50 > e200) == (px > e50) else 0.5); al = "lẫn lộn"
    else:
        al_s = 1 if px > e20 > e50 else (-1 if px < e20 < e50 else 0); al = "thiếu EMA200 (ít dữ liệu)"
    di_s = (0.5 if pdi[-1] > ndi[-1] else -0.5) if adx[-1] > 20 else 0
    macd_s = 0.5 if mh[-1] > 0 else -0.5
    score = al_s + st_s + di_s + macd_s
    bias = "tăng" if score >= 1.5 else "giảm" if score <= -1.5 else "trung tính"
    regime = ("trend" if adx[-1] >= 25 else "range" if adx[-1] < 20 else "chuyển tiếp")
    if bwp <= 15: regime += "+squeeze"
    elif bwp >= 85: regime += "+expansion"
    ch = lambda nb: (px / c[-1 - nb] - 1) * 100 if n > nb else float("nan")
    return dict(tf=tf, close=px, ema20=e20, ema50=e50, ema200=e200, ema_align=al, atr=A, atr_pct=A / px * 100,
                atr_pct_rank=atr_pct_rank, adx=adx[-1], pdi=pdi[-1], ndi=ndi[-1], rsi=r[-1],
                macd=m[-1], macd_signal=ms[-1], macd_hist=mh[-1], macd_hist_prev=mh[-2] if n > 1 else float("nan"),
                bb_width_pct=bw[-1] * 100 if not np.isnan(bw[-1]) else float("nan"), bb_width_rank=bwp,
                structure=st, structure_score=st_s, rsi_divergence=div, score=round(float(score), 2), bias=bias, regime=regime,
                last_swing_high=ph[-1][1] if ph else None, last_swing_low=pl[-1][1] if pl else None,
                change_1bar=ch(1), last_range_atr=(h[-1] - l[-1]) / A if A else float("nan"),
                _ph=ph, _pl=pl, _n=n)

# ---------------- VWAP & volume profile ----------------
def vwap(K, start_ms):
    ts = np.asarray(K["ts"]); m = ts >= start_ms
    if not m.any(): return float("nan")
    tp = (np.asarray(K["h"])[m] + np.asarray(K["l"])[m] + np.asarray(K["c"])[m]) / 3; v = np.asarray(K["v"])[m]
    return float((tp * v).sum() / max(v.sum(), 1e-12))

def volume_profile(K, bin_pct=0.1, va=0.70):
    h, l, v = (np.asarray(K[x], float) for x in "hlv")
    lo, hi = l.min(), h.max(); mid = (lo + hi) / 2; bs = mid * bin_pct / 100
    nb = max(int((hi - lo) / bs) + 1, 1); edges = lo + bs * np.arange(nb + 1); prof = np.zeros(nb)
    for hh, ll, vv in zip(h, l, v):
        i0 = int((ll - lo) / bs); i1 = min(int((hh - lo) / bs), nb - 1)
        prof[i0:i1 + 1] += vv / (i1 - i0 + 1)
    ctr = (edges[:-1] + edges[1:]) / 2; poc_i = int(prof.argmax())
    tot = prof.sum(); inc = prof[poc_i]; a, b = poc_i, poc_i
    while inc < va * tot and (a > 0 or b < nb - 1):
        la = prof[a - 1] if a > 0 else -1; lb = prof[b + 1] if b < nb - 1 else -1
        if la >= lb: a -= 1; inc += la
        else: b += 1; inc += lb
    sm = np.convolve(prof, np.ones(5) / 5, mode="same")
    hvn, lvn = [], []
    for i in range(3, nb - 3):
        w = sm[i - 3:i + 4]
        if sm[i] == w.max() and sm[i] > np.median(sm) * 1.3: hvn.append((float(ctr[i]), float(sm[i] / sm.max())))
        if sm[i] == w.min() and sm[i] < np.median(sm) * 0.6: lvn.append((float(ctr[i]), float(sm[i] / sm.max())))
    return dict(poc=float(ctr[poc_i]), vah=float(ctr[b]), val=float(ctr[a]), hvn=hvn, lvn=lvn, bin=float(bs))

# ---------------- key levels ----------------
def key_levels(px, tfres, extra, atr1h, max_levels=14):
    """cluster swing pivots of all TFs + VP/VWAP/high-low into levels with a 0-100 strength score."""
    pts = []  # (price, weight, source)
    for tf, R in tfres.items():
        n = R["_n"]; w = TF_W.get(tf, 1)
        for lst in (R["_ph"], R["_pl"]):
            for i, p in lst:
                rec = 0.5 + 0.5 * (i / max(n - 1, 1))          # recency 0.5..1
                pts.append((p, w * rec, f"swing {tf}"))
    for name, p, w in extra: pts.append((p, w, name))
    if not pts: return []
    tol = max(px * 0.0025, 0.5 * atr1h)
    pts.sort(key=lambda x: x[0]); cl = []
    for p, w, s in pts:
        if cl and p - cl[-1]["hi"] <= tol:
            c = cl[-1]; c["pw"] += p * w; c["w"] += w; c["hi"] = p; c["src"].add(s); c["n"] += 1
        else: cl.append(dict(pw=p * w, w=w, hi=p, lo=p, src={s}, n=1))
    out = []
    for c in cl:
        price = c["pw"] / c["w"]
        out.append(dict(price=price, raw=c["w"], touches=c["n"], sources=sorted(c["src"]),
                        type="support" if price < px else "resistance", dist_pct=(price / px - 1) * 100))
    mx = max(x["raw"] for x in out)
    for x in out: x["strength"] = round(100 * x["raw"] / mx)
    near = [x for x in out if abs(x["dist_pct"]) <= 15]
    near.sort(key=lambda x: -x["strength"]); near = near[:max_levels]; near.sort(key=lambda x: -x["price"])
    return near

# ---------------- risk flag ----------------
def ladder_risk(side, R, ext, depth_pct=6.0):
    """side long/short. returns (flag, reasons[]). AVOID > CAUTION > OK. Risk filter only."""
    sg = 1 if side == "long" else -1; avoid, caution = [], []
    h4, h1, d1 = R.get("4h"), R.get("1h"), R.get("1d")
    def against(x): return x and ((sg == 1 and x["ndi"] > x["pdi"]) or (sg == -1 and x["pdi"] > x["ndi"]))
    if h4 and h4["adx"] > 30 and against(h4) and sg * h4["structure_score"] < 0:
        avoid.append(f"4h trend mạnh ngược chiều thang (ADX {h4['adx']:.0f}, DI ngược, cấu trúc {h4['structure']})")
    elif h4 and h4["adx"] > 30 and against(h4):
        caution.append(f"4h ADX {h4['adx']:.0f} với DI ngược chiều thang")
    if h1 and h1["last_range_atr"] > 3:
        avoid.append(f"nến 1h gần nhất biên độ {h1['last_range_atr']:.1f}x ATR1h (biến động sốc)")
    if ext.get("range_1h_atr", 0) > 3:
        avoid.append(f"biên độ 60 phút gần nhất = {ext['range_1h_atr']:.1f}x ATR1h")
    if d1 and d1["bias"] == ("giảm" if sg == 1 else "tăng") and h4 and h4["bias"] == d1["bias"]:
        caution.append(f"1d và 4h cùng thiên {d1['bias']} (ngược chiều thang)")
    if h1 and h1["adx"] > 35 and against(h1): caution.append(f"1h ADX {h1['adx']:.0f} DI ngược chiều")
    if h4 and "squeeze" in h4["regime"]: caution.append("4h Bollinger squeeze → dễ bung mạnh 1 chiều")
    if h1 and h1["atr_pct_rank"] >= 90: caution.append(f"ATR1h ở phân vị {h1['atr_pct_rank']:.0f} (biến động cao)")
    if d1 and d1["atr_pct"] > depth_pct * 0.8: caution.append(f"ATR 1d {d1['atr_pct']:.1f}% ~ độ sâu thang {depth_pct:.1f}%")
    fr = ext.get("funding"); frp = ext.get("funding_pctile")
    if fr is not None:
        crowded = (sg == 1 and fr > 0) or (sg == -1 and fr < 0)
        if abs(fr) >= 0.0005 or (frp is not None and crowded and (frp >= 95 if sg == 1 else frp <= 5)):
            caution.append(f"funding cực trị {fr*100:.4f}% (phân vị 30 ngày {frp:.0f}) – phe {side} đông")
    for tf in ("1h", "4h"):
        x = R.get(tf)
        if x:
            for d in x["rsi_divergence"]:
                if (sg == 1 and d.startswith("bearish")) or (sg == -1 and d.startswith("bullish")):
                    caution.append(f"phân kỳ RSI {tf} {d.split(' ')[0]} (ngược chiều thang)")
    flag = "AVOID" if avoid else "CAUTION" if caution else "OK"
    return flag, avoid + caution

# ---------------- full analysis ----------------
def analyze(C, now_ms, ext=None, vp_days=14):
    """C: dict tf -> candles (keys 15m,1h,4h,1d; 15m should cover >= vp_days). ext: funding/oi/ls extras."""
    ext = dict(ext or {})
    R = {tf: analyze_tf(tf, K) for tf, K in C.items() if K is not None and len(K["c"]) >= 30}
    k15 = C["15m"]; px = float(k15["c"][-1]); ts15 = np.asarray(k15["ts"])
    m24 = ts15 >= now_ms - 86400e3; m7 = ts15 >= now_ms - 7 * 86400e3; m1h = ts15 >= now_ms - 3600e3
    hi24, lo24 = float(np.max(k15["h"][m24])), float(np.min(k15["l"][m24]))
    hi7, lo7 = float(np.max(k15["h"][m7])), float(np.min(k15["l"][m7]))
    atr1h = R["1h"]["atr"]
    ext["range_1h_atr"] = (float(np.max(k15["h"][m1h])) - float(np.min(k15["l"][m1h]))) / atr1h if m1h.any() else 0
    day0 = int(now_ms // 86400000 * 86400000)
    vw_d = vwap(k15, day0)
    i_lo = int(np.argmin(np.where(m7, k15["l"], np.inf))); i_hi = int(np.argmax(np.where(m7, k15["h"], -np.inf)))
    vw_lo, vw_hi = vwap(k15, ts15[i_lo]), vwap(k15, ts15[i_hi])
    mvp = ts15 >= now_ms - vp_days * 86400e3
    vp = volume_profile({x: np.asarray(k15[x])[mvp] for x in "hlv"})
    extra = [("POC", vp["poc"], 4), ("VAH", vp["vah"], 2.5), ("VAL", vp["val"], 2.5),
             ("24h high", hi24, 2), ("24h low", lo24, 2), ("7d high", hi7, 3), ("7d low", lo7, 3),
             ("VWAP ngày", vw_d, 1), ("AVWAP từ đáy 7d", vw_lo, 1.5), ("AVWAP từ đỉnh 7d", vw_hi, 1.5)]
    extra += [("HVN", p, 2 * s) for p, s in vp["hvn"]]
    levels = key_levels(px, {tf: R[tf] for tf in ("1h", "4h", "1d") if tf in R}, extra, atr1h)
    c1h = C["1h"]["c"]; c4 = C["4h"]["c"]; c1d = C["1d"]["c"]
    chg = dict(ch_1h=(px / c1h[-2] - 1) * 100 if len(c1h) > 1 else None, ch_4h=(px / c4[-2] - 1) * 100 if len(c4) > 1 else None,
               ch_24h=(px / C["1h"]["c"][-25] - 1) * 100 if len(c1h) > 25 else None, ch_7d=(px / c1d[-8] - 1) * 100 if len(c1d) > 8 else None)
    risk = {s: dict(zip(("flag", "reasons"), ladder_risk(s, R, ext))) for s in ("long", "short")}
    votes = [R[t]["score"] for t in ("1h", "4h", "1d") if t in R]
    trend_tfs = [t for t in ("1h", "4h", "1d") if t in R and R[t]["adx"] >= 25]
    overall = "trend" if len(trend_tfs) >= 2 else "range" if all(R[t]["adx"] < 22 for t in ("1h", "4h") if t in R) else "hỗn hợp"
    return dict(price=px, now_ms=now_ms, changes=chg, hi24=hi24, lo24=lo24, hi7d=hi7, lo7d=lo7,
                dist_hi24_pct=(px / hi24 - 1) * 100, dist_lo24_pct=(px / lo24 - 1) * 100,
                vwap_day=vw_d, avwap_7d_low=vw_lo, avwap_7d_high=vw_hi, volume_profile=vp, levels=levels,
                tf={t: {k: v for k, v in x.items() if not k.startswith("_")} for t, x in R.items()},
                regime=overall, mtf_score=round(float(sum(votes)), 2), ext=ext, risk=risk,
                disclaimer="Bộ lọc rủi ro cho thang DCA, KHÔNG phải dự báo giá.")

def levels_for_snap(A, side, min_strength=0):
    """(prices, strengths) arrays of supports (long) / resistances (short)."""
    t = "support" if side == "long" else "resistance"
    L = [x for x in A["levels"] if x["type"] == t and x["strength"] >= min_strength]
    return np.array([x["price"] for x in L], float), np.array([x["strength"] for x in L], float)
