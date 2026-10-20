# planner/
- `ladder.py`  – in bảng thang DCA + CSV (giá live, ATR 1h/4h, EMA50, ADX từ nến public). Ví dụ:
  `python3 ladder.py --symbol ETHUSDT --side long --equity 524.87`  (mặc định = phương án DEFAULT, 1 thang = 1.25x equity)
  `python3 ladder.py --symbol BTCUSDT --side short --equity 524.87 --cap 2 --stop 7`  (thang của phương án MẠNH TAY)
  `python3 ladder.py --symbol ETHUSDT --side long --spacing atr --atr-mult 2 --layers 7 --mult 1.2 --tp 0.8 --part 1`
- `sim.py` (numba engine), `run_grid.py`, `run_grid2.py`, `combined_grid.py`, `final_eval.py`, `analyze*.py`, `neighbors.py`
- `recap.py` → `recap.json`, `recap_positions.csv`, `recap_exposure_1m.csv`
- `fetch_data.py` / `fetch_data180.py` / `fill_gaps.py` → `data/` (90d), `data180/` (180d), `data/funding.json`
- `PLAN.md`, `equity_top3.png`, `results/`
