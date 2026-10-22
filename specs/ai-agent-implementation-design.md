# Thiết kế triển khai: AI Agent giao dịch có hạn mức

- Trạng thái: Dự thảo cập nhật theo mandate cấp vốn và mode AI tự chủ; chờ spec nghiệp vụ được duyệt
- Phạm vi thiết kế: P1 paper trading, P2 Demo trading và cổng sau cho `AUTONOMOUS_WITHIN_MANDATE`; chưa triển khai live
- Spec nguồn: [`ai-agent-autonomous-trading.md`](ai-agent-autonomous-trading.md)
- Ràng buộc: không gửi lệnh live, không dùng trade key thật, không cài dependency mới trong pha này

## 1. Mục tiêu triển khai đầu tiên

- Pha đầu vẫn xây pipeline paper/Demo với `PROPOSAL_ONLY` và `MANAGED_ZONE` để kiểm chứng contract, risk và recovery.
- Sau khi các cổng kỹ thuật đạt, thêm mode `AUTONOMOUS_WITHIN_MANDATE`: người dùng cấp vốn và mandate; AI được tự mở, quản lý, giảm và đóng vị thế trong allowlist, không cần người dùng mở zone trước.
- Mọi mode đều đi qua Risk Engine deterministic. Mode tự chủ chỉ thay đổi quyền khởi tạo cơ hội, không thay đổi hard limit, protective policy hoặc yêu cầu reconcile.
- Không có mode nào cho phép AI tự tăng vốn, nạp/chuyển margin, sửa mandate, mở rộng allowlist hoặc gọi Bitget ngoài executor.

Kết quả P1/P2 phải chứng minh được:

- provider lỗi hoặc output sai schema thì không tạo intent giao dịch;
- proposal hợp lệ nhưng vượt mandate bị từ chối;
- proposal được duyệt tạo intent có `decision_id`, `risk_check_id` và `client_oid` ổn định;
- timeout, partial fill, restart và reconcile không tạo lệnh trùng;
- chạm risk limit chuyển zone sang trạng thái dừng và chặn intent tăng rủi ro;
- toàn bộ quyết định và kết quả có audit event không lộ secret.

## 2. Quyết định kiến trúc

### 2.1 Giữ các lớp hiện có

- `ai_proposal/schema.py`: schema snapshot/proposal và Decimal validation.
- `ai_proposal/interface.py`: boundary adapter, bắt exception thành proposal rejected.
- `ai_proposal/validator.py`: deterministic hard-limit validator.
- `ai_proposal/store.py`: proposal log append-only.
- `executor/zone_executor.py`: local deterministic intent/state machine, idempotency và risk-stop intent.
- `executor/p1_adapter.py`: cầu lưu intent/event/snapshot vào SQLite.
- `trader/zone_store.py`: persistence zone/config/state.
- `trader/bitget_readonly.py`: adapter GET-only cho snapshot.

Không sửa `trader/bgapi.py` để thêm live dispatch trong pha này.

### 2.2 Bổ sung theo từng lớp

```text
ai_proposal/
  provider.py       # protocol provider, chưa biết Bitget
  provider_config.py# đọc config không lộ secret
  decision.py       # schema decision/order proposal mở rộng
  prompt.py         # dựng context ổn định và redacted
  adapter.py        # gọi provider, parse structured output, fallback NO_TRADE

trading/
  mandate.py        # immutable mandate/version và state
  mandate_store.py  # SQLite append-only version/event
  risk_engine.py    # pure deterministic checks, APPROVED/REJECTED/PAUSED/UNKNOWN
  order_intent.py   # mapping decision -> executor intent sau risk check
  reconcile.py      # boundary cho snapshot/order reconciliation
  audit.py          # event type và redaction/hash
```

Tên module là thiết kế đề xuất, chưa tạo file cho đến khi kế hoạch được duyệt để code.

## 3. Luồng xử lý chi tiết

### 3.1 Read phase

1. `bitget_readonly` hoặc paper source lấy market/account/position/orders.
2. Snapshot builder gắn `snapshot_at`, `feature_as_of`, freshness deadline và `mandate_version`.
3. Nếu snapshot không đủ, stale, hoặc zone đang `UNKNOWN/STOPPING`, ghi `DECISION_BLOCKED` và trả `NO_TRADE` nội bộ.

### 3.2 AI phase

1. Provider adapter nhận snapshot đã lọc, không nhận API key hoặc thông tin không cần thiết.
2. Prompt yêu cầu duy nhất một structured decision theo schema.
3. Response được parse bằng schema chặt, giới hạn độ dài và `valid_until`.
4. Provider exception, timeout, HTTP error, parse error hoặc schema mismatch đều tạo `NO_TRADE`/rejected record với mã ổn định.
5. Không retry gửi lệnh. Nếu retry gọi AI là cần thiết, chỉ retry phân tích trước khi có order intent và phải giới hạn số lần.

### 3.3 Risk phase

1. Decision validator kiểm tra field bất biến: mandate, symbol, state, snapshot id và mode tự chủ.
2. Risk Engine đọc mandate immutable và live snapshot mới nhất.
3. Kiểm tra freshness, allowlist, lot/tick, exposure, margin, granted capital, per-order risk, daily loss, drawdown, loss budget, loss streak, rate limit, loại lệnh và protective policy.
4. Nếu entry, DCA hoặc take-profit dùng market, từ chối; market chỉ hợp lệ khi là `reduce-only` strategic stop, emergency close hoặc kill switch theo mandate.
5. Với `PROPOSAL_ONLY`, không tạo order intent. Với `MANAGED_ZONE`, chỉ chấp thuận hành động trong zone đã mở. Với `AUTONOMOUS_WITHIN_MANDATE`, cho phép OPEN tạo zone/episode mới nếu symbol, side, vốn, exposure và giới hạn zone đều hợp lệ.
6. Kiểm tra `allow_average_down`; nếu false thì từ chối ADD/DCA. Nếu true thì kiểm tra DCA plan, remaining risk budget và không cấp lại budget đã dùng.
7. Khi daily loss hoặc loss streak đã chạm ngưỡng, trả `PAUSED` cho entry mới; chỉ cho phép reduce/close/protective action theo `daily_loss_action`.
8. Risk Engine trả `RiskCheckRecord` append-only.
9. Chỉ `APPROVED` mới được chuyển sang order intent.

### 3.4 Execution phase

1. `order_intent` tạo intent với `client_oid` deterministic từ `decision_id` và action.
2. Paper mode chỉ ghi intent và mô phỏng fill.
3. Demo mode sau cổng riêng mới gọi exchange dispatcher, nhưng vẫn phải giữ `dry_run` mặc định và guard rõ ràng.
4. Timeout hoặc response không xác định chuyển intent/zone sang `UNKNOWN`.
5. Reconcile đọc lại trạng thái sàn trước khi cho phép bất kỳ intent tăng rủi ro nào.

### 3.5 Audit phase

Ghi event theo thứ tự:

```text
SNAPSHOT_CAPTURED
AI_DECISION_RECEIVED
AI_DECISION_VALIDATED
RISK_CHECKED
ORDER_INTENT_CREATED
ORDER_DISPATCH_RESULT
RECONCILE_RESULT
STATE_TRANSITION
```

Payload dùng context hash và redaction, không lưu secret/raw authorization header.

## 4. Hợp đồng dữ liệu chính

### 4.1 Mandate

Mandate bất biến theo version, tối thiểu:

```text
mandate_id, version, zone_id, subaccount_id
ai_autonomy, granted_capital, capital_currency
allowed_symbols, allowed_sides, allowed_order_types
max_capital, max_exposure, max_margin, max_leverage
max_order_risk, loss_budget, daily_loss_limit, drawdown_limit
daily_loss_scope, drawdown_scope, drawdown_reference
max_consecutive_losses, loss_streak_scope, loss_streak_cooldown
daily_loss_action, allow_average_down
margin_mode, entry_order_type, dca_order_type, take_profit_order_type
strategic_stop_mode, emergency_order_type, kill_switch_order_type
max_open_positions, max_orders_per_window
require_protective_stop, mode, valid_from, valid_until, state
```

Quy tắc policy đã chốt cho P0:

- Các giá trị `granted_capital`, loss budget, per-order risk, daily loss, drawdown, leverage và allowlist là cấu hình theo mandate/zone, không hard-code một mức duy nhất.
- `granted_capital` là trần vốn AI được quản lý; không đồng nghĩa với mức lỗ tối đa và không được tự tăng. Margin, exposure và rủi ro mỗi lệnh được kiểm tra độc lập.
- Hệ thống được phép đề xuất giới hạn hoặc symbol dựa trên dữ liệu, nhưng người dùng phải xác nhận; đề xuất không tự trở thành policy hay allowlist.
- `ai_autonomy=AUTONOMOUS_WITHIN_MANDATE` cho phép AI khởi tạo zone/vị thế mới trong allowlist và vốn được cấp. `PROPOSAL_ONLY` chỉ ghi proposal; `MANAGED_ZONE` chỉ quản lý zone đã mở.
- `margin_mode` là `isolated`; người dùng tự thêm ký quỹ, hệ thống không tự nạp/chuyển/cấp thêm margin.
- Entry, DCA và take-profit dùng `limit`. Market chỉ dành cho `reduce-only` strategic stop khi được bật, emergency close và kill switch.
- Khi chạm zone loss limit hoặc daily loss limit, hủy entry/DCA, chặn tăng rủi ro và thực hiện `daily_loss_action` hoặc emergency policy tương ứng.
- Khi đạt `max_consecutive_losses`, chuyển `COOLDOWN`, chặn entry mới và chỉ khôi phục sau thời gian/phê duyệt được mandate quy định. Không reset loss streak bằng cách đổi symbol, zone hoặc model.
- `allow_average_down=false` mặc định theo hướng an toàn; khi bật phải có DCA plan và risk budget riêng.
- Không gồng lệnh: không được nới SL theo hướng tăng rủi ro, tăng size để bù lỗ hoặc tạo lệnh mới để gỡ lệnh đang lỗ.
- Khi zone đã bắt đầu, config là bất biến; thay đổi phải tạo version mới cho episode mới.

`daily_loss_scope`, `drawdown_scope` và `drawdown_reference` phải được lưu rõ trong mandate. Nếu chưa được xác định, mandate không được chuyển sang trạng thái có thể tạo intent tăng rủi ro. `max_leverage` và các trường vốn/risk bắt buộc cũng phải có giá trị hợp lệ trước P2 Demo. Mặc định của thiết kế là không cho thực thi khi các trường này còn `TBD`, không tự suy diễn giá trị an toàn.

### 4.2 Decision

Giữ schema proposal P3 làm nền, bổ sung hoặc ánh xạ rõ:

```text
decision_id, opportunity_id, mandate_id, mandate_version
symbol, side, action, order_type, quantity, limit_price
stop_loss, take_profit, thesis, risk_factors, confidence
valid_until, provider, model, model_version, prompt_version
```

Không dùng `confidence` làm hard gate duy nhất. Không chấp nhận action ngoài enum đã duyệt.

### 4.3 RiskCheckRecord

```text
risk_check_id, decision_id, mandate_id, snapshot_id
result, reason_codes, checked_at, policy_version
observed_limits, proposed_delta, protective_order_status
```

`observed_limits` chỉ ghi số liệu đã redaction và đủ để audit, không ghi credential.

### 4.4 OrderIntent

Tái sử dụng record `OrderIntent` của `executor/zone_executor.py`, bổ sung metadata bắt buộc:

```text
source=ai_agent
 decision_id
risk_check_id
mandate_id
mandate_version
paper_or_demo
```

Tên field và serialization phải tương thích với `P1IntegrationStore`.

## 5. Provider adapter

Dùng interface provider-agnostic:

```python
class AIProvider(Protocol):
    def decide(self, request: DecisionRequest) -> ProviderResponse: ...
```

`ProviderConfig` chỉ giữ metadata cấu hình và secret reference. API key đọc từ environment/secret store tại boundary, không truyền vào prompt, không đưa vào exception message và không ghi vào log.

MVP cho phép hai implementation độc lập:

- Gemini native adapter.
- OpenAI-compatible adapter nhận `base_url`, `api_key`, `model`.

Provider adapter chỉ tạo decision, không được gọi Bitget, không được tạo `OrderIntent`, không được sửa mandate và không được tự retry exchange request. Việc chọn SDK/client cụ thể và dependency cần được duyệt riêng trước khi cài.

## 6. State và persistence

- Mandate version, risk check, decision và order intent phải có idempotency key.
- Event log append-only; snapshot/materialized state có thể upsert nhưng phải truy được event nguồn.
- Restart phải load mandate/state/intent pending trước khi gọi AI hoặc tạo intent mới.
- Khi tồn tại intent `UNKNOWN`, không tạo intent mới cho cùng logical action.
- Reconcile result phải phân biệt `confirmed_open`, `confirmed_absent`, `partial`, `unknown`.
- Zone risk ledger tiếp tục theo `specs/zone-risk-policy.md`; không cấp lại budget sau partial close.

## 7. Pha triển khai tuần tự

### Bước 1: Chốt contract nội bộ

Tạo test trước cho mandate, decision, risk result, reason codes và mapping action. Không gọi network.

### Bước 2: Mandate và risk facade

Thêm immutable mandate/store và facade gọi validator hiện có cùng risk policy. Bảo đảm mọi đường tạo intent đều cần `RiskCheckRecord(APPROVED)`.

### Bước 3: Paper agent adapter

Thêm provider protocol và fake provider cho test. Nối snapshot -> decision -> validator -> risk -> dry-run intent. Provider thật chưa được gọi trong test.

### Bước 4: Persistence và recovery

Lưu decision/risk/order events vào SQLite bridge, khôi phục pending/unknown sau restart và kiểm thử idempotency.

### Bước 5: Bitget Demo boundary

Chỉ sau khi P1 đạt, thiết kế dispatcher Demo riêng, xác minh API semantics bằng tài khoản Demo theo yêu cầu rõ. Không dùng `GROK_TRADER_ALLOW_LIVE` và không mở live.

### Bước 6: Shadow và đánh giá

Chạy proposal-only/shadow, ghi decision opportunities, so sánh baseline deterministic và đánh giá ngoài mẫu. Chưa cấp quyền live cho AI.

## 8. Ma trận test tối thiểu

### Contract và provider

- Output hợp lệ tạo decision đúng Decimal và timestamp.
- JSON thiếu field, thêm field, sai enum hoặc hết hạn bị từ chối.
- Timeout/provider error/rate limit tạo no-trade, không tạo intent.
- API key không xuất hiện trong log, exception hoặc audit payload.

### Risk và mandate

- Symbol/side/order type ngoài allowlist bị từ chối.
- Quantity, exposure, leverage, daily loss, loss budget vượt ngưỡng bị từ chối.
- Mandate hết hạn/revoked/paused không tạo intent.
- `PROPOSAL_ONLY` không tạo intent; `MANAGED_ZONE` từ chối mở zone chưa có; `AUTONOMOUS_WITHIN_MANDATE` chỉ cho mở khi còn vốn/exposure và policy hợp lệ.
- Đạt daily loss hoặc `max_consecutive_losses` chuyển `COOLDOWN`/`PAUSED`, chặn entry nhưng vẫn xử lý reduce/close/protective action.
- `allow_average_down=false` chặn ADD/DCA; khi bật, DCA vượt risk budget bị từ chối.
- Zone `UNKNOWN`, `STOPPING`, kill switch hoặc stale snapshot chặn tăng rủi ro.
- Protective stop thiếu khi mandate bắt buộc bị từ chối.

### Execution và recovery

- Cùng decision retry cho cùng `client_oid` không tạo intent thứ hai.
- Timeout sau dispatch chuyển `UNKNOWN` và buộc reconcile.
- Partial fill cập nhật đúng remaining quantity.
- Restart không làm mất pending/unknown hoặc cấp lại loss budget.
- Risk stop tạo cancel/emergency-close intent đúng một lần.

## 9. Điều kiện chuyển bước

- Không chuyển P1 sang P2 nếu còn test không giải thích về idempotency, unknown state, risk rejection hoặc audit.
- Không chuyển P2 sang live nếu chưa có Demo evidence cho partial fill, timeout, reconnect, reduce-only, protective stop và reconcile.
- Không cho AI tự mở rộng mandate hoặc tự bật live.
- Mọi thay đổi provider hoặc model phải tạo version và kiểm thử lại contract/schema; không thay provider giữa một episode đang chạy.

## 10. Phạm vi file dự kiến

### Pha contract/risk/paper

- `ai_proposal/schema.py`
- `ai_proposal/validator.py`
- `ai_proposal/interface.py`
- `ai_proposal/provider.py` mới
- `ai_proposal/decision.py` mới hoặc mở rộng schema hiện có
- `trading/mandate.py` mới
- `trading/risk_engine.py` mới
- `trading/order_intent.py` mới
- `executor/p1_adapter.py`
- test mới tương ứng trong `tests/` hoặc thư mục test hiện có

### Không sửa trong pha đầu

- `trader/bgapi.py` để bật live POST.
- `monitor.py` để gửi lệnh.
- `spec/SPEC.md` vì đây là hướng nghiệp vụ khác.
- Dependency lock/package files nếu chưa được duyệt.

Nếu cần thêm file ngoài danh sách, phải dừng và báo phạm vi trước khi sửa.
