# Bitget DCA ladder tools (WIP)

Python scripts for monitoring a Bitget USDT-M futures account (read-only), journaling orders, backtesting DCA ladders and planning ladder orders.

- `bg.py`, `monitor.py`: read-only account/position monitor (Bitget v2 API).
- `journal/`: order/fill/position journal sync + daily style digest.
- `backtest/`, `planner/`: 1m-candle DCA ladder backtests, `ladder.py` ladder calculator, `PLAN.md`.
- `trader/`: **unfinished** semi-auto order tool (TA module `ta.py`, API wrapper `bgapi.py`). Not tested against live trading; do not use with a trade key as-is.

Secrets come only from env vars (`BITGET_API_KEY`, `BITGET_API_SECRET`, `BITGET_PASSPHRASE`; trade key later as `BITGET_TRADE_*`). No data files or account history are committed.
