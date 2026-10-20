#!/usr/bin/env python3
"""Run baseline, no-stop, and sensitivity grid; write CSVs + equity PNG."""
from __future__ import annotations

import itertools
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from simulator import Params, run_backtest, sanity_check

ROOT = Path("/workspace/bitget/backtest")
CACHE = ROOT / "cache"
OUT = ROOT


def load_data():
    data = {}
    for sym in ("BTCUSDT", "ETHUSDT"):
        df = pd.read_pickle(CACHE / f"{sym}_1m.pkl")
        data[sym] = df
        print(f"loaded {sym}: {len(df)} bars {df['ts'].iloc[0]} .. {df['ts'].iloc[-1]}")
    return data


def save_daily(res, path: Path):
    rows = [{"date": d, "daily_pnl": pnl} for d, pnl in res.daily_pnl]
    pd.DataFrame(rows).to_csv(path, index=False)


def plot_equity(res, path: Path, title: str):
    if not res.equity_curve:
        return
    # downsample for plot
    step = max(1, len(res.equity_curve) // 5000)
    xs = [res.equity_curve[i][0] for i in range(0, len(res.equity_curve), step)]
    ys = [res.equity_curve[i][1] for i in range(0, len(res.equity_curve), step)]
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(xs, ys, lw=0.8, color="#2563eb")
    ax.set_title(title)
    ax.set_ylabel("Equity (USDT)")
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def fmt_res(name: str, res) -> str:
    liq = "YES @ " + str(res.liquidated_at) if res.liquidated else "NO"
    return (
        f"=== {name} ===\n"
        f"final_equity={res.final_equity:.2f}  net_pnl={res.net_pnl:.2f}\n"
        f"fees={res.total_fees:.2f}  fee%_of_gross={res.fee_pct_of_gross:.1f}%  gross_wins={res.gross_profit:.2f}\n"
        f"max_dd={res.max_dd_usdt:.2f} USDT ({res.max_dd_pct:.1f}%)\n"
        f"hard_stops={res.n_hard_stops}  stop_pnl_sum={res.hard_stop_loss:.2f}\n"
        f"liquidated={liq}\n"
        f"round_trips={res.n_round_trips}  wins={res.n_wins}  win_rate={res.win_rate:.1f}%\n"
        f"worst_day={res.worst_day}  worst_day_pnl={res.worst_day_pnl:.2f}\n"
        f"bars={res.n_bars}  range={res.start_ts} .. {res.end_ts}\n"
    )


def main():
    print(sanity_check())
    print()
    data = load_data()

    baseline = Params()
    print("Running baseline...")
    res = run_backtest(data, baseline)
    print(fmt_res("BASELINE", res))
    save_daily(res, OUT / "daily_pnl_baseline.csv")
    plot_equity(res, OUT / "equity_baseline.png",
                f"Baseline equity (d=0.3% m=1.5 N=6) final={res.final_equity:.1f}")

    print("Running baseline NO STOP (gong)...")
    nostop = Params(enable_stop=False)
    res_ns = run_backtest(data, nostop)
    print(fmt_res("BASELINE_NO_STOP", res_ns))
    save_daily(res_ns, OUT / "daily_pnl_nostop.csv")
    plot_equity(res_ns, OUT / "equity_nostop.png",
                f"No-stop equity final={res_ns.final_equity:.1f}")

    # sensitivity
    print("Running sensitivity grid...")
    ds = [0.002, 0.003, 0.005]
    ms = [1.0, 1.5, 2.0]
    Ns = [4, 6, 8]
    rows = []
    for d, m, N in itertools.product(ds, ms, Ns):
        p = Params(d=d, m=m, N=N)
        r = run_backtest(data, p)
        rows.append({
            "d_pct": d * 100,
            "m": m,
            "N": N,
            "final_equity": round(r.final_equity, 2),
            "net_pnl": round(r.net_pnl, 2),
            "max_dd_usdt": round(r.max_dd_usdt, 2),
            "max_dd_pct": round(r.max_dd_pct, 2),
            "n_hard_stops": r.n_hard_stops,
            "hard_stop_loss": round(r.hard_stop_loss, 2),
            "liquidated": r.liquidated,
            "win_rate": round(r.win_rate, 2),
            "round_trips": r.n_round_trips,
            "fees": round(r.total_fees, 2),
        })
        print(f"  d={d*100:.1f}% m={m} N={N} -> eq={r.final_equity:.1f} "
              f"dd={r.max_dd_usdt:.1f} stops={r.n_hard_stops} liq={r.liquidated}")

    grid = pd.DataFrame(rows)
    grid.to_csv(OUT / "sensitivity_grid.csv", index=False)

    # robust: no liq, good return, lowest DD
    ok = grid[~grid["liquidated"]].copy()
    if len(ok) == 0:
        print("No non-liquidated combos!")
        top = grid.sort_values("final_equity", ascending=False).head(3)
    else:
        # score: prefer high equity, low DD
        ok["score"] = ok["final_equity"] / (1.0 + ok["max_dd_usdt"])
        top = ok.sort_values(["score", "final_equity"], ascending=False).head(3)

    print("\nTOP ROBUST COMBOS:")
    print(top.to_string(index=False))
    top.to_csv(OUT / "top_robust_combos.csv", index=False)

    # write summary txt
    summary = []
    summary.append(fmt_res("BASELINE", res))
    summary.append(fmt_res("BASELINE_NO_STOP", res_ns))
    summary.append("TOP ROBUST:\n" + top.to_string(index=False))
    (OUT / "summary.txt").write_text("\n".join(summary))
    print("Wrote outputs to", OUT)


if __name__ == "__main__":
    main()
