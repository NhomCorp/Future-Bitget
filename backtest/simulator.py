#!/usr/bin/env python3
"""Neutral futures DCA+partial-TP simulator (Bitget USDT-M hedge, cross)."""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Tuple
import pandas as pd


@dataclass
class Params:
    start_equity: float = 300.0
    base_notional: float = 150.0
    d: float = 0.003
    m: float = 1.5
    N: int = 6
    tp1: float = 0.0025
    tp2: float = 0.005
    tp1_frac: float = 0.5
    s: float = 0.01
    notional_cap_mult: float = 15.0
    mm_rate: float = 0.005
    fee_open: float = 0.0002
    fee_tp: float = 0.0004
    fee_stop: float = 0.0006
    enable_stop: bool = True
    symbols: Tuple[str, ...] = ("BTCUSDT", "ETHUSDT")


@dataclass
class LegState:
    # packed arrays for speed: prices[], coins[]
    prices: List[float] = field(default_factory=list)
    coins: List[float] = field(default_factory=list)
    notionals: List[float] = field(default_factory=list)
    tp1_done: bool = False
    pending_reopen: bool = True
    trip_pnl: float = 0.0  # realized since last full open cycle


@dataclass
class BacktestResult:
    final_equity: float
    net_pnl: float
    total_fees: float
    gross_profit: float
    fee_pct_of_gross: float
    max_dd_usdt: float
    max_dd_pct: float
    n_hard_stops: int
    hard_stop_loss: float
    liquidated: bool
    liquidated_at: Optional[object]
    n_round_trips: int
    n_wins: int
    win_rate: float
    worst_day_pnl: float
    worst_day: Optional[object]
    daily_pnl: List[Tuple[object, float]]
    equity_curve: List[Tuple[object, float]]
    params: dict
    n_bars: int
    start_ts: object
    end_ts: object


class Simulator:
    def __init__(self, params: Params, active_sides: Optional[set] = None):
        self.p = params
        self.balance = params.start_equity
        self.fees = 0.0
        self.gross_wins = 0.0
        self.n_stops = 0
        self.stop_loss_total = 0.0
        self.liquidated = False
        self.liquidated_at = None
        self.round_trips = 0
        self.wins = 0
        self.equity_curve: List[Tuple] = []
        self.daily_close_eq: Dict = {}
        self.peak_equity = params.start_equity
        self.max_dd = 0.0
        self.max_dd_pct = 0.0
        self.active_sides = active_sides  # e.g. {("TEST","long")} or None=all
        self.legs: Dict[Tuple[str, str], LegState] = {}
        for sym in params.symbols:
            for side in ("long", "short"):
                leg = LegState()
                if self.active_sides is not None and (sym, side) not in self.active_sides:
                    leg.pending_reopen = False
                self.legs[(sym, side)] = leg

    def _coins(self, leg: LegState) -> float:
        return sum(leg.coins) if leg.coins else 0.0

    def _notional(self, leg: LegState) -> float:
        return sum(leg.notionals) if leg.notionals else 0.0

    def _avg(self, leg: LegState) -> float:
        c = self._coins(leg)
        if c <= 0:
            return 0.0
        return sum(p * c_ for p, c_ in zip(leg.prices, leg.coins)) / c

    def total_open_notional(self) -> float:
        return sum(self._notional(L) for L in self.legs.values())

    def unrealized(self, marks: Dict[str, float]) -> float:
        u = 0.0
        for (sym, side), leg in self.legs.items():
            c = self._coins(leg)
            if c <= 0:
                continue
            avg = self._avg(leg)
            mark = marks[sym]
            if side == "long":
                u += c * (mark - avg)
            else:
                u += c * (avg - mark)
        return u

    def equity(self, marks: Dict[str, float]) -> float:
        return self.balance + self.unrealized(marks)

    def _fee(self, amount: float):
        self.balance -= amount
        self.fees += amount

    def _can_open(self, notional: float, marks: Dict[str, float]) -> bool:
        eq = self.equity(marks)
        cap = self.p.notional_cap_mult * max(eq, 0.0)
        return self.total_open_notional() + notional <= cap + 1e-9

    def _open_layer(self, leg: LegState, price: float, notional: float, marks) -> bool:
        if not self._can_open(notional, marks):
            return False
        coins = notional / price
        self._fee(notional * self.p.fee_open)
        leg.prices.append(price)
        leg.coins.append(coins)
        leg.notionals.append(notional)
        leg.tp1_done = False
        return True

    def _close_frac(self, leg: LegState, side: str, symbol: str, frac: float,
                    price: float, fee_rate: float, kind: str) -> float:
        """Close `frac` of current coins. Returns pnl before fee."""
        total_c = self._coins(leg)
        if total_c <= 0 or frac <= 0:
            return 0.0
        frac = min(1.0, frac)
        coins_close = total_c * frac
        avg = self._avg(leg)
        if side == "long":
            pnl = coins_close * (price - avg)
        else:
            pnl = coins_close * (avg - price)
        fee = coins_close * price * fee_rate
        self.balance += pnl
        self._fee(fee)
        leg.trip_pnl += pnl - fee
        if pnl > 0:
            self.gross_wins += pnl

        if frac >= 1.0 - 1e-12:
            if kind == "stop":
                self.n_stops += 1
                self.stop_loss_total += pnl  # typically negative
            self.round_trips += 1
            if leg.trip_pnl > 0:
                self.wins += 1
            leg.prices.clear()
            leg.coins.clear()
            leg.notionals.clear()
            leg.tp1_done = False
            leg.pending_reopen = True
            leg.trip_pnl = 0.0
        else:
            remain = 1.0 - frac
            leg.coins = [c * remain for c in leg.coins]
            leg.notionals = [n * remain for n in leg.notionals]
        return pnl

    def _adverse(self, key, leg: LegState, adverse_px: float, marks: Dict[str, float]):
        sym, side = key
        if not leg.prices:
            return
        p = self.p
        # DCA ladder
        while len(leg.prices) < p.N:
            last = leg.prices[-1]
            n_idx = len(leg.prices)
            next_notional = p.base_notional * (p.m ** n_idx)
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
        # hard stop
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

    def _favorable(self, key, leg: LegState, fav_px: float, marks: Dict[str, float]):
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

    def _liquidate(self, ts, marks):
        self.liquidated = True
        self.liquidated_at = ts
        for key, leg in self.legs.items():
            if self._coins(leg) > 0:
                sym, side = key
                self._close_frac(leg, side, sym, 1.0, marks[sym], self.p.fee_stop, "liq")
        self.balance = max(0.0, self.balance)
        self.equity_curve.append((ts, max(0.0, self.equity(marks))))

    def step(self, ts, o: Dict[str, float], h: Dict[str, float],
             l: Dict[str, float], c: Dict[str, float]):
        if self.liquidated:
            return
        marks = dict(o)
        # reopen
        for key, leg in self.legs.items():
            sym, side = key
            if leg.pending_reopen and not leg.prices:
                if self._open_layer(leg, o[sym], self.p.base_notional, marks):
                    leg.pending_reopen = False
                    leg.trip_pnl = 0.0

        if self.equity(marks) <= self.p.mm_rate * self.total_open_notional() and self.total_open_notional() > 0:
            self._liquidate(ts, marks)
            return

        # adverse all
        for key, leg in self.legs.items():
            sym, side = key
            adv = l[sym] if side == "long" else h[sym]
            marks[sym] = adv
            self._adverse(key, leg, adv, marks)
            if self.liquidated:
                return

        if self.equity(marks) <= self.p.mm_rate * self.total_open_notional() and self.total_open_notional() > 0:
            self._liquidate(ts, {s: c[s] for s in self.p.symbols})
            # use more adverse? keep close for liq mark
            return

        # favorable all
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
            self.max_dd_pct = (dd / self.peak_equity) if self.peak_equity > 0 else 0.0
        day = ts.floor("D") if hasattr(ts, "floor") else pd.Timestamp(ts).floor("D")
        self.daily_close_eq[day] = eq

    def result(self) -> BacktestResult:
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
        return BacktestResult(
            final_equity=final,
            net_pnl=final - start_eq,
            total_fees=self.fees,
            gross_profit=self.gross_wins,
            fee_pct_of_gross=fee_pct,
            max_dd_usdt=self.max_dd,
            max_dd_pct=self.max_dd_pct * 100.0,
            n_hard_stops=self.n_stops,
            hard_stop_loss=self.stop_loss_total,
            liquidated=self.liquidated,
            liquidated_at=self.liquidated_at,
            n_round_trips=self.round_trips,
            n_wins=self.wins,
            win_rate=wr,
            worst_day_pnl=worst,
            worst_day=worst_day,
            daily_pnl=daily_pnl,
            equity_curve=self.equity_curve,
            params=asdict(self.p),
            n_bars=len(self.equity_curve),
            start_ts=self.equity_curve[0][0] if self.equity_curve else None,
            end_ts=self.equity_curve[-1][0] if self.equity_curve else None,
        )


def align_data(data: Dict[str, pd.DataFrame], symbols: Tuple[str, ...]) -> pd.DataFrame:
    frames = []
    for sym in symbols:
        d = data[sym][["ts", "open", "high", "low", "close"]].copy()
        d.columns = ["ts", f"{sym}_o", f"{sym}_h", f"{sym}_l", f"{sym}_c"]
        frames.append(d)
    m = frames[0]
    for f in frames[1:]:
        m = m.merge(f, on="ts", how="inner")
    return m.sort_values("ts").reset_index(drop=True)


def run_backtest(data: Dict[str, pd.DataFrame], params: Params,
                 active_sides=None) -> BacktestResult:
    merged = align_data(data, params.symbols)
    sim = Simulator(params, active_sides=active_sides)
    # column index access for speed
    ts_a = merged["ts"].values
    cols = {}
    for sym in params.symbols:
        cols[sym] = (
            merged[f"{sym}_o"].to_numpy(),
            merged[f"{sym}_h"].to_numpy(),
            merged[f"{sym}_l"].to_numpy(),
            merged[f"{sym}_c"].to_numpy(),
        )
    n = len(merged)
    for i in range(n):
        o, h, l, c = {}, {}, {}, {}
        for sym in params.symbols:
            oo, hh, ll, cc = cols[sym]
            o[sym] = float(oo[i])
            h[sym] = float(hh[i])
            l[sym] = float(ll[i])
            c[sym] = float(cc[i])
        sim.step(pd.Timestamp(ts_a[i]), o, h, l, c)
        if sim.liquidated:
            break
    return sim.result()


def sanity_check() -> str:
    """Hand-checked: long-only, B=100, d=1%, m=2, N=2, TP 1%/2%."""
    p = Params(
        start_equity=300, base_notional=100, d=0.01, m=2.0, N=2,
        tp1=0.01, tp2=0.02, s=0.05, enable_stop=False,
        symbols=("TEST",), fee_open=0.0002, fee_tp=0.0004,
        notional_cap_mult=100.0,
    )
    # Hand:
    # Open @100, notional 100, coins=1, fee=0.02
    # DCA @99 (=100*0.99), notional 200, coins=200/99, fee=0.04
    # avg = (100*1 + 99*(200/99)) / (1+200/99) = (100+200)/(1+2.020202) = 300/3.020202 = 99.331126
    c1, c2 = 1.0, 200.0 / 99.0
    avg = (100 * c1 + 99 * c2) / (c1 + c2)
    assert abs(avg - 99.3311036789) < 1e-6
    tp1 = avg * 1.01
    # After TP1 close 50%: coins left = half, pnl = 0.5*(c1+c2)*(tp1-avg) = 0.5*total_c*avg*0.01
    total_c = c1 + c2
    pnl_tp1 = 0.5 * total_c * (tp1 - avg)
    fee_tp1 = 0.5 * total_c * tp1 * 0.0004
    # Then TP2 at avg*1.02 (avg unchanged after proportional close)
    tp2 = avg * 1.02
    pnl_tp2 = 0.5 * total_c * (tp2 - avg)
    fee_tp2 = 0.5 * total_c * tp2 * 0.0004
    open_fees = 0.06
    hand_net = pnl_tp1 + pnl_tp2 - open_fees - fee_tp1 - fee_tp2

    rows = [
        {"ts": pd.Timestamp("2026-01-01 00:00", tz="UTC"), "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0},
        {"ts": pd.Timestamp("2026-01-01 00:01", tz="UTC"), "open": 100.0, "high": 100.0, "low": 98.5, "close": 99.0},
        {"ts": pd.Timestamp("2026-01-01 00:02", tz="UTC"), "open": 99.0, "high": tp2 + 1.0, "low": 99.0, "close": tp2},
    ]
    # After full close on bar2, bar3 would reopen — stop data before that affects equity much
    df = pd.DataFrame(rows)
    # only 3 bars; after close on bar2 pending reopen; no bar3 so final equity = balance
    data = {"TEST": df}
    res = run_backtest(data, p, active_sides={("TEST", "long")})
    # After full close equity should be start + hand_net (no open position)
    # But wait: on bar2 after close, pending_reopen — reopen happens at START of next bar only.
    # So final = 300 + hand_net
    expected = 300.0 + hand_net
    lines = [
        f"hand avg={avg:.6f} tp1={tp1:.6f} tp2={tp2:.6f}",
        f"hand pnl_tp1={pnl_tp1:.6f} pnl_tp2={pnl_tp2:.6f} fees_open={open_fees:.6f}",
        f"hand fee_tp={fee_tp1+fee_tp2:.6f} hand_net={hand_net:.6f} expected_eq={expected:.6f}",
        f"sim final_equity={res.final_equity:.6f} fees={res.total_fees:.6f}",
        f"sim round_trips={res.n_round_trips} wins={res.n_wins}",
        f"diff={res.final_equity - expected:.8f}",
    ]
    if abs(res.final_equity - expected) < 0.02 and res.n_round_trips == 1:
        lines.append("SANITY_OK")
    else:
        lines.append("SANITY_FAIL")
    return "\n".join(lines)
