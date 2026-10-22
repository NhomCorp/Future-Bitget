# Bitget DCA ladder tools (WIP)

Python scripts for monitoring a Bitget USDT-M futures account (read-only), journaling orders, backtesting DCA ladders and planning ladder orders.

- `bg.py`, `monitor.py`: read-only account/position monitor (Bitget v2 API).
- `journal/`: order/fill/position journal sync + daily style digest.
- `backtest/`, `planner/`: 1m-candle DCA ladder backtests, `ladder.py` ladder calculator, `PLAN.md`.
- `trader/`: **unfinished** semi-auto order tool (TA module `ta.py`, API wrapper `bgapi.py`). Not tested against live trading; do not use with a trade key as-is.
- `frontend/`: local-only Demo/dry-run zone desk. It uses browser local storage and never calls Bitget.

## Mở demo frontend local

Cổng cố định `3007`. Không cần `npm install`. Chạy từ thư mục repo:

```bash
npm start
```

Sau đó mở `http://localhost:3007`. Nav trong-trang: Kết nối, Cấu hình AI, Mandate, Quyền AI, Phong cách, Tổng quan, Bàn zone, Nhật ký. Cấu hình AI lưu provider/model local; Gemini nhiều key ngang hàng (bốc ngẫu nhiên), OpenAI-compatible một key; nút Check live ping provider. Tổng quan là mock (ticker nhập tay, phiếu intent, tab rỗng). Kết nối hiện status Demo/env đủ-thiếu, không form secret; Phong cách và Nhật ký đang stub. Tạo zone preview, kích hoạt local và ghi observation mock. Dữ liệu chỉ lưu trong local storage; đổi trang không mất dữ liệu.

Cách khác (Python) chỉ phục vụ file tĩnh, không có `/api/connect-status` hay Check live:

```bash
python -m http.server 3007 --bind 127.0.0.1 --directory frontend
```

Secrets come from a local gitignored `.env` (copy `.env.example`) or OS env vars (`BITGET_API_KEY`, `BITGET_API_SECRET`, `BITGET_PASSPHRASE`; trade key later as `BITGET_TRADE_*`). No data files or account history are committed.
