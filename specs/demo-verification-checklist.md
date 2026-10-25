# Checklist xác minh Bitget Demo cho zone

- Trạng thái: Checklist đã chốt. Harness local [`trader/demo_verify.py`](../trader/demo_verify.py) / CLI [`trader/demo_verify_cli.py`](../trader/demo_verify_cli.py) đã có. Demo 2026-10-22 `BTCUSDT` (`isolated`, `hedge_mode`, `paptrading: 1`): D0–D6 PASS; D7 UNKNOWN (2 lot tại `last` khớp hết trong một lần GET, không thấy partial); D8–D10 PASS; D11 PASS (`pos_loss` + `mark_price` khi còn long); D12–D13 PASS; D14–D15 UNKNOWN (có `unrealizedPL`/`deductedFee`/`liquidationPrice`, chưa tách realized/funding, không có sự kiện thanh lý). Bằng chứng: [`evidence/demo-verify/2026-10-22-btcusdt.jsonl`](../evidence/demo-verify/2026-10-22-btcusdt.jsonl), [`evidence/demo-verify/2026-10-22-btcusdt-d7-d10.jsonl`](../evidence/demo-verify/2026-10-22-btcusdt-d7-d10.jsonl), [`evidence/demo-verify/2026-10-22-btcusdt-d11-d15.jsonl`](../evidence/demo-verify/2026-10-22-btcusdt-d11-d15.jsonl).
- Phạm vi: Bitget USDT-M Futures Classic API, tài khoản Demo, không live
- Liên quan: [`zone-risk-policy.md`](zone-risk-policy.md), [`ai-agent-autonomous-trading.md`](ai-agent-autonomous-trading.md)
- Tài liệu API: [Demo Trading REST API](https://www.bitget.com/docs/classic/demo-trading/rest-api), [Classic Contract Trade API](https://www.bitget.com/docs/catalog/classic-contract-trade/classic-contract-trade), [Classic Contract Account API](https://www.bitget.com/docs/catalog/classic-contract-account/classic-contract-account)

## 1. Quy tắc an toàn trước khi chạy

- [ ] Tài khoản đang ở Demo mode.
- [ ] API key là Demo API key, có scope tối thiểu cần cho bài test.
- [ ] Không dùng API key live và không đưa secret vào log, output, test hoặc tài liệu.
- [x] Mọi request Demo có header `paptrading: 1`.
- [x] Base URL là `https://api.bitget.com` và product type là `USDT-FUTURES`.
- [x] Môi trường ứng dụng xác nhận `BITGET_ENV=demo`; không bật `GROK_TRADER_ALLOW_LIVE`.
- [ ] Giới hạn vốn Demo và symbol test được ghi trước khi chạy.
- [ ] Có cách dừng thủ công và không chạy đồng thời thao tác bằng tay trên cùng symbol trong lúc test.
- [x] D0–D6: harness JSONL đã redaction, timestamp và kết luận — [`evidence/demo-verify/2026-10-22-btcusdt.jsonl`](../evidence/demo-verify/2026-10-22-btcusdt.jsonl). Không dump raw HTTP.
- [x] D7–D10: [`evidence/demo-verify/2026-10-22-btcusdt-d7-d10.jsonl`](../evidence/demo-verify/2026-10-22-btcusdt-d7-d10.jsonl) — D7 UNKNOWN; D8 timeout/`FOUND`/`NOT_FOUND` không place bù; D9 trùng `clientOid` bị `REJECTED`; D10 hedge close long = `buy`+`close`, leftover đã flatten.
- [x] D11–D15: [`evidence/demo-verify/2026-10-22-btcusdt-d11-d15.jsonl`](../evidence/demo-verify/2026-10-22-btcusdt-d11-d15.jsonl) — D11 PASS; D12–D13 PASS; D14–D15 UNKNOWN.

**Điều kiện dừng ngay:** phát hiện host live, thiếu header Demo, sai product type, trạng thái tài khoản không rõ, hoặc response không thể đối soát.

## 2. Ma trận trạng thái xác minh

| Mã | Nội dung | Căn cứ tài liệu | Bằng chứng Demo cần lưu | Đạt khi |
|---|---|---|---|---|
| D0 | Demo key và header | Đã xác nhận | Request metadata đã redaction | Tất cả request có `paptrading: 1`, không lộ secret |
| D1 | Account mode | Đã xác nhận endpoint account | Response `marginMode`, `posMode`, equity đã redaction | Đọc được mode hiện tại và khớp cấu hình test |
| D2 | Isolated margin | Đã xác nhận giá trị `isolated` | Account/position response | Symbol test ở isolated |
| D3 | Position mode | Đã xác nhận `one_way_mode` hoặc `hedge_mode` | Account response và kết quả set mode nếu cần | Mode ổn định trước khi có order |
| D4 | Contract rules | Endpoint contracts | `minTradeNum`, `sizeMultiplier`, `pricePlace`, `priceEndStep` | Có thể làm tròn size/price không vượt rule |
| D5 | Limit entry | Endpoint place-order | Order detail và pending order | Order nhận đúng symbol, size, price, clientOid |
| D6 | Cancel entry | Endpoint cancel-order | Cancel response và order detail sau cancel | Order về trạng thái `canceled`, không còn pending |
| D7 | Partial fill | Order detail/pending fields | Các lần detail và position snapshot | `executedQty`, average price và remaining size khớp thực tế |
| D8 | Timeout sau gửi | Chưa đủ trong tài liệu | Log timeout, query theo clientOid/orderId, position snapshot | Phân biệt `FOUND`, `NOT_FOUND` và `UNKNOWN`; không gửi lệnh bù mù |
| D9 | Retry clientOid | Tài liệu chỉ cho phép query bằng clientOid, không cam kết idempotency | Hai response và order list | Kết luận rõ duplicate hoặc no-duplicate; không suy diễn trước khi test |
| D10 | Close/reduce | Mapping side/tradeSide trong tài liệu | Order detail, position snapshot | Đúng leg và đúng size; không ảnh hưởng leg khác |
| D11 | Protective stop/TP | Có preset fields, trigger semantics chưa đủ | Pending plan/order và fill | Xác nhận trigger type, mark price và hành vi khớp |
| D12 | Risk trigger | Chính sách zone | Zone event, order state, position | Hủy entry/DCA, chặn tăng size, tạo emergency intent đúng một lần |
| D13 | Restart/reconnect | Chưa đủ trong tài liệu | Snapshot trước/sau restart, pending queries | Không mất intent, không tạo duplicate, unknown buộc reconcile |
| D14 | Funding/PnL | Chưa đủ trong tài liệu trade page | Account/position/history response | Tách được realized, unrealized, fee, funding; không trừ trùng |
| D15 | Liquidation/ADL | Chưa đủ trong tài liệu trade page | Position/order/history sau event Demo nếu có | Ghi nhận được trạng thái và không tuyên bố kiểm soát tuyệt đối |

## 3. Trình tự chạy bắt buộc

### Bước A: Baseline không đặt lệnh

1. Đọc account theo symbol và `USDT-FUTURES`.
2. Đọc positions, pending orders, ticker và contract.
3. Xác nhận không có position/order cũ trên symbol test.
4. Ghi `marginMode`, `posMode`, leverage, available equity và các rule của contract.

**Không đạt:** còn position/order không rõ nguồn hoặc account mode không đúng. Không được chuyển sang bước đặt lệnh.

### Bước B: Chốt mode trước khi có order

1. Nếu cần đổi position mode, đổi `one_way_mode` hoặc `hedge_mode` khi product type không có position/order.
2. Nếu cần đổi margin mode, đổi sang `isolated` khi symbol không có position/order.
3. Đọc lại account để xác nhận mode sau thay đổi.

**Không đạt:** API từ chối do còn position/order, mode đọc lại không khớp, hoặc không xác định được mode đang áp dụng.

### Bước C: Limit entry nhỏ trên Demo

1. Dùng size hợp lệ nhỏ nhất theo contract.
2. Dùng `orderType=limit`, `force=gtc`, `marginMode=isolated`.
3. Dùng `clientOid` deterministic từ zone, role và sequence.
4. Trong hedge mode, xác định rõ `side` và `tradeSide=open`.
5. Lưu order response đã redaction.
6. Query detail bằng `orderId` và bằng `clientOid`.

**Không đạt:** response thiếu định danh, size/price bị thay đổi ngoài rule, hoặc không thể query lại order.

### Bước D: Cancel và kiểm tra trạng thái

1. Hủy bằng `orderId` hoặc `clientOid`.
2. Query detail sau cancel.
3. Đọc pending orders và position.

**Đạt:** order là `canceled`, không phát sinh fill ngoài dự kiến, position không tăng.

### Bước E: Fill và partial fill

1. Tạo một limit order có thể khớp từng phần trong Demo.
2. Query detail nhiều lần, ghi `status`, original size, executed volume và average price.
3. Đọc position sau mỗi thay đổi.
4. Khi timeout giả lập hoặc mất kết nối, chỉ query và reconcile, không gửi lại ngay.

**Đạt:** remaining quantity được tính từ dữ liệu sàn, partial fill không bị ghi thành filled, và retry không tạo rủi ro mới khi trạng thái là `UNKNOWN`.

### Bước F: Close/reduce và bảo vệ

1. Xác nhận side/tradeSide theo position mode trước khi đóng.
2. Test đóng một phần nếu policy cho phép.
3. Kiểm tra stop/TP theo mark price bằng size Demo nhỏ.
4. Sau fill, đọc lại pending protection và position thực tế.

**Đạt:** đúng leg, đúng size, protection được giữ hoặc cập nhật theo kết quả thực tế. Nếu chưa chứng minh được, không bật reduce hoặc stop production.

### Bước G: Restart, reconcile và risk stop

1. Dừng ứng dụng giữa trạng thái pending hoặc sau timeout.
2. Khởi động lại và tải pending intent trước khi tạo intent mới.
3. Gọi reconcile account, positions, orders.
4. Kích hoạt test loss budget hoặc price SL trong môi trường dry-run trước, sau đó chỉ chạy Demo nếu có approval riêng.
5. Kiểm tra hủy entry/DCA, emergency close intent và chuyển `UNKNOWN` khi response không xác nhận được.

**Đạt:** restart không mất intent, không duplicate, loss đã thực hiện không được cấp lại, và zone không tăng rủi ro khi `STOPPING` hoặc `UNKNOWN`.

## 4. Bằng chứng tối thiểu cho mỗi case

- `case_id`, thời điểm UTC, symbol và zone test.
- Mode trước và sau test.
- Request method/path/body đã redaction.
- Response code/data đã redaction.
- Snapshot account, positions, pending orders trước và sau.
- `orderId`, `clientOid` đã redaction theo chính sách nếu cần, không ghi secret.
- State transition của zone và event audit tương ứng.
- Kết luận `PASS`, `FAIL`, `BLOCKED` hoặc `UNKNOWN`.
- Ghi rõ điểm nào là hành vi tài liệu không mô tả đủ.

## 5. Tiêu chí mở cổng Demo boundary

Chỉ xem xét viết dispatcher Demo sau khi:

- D0 đến D6 đạt.
- D7 đến D10 có bằng chứng đầy đủ cho partial fill, timeout, duplicate và close/reduce.
- D11 đến D13 đạt hoặc có quyết định chặn rõ ràng cho phần chưa đạt.
- D14 và D15 được ghi nhận là đã xác minh, chưa xác minh, hoặc không thể kiểm thử trong Demo.
- Có test mock tương ứng cho mọi kết quả `FOUND`, `REJECTED`, `VERIFIED_NOT_RECEIVED` và `UNKNOWN`.
- Dispatcher có dry-run mặc định, không có đường chuyển sang live trong cùng cấu hình test.

## 6. Trạng thái hiện tại của repo

- Đã có: adapter GET-only, zone store SQLite, zone executor dry-run, state machine cục bộ, test mock cho partial fill/timeout/unknown/idempotency, và harness DemoVerify.
- Harness: `python -m trader.demo_verify_cli run --symbol BTCUSDT` (GET D0-D4). POST Demo D5-D6 cần `--place-orders --i-confirm-demo`. Không sửa `trader/bgapi.py`, không bật `GROK_TRADER_ALLOW_LIVE`, không phải dispatcher.
- Test mock: [`tests/test_demo_verify.py`](../tests/test_demo_verify.py) cover `FOUND`, `REJECTED`, `VERIFIED_NOT_RECEIVED`, `UNKNOWN`; isolated bắt buộc; leftover position chặn entry; live env fail-closed.
- Dispatcher Demo: [`trading/demo_dispatch.py`](../trading/demo_dispatch.py); mặc định dry-run; paper scan CLI POST place/cancel/close + TPSL OPEN khi `--place-orders --i-confirm-demo` và symbol nằm trong `mandate.allowed_symbols`; GET order detail sau gửi; kill CLI flatten whitelist; whitelist rỗng hoặc ngoài list thì không POST; protect clock **không** gọi; demo cycle có thể gọi `kill_symbol` khi protect trigger. Restart theo trạng thái sàn **chưa có**.
- Demo 2026-10-22 `BTCUSDT`: D0–D6 PASS. D2 từng FAIL khi `crossed`, PASS sau khi tài khoản ở `isolated`. D5 limit `FOUND`, D6 cancel `canceled` (harness `--place-orders --i-confirm-demo`). Bằng chứng: [`evidence/demo-verify/2026-10-22-btcusdt.jsonl`](../evidence/demo-verify/2026-10-22-btcusdt.jsonl) (`clientOid` đã che giữa; equity chỉ `present`/`missing`). D7 UNKNOWN; D8–D10 PASS. D11 PASS (`pos_loss` lúc còn vị thế, GET `planType=profit_loss` thấy `mark_price`); D12–D13 PASS; D14–D15 UNKNOWN. Bằng chứng: [`evidence/demo-verify/2026-10-22-btcusdt-d7-d10.jsonl`](../evidence/demo-verify/2026-10-22-btcusdt-d7-d10.jsonl), [`evidence/demo-verify/2026-10-22-btcusdt-d11-d15.jsonl`](../evidence/demo-verify/2026-10-22-btcusdt-d11-d15.jsonl).
- D11 đặt `pos_loss` khi còn long, rồi mới flatten; trigger fill/liq thật không mô phỏng. D7 poll nhanh hơn vẫn thấy khớp full 2 lot, không partial.
- Vì vậy hiện tại: **D0–D6 PASS; D7 UNKNOWN; D8–D13 PASS; D14–D15 UNKNOWN**. Chủ dự án đã mở cổng Demo POST từ paper scan trong whitelist (CLI `--place-orders --i-confirm-demo`); D7/D14/D15 vẫn UNKNOWN; live vẫn khóa.
