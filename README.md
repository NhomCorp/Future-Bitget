# Bitget DCA ladder tools (WIP)

Python scripts for monitoring a Bitget USDT-M futures account (read-only), journaling orders, backtesting DCA ladders and planning ladder orders.

- `bg.py`, `monitor.py`: read-only account/position monitor (Bitget v2 API).
- `journal/`: order/fill/position journal sync + daily style digest.
- `backtest/`, `planner/`: 1m-candle DCA ladder backtests, `ladder.py` ladder calculator, `PLAN.md`.
- `trader/`: **unfinished** semi-auto order tool (TA module `ta.py`, API wrapper `bgapi.py`). Not tested against live trading; do not use with a trade key as-is.
- `frontend/`: local-only Demo/dry-run zone desk. It uses browser local storage and never calls Bitget.

## Mở demo frontend local

Không cần cài thêm package. Chạy từ thư mục repo:

```bash
python -m http.server 4173 --directory frontend
```

Sau đó mở `http://localhost:4173`. Giao diện hỗ trợ tạo zone preview, kích hoạt local và ghi observation mock. Dữ liệu chỉ được lưu trong local storage của trình duyệt.

Secrets come only from env vars (`BITGET_API_KEY`, `BITGET_API_SECRET`, `BITGET_PASSPHRASE`; trade key later as `BITGET_TRADE_*`). No data files or account history are committed.
