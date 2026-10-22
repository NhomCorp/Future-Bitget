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
| AI Agent tự giao dịch có hạn mức | [`specs/ai-agent-autonomous-trading.md`](specs/ai-agent-autonomous-trading.md) | [`specs/ai-agent-implementation-design.md`](specs/ai-agent-implementation-design.md), `specs/zone-risk-policy.md`, `ai_proposal/`, `executor/`, [`trading/mandate_store.py`](trading/mandate_store.py), [`trading/reconcile.py`](trading/reconcile.py) | Dự thảo cập nhật theo hướng người dùng cấp vốn và AI tự chủ trong mandate; P1 Bước 4 local (restart/reconcile/budget) **đã có**; các mode, hạn mức cụ thể, Demo và live vẫn chờ duyệt/xác minh riêng |
| Giao diện, output, CLI | Các `main()`/script liên quan; [`README.md`](README.md); [`frontend/`](frontend/); [`package.json`](package.json); [`trader/equity_cli.py`](trader/equity_cli.py); [`trader/demo_verify_cli.py`](trader/demo_verify_cli.py) | [`specs/frontend-local.md`](specs/frontend-local.md) mục 8 IA, [`specs/manual-risk-settings.md`](specs/manual-risk-settings.md), [`specs/demo-verification-checklist.md`](specs/demo-verification-checklist.md) | CLI package thống nhất: **chưa có**; frontend local Demo/dry-run: **đã có**, một HTML nhiều view hash, `npm start` cổng `3007`; Cấu hình AI (provider/model/timeout, version riêng; Gemini nhiều key ngang hàng, bốc ngẫu nhiên; OpenAI-compatible một key; key hiện rõ trên form; Check live ping provider, dòng kết quả gần nhất không chứa key) tách khỏi Quyền AI; Mandate và Quyền AI là hai màn, cùng policy object; Tổng quan mock local (ticker nhập tay, phiếu intent, tab rỗng, không chart); Kết nối: status Demo/env đủ-thiếu (`GET /api/connect-status`), không form secret, GET Bitget chưa nối; Phong cách/Nhật ký: stub; equity CLI GET-only: **đã có**; DemoVerify CLI: **đã có** (GET mặc định; POST D5-D6 cần `--place-orders --i-confirm-demo`); frontend production: **chưa có** |
| Tài khoản và vị thế read-only | [`bg.py`](bg.py), [`monitor.py`](monitor.py), [`trader/equity_cli.py`](trader/equity_cli.py), [`trader/demo_verify_cli.py`](trader/demo_verify_cli.py) | [`trader/bgapi.py`](trader/bgapi.py), [`trader/bitget_readonly.py`](trader/bitget_readonly.py), [`trader/demo_verify.py`](trader/demo_verify.py) | Đã có script đọc, monitor, snapshot equity GET-only và harness DemoVerify; không phải executor/dispatcher |
| Bitget API và trader | [`trader/bgapi.py`](trader/bgapi.py) | [`trader/ta.py`](trader/ta.py), `spec/SPEC.md` | Có helper và dry-run; giao dịch live chưa được nghiệm thu |
| Ladder, chiến lược, risk | [`planner/ladder.py`](planner/ladder.py) | [`planner/PLAN.md`](planner/PLAN.md), `spec/SPEC.md` | Đối chiếu công thức và backtest trước khi đổi tham số |
| Dữ liệu và backtest | [`backtest/simulator.py`](backtest/simulator.py) | [`backtest/run_backtest.py`](backtest/run_backtest.py), `planner/` | Nghiên cứu; không phải bằng chứng lợi thế hoặc an toàn live |
| TA và mức giá | [`trader/ta.py`](trader/ta.py), [`trader/snap.py`](trader/snap.py) | `spec/SPEC.md` | TA là bộ lọc rủi ro, không phải dự báo |
| Journal, audit, PnL và profile phong cách | [`journal/journal.py`](journal/journal.py) | [`journal/style_digest.py`](journal/style_digest.py), [`profile/user_style.yaml`](profile/user_style.yaml), [`specs/user-style-profile.md`](specs/user-style-profile.md) | Giữ lịch sử append-oriented; profile người dùng tách khỏi digest tự rút và không được chứa hard limits |
| Vận hành monitor | [`monitor.py`](monitor.py) | `journal/journal.py`, `README.md` | Có state cục bộ và journal hook; watcher production chưa có |
| Zone risk policy và xác minh Demo | [`specs/zone-risk-policy.md`](specs/zone-risk-policy.md) | [`specs/demo-verification-checklist.md`](specs/demo-verification-checklist.md), [`trader/demo_verify.py`](trader/demo_verify.py), [`trader/demo_verify_cli.py`](trader/demo_verify_cli.py), [`trader/zone_risk.py`](trader/zone_risk.py), [`trader/zone_state.py`](trader/zone_state.py), [`trader/zone_store.py`](trader/zone_store.py), [`executor/zone_executor.py`](executor/zone_executor.py), [`ai_proposal/validator.py`](ai_proposal/validator.py), [`trading/`](trading/) | Risk policy đang ở bản dự thảo cập nhật cho mandate và AI tự chủ; Demo 2026-10-22 `BTCUSDT` D0–D6 PASS (`isolated`, `hedge_mode`; D5 limit FOUND, D6 cancel `canceled`); D7–D15 chưa chạy; chưa có dispatcher hoặc live |
| Bảo mật | [`trader/bgapi.py`](trader/bgapi.py), [`trader/envfile.py`](trader/envfile.py) | [`README.md`](README.md), [`.env.example`](.env.example), `CLAUDE.md` | Key local điền vào `.env` (gitignored) hoặc OS env; không lộ key; live POST guard không được bỏ qua |
| Kiểm thử | File test liên quan, hiện có [`planner/test_sim.py`](planner/test_sim.py), [`tests/test_recovery.py`](tests/test_recovery.py) | File module được sửa | Chọn kiểm tra hẹp theo thay đổi; không cài gói khi chưa duyệt |

## 3. Spec và quyết định nghiệp vụ

| Tài liệu | Trạng thái | Dùng khi |
|---|---|---|
| [`spec/SPEC.md`](spec/SPEC.md) | Đặc tả kỹ thuật cho công cụ DCA-ladder bán tự động, Wide/Scalp, CLI preview/execute/sync/cancel/kill/status/ta/journal; có giả định Cross margin và ràng buộc risk. | Sửa ladder hiện tại, lệnh, risk, API hoặc luồng công cụ theo đặc tả này. |
| [`specs/zone-auto-trade-ai-plan.md`](specs/zone-auto-trade-ai-plan.md) | Dự thảo định hướng bot theo mandate cấp vốn, zone loss-budget, isolated margin, ledger và các cổng AI. Policy P0 cũ đã được cập nhật thành bản dự thảo thống nhất với mode AI tự chủ; các con số vận hành, Demo semantics và live vẫn chưa chốt. | Nghiên cứu hoặc soạn spec cho hướng zone/AI; không triển khai nghiệp vụ còn mở. |
| [`planner/PLAN.md`](planner/PLAN.md) | Kế hoạch/kết quả nghiên cứu planner, không thay thế spec sản phẩm. | Sửa hoặc diễn giải nghiên cứu chiến lược. |
| [`specs/project-compass.md`](specs/project-compass.md) | Spec đã duyệt cho la bàn ban đầu. | Tham khảo nguồn gốc phạm vi sổ tay. |
| [`specs/project-handbook.md`](specs/project-handbook.md) | Spec đã duyệt cho sổ tay và rule riêng repo. | Tham khảo mục tiêu/tiêu chí của tài liệu này. |

Nếu hai spec xung đột, nêu rõ xung đột và hỏi chủ dự án trước khi sửa code phụ thuộc vào quyết định đó. Không tự chuyển Cross margin thành isolated margin hoặc ngược lại. Mục tiêu lợi nhuận/backtest trong tài liệu không phải cam kết.

## 4. Giao diện và điểm vào

### Đã có

- [`bg.py`](bg.py): đọc account và positions qua Bitget v2, xuất JSON.
- [`monitor.py`](monitor.py): lấy account, positions, lệnh chờ/plan; so sánh `state.json`, in cảnh báo/thay đổi và gọi hook journal sync.
- Các script planner/backtest có entrypoint riêng.
- [`frontend/`](frontend/): frontend local-only Demo/dry-run, một HTML nhiều view theo hash (`#/cau-hinh-ai`, `#/mandate`, `#/quyen-ai`, `#/ban-zone`, …). Nav: Kết nối, Cấu hình AI, Mandate, Quyền AI, Phong cách, Tổng quan, Bàn zone, Nhật ký. Dữ liệu lưu local storage schema v4, không gọi Bitget. Khởi động `npm start` ([`package.json`](package.json), [`frontend/server.js`](frontend/server.js)), cổng `3007`, chỉ nghe `127.0.0.1`. Cấu hình AI lưu object `agentConfig` riêng (provider/model/timeout/key); đổi provider/model/key tạo agent-config version, không đụng version mandate. Gemini: nhiều key ngang hàng, mỗi key một nhãn, `gemini_key_strategy=random`; OpenAI-compatible: một `api_key`. Key hiện rõ trên form, lưu localStorage máy này; notice/log không in giá trị. Nút Check live ping provider qua `POST /api/ai-check` (hoặc gọi thẳng nếu proxy chưa có); dòng kết quả gần nhất lưu local, không chứa key; không phải đường giao dịch. Trang Kết nối đọc `GET /api/connect-status`: Demo/dry-run và env đủ/thiếu, không form secret, không in giá trị key. GET Bitget chưa nối. Key Bitget không nhập trên web. Mandate nhập khẩu vị; Quyền AI chọn 3 mode trên trang riêng, vẫn cùng policy object, đổi mode tạo version mới. Bàn zone: preview/status/sync; thiếu policy thì không tạo zone. Tổng quan mock: ticker last/mark/funding nhập tay, phiếu intent không POST, tab vị thế/lệnh/tài sản rỗng; equity local chưa có thì để trống, không bịa số sàn. Phong cách, Nhật ký đang stub. Daily/drawdown/streak trên frontend chưa tính từ equity thật. CLI/paper có thể gắn features từ snapshot GET khi sổ equity local đủ `day_start`. `AUTONOMOUS_WITHIN_MANDATE` chỉ lưu cấu hình, không tự giao dịch.

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
| [`trader/bitget_readonly.py`](trader/bitget_readonly.py) | GET-only Bitget adapter, Demo header `paptrading: 1`, cấm live; transport injectable cho test. Nạp `.env` local khi không truyền `environ`. |
| [`trader/envfile.py`](trader/envfile.py) | Đọc `.env` local vào process env; không ghi đè biến đã có; không log giá trị. |
| [`trader/equity_cli.py`](trader/equity_cli.py) | CLI local `snapshot` đọc equity Demo GET-only, in bản đã redaction; bắt buộc `--max-age-seconds`; không dump raw account, không tạo intent. |
| [`trader/demo_verify.py`](trader/demo_verify.py) | Harness checklist Demo D0-D15: GET baseline, POST Demo có khóa, redaction, phân loại `FOUND`/`REJECTED`/`VERIFIED_NOT_RECEIVED`/`UNKNOWN`. Không phải dispatcher. |
| [`trader/demo_verify_cli.py`](trader/demo_verify_cli.py) | CLI `run --symbol`; mặc định GET-only; POST D5-D6 cần `--place-orders --i-confirm-demo`; cấm live và `GROK_TRADER_ALLOW_LIVE`; ghi evidence JSONL đã redaction. |
| [`trader/zone_store.py`](trader/zone_store.py) | P1 SQLite durable zone config/state, observations and append-only audit events. |
| [`trader/zone_cli.py`](trader/zone_cli.py) | P1 local `preview`, `status`, `sync` mock/dry-run entrypoint; never sends exchange requests. |
| [`trader/ta.py`](trader/ta.py) | Tính indicator, key levels và ladder risk. |
| [`executor/zone_executor.py`](executor/zone_executor.py) | P2 local-only deterministic entry/DCA/cancel/emergency-close intent state machine; `restore`/`load_zone` đọc lại pending/unknown từ SQLite sau restart; no exchange dispatcher. |
| [`executor/p1_adapter.py`](executor/p1_adapter.py) | P1 SQLite bridge for P2 intents/events/snapshots, paper intent runtime, mandate versions, paper budget events and P3 proposal audit events; no order dispatch. |
| [`ai_proposal/schema.py`](ai_proposal/schema.py) | P3 immutable decision snapshot, proposal and validation record schemas. |
| [`ai_proposal/validator.py`](ai_proposal/validator.py) | P3 deterministic hard-limit validator; accepted/rejected result only. |
| [`ai_proposal/interface.py`](ai_proposal/interface.py) | P3 model/provider-agnostic proposal boundary; no model/network call. |
| [`trading/mandate.py`](trading/mandate.py) | Paper mandate immutable: vốn cấp, 3 mode AI, daily loss/action, chuỗi lỗ/cooldown, drawdown, leverage, isolated/limit policy. Thiếu field hoặc TBD chặn tăng rủi ro. `AUTONOMOUS_WITHIN_MANDATE` fail-closed, chưa thực thi. |
| [`trading/risk_engine.py`](trading/risk_engine.py) | Deterministic proposal-to-mandate check; validates loss budget, order risk, leverage, isolated margin, limit/market reduce-only, daily loss, drawdown, loss streak và `allow_average_down`; no dispatch. AUTONOMOUS chặn intent tăng rủi ro. Thiếu/stale equity chặn intent tăng rủi ro. |
| [`trading/equity_store.py`](trading/equity_store.py) | Sổ SQLite append-only cho số equity đã parse; không lưu secret hay raw response. |
| [`trading/equity_snapshot.py`](trading/equity_snapshot.py) | Builder GET-only: `day_start_equity` = snapshot cuối trước 00:00 UTC, daily_loss/drawdown local; thiếu/stale thì không bịa số. PaperAgent không gọi module này. |
| [`trading/paper_agent.py`](trading/paper_agent.py) | Paper pipeline: `PROPOSAL_ONLY` chỉ ghi proposal; `MANAGED_ZONE` tạo paper intent OPEN/CLOSE/REDUCE; AUTONOMOUS bị chặn. Restart nạp pending/unknown trước khi tạo intent mới; cùng `client_oid` không tạo bản thứ hai; `UNKNOWN` bắt reconcile. `EMERGENCY_FLATTEN` gọi executor dry-run một lần. Không gọi sàn. Caller gắn features equity trước `run()`. |
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
| [`journal/style_digest.py`](journal/style_digest.py) | Tạo digest thời lượng, equity và size từ journal. |
| [`profile/report.md`](profile/report.md) | Báo cáo profile hiện có. |
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
- P1 paper agent: mandate có vốn/mode AI, risk fail-closed, paper intent OPEN/CLOSE/REDUCE, `PROPOSAL_ONLY` không tạo intent, AUTONOMOUS bị khóa; không gọi exchange.
- P1 Bước 4 local: khôi phục mandate/paper intent/executor pending-unknown sau restart, reconcile paper (`confirmed_open`/`confirmed_absent`/`partial`/`unknown`), idempotent `client_oid`, sổ loss-budget không cấp lại. Chưa phải reconcile sàn.
- Equity GET-only: adapter → builder features (`day_start`/`daily_loss`/`drawdown`) → CLI local; thiếu sổ ngày trước hoặc stale thì không tăng rủi ro. Chưa phải trigger production và chưa xác minh Demo.
- DemoVerify harness: CLI GET-only mặc định; POST Demo D5-D6 chỉ khi có `--place-orders --i-confirm-demo`; mock đã cover FOUND/REJECTED/UNKNOWN/VERIFIED_NOT_RECEIVED. Demo 2026-10-22 `BTCUSDT`: D0–D6 PASS (`isolated`, `hedge_mode`; D5 `FOUND`, D6 `canceled`). D7–D15 chưa chạy.
- `trader/bgapi.py` có chế độ dry-run và guard cho live POST.

### Chưa có hoặc chưa nghiệm thu

- Executor production và watcher lệnh production.
- Zone state machine và ledger giới hạn lỗ production/reconcile: chưa có; P1 chỉ lưu state/observation local và stop intent dry-run.
- Dispatcher exchange, WebSocket reconcile production và phục hồi theo trạng thái sàn sau restart/reconnect. Phục hồi local SQLite (paper/executor) đã có.
- Kill workflow production đã được kiểm thử đầy đủ.
- AI proposal có schema/validator/log và P1 paper pipeline, nhưng chưa có model training/evaluation, provider API thật, Demo dispatcher hoặc AI-to-exchange execution. Harness DemoVerify không phải dispatcher.
- Triển khai live được nghiệm thu.
- Tailscale gateway.

Không chạy lệnh thay đổi trạng thái tài khoản, gửi lệnh, deploy hoặc thao tác vận hành có tác động bên ngoài khi chưa được chủ dự án yêu cầu rõ. `zone_loss_limit` là ngưỡng điều khiển, không phải bảo đảm lỗ thực tế tuyệt đối.

## 10. Bảo mật và an toàn

- Không in/ghi secret, token, mật khẩu, API key, signature/header ký hoặc dữ liệu tài khoản thật vào output, log, test hoặc tài liệu.
- Key Bitget Demo điền vào [`.env`](.env) (gitignored). Bản mẫu: [`.env.example`](.env.example). Không commit `.env`.
- Key AI của frontend local nhập trên trang Cấu hình AI, hiện rõ trên form, lưu localStorage máy này; không in giá trị vào notice/log. Check live được phép gọi AI provider. Không dùng trang web để nhập trade key Bitget.
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

Nguồn định hướng là [`specs/zone-auto-trade-ai-plan.md`](specs/zone-auto-trade-ai-plan.md) và [`specs/ai-agent-autonomous-trading.md`](specs/ai-agent-autonomous-trading.md). Ba mode AI đã có trên mandate/frontend/paper: `PROPOSAL_ONLY`, `MANAGED_ZONE`, `AUTONOMOUS_WITHIN_MANDATE`. Mode tự chủ **fail-closed**, chưa được phép mở vị thế.

Không dùng số P lẫn giữa spec sản phẩm, cổng AI và code. Cổng đã làm: `LocalContract` + `PaperModes` + `ReadonlyEquity` + `LocalRecovery` + harness `DemoVerify` + Demo D0–D6. Cổng chưa đóng: Demo D7–D15, `DemoDispatch`, `Shadow`.

- Risk engine thuần hàm và lifecycle khô local cho zone: **đã có, chưa nối sàn**.
- Zone store SQLite append-oriented lưu config bất biến, state, observation và audit event; CLI local có `preview/status/sync` mock/dry-run.
- Adapter Bitget chỉ GET, dùng read-only env vars; **đã nối** CLI equity + builder features cho risk/paper (caller gắn tay) và harness DemoVerify. **Chưa nối** frontend. Field `accountEquity` theo contract test local, **chưa xác minh** trên tài khoản Demo.
- Executor, state machine bền vững theo dữ liệu sàn, reconcile WebSocket và loss-budget ledger production: **chưa có**.
- Decision opportunity dataset: **chưa có**.
- Paper agent dùng `ai_proposal/provider.py` với provider protocol/fake; pipeline lưu decision/risk/paper intent qua `executor/p1_adapter.py`, nạp lại sau restart bằng `trading/mandate_store.py` và quan sát local bằng `trading/reconcile.py`; không gọi exchange.
- AI training/evaluation pipeline và provider API thật: **chưa có**.
- Demo dispatcher, AI tự gửi lệnh lên sàn và live trading: **chưa có**. Harness `demo_verify` chỉ ghi evidence; không phải đường thực thi AI.
- Tailscale gateway: **chưa có**.

P0 không gửi/cancel lệnh. Adapter GET-only đã nối CLI equity và harness DemoVerify (GET mặc định). Harness đã POST Demo D5–D6 (`BTCUSDT` 2026-10-22, không phải dispatcher). Trước dispatcher Demo phải có bằng chứng D0-D10 trên tài khoản Demo, idempotency, persistence/restart, reconcile và lệnh bảo vệ.

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
                    +--> trader/demo_verify.py --> checklist D0-D15, evidence đã redaction
                    |         POST D5-D6 chỉ khi --place-orders --i-confirm-demo
                    |
                    frontend không gọi nhánh này

frontend local
  GET /api/connect-status --> env đủ/thiếu, không nối Bitget

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
          PaperAgent không tạo client_oid mới khi intent đã có hoặc đang UNKNOWN

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
