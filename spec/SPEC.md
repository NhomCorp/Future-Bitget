# ĐẶC TẢ KỸ THUẬT – Công cụ bán tự động DCA-ladder cho Bitget USDT-M Futures

| | |
|---|---|
| Phiên bản | 1.0 (bản bàn giao cho developer) |
| Ngày | 2026-10-20 (UTC+7) |
| Chủ sở hữu | Trung Hieu |
| Phạm vi | BTCUSDT, ETHUSDT – USDT-M perpetual, Hedge mode, Cross margin |
| Trạng thái | Đặc tả. **Không chứa mã triển khai.** Mọi đoạn code/JSON chỉ là ví dụ định dạng |
| Tài liệu nguồn | `planner/PLAN.md`, `planner/ladder.py`, `planner/results/final_eval.csv`, `planner/recap.json`, `backtest/REPORT.txt`, `profile/report.md`, mã tham khảo bỏ dở `trader/` (bgapi.py, ta.py, snap.py) |

> **Quy ước:** "PHẢI" = bắt buộc, "NÊN" = khuyến nghị mạnh, "CÓ THỂ" = tuỳ chọn. Mục được đánh dấu **[CHƯA XÁC MINH]** là hành vi API chưa kiểm chứng được từ tài liệu chính thức → developer PHẢI kiểm tra trên Demo trước khi dựa vào (xem Phụ lục B). Mọi thời gian hiển thị cho người dùng theo giờ Asia/Saigon (UTC+7); lưu trữ nội bộ dùng epoch ms UTC.

---

## Mục lục

1. Mục tiêu & phạm vi
2. Luồng sử dụng
3. Kiến trúc & module
4. Logic lưới (ladder) chi tiết – công thức & ví dụ số
5. Quy tắc rủi ro & kiểm tra trước khi đặt lệnh
6. Module phân tích kỹ thuật (TA)
7. Tích hợp API Bitget v2
8. Trạng thái, lưu trữ, log, triển khai VPS & đồng bộ dữ liệu (WebSocket)
9. Bảo mật
10. Kiểm thử & tiêu chí nghiệm thu
11. Lộ trình
12. Câu hỏi mở cho chủ sở hữu
13. Checklist review code
- Phụ lục A – Tham số cấu hình & giới hạn cứng
- Phụ lục B – Nguồn tài liệu API & điểm chưa xác minh
- Phụ lục C – Tóm tắt kết quả backtest làm cơ sở

---

## 1. Mục tiêu & phạm vi

### 1.1 Bối cảnh

- Tài khoản: Bitget USDT-M Futures, **Hedge mode** (`posMode=hedge_mode`), **Cross margin**, `assetMode=single` (tài khoản Classic – API v2 `/api/v2/mix/*` đang hoạt động với key chỉ-đọc). Equity ≈ **524.87 USDT** (log 2026-10-20 07:49 UTC+7: `accountEquity` 524.70).
- Phí: maker **0.02%**, taker **0.06%** (khớp `makerFeeRate`/`takerFeeRate` của endpoint contracts).
- Lịch sử: người dùng giao dịch kiểu micro-grid DCA, đòn bẩy cài 125–150x, notional thường 50–95x equity (đỉnh ~218x), **suýt bị thanh lý** (2026-10-15 20:52: chỉ cần ~0.06% nữa). Backtest cho thấy kiểu micro-grid (bước 0.2%, TP 0.3%) **âm sau phí** (−41%/180 ngày có stop; cháy tài khoản khi không stop).
- Kế hoạch mới (từ backtest 180 ngày nến 1m, xem Phụ lục C): **thang thưa**, 5 lớp đều, cách 1.5%, TP1 +1.2% đóng 50% (ngừng DCA sau TP1), phần còn lại TP2 +2.4% hoặc hoà vốn, stop cứng theo % equity cho mỗi thang, giới hạn tổng exposure.

### 1.2 Mục tiêu

1. Biến kế hoạch trên thành công cụ **bán tự động**: người dùng ra lệnh qua chat → công cụ tính toán & kiểm tra rủi ro → hiển thị bản xem trước → người dùng xác nhận → công cụ đặt lệnh và **tự động bảo trì** TP/SL của thang đã được xác nhận.
2. **Không bao giờ** vượt giới hạn rủi ro cứng, kể cả khi cấu hình sai hoặc người dùng yêu cầu.
3. Hai chế độ thang: **Wide-ladder** (chiến lược chính, đã backtest – mục 4.1–4.11) và **Scalp mode** (hỗ trợ phong cách cũ của người dùng, do người dùng điều khiển, giới hạn cứng chặt – mục 4.12).
4. Cung cấp **module phân tích kỹ thuật** đa khung thời gian làm **bộ lọc rủi ro** (OK/CAUTION/AVOID) – *không phải công cụ dự báo*.
5. Nhật ký đầy đủ mọi request/response để kiểm toán; chế độ dry-run và Demo.

### 1.3 Kỳ vọng thực tế (PHẢI hiển thị trong README và lệnh `status`)

- Phương án AN TOÀN (khuyến nghị bắt đầu): backtest 180 ngày **+22.9%**, max DD 19%, ~0.67 USDT/ngày (~17k VND/ngày); giai đoạn giảm 90 ngày **−1.4%**.
- **Mục tiêu 700k VND/ngày (~27 USDT/ngày ≈ 5%/ngày) KHÔNG thực tế** ở mức rủi ro này: 0% số ngày đạt ở phương án an toàn, 1.7% ở mặc định, 6.7% ở mạnh tay. Đạt 700k/ngày đòi hỏi notional 50–100x equity = trạng thái suýt thanh lý trước đây.
- Tham số được chọn trên chính dữ liệu backtest → kết quả thật sẽ kém hơn.

### 1.4 Trong phạm vi (MVP → các pha sau)

| Hạng mục | Pha |
|---|---|
| CLI: `preview`, `execute`, `sync` (watcher), `cancel`, `kill`, `status`, `ta`, `journal` | MVP / P1 |
| Tính thang (fixed spacing), kiểm tra rủi ro, đặt lệnh entry post-only + SL + TP | MVP |
| **Scalp mode** (thang dày do người dùng điều khiển, giới hạn cứng riêng – mục 4.12) | P1b (sau khi Wide mode qua Demo) |
| Dry-run, Demo (`paptrading`), log JSONL, lưu trạng thái | MVP |
| Module TA + cờ rủi ro + chế độ `levels` (snap theo S/R) | P2 |
| Backtest bắt buộc cho bộ lọc TA và `levels` | P2 (cổng chặn) |
| Lớp tin tức: lịch kinh tế, tin crypto lớn, sentiment X | P3 |
| Tự động mở thang mới không cần xác nhận | P4 – tuỳ chọn, chỉ sau khi đạt tiêu chí |

### 1.5 Ngoài phạm vi

- Rút/chuyển tiền, đổi chế độ tài khoản (hedge/one-way, cross/isolated, Classic/UTA), giao dịch coin khác ngoài BTCUSDT/ETHUSDT, copy-trading, market-making, scalping micro-grid kiểu cũ.
- Thay đổi tham số chiến lược "tại chỗ" khi đang có thang mở (thay đổi chỉ áp dụng cho thang mới).

---

## 2. Luồng sử dụng

### 2.1 Tổng quan
```
Người dùng (chat) ──yêu cầu──► Trợ lý ──gọi CLI──► preview ──► bảng + plan_id (hết hạn 10 phút / lệch giá 0.3%)
        ▲                                                         │
        └──────────── trình bày bảng, cảnh báo, cờ TA ◄───────────┘
Người dùng "xác nhận <plan_id>" ──► execute <plan_id> --confirm ──► tái kiểm tra ──► đặt lệnh entry post-only + SL
                                                                                   │
sync (watcher chạy nền trên VPS: WebSocket + đối soát REST 60s) ◄─────────────────────────────────────────────────┘
   - phát hiện lớp khớp → đặt lại TP1/TP2 theo giá TB mới, kiểm tra SL
   - TP1 khớp → huỷ DCA còn lại, dời SL về hoà vốn
   - TP2 / hoà vốn / SL → đóng thang, ghi journal
```

### 2.2 Các lệnh CLI (giao diện bắt buộc)
Mọi lệnh hỗ trợ `--json` (đầu ra máy đọc, để trợ lý xử lý) và mặc định in bảng tiếng Việt dễ đọc. Mọi lệnh hỗ trợ `--env live|demo` (mặc định lấy từ cấu hình) và `--dry-run`.

| Lệnh | Mô tả | Gửi lệnh lên sàn? |
|---|---|---|
| `preview --symbol ETHUSDT --side long [--variant safe\|default\|aggressive] [--spacing fixed\|levels] [--anchor <giá>] [--layers N]` | Lấy giá, equity, vị thế, lệnh chờ; tính thang; chạy kiểm tra rủi ro (mục 5) & TA (nếu bật); in bảng; lưu plan với `plan_id`. Có thể tạo **nhiều chân** trong 1 plan (`--legs ETHUSDT:long,ETHUSDT:short`) | Không (chỉ GET) |
| `execute <plan_id> --confirm` | Tái kiểm tra toàn bộ, nếu khớp → đặt entry post-only + SL; ghi trạng thái. Thiếu `--confirm` → chỉ in lại bản xem trước | Có |
| `sync [--once]` | Watcher (WebSocket thời gian thực + đối soát REST định kỳ, mục 8.5): đồng bộ fills/vị thế, đặt lại TP, đảm bảo SL, xử lý TP1/TP2/hoà vốn/SL, phát hiện lệch trạng thái. `--once` chạy 1 vòng | Có |
| `cancel <plan_id> [--leg ETHUSDT:long]` | Huỷ các lệnh **chưa khớp** của plan (entry + TP; giữ SL nếu còn vị thế). Không đóng vị thế | Có |
| `kill [--close-positions --confirm-close]` | Dừng khẩn cấp: dừng watcher, huỷ **mọi lệnh của công cụ** (lọc theo tiền tố `clientOid`), bao gồm lệnh plan/TP-SL của công cụ. Chỉ đóng vị thế khi có **cả hai** cờ `--close-positions --confirm-close` | Có |
| `status [--plan <id>]` | Equity, exposure (x equity), từng thang (lớp đã khớp, giá TB, TP, SL, khoảng cách tới SL/liq), lệnh treo, cảnh báo lệch trạng thái, PnL ngày/tuần | Không |
| `ta --symbol ETHUSDT [--json]` | Chạy module TA độc lập (mục 6) | Không |
| `journal [--from --to]` | Xuất nhật ký thang đã đóng (CSV) | Không |
| `selftest` | Kiểm tra cấu hình, quyền key, posMode/marginMode, đồng hồ, kết nối; không đặt lệnh | Không |

### 2.3 Quy tắc plan (preview → execute)

- `plan_id`: chuỗi 8 ký tự base32 ngẫu nhiên (vd `K7Q2M9XA`), duy nhất.
- Plan lưu: thời điểm tạo, giá tham chiếu (`ref_price` = last price lúc preview), equity, snapshot vị thế/lệnh, tham số, toàn bộ lệnh dự kiến (giá, size, clientOid), kết quả kiểm tra rủi ro, kết quả TA, hash nội dung.
- **Hết hạn**: sau **10 phút** HOẶC khi `|last/ref_price − 1| > 0.3%` tại thời điểm execute → từ chối, yêu cầu preview lại.
- `execute` PHẢI tính lại thang với dữ liệu mới. Nếu bất kỳ giá lệnh nào lệch > 1 tick hoặc size khác, hoặc kết quả kiểm tra rủi ro đổi trạng thái → **huỷ execute**, in diff, yêu cầu preview mới. (Ngoại lệ: lớp 1 có thể được re-anchor theo quy tắc mục 4.7 nếu người dùng chọn `anchor=market`.)
- Một plan chỉ được execute **một lần** (idempotent: execute lần 2 chỉ in trạng thái).
- Cờ TA = **AVOID** → `execute` từ chối trừ khi có `--override-avoid "<lý do>"` (lý do được ghi log). Cờ CAUTION → in cảnh báo, cho phép.

### 2.4 Kịch bản chat mẫu

1. Người dùng: "Mở thang ETH long an toàn." → trợ lý chạy `preview --symbol ETHUSDT --side long --variant safe --json`, trình bày bảng + cờ TA + exposure sau khi mở.
2. Người dùng: "OK K7Q2M9XA." → trợ lý chạy `execute K7Q2M9XA --confirm`, báo lại danh sách orderId/clientOid, SL.
3. Watcher `sync` chạy nền; trợ lý dùng `status` để báo tình hình khi được hỏi.
4. Người dùng: "Dừng hết." → `kill` (không đóng vị thế); "Đóng luôn vị thế." → trợ lý PHẢI hỏi lại một lần rồi mới chạy `kill --close-positions --confirm-close`.

---

## 3. Kiến trúc & module

### 3.1 Yêu cầu nền tảng

- Ngôn ngữ đề xuất: Python ≥ 3.11 (đã có mã tham khảo Python). Có thể dùng ngôn ngữ khác nếu đáp ứng toàn bộ đặc tả.
- Tính toán tiền/giá PHẢI dùng số thập phân chính xác (`Decimal` hoặc số nguyên theo tick/lot), **không dùng float** cho giá/size gửi lên sàn. TA được dùng float/numpy.
- Chạy trên **VPS** có IP tĩnh (để whitelist IP); watcher là service systemd tự khởi động lại; chi tiết triển khai, WebSocket và giám sát ở mục 8.5.
- Một tiến trình watcher duy nhất cho mỗi tài khoản (file lock). `execute`/`cancel`/`kill` dùng chung lock trạng thái để tránh race.

### 3.2 Sơ đồ module
```
cli/                → phân tích lệnh, in bảng/JSON
config/             → nạp cấu hình + áp giới hạn cứng (HardLimits) – không thể vượt
exchange/
  client.py         → REST ký HMAC, rate-limiter, retry, đồng bộ giờ, header demo, log
  models.py         → ContractSpec, Position, Order, PlanOrder, Account
  bitget_v2.py      → các hàm endpoint (mục 7)
market/             → nến, ticker, funding, OI, long/short ratio (public REST, TA poll ~1/phút)
stream/             → WebSocket public/private: login, ping/pong, reconnect backoff, phát sự kiện
monitor/            → health, heartbeat, cảnh báo, dead-man ping ra ngoài
ladder/
  builder.py        → tính giá/size các lớp (fixed | levels), làm tròn
  math.py           → giá TB, TP, SL theo % equity, ước tính thanh lý cross
risk/
  checks.py         → bảng kiểm tra trước khi đặt (mục 5), trả về PASS/FAIL + lý do
  exposure.py       → exposure hiện tại + dự kiến, cùng chiều, tổng
ta/                 → phân tích kỹ thuật (mục 6)
news/               → (P3) lịch kinh tế, tin tức, sentiment
planner/            → tạo/lưu/kiểm tra hạn plan
executor/           → execute, cancel, kill (idempotent theo clientOid)
sync/               → watcher, máy trạng thái thang (mục 8.2), đối soát
store/              → SQLite + file JSONL
backtest/           → tái sử dụng engine 1m hiện có để kiểm định TA filter/levels
tests/
```

### 3.3 Nguyên tắc thiết kế

1. **Thuần hàm cho phần tính toán** (`ladder`, `risk`, `ta`): đầu vào → đầu ra, không gọi mạng → dễ unit-test và dùng chung với backtest.
2. **Sàn là nguồn sự thật** (source of truth) cho vị thế/lệnh; DB cục bộ là nguồn sự thật cho *ý định* (plan, vai trò của từng lệnh). Watcher luôn đối soát hai bên.
3. **Mọi lệnh gửi đi có `clientOid` xác định trước** (deterministic) → gửi lại không tạo lệnh trùng.
4. **Fail-safe**: khi không chắc chắn (lỗi mạng, phản hồi lạ, lệch trạng thái) → không mở thêm vị thế; ưu tiên giữ/đặt SL; báo động.
5. Không có đường code nào đặt lệnh *mở* vị thế ngoài `execute` (và watcher chỉ được đặt lệnh *đóng* + SL, cộng lại các lớp entry đã thuộc plan được xác nhận – xem 4.7 "đặt lớp trễ").

---

## 4. Logic lưới chi tiết

### 4.1 Ký hiệu

| Ký hiệu | Ý nghĩa |
|---|---|
| `E` | Equity tài khoản futures USDT (`accountEquity` từ `/api/v2/mix/account/account`), tính theo mark price |
| `sg` | +1 cho long, −1 cho short |
| `N` | Số lớp (mặc định 5; giới hạn cứng ≤ 5 ở MVP) |
| `d` | Khoảng cách giữa 2 lớp liên tiếp (mặc định 1.5% = 0.015) |
| `capLeg` | Notional tối đa của 1 thang, theo bội số equity (an toàn 0.75; mặc định 1.25; mạnh tay 2.0) |
| `P_i`, `q_i` | Giá và khối lượng (base coin) lớp i (i = 1..N) |
| `Q_k`, `A_k` | Tổng khối lượng và giá TB sau khi khớp k lớp |
| `m`, `t` | Phí maker 0.0002, taker 0.0006 |
| `tp1`, `tp2` | 1.2% và 2.4% từ giá TB; `f1` = 0.5 (tỷ lệ đóng ở TP1) |
| `s` | Stop theo % equity mỗi thang (an toàn 5%, mặc định/mạnh 7%) |
| `tick` | Bước giá = `priceEndStep × 10^(−pricePlace)` |
| `lot` | Bước khối lượng = `sizeMultiplier`; tối thiểu `minTradeNum`; notional tối thiểu `minTradeUSDT` |
| `mmr` | Tỷ lệ ký quỹ duy trì theo bậc (`keepMarginRate` từ `query-position-lever`) |

Thông số hợp đồng lấy **lúc chạy** từ `/api/v2/mix/market/contracts` (kiểm tra ngày 2026-10-20):

| Symbol | pricePlace | priceEndStep | → tick | sizeMultiplier (lot) | minTradeNum | minTradeUSDT | maxLever | MMR bậc 1 (≤200k USDT) |
|---|---|---|---|---|---|---|---|---|
| BTCUSDT | 1 | 1 | 0.1 | 0.0001 | 0.0001 | 5 | 150 | 0.40% |
| ETHUSDT | 2 | 1 | 0.01 | 0.01 | 0.01 | 5 | 150 | 0.40% |

> Lưu ý: backtest/`ladder.py` giả định MMR ETH 0.5% (thận trọng hơn). Bậc MMR thực tế hiện là 0.4% cho cả hai; công cụ PHẢI lấy bậc thật qua API và dùng `max(api_mmr, cấu hình_tối_thiểu)`.

### 4.2 Biến thể (variant)

| Thông số | AN TOÀN (`safe`, mặc định của công cụ) | MẶC ĐỊNH (`default`) | MẠNH TAY (`aggressive`) |
|---|---|---|---|
| Tổng cap (mọi vị thế) | 3x E | 5x E | 8x E |
| Cap mỗi thang `capLeg` | 0.75x E | 1.25x E | 2.0x E |
| Cap cùng chiều (BTC+ETH) | 1.5x E (tự nhiên = 2 × 0.75) | 2.5x E | 2.5x E (giới hạn cứng – xem câu hỏi mở Q3) |
| Số lớp / khoảng cách / khối lượng | 5 / 1.5% / đều | như trái | như trái |
| TP1 / TP2 | +1.2% đóng 50% / +2.4% hoặc hoà vốn | như trái | như trái |
| Stop mỗi thang `s` | 5% E | 7% E | 7% E |
| Đòn bẩy cài trên sàn | 10x | 10x | 10x |

Đòn bẩy cài trên sàn chỉ ảnh hưởng ký quỹ ban đầu; rủi ro do **notional** quyết định. Công cụ PHẢI kiểm tra đòn bẩy symbol ≤ giới hạn cứng 20x và (tuỳ cấu hình) đặt về 10x qua `set-leverage` trước khi execute – chỉ khi không có vị thế mở trên symbol đó **[CHƯA XÁC MINH: có được đổi leverage khi có vị thế cross không]**.

### 4.3 Giá các lớp (chế độ `fixed`)

- `P_1` = giá neo (anchor). Mặc định anchor = giá tốt nhất phía maker: long → `bidPr`; short → `askPr` (từ `ticker`). Người dùng có thể chỉ định `--anchor`.
- Lớp tiếp theo (hình học, đúng như backtest/`ladder.py`): `P_i = P_{i−1} × (1 − sg·d)`, tức `P_i = P_1 × (1 − sg·d)^(i−1)`.
- Độ phủ thang với N=5, d=1.5%: long −5.87%, short +6.14% từ `P_1`.

### 4.4 Khối lượng các lớp

- Ngân sách mỗi lớp (đều): `B = capLeg × E / N`. (Hỗ trợ hệ số tăng dần `mult` cho tương lai, mặc định 1.0; `mult > 1` bị giới hạn cứng ở MVP = 1.0.)
- `q_i = floor( B / P_i / lot ) × lot`. **Luôn làm tròn xuống** → không bao giờ vượt cap.
- Nếu `q_i < minTradeNum` hoặc `q_i × P_i < minTradeUSDT` → plan **FAIL** (không tự nâng size lên vượt ngân sách). Thông báo: "equity quá nhỏ cho số lớp này".
- Ghi rõ trong bảng: notional thực tế/cap (do làm tròn, ETH lot 0.01 ≈ 24 USDT nên thang an toàn thực tế chỉ ≈ 89% cap).

### 4.5 Giá trung bình, TP

- Sau k lớp khớp: `Q_k = Σ q_i`, `A_k = Σ(q_i·P_i)/Q_k` (dùng **giá khớp thật** `priceAvg`/fills khi chạy live, không dùng giá dự kiến).
- `TP1_k = A_k × (1 + sg·tp1)`, `TP2_k = A_k × (1 + sg·tp2)`.
- Khối lượng: `qTP1 = floor(f1 × Q_k / lot) × lot`; `qTP2 = Q_k − qTP1`. Nếu `qTP1 < minTradeNum` (vd chỉ có 1 lớp ETH 0.03 → qTP1 = 0.01 OK; BTC lớp nhỏ có thể không đủ) → đặt 1 lệnh TP duy nhất tại TP1 cho toàn bộ Q_k và ghi chú.
- **Sau khi TP1 khớp**: (a) huỷ toàn bộ entry chưa khớp của thang (ngừng DCA); (b) TP2 giữ nguyên tại `A_k × (1+sg·tp2)` với `A_k` là giá TB **tại thời điểm TP1** ("giá TB cũ"); (c) SL được dời về **hoà vốn**: `BE = A_k × (1 + sg·(2m + t + buffer_be))`, `buffer_be` mặc định 0.0005 (0.05%) – lệnh stop market (taker), đúng như giả định backtest "thoát hoà vốn = taker 0.06%".
- Thang đóng khi Q = 0 (TP2, BE, SL, hay đóng tay).

### 4.6 Stop-loss theo % equity
Mục tiêu: nếu cả N lớp đều khớp rồi giá chạm SL, tổng lỗ (gồm phí) = `L = s × E_open` (E_open = equity lúc execute).

Giải cho giá SL (lỗ = chênh lệch giá + phí mở maker + phí đóng taker):

- Long: `Q·(A − SL) + F_open + Q·SL·t = L`  ⇒  **`SL = (Q·A + F_open − L) / (Q·(1 − t))`**
- Short: `Q·(SL − A) + F_open + Q·SL·t = L`  ⇒  **`SL = (Q·A − F_open + L) / (Q·(1 + t))`**

với `F_open = m × Σ q_i·P_i`.

**Quy tắc chọn Q, A để tính SL (quan trọng):** dùng **khối lượng thiết kế chưa làm tròn** `q_i* = B/P_i` (đúng như backtest) để giá SL khớp với backtest; sau đó kiểm tra lỗ thực tế với khối lượng đã làm tròn ≤ `L` (luôn đúng vì làm tròn xuống). Nếu dùng Q đã làm tròn (nhỏ hơn) thì SL sẽ xa hơn backtest (vd ETH: −10.17% thay vì −9.39%) → **không được**.

- Làm tròn SL: long → **làm tròn lên** (gần giá hơn, lỗ ≤ L); short → **làm tròn xuống**.
- SL là **một lệnh SL cấp vị thế duy nhất** cho (symbol, holdSide), giá cố định từ lúc execute, **không bao giờ được dời ra xa**; chỉ được dời *về phía có lợi* (về hoà vốn sau TP1).
- Trigger theo **mark price** (`triggerType=mark_price`), thực thi market (`executePrice` = 0) – tránh bị quét bởi râu last price và đảm bảo thoát.
- Kiểm tra: `|SL/P_N − 1| ≥ 1%` (SL phải nằm ngoài lớp cuối ít nhất 1%) – nếu không, plan FAIL ("stop quá gần lớp cuối, giảm số lớp hoặc cap").
- Trượt giá: báo cáo thêm "lỗ ước tính nếu trượt 0.3%" = `L + Q·SL·0.003`.

### 4.7 Đặt lớp trễ (lazy placement) – tuỳ chọn, mặc định TẮT
Bitget có giới hạn giá lệnh so với giá hiện tại (`buyLimitPriceRatio`/`sellLimitPriceRatio` = 0.05 trong contracts; lỗi 22046 "order price exceeds the minimum price limit") **[CHƯA XÁC MINH: lệnh mua cách −5.87% có bị từ chối không]**. Nếu Demo cho thấy lớp sâu bị từ chối: bật `lazy_layers=true` → execute chỉ đặt các lớp nằm trong `lazy_window` (mặc định 4%) từ giá hiện tại; watcher đặt lớp còn lại khi giá tiến gần (chỉ cho plan đã xác nhận, chưa TP1, cùng giá/size đã lưu, vẫn qua kiểm tra cap). Giá/size của lớp trễ KHÔNG được tính lại.

### 4.8 Ước tính thanh lý (cross)
Mô hình (giống `ladder.py`, mở rộng cho nhiều vị thế): tài khoản cross bị thanh lý khi
`E + Σ_j uPnL_j(P) ≤ Σ_j mmr_j × |Q_j| × P_j`  (bỏ qua phí thanh lý; ghi rõ là ước tính).

(a) **Một thang dùng toàn bộ equity** (công thức đóng):

- Long: `P_liq = (Q·A − E') / (Q·(1 − mmr))`; Short: `P_liq = (E' + Q·A) / (Q·(1 + mmr))`, với `E' = E − F_open`. Nếu `P_liq ≤ 0` (long) → "không có giá thanh lý".

(b) **Kịch bản xấu nhất toàn tài khoản** (bắt buộc trong preview): giả định mọi thang cùng chiều với thang mới đã **khớp đủ N lớp**, mọi thang ngược chiều giữ nguyên hiện trạng, BTC và ETH cùng di chuyển x% (tương quan 0.87 ≈ 1). Tìm x nhỏ nhất (bisection) sao cho bất đẳng thức trên xảy ra. Báo cáo `move_to_liq_pct` và so với khoảng cách tới SL.

(c) Đối chiếu với sàn: sau khi có vị thế, đọc `liquidationPrice` từ `all-position` và (tuỳ chọn) `GET /api/v2/mix/account/liq-price`; nếu chênh > 20% so với ước tính → log cảnh báo.

**Yêu cầu:** `move_to_liq` phải ≥ **3 × khoảng cách tới SL** (của thang xa nhất) và tỷ lệ MM/equity dự kiến ở kịch bản (b) tại giá SL < 10%. Không đạt → FAIL.

### 4.9 Quy tắc làm tròn (tổng hợp)

| Đại lượng | Long | Short | Lý do |
|---|---|---|---|
| Giá entry `P_i` | floor theo tick | ceil theo tick | Không vào giá xấu hơn thiết kế |
| Size `q_i`, TP size | floor theo lot | floor theo lot | Không vượt cap |
| TP1/TP2 | ceil | floor | Lãi ≥ thiết kế |
| SL | ceil | floor | Lỗ ≤ ngân sách |
| BE stop | ceil | floor | Thoát không lỗ phí |
Chuỗi gửi lên sàn: định dạng đúng số chữ số thập phân (`pricePlace`, `volumePlace`), không dạng khoa học (vd `"0.0016"`, không phải `"1.6e-3"`).

### 4.10 Ví dụ số – ETHUSDT, giá ≈ 2400.00, E = 524.87, phương án AN TOÀN
Tham số: `capLeg` 0.75 → 393.65 USDT/thang; `B` = 78.73 USDT/lớp; d 1.5%; tick 0.01; lot 0.01; s 5% → `L` = 26.24 USDT; MMR 0.4%.

**ETH Long** (anchor 2400.00)

| Lớp | Giá | Δ% từ L1 | Size ETH | Notional | Q lũy kế | Giá TB | TP1 (+1.2%) | TP2 (+2.4%) | x equity |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2400.00 | 0.00 | 0.03 | 72.00 | 0.03 | 2400.00 | 2428.80 | 2457.60 | 0.14 |
| 2 | 2364.00 | −1.50 | 0.03 | 70.92 | 0.06 | 2382.00 | 2410.59 | 2439.17 | 0.27 |
| 3 | 2328.54 | −2.98 | 0.03 | 69.86 | 0.09 | 2364.18 | 2392.56 | 2420.93 | 0.41 |
| 4 | 2293.61 | −4.43 | 0.03 | 68.81 | 0.12 | 2346.54 | 2374.70 | 2402.86 | 0.54 |
| 5 | 2259.20 | −5.87 | 0.03 | 67.78 | 0.15 | 2329.07 | 2357.02 | 2384.97 | 0.67 |

- Notional đầy thang 349.36 USDT (89% cap do lot 0.01 ≈ 24 USDT).
- SL (tính với Q thiết kế 0.1691, A 2328.01): **2174.58** (−9.39% từ L1, −6.59% từ giá TB thiết kế). Lỗ thực tế với Q = 0.15 tại SL ≈ **23.4 USDT** (≤ 26.24). Nếu trượt 0.3%: +~1 USDT.
- TP1 đầy thang: đóng 0.07 ETH tại 2357.02 → lãi ròng ≈ 1.9 USDT; TP1 khi chỉ có lớp 1 (đóng 0.01 ETH = floor(0.5×0.03)): ≈ 0.28 USDT. *(Con số nhỏ – đúng bản chất phương án an toàn.)*
- Thanh lý (a) 1 thang dùng toàn bộ equity: không có (P_liq < 0). (b) ETH long + BTC long đầy (~350 USDT mỗi bên): cần giá giảm ~75% từ giá TB → rất xa; rủi ro chính là **chuỗi stop**, không phải thanh lý.

**ETH Short** (anchor 2400.00): lớp 2400.00 / 2436.00 / 2472.54 / 2509.63 / 2547.28, mỗi lớp 0.03 ETH; TB đầy 2473.09; TP1 2443.41; TP2 2413.73; **SL 2634.72** (+9.78% từ L1); lỗ thực tế tại SL ≈ 24.6 USDT.

> Developer PHẢI tái tạo chính xác các con số trên trong unit test (sai số ≤ 1 tick / 0.01 USDT), với dữ liệu contract cố định như bảng 4.1.

### 4.11 Hedge & nhiều thang

- Mỗi (symbol, holdSide) tối đa **1 thang** của công cụ tại một thời điểm → tối đa 4 thang: BTC-L, BTC-S, ETH-L, ETH-S.
- Thang long và short cùng symbol chạy độc lập (hedge mode cho phép).
- Khi một thang đóng, MVP **không** tự mở thang mới: watcher gửi thông báo "thang X đã đóng (lý do), đề xuất preview thang mới". (Tự mở lại = P4.)
- Công cụ **từ chối** mở thang trên (symbol, holdSide) đang có vị thế hoặc lệnh *không thuộc công cụ* (vì SL cấp vị thế sẽ ảnh hưởng cả vị thế tay).

### 4.12 Chế độ thứ hai: **Scalp mode** (phong cách lịch sử của người dùng – do người dùng điều khiển)

> **CẢNH BÁO BẮT BUỘC (hiển thị ở mọi preview/status của Scalp mode):** Backtest *cơ học* đúng phong cách này (bước 0.18%, size ×0.87, lớp đầu 10x equity, không stop, cap 49x) **bị thanh lý sau ~9 giờ** (`backtest/REPORT.txt`: thanh lý 2026-08-21 08:18 UTC+7). Các phiên bản "thuần hoá" (lớp đầu 2x, cap 15x, 8 lớp, stop 1% sau lớp cuối) sống sót nhưng **âm ròng sau phí** (−62% trên 300 USDT/60 ngày, phí 782 USDT, 77 lần stop); micro-grid 0.2%/TP 0.3% cap 8x: −41%/180 ngày có stop, cháy tài khoản khi không stop (`PLAN.md`). ⇒ **Scalp mode là công cụ HỖ TRỢ QUYẾT ĐỊNH (discretion-assist), KHÔNG phải chiến lược tự động.** Công cụ không bao giờ tự mở thang Scalp; mọi thang Scalp do người dùng chọn symbol/chiều/thời điểm và xác nhận. Không có pha "full-auto" cho Scalp mode.

**4.12.1 Mô tả**

- Người dùng chọn `symbol`, `side`, thời điểm (thường là "fade" một nhịp 1h – 82% lệnh lịch sử). Công cụ dựng một thang **dày**: lớp đầu lớn, các lớp sau nhỏ dần, TP sát giá TB, chốt từng phần khi giá hồi.
- Mọi lệnh vẫn theo nguyên tắc "nằm trên sàn" (8.5): entry post-only, TP limit close post-only, SL khẩn cấp là lệnh trigger phía sàn.

**4.12.2 Tham số (mặc định / khoảng cho phép trong cấu hình)**

| Tham số | Mặc định | Khoảng cấu hình | Giới hạn cứng trong mã |
|---|---|---|---|
| Notional lớp đầu `first_x` (bội số E) | 3x | 2–5x | ≤ 5x (lịch sử ~10x – **không cho phép**) |
| Khoảng cách `d` | 0.20% | 0.18–0.30% | ≥ 0.15% |
| Hệ số size `mult` (giảm dần) | 0.87 | 0.80–1.00 | ≤ 1.00 (cấm martingale tăng dần) |
| Số lớp tối đa | đến khi chạm cap | – | ≤ 12 |
| TP từ giá TB | 0.20% | 0.15–0.30% | ≥ 0.12% (phí maker 2 chiều 0.04%) |
| Chốt từng phần | 50% tại TP_a = +0.15%, 50% tại TP_b = cấu hình TP | tuỳ chỉnh | – |
| Tổng notional mọi vị thế | **15x E** | ≤ cấu hình | **≤ 20x E tuyệt đối** |
| Cùng chiều BTC+ETH | 10x E | ≤ tổng cap | ≤ 15x E |
| Khoảng cách tới thanh lý tối thiểu khi thêm lớp | 3% | ≥ 3% | **≥ 3%** |
| SL khẩn cấp phía sàn (mỗi thang) | −15% E | 5–15% | **≤ 15% E, bắt buộc** |
| Lỗ ngày → khoá công cụ | 10% E đầu ngày | 3–15% | ≤ 15%; khoá đến 00:00 UTC+7 hôm sau |
| Hết hạn preview | 2 phút / lệch 0.10% | – | ≤ 10 phút / 0.3% |

**4.12.3 Công thức** (dùng lại 4.3–4.9 với khác biệt):

- `B_i = first_x × E × mult^(i−1)`; `q_i = floor(B_i / P_i / lot) × lot`; `P_i = P_1 × (1 − sg·d)^(i−1)`.
- Thêm lớp i chỉ khi **cả ba** đúng (tính ở preview cho toàn thang, và **tính lại khi watcher chuẩn bị/giữ từng lớp**): (a) exposure_worst sau lớp i ≤ tổng cap; (b) cùng chiều ≤ cap cùng chiều; (c) ước tính thanh lý toàn tài khoản (4.8(b), mọi vị thế hiện có + thang này đến lớp i) cách **giá lớp i** ≥ 3%. Lớp vi phạm → bị cắt khỏi thang (preview hiện "thang dừng ở lớp k vì …"). Nếu equity giảm khiến lớp đang treo vi phạm (c) → watcher **huỷ** lớp đó.
- SL khẩn cấp: công thức 4.6 với `s` = 15% và Q/A của **thang đầy** (đã cắt theo cap) – `pos_loss` trigger mark price, đặt bằng preset trên lớp 1 và xác nhận sau fill đầu (như Wide mode). Không bao giờ dời xa hơn; chỉ được dời gần hơn/về hoà vốn.
- TP: sau mỗi fill, watcher (sự kiện WS `orders`/`positions`, mục tiêu **≤ ~1 s** từ lúc nhận event) huỷ & đặt lại TP_a/TP_b theo giá TB mới (clientOid `rev+1`). Hệ quả nếu VPS/WS chậm: TP cũ còn treo – không tăng rủi ro, SL vẫn trên sàn.
- Chốt từng phần khi hồi (`scalp scaleout <leg> --pct 30`): người dùng ra lệnh, công cụ đặt limit close post-only sát giá tốt nhất cho X% vị thế; sau khi chốt, các lớp DCA còn treo **giữ nguyên** trừ khi người dùng thêm `--cancel-dca`.

**4.12.4 Ví dụ số (minh hoạ quy mô rủi ro)** – ETHUSDT long, E = 524.87, P₁ = 2400.00, first 3x, d 0.20%, mult 0.87, cap 15x, MMR 0.4%, giả định không có vị thế khác:

| Lớp | Giá | Δ% | ETH | Notional | x E lũy kế | Giá TB | TP (+0.2%) | Liq ước tính (1 thang) | Khoảng cách liq từ giá lớp |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2400.00 | 0.00 | 0.65 | 1560.0 | 2.97 | 2400.00 | 2404.81 | 1599.39 | 33.4% |
| 2 | 2395.20 | −0.20 | 0.57 | 1365.3 | 5.57 | 2397.76 | 2402.56 | 1975.92 | 17.5% |
| 3 | 2390.40 | −0.40 | 0.49 | 1171.3 | 7.80 | 2395.65 | 2400.45 | 2097.58 | 12.3% |
| 4 | 2385.62 | −0.60 | 0.43 | 1025.8 | 9.76 | 2393.63 | 2398.43 | 2157.48 | 9.6% |
| 5 | 2380.85 | −0.80 | 0.37 | 880.9 | 11.44 | 2391.75 | 2396.54 | 2191.88 | 7.9% |
| 6 | 2376.09 | −1.00 | 0.33 | 784.1 | 12.93 | 2389.93 | 2394.71 | 2214.45 | 6.8% |
| 7 | 2371.34 | −1.19 | 0.28 | 664.0 | 14.20 | 2388.26 | 2393.04 | 2229.43 | 6.0% |
- Lớp 8 bị cắt (vượt 15x). **SL khẩn cấp −15% E ≈ 78.7 USDT tại 2364.92** – chỉ cách giá TB đầy thang **−0.98%** và cách lớp 1 −1.46%. Đây là bản chất của Scalp mode: ở 14x notional, biến động bất lợi ~1% = mất 15% tài khoản. Lãi TP lớp 1 (đóng hết 0.65 ETH ở +0.2%): ≈ 2.5 USDT.
- Nếu đồng thời có thang BTC long cùng quy mô → cap cùng chiều 10x chặn, thang ETH bị cắt còn ~lớp 4–5.

**4.12.5 Quy tắc riêng**

- Scalp và Wide-ladder dùng chung bộ đếm exposure; mỗi (symbol, holdSide) chỉ 1 thang (bất kể chế độ). Khi đang có thang Scalp lớn, kiểm tra R9/R10 của Wide mode (3–5x) sẽ tự chặn mở thang Wide mới – đúng ý đồ.
- **Khoá ngày**: lỗ thực hiện + chưa thực hiện của thang Scalp trong ngày (00:00 UTC+7) ≥ giới hạn → huỷ mọi entry Scalp đang treo, **không** mở thang mới (cả Scalp lẫn Wide) đến 00:00 hôm sau; SL/TP hiện có giữ nguyên. Mở khoá sớm: không cho phép.
- Sau 2 lần SL khẩn cấp Scalp trong 7 ngày → Scalp mode tự tắt, cần chủ bật lại bằng lệnh có xác nhận.
- Lệnh CLI: `scalp preview --symbol --side [--first 3] [--spacing 0.2] [--mult 0.87] [--tp 0.2]`, `scalp execute <id> --confirm`, `scalp scaleout <leg> --pct N [--cancel-dca]`, `scalp cancel <leg>`; `kill` áp dụng cho cả hai chế độ. clientOid dùng tiền tố `gsc1-` (vẫn được `kill` nhận diện).

**4.12.6 Nhật ký bắt buộc để so sánh với Wide-ladder**

- Mỗi thang Scalp ghi bảng `scalp_journal` (và `journal/scalp.csv`): thời điểm mở/đóng (UTC+7), symbol/chiều, lý do người dùng nêu (chuỗi tự do, bắt buộc nhập ở execute), ảnh chụp TA lúc mở (cờ & bias), first_x/d/mult/TP, số lớp khớp, notional đỉnh (x E), khoảng cách liq nhỏ nhất, MAE%, thời gian giữ, PnL gộp/phí/funding/ròng, lý do đóng (TP/scaleout/SL/tay/kill), có chạm khoá ngày không.
- `journal --compare --from --to`: báo cáo Scalp vs Wide trên cùng kỳ: tổng PnL ròng, phí/lãi gộp, max DD, lỗ ngày tệ nhất, PnL theo rủi ro (ròng / Σ ngân sách SL), số lần gần thanh lý (< 5%). Báo cáo tự động mỗi Chủ nhật để chủ xem lại.
- Khuyến nghị (ghi trong README): sau 4 tuần, nếu Scalp kém Wide về PnL/rủi ro → giảm `first_x`/cap hoặc tắt Scalp.

---

## 5. Quy tắc rủi ro & kiểm tra trước khi đặt lệnh

### 5.1 Định nghĩa exposure

- `notional_pos` = Σ |total| × markPrice của mọi vị thế USDT-M (kể cả vị thế tay, coin khác).
- `notional_open_orders` = Σ size × price của mọi lệnh **mở vị thế** đang treo (kể cả lệnh tay và lệnh plan/trigger mở vị thế). Lệnh đóng (`tradeSide=close`) không tính.
- `exposure_worst` = `notional_pos + notional_open_orders + notional_plan_mới` (giả định mọi lệnh mở đều khớp).
- `same_dir_worst(long)` = phần exposure_worst của **long BTC + long ETH**; tương tự short. Hai coin tương quan 0.87 (lợi nhuận 1h, 180 ngày) nên coi như một rổ.
- Mọi tỷ lệ chia cho `E` hiện tại (mark-based) tại thời điểm kiểm tra.

### 5.2 Bảng kiểm tra (chạy ở `preview` VÀ lặp lại ở `execute`)

| # | Kiểm tra | Điều kiện PASS | Khi FAIL |
|---|---|---|---|
| R1 | Môi trường | `env` ∈ {demo, live}; live yêu cầu biến môi trường mở khoá `LIVE_TRADING_ENABLED=1` và key trade tồn tại | Chặn |
| R2 | Chế độ tài khoản | `posMode=hedge_mode`, `marginMode=crossed`, `assetMode=single`, tài khoản Classic (v2 trả `00000`) | Chặn, không tự đổi |
| R3 | Symbol | ∈ {BTCUSDT, ETHUSDT}; `symbolStatus=normal`; `limitOpenTime=-1`; `offTime=-1` | Chặn |
| R4 | Đồng hồ | `|local − server| < 2 s` (sàn từ chối nếu > 30 s) | Chặn |
| R5 | Plan còn hạn | ≤ 10 phút từ preview và lệch giá ≤ 0.3% | Chặn, yêu cầu preview lại |
| R6 | Thang trùng | Không có thang công cụ đang hoạt động cùng (symbol, holdSide) | Chặn |
| R7 | Vị thế/lệnh tay | Không có vị thế hoặc lệnh mở *không thuộc công cụ* trên cùng (symbol, holdSide) | Chặn |
| R8 | Cap mỗi thang | notional thang ≤ `capLeg × E` và ≤ giới hạn cứng 2.0x | Chặn |
| R9 | Cap tổng | `exposure_worst / E` ≤ cap biến thể (3/5/8x) và ≤ cứng 8x | Chặn |
| R10 | Cap cùng chiều | `same_dir_worst / E` ≤ cap cùng chiều (1.5/2.5/2.5x) và ≤ cứng 2.5x | Chặn |
| R11 | Số lớp & khoảng cách | 1 ≤ N ≤ 5; mọi khoảng cách giữa 2 lớp ≥ 1.0% (cứng) | Chặn |
| R12 | Size tối thiểu | mọi `q_i ≥ minTradeNum`, `q_i·P_i ≥ minTradeUSDT` | Chặn |
| R13 | SL tồn tại & hợp lệ | SL tính được, nằm ngoài lớp cuối ≥ 1%, lỗ dự kiến ≤ `s × E` và `s` ≤ cứng 7% | Chặn |
| R14 | Tổng rủi ro đồng thời | Σ lỗ-tại-SL của mọi thang đang mở + thang mới ≤ 20% E (cứng 25%) | Chặn |
| R15 | Khoảng cách thanh lý | kịch bản 4.8(b): `move_to_liq ≥ 3 × khoảng cách SL`, MM/E tại SL < 10% | Chặn |
| R16 | Ký quỹ khả dụng | ký quỹ ban đầu cần (Σ notional / leverage) ≤ 50% `crossedMaxAvailable` | Chặn |
| R17 | Đòn bẩy symbol | leverage cài trên sàn ≤ cứng 20x (≤ 50x nếu symbol đang có thang Scalp, vì leverage cross áp chung cho symbol – Q5) | Chặn (hoặc đặt về 10x nếu được phép, mục 4.2) |
| R18 | Drawdown breaker | E ≥ 80% đỉnh equity 30 ngày (theo dõi trong DB) | Chặn mở mới; gợi ý nghỉ 24h & dùng `safe` |
| R19 | Lỗ ngày | Lỗ thực hiện hôm nay (00:00 UTC+7) ≤ 10% E đầu ngày | Chặn mở mới đến hết ngày |
| R20 | Chuỗi stop | ≤ 2 lần SL trong 24h gần nhất | Chặn mở mới 12h |
| R21 | Cờ TA | ≠ AVOID (hoặc có `--override-avoid` với lý do) | Chặn / cảnh báo |
| R22 | Cờ tin tức (P3) | ≠ AVOID | Chặn / cảnh báo |
| R23 | Post-only khả thi | Long: mọi giá entry ≤ `bidPr`; Short: ≥ `askPr` (nếu không, lớp 1 sẽ bị từ chối post-only) | Re-anchor lớp 1 (nếu `anchor=market`) hoặc chặn |
| R24 | Funding | `|fundingRate|` ≤ 0.1%/kỳ, nếu phe mình trả funding cực trị → CAUTION | Cảnh báo |
| R25 | Watcher | Tiến trình `sync` đang chạy (heartbeat < 60 s) | Chặn execute (không có watcher = không có TP/BE) |

Kết quả mỗi kiểm tra PHẢI hiện trong preview (bảng PASS/FAIL/WARN + giá trị đo được + ngưỡng).

**Scalp mode** dùng cùng bảng nhưng thay ngưỡng: R8–R10 → cap 4.12.2 (tổng 15x/cứng 20x, cùng chiều 10x/cứng 15x); R11 → d ≥ 0.15%, ≤ 12 lớp; R13 → SL khẩn cấp ≤ 15% E bắt buộc; R14 → Σ lỗ-tại-SL ≤ 30% E; R15 → khoảng cách liq ≥ 3% từ giá mỗi lớp; R16 → ký quỹ cần ≤ 80% `crossedMaxAvailable`; R17 → đòn bẩy cài trên sàn cho Scalp 25–50x (cứng ≤ 50x) vì ở cross, ký quỹ ban đầu của lệnh treo = notional/leverage (15x E ở 10x leverage cần 1.5 E ký quỹ – không đặt được). Đòn bẩy cài không thay đổi rủi ro thật; rủi ro do notional + SL quyết định; R19 → khoá ngày 4.12.5; R21 (cờ TA) chỉ cảnh báo, không chặn (người dùng tự quyết), nhưng cờ được ghi vào nhật ký.

### 5.3 Quy tắc vận hành bất biến

- Không thêm lớp thứ 6; không "nhồi tay" qua công cụ; không có lệnh mở vị thế nào thiếu SL đi kèm.
- SL không bao giờ bị huỷ khi còn vị thế (trừ thao tác `kill --close-positions` đóng vị thế trước rồi mới huỷ SL).
- Giới hạn cứng (Phụ lục A) là **hằng số trong mã**; cấu hình chỉ được *thấp hơn hoặc bằng*. Giá trị cấu hình vượt → lỗi khởi động (không âm thầm cắt).
- Equity thay đổi > 10% so với lúc mở thang → không điều chỉnh thang đang chạy, nhưng thang mới tính theo E mới.

---

## 6. Module phân tích kỹ thuật (TA)

> **Nhãn bắt buộc trên mọi đầu ra:** "Bộ lọc rủi ro cho thang DCA, KHÔNG phải dự báo giá." Trong backtest hiện có, bộ lọc xu hướng đơn giản (ADX 4h > 30, độ lệch EMA50 1h) **không cải thiện** kết quả thang thưa. Bộ lọc mở rộng và chế độ `levels` dưới đây **chưa được backtest** → chỉ được bật để *chặn* sau khi qua cổng backtest ở 6.8. Trước đó: chỉ hiển thị.

### 6.1 Dữ liệu đầu vào

| Dữ liệu | Endpoint (public) | Tham số | Ghi chú |
|---|---|---|---|
| Nến 15m, 1H, 4H, 1D | `GET /api/v2/mix/market/candles` (gần) và `history-candles` (cũ) | `granularity`=15m/1H/4H/1D, `limit` ≤ 1000 (candles, mặc định 100) / ≤ 200 (history-candles); khoảng startTime–endTime ≤ 90 ngày | Cần ≥ 300 nến mỗi TF (EMA200 + phân vị). Sàn giới hạn lịch sử: 15m ~52 ngày, 1H ~83 ngày, 4H ~240 ngày qua `candles` |
| Nến 1m (tuỳ chọn cho VWAP chính xác) | như trên | 1m (≤ 1 tháng) | |
| Ticker | `GET /api/v2/mix/market/ticker` | | lastPr, bidPr, askPr, markPrice, fundingRate |
| Funding hiện tại / lịch sử | `current-fund-rate`, `history-fund-rate` | 30 ngày | phân vị funding |
| Open interest | `GET /api/v2/mix/market/open-interest` | | Chỉ trả giá trị hiện tại → công cụ PHẢI tự lưu snapshot mỗi 5 phút để tính ΔOI 1h/4h/24h |
| Long/short ratio | `GET /api/v2/mix/market/long-short`, `account-long-short`, `position-long-short` | `period`=1h | giới hạn 1 req/s/IP |
| Thống kê toàn thị trường (tuỳ chọn) | nguồn ngoài | | Không bắt buộc |

Chuẩn hoá nến: mảng tăng dần theo thời gian mở nến; **chỉ dùng nến đã đóng** (bỏ nến đang chạy) cho mọi chỉ báo, trừ "giá hiện tại".

### 6.2 Chỉ báo & thông số (mỗi TF: 15m, 1h, 4h, 1d)

| Nhóm | Định nghĩa | Thông số mặc định |
|---|---|---|
| EMA | EMA20/50/200 (seed = giá đầu, α = 2/(n+1)) | 20, 50, 200 |
| Căn chỉnh EMA | "tăng đầy đủ": giá > EMA20 > EMA50 > EMA200 (+2); "giảm đầy đủ" (−2); còn lại ±1/±0.5 theo vị trí giá so với EMA50 và EMA50 so với EMA200 | |
| Cấu trúc swing | Pivot xác nhận k nến mỗi bên (k=3 cho 15m/1h, k=2 cho 4h/1d). So 2 đỉnh & 2 đáy gần nhất: HH+HL = tăng (+1), LH+LL = giảm (−1), còn lại = nén/mở rộng (0) | k = 3/2 |
| ADX/DI | Wilder RMA, n=14; regime: ADX ≥ 25 trend, < 20 range, giữa = chuyển tiếp | 14 |
| RSI | Wilder, n=14 | 14 |
| Phân kỳ RSI | Thường (regular): đáy giá thấp hơn & RSI đáy cao hơn (> 1 điểm) = bullish; đỉnh giá cao hơn & RSI đỉnh thấp hơn = bearish; pivot mới nhất trong 12 nến | lookback 12 |
| MACD | 12/26/9; dùng histogram và độ dốc histogram | 12, 26, 9 |
| Bollinger width | `BBW = 4·σ20/SMA20`; phân vị trong 120 nến; ≤ 15 = squeeze, ≥ 85 = expansion | 20, 2σ, 120 |
| ATR | Wilder 14; `ATR%` = ATR/close; phân vị ATR% trong 180 nến | 14, 180 |
| VWAP | VWAP ngày (từ 00:00 UTC); Anchored VWAP từ đáy 7 ngày và đỉnh 7 ngày | |
| Volume profile | 7 ngày và 14 ngày từ nến 15m; bin = 0.1% giá giữa; phân bổ volume đều trên [low, high] của nến; POC = bin max; Value Area 70% mở rộng từ POC; HVN/LVN = cực đại/cực tiểu cục bộ trên profile làm mượt 5 bin, HVN > 1.3× trung vị, LVN < 0.6× trung vị | 0.1%, 70% |
| Biên độ sốc | Biên độ 60 phút gần nhất / ATR1h; biên độ nến 1h cuối / ATR1h | |
| Funding | giá trị hiện tại; phân vị trong 30 ngày (90 kỳ 8h) | |
| ΔOI | % thay đổi OI 1h/4h/24h (từ snapshot tự lưu) | |
| Long/short ratio | giá trị hiện tại & z-score 7 ngày | |

**Bias mỗi TF:** `score = align_score + structure_score + di_score (±0.5 nếu ADX > 20) + macd_score (±0.5 theo dấu histogram)`; `score ≥ 1.5` → tăng, `≤ −1.5` → giảm, còn lại trung tính. **Regime tổng:** ≥ 2 TF (1h/4h/1d) có ADX ≥ 25 → "trend"; 1h và 4h đều ADX < 22 → "range"; còn lại "hỗn hợp".

### 6.3 Mức hỗ trợ/kháng cự (S/R) có điểm sức mạnh

1. Thu thập điểm ứng viên: pivot đỉnh/đáy các TF 1h/4h/1d (trọng số TF: 15m 0.5, 1h 1, 4h 2, 1d 3) × hệ số gần đây `0.5 + 0.5·(i/(n−1))`; cộng các mức đặc biệt với trọng số: POC 4, VAH/VAL 2.5, đỉnh/đáy 7 ngày 3, đỉnh/đáy 24h 2, HVN 2×(độ cao chuẩn hoá), VWAP ngày 1, AVWAP 7d 1.5.
2. Gom cụm: sắp xếp theo giá, gộp điểm cách điểm cao nhất của cụm ≤ `tol = max(0.25% giá, 0.5·ATR1h)`.
3. Giá cụm = trung bình có trọng số; `strength = 100 × raw_weight / max_raw_weight` (0–100); `touches` = số điểm; `sources` = danh sách nguồn.
4. Giữ tối đa 14 mức trong ±15% giá hiện tại, phân loại support (dưới giá) / resistance (trên giá).
5. LVN được báo cáo riêng như "vùng trống" (giá dễ chạy nhanh qua) – không dùng làm mức snap.

### 6.4 Cờ rủi ro thang (`ladder_risk`) – cho từng chiều long/short
AVOID (bất kỳ điều kiện nào):

- 4h ADX > 30 **và** DI ngược chiều thang **và** cấu trúc 4h ngược chiều (vd thang long khi 4h LH/LL).
- Nến 1h gần nhất có biên độ > 3× ATR1h, hoặc biên độ 60 phút gần nhất > 3× ATR1h (biến động sốc).
- (P3) Sự kiện vĩ mô mức cao trong cửa sổ cấm (mục 6.9).

CAUTION (bất kỳ điều kiện nào):

- 4h ADX > 30 với DI ngược chiều (cấu trúc chưa xác nhận); 1h ADX > 35 với DI ngược chiều.
- 1d và 4h cùng bias ngược chiều thang.
- 4h Bollinger squeeze (BBW phân vị ≤ 15).
- ATR1h phân vị ≥ 90.
- ATR1d% > 0.8 × độ sâu thang (vd > 4.7% với thang 5.87%).
- Funding cực trị phe mình (|f| ≥ 0.05%/kỳ, hoặc phân vị ≥ 95 cho long / ≤ 5 cho short).
- Phân kỳ RSI 1h/4h ngược chiều thang.
- ΔOI 4h > +10% đi cùng giá chạy ngược chiều thang (đòn bẩy mới đổ vào xu hướng) – *ngưỡng cần hiệu chỉnh bằng backtest*.
- Long/short ratio z-score cực trị (|z| > 2) cùng phe mình.

Ngược lại → OK. Mỗi lý do là một chuỗi tiếng Việt có số đo cụ thể (vd "4h ADX 34 với DI ngược chiều thang").

### 6.5 Chế độ khoảng cách `levels` (snap theo S/R)
Thuật toán (tham chiếu `trader/snap.py`):

- Lớp 1 = anchor. Với lớp i ≥ 2: mục tiêu cố định `tgt_i = P_1·(1 − sg·d)^(i−1)`.
- Ứng viên: mức support (long) / resistance (short) có `strength ≥ 40`, giá đặt lệnh `q = level × (1 + sg·0.001)` (đặt **trước** mức 0.1% – phía trên support cho long, dưới resistance cho short), thoả: (a) cách lớp trước ≥ `min_gap` = **1.0%**; (b) `|q/tgt_i − 1| ≤ 0.4·d` (cửa sổ ±0.6% với d=1.5%); (c) độ sâu tổng ≤ độ sâu fixed + 0.5·d.
- Chọn ứng viên strength cao nhất (hoà → gần mục tiêu hơn). Không có ứng viên → dùng `tgt_i` (nếu vi phạm min_gap thì `prev·(1 − sg·min_gap)`).
- Sau khi snap: tính lại size (ngân sách B mỗi lớp theo giá mới), SL (mục 4.6), và **chạy lại toàn bộ kiểm tra mục 5** – snap không bao giờ được làm vượt cap hay giảm khoảng cách < 1%.
- Bảng preview đánh dấu lớp nào được snap, mức nào, strength bao nhiêu.

### 6.6 Hiệu năng

- `ta` cho 1 symbol hoàn tất < 5 s (bao gồm tải dữ liệu, có cache nến trên đĩa, chỉ tải phần mới).
- Mã TA thuần hàm, chạy được trên lát cắt lịch sử (để backtest), không lookahead.

### 6.7 Schema đầu ra JSON (`ta --json`)
```json
{
  "schema_version": "ta.v1",
  "symbol": "ETHUSDT",
  "generated_at": "2026-10-20T07:55:00+07:00",
  "price": 2398.78,
  "mark_price": 2398.90,
  "disclaimer": "Bộ lọc rủi ro cho thang DCA, KHÔNG phải dự báo giá.",
  "changes_pct": {"1h": -0.12, "4h": 0.35, "24h": -0.75, "7d": 2.1},
  "range": {"hi24": 2445.68, "lo24": 2383.94, "hi7d": 2510.0, "lo7d": 2290.0},
  "timeframes": {
    "1h": {
      "close": 2398.78, "ema20": 2401.2, "ema50": 2405.0, "ema200": 2380.4,
      "ema_align": "lẫn lộn", "structure": "LH/HL (nén)", "structure_score": 0,
      "adx": 18.4, "pdi": 21.0, "ndi": 23.5, "rsi": 47.2,
      "rsi_divergence": [],
      "macd": -1.2, "macd_signal": -0.8, "macd_hist": -0.4, "macd_hist_prev": -0.6,
      "bb_width_pct": 1.9, "bb_width_rank": 22,
      "atr": 18.2, "atr_pct": 0.76, "atr_pct_rank": 41,
      "last_swing_high": 2445.6, "last_swing_low": 2383.9,
      "score": -0.5, "bias": "trung tính", "regime": "range"
    },
    "15m": {"...": "cùng cấu trúc"}, "4h": {"...": "..."}, "1d": {"...": "..."}
  },
  "regime": "range | trend | hỗn hợp",
  "mtf_score": -1.0,
  "vwap": {"day": 2405.1, "avwap_7d_low": 2360.2, "avwap_7d_high": 2440.8},
  "volume_profile": {
    "7d":  {"poc": 2410.0, "vah": 2448.0, "val": 2372.0, "hvn": [[2410.0, 1.0]], "lvn": [[2340.0, 0.21]], "bin": 2.4},
    "14d": {"poc": 2395.0, "vah": 2470.0, "val": 2330.0, "hvn": [], "lvn": [], "bin": 2.4}
  },
  "levels": [
    {"price": 2364.5, "type": "support", "strength": 82, "touches": 6,
     "sources": ["swing 4h", "VAL", "7d low"], "dist_pct": -1.43}
  ],
  "derivatives": {
    "funding_rate": 0.0001, "funding_pctile_30d": 55,
    "oi": 786838.55, "oi_change_pct": {"1h": 0.4, "4h": 1.2, "24h": -2.0},
    "long_short_ratio": 1.21, "long_short_z7d": 0.6
  },
  "risk": {
    "long":  {"flag": "OK | CAUTION | AVOID", "reasons": ["..."]},
    "short": {"flag": "CAUTION", "reasons": ["1d và 4h cùng thiên tăng (ngược chiều thang)"]}
  },
  "data_quality": {"missing_bars": 0, "stale_seconds": 3, "oi_history_points": 288}
}
```
Quy định: số là số (không phải chuỗi); giá làm tròn theo `pricePlace`; trường không tính được = `null` kèm lý do trong `data_quality.notes`. Thay đổi schema → tăng `schema_version`.

### 6.8 Cổng backtest bắt buộc trước khi dùng TA để chặn/snap
Developer PHẢI chạy (tái sử dụng engine 1m trong `planner/sim.py`/`final_eval.py` hoặc tương đương đã được đối chiếu với kết quả `final_eval.csv` sai số ≤ 1%):

1. **Baseline**: tái tạo SAFE/DEFAULT 180 ngày (2026-04-22 → 10-20) – lợi nhuận, DD, số stop khớp `final_eval.csv` (±1 điểm %).
2. **Bộ lọc**: thang chỉ được mở khi cờ ≠ AVOID (biến thể A) và ≠ AVOID/CAUTION (biến thể B). TA tính trên dữ liệu đến nến **đã đóng** trước thời điểm mở thang (không lookahead; chỉ báo dùng `history` lát cắt).
3. **Levels**: spacing `levels` vs `fixed`, cùng mọi tham số khác.
4. Báo cáo trên **cả 2 nửa** (A_bear 04-22..07-21, B_bull 07-21..10-20) và toàn kỳ: lợi nhuận, max DD, số stop, lỗ ngày tệ nhất, phí/lãi gộp, số thang bị bỏ qua.
5. Kiểm tra độ nhạy: ngưỡng ADX ±5, strength 30/40/50, window 0.3/0.4/0.5.
6. **Tiêu chí bật**: chỉ bật chặn/snap nếu cải thiện `return/maxDD` ở **cả hai** nửa và không tăng số stop > 10%; ngược lại để chế độ "chỉ hiển thị". Kết quả lưu `backtest/ta_gate_report.md`.
7. Khuyến cáo: dữ liệu OI/long-short lịch sử có thể không đủ → các điều kiện dùng OI/LS ratio chỉ hiển thị cho tới khi có đủ dữ liệu tự lưu (≥ 60 ngày).

### 6.9 Lớp tin tức (P3 – sau TA)

- **Lịch kinh tế**: CPI, Core PCE, FOMC (quyết định lãi suất + họp báo), NFP, phát biểu Chủ tịch Fed. Nguồn: cấu hình được (vd feed lịch kinh tế công khai, hoặc file YAML do chủ nhập tay hằng tuần) **[nguồn cụ thể: CHƯA CHỌN]**. Quy tắc: AVOID mở thang mới từ T−60 phút đến T+60 phút sự kiện mức cao; CAUTION T−4h..T+4h. (Không động vào thang đang chạy.)
- **Tin crypto lớn**: từ khoá (hack/exploit, ETF approval/denial, SEC/CFTC, sàn mất thanh khoản, depeg stablecoin, liquidations > X tỷ USD) từ nguồn tin (RSS/API) → CAUTION; xác nhận ≥ 2 nguồn → AVOID 6h.
- **Sentiment X**: đếm số bài/giờ có từ khoá BTC/ETH + "crash/dump/pump/liquidation"; z-score so với 7 ngày; |z| > 3 → CAUTION. Chỉ là tín hiệu phụ.
- Đầu ra hợp nhất vào `risk.<side>.reasons` với tiền tố `[news]`; schema `news.v1` (event list, nguồn, thời gian UTC+7, mức độ).
- Lớp tin tức cũng phải qua backtest/quan sát forward ≥ 4 tuần trước khi được chặn cứng.

---

## 7. Tích hợp API Bitget v2 (Classic account, USDT-M)

Base URL: `https://api.bitget.com`. Tất cả tham số chuỗi; số gửi dạng chuỗi thập phân. Phản hồi thành công: `code == "00000"`.

### 7.1 Ký request

- Header bắt buộc: `ACCESS-KEY`, `ACCESS-SIGN`, `ACCESS-TIMESTAMP` (epoch **ms**), `ACCESS-PASSPHRASE`, `Content-Type: application/json`, `locale: en-US`.
- Chuỗi ký: `timestamp + METHOD + requestPath + ("?" + queryString nếu có) + body`. GET: body rỗng. POST: body là **đúng chuỗi JSON được gửi** (serialize một lần, ký và gửi cùng một chuỗi byte).
- `ACCESS-SIGN = Base64( HMAC_SHA256(secretKey, chuỗi_ký) )`. (Bitget cũng hỗ trợ RSA – không dùng ở MVP.)
- Timestamp phải trong ±30 s so với giờ server; đồng bộ bằng `GET /api/v2/public/time` khi khởi động và mỗi 10 phút (đã gọi thử 2026-10-20: trả `data.serverTime` dạng ms).
- Thứ tự tham số query khi ký phải trùng với URL thật gửi đi (tạo query string một lần, dùng cho cả hai).
- **Demo trading**: dùng **Demo API Key** (tạo trong chế độ Demo trên web) + header `paptrading: 1`. Theo tài liệu, `productType`/symbol giữ nguyên (`USDT-FUTURES`, `ETHUSDT`) khi dùng header này; cách cũ dùng `SUSDT-FUTURES`/`SETHSUSDT` không có header **[cần xác nhận bằng thử thực tế]**. Lưu ý: `fill-history` **không hỗ trợ** demo → dùng `order/fills`/`order/detail`. WebSocket demo: `wss://wspap.bitget.com/v2/ws/...` (nguồn: issue ccxt, chưa xác minh trên tài liệu chính thức).

### 7.2 Danh sách endpoint sử dụng

| Mục đích | Method & path | Rate limit (tài liệu) | Key |
|---|---|---|---|
| Thông số hợp đồng | GET `/api/v2/mix/market/contracts?productType=USDT-FUTURES&symbol=` | 20/s/IP | public |
| Bậc MMR | GET `/api/v2/mix/market/query-position-lever?productType=&symbol=` | 10/s/IP | public |
| Ticker | GET `/api/v2/mix/market/ticker?productType=&symbol=` | 20/s/IP | public |
| Nến | GET `/api/v2/mix/market/candles`, `/history-candles` | 20/s/IP | public |
| Funding | GET `/api/v2/mix/market/current-fund-rate`, `/history-fund-rate` | 20/s/IP | public |
| OI | GET `/api/v2/mix/market/open-interest` | 20/s/IP | public |
| Long/short | GET `/api/v2/mix/market/long-short`, `/account-long-short`, `/position-long-short` | 1/s/IP | public |
| Tài khoản | GET `/api/v2/mix/account/account?symbol=&productType=&marginCoin=USDT` | 10/s/UID | read |
| Vị thế | GET `/api/v2/mix/position/all-position?productType=&marginCoin=USDT` | 5/s/UID | read |
| Vị thế 1 symbol | GET `/api/v2/mix/position/single-position` | 10/s/UID | read |
| Lệnh treo | GET `/api/v2/mix/order/orders-pending?productType=` (phân trang `idLessThan`, `limit` ≤ 100) | 10/s/UID | read |
| Chi tiết lệnh | GET `/api/v2/mix/order/detail?symbol=&productType=&clientOid=` | 10/s/UID | read |
| Fills | GET `/api/v2/mix/order/fills?productType=&symbol=` (≤ 100/lần) | 10/s/UID | read |
| Lệnh plan/TP-SL treo | GET `/api/v2/mix/order/orders-plan-pending?productType=&planType=profit_loss` (và `normal_plan`) | 10/s/UID | read |
| Ước tính liq | GET `/api/v2/mix/account/liq-price` | 20/s/UID | read |
| Đặt đòn bẩy | POST `/api/v2/mix/account/set-leverage` | 5/s/UID | trade |
| Đặt lệnh | POST `/api/v2/mix/order/place-order` | 10/s/UID | trade |
| Đặt lệnh lô | POST `/api/v2/mix/order/batch-place-order` (≤ 50 lệnh, cùng symbol) | 5/s/UID | trade |
| Sửa lệnh | POST `/api/v2/mix/order/modify-order` | 10/s/UID | trade |
| Huỷ lệnh | POST `/api/v2/mix/order/cancel-order` | 10/s/UID | trade |
| Huỷ lô | POST `/api/v2/mix/order/batch-cancel-orders` (≤ 50 id) | 10/s/UID | trade |
| Huỷ tất cả | POST `/api/v2/mix/order/cancel-all-orders` | 10/s/UID | trade – **CẤM dùng** (huỷ cả lệnh tay) |
| Đặt TP/SL | POST `/api/v2/mix/order/place-tpsl-order` | 10/s/UID | trade |
| Sửa TP/SL | POST `/api/v2/mix/order/modify-tpsl-order` (với pos_loss: `"size":""`) | 10/s/UID | trade |
| Huỷ lệnh plan/TP-SL | POST `/api/v2/mix/order/cancel-plan-order` | 10/s/UID | trade |
| Đóng nhanh vị thế | POST `/api/v2/mix/order/close-positions` (`holdSide`) | 1/s/UID | trade – chỉ dùng trong `kill --close-positions` |

Rate-limiter phía client: token-bucket theo từng endpoint ở **50%** giới hạn tài liệu; xử lý HTTP 429 / mã giới hạn → backoff lũy tiến (0.5, 1, 2, 4 s, tối đa 5 lần, có jitter). Một vòng đối soát (60 s) dùng ≤ ~6 request; trạng thái thời gian thực lấy từ WebSocket (mục 8.5).

### 7.3 Ngữ nghĩa Hedge mode (đã xác minh trên tài liệu place-order)

| Hành động | `side` | `tradeSide` | `reduceOnly` |
|---|---|---|---|
| Mở long | `buy` | `open` | không gửi |
| **Đóng long** | `buy` | `close` | không gửi |
| Mở short | `sell` | `open` | không gửi |
| **Đóng short** | `sell` | `close` | không gửi |

- Trong hedge mode `side` = **hướng vị thế**, không phải hướng mua/bán. Đóng long là `side=buy, tradeSide=close` (dễ nhầm!). Unit test PHẢI khoá bảng này.
- `reduceOnly` **chỉ áp dụng one-way mode** → không gửi trong hedge mode (lệnh close đã tự giảm vị thế).
- Lệnh close bị giới hạn bởi khối lượng khả dụng của vị thế. Theo tài liệu: trong hedge mode, nếu lệnh limit close đang "chiếm" vị thế và lệnh market close mới + lệnh limit vượt tổng vị thế → lệnh market **chỉ đóng phần còn lại** (vd vị thế 100, limit chiếm 70, market close 50 → chỉ đóng 30), không huỷ lệnh limit; và nếu tổng lệnh close limit = vị thế thì lệnh close mới sẽ tự huỷ lệnh limit đang chiếm (hai câu trong tài liệu mâu thuẫn một phần) → xem rủi ro 7.6.
- `tradeSide` cho lệnh plan (`place-plan-order`): cùng quy ước (close long = buy + close).
- `holdSide` cho TP/SL (`place-tpsl-order`, `close-positions`): `long` / `short`.

### 7.4 Payload mẫu
**(a) Entry lớp 1, ETH long, post-only:**
```json
POST /api/v2/mix/order/place-order
{"symbol":"ETHUSDT","productType":"USDT-FUTURES","marginMode":"crossed","marginCoin":"USDT",
 "size":"0.03","price":"2400.00","side":"buy","tradeSide":"open","orderType":"limit",
 "force":"post_only","clientOid":"gdl1-K7Q2M9XA-EL-E1-0",
 "presetStopLossPrice":"2174.58"}
```
`presetStopLossPrice` là phương án dự phòng để vị thế có SL ngay khi khớp lớp đầu; theo ghi chú batch-place-order, TP/SL preset là cấp vị thế ("nếu chưa có vị thế → preset; nếu đã có → sửa TP/SL") **[CHƯA XÁC MINH trong hedge+cross; kiểm Demo test D7]**. Nếu Demo cho thấy preset tạo SL theo từng lệnh thay vì cấp vị thế → bỏ preset, chỉ dùng (c).

**(b) Các lớp DCA 2–5 – batch:**
```json
POST /api/v2/mix/order/batch-place-order
{"symbol":"ETHUSDT","productType":"USDT-FUTURES","marginMode":"crossed","marginCoin":"USDT",
 "orderList":[
  {"size":"0.03","price":"2364.00","side":"buy","tradeSide":"open","orderType":"limit","force":"post_only","clientOid":"gdl1-K7Q2M9XA-EL-E2-0"},
  {"size":"0.03","price":"2328.54","side":"buy","tradeSide":"open","orderType":"limit","force":"post_only","clientOid":"gdl1-K7Q2M9XA-EL-E3-0"},
  {"size":"0.03","price":"2293.61","side":"buy","tradeSide":"open","orderType":"limit","force":"post_only","clientOid":"gdl1-K7Q2M9XA-EL-E4-0"},
  {"size":"0.03","price":"2259.20","side":"buy","tradeSide":"open","orderType":"limit","force":"post_only","clientOid":"gdl1-K7Q2M9XA-EL-E5-0"}]}
```
Phản hồi có `successList`/`failureList` và `result`. **Thành công một phần** → xử lý từng phần tử (thử lại phần lỗi tối đa 2 lần với *cùng* clientOid; vẫn lỗi → huỷ toàn bộ entry chưa khớp của thang và báo cáo).

**(c) Stop-loss cấp vị thế (sau khi có vị thế):**
```json
POST /api/v2/mix/order/place-tpsl-order
{"marginCoin":"USDT","productType":"USDT-FUTURES","symbol":"ETHUSDT","planType":"pos_loss",
 "triggerPrice":"2174.58","triggerType":"mark_price","executePrice":"0","holdSide":"long",
 "clientOid":"gdl1-K7Q2M9XA-EL-SL-0"}
```
`pos_loss` không cần `size` (áp cho toàn vị thế). Tài liệu không nói rõ có đặt được khi **chưa có vị thế** → giả định KHÔNG; watcher đặt ngay khi phát hiện fill đầu tiên (mục 8.2) **[CXM]**. Dời SL về hoà vốn: `modify-tpsl-order` với `clientOid` của SL, `triggerPrice` mới, `size:""` (hoặc huỷ + đặt lại với `rev+1`, đảm bảo khoảng hở không quá 1 vòng gọi; ưu tiên *đặt mới trước, huỷ cũ sau* nếu sàn cho phép 2 pos_loss – **[CXM]**).

**(d) TP1 (đóng 50%) – limit close post-only:**
```json
POST /api/v2/mix/order/place-order
{"symbol":"ETHUSDT","productType":"USDT-FUTURES","marginMode":"crossed","marginCoin":"USDT",
 "size":"0.01","price":"2428.80","side":"buy","tradeSide":"close","orderType":"limit",
 "force":"post_only","clientOid":"gdl1-K7Q2M9XA-EL-T1-0"}
```
TP2 tương tự với `T2`. Khi giá TB đổi (lớp mới khớp): huỷ T1/T2 cũ theo clientOid rồi đặt lại với `rev+1` (`...-T1-1`). Có thể dùng `modify-order` (bắt buộc truyền `newClientOid`, phải truyền cả `newSize` và `newPrice`; sàn huỷ lệnh cũ và tạo lệnh mới bất đồng bộ).

**(e) Huỷ theo clientOid:**
```json
POST /api/v2/mix/order/cancel-order
{"symbol":"ETHUSDT","productType":"USDT-FUTURES","marginCoin":"USDT","clientOid":"gdl1-K7Q2M9XA-EL-E3-0"}
```
Lệnh plan/TP-SL: `cancel-plan-order` **luôn truyền `orderIdList` + `symbol` + `planType`** – nếu bỏ `orderIdList`, sàn huỷ **mọi** lệnh plan của symbol/productType (kể cả lệnh tay).

**(f) Đóng khẩn cấp (chỉ `kill --close-positions --confirm-close`):**
```json
POST /api/v2/mix/order/close-positions
{"symbol":"ETHUSDT","productType":"USDT-FUTURES","holdSide":"long"}
```
Chỉ áp cho (symbol, holdSide) có thang công cụ. Không gọi khi bỏ trống `holdSide` (sẽ đóng cả hai chiều).

### 7.5 Quy ước `clientOid`
Định dạng: `{prefix}-{plan_id}-{leg}-{role}{idx}-{rev}`

- `prefix` = `gdl1` (cố định trong mã; `kill` chỉ đụng lệnh có tiền tố này).
- `leg` = `BL`/`BS`/`EL`/`ES` (BTC long/short, ETH long/short).
- `role`: `E` entry (idx 1..5), `T1`/`T2` take-profit, `SL` stop, `BE` stop hoà vốn, `X` đóng khẩn.
- `rev`: số lần đặt lại (0, 1, 2…).
- Ví dụ: `gdl1-K7Q2M9XA-EL-T1-3` (≤ 32 ký tự; chỉ `[A-Za-z0-9-]`). **[CHƯA XÁC MINH: độ dài tối đa & ký tự cho phép của clientOid; tính duy nhất trong bao lâu; mã lỗi khi trùng]**.
- clientOid được sinh và **lưu DB trước khi gửi**. Khi timeout/không rõ kết quả: truy vấn `order/detail?clientOid=` trước khi gửi lại; không bao giờ tạo clientOid mới cho cùng ý định trừ khi lệnh cũ chắc chắn không tồn tại.

### 7.6 Rủi ro tích hợp phải kiểm Demo (chặn go-live)

1. **SL bị "chiếm" bởi lệnh TP limit close**: TP1+TP2 limit close chiếm 100% vị thế. Khi `pos_loss` kích hoạt (market close), theo tài liệu có thể chỉ đóng phần chưa bị chiếm → **không đóng gì**. PHẢI kiểm (test D9). Phương án nếu đúng là vậy: (i) TP dạng `profit_plan` trigger (`place-tpsl-order`, `size`, `executePrice` = giá TP → limit khi kích hoạt; không chiếm vị thế cho tới khi kích hoạt; nhưng có thể khớp taker), hoặc (ii) watcher theo dõi mark price và khi còn cách SL < 0.5% thì huỷ TP limit (không đủ an toàn khi gap) – ưu tiên (i). Quyết định ghi vào `docs/decisions.md`.
2. **Post-only bị từ chối/huỷ khi cắt giá**: xác định sàn trả lỗi đồng bộ hay nhận lệnh rồi huỷ (`status=canceled`). Watcher phải xử lý cả hai.
3. **Giới hạn giá lệnh** (`buyLimitPriceRatio`/`sellLimitPriceRatio` 5%, lỗi 22046/22006/22007): lớp cách > 5% có bị từ chối? → quyết định bật `lazy_layers`.
4. **Preset SL** (`presetStopLossPrice`) trong hedge+cross: cấp vị thế hay từng lệnh; có bị ghi đè khi lớp sau khớp không.
5. **pos_loss khi vị thế tăng**: SL cấp vị thế có tự áp cho phần khối lượng mới khớp không (kỳ vọng: có).
6. **Đổi leverage khi đang có vị thế/lệnh treo** (cross).
7. **Partial fill** của entry & TP: `orders-pending` trả `partially_filled`; giá TB lấy từ `all-position.openPriceAvg`.

### 7.7 Lỗi thường gặp & xử lý

| Mã | Ý nghĩa (theo tài liệu/cộng đồng) | Xử lý |
|---|---|---|
| `00000` | Thành công | – |
| 40762 | Số tiền lệnh vượt số dư (thiếu ký quỹ) | Không thử lại; FAIL execute; kiểm tra R16 |
| 45110 / 22034 | Dưới giá trị tối thiểu (5 USDT) | Lỗi tính size → bug, dừng |
| 22038 | Size không phải bội số của lot | Bug làm tròn, dừng |
| 22002 | Không có vị thế để đóng | Đối soát lại vị thế; huỷ TP mồ côi |
| 22001 | Không có lệnh để huỷ | Coi như đã huỷ (idempotent) |
| 22003 | Sửa giá/size phải có `newClientOid` | Bug |
| 22046 / 22006 / 22007 | Giá vượt giới hạn giá sàn | Xem 7.6(3) |
| 22010 | Phải bind IP whitelist | Cấu hình key |
| 22030 / 22035 | Hạn chế demo | Log, giảm tần suất |
| 40012 | apikey/passphrase sai | Dừng; kiểm tra key |
| 40084 | Tài khoản không đúng chế độ (Classic vs UTA) | Dừng; xem câu hỏi mở Q8 |
| HTTP 429 / mã giới hạn tần suất | Vượt rate limit | Backoff |
| Timeout/5xx | Không rõ kết quả | Truy vấn theo clientOid trước khi gửi lại |
> Bảng mã lỗi được lấy từ trang error-code UTA/WebSocket và báo cáo cộng đồng; **[CHƯA XÁC MINH đầy đủ cho REST Classic]**. Developer PHẢI log nguyên `code` + `msg` và bổ sung bảng này từ Demo.

---

## 8. Trạng thái, lưu trữ, log, triển khai & đồng bộ dữ liệu

### 8.1 Lưu trữ

- **SQLite** `state/state.db` (WAL mode) – bảng tối thiểu:
  - `plans(plan_id PK, created_at, expires_at, env, variant, ref_price, equity, params_json, checks_json, ta_json, status, content_hash)`
  - `legs(leg_id PK, plan_id FK, symbol, hold_side, state, n_layers, filled_layers, qty, avg_price, sl_price, be_active, tp1_done, opened_at, closed_at, close_reason, realized_pnl, fees, funding)`
  - `orders(client_oid PK, leg_id FK, role, idx, rev, exch_order_id, kind(order|plan), price, trigger_price, size, filled, status, created_at, updated_at, last_error)`
  - `fills(trade_id PK, client_oid, order_id, price, size, fee, side, trade_side, ts)`
  - `equity_snapshots(ts, equity, notional, mm_ratio)` (mỗi phút) – dùng cho R18/R19.
  - `oi_snapshots(ts, symbol, oi)` (mỗi 5 phút) – dùng cho TA.
  - `events(ts, level, kind, leg_id, message, data_json)`.
- `plans/<plan_id>.json` – bản sao plan để người đọc được.
- `journal/legs.csv` – mỗi thang đã đóng một dòng (giờ UTC+7, symbol, chiều, số lớp khớp, giá TB, lý do đóng, PnL gộp/phí/funding/ròng, MAE%).

### 8.2 Máy trạng thái của một thang (leg)
```
PLANNED ─execute─► PLACING ─ok─► WORKING (0 lớp khớp, entry treo)
   │                  │fail                │ fill lớp 1
   ▼                  ▼                    ▼
EXPIRED          FAILED(đã dọn)        ACTIVE(k lớp) ──fill thêm──► ACTIVE(k+1)  [đặt lại T1/T2, kiểm SL]
                                           │ TP1 khớp
                                           ▼
                                       TP1_DONE  [huỷ entry còn lại, SL→BE, T2 giữ]
                                           │ T2 / BE / SL / đóng tay / kill
                                           ▼
                                        CLOSED(lý do)
WORKING ─cancel─► CANCELLED ; mọi trạng thái có vị thế ─SL─► CLOSED(stop)
```
Quy tắc watcher: chạy theo sự kiện WebSocket (orders/positions/account – mục 8.5) cộng một vòng đối soát REST mỗi 60 s (và ngay khi (re)connect):

1. Lấy trạng thái từ WS; ở vòng đối soát đọc REST `all-position`, `orders-pending`, `orders-plan-pending` (profit_loss), `account`.
2. Đối soát: mỗi lệnh DB ↔ sàn; lệnh công cụ trên sàn mà DB không biết → log `ORPHAN` (không tự huỷ trừ khi tiền tố đúng & plan đã đóng); vị thế công cụ có size ≠ tổng fill → `DRIFT` cảnh báo.
3. **SL trước tiên**: mọi leg có `total > 0` PHẢI có đúng 1 `pos_loss` với trigger = `sl_price` (±1 tick). Thiếu → đặt ngay. Không đặt được sau 3 lần/60 s → **báo động mức cao** và (theo cấu hình `on_sl_failure`, mặc định `close_leg`) đóng leg bằng market.
4. Fill mới (size vị thế tăng) → cập nhật `Q`, `A` từ `openPriceAvg`; huỷ & đặt lại T1/T2.
5. Size vị thế giảm do T1 khớp → `TP1_DONE`: huỷ entry còn lại (theo clientOid), dời SL → BE.
6. Vị thế = 0 → `CLOSED`, huỷ mọi lệnh còn lại của leg, tính PnL từ fills, ghi journal, thông báo.
7. Ghi heartbeat (R25) và `equity_snapshots`.
8. Lỗi mạng: không thay đổi gì; sau 5 vòng lỗi liên tiếp → báo động.

Khởi động lại: watcher PHẢI tái dựng trạng thái từ DB + sàn (không giả định gì từ bộ nhớ), chạy đối soát trước khi hành động.

### 8.3 Log

- `logs/YYYYMMDD.jsonl` (ngày theo UTC+7), mỗi dòng: `t` (ISO có offset +07:00), `env`, `kind` (pub/private/post), `method`, `path`, `query`, `body` (đã ẩn trường nhạy cảm), `http_status`, `code`, `msg`, `resp` (rút gọn ≤ 4 KB), `latency_ms`, `client_oid`, `plan_id`, `dry_run`.
- **Không bao giờ log** header `ACCESS-*`, secret, passphrase, chuỗi ký. Có test tự động quét log tìm giá trị secret.
- Log ứng dụng (`app.log`, xoay vòng 10 MB × 10) cho sự kiện nghiệp vụ; mức WARN/ERROR gửi thông báo (kênh do chủ chọn – Q6).
- Lưu log ≥ 90 ngày.

### 8.4 Dry-run

- `--dry-run` (hoặc cấu hình `dry_run: true`, **mặc định bật** khi cài lần đầu): chạy đầy đủ logic, GET thật, nhưng mọi POST bị chặn ở tầng `client` → log body đã ký giả lập và trả phản hồi giả `{"dry_run":true}`.
- Watcher ở dry-run mô phỏng khớp lệnh dựa trên giá nến 1m (giá chạm → coi như khớp) để kiểm tra luồng TP/SL/BE end-to-end trên dữ liệu thật mà không đặt lệnh.

### 8.5 Triển khai trên VPS & đồng bộ dữ liệu thời gian thực

**Nguyên tắc thiết kế cốt lõi – "lệnh nằm trên sàn":** mọi entry (limit post-only), TP (limit close) và **SL (lệnh trigger phía sàn – `pos_loss`, trigger mark price)** đều nằm sẵn trên sàn ngay sau `execute`/lần đồng bộ đầu tiên. Vì vậy VPS mất kết nối, khởi động lại hay trễ mạng **không làm mất bảo vệ**; tốc độ/độ trễ không phải yếu tố lợi nhuận của chiến lược này (thang cách 1.5%, TP ≥ 1.2%). SL **tuyệt đối không** được mô phỏng phía client (không có "stop mềm" do VPS theo dõi giá rồi bắn lệnh market).

Hệ quả khi VPS ngừng (phải ghi trong README):

| Việc phụ thuộc VPS | Hậu quả nếu VPS chết | Giới hạn rủi ro |
|---|---|---|
| Đặt lại TP theo giá TB mới sau khi lớp mới khớp | TP cũ vẫn treo (giá/size theo giá TB cũ) → chốt chưa tối ưu, một phần vị thế không có TP | SL trên sàn vẫn giới hạn lỗ ≤ ngân sách `s×E` |
| Đặt SL lần đầu sau fill lớp 1 (nếu preset SL không dùng được, 7.6(4)) | Vị thế **không có SL** trong thời gian VPS chết | ⇒ PHẢI dùng `presetStopLossPrice` trên lệnh entry nếu Demo xác nhận hoạt động cấp vị thế; nếu không, đây là rủi ro mở (Q11) |
| Huỷ DCA còn lại sau TP1, dời SL về hoà vốn | DCA có thể khớp lại sau TP1; SL vẫn ở mức gốc | Lỗ vẫn ≤ ngân sách vì SL tính cho thang đầy |
| `lazy_layers` (4.7) | Lớp sâu không được đặt | Không tăng rủi ro (chỉ bỏ lỡ lớp); nhưng vi phạm nguyên tắc → chỉ bật nếu Demo bắt buộc |

**Kiến trúc dữ liệu:**

- **WebSocket v2 cho trạng thái thời gian thực:**
  - Public `wss://ws.bitget.com/v2/ws/public`: `ticker` (`instType=USDT-FUTURES`, `instId=BTCUSDT|ETHUSDT`) – giá last/bid/ask/mark cho kiểm tra lệch giá, R23, hiển thị. (Kênh nến `candle15m`… CÓ THỂ dùng nhưng không bắt buộc – xem TA bên dưới.)
  - Private `wss://ws.bitget.com/v2/ws/private` (sau `login`): `orders` (`instId=default`), `positions` (`instId=default`), `account` (`coin=default`), và kênh lệnh trigger/TP-SL `orders-algo` **[CHƯA XÁC MINH tên kênh plan/TP-SL trong v2 Classic]**.
  - Login: `{"op":"login","args":[{"apiKey":…,"passphrase":…,"timestamp":"<giây>","sign":Base64(HMAC_SHA256(secret, timestamp+"GET"+"/user/verify"))}]}` – timestamp WS tính bằng **giây** (theo tài liệu/ví dụ cộng đồng; **[kiểm Demo]**). Demo: `wss://wspap.bitget.com/v2/ws/public|private` **[CHƯA XÁC MINH trên tài liệu chính thức]**.
  - Dùng key **chỉ-đọc** cho kết nối private WS nếu sàn cho phép nhận kênh orders/positions bằng key read-only (giảm phơi nhiễm key trade) **[kiểm Demo]**; nếu không được thì dùng key trade.
- **REST chỉ cho**: đặt/sửa/huỷ lệnh; **đối soát định kỳ** (mỗi 60 s, và ngay sau mỗi lệnh ghi quan trọng); dữ liệu không có trên WS (contracts, MMR tiers, funding history, OI, long/short, nến cho TA).
- **TA**: dùng nến ≥ 15m, **poll REST ~1 lần/phút** (chỉ tải nến mới, cache đĩa); không cần WS cho TA.

**Heartbeat, reconnect, reconcile:**

1. Gửi chuỗi `"ping"` mỗi **25–30 s**, mong đợi `"pong"`; không nhận `pong` trong 10 s hoặc không có message nào trong 60 s → coi là chết, đóng & kết nối lại. (Sàn tự ngắt nếu không nhận ping trong 2 phút.)
2. Reconnect với **exponential backoff + jitter**: 1, 2, 4, 8, 16, 30 s (trần 30 s), reset sau khi ổn định 5 phút. Tôn trọng giới hạn sàn: ≤ 300 lần kết nối/IP/5 phút, ≤ 100 kết nối/IP, ≤ 10 message/s/kết nối, ≤ 240 lệnh subscribe/giờ/kết nối; nên < 50 kênh/kết nối (công cụ dùng ~2 kết nối, < 10 kênh).
3. **Trên MỌI lần (re)connect – trước bất kỳ hành động ghi nào**: (a) login + subscribe lại; (b) đặt cờ `RECONCILING` (chặn execute/sync ghi); (c) REST full snapshot: `all-position`, `orders-pending` (đủ trang), `orders-plan-pending` (profit_loss + normal_plan), `account`, fills kể từ `last_fill_ts` trong DB; (d) đối soát với DB theo `clientOid` (mục 8.2 bước 2–6): áp các fill bị lỡ, cập nhật trạng thái leg, **đặt lại TP/SL thiếu**, huỷ lệnh công cụ mồ côi của leg đã đóng; (e) bỏ cờ. Mọi lệnh gửi lại dùng clientOid xác định trước → **không tạo lệnh trùng** (nếu clientOid đã tồn tại trên sàn → coi là đã đặt).
4. Dữ liệu WS chỉ là *gợi ý thay đổi*; quyết định quan trọng (đặt lại TP, dời SL, đóng leg) dựa trên trạng thái sau khi đã đối chiếu (WS event + REST xác nhận nếu nghi ngờ, vd thứ tự message lộn xộn, `seq` nhảy).
5. WS mất > **N = 60 s** (cấu hình 30–300): chuyển sang chế độ **REST polling** (mỗi 10 s, trong ngân sách rate limit) + báo động; WS phục hồi → reconcile đầy đủ rồi quay lại chế độ WS.

**Rate limit**: ngân sách chung trong client (mục 7.2, 50% giới hạn tài liệu); đối soát 60 s ≈ 5–6 request; không bao giờ polling dày hơn 1 vòng/5 s kể cả khi mất WS.

**Hết hạn plan**: giữ **10 phút / lệch 0.3%** (mục 2.3) – bước chậm nhất là con người xác nhận, không phải mạng; độ trễ VPS không đổi ngưỡng này.

**Chọn VPS:**

- Khuyến nghị VPS khu vực châu Á (Tokyo / Singapore / Hong Kong). **Vị trí máy chủ của Bitget chưa được xác minh** (api.bitget.com chạy sau CDN) → trước khi thuê dài hạn, đo trên 2–3 VPS ứng viên: RTT trung vị & p95 của 200 lần `GET /api/v2/public/time` và `GET …/market/ticker`, thời gian bắt tay TLS, độ ổn định WS (số lần rớt / 24 h). Chọn p95 thấp và ổn định nhất; ghi kết quả vào `docs/vps_latency.md`.
- Cấu hình tối thiểu: 1 vCPU, 1–2 GB RAM, SSD, **IP tĩnh** (cho whitelist API key), đồng bộ giờ NTP (chrony), Linux LTS, tường lửa chỉ mở SSH bằng key (không mật khẩu), tự cập nhật bảo mật.
- Chạy dưới systemd: service `dca-sync` (watcher, `Restart=always`), timer backup DB hằng ngày (giữ 30 bản, mã hoá nếu đưa ra ngoài VPS). Secrets trong file env quyền 600 do systemd nạp.
- Trợ lý (chat) gọi CLI trên VPS qua kênh do chủ chọn (SSH cố định lệnh / API nội bộ chỉ nghe localhost + tunnel) – không mở cổng công khai (Q12).

**Giám sát & cảnh báo chính công cụ:**

| Chỉ số | Ngưỡng cảnh báo | Mức |
|---|---|---|
| Heartbeat watcher (`state/heartbeat` cập nhật mỗi vòng) | > 60 s không cập nhật | CAO |
| WS public/private mất kết nối | > N s (mặc định 60 s) | CAO |
| Reconcile thất bại / lệch trạng thái (`DRIFT`, `ORPHAN`) | bất kỳ | CAO |
| Leg có vị thế nhưng không có SL trên sàn | bất kỳ, > 1 vòng | KHẨN |
| Lỗi REST liên tiếp / 429 | ≥ 5 liên tiếp | TRUNG |
| Lệch đồng hồ so với server | > 2 s | TRUNG |
| Đĩa trống / RAM | < 15% | TRUNG |
| Kill switch được kích hoạt, SL khớp, DD breaker | sự kiện | THÔNG TIN/CAO |
- `health` endpoint/lệnh `status --health` trả JSON (`ws_public`, `ws_private`, `last_reconcile_ts`, `heartbeat_age_s`, `legs_without_sl`, `mode=ws|polling`).
- **Giám sát từ bên ngoài** (dead-man switch): watcher ping một dịch vụ kiểm tra định kỳ (vd healthchecks-style URL) mỗi phút; không ping 3 phút → dịch vụ ngoài báo cho chủ (vì VPS chết thì không tự báo được). Kênh nhận cảnh báo: Q6.


---

## 9. Bảo mật

1. **Hai API key riêng**:
   - Key **chỉ-đọc** (đang có): dùng cho `status`, `ta`, giám sát. Biến môi trường `BITGET_RO_API_KEY/SECRET/PASSPHRASE`.
   - Key **giao dịch**: quyền **Futures Trade** (Orders + Positions) **chỉ**; **Withdraw OFF, Transfer OFF**, không quyền spot/margin/copy; **bắt buộc IP whitelist** (IP máy chạy công cụ). Biến `BITGET_TRADE_API_KEY/SECRET/PASSPHRASE`.
   - Key **Demo** riêng: `BITGET_DEMO_API_KEY/...`.
2. Secrets chỉ ở biến môi trường hoặc file `.env` quyền `600` ngoài repo; `.env` trong `.gitignore`; không commit, không in ra màn hình, không đưa vào log/exception/traceback (bọc trong kiểu `Secret` có `__repr__` ẩn).
3. Gửi lệnh live cần đồng thời: `env=live`, `LIVE_TRADING_ENABLED=1`, key trade có mặt, `--confirm` (execute). Thiếu bất kỳ → chặn.
4. Giới hạn cứng trong mã (Phụ lục A) – cấu hình không thể vượt; thay đổi giới hạn cứng = thay đổi mã + review.
5. Kill switch: `kill` + file cờ `state/KILL` (watcher thấy file → huỷ lệnh công cụ, không mở/đặt entry mới, vẫn giữ SL). Xoá file + `selftest` mới chạy lại.
6. `selftest` kiểm tra quyền key: gọi endpoint chỉ-đọc bằng key trade OK; **không** có cách kiểm tra quyền rút qua API an toàn → chủ phải xác nhận thủ công trên web và ghi vào checklist go-live.
7. Phụ thuộc: khoá phiên bản (lock file), không dùng thư viện SDK không rõ nguồn; ưu tiên tự viết client REST nhỏ (đã có mẫu `trader/bgapi.py`).
8. Chạy trên Demo trước, rồi live với size tối thiểu (mục 10.4).
9. Không mở cổng mạng vào máy chạy công cụ; trợ lý gọi CLI cục bộ.

---

## 10. Kiểm thử & tiêu chí nghiệm thu

### 10.1 Unit test (bắt buộc, chạy trong CI, không cần mạng)

| ID | Nội dung |
|---|---|
| U1 | Tái tạo ví dụ 4.10 (ETH long/short safe) chính xác: giá lớp, size, giá TB, TP1/TP2, SL (2174.58 / 2634.72), lỗ thực tế tại SL |
| U2 | Tái tạo bảng `PLAN.md` mục 4 (DEFAULT, MMR 0.5%) với `ladder.py` làm oracle: sai số ≤ 1 tick |
| U3 | Tái tạo ví dụ Scalp 4.12.4 (7 lớp, cắt lớp 8, SL 2364.92) |
| U4 | Làm tròn: bảng 4.9 cho cả long/short, BTC (tick 0.1, lot 0.0001) và ETH (tick 0.01, lot 0.01); không bao giờ xuất số dạng khoa học |
| U5 | Size < minTradeNum hoặc < 5 USDT → FAIL có thông báo |
| U6 | Công thức SL 4.6: thuộc tính "lỗ tại SL (gồm phí) ≤ s·E" với 10.000 bộ ngẫu nhiên (property-based) |
| U7 | Ước tính liq 4.8(a) khớp `ladder.py`; 4.8(b) bisection hội tụ, đơn điệu theo notional |
| U8 | Mỗi kiểm tra R1–R25 (và biến thể Scalp) có test PASS và FAIL |
| U9 | Giới hạn cứng: cấu hình vượt (vd cap 30x, stop 20%, first_x 10x, mult 1.2) → lỗi khởi động |
| U10 | Bảng hedge-mode 7.3: map (hành động → side/tradeSide), không bao giờ gửi `reduceOnly` |
| U11 | Ký request: vector test cố định (timestamp, method, path, query, body → sign) cho GET có query, POST có body; WS login sign |
| U12 | clientOid: định dạng, độ dài, xác định (cùng đầu vào → cùng chuỗi), rev tăng |
| U13 | Máy trạng thái 8.2: mọi chuyển trạng thái hợp lệ; chuyển không hợp lệ bị từ chối; replay chuỗi sự kiện (fill 1, fill 2, TP1, BE) cho kết quả đúng |
| U14 | Reconcile: các kịch bản lệch (thiếu SL, thiếu TP, lệnh mồ côi, fill bị lỡ khi mất WS, partial fill) → hành động đúng, không tạo lệnh trùng |
| U15 | Plan hết hạn theo thời gian và theo lệch giá; execute 2 lần idempotent |
| U16 | Log: quét toàn bộ log sau bộ test – không chứa secret/passphrase/sign |
| U17 | TA: chỉ báo khớp giá trị tham chiếu (vd TA-Lib hoặc tính tay) trên bộ nến cố định; không lookahead (thêm nến tương lai không đổi kết quả quá khứ) |
| U18 | `levels` snap: tôn trọng min_gap 1%, độ sâu tối đa, fallback; không vượt cap sau snap |
| U19 | Khoá ngày Scalp, chuỗi stop, DD breaker kích hoạt đúng ngưỡng và đúng múi giờ UTC+7 |

### 10.2 Dry-run (trên dữ liệu live, không đặt lệnh)

- Chạy ≥ 3 ngày liên tục trên VPS: preview/execute/sync ở dry-run, watcher mô phỏng khớp theo nến 1m. Tiêu chí: không crash, không rò rỉ bộ nhớ, reconcile không báo lệch giả, log đầy đủ, mọi body POST được ký hợp lệ (kiểm bằng vector).

### 10.3 Demo (Bitget Demo, `paptrading: 1`) – bắt buộc qua hết trước live

| ID | Kịch bản | Kỳ vọng |
|---|---|---|
| D1 | `selftest` | posMode/marginMode đúng, đồng hồ OK, quyền key OK |
| D2 | Execute thang Wide ETH long safe | 5 entry post-only + SL; clientOid đúng |
| D3 | Lệnh post-only cắt giá | Ghi nhận hành vi (lỗi đồng bộ hay canceled) & xử lý đúng |
| D4 | Lớp sâu > 5% | Ghi nhận có bị giới hạn giá (22046…) → quyết định `lazy_layers` |
| D5 | Fill lớp 1 → TP1/TP2 xuất hiện ≤ 2 s (WS) | Đúng giá/size |
| D6 | Fill lớp 2 → TP đặt lại theo giá TB mới | rev tăng, lệnh cũ bị huỷ |
| D7 | `presetStopLossPrice` | Xác định cấp vị thế hay cấp lệnh, có bị ghi đè khi lớp sau khớp |
| D8 | `pos_loss` áp cho phần vị thế mới khớp | Có |
| D9 | **SL kích hoạt khi TP1+TP2 limit close chiếm 100% vị thế** | Vị thế đóng hết. Nếu không → áp phương án 7.6(1) và lặp lại test |
| D10 | TP1 khớp → huỷ DCA, SL→BE | Đúng |
| D11 | `cancel`, `kill` | Chỉ lệnh tiền tố công cụ bị huỷ; lệnh tay (đặt thủ công trên web) còn nguyên |
| D12 | `kill --close-positions --confirm-close` | Chỉ đóng (symbol, holdSide) của công cụ |
| D13 | Ngắt mạng VPS 5 phút trong khi có fill | Sau reconnect: reconcile, áp fill bị lỡ, đặt lại TP thiếu, không lệnh trùng |
| D14 | Kill tiến trình giữa batch-place-order | Khởi động lại không đặt trùng (clientOid) |
| D15 | Scalp mode: thang 7 lớp, cắt theo cap; huỷ lớp khi liq < 3%; khoá ngày | Đúng 4.12 |
| D16 | Rate limit: chạy 24 h | Không có lỗi 429 |
| D17 | WS mất > 60 s | Cảnh báo + chuyển REST polling + dead-man ping hoạt động |
Thời gian Demo tối thiểu: 2 tuần với watcher chạy liên tục, ≥ 20 thang Wide đóng, ≥ 10 thang Scalp.

### 10.4 Live cỡ nhỏ

- Tuần 1: Wide mode, 1 thang, size tối thiểu sàn (ETH 0.01/lớp hoặc BTC 0.0001–0.0002/lớp), `variant=safe`.
- Tuần 2–4: Wide `safe` đầy đủ 4 thang. Scalp mode chỉ bật sau tuần 2, `first_x` ≤ 2x, cap ≤ 10x.
- Nâng lên `default` chỉ khi: 4 tuần live không có sự cố nghiêm trọng (SL thiếu, lệnh trùng, lệch trạng thái chưa giải thích) và kết quả không tệ hơn khoảng backtest an toàn quá 2 độ lệch chuẩn tuần.

### 10.5 Yêu cầu backtest

- B1: Engine backtest được đối chiếu với `planner/results/final_eval.csv` (SAFE/DEFAULT/AGGR, 3 giai đoạn) sai số ≤ 1 điểm %.
- B2: Logic thang trong công cụ (ladder/risk) phải là **cùng mã** được gọi bởi backtest (không viết lại hai lần).
- B3: Cổng TA/`levels` (6.8) và tin tức (6.9) trước khi được chặn/snap.
- B4: Scalp mode: chạy lại `run_user_style.py`-tương đương với giới hạn 4.12 (first 3x, cap 15x, SL −15%, khoá ngày) để báo cáo cho chủ – **chỉ để hiểu rủi ro**, không phải tiêu chí bật (Scalp không bao giờ tự động).
- B5: Kiểm định giả định thực thi: tỷ lệ khớp post-only và trượt giá SL đo từ Demo/live được đưa ngược vào backtest.

### 10.6 Tiêu chí nghiệm thu tổng

1. Toàn bộ U1–U19 xanh; độ phủ test của `ladder/`, `risk/`, `executor/`, `sync/` ≥ 90% dòng.
2. D1–D17 đạt, có log/ảnh chụp minh chứng trong `docs/demo_report.md`.
3. Checklist mục 13 không còn mục "FAIL".
4. README tiếng Việt: cài đặt VPS, tạo key, cấu hình, các lệnh, kỳ vọng thực tế (1.3), cảnh báo Scalp (4.12).

---

## 11. Lộ trình

| Pha | Nội dung | Cổng ra |
|---|---|---|
| **P0 – Nền tảng** (≈1 tuần) | Client REST ký + rate limit + log; models; contracts/MMR; `status`, `selftest`; dry-run | U4, U10–U12, U16 |
| **P1 – MVP Wide-ladder** (≈2 tuần) | preview/execute/cancel/kill; risk checks; SQLite; watcher WS + reconcile; VPS + giám sát | U1–U2, U5–U9, U13–U15; D1–D14, D16–D17 |
| **P1b – Scalp mode** (≈1 tuần) | 4.12 + nhật ký so sánh | U3, U19, D15 |
| **P2 – TA** (≈2 tuần) | Module TA, `ta` CLI, cờ rủi ro hiển thị trong preview; `levels`; backtest cổng 6.8 | U17–U18; báo cáo `ta_gate_report.md`; chỉ bật chặn nếu đạt |
| **P3 – Tin tức** (≈1–2 tuần) | Lịch kinh tế, tin lớn, sentiment X → cờ bổ sung | Quan sát forward ≥ 4 tuần |
| **P4 – Tuỳ chọn: tự động mở lại thang Wide** | Khi một thang Wide đóng → tự mở thang mới cùng chiều nếu mọi kiểm tra PASS và cờ ≠ AVOID; vẫn có kill switch, giới hạn cứng, thông báo | ≥ 8 tuần live bán tự động ổn định + chủ phê duyệt bằng văn bản. **Không áp dụng cho Scalp mode** |

---

## 12. Câu hỏi mở cho chủ sở hữu

| # | Câu hỏi | Mặc định nếu chưa trả lời |
|---|---|---|
| Q1 | Bắt đầu live với `safe` (3x, stop 5%) như khuyến nghị? | Có |
| Q2 | Khi một thang Wide đóng: chỉ thông báo, hay tự đề xuất preview mới ngay? | Chỉ thông báo + gợi ý |
| Q3 | Phương án `aggressive` (cap 8x, mỗi thang 2x) mâu thuẫn với cap cùng chiều 2.5x (2 thang cùng chiều = 4x). Giữ 2.5x (cứng) và chấp nhận thang bị thu nhỏ? | Giữ 2.5x |
| Q4 | Khi không đặt/không xác nhận được SL sau 60 s: đóng leg bằng market (`close_leg`) hay chỉ báo động? | `close_leg` |
| Q5 | Có cho phép công cụ đổi leverage symbol (10x Wide / 25–50x Scalp)? Leverage cross là theo symbol → nếu ETH-long Scalp cần 30x thì ETH-short Wide cũng ở 30x (không đổi rủi ro thật, chỉ ký quỹ) | Cho phép, chỉ khi không có vị thế trên symbol |
| Q6 | Kênh nhận cảnh báo/báo cáo (Telegram, email, chat với trợ lý)? | Chat trợ lý + email |
| Q7 | Ngưỡng DD breaker 20% và lỗ ngày 10% (Wide) có phù hợp? | Có |
| Q8 | Tài khoản sẽ giữ **Classic** (API v2)? Nếu nâng lên Unified Trading Account, API v2 mix có thể không dùng được (mã 40084) → cần làm lại tầng API v3 | Giữ Classic |
| Q9 | Chấp nhận có VPS trả phí (ước tính 5–12 USD/tháng) và dịch vụ dead-man ping ngoài? | Có |
| Q10 | Vị thế/lệnh tay trên cùng (symbol, chiều) với công cụ: chặn hoàn toàn (mặc định) hay cho phép "nhận nuôi" (adopt) vào thang? | Chặn |
| Q11 | Nếu Demo cho thấy SL chỉ đặt được sau fill (không preset được): chấp nhận rủi ro "khoảng hở SL" khi VPS chết đúng lúc lớp 1 khớp, hay chỉ đặt lớp 1 khi watcher khoẻ & dùng lệnh lớp 1 có TP/SL preset bằng cách khác? | Chỉ execute khi watcher khoẻ (R25) + báo động KHẨN |
| Q12 | Trợ lý gọi CLI trên VPS bằng cách nào (SSH lệnh cố định / API nội bộ qua tunnel)? Ai giữ khoá SSH? | SSH key riêng, lệnh giới hạn |
| Q13 | Scalp mode: các mặc định 4.12.2 (first 3x, cap 15x, SL −15%, khoá ngày 10%) – chủ muốn chặt hơn? | Như bảng |
| Q14 | Nguồn lịch kinh tế/tin tức/X cho P3 (có trả phí không)? | Chưa chọn |
| Q15 | Funding: có muốn tránh giữ thang qua mốc funding khi phe mình trả funding cực trị? | Chỉ cảnh báo |

---

## 13. Checklist review code (trợ lý sẽ dùng khi review mã của developer)
**An toàn tiền & giới hạn**

- [ ] Giới hạn cứng (Phụ lục A) là hằng số trong mã; có test cấu hình vượt → lỗi; không có đường nào bỏ qua (kể cả cờ debug).
- [ ] Không có lệnh *mở* vị thế nào ngoài `execute`/`scalp execute` của plan đã xác nhận (và lớp trễ thuộc plan đó). Tìm mọi lời gọi `place-order`/`batch-place-order` với `tradeSide=open`.
- [ ] Mọi leg có vị thế đều có SL phía sàn (`pos_loss`, mark price); không có SL mô phỏng phía client; SL không bao giờ bị dời xa.
- [ ] Exposure tính cả vị thế tay, lệnh tay đang treo, và mọi lớp chưa khớp (worst-case).
- [ ] `cancel-all-orders` không được dùng; `cancel-plan-order` luôn có `orderIdList`; `close-positions` luôn có `holdSide`.
- [ ] Live cần đủ: env live + `LIVE_TRADING_ENABLED=1` + key trade + `--confirm`.

**Tính toán**

- [ ] Giá/size dùng Decimal/số nguyên tick; làm tròn đúng bảng 4.9; format chuỗi đúng số thập phân.
- [ ] SL dùng Q thiết kế (4.6); lỗ thực tế ≤ ngân sách; công thức có phí.
- [ ] Giá TB lấy từ sàn (`openPriceAvg`/fills), không từ giá dự kiến.
- [ ] Thông số contract & MMR lấy từ API lúc chạy, có cache có hạn; MMR dùng max(API, cấu hình).

**API & đồng bộ**

- [ ] Hedge mode: đóng long = `buy`+`close`, đóng short = `sell`+`close`; không gửi `reduceOnly`.
- [ ] Ký: chuỗi body ký == chuỗi body gửi; query string ký == query gửi; timestamp ms (REST) / giây (WS login).
- [ ] clientOid xác định, lưu DB trước khi gửi; timeout → truy vấn theo clientOid trước khi gửi lại.
- [ ] Batch: xử lý `failureList` từng phần tử.
- [ ] WS: ping 25–30 s, phát hiện mất pong, backoff có trần, reconcile đầy đủ trước khi ghi sau mỗi (re)connect; chế độ REST polling khi mất WS.
- [ ] Rate limiter theo endpoint; xử lý 429; không vòng lặp gọi API không giới hạn.
- [ ] Demo header `paptrading: 1` chỉ khi env=demo; không bao giờ trộn key demo/live.

**Trạng thái & lỗi**

- [ ] Máy trạng thái rõ ràng; chuyển không hợp lệ bị từ chối; khởi động lại tái dựng từ DB + sàn.
- [ ] Mọi exception trong watcher được bắt ở mức vòng; không để watcher chết im lặng; heartbeat + dead-man ping.
- [ ] File lock một watcher; giao dịch DB nguyên tử khi đổi trạng thái + ghi lệnh.
- [ ] Partial fill được xử lý (entry & TP).

**Bảo mật & log**

- [ ] Không log header/secret/sign; test quét log; `Secret.__repr__` ẩn; `.env` trong `.gitignore`.
- [ ] Key trade không có quyền rút/chuyển (xác nhận thủ công của chủ ghi trong `docs/golive.md`); IP whitelist.
- [ ] Log JSONL có `client_oid`, `plan_id`, latency, mã lỗi; thời gian hiển thị UTC+7.

**TA & Scalp**

- [ ] TA chỉ dùng nến đã đóng; không lookahead; nhãn "bộ lọc rủi ro, không phải dự báo" có trong mọi đầu ra.
- [ ] Chặn/snap theo TA chỉ bật khi có `ta_gate_report.md` đạt; mặc định chỉ hiển thị.
- [ ] Scalp: cap 15x/20x, cùng chiều, liq ≥ 3% mỗi lớp, SL −15% bắt buộc, khoá ngày, cảnh báo backtest hiển thị, `scalp_journal` đầy đủ.

**Kiểm thử**

- [ ] U1–U19 tồn tại và chạy được offline; báo cáo Demo D1–D17 có minh chứng.

---

## Phụ lục A – Tham số cấu hình & giới hạn cứng

### A.1 Giới hạn cứng (hằng số trong mã – cấu hình chỉ được ≤)

| Hằng số | Giá trị | Áp dụng |
|---|---|---|
| `HARD_SYMBOLS` | {BTCUSDT, ETHUSDT} | cả hai |
| `HARD_WIDE_TOTAL_X` | 8.0 | Wide |
| `HARD_WIDE_LEG_X` | 2.0 | Wide |
| `HARD_WIDE_SAMEDIR_X` | 2.5 | Wide |
| `HARD_WIDE_MAX_LAYERS` | 5 | Wide |
| `HARD_WIDE_MIN_SPACING` | 1.0% | Wide (cả `levels`) |
| `HARD_WIDE_STOP_PCT_MAX` | 7% E/thang | Wide |
| `HARD_WIDE_LEVERAGE_MAX` | 20x | Wide |
| `HARD_SCALP_TOTAL_X` | 20.0 | Scalp |
| `HARD_SCALP_SAMEDIR_X` | 15.0 | Scalp |
| `HARD_SCALP_FIRST_X` | 5.0 | Scalp |
| `HARD_SCALP_MULT_MAX` | 1.0 | Scalp |
| `HARD_SCALP_MIN_SPACING` | 0.15% | Scalp |
| `HARD_SCALP_MAX_LAYERS` | 12 | Scalp |
| `HARD_SCALP_MIN_LIQ_DIST` | 3% | Scalp |
| `HARD_SCALP_STOP_PCT_MAX` | 15% E (bắt buộc có) | Scalp |
| `HARD_SCALP_DAILY_LOSS_MAX` | 15% E | Scalp |
| `HARD_SCALP_LEVERAGE_MAX` | 50x | Scalp |
| `HARD_TOTAL_SL_BUDGET` | 25% E (Wide) / 30% E (khi có Scalp) | cả hai |
| `HARD_PLAN_TTL` | 10 phút / 0.3% | cả hai |
| `HARD_CLIENT_OID_PREFIX` | `gdl1-`, `gsc1-` | cả hai |

### A.2 Cấu hình mặc định (`config.yaml`, ví dụ)
```yaml
env: demo                # demo | live
dry_run: true
variant: safe            # safe | default | aggressive
wide:
  layers: 5
  spacing_pct: 1.5
  spacing_mode: fixed    # fixed | levels (levels chỉ khi qua cổng 6.8)
  tp1_pct: 1.2
  tp1_fraction: 0.5
  tp2_pct: 2.4
  be_buffer_pct: 0.05
  leverage: 10
  lazy_layers: false
  lazy_window_pct: 4.0
risk:
  daily_loss_pct: 10
  dd_breaker_pct: 20
  max_stops_24h: 2
  on_sl_failure: close_leg
  mmr_floor: {BTCUSDT: 0.004, ETHUSDT: 0.005}
scalp:
  enabled: false
  first_x: 3.0
  spacing_pct: 0.20
  mult: 0.87
  tp_a_pct: 0.15
  tp_a_fraction: 0.5
  tp_b_pct: 0.20
  total_cap_x: 15
  samedir_cap_x: 10
  min_liq_dist_pct: 3
  emergency_sl_pct: 15
  daily_loss_pct: 10
  leverage: 30
  plan_ttl_s: 120
  plan_drift_pct: 0.10
sync:
  reconcile_interval_s: 60
  ws_ping_s: 25
  ws_dead_alert_s: 60
  rest_fallback_poll_s: 10
ta:
  enabled_display: true
  enabled_block: false   # chỉ true khi ta_gate_report đạt
  poll_s: 60
fees: {maker: 0.0002, taker: 0.0006}
```

---

## Phụ lục B – Nguồn tài liệu API & điểm chưa xác minh

### B.1 Tài liệu đã đọc (truy cập 2026-10-20)

| Chủ đề | URL |
|---|---|
| Place order, batch, modify, cancel, batch cancel, cancel all, close positions, order detail, fills, pending, history (Classic contract trade) | https://www.bitget.com/api-doc/contract/trade/Place-Order · https://www.bitget.com/docs/catalog/classic-contract-trade/classic-contract-trade |
| Trigger orders: place-plan-order, place-tpsl-order (`pos_loss`…), place-pos-tpsl, modify-tpsl-order, cancel-plan-order, orders-plan-pending | https://www.bitget.com/docs/catalog/classic-contract-plan/classic-contract-plan · https://www.bitget.com/zh-CN/api-doc/classic/contract/plan/Place-Tpsl-Order · https://www.bitget.com/api-doc/contract/plan/Place-Tpsl-Order |
| Market: contracts (sizeMultiplier, pricePlace, priceEndStep, minTradeNum, minTradeUSDT…), candles/history-candles, ticker, funding, open-interest | https://www.bitget.com/docs/catalog/classic-contract-market/classic-contract-market |
| Position: query-position-lever (MMR tiers), all-position, single-position | https://www.bitget.com/docs/catalog/classic-contract-position/classic-contract-position |
| Account: account, accounts, liq-price, max-open, set-leverage | https://www.bitget.com/docs/catalog/classic-contract-account/classic-contract-account |
| Long/short ratio | https://www.bitget.com/api-doc/classic/common/apidata/Long-Short · https://www.bitget.com/zh-CN/api-doc/common/apidata/Account-Long-Short · https://www.bitget.com/zh-CN/api-doc/classic/common/apidata/Position-Long-Short |
| Ký request (HMAC SHA256 + Base64), header | https://www.bitget.com/api-doc/classic/quickStart/intro · https://www.bitget.com/zh-CN/api-doc/common/signature · https://www.bitget.com/docs/uta/rest-api |
| Timestamp ±30 s | https://www.bitget.com/zh-CN/api-doc/common/signature-samaple/interaction |
| Demo trading (`paptrading: 1`, Demo API key) | https://www.bitget.com/api-doc/common/demotrading/restapi · https://www.bitget.com/api-doc/classic/demotrading/restapi · https://www.bitget.com/docs/classic/demo-trading/rest-api |
| WebSocket (domain, ping/pong 30 s, giới hạn kết nối/subscribe/message) | https://www.bitget.com/api-doc/classic/quickStart/websocket-intro |
| Mã lỗi (bảng UTA/WebSocket – dùng tham khảo) | https://www.bitget.com/docs/uta/error-code/websocket |
| Unified Trading Account (khác Classic) | https://www.bitget.com/api-doc/contract/plan/Place-Pos-Tpsl-Order (trang hiển thị giới thiệu UTA) |
| Tham khảo cộng đồng (không chính thức) | https://github.com/ccxt/ccxt/issues/25523 (demo WS `wspap`), https://github.com/ccxt/ccxt/issues/25524 (WS login/subscribe mẫu), https://github.com/tiagosiebler/bitget-api (danh sách endpoint), https://github.com/ccxt/ccxt/issues/18733 (lỗi 45110) |
Dữ liệu live đã gọi thử (public, 2026-10-20): `contracts` BTC/ETH, `query-position-lever`, `ticker` ETH, `public/time`.

### B.2 Đã xác minh từ tài liệu chính thức

- Trường place-order: `symbol, productType=USDT-FUTURES, marginMode=crossed, marginCoin=USDT, size, price, side, tradeSide, orderType, force (gtc/ioc/fok/post_only), clientOid, reduceOnly (chỉ one-way), presetStopSurplusPrice, presetStopLossPrice, stpMode`.
- Hedge mode: mở/đóng long = `buy` + `open/close`; mở/đóng short = `sell` + `open/close`; `tradeSide` bắt buộc ở hedge mode.
- Hành vi lệnh close limit "chiếm" vị thế trong hedge mode (ví dụ 100/70/50 → đóng 30).
- `place-tpsl-order`: `planType` (profit_plan, loss_plan, moving_plan, pos_profit, pos_loss), `triggerPrice`, `triggerType` (fill_price/mark_price), `executePrice` (0 = market), `holdSide`, `size` (không cần với pos_*), `clientOid`.
- `cancel-plan-order` không có `orderIdList` → huỷ mọi lệnh plan của symbol/productType.
- Rate limit: place-order 10/s/UID; batch-place 5/s/UID (≤ 50 lệnh); modify/cancel/batch-cancel/cancel-all 10/s; close-positions 1/s; all-position 5/s; single-position, account, orders-pending, plan-pending, tpsl 10/s/UID; set-leverage 5/s; liq-price 20/s/UID; contracts/candles/ticker/funding/OI 20/s/IP; query-position-lever 10/s/IP; long-short 1/s/IP.
- Contracts: `sizeMultiplier`, `minTradeNum`, `pricePlace`, `priceEndStep`, `volumePlace`, `minTradeUSDT`, `symbolStatus`, `maxSymbolOrderNum`…
- Ký: `timestamp + METHOD + path + ?query + body`, HMAC-SHA256, Base64; header `ACCESS-*`; timestamp ms trong 30 s.
- Demo: Demo API key + header `paptrading: 1`; `fill-history` không hỗ trợ demo.
- WebSocket: `wss://ws.bitget.com/v2/ws/public|private`; ping chuỗi 30 s; server ngắt sau 2 phút không ping; ≤ 10 message/s; 300 kết nối/IP/5 phút; 240 subscribe/giờ/kết nối.

### B.3 CHƯA XÁC MINH (developer PHẢI kiểm Demo – liên kết test 10.3)

1. **SL `pos_loss` có đóng đủ vị thế khi TP limit close đã chiếm 100% vị thế** (D9) – rủi ro nghiêm trọng nhất.
2. `pos_loss` có đặt được khi chưa có vị thế không; có tự áp cho khối lượng khớp thêm (D8).
3. `presetStopLossPrice` trong hedge+cross là cấp vị thế hay cấp lệnh; bị ghi đè thế nào khi nhiều lệnh entry có preset (D7).
4. Hành vi post-only khi cắt giá: lỗi đồng bộ hay nhận rồi huỷ; mã lỗi (D3).
5. Giới hạn giá lệnh `buyLimitPriceRatio/sellLimitPriceRatio` (0.05) với lớp sâu > 5% (D4).
6. Độ dài tối đa/ký tự cho phép/tính duy nhất của `clientOid`, mã lỗi khi trùng.
7. Đổi leverage khi đang có vị thế/lệnh treo ở cross.
8. Có được giữ 2 lệnh `pos_loss` cùng lúc (để "đặt mới trước, huỷ cũ sau") hay sàn thay thế.
9. Demo: dùng `productType=USDT-FUTURES` + header, hay `SUSDT-FUTURES`/symbol `S…`; URL WS demo `wspap.bitget.com`.
10. Tên kênh WS cho lệnh trigger/TP-SL (`orders-algo`?) và cấu trúc message; WS login timestamp tính bằng giây; key read-only có subscribe được kênh private không.
11. Bảng mã lỗi REST Classic (đang dùng bảng UTA/WS + cộng đồng).
12. Vị trí máy chủ Bitget (để chọn VPS) – chỉ xác định bằng đo độ trễ.
13. Ngữ nghĩa chính xác của `buyLimitPriceRatio`.

---

## Phụ lục C – Tóm tắt kết quả backtest làm cơ sở
Nguồn: `planner/results/final_eval.csv` (180 ngày 2026-04-22 → 10-20, nến 1m, 1 tài khoản cross BTC+ETH, phí + funding thật, vốn 524.87).

| Phương án | Kỳ | Lợi nhuận | Max DD | Stop | Phí/lãi gộp | USDT/ngày | Ngày tệ nhất | % ngày ≥ 700k VND |
|---|---|---|---|---|---|---|---|---|
| SAFE 3x, stop −5% | 180d | +22.9% | 19.0% | 23 | 24.9% | 0.67 | −37.1 | 0.0% |
| SAFE | A_bear | −1.4% | 19.0% | 15 | 73.5% | −0.08 | −30.9 | 0.0% |
| SAFE | B_bull | +20.8% | 17.8% | 8 | 14.8% | 1.21 | −36.1 | 0.0% |
| DEFAULT 5x, stop −7% | 180d | +38.0% | 24.9% | 28 | 26.8% | 1.11 | −57.9 | 1.7% |
| AGGR 8x, stop −7% | 180d | +41.6% | 29.1% | 49 | 42.3% | 1.21 | −91.6 | 6.7% |
| Micro-grid 8x, 0.2%/TP 0.3%, stop −10% | 180d | −40.7% | 53.6% | 71 | 158.3% | −1.19 | −102.2 | 3.9% |
| Micro-grid 8x, không stop | 180d | **−100% (thanh lý)** | 100% | 0 | – | – | – | – |
Bổ sung (`backtest/REPORT.txt`, 60 ngày, vốn 300): phong cách người dùng cơ học (lớp đầu 10x, 0.18%, ×0.87, 16 lớp, cap 49x, không stop) **thanh lý sau ~9 giờ**; bản thuần hoá (2x, cap 15x, 8 lớp, stop 1%) **−62%**, phí 782 USDT. Hồ sơ giao dịch thật 30 ngày (`profile/report.md`): +459.9 USDT ròng, win rate 90.9%, nhưng notional đỉnh 34–95x equity và một lần chỉ cách thanh lý ~0.06% (`recap.json`).
