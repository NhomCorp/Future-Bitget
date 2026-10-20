#!/usr/bin/env python3
"""User-style variants: fade-1h entry, equity-scaled base, (a) faithful (b) tamed."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path("/workspace/bitget/backtest")
CACHE = ROOT / "cache"


@dataclass
class Params:
    start_equity: float = 300.0
    base_notional: float = 150.0  # used if base_equity_mult is None
    base_equity_mult: Optional[float] = None  # if set, B = mult * equity at open
    d: float = 0.0018
    m: float = 0.87
    N: int = 16
    tp1: float = 0.0025
    tp2: float = 0.0045
    tp1_frac: float = 0.5
    s: float = 0.01
    notional_cap_mult: float = 49.0
    mm_rate: float = 0.005
    fee_open: float = 0.0002
    fee_tp: float = 0.0004
    fee_stop: float = 0.0006
    enable_stop: bool = False
    fade_1h: bool = True
    symbols: Tuple[str, ...] = ("BTCUSDT", "ETHUSDT")


@dataclass
class LegState:
    prices: List[float] = field(default_factory=list)
    coins: List[float] = field(default_factory=list)
    notionals: List[float] = field(default_factory=list)
    tp1_done: bool = False
    pending_reopen: bool = True
    trip_pnl: float = 0.0


class Simulator:
    def __init__(self, params: Params):
        self.p = params
        self.balance = params.start_equity
        self.fees = 0.0
        self.gross_wins = 0.0
        self.n_stops = 0
        self.stop_loss_total = 0.0
        self.liquidated = False
        self.liquidated_at = None
        self.liq_info = None
        self.round_trips = 0
        self.wins = 0
        self.equity_curve: List[Tuple] = []
        self.daily_close_eq: Dict = {}
        self.peak_equity = params.start_equity
        self.max_dd = 0.0
        self.max_dd_pct = 0.0
        self.legs: Dict[Tuple[str, str], LegState] = {}
        for sym in params.symbols:
            for side in ("long", "short"):
                self.legs[(sym, side)] = LegState()
        # lookback closes for fade: list per symbol of recent closes
        self._closes: Dict[str, List[float]] = {s: [] for s in params.symbols}
        self._close_ts: List = []

    def _coins(self, leg): return sum(leg.coins) if leg.coins else 0.0
    def _notional(self, leg): return sum(leg.notionals) if leg.notionals else 0.0

    def _avg(self, leg):
        c = self._coins(leg)
        if c <= 0: return 0.0
        return sum(p * c_ for p, c_ in zip(leg.prices, leg.coins)) / c

    def total_open_notional(self):
        return sum(self._notional(L) for L in self.legs.values())

    def unrealized(self, marks):
        u = 0.0
        for (sym, side), leg in self.legs.items():
            c = self._coins(leg)
            if c <= 0: continue
            avg = self._avg(leg)
            mark = marks[sym]
            u += c * (mark - avg) if side == "long" else c * (avg - mark)
        return u

    def equity(self, marks):
        return self.balance + self.unrealized(marks)

    def _fee(self, amount):
        self.balance -= amount
        self.fees += amount

    def _base_size(self, marks) -> float:
        if self.p.base_equity_mult is not None:
            return max(0.0, self.equity(marks)) * self.p.base_equity_mult
        return self.p.base_notional

    def _can_open(self, notional, marks):
        eq = self.equity(marks)
        cap = self.p.notional_cap_mult * max(eq, 0.0)
        return notional > 0 and self.total_open_notional() + notional <= cap + 1e-9

    def _fade_ok(self, sym: str, side: str) -> bool:
        if not self.p.fade_1h:
            return True
        hist = self._closes[sym]
        if len(hist) < 61:
            return False  # not enough history
        # prior 1h move: close_now_proxy = last appended is previous bar's close;
        # at decision we use current open vs close 60 bars ago.
        # hist currently holds closes UP TO previous bar; caller passes cur_open separately.
        return True  # placeholder; real check in _fade_ok_price

    def _fade_ok_price(self, sym: str, side: str, cur_open: float) -> bool:
        if not self.p.fade_1h:
            return True
        hist = self._closes[sym]
        if len(hist) < 60:
            return False
        ref = hist[-60]  # close from 60 minutes ago
        chg = (cur_open - ref) / ref
        if side == "long":
            return chg < 0  # price fell -> long fade
        else:
            return chg > 0  # price rose -> short fade

    def _open_layer(self, leg, price, notional, marks) -> bool:
        if not self._can_open(notional, marks):
            return False
        self._fee(notional * self.p.fee_open)
        leg.prices.append(price)
        leg.coins.append(notional / price)
        leg.notionals.append(notional)
        leg.tp1_done = False
        return True

    def _close_frac(self, leg, side, symbol, frac, price, fee_rate, kind):
        total_c = self._coins(leg)
        if total_c <= 0 or frac <= 0:
            return 0.0
        frac = min(1.0, frac)
        coins_close = total_c * frac
        avg = self._avg(leg)
        pnl = coins_close * (price - avg) if side == "long" else coins_close * (avg - price)
        fee = coins_close * price * fee_rate
        self.balance += pnl
        self._fee(fee)
        leg.trip_pnl += pnl - fee
        if pnl > 0:
            self.gross_wins += pnl
        if frac >= 1.0 - 1e-12:
            if kind == "stop":
                self.n_stops += 1
                self.stop_loss_total += pnl
            self.round_trips += 1
            if leg.trip_pnl > 0:
                self.wins += 1
            leg.prices.clear(); leg.coins.clear(); leg.notionals.clear()
            leg.tp1_done = False
            leg.pending_reopen = True
            leg.trip_pnl = 0.0
        else:
            remain = 1.0 - frac
            leg.coins = [c * remain for c in leg.coins]
            leg.notionals = [n * remain for n in leg.notionals]
        return pnl

    def _adverse(self, key, leg, adverse_px, marks):
        sym, side = key
        if not leg.prices:
            return
        p = self.p
        while len(leg.prices) < p.N:
            last = leg.prices[-1]
            n_idx = len(leg.prices)
            # size = previous_layer * m  == base * m^n_idx, but base may vary;
            # use last layer notional * m for faithfulness to "previous * m"
            next_notional = leg.notionals[-1] * p.m
            if side == "long":
                trig = last * (1.0 - p.d)
                if adverse_px <= trig + 1e-15:
                    if not self._open_layer(leg, trig, next_notional, marks):
                        break
                else:
                    break
            else:
                trig = last * (1.0 + p.d)
                if adverse_px >= trig - 1e-15:
                    if not self._open_layer(leg, trig, next_notional, marks):
                        break
                else:
                    break
        if p.enable_stop and len(leg.prices) >= p.N and leg.prices:
            last = leg.prices[-1]
            if side == "long":
                stop_px = last * (1.0 - p.s)
                if adverse_px <= stop_px + 1e-15:
                    self._close_frac(leg, side, sym, 1.0, stop_px, p.fee_stop, "stop")
            else:
                stop_px = last * (1.0 + p.s)
                if adverse_px >= stop_px - 1e-15:
                    self._close_frac(leg, side, sym, 1.0, stop_px, p.fee_stop, "stop")

    def _favorable(self, key, leg, fav_px, marks):
        sym, side = key
        if not leg.prices:
            return
        p = self.p
        avg = self._avg(leg)
        if side == "long":
            if not leg.tp1_done:
                tp1 = avg * (1.0 + p.tp1)
                if fav_px >= tp1 - 1e-15:
                    self._close_frac(leg, side, sym, p.tp1_frac, tp1, p.fee_tp, "tp1")
                    leg.tp1_done = True
            if leg.prices:
                avg2 = self._avg(leg)
                tp2 = avg2 * (1.0 + p.tp2)
                if fav_px >= tp2 - 1e-15:
                    self._close_frac(leg, side, sym, 1.0, tp2, p.fee_tp, "tp2")
        else:
            if not leg.tp1_done:
                tp1 = avg * (1.0 - p.tp1)
                if fav_px <= tp1 + 1e-15:
                    self._close_frac(leg, side, sym, p.tp1_frac, tp1, p.fee_tp, "tp1")
                    leg.tp1_done = True
            if leg.prices:
                avg2 = self._avg(leg)
                tp2 = avg2 * (1.0 - p.tp2)
                if fav_px <= tp2 + 1e-15:
                    self._close_frac(leg, side, sym, 1.0, tp2, p.fee_tp, "tp2")

    def _snapshot_liq(self, ts, marks):
        legs_snap = []
        for (sym, side), leg in self.legs.items():
            if self._coins(leg) <= 0:
                continue
            avg = self._avg(leg)
            u = self._coins(leg) * ((marks[sym] - avg) if side == "long" else (avg - marks[sym]))
            legs_snap.append({
                "symbol": sym, "side": side, "layers": len(leg.prices),
                "notional": round(self._notional(leg), 2),
                "avg": round(avg, 4), "mark": marks[sym],
                "unrealized": round(u, 2),
            })
        moves = {}
        for sym in self.p.symbols:
            hist = self._closes[sym]
            if len(hist) >= 60:
                ref = hist[-60]
                moves[sym] = {
                    "chg_1h_pct": round((marks[sym] / ref - 1) * 100, 3),
                    "ref_1h": ref, "mark": marks[sym],
                }
            if len(hist) >= 1:
                moves.setdefault(sym, {})["chg_from_prev_close_pct"] = round(
                    (marks[sym] / hist[-1] - 1) * 100, 3)
        eq = self.equity(marks)
        tot = self.total_open_notional()
        # dominant loss leg
        worst = min(legs_snap, key=lambda x: x["unrealized"]) if legs_snap else None
        self.liq_info = {
            "ts": str(ts),
            "equity": round(eq, 2),
            "balance": round(self.balance, 2),
            "total_notional": round(tot, 2),
            "mm": round(self.p.mm_rate * tot, 2),
            "legs": legs_snap,
            "moves": moves,
            "worst_leg": worst,
        }

    def _liquidate(self, ts, marks):
        self._snapshot_liq(ts, marks)
        self.liquidated = True
        self.liquidated_at = ts
        for key, leg in self.legs.items():
            if self._coins(leg) > 0:
                sym, side = key
                self._close_frac(leg, side, sym, 1.0, marks[sym], self.p.fee_stop, "liq")
        self.balance = max(0.0, self.balance)
        self.equity_curve.append((ts, max(0.0, self.equity(marks))))

    def step(self, ts, o, h, l, c):
        if self.liquidated:
            return
        marks = dict(o)

        # reopen with fade filter + equity-scaled base
        for key, leg in self.legs.items():
            sym, side = key
            if leg.pending_reopen and not leg.prices:
                if self._fade_ok_price(sym, side, o[sym]):
                    B = self._base_size(marks)
                    if B > 1e-6 and self._open_layer(leg, o[sym], B, marks):
                        leg.pending_reopen = False
                        leg.trip_pnl = 0.0

        if self.total_open_notional() > 0 and self.equity(marks) <= self.p.mm_rate * self.total_open_notional():
            self._liquidate(ts, marks)
            return

        for key, leg in self.legs.items():
            sym, side = key
            adv = l[sym] if side == "long" else h[sym]
            marks[sym] = adv
            self._adverse(key, leg, adv, marks)
            if self.liquidated:
                return

        if self.total_open_notional() > 0 and self.equity(marks) <= self.p.mm_rate * self.total_open_notional():
            self._liquidate(ts, dict(marks))
            return

        for key, leg in self.legs.items():
            sym, side = key
            fav = h[sym] if side == "long" else l[sym]
            marks[sym] = fav
            self._favorable(key, leg, fav, marks)

        marks = dict(c)
        if self.total_open_notional() > 0 and self.equity(marks) <= self.p.mm_rate * self.total_open_notional():
            self._liquidate(ts, marks)
            return

        eq = self.equity(marks)
        self.equity_curve.append((ts, eq))
        if eq > self.peak_equity:
            self.peak_equity = eq
        dd = self.peak_equity - eq
        if dd > self.max_dd:
            self.max_dd = dd
            self.max_dd_pct = dd / self.peak_equity if self.peak_equity > 0 else 0.0
        day = pd.Timestamp(ts).floor("D")
        self.daily_close_eq[day] = eq

        # append closes for fade lookback AFTER processing
        for sym in self.p.symbols:
            self._closes[sym].append(c[sym])

    def result(self):
        start_eq = self.p.start_equity
        final = self.equity_curve[-1][1] if self.equity_curve else max(0.0, self.balance)
        days = sorted(self.daily_close_eq.keys())
        daily_pnl = []
        prev = start_eq
        worst_day = None
        worst = 0.0
        for d in days:
            pnl = self.daily_close_eq[d] - prev
            daily_pnl.append((d, pnl))
            if pnl < worst:
                worst = pnl
                worst_day = d
            prev = self.daily_close_eq[d]
        fee_pct = (self.fees / self.gross_wins * 100.0) if self.gross_wins > 0 else float("nan")
        wr = (self.wins / self.round_trips * 100.0) if self.round_trips else 0.0
        return {
            "final_equity": final,
            "net_pnl": final - start_eq,
            "total_fees": self.fees,
            "gross_profit": self.gross_wins,
            "fee_pct_of_gross": fee_pct,
            "max_dd_usdt": self.max_dd,
            "max_dd_pct": self.max_dd_pct * 100.0,
            "n_hard_stops": self.n_stops,
            "hard_stop_loss": self.stop_loss_total,
            "liquidated": self.liquidated,
            "liquidated_at": self.liquidated_at,
            "liq_info": self.liq_info,
            "n_round_trips": self.round_trips,
            "n_wins": self.wins,
            "win_rate": wr,
            "worst_day_pnl": worst,
            "worst_day": worst_day,
            "daily_pnl": daily_pnl,
            "equity_curve": self.equity_curve,
            "params": asdict(self.p),
            "n_bars": len(self.equity_curve),
            "start_ts": self.equity_curve[0][0] if self.equity_curve else None,
            "end_ts": self.equity_curve[-1][0] if self.equity_curve else None,
        }


def run(data, params: Params):
    frames = []
    for sym in params.symbols:
        d = data[sym][["ts", "open", "high", "low", "close"]].copy()
        d.columns = ["ts", f"{sym}_o", f"{sym}_h", f"{sym}_l", f"{sym}_c"]
        frames.append(d)
    merged = frames[0]
    for f in frames[1:]:
        merged = merged.merge(f, on="ts", how="inner")
    merged = merged.sort_values("ts").reset_index(drop=True)

    sim = Simulator(params)
    ts_a = merged["ts"].values
    cols = {sym: (
        merged[f"{sym}_o"].to_numpy(),
        merged[f"{sym}_h"].to_numpy(),
        merged[f"{sym}_l"].to_numpy(),
        merged[f"{sym}_c"].to_numpy(),
    ) for sym in params.symbols}

    for i in range(len(merged)):
        o, h, l, c = {}, {}, {}, {}
        for sym in params.symbols:
            oo, hh, ll, cc = cols[sym]
            o[sym] = float(oo[i]); h[sym] = float(hh[i])
            l[sym] = float(ll[i]); c[sym] = float(cc[i])
        sim.step(pd.Timestamp(ts_a[i]), o, h, l, c)
        if sim.liquidated:
            break
    return sim.result()


def plot_eq(res, path, title):
    ec = res["equity_curve"]
    if not ec:
        return
    step = max(1, len(ec) // 5000)
    xs = [ec[i][0] for i in range(0, len(ec), step)]
    ys = [ec[i][1] for i in range(0, len(ec), step)]
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(xs, ys, lw=0.8, color="#059669")
    ax.set_title(title)
    ax.set_ylabel("Equity (USDT)")
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def fmt(name, res):
    liq = "NO"
    if res["liquidated"]:
        info = res["liq_info"] or {}
        worst = info.get("worst_leg") or {}
        moves = info.get("moves") or {}
        move_str = ", ".join(
            f"{s} 1h={v.get('chg_1h_pct','?')}%" for s, v in moves.items()
        )
        liq = (
            f"YES @ {res['liquidated_at']} Asia/Saigon≈UTC+7 same clock on box; "
            f"eq={info.get('equity')} notional={info.get('total_notional')} mm={info.get('mm')}; "
            f"worst={worst.get('symbol')} {worst.get('side')} uPnL={worst.get('unrealized')} "
            f"notional={worst.get('notional')} layers={worst.get('layers')}; moves: {move_str}"
        )
    return (
        f"=== {name} ===\n"
        f"final_equity={res['final_equity']:.2f}  net_pnl={res['net_pnl']:.2f}\n"
        f"fees={res['total_fees']:.2f}  fee%_gross={res['fee_pct_of_gross']:.1f}%\n"
        f"max_dd={res['max_dd_usdt']:.2f} USDT ({res['max_dd_pct']:.1f}%)\n"
        f"hard_stops={res['n_hard_stops']}  stop_pnl={res['hard_stop_loss']:.2f}\n"
        f"liquidated={liq}\n"
        f"round_trips={res['n_round_trips']}  win_rate={res['win_rate']:.1f}%\n"
        f"worst_day={res['worst_day']} pnl={res['worst_day_pnl']:.2f}\n"
        f"bars={res['n_bars']}  {res['start_ts']} .. {res['end_ts']}\n"
    )


def main():
    data = {
        "BTCUSDT": pd.read_pickle(CACHE / "BTCUSDT_1m.pkl"),
        "ETHUSDT": pd.read_pickle(CACHE / "ETHUSDT_1m.pkl"),
    }
    print(f"data {data['BTCUSDT'].ts.iloc[0]} .. {data['BTCUSDT'].ts.iloc[-1]} n={len(data['BTCUSDT'])}")

    faithful = Params(
        base_equity_mult=10.0, d=0.0018, m=0.87, N=16,
        notional_cap_mult=49.0, tp1=0.0025, tp2=0.0045,
        enable_stop=False, fade_1h=True,
    )
    tamed = Params(
        base_equity_mult=2.0, d=0.0018, m=0.87, N=8,
        notional_cap_mult=15.0, tp1=0.0025, tp2=0.0045,
        s=0.01, enable_stop=True, fade_1h=True,
    )

    print("Running USER-STYLE FAITHFUL...")
    r_a = run(data, faithful)
    print(fmt("USER_STYLE_FAITHFUL", r_a))
    plot_eq(r_a, ROOT / "equity_user_faithful.png",
            f"User-style faithful final={r_a['final_equity']:.1f}")
    pd.DataFrame([{"date": d, "daily_pnl": p} for d, p in r_a["daily_pnl"]]).to_csv(
        ROOT / "daily_pnl_user_faithful.csv", index=False)
    if r_a["liq_info"]:
        (ROOT / "liq_user_faithful.json").write_text(json.dumps(r_a["liq_info"], indent=2, default=str))

    print("Running USER-STYLE TAMED...")
    r_b = run(data, tamed)
    print(fmt("USER_STYLE_TAMED", r_b))
    plot_eq(r_b, ROOT / "equity_user_tamed.png",
            f"User-style tamed final={r_b['final_equity']:.1f}")
    pd.DataFrame([{"date": d, "daily_pnl": p} for d, p in r_b["daily_pnl"]]).to_csv(
        ROOT / "daily_pnl_user_tamed.csv", index=False)
    if r_b["liq_info"]:
        (ROOT / "liq_user_tamed.json").write_text(json.dumps(r_b["liq_info"], indent=2, default=str))

    out = {
        "faithful": {k: v for k, v in r_a.items() if k not in ("equity_curve", "daily_pnl", "params")},
        "tamed": {k: v for k, v in r_b.items() if k not in ("equity_curve", "daily_pnl", "params")},
    }
    # stringify timestamps
    for block in out.values():
        for k in ("liquidated_at", "start_ts", "end_ts", "worst_day"):
            if block.get(k) is not None:
                block[k] = str(block[k])
    (ROOT / "user_style_results.json").write_text(json.dumps(out, indent=2, default=str))
    summary = fmt("USER_STYLE_FAITHFUL", r_a) + "\n" + fmt("USER_STYLE_TAMED", r_b)
    (ROOT / "user_style_summary.txt").write_text(summary)
    print("Done.")


if __name__ == "__main__":
    main()
