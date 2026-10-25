# Bitget DCA ladder tools (WIP)

Python scripts for monitoring a Bitget USDT-M futures account (read-only), journaling orders, backtesting DCA ladders and planning ladder orders.

- `bg.py`, `monitor.py`: read-only account/position monitor (Bitget v2 API).
- `journal/`: order/fill/position journal sync + daily style digest.
- `backtest/`, `planner/`: 1m-candle DCA ladder backtests, `ladder.py` ladder calculator, `PLAN.md`.
- `trader/`: **unfinished** semi-auto order tool (TA module `ta.py`, API wrapper `bgapi.py`). Not tested against live trading; do not use with a trade key as-is.
- `frontend/`: local-only Demo/dry-run zone desk. Zone/policy/AI stay in browser storage. Tổng quan GET Demo via local CLI. Trial **Dự phòng 2** (`specs/du-phong-2.md`): Chạy/Dừng is the only run door; one cycle walks every approved pair (no checkbox, no side picker). `POST /api/demo-cycle` GETs a fresh snapshot, appends the equity ledger once, runs protect (optional flatten), then scans due pairs; it can POST place/cancel/close plus TPSL on OPEN in the whitelist. The timer does not start on page load. Configured AI is required on the UI (errors become `NO_TRADE`). Kill (`POST /api/demo-kill`) still flattens the selected ticker symbol. Live stays locked. Paper scan loop remains a separate CLI (`python -m trader.paper_scan_cli`).

## Mở demo frontend local

Cổng cố định `3007`. Không cần `npm install`. Chạy từ thư mục repo:

```bash
npm start
```

`npm start` tự mở `http://localhost:3007`. Đặt `FRONTEND_NO_OPEN=1` nếu chỉ cần server. Nav bốn nhóm: Vận hành (Tổng quan, Bàn zone), Nền tảng (Kết nối, Cấu hình AI, Phong cách), Hạn mức (Mandate, Đề xuất cặp, Quyền AI), Chưa làm (Nhật ký). Hash mặc định `#/tong-quan`. Cấu hình AI lưu provider/model local; Gemini nhiều key ngang hàng (bốc ngẫu nhiên), OpenAI-compatible một key; form che ký tự giữa; nút Check live ping provider. Mandate lần đầu cho phép allowlist trống. Đề xuất cặp GET public ticker, user duyệt mới vào allowlist (không tự thêm). Tổng quan GET Demo khi vào trang rồi poll mỗi 12 giây khi đang mở (nút làm mới tay, không POST); tab vị thế/lệnh/fills/đối soát/tài sản; thử Dự phòng 2: Chạy/Dừng đi hết allowlist, hạn mức từ Mandate, cần AI; Kill Demo flatten symbol đang chọn. Kết nối hiện status Demo/env đủ-thiếu và form ghi Demo key vào `.env`. Phong cách đọc/ghi `profile/user_style.yaml` (append-only, không hard limit). Nhật ký đang stub. Tạo zone preview, kích hoạt local và ghi observation mock. Zone/policy/AI lưu local storage; key Bitget ghi `.env`, không localStorage.

Cách khác (Python) chỉ phục vụ file tĩnh, không có `/api/connect-status`, `/api/bitget-snapshot`, `/api/pair-screen`, `/api/user-style`, `/api/demo-scan`, `/api/demo-cycle`, `/api/demo-kill` hay Check live:

```bash
python -m http.server 3007 --bind 127.0.0.1 --directory frontend
```

Secrets come from a local gitignored `.env` (copy `.env.example`) or OS env vars (`BITGET_API_KEY`, `BITGET_API_SECRET`, `BITGET_PASSPHRASE`; trade key later as `BITGET_TRADE_*`). No data files or account history are committed.
