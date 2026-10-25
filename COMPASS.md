# Sổ tay làm việc dự án Future Bitget

## 1. Mục đích và quy ước

Đây là sổ tay tra cứu trước khi khảo sát, sửa code hoặc thay đổi cách vận hành dự án. Rule tự động áp dụng riêng repo nằm trong [`CLAUDE.md`](CLAUDE.md). Sổ tay này chỉ ra mảng công việc, điểm bắt đầu, nguồn nghiệp vụ và các giới hạn đã biết.

Repo hiện là bộ script Python cho Bitget USDT-M futures, kèm frontend local Demo/dry-run. **Chưa có frontend production, CLI package thống nhất hoặc backend service production riêng.** Không xem nội dung dự thảo là chức năng đã có.

### Trạng thái thông tin

- **Đã có:** thấy trong mã hoặc tài liệu hiện tại.
- **Chưa có:** không tìm thấy triển khai trong repo hiện tại.
- **Chưa xác minh:** tài liệu/API chưa đủ chứng cứ để dựa vào.
- **Dự thảo:** ý tưởng hoặc định hướng chưa được duyệt làm đặc tả triển khai.

## 2. Tra cứu nhanh theo mảng

| Mảng / việc cần làm | Bắt đầu tại | Đọc cùng | Trạng thái và lưu ý |
|---|---|---|---|
| Spec, quyết định nghiệp vụ | [`spec/SPEC.md`](spec/SPEC.md) hoặc [`specs/zone-auto-trade-ai-plan.md`](specs/zone-auto-trade-ai-plan.md) | Mục 3 dưới đây | Hai tài liệu mô tả hai hướng khác nhau, không tự hợp nhất |
| AI Agent tự giao dịch có hạn mức | [`specs/ai-agent-autonomous-trading.md`](specs/ai-agent-autonomous-trading.md) | [`specs/ai-agent-implementation-design.md`](specs/ai-agent-implementation-design.md), `specs/zone-risk-policy.md`, `ai_proposal/`, `executor/`, [`trading/mandate_store.py`](trading/mandate_store.py), [`trading/reconcile.py`](trading/reconcile.py), [`trading/paper_scan.py`](trading/paper_scan.py), [`trading/protect_clock.py`](trading/protect_clock.py), [`trading/demo_cycle.py`](trading/demo_cycle.py) | Dự thảo cập nhật theo hướng người dùng cấp vốn và AI tự chủ trong mandate; P1 Bước 4 local (restart/reconcile/budget) **đã có**; các mode, hạn mức cụ thể, Demo và live vẫn chờ duyệt/xác minh riêng. Dự thảo mục 5.3: mỗi lần quét phân tích rồi ra phương án linh hoạt theo tình huống (0–nhiều hành động, trong mandate); nới SL nếu Risk Engine duyệt — khác P0 mục 7 cho tới khi chốt; frontend GET Demo **đã nối** (Tổng quan, không POST, poll GET 12s khi đang mở trang; fills gần nhất và đối soát UI với zone local **đã có**); field `position_review_interval` **đã có** trên Mandate (phút, 1–240, gợi ý 5/15/30/60 không tự lưu); chu kỳ quét paper **đã có** CLI tick/loop local (`metadata.plan_actions` 1–4 bước, không flatten khi hết giờ; mặc định không POST, `--place-orders --i-confirm-demo` POST Demo trong whitelist); đồng hồ bảo vệ paper **đã có** CLI tick/loop local tách scan (mark/fill/SL/UNKNOWN/kill, module không POST); chu kỳ Demo giám sát **đã có** GET mới + sổ equity (bootstrap ngày đầu) + protect flatten opt-in + scan nếu tới giờ; frontend Chạy/Dừng timer, không tự loop khi mở trang; tick Demo **đã nối** AI adapter (lỗi → `NO_TRADE`); WebSocket **chưa có** |
| Giao diện, output, CLI | Các `main()`/script liên quan; [`README.md`](README.md); [`frontend/`](frontend/); [`package.json`](package.json); [`trader/equity_cli.py`](trader/equity_cli.py); [`trader/bitget_snapshot_cli.py`](trader/bitget_snapshot_cli.py); [`trader/pair_screen_cli.py`](trader/pair_screen_cli.py); [`trader/style_cli.py`](trader/style_cli.py); [`trader/paper_scan_cli.py`](trader/paper_scan_cli.py); [`trader/demo_scan_cli.py`](trader/demo_scan_cli.py); [`trader/demo_kill_cli.py`](trader/demo_kill_cli.py); [`trader/protect_clock_cli.py`](trader/protect_clock_cli.py); [`trader/demo_verify_cli.py`](trader/demo_verify_cli.py) | [`specs/frontend-local.md`](specs/frontend-local.md) mục 8 IA, [`specs/manual-risk-settings.md`](specs/manual-risk-settings.md), [`specs/demo-verification-checklist.md`](specs/demo-verification-checklist.md) | CLI package thống nhất: **chưa có**; frontend local Demo/dry-run: **đã có**, một HTML nhiều view hash, `npm start` cổng `3007` (tự mở trình duyệt); Cấu hình AI (provider/model/timeout, version riêng; Gemini nhiều key ngang hàng, bốc ngẫu nhiên; OpenAI-compatible một key; form che ký tự giữa; Check live ping provider, dòng kết quả gần nhất không chứa key) tách khỏi Quyền AI; Mandate, Đề xuất cặp và Quyền AI là ba màn, cùng policy object; Đề xuất cặp GET public ticker (`GET /api/pair-screen`), user duyệt mới vào allowlist, không tự thêm; Tổng quan GET Demo (vào trang fetch một lần + poll GET 12s khi đang mở, nút làm mới tay; hàng số nổi: số dư/khả dụng/lãi-lỗ chưa chốt + đếm vị thế/lệnh/fills, không bịa PnL đã chốt hay PnL ngày; ticker từ snapshot nếu có; sổ đầy ngang tab vị thế/lệnh/lịch sử fills/đối soát/tài sản số sàn đã lọc hoặc rỗng rõ; chu kỳ Demo/Kill gập dưới sổ, hạn mức từ Mandate); Chu kỳ Demo (`POST /api/demo-cycle` → [`trader/demo_scan_cli.py`](trader/demo_scan_cli.py) `cycle`), một tick Chạy trên Demo, GET mới + equity bootstrap + protect flatten opt-in + scan nếu tới giờ, POST place/cancel/close + TPSL OPEN trong whitelist, GET reconcile sau gửi, gọi AI nếu đã cấu hình khi tới giờ (lỗi → `NO_TRADE`), live khóa, Chạy/Dừng timer không tự loop khi mở trang; không phiếu intent trên UI; tick cũ `POST /api/demo-scan` vẫn còn; Kill Demo (`POST /api/demo-kill` → [`trader/demo_kill_cli.py`](trader/demo_kill_cli.py)) hủy pending và flatten symbol đã duyệt, không qua AI; Kết nối: status Demo/env đủ-thiếu (`GET /api/connect-status`, `get_bitget=connected`) và form ghi Demo key vào `.env` (`POST /api/connect-credentials`, che giữa, không trả giá trị, không localStorage); Phong cách: form YAML local (`GET|POST /api/user-style` → [`trader/style_cli.py`](trader/style_cli.py), append-only, không hard limit); Nhật ký: stub; equity CLI GET-only: **đã có**; dashboard snapshot CLI GET-only: **đã có**; paper scan CLI tick/loop local: **đã có** (mặc định không POST; `--place-orders --i-confirm-demo` POST Demo whitelist); đồng hồ bảo vệ CLI tick/loop local: **đã có** (mark/fill/SL/UNKNOWN/kill, module không POST, tách scan, frontend không gọi CLI này); demo scan CLI cycle/loop: **đã có**; DemoVerify CLI: **đã có** (GET mặc định; POST D5-D6 cần `--place-orders --i-confirm-demo`); frontend production: **chưa có** |
| Tài khoản và vị thế read-only | [`bg.py`](bg.py), [`monitor.py`](monitor.py), [`trader/equity_cli.py`](trader/equity_cli.py), [`trader/bitget_snapshot_cli.py`](trader/bitget_snapshot_cli.py), [`trader/demo_verify_cli.py`](trader/demo_verify_cli.py) | [`trader/bgapi.py`](trader/bgapi.py), [`trader/bitget_readonly.py`](trader/bitget_readonly.py), [`trader/demo_verify.py`](trader/demo_verify.py) | Đã có script đọc, monitor, snapshot equity GET-only, dashboard snapshot CLI và harness DemoVerify; không phải executor/dispatcher |
| Bitget API và trader | [`trader/bgapi.py`](trader/bgapi.py) | [`trader/ta.py`](trader/ta.py), `spec/SPEC.md` | Có helper và dry-run; giao dịch live chưa được nghiệm thu |
| Ladder, chiến lược, risk | [`planner/ladder.py`](planner/ladder.py) | [`planner/PLAN.md`](planner/PLAN.md), `spec/SPEC.md` | Đối chiếu công thức và backtest trước khi đổi tham số |
| Dữ liệu và backtest | [`backtest/simulator.py`](backtest/simulator.py) | [`backtest/run_backtest.py`](backtest/run_backtest.py), `planner/` | Nghiên cứu; không phải bằng chứng lợi thế hoặc an toàn live |
| TA và mức giá | [`trader/ta.py`](trader/ta.py), [`trader/snap.py`](trader/snap.py) | `spec/SPEC.md` | TA là bộ lọc rủi ro, không phải dự báo |
| Journal, audit, PnL và profile phong cách | [`journal/journal.py`](journal/journal.py) | [`journal/style_digest.py`](journal/style_digest.py), [`profile/user_style.yaml`](profile/user_style.yaml), [`trading/style_load.py`](trading/style_load.py), [`specs/user-style-profile.md`](specs/user-style-profile.md), [`specs/experience-ledger.md`](specs/experience-ledger.md) | YAML **đã có** 9 entry; chu kỳ/tick Demo **đã nhét** `user_style` vào snapshot/prompt AI (preference, không hard limit). TA compact [`trader/ta_brief.py`](trader/ta_brief.py) trên cycle khi adapter có `public_candles`. Frontend Phong cách **đã có** (`#/phong-cach`, `GET|POST /api/user-style`, append-only). Kho kinh nghiệm: **dự thảo**, chưa triển khai. Digest journal tách riêng. Dataset học **chưa có** |
| Vận hành monitor | [`monitor.py`](monitor.py) | `journal/journal.py`, `README.md` | Có state cục bộ và journal hook; watcher production chưa có |
| Zone risk policy và xác minh Demo | [`specs/zone-risk-policy.md`](specs/zone-risk-policy.md) | [`specs/demo-verification-checklist.md`](specs/demo-verification-checklist.md), [`trader/demo_verify.py`](trader/demo_verify.py), [`trader/demo_verify_cli.py`](trader/demo_verify_cli.py), [`evidence/demo-verify/2026-10-22-btcusdt.jsonl`](evidence/demo-verify/2026-10-22-btcusdt.jsonl), [`evidence/demo-verify/2026-10-22-btcusdt-d7-d10.jsonl`](evidence/demo-verify/2026-10-22-btcusdt-d7-d10.jsonl), [`evidence/demo-verify/2026-10-22-btcusdt-d11-d15.jsonl`](evidence/demo-verify/2026-10-22-btcusdt-d11-d15.jsonl), [`trader/zone_risk.py`](trader/zone_risk.py), [`trader/zone_state.py`](trader/zone_state.py), [`trader/zone_store.py`](trader/zone_store.py), [`executor/zone_executor.py`](executor/zone_executor.py), [`ai_proposal/validator.py`](ai_proposal/validator.py), [`trading/`](trading/) | Risk policy đang ở bản dự thảo cập nhật cho mandate và AI tự chủ; Demo 2026-10-22 `BTCUSDT` D0–D6 PASS; D8–D13 PASS; D7 UNKNOWN (2 lot tại `last` khớp full); D11 PASS (`pos_loss`/`mark_price`); D14–D15 UNKNOWN; dispatcher Demo **đã có** (mặc định dry-run; scan CLI `--place-orders --i-confirm-demo` POST whitelist); live **chưa có** |
| Bảo mật | [`trader/bgapi.py`](trader/bgapi.py), [`trader/envfile.py`](trader/envfile.py) | [`README.md`](README.md), [`.env.example`](.env.example), `CLAUDE.md` | Key local điền vào `.env` (gitignored) hoặc OS env; không lộ key; live POST guard không được bỏ qua |
| Kiểm thử | File test liên quan, hiện có [`planner/test_sim.py`](planner/test_sim.py), [`tests/test_recovery.py`](tests/test_recovery.py), [`tests/test_paper_scan.py`](tests/test_paper_scan.py), [`tests/test_protect_clock.py`](tests/test_protect_clock.py), [`tests/test_demo_dispatch.py`](tests/test_demo_dispatch.py), [`tests/test_demo_kill.py`](tests/test_demo_kill.py), [`tests/test_demo_cycle.py`](tests/test_demo_cycle.py), [`tests/test_pair_screen.py`](tests/test_pair_screen.py), [`tests/test_frontend_mandate.py`](tests/test_frontend_mandate.py), [`tests/test_frontend_nav.py`](tests/test_frontend_nav.py), [`tests/test_frontend_style.py`](tests/test_frontend_style.py), [`tests/test_style_context.py`](tests/test_style_context.py), [`tests/test_ai_adapter.py`](tests/test_ai_adapter.py) | File module được sửa | Chọn kiểm tra hẹp theo thay đổi; không cài gói khi chưa duyệt |

## 3. Spec và quyết định nghiệp vụ

| Tài liệu | Trạng thái | Dùng khi |
|---|---|---|
| [`spec/SPEC.md`](spec/SPEC.md) | Đặc tả kỹ thuật cho công cụ DCA-ladder bán tự động, Wide/Scalp, CLI preview/execute/sync/cancel/kill/status/ta/journal; có giả định Cross margin và ràng buộc risk. | Sửa ladder hiện tại, lệnh, risk, API hoặc luồng công cụ theo đặc tả này. |
| [`specs/zone-auto-trade-ai-plan.md`](specs/zone-auto-trade-ai-plan.md) | Dự thảo định hướng bot theo mandate cấp vốn, zone loss-budget, isolated margin, ledger và các cổng AI. Policy P0 cũ đã được cập nhật thành bản dự thảo thống nhất với mode AI tự chủ; các con số vận hành, Demo semantics và live vẫn chưa chốt. | Nghiên cứu hoặc soạn spec cho hướng zone/AI; không triển khai nghiệp vụ còn mở. |
| [`planner/PLAN.md`](planner/PLAN.md) | Kế hoạch/kết quả nghiên cứu planner, không thay thế spec sản phẩm. | Sửa hoặc diễn giải nghiên cứu chiến lược. |
| [`specs/project-compass.md`](specs/project-compass.md) | Spec đã duyệt cho la bàn ban đầu. | Tham khảo nguồn gốc phạm vi sổ tay. |
| [`specs/project-handbook.md`](specs/project-handbook.md) | Spec đã duyệt cho sổ tay và rule riêng repo. | Tham khảo mục tiêu/tiêu chí của tài liệu này. |
| [`specs/du-phong-2.md`](specs/du-phong-2.md) | Thử vận hành tối giản: một cửa Chạy/Dừng, auto trên allowlist. Chưa chốt thay frontend-local / AI spec. Live khóa. | Xem hoặc sửa chu kỳ Tổng quan / `demo_cycle` allowlist; không hợp nhất với `spec/SPEC.md`. |

Nếu hai spec xung đột, nêu rõ xung đột và hỏi chủ dự án trước khi sửa code phụ thuộc vào quyết định đó. Không tự chuyển Cross margin thành isolated margin hoặc ngược lại. Mục tiêu lợi nhuận/backtest trong tài liệu không phải cam kết.

## 4. Giao diện và điểm vào

### Đã có

- [`bg.py`](bg.py): đọc account và positions qua Bitget v2, xuất JSON.
- [`monitor.py`](monitor.py): lấy account, positions, lệnh chờ/plan; so sánh `state.json`, in cảnh báo/thay đổi và gọi hook journal sync.
- Các script planner/backtest có entrypoint riêng.
- [`frontend/`](frontend/): frontend local-only Demo/dry-run, một HTML nhiều view theo hash (`#/tong-quan`, `#/ban-zone`, `#/ket-noi`, `#/cau-hinh-ai`, `#/phong-cach`, `#/mandate`, `#/de-xuat-cap`, `#/quyen-ai`, …). Nav bốn nhóm: Vận hành (Tổng quan, Bàn zone), Nền tảng (Kết nối, Cấu hình AI, Phong cách), Hạn mức (Mandate, Đề xuất cặp, Quyền AI), Chưa làm (Nhật ký). Hash mặc định `#/tong-quan`. Nav checklist local (số zone/version/allowlist/mode/số rule đã đọc, không GET, không in key). Dữ liệu zone/policy/AI/đề xuất cặp lưu local storage schema v5. Tổng quan GET Demo qua server local; một chu kỳ Demo qua `POST /api/demo-cycle` khi user xác nhận (GET mới, equity ledger, protect flatten opt-in, scan nếu tới giờ; place/cancel/close + TPSL OPEN, GET reconcile; gọi AI nếu đã cấu hình khi tới giờ quét, lỗi → `NO_TRADE`). Hạn mức SL/lỗ/risk/KL lấy từ Mandate. Nút Chạy / Dừng trên Tổng quan (timer ~8s, không tự chạy khi mở trang). Tick cũ `POST /api/demo-scan` vẫn còn. Kill Demo `POST /api/demo-kill` hủy pending và flatten symbol đã duyệt, không qua AI. Khởi động `npm start` ([`package.json`](package.json), [`frontend/server.js`](frontend/server.js)), cổng `3007`, chỉ nghe `127.0.0.1`, tự mở trình duyệt. Cấu hình AI lưu object `agentConfig` riêng (provider/model/timeout/key); đổi provider/model/key tạo agent-config version, không đụng version mandate. Gemini: nhiều key ngang hàng, mỗi key một nhãn, `gemini_key_strategy=random`; OpenAI-compatible: một `api_key`. Form che ký tự giữa (4 đầu + 4 cuối), lưu localStorage máy này; notice/log không in giá trị. Nút Check live ping provider qua `POST /api/ai-check` (chỉ Origin local; OpenAI-compatible HTTPS công khai, không SSRF nội bộ; hoặc gọi thẳng nếu proxy chưa có / URL local); dòng kết quả gần nhất lưu local, không chứa key; không phải đường giao dịch. Trang Kết nối đọc `GET /api/connect-status` (Đã có/Thiếu, không in giá trị) và form Demo key ghi `.env` qua `POST /api/connect-credentials` (Origin local, xác nhận Demo, không trả secret, không localStorage, không bật live). `get_bitget=connected`. Mandate nhập khẩu vị, gồm `position_review_interval` (phút, 1–240, gợi ý 5/15/30/60 không tự lưu); allowlist lần đầu được trống, chip chỉ đọc. Đề xuất cặp: GET public ticker rank khối lượng 24h, user duyệt/từ chối/thêm tay/gỡ; duyệt hoặc gỡ tạo policy version mới, đề xuất không tự vào allowlist. Chu kỳ quét paper và đồng hồ bảo vệ chạy CLI local riêng, frontend không tự tick. Quyền AI chọn 3 mode trên trang riêng, vẫn cùng policy object, đổi mode tạo version mới. Bàn zone: preview/status/sync; thiếu policy hoặc allowlist trống thì không tạo zone. Tổng quan GET Demo: vào `#/tong-quan` fetch một lần + poll GET 12s khi đang mở (ẩn tab thì dừng), nút làm mới tay; hàng số nổi (số dư/khả dụng/lãi-lỗ chưa chốt + đếm vị thế/lệnh/fills, không bịa PnL đã chốt hay PnL ngày); ticker last/mark/funding từ snapshot nếu có (sửa tay khi GET lỗi); sổ đầy ngang tab vị thế/lệnh/lịch sử fills/đối soát/tài sản hiện số sàn đã lọc hoặc rỗng rõ; fills tối đa 20 từ `/order/fills`; đối soát zone local với sàn chỉ đọc, không POST; chu kỳ Demo/Kill gập dưới sổ; không phiếu intent trên UI. Phong cách: `#/phong-cach` đọc/ghi YAML local (`GET|POST /api/user-style`, append-only, không hard limit). Nhật ký đang stub. Daily/drawdown/streak trên frontend chưa tính từ equity thật. CLI/paper có thể gắn features từ snapshot GET khi sổ equity local đủ `day_start`. `AUTONOMOUS_WITHIN_MANDATE` tạo paper intent OPEN local; tick Demo trên Tổng quan mới được POST whitelist (xác nhận Demo, live khóa). Nút Kill trên Tổng quan flatten Demo cùng symbol, không cần AI.

### Chưa có

- Frontend production kết nối backend hoặc Bitget.
- CLI package thống nhất thực hiện đầy đủ các lệnh mô tả trong `spec/SPEC.md`.

Khi thay đổi giao diện output, giữ ổn định dữ liệu và thông điệp máy đọc nếu có caller phụ thuộc. Không biến monitor thành nơi thực hiện lệnh giao dịch nếu chưa có spec được duyệt.

## 5. Backend/API và trader

| File | Vai trò |
|---|---|
| [`bg.py`](bg.py) | Lời gọi Bitget read-only đơn giản và xuất account/positions. |
| [`monitor.py`](monitor.py) | Đọc trạng thái account/position/order, phát hiện thay đổi và gọi journal. |
| [`trader/bgapi.py`](trader/bgapi.py) | Public GET, signed read-only GET, trade-key POST, JSONL log, dry-run. |
| [`trader/bitget_readonly.py`](trader/bitget_readonly.py) | GET-only Bitget adapter, Demo header `paptrading: 1`, cấm live; transport injectable cho test. Nạp `.env` local khi không truyền `environ`. `snapshot()` gồm account, vị thế, lệnh chờ, fills `/order/fills`. `order_detail` / `plan_pending` cho reconcile và kill. `public_tickers()` cho sàng lọc cặp. `public_candles()` cho TA compact Demo. |
| [`trader/envfile.py`](trader/envfile.py) | Đọc `.env` local vào process env; không ghi đè biến đã có; không log giá trị. |
| [`trader/equity_cli.py`](trader/equity_cli.py) | CLI local `snapshot` đọc equity Demo GET-only, in bản đã redaction; bắt buộc `--max-age-seconds`; không dump raw account, không tạo intent. |
| [`trader/bitget_snapshot_cli.py`](trader/bitget_snapshot_cli.py) | CLI local `snapshot` GET Demo cho dashboard: vị thế, lệnh chờ, fills gần nhất (`/order/fills`, tối đa 20), tài sản/equity đã lọc field, ticker nếu có `--symbol`; không dump raw account, không POST, không tạo intent. Frontend spawn qua `GET /api/bitget-snapshot`. |
| [`trader/pair_screen_cli.py`](trader/pair_screen_cli.py) | CLI local `screen` GET public `tickers` USDT-M, rank khối lượng 24h; không duyệt allowlist, không POST, không tạo intent. Frontend spawn qua `GET /api/pair-screen`. |
| [`trader/style_cli.py`](trader/style_cli.py) | CLI local `list` / `add` / `retire` cho `profile/user_style.yaml`; append-only; không sửa entry cũ; cấm từ khóa hard limit. Frontend spawn qua `GET|POST /api/user-style`. |
| [`trading/pair_screen.py`](trading/pair_screen.py) | Hàm rank ứng viên public theo volume 24h; `exclude` bỏ symbol đã duyệt/từ chối; không tự thêm allowlist. |
| [`trader/paper_scan_cli.py`](trader/paper_scan_cli.py) | CLI local `tick` / `loop` cho chu kỳ quét paper; đọc mandate interval, gọi [`trading/paper_scan.py`](trading/paper_scan.py); cấm `GROK_TRADER_ALLOW_LIVE` và `BITGET_ENV` live; mặc định provider `NO_TRADE`; mặc định không POST; `--place-orders --i-confirm-demo` POST Demo chỉ symbol trong whitelist mandate; không flatten khi hết giờ. |
| [`trader/demo_scan_cli.py`](trader/demo_scan_cli.py) | Tick / cycle / loop Demo từ policy frontend: map allowlist + hạn mức Mandate (`sl_pct` / `zone_loss_limit_usdt` / `max_order_risk_usdt` / `max_size`, hoặc limits.json) → mandate. `tick` gọi paper scan + `demo_dispatch`. `cycle`/`loop` gọi [`trading/demo_cycle.py`](trading/demo_cycle.py): GET snapshot mới, sổ equity (bootstrap ngày đầu), protect, scan nếu tới giờ. `--agent-config` gọi AI khi scan tới giờ (intent `--proposal` thắng; lỗi → `NO_TRADE`); cấm live; mặc định dry-run; `--place-orders --i-confirm-demo` POST place/cancel/close trong allowlist, TPSL `pos_loss` kèm OPEN, và flatten khi protect trigger. Frontend spawn `tick` qua `POST /api/demo-scan`, `cycle` qua `POST /api/demo-cycle`. |
| [`trader/demo_kill_cli.py`](trader/demo_kill_cli.py) | Flatten Demo một symbol whitelist: hủy lệnh chờ rồi đóng vị thế (hedge = `buy`/`sell` + `tradeSide=close`); không gọi AI; cấm live; mặc định dry-run; `--place-orders --i-confirm-demo` mới POST. Frontend spawn qua `POST /api/demo-kill`. |
| [`trading/frontend_mandate.py`](trading/frontend_mandate.py) | Map policy localStorage → `TradingMandate`; hạn mức lệnh từ Mandate hoặc limits.json qua `scan_limits_from_policy`; allowlist trống hoặc symbol ngoài list thì không tạo mandate giao dịch; không bịa số risk. |
| [`trader/protect_clock_cli.py`](trader/protect_clock_cli.py) | CLI local `tick` / `loop` cho đồng hồ bảo vệ; gọi [`trading/protect_clock.py`](trading/protect_clock.py); cấm `GROK_TRADER_ALLOW_LIVE`; không dùng `position_review_interval`; không POST. Frontend không gọi CLI này; chu kỳ Demo gọi protect rồi có thể flatten qua dispatcher. |
| [`trader/demo_verify.py`](trader/demo_verify.py) | Harness checklist Demo D0-D15: GET baseline, POST Demo có khóa, redaction, phân loại `FOUND`/`REJECTED`/`VERIFIED_NOT_RECEIVED`/`UNKNOWN`. Không phải dispatcher. |
| [`trader/demo_verify_cli.py`](trader/demo_verify_cli.py) | CLI `run --symbol`; mặc định GET-only; POST D5–D10 cần `--place-orders --i-confirm-demo`; cấm live và `GROK_TRADER_ALLOW_LIVE`; ghi evidence JSONL đã redaction vào `logs/` (gitignored). Bản commit: [`evidence/demo-verify/2026-10-22-btcusdt.jsonl`](evidence/demo-verify/2026-10-22-btcusdt.jsonl), [`evidence/demo-verify/2026-10-22-btcusdt-d7-d10.jsonl`](evidence/demo-verify/2026-10-22-btcusdt-d7-d10.jsonl). |
| [`trader/zone_store.py`](trader/zone_store.py) | P1 SQLite durable zone config/state, observations and append-only audit events. |
| [`trader/zone_cli.py`](trader/zone_cli.py) | P1 local `preview`, `status`, `sync` mock/dry-run entrypoint; never sends exchange requests. |
| [`trader/ta.py`](trader/ta.py) | Tính indicator, key levels và ladder risk. |
| [`executor/zone_executor.py`](executor/zone_executor.py) | P2 local-only deterministic entry/DCA/cancel/emergency-close intent state machine; `restore`/`load_zone` đọc lại pending/unknown từ SQLite sau restart; no exchange dispatcher. |
| [`executor/p1_adapter.py`](executor/p1_adapter.py) | P1 SQLite bridge for P2 intents/events/snapshots, paper intent runtime, mandate versions, paper budget events and P3 proposal audit events; no order dispatch. |
| [`ai_proposal/schema.py`](ai_proposal/schema.py) | P3 immutable decision snapshot, proposal and validation record schemas. |
| [`ai_proposal/validator.py`](ai_proposal/validator.py) | P3 deterministic hard-limit validator; accepted/rejected result only. |
| [`ai_proposal/interface.py`](ai_proposal/interface.py) | P3 model/provider-agnostic proposal boundary; no model/network call. |
| [`ai_proposal/adapter.py`](ai_proposal/adapter.py) | Một lần gọi Gemini/OpenAI-compatible cho tick Demo; OpenAI-compatible nhận HTTPS công khai, chặn URL nội bộ; prompt gồm `user_style` + `ta` nếu có trên snapshot; parse JSON; lỗi/timeout/sai schema → `NO_TRADE`; không log key; không gọi Bitget. |
| [`trading/mandate.py`](trading/mandate.py) | Paper mandate immutable: vốn cấp, 3 mode AI, daily loss/action, chuỗi lỗ/cooldown, drawdown, leverage, `position_review_interval` (phút, 1–240), isolated/limit policy, `ADJUST_SL`/`CANCEL` trong allowlist. Thiếu field hoặc TBD chặn tăng rủi ro. `AUTONOMOUS_WITHIN_MANDATE` tạo paper OPEN local, không POST. |
| [`trading/risk_engine.py`](trading/risk_engine.py) | Deterministic proposal-to-mandate check; validates loss budget, order risk, leverage, isolated margin, limit/market reduce-only, daily loss, drawdown, loss streak, `allow_average_down` và `ADJUST_SL` (nới SL nếu remaining loss-to-SL còn trong hard limit). No dispatch. Thiếu/stale equity chặn intent tăng rủi ro. |
| [`trading/equity_store.py`](trading/equity_store.py) | Sổ SQLite append-only cho số equity đã parse; không lưu secret hay raw response. |
| [`trading/equity_snapshot.py`](trading/equity_snapshot.py) | Builder GET-only: `day_start_equity` = snapshot cuối trước 00:00 UTC; Demo cycle có thể bootstrap mốc phiên bằng hàng UTC-day đầu (`DAY_START_BOOTSTRAP`); thiếu/stale thì không bịa số. PaperAgent không gọi module này. |
| [`trading/paper_agent.py`](trading/paper_agent.py) | Paper pipeline: `PROPOSAL_ONLY` chỉ ghi proposal; `MANAGED_ZONE` tạo paper intent trên zone user; `AUTONOMOUS_WITHIN_MANDATE` được OPEN paper (tạo zone `opened_by=ai` nếu chưa có). `metadata.plan_actions` 1–4 bước, từng bước qua Risk Engine; bước bị từ chối không gửi, không bịa thay thế. Trước khi gọi AI: nạp mandate mới nhất, chặn nếu còn `UNKNOWN` hoặc remaining budget ≤ 0. OPEN mới trừ `max_order_risk` khỏi sổ budget local. Cùng `client_oid` không tạo bản thứ hai. `EMERGENCY_FLATTEN` gọi executor dry-run một lần. Không gọi sàn. |
| [`trading/paper_scan.py`](trading/paper_scan.py) | Đồng hồ quét paper local: đọc `position_review_interval`, `tick`/`loop` gọi `PaperAgent.run()` khi tới giờ. Chưa tới giờ / stale / `UNKNOWN` / zone không ACTIVE (trừ AUTONOMOUS chưa có zone) / mandate hết hạn → `NO_TRADE`, không gọi AI, không flatten. Có thể 0–N paper intent. Không chạy đồng hồ bảo vệ. Mặc định không POST; opt-in `ScanDispatchOptions` gọi [`trading/demo_dispatch.py`](trading/demo_dispatch.py) cho symbol trong `allowed_symbols`; OPEN kèm TPSL `pos_loss`; sau POST GET `order_detail` để `PaperReconcile`; cùng `client_oid` không POST lại; `UNKNOWN` → `paper_unknown`. |
| [`trading/protect_clock.py`](trading/protect_clock.py) | Đồng hồ bảo vệ paper local, tách scan: `tick`/`loop` nhận quan sát mark/fill/SL/`UNKNOWN`/kill; fill → `PaperReconcile`; mark chạm SL/loss → `ZoneExecutor.on_risk_trigger` dry-run một lần; stale/`UNKNOWN` không bắn SL bịa; kill flatten một lần. Không gọi PaperAgent. Module không POST. |
| [`trading/demo_cycle.py`](trading/demo_cycle.py) | Một chu kỳ Demo giám sát: GET snapshot mới, ghi sổ equity (bootstrap ngày đầu UTC), protect, flatten opt-in nếu trigger, rồi scan nếu tới giờ. Thử Dự phòng 2: `run_allowlist_cycle` đi hết cặp đã duyệt, equity một lần. Không tự loop; CLI `loop` hoặc frontend timer. Live khóa. `zone_loss_limit` không phải cam kết lỗ tuyệt đối. |
| [`trading/demo_dispatch.py`](trading/demo_dispatch.py) | Dispatcher Demo: cấm live/`GROK_TRADER_ALLOW_LIVE`; cần `confirm_demo`; mặc định dry-run. POST `place-order` (OPEN/CLOSE/REDUCE), `cancel-order`, TPSL `pos_loss` kèm OPEN; `ADJUST_SL` vẫn dry-run. GET order detail sau gửi để reconcile. `kill_symbol` hủy pending + flatten, không qua AI. Whitelist rỗng hoặc ngoài list thì không POST. Protect clock **không** gọi; [`trading/demo_cycle.py`](trading/demo_cycle.py) có thể gọi `kill_symbol` khi protect trigger. WebSocket **chưa có**. |
| [`trading/mandate_store.py`](trading/mandate_store.py) | Facade mandate version append-only và `recover_session`; sổ loss-budget chỉ tiêu, không cấp lại sau restart. Local, không gọi sàn. |
| [`trading/reconcile.py`](trading/reconcile.py) | Biên quan sát paper: `confirmed_open` / `confirmed_absent` / `partial` / `unknown`; timeout → `UNKNOWN`; cập nhật remaining. Không phải dispatcher Demo. |

### Quy tắc khi sửa API/trader

- Kiểm tra key scope, request signing, response/error handling, timeout và log redaction.
- `trader/bgapi.py::post()` mặc định dry-run. Live POST được chặn trừ khi có đủ trade key và `GROK_TRADER_ALLOW_LIVE=1`; không bật guard trong công việc thường lệ.
- Không dùng credential hoặc tài khoản live trong test.
- Executor production, quản lý vòng đời lệnh và reconcile WebSocket production: **chưa có**.

## 6. Chiến lược, ladder và risk

| File | Vai trò |
|---|---|
| [`planner/ladder.py`](planner/ladder.py) | Lấy public price/ATR/contract, tính các lớp ladder và liquidation estimate. |
| [`planner/PLAN.md`](planner/PLAN.md) | Nguồn nghiên cứu planner và kết quả. |
| [`planner/sim.py`](planner/sim.py) | Indicator và mô phỏng planner. |
| [`planner/run_grid.py`](planner/run_grid.py), [`planner/run_grid2.py`](planner/run_grid2.py), [`planner/combined_grid.py`](planner/combined_grid.py) | Tìm kiếm tổ hợp tham số. |
| [`planner/final_eval.py`](planner/final_eval.py), [`planner/analyze.py`](planner/analyze.py), [`planner/analyze2.py`](planner/analyze2.py), [`planner/neighbors.py`](planner/neighbors.py) | Đánh giá và phân tích vùng tham số. |
| [`trader/ta.py`](trader/ta.py), [`trader/snap.py`](trader/snap.py) | Bộ lọc kỹ thuật và snap layer. |

Trước khi đổi tham số hoặc công thức, đọc spec đúng hướng, xác định tác động lên size/exposure/liquidation/fees, rồi kiểm tra backtest liên quan. Không tuyên bố TA dự báo giá. Backtest hiện có không chứng minh an toàn live.

## 7. Dữ liệu, journal, PnL và profile

| File | Vai trò |
|---|---|
| [`journal/journal.py`](journal/journal.py) | Raw append, event/upsert và đồng bộ account history, pending orders, fills, plans, positions. |
| [`journal/style_digest.py`](journal/style_digest.py) | Tạo digest thời lượng, equity và size từ journal; không trộn vào `user_style.yaml`, không tự học. |
| [`profile/user_style.yaml`](profile/user_style.yaml) | 9 entry active (mcp_chat, 2026-10-23): BTC/ETH, fade 1h, limit/maker, DCA ~0.18%, hedge, scale-out, giảm khi đỏ. Không đòn bẩy/vốn. |
| [`trading/style_load.py`](trading/style_load.py) | Nạp/gộp YAML local vào `features.user_style`; list latest + append/retire version; bỏ entry chứa từ khóa hard limit; không gọi sàn. |
| [`trader/ta_brief.py`](trader/ta_brief.py) | TA compact từ nến public + [`trader/ta.py`](trader/ta.py); thiếu nến/numpy → `unavailable`, không bịa mức. |
| [`trading/decision_context.py`](trading/decision_context.py) | Gắn style + TA lên features snapshot Demo. |
| [`profile/report.md`](profile/report.md) | Báo cáo nghiên cứu nguồn cho YAML; không phải context runtime. |
| [`specs/experience-ledger.md`](specs/experience-ledger.md) | Dự thảo kho bài học; chưa code. |
| [`planner/recap.py`](planner/recap.py) | Tạo recap và báo cáo position/exposure của planner. |

Khi sửa audit hoặc PnL:

- giữ dữ liệu nguồn append-oriented; không âm thầm xóa hoặc sửa lịch sử;
- phân biệt realized PnL, unrealized PnL, phí và funding, tránh tính trùng;
- đối soát với dữ liệu Bitget và ghi rõ nguồn/thời điểm;
- không đưa dữ liệu tài khoản thật, key hoặc thông tin nhạy cảm vào tài liệu/test.

- Ledger zone và decision-opportunity dataset: zone store SQLite P1 đã có cấu hình/trạng thái/observation/event cục bộ; decision-opportunity dataset vẫn **chưa có**.

## 8. Backtest và TA

| File | Vai trò |
|---|---|
| [`backtest/simulator.py`](backtest/simulator.py) | Engine simulator chính và mô hình trạng thái. |
| [`backtest/run_backtest.py`](backtest/run_backtest.py) | Nạp dữ liệu, chạy backtest, lưu kết quả/biểu đồ. |
| [`backtest/run_user_style.py`](backtest/run_user_style.py) | Backtest phong cách người dùng. |
| [`backtest/download_data.py`](backtest/download_data.py) | Tải dữ liệu cho backtest. |
| [`trader/ta.py`](trader/ta.py) | Indicator đa khung và risk filter. |

Kết quả backtest là nghiên cứu. Trước khi dùng làm căn cứ risk/triển khai, kiểm tra độ rò rỉ dữ liệu, chia tách thời gian/ngoài mẫu, mark price, liquidation path, fill/slippage, fees, funding và episode chưa đóng. Những yếu tố chưa mô hình hóa phải được ghi là giới hạn, không được ngầm coi là đã bao gồm.

## 9. Vận hành và trạng thái triển khai

### Đang có

- Script read-only account/position (`bg.py`).
- Monitor so sánh state cục bộ, phát cảnh báo và gọi journal sync (`monitor.py`).
- Journal sync REST và script nghiên cứu/backtest.
- P1 local zone foundation: SQLite store and CLI mock/dry-run `preview/status/sync`; adapter Bitget GET-only có thể đọc account/position/order/ticker/contract.
- P2 local dry-run executor tạo intent entry/DCA/cancel/emergency-close với idempotency và state machine fill/timeout/unknown.
- P3 AI proposal-only lưu snapshot/proposal append-only, deterministic hard-limit validator và audit bridge vào SQLite P1.
- P1 paper agent: mandate có vốn/mode AI, risk fail-closed, paper intent OPEN/CLOSE/REDUCE/ADJUST_SL/CANCEL, combo `plan_actions`, `PROPOSAL_ONLY` không tạo intent, AUTONOMOUS được OPEN paper local; không gọi exchange.
- P1 Bước 4 local: khôi phục mandate/paper intent/executor pending-unknown sau restart (chỉ đọc SQLite, không hỏi sàn), reconcile paper (`confirmed_open`/`confirmed_absent`/`partial`/`unknown`), chặn AI/intent mới khi còn `UNKNOWN` mọi `client_oid`, risk dùng mandate mới nhất, OPEN trừ `max_order_risk` khỏi sổ budget, không cấp lại budget. Chưa phải reconcile sàn.
- Equity GET-only: adapter → builder features (`day_start`/`daily_loss`/`drawdown`) → CLI local; thiếu sổ ngày trước hoặc stale thì không tăng rủi ro. Chưa phải trigger production và chưa xác minh Demo.
- DemoVerify harness: CLI GET-only mặc định; POST Demo D5–D15 chỉ khi có `--place-orders --i-confirm-demo`; mock đã cover FOUND/REJECTED/UNKNOWN/VERIFIED_NOT_RECEIVED. Demo 2026-10-22 `BTCUSDT` (`isolated`, `hedge_mode`): D0–D6 PASS; D7 UNKNOWN (2 lot tại `last` khớp full trong một GET, không partial); D8 PASS (`FOUND`/`NOT_FOUND`/`UNKNOWN` do timeout client, `extra_place=0`); D9 PASS (`no-duplicate-rejected`); D10 PASS (đóng long hedge = `buy`+`tradeSide=close`, leftover flatten); D11 PASS (`pos_loss` khi còn long, GET `planType=profit_loss` thấy `mark_price`); D12–D13 PASS; D14–D15 UNKNOWN (có `unrealizedPL`/`deductedFee`/`liquidationPrice`, chưa tách realized/funding, không có sự kiện thanh lý). Bằng chứng: [`evidence/demo-verify/2026-10-22-btcusdt.jsonl`](evidence/demo-verify/2026-10-22-btcusdt.jsonl), [`evidence/demo-verify/2026-10-22-btcusdt-d7-d10.jsonl`](evidence/demo-verify/2026-10-22-btcusdt-d7-d10.jsonl), [`evidence/demo-verify/2026-10-22-btcusdt-d11-d15.jsonl`](evidence/demo-verify/2026-10-22-btcusdt-d11-d15.jsonl).
- P1 đồng hồ bảo vệ local: CLI `tick`/`loop` tách chu kỳ quét; mark/fill/SL/`UNKNOWN`/kill; dry-run emergency một lần; không POST.
- `trader/bgapi.py` có chế độ dry-run và guard cho live POST.

### Chưa có hoặc chưa nghiệm thu

- Executor production và watcher lệnh production.
- Zone state machine và ledger giới hạn lỗ production/reconcile: chưa có; P1 chỉ lưu state/observation local và stop intent dry-run.
- Dispatcher exchange live, WebSocket reconcile production và phục hồi theo trạng thái sàn sau restart/reconnect. Dispatcher Demo local **đã có** (dry-run mặc định; scan CLI POST whitelist opt-in); phục hồi local SQLite (paper/executor) đã có.
- Kill workflow production đã được kiểm thử đầy đủ.
- AI proposal có schema/validator/log, P1 paper pipeline, và adapter HTTP cho tick/cycle Demo (test mock, không gọi mạng trong CI). Dispatcher Demo **đã có**: scan CLI POST whitelist opt-in; protect không gọi; demo cycle flatten khi protect trigger. Live **chưa**. Harness DemoVerify không phải đường thực thi AI.
- Triển khai live được nghiệm thu.
- Tailscale gateway.

Không chạy lệnh thay đổi trạng thái tài khoản, gửi lệnh, deploy hoặc thao tác vận hành có tác động bên ngoài khi chưa được chủ dự án yêu cầu rõ. `zone_loss_limit` là ngưỡng điều khiển, không phải bảo đảm lỗ thực tế tuyệt đối.

## 10. Bảo mật và an toàn

- Không in/ghi secret, token, mật khẩu, API key, signature/header ký hoặc dữ liệu tài khoản thật vào output, log, test hoặc tài liệu.
- Key Bitget Demo điền vào [`.env`](.env) (gitignored). Bản mẫu: [`.env.example`](.env.example). Không commit `.env`.
- Key AI của frontend local nhập trên trang Cấu hình AI, form che ký tự giữa, lưu localStorage máy này; không in giá trị vào notice/log. Check live được phép gọi AI provider; `POST /api/ai-check` chỉ nhận Origin local. OpenAI-compatible nhận mọi host HTTPS công khai, không gửi key tới URL nội bộ/arbitrary scheme.
- Key Bitget Demo nhập trên trang Kết nối, ghi `.env` local qua `POST /api/connect-credentials`; form che giữa, không lưu localStorage, không trả giá trị, không bật live. Không dùng form này cho trade key live.
- Dùng key chỉ đọc cho tác vụ đọc. Không đưa trade key vào môi trường test.
- Không bỏ qua dry-run/live guard; không tự đặt lệnh live.
- Không tự deploy, push, merge, cài/nâng cấp dependency, tạo/sửa migration hoặc xóa dữ liệu nếu chưa được yêu cầu rõ.
- Nếu phát hiện secret trong output/tài liệu, không lặp lại giá trị; báo vị trí cần xử lý.
- Hành vi Bitget chưa xác minh phải được đánh dấu và kiểm chứng Demo theo spec trước khi dựa vào.

## 11. Kiểm thử và checklist thay đổi

### Trước khi sửa

1. Đọc [`CLAUDE.md`](CLAUDE.md) và mục tương ứng trong sổ tay này.
2. Xác định mảng thay đổi và file bắt đầu; chỉ mở thêm các file phụ thuộc cần thiết.
3. Đọc spec nguồn nếu thay đổi có tác động nghiệp vụ hoặc an toàn.
4. Nếu spec mơ hồ/xung đột, không đoán; hỏi trước cho phần bị chặn.
5. Chốt kiểm tra nhỏ nhất phù hợp trước khi sửa.

### Sau khi sửa

1. Chạy test/lint/kiểm tra liên quan; không cài dependency mới nếu chưa duyệt.
2. Kiểm tra diff chỉ chứa file thuộc phạm vi.
3. Cập nhật la bàn nếu đổi file neo, cấu trúc, entrypoint, luồng dữ liệu, trạng thái tính năng hoặc quy tắc vận hành.
4. Kiểm tra đường dẫn tài liệu mới và bảo đảm không lộ secret/dữ liệu thật.
5. Báo file đã đổi, kiểm tra và kết quả; nêu rõ phần chưa chạy/chưa xác minh.

Test hiện có được thấy trong repo: [`planner/test_sim.py`](planner/test_sim.py). Chọn thêm test đúng module nếu có; không khẳng định đã chạy khi chưa chạy.

## 12. AI và zone

Nguồn định hướng là [`specs/zone-auto-trade-ai-plan.md`](specs/zone-auto-trade-ai-plan.md) và [`specs/ai-agent-autonomous-trading.md`](specs/ai-agent-autonomous-trading.md). Ba mode AI đã có trên mandate/frontend/paper: `PROPOSAL_ONLY`, `MANAGED_ZONE`, `AUTONOMOUS_WITHIN_MANDATE`. Mode tự chủ **paper local được OPEN**; Demo POST whitelist opt-in từ scan CLI; live vẫn khóa. P0 [`zone-policy-decisions.md`](specs/zone-policy-decisions.md) mục 7 vẫn cấm nới SL tăng rủi ro; paper đợt D theo dự thảo AI mục 4.7 (nới nếu remaining loss-to-SL còn trong hard limit) — **chưa chốt P0**.

Không dùng số P lẫn giữa spec sản phẩm, cổng AI và code. Cổng đã làm: `LocalContract` + `PaperModes` + `ReadonlyEquity` + `LocalRecovery` + harness `DemoVerify` + Demo D0–D6, D8–D13 + paper combo/`ADJUST_SL` + dispatcher Demo whitelist POST (scan CLI opt-in) + đồng hồ bảo vệ local. Cổng chưa đóng: Demo D7 (partial fill chưa quan sát trên `BTCUSDT` 2 lot), D14–D15 UNKNOWN, `Shadow`, live. P0 mục 7 vs nới SL paper **chưa chốt**. D11–D13 Demo **đã PASS**.

- Dashboard + chu kỳ quét (spec AI mục 5.3): frontend GET Demo **đã nối** (vị thế, lệnh chờ, fills gần nhất, đối soát UI với zone local; poll GET 12s khi đang mở Tổng quan, không POST); `position_review_interval` **đã có**; paper scan CLI **đã có** (mặc định không POST; `--place-orders --i-confirm-demo` POST Demo trong whitelist); frontend **chu kỳ Demo** (`POST /api/demo-cycle`) **đã có**; thử Dự phòng 2: một cửa Chạy/Dừng, `scope=allowlist` đi hết cặp đã duyệt (GET mới, equity một lần, protect flatten opt-in, scan nếu tới giờ; hạn mức Mandate, whitelist, TPSL OPEN, GET reconcile; không checkbox/hướng; không tự loop khi mở trang; UI cần AI, lỗi → `NO_TRADE`); không phiếu intent trên UI; tick cũ `POST /api/demo-scan` vẫn còn; Kill Demo (`POST /api/demo-kill`) **đã có** (flatten whitelist, không qua AI); đồng hồ bảo vệ CLI **đã có** (tách scan, module không POST); combo `metadata.plan_actions` (tối đa 4) **đã có** trên paper; `ADJUST_SL` paper **đã có** nếu remaining loss-to-SL trong hạn mức. WebSocket **chưa có**.
- Risk engine thuần hàm và lifecycle khô local cho zone: **đã có, chưa nối sàn**.
- Zone store SQLite append-oriented lưu config bất biến, state, observation và audit event; CLI local có `preview/status/sync` mock/dry-run.
- Adapter Bitget chỉ GET, dùng read-only env vars; **đã nối** CLI equity + builder features cho risk/paper (caller gắn tay), harness DemoVerify, frontend Tổng quan (CLI snapshot gồm fills `/order/fills`, không POST), và Đề xuất cặp (public tickers, user duyệt allowlist, không POST). Field `accountEquity` theo contract test local, **chưa xác minh** trên tài khoản Demo. Snapshot fills Demo **chưa xác minh** trên tài khoản Demo thật.
- Executor, state machine bền vững theo dữ liệu sàn, reconcile WebSocket và loss-budget ledger production: **chưa có**.
- Decision opportunity dataset: **chưa có**.
- Paper agent dùng `ai_proposal/provider.py` với provider protocol/fake; pipeline lưu decision/risk/paper intent qua `executor/p1_adapter.py`, nạp lại sau restart bằng `trading/mandate_store.py` và quan sát local bằng `trading/reconcile.py`; không gọi exchange.
- Adapter AI HTTP cho tick/cycle Demo: [`ai_proposal/adapter.py`](ai_proposal/adapter.py); frontend/CLI opt-in khi scan tới giờ; prompt đọc `user_style` đã nạp và TA compact trên cycle; lỗi → `NO_TRADE`. paper_scan_cli vẫn mặc định không gọi mạng. AI training/evaluation: **chưa có**. Kho kinh nghiệm: dự thảo [`specs/experience-ledger.md`](specs/experience-ledger.md), chưa triển khai.
- Dispatcher Demo: **đã có** [`trading/demo_dispatch.py`](trading/demo_dispatch.py); mặc định dry-run; paper scan CLI POST place/cancel/close + TPSL OPEN trong whitelist khi `--place-orders --i-confirm-demo`; GET reconcile sau gửi; kill CLI/frontend flatten whitelist; `ADJUST_SL` vẫn dry-run; protect clock không gọi; demo cycle có thể gọi `kill_symbol` khi protect trigger. Live: **chưa có**. Harness `demo_verify` ghi evidence; không phải đường thực thi AI.
- Tailscale gateway: **chưa có**.

P0 không gửi/cancel lệnh. Adapter GET-only đã nối CLI equity và harness DemoVerify (GET mặc định). Harness đã POST Demo D5–D13 (`BTCUSDT` 2026-10-22); JSONL đã redaction tại [`evidence/demo-verify/2026-10-22-btcusdt.jsonl`](evidence/demo-verify/2026-10-22-btcusdt.jsonl), [`evidence/demo-verify/2026-10-22-btcusdt-d7-d10.jsonl`](evidence/demo-verify/2026-10-22-btcusdt-d7-d10.jsonl) và [`evidence/demo-verify/2026-10-22-btcusdt-d11-d15.jsonl`](evidence/demo-verify/2026-10-22-btcusdt-d11-d15.jsonl). Dispatcher Demo POST từ paper scan **đã mở** trong whitelist (CLI `--place-orders --i-confirm-demo`); mặc định dry-run; live khóa. D7/D14–D15 vẫn UNKNOWN.

## 13. Bản đồ luồng hiện tại

```text
Bitget REST read-only
        |
        +--> bg.py ----------------------> JSON account/positions
        |
        +--> monitor.py --> state.json --> báo cáo thay đổi/cảnh báo
                         |
                         +--> journal/journal.py --> raw/event/upsert journal
        |
        +--> trader/bitget_readonly.py -- GET, paptrading: 1, cấm live
                    |
                    +--> trading/equity_snapshot.py --> trading/equity_store.py
                    |         |
                    |         +--> features --> caller gắn vào risk_engine / paper_agent
                    +--> trader/equity_cli.py --> snapshot đã redaction
                    +--> trader/bitget_snapshot_cli.py --> JSON đã lọc field
                    |         |         (positions, pending, fills /order/fills)
                    |         +--> frontend/server.js GET /api/bitget-snapshot
                    |                   --> Tổng quan (vào trang + poll GET 12s;
                    |                       tab fills + đối soát zone local)
                    +--> trader/pair_screen_cli.py --> trading/pair_screen.py
                              |         (public tickers, rank volume 24h)
                              +--> frontend/server.js GET /api/pair-screen
                                        --> Đề xuất cặp (user duyệt mới vào allowlist)
                    +--> trader/demo_verify.py --> checklist D0-D15, evidence đã redaction
                    |         POST D5-D10 chỉ khi --place-orders --i-confirm-demo

frontend local
  GET /api/connect-status --> env đủ/thiếu, get_bitget=connected
  POST /api/connect-credentials --> ghi Demo key vào .env local
  GET /api/bitget-snapshot --> spawn CLI GET Demo, Origin local, cấm live
                            --> Tổng quan: vị thế/lệnh/fills + đối soát; poll GET 12s
  GET /api/pair-screen --> spawn CLI public tickers, Origin local, cấm live
                       --> Đề xuất cặp: ứng viên chờ user duyệt, không tự thêm
  GET /api/user-style --> spawn trader/style_cli list; YAML local, Origin local
  POST /api/user-style --> spawn trader/style_cli add|retire; append-only; không hard limit
                       --> Phong cách: form không localStorage, không đè Mandate
  POST /api/demo-scan --> spawn trader/demo_scan_cli tick
                      --> mandate từ policy + allowlist; POST Demo opt-in
                      --> place/cancel/close + TPSL OPEN; GET reconcile
                      --> optional AI một lần (adapter); CLI --proposal thắng; lỗi → NO_TRADE
                      --> whitelist rỗng / ngoài list / live → không POST
  POST /api/demo-cycle --> spawn trader/demo_scan_cli cycle
                       --> thử Dự phòng 2: scope=allowlist, một cửa Chạy
                       --> GET snapshot mới + sổ equity một lần (bootstrap ngày đầu)
                       --> hạn mức SL/lỗ/risk/KL từ Mandate; gọi AI nếu đã cấu hình
                       --> features.user_style (YAML local) + features.ta (nến public)
                       --> mỗi cặp đã duyệt: protect; flatten opt-in nếu trigger; scan nếu tới giờ
                       --> frontend timer Chạy/Dừng; không tự loop khi mở trang
  POST /api/demo-kill --> spawn trader/demo_kill_cli run
                      --> hủy pending + flatten symbol allowlist; không qua AI
  POST /api/ai-check --> ping provider, Origin local, không SSRF nội bộ

Public market data --> planner/ladder.py --> bảng ladder
                  --> planner/sim.py ------> planner/backtest reports
                  --> trader/ta.py --------> indicators và risk filter

P1 zone CLI (local only)
  preview --> trader/zone_store.py --> SQLite config/state/events
  status  --> trader/zone_store.py --> local snapshot
  sync    --> mock/dry-run observation --> risk trigger/STOPPING intent

P1 paper recovery (local only)
  restart --> trading/mandate_store.recover_session --> mandate + paper intents + remaining budget
          --> trading/reconcile.PaperReconcile --> confirmed_open/absent/partial/unknown
          --> ZoneExecutor.restore --> pending/unknown executor intents
          PaperAgent chặn AI/intent mới khi zone còn UNKNOWN (mọi client_oid)
          OPEN paper trừ max_order_risk khỏi sổ budget local; hết budget chặn trước AI

P1 paper scan (local; Demo POST opt-in)
  trader/paper_scan_cli tick|loop --> trading/paper_scan.py
          --> due? PaperAgent.run() --> proposal / risk / 0-N paper intent (plan_actions)
          --> chưa tới giờ / stale / UNKNOWN / hết hạn mandate --> NO_TRADE, không gọi AI
          --> hết giờ không flatten; không chạy đồng hồ bảo vệ
          --> AUTONOMOUS paper OPEN local
          --> demo_dispatch: mặc định không POST; --place-orders --i-confirm-demo
              POST place/cancel/close + TPSL OPEN trong whitelist; live khóa
              GET order_detail sau gửi → PaperReconcile; cùng client_oid không POST lại
              UNKNOWN → paper_unknown
          trader/demo_kill_cli run --> hủy pending + flatten symbol whitelist; không qua AI

P1 paper protect (local only)
  trader/protect_clock_cli tick|loop --> trading/protect_clock.py
          --> fills → PaperReconcile; timeout/UNKNOWN không lệnh bù
          --> mark vs zone_risk → ZoneExecutor.on_risk_trigger dry-run một lần
          --> stale/thiếu mark: không bắn SL bịa; kill flatten một lần
          --> không gọi PaperAgent; không POST; không dùng interval quét

trader/bgapi.py::post()
        |
        +--> dry-run mặc định
        +--> live POST có hard guard; chưa có executor production
```

`preview -> execute -> sync` là luồng được mô tả trong [`spec/SPEC.md`](spec/SPEC.md), chưa được triển khai đầy đủ thành CLI/service production trong repo.

## 14. Cập nhật sổ tay

Cập nhật `COMPASS.md` cùng thay đổi khi có một trong các việc sau:

- thêm/bỏ/đổi tên module hoặc file điểm vào;
- đổi luồng gọi, dữ liệu, trạng thái hoặc trách nhiệm giữa các module;
- tính năng chuyển từ chưa có sang đã có, hoặc ngược lại;
- thay đổi quy tắc bảo mật, vận hành, kiểm thử hoặc tình trạng xác minh API;
- bổ sung/chốt spec khiến điểm bắt đầu hoặc thứ tự tra cứu đổi.

Không cần sửa sổ tay cho thay đổi nội bộ nhỏ nếu không làm đổi định vị, luồng, trạng thái hay hướng dẫn làm việc. Khi cập nhật, kiểm tra file tồn tại, trạng thái đúng với code và mọi liên kết markdown tương đối hoạt động.
