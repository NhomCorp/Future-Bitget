# Spec: AI Agent tự phân tích và giao dịch có hạn mức

- Trạng thái: Đã duyệt định hướng; thông số hạn mức cụ thể và triển khai live vẫn chờ chốt/phê duyệt riêng
- Thiết kế triển khai: [`ai-agent-implementation-design.md`](ai-agent-implementation-design.md)
- Phạm vi: Thiết kế nghiệp vụ cho AI Agent giao dịch Bitget USDT-M Futures trong hạn mức được cấp
- Không phải giấy phép bật live: mọi triển khai thực tế phải đi qua các cổng Demo, paper trading, shadow và live vốn nhỏ
- Tài liệu liên quan: `specs/zone-risk-policy.md`, `specs/zone-auto-trade-ai-plan.md`

## 1. Mục tiêu

Xây dựng một AI Agent có thể tự thu thập dữ liệu, phân tích cơ hội, tạo quyết định và gửi lệnh giao dịch Bitget trong một phạm vi quyền hạn cố định do chủ tài khoản cấp. Agent được tự chủ về thời điểm và hành động giao dịch trong phạm vi đó, nhưng không được tự tăng ngân sách, nới rủi ro, thay đổi policy hoặc truy cập quyền ngoài giao dịch.

Mục tiêu của hệ thống là kiểm soát được quyền hạn, rủi ro, trạng thái lệnh và khả năng truy vết của từng quyết định. Hệ thống không cam kết lợi nhuận và không coi dự đoán của AI là bảo đảm kết quả.

## 2. Phạm vi

### 2.1 Trong phạm vi

- Kết nối dữ liệu thị trường Bitget qua REST và WebSocket khi phù hợp.
- Phân tích nhiều symbol, timeframe và vị thế đang mở trong allowlist.
- Gọi AI provider được cấu hình bởi người dùng:
  - Gemini native hoặc endpoint tương thích OpenAI.
  - OpenAI-compatible với `base_url`, `api_key`, `model`.
- Tạo quyết định có cấu trúc: `no_trade`, mở vị thế, tăng vị thế theo plan, giảm vị thế, đóng vị thế hoặc quản lý lệnh bảo vệ.
- Kiểm tra quyết định qua Risk Engine deterministic trước khi gửi lệnh.
- Gửi, theo dõi, hủy hoặc điều chỉnh lệnh trong quyền hạn được cấp.
- Reconcile trạng thái giữa hệ thống và Bitget sau restart, timeout, mất kết nối hoặc partial fill.
- Ghi audit log append-only cho dữ liệu, prompt context, phiên bản model, quyết định, kiểm tra risk và kết quả lệnh.
- Paper trading và Demo trading trước live.

### 2.2 Ngoài phạm vi MVP

- Tự mở zone hoặc tự cấp thêm ngân sách.
- Tự nạp, rút hoặc chuyển margin.
- Quyền withdrawal trên API key Bitget.
- Tự thay đổi model, provider, policy, risk limit hoặc allowlist khi đang chạy.
- Tự sửa hoặc xóa audit log.
- Tự giao dịch ngoài symbol, side, leverage, margin mode hoặc timeframe được cấp.
- Tự triển khai code, thay secret hoặc thay quyền hệ thống.

## 3. Mô hình quyền hạn của Agent

Agent được cấp một `trading mandate` bất biến cho mỗi episode hoặc zone. Mandate gồm:

- `mandate_id`, `version`, thời điểm bắt đầu và hết hạn.
- Subaccount được phép sử dụng.
- Symbol và side được phép.
- Chế độ margin và leverage tối đa.
- Vốn tối đa được cấp cho mandate.
- Exposure và margin tối đa.
- Rủi ro tối đa cho mỗi lệnh.
- Tổng loss budget của zone hoặc episode.
- Lỗ tối đa trong ngày và trong chu kỳ mandate.
- Số vị thế mở và số lệnh tối đa.
- Tốc độ đặt lệnh tối đa theo khoảng thời gian.
- Loại lệnh được phép.
- Bắt buộc có stop-loss, take-profit hoặc emergency policy theo chế độ đã chọn.
- Thời gian không được giao dịch, nếu có.
- Trạng thái `enabled`, `paused`, `stopping`, `expired`, `revoked`.

Các giá trị trên do người dùng hoặc policy đã duyệt đặt trước. Agent chỉ được đọc, không được ghi hoặc nới chúng. Thay đổi mandate phải tạo version mới và áp dụng cho episode mới, không sửa đè mandate đang chạy.

## 4. Nguyên tắc risk bắt buộc

1. Mọi lệnh từ AI phải đi qua Risk Engine trước khi gọi Bitget.
2. Risk Engine không phụ thuộc vào câu trả lời tự do của AI và không dùng AI để quyết định hard limit.
3. Khi dữ liệu giá, số dư, vị thế hoặc trạng thái lệnh bị thiếu hoặc quá cũ, hệ thống không được mở thêm rủi ro.
4. Khi chạm hard limit, hệ thống hủy entry/DCA chưa khớp, chặn lệnh làm tăng size và chạy emergency policy đã duyệt.
5. Khi không xác nhận được trạng thái sau khi gửi lệnh, chuyển sang `UNKNOWN`, không gửi lệnh bù hoặc lệnh mới dựa trên giả định.
6. Không cấp lại loss budget sau khi giảm size hoặc đóng một phần.
7. Không coi loss limit là cam kết lỗ thực tế tuyệt đối. Gap, slippage, phí, funding, lỗi sàn và thanh lý có thể làm vượt ngưỡng.
8. API Bitget chỉ được cấp quyền đọc và trade, tắt withdrawal. Secret chỉ tồn tại ở backend hoặc secret store.
9. Có kill switch độc lập với AI. Kill switch phải chặn lệnh tăng rủi ro và kích hoạt quy trình xử lý đã duyệt.

Risk theo zone dùng định nghĩa trong `specs/zone-risk-policy.md`, gồm loss budget, stop theo mark price, phí, funding, trạng thái `STOPPING` và `UNKNOWN`.

## 5. Kiến trúc và luồng dữ liệu

```text
Bitget REST/WebSocket
        ↓
Market Data + Account/Position Snapshot
        ↓
Feature Builder + Data Freshness Check
        ↓
AI Agent Planner
        ↓
Structured Decision Validator
        ↓
Deterministic Risk Engine
        ↓
Order Executor với clientOid idempotent
        ↓
Bitget
        ↓
Reconciler + Position Monitor + Append-only Journal
```

### 5.1 AI Provider Adapter

Ứng dụng dùng interface chung, không để logic giao dịch phụ thuộc vào một provider cụ thể.

Cấu hình tối thiểu:

```text
provider: gemini | openai_compatible
base_url: tùy chọn theo provider
api_key: secret, không ghi log
model: tên model
request_timeout: giới hạn thời gian
max_output_tokens: giới hạn đầu ra
```

Adapter phải hỗ trợ structured output hoặc cơ chế parse và validate schema tương đương. Nếu provider lỗi, timeout, trả schema không hợp lệ hoặc bị giới hạn tốc độ, quyết định mặc định là `NO_TRADE`, không tự retry lệnh giao dịch.

### 5.2 Agent loop

Mỗi chu kỳ Agent:

1. Đọc snapshot thị trường, account, position, orders và mandate hiện tại.
2. Kiểm tra freshness, tính toàn vẹn và trạng thái reconcile.
3. Tính indicator và feature theo timestamp dữ liệu thực tế.
4. Gửi context tối thiểu cần thiết cho AI.
5. Nhận một quyết định có schema cố định.
6. Validate schema, mandate và thời hạn quyết định.
7. Gửi decision tới Risk Engine.
8. Chỉ khi Risk Engine chấp thuận mới tạo order intent.
9. Executor gửi lệnh idempotent.
10. Reconcile kết quả, cập nhật ledger và ghi audit event.

Agent không được tự gọi endpoint Bitget tùy ý. Agent chỉ được yêu cầu các tool nội bộ đã allowlist như `read_market_snapshot`, `read_account_state`, `propose_order`, `request_reduce`, `request_close` và `cancel_pending_order`. Các tool gửi lệnh phải tự gọi Risk Engine, không tin vào việc Agent đã tự kiểm tra.

## 6. Schema quyết định tối thiểu

```json
{
  "decision_id": "uuid",
  "mandate_id": "id",
  "symbol": "BTCUSDT",
  "action": "NO_TRADE|OPEN_LONG|OPEN_SHORT|ADD|REDUCE|CLOSE|CANCEL",
  "order_type": "MARKET|LIMIT|NONE",
  "quantity": "decimal",
  "limit_price": "decimal|null",
  "stop_loss": "decimal|null",
  "take_profit": "decimal|null",
  "thesis": ["string"],
  "risk_factors": ["string"],
  "confidence": 0.0,
  "valid_until": "ISO-8601 timestamp"
}
```

Quy tắc schema:

- `quantity`, giá và phần trăm phải parse bằng Decimal, không dùng số thực nhị phân cho tính tiền.
- `confidence` chỉ là tín hiệu tham khảo, không thay thế Risk Engine.
- `valid_until` bắt buộc để tránh thực thi quyết định cũ.
- `NO_TRADE` không được tạo order intent.
- Action, symbol, side, loại lệnh và quantity phải nằm trong mandate.
- Thiếu trường, thêm trường ngoài schema, giá trị không hợp lệ hoặc lý do mâu thuẫn với action thì từ chối.

## 7. Risk Engine và Order Executor

Risk Engine đánh giá tối thiểu:

- Mandate còn hiệu lực và chưa bị revoke.
- Symbol, side, margin mode, leverage và order type có trong allowlist.
- Dữ liệu market/account/position còn fresh.
- Quantity hợp lệ theo lot size, tick size và min notional.
- Exposure, margin và vốn sau lệnh không vượt hạn mức.
- Risk của lệnh không vượt rủi ro mỗi lệnh.
- Loss budget, daily loss và drawdown chưa chạm ngưỡng.
- Số lệnh, vị thế và tốc độ đặt lệnh chưa vượt giới hạn.
- Có protective stop hoặc emergency policy theo mandate.
- Không có trạng thái `STOPPING`, `UNKNOWN`, liquidation warning hoặc kill switch.
- Decision chưa hết hạn và chưa được thực thi trước đó.

Kết quả Risk Engine phải là một record rõ ràng:

```text
APPROVED | REJECTED | PAUSED | UNKNOWN
```

Mọi `REJECTED`, `PAUSED` và `UNKNOWN` đều phải có mã nguyên nhân ổn định. Executor chỉ nhận `APPROVED` có `risk_check_id`. `clientOid` phải deterministic theo `decision_id` hoặc order intent để retry không tạo lệnh trùng.

## 8. State machine

Mandate hoặc zone có thể đi qua:

```text
CREATED → ENABLED → RUNNING → PAUSED
                         ↓       ↓
                    STOPPING ← LIMIT_REACHED
                         ↓
                    CLOSED

Mọi trạng thái → UNKNOWN khi không xác nhận được trạng thái sàn
UNKNOWN → RUNNING chỉ sau reconcile thành công và policy cho phép
Mọi trạng thái đang chạy → REVOKED khi kill switch hoặc người dùng thu hồi quyền
```

Không được chuyển từ `STOPPING`, `UNKNOWN`, `LIMIT_REACHED` hoặc `REVOKED` về trạng thái tăng rủi ro bằng quyết định của AI.

## 9. Audit và quan sát

Mỗi chu kỳ phải ghi append-only:

- Snapshot timestamp và `feature_asof_ts`.
- Mandate, zone, plan, policy và model version.
- Provider, model, request id, latency và token usage nếu provider cung cấp.
- Context hash, không ghi secret.
- Raw structured decision hoặc bản đã redaction.
- Kết quả validate và Risk Engine.
- Order intent, clientOid, request/response đã redaction.
- Fills, phí, funding, PnL gross và net.
- Reconcile result, state transition và nguyên nhân.
- Can thiệp thủ công, pause, revoke và kill switch.

Log không được chứa API key, token, password, chữ ký request hoặc toàn bộ header xác thực.

## 10. Chế độ vận hành và cổng triển khai

### P0: Chốt policy và xác minh Bitget

Chốt semantics position mode, isolated margin, mark price, reduce-only, partial fill, funding, liquidation, clientOid, rate limit và trạng thái sau timeout bằng tài liệu chính thức và Demo. Chốt các giá trị hạn mức thực tế, hiện vẫn để `TBD`.

### P1: Paper trading

Agent chạy với dữ liệu thật hoặc dữ liệu replay nhưng không gọi endpoint đặt lệnh. Kiểm tra schema, state machine, risk rejection, audit và restart.

### P2: Demo trading

Cho phép executor trên tài khoản Demo với symbol và vốn giới hạn. Kiểm tra timeout sau gửi, partial fill, reconnect, lệnh trùng, emergency close và reconcile.

### P3: Shadow mode

Agent tạo quyết định và mô phỏng thực thi, so sánh với baseline deterministic. Chưa có quyền live.

### P4: Live vốn nhỏ

Chỉ bật sau khi P0 đến P3 đạt tiêu chí, có xác nhận rõ của chủ tài khoản. Mandate được cấp vốn nhỏ, allowlist hẹp, leverage thấp, kill switch độc lập và giám sát cảnh báo.

### P5: Mở rộng có kiểm soát

Mỗi lần tăng symbol, vốn, leverage hoặc quyền hành động phải tạo phiên bản policy mới, có đánh giá kết quả và phê duyệt riêng. Không tự động mở rộng theo đề xuất của AI.

## 11. Tiêu chí nghiệm thu chính

1. AI provider lỗi hoặc trả output sai schema thì hệ thống không gửi lệnh.
2. Proposal vượt symbol, side, quantity, leverage hoặc vốn được cấp bị Risk Engine từ chối.
3. Lệnh đã gửi bị timeout không tạo lệnh trùng sau retry.
4. Partial fill và restart khôi phục đúng vị thế sau reconcile.
5. Chạm loss budget hoặc daily loss chuyển state đúng và chặn lệnh tăng rủi ro.
6. Stop theo mark price đúng chiều Long và Short.
7. Loss đã thực hiện không được cấp lại sau khi giảm vị thế.
8. Kill switch không phụ thuộc vào việc AI còn phản hồi hay không.
9. Agent không thể gọi endpoint ngoài tool allowlist và không thể sửa mandate.
10. Audit truy được từ snapshot, decision, risk check đến order và fill mà không lộ secret.
11. Dùng mock, paper hoặc Demo cho toàn bộ test kỹ thuật. Không dùng tài khoản thật để kiểm thử.
12. Có thể tắt live bằng cấu hình độc lập và ứng dụng mặc định khởi động ở paper hoặc Demo.

## 12. Các quyết định cần chủ dự án chốt

1. Hạn mức vốn ban đầu cho mỗi mandate và mỗi zone là bao nhiêu?
2. Rủi ro tối đa mỗi lệnh tính theo USDT, phần trăm vốn hay phần trăm loss budget?
3. Daily loss limit, drawdown limit và số lệnh tối đa là bao nhiêu?
4. Leverage tối đa, symbol allowlist và margin mode mặc định là gì?
5. Agent được tự mở vị thế trong mandate hay chỉ được quản lý zone do người dùng mở?
6. Agent được tự đặt market order hay chỉ limit order trong giai đoạn đầu?
7. Stop-loss bắt buộc đặt trên sàn, hay emergency policy nội bộ là đủ ở từng giai đoạn?
8. Khi chạm limit, hệ thống market close toàn bộ hay dùng emergency policy theo từng zone?
9. Live mode có cần xác nhận từng mandate, hay cho phép chạy tự động sau một lần bật rõ ràng?
10. Chọn Gemini native, OpenAI-compatible, hay cho phép cả hai ngay từ MVP?
11. Các giá trị `TBD` phải được lưu trong config version và từ chối bật live khi chưa điền đủ hay dùng giá trị mặc định an toàn?

## 13. Ràng buộc triển khai

- Chưa triển khai code hoặc bật live dựa trên tài liệu này khi trạng thái còn là Dự thảo.
- Không hợp nhất các con số hoặc semantics chưa được duyệt với `spec/SPEC.md`.
- Không xem backtest hiện tại là bằng chứng đủ để cấp quyền live.
- Mọi thay đổi nghiệp vụ phải cập nhật spec trước, sau đó mới cập nhật code và test liên quan.
