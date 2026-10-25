# Dự phòng 2 — vận hành tối giản (thử)

Trạng thái: **thử trên Demo**, chưa chốt thay [`frontend-local.md`](frontend-local.md) hay [`ai-agent-autonomous-trading.md`](ai-agent-autonomous-trading.md). Live vẫn khóa. Không hợp nhất với [`spec/SPEC.md`](../spec/SPEC.md).

Mục đích: một cửa để chạy, tự quét cặp đã duyệt, ràng buộc vừa đủ để xem có phù hợp không.

## 1. Bạn làm gì

Chuẩn bị một lần:

1. Kết nối Demo.
2. Lưu Mandate (vốn, SL, lỗ zone, rủi ro/lệnh, trần KL, chu kỳ quét).
3. Duyệt cặp vào allowlist.
4. Bật Tự chủ + cấu hình AI.

Sau đó chỉ hai nút trên Tổng quan:

- **Chạy** = gửi Demo, tự đi hết cặp đã duyệt.
- **Dừng** = tắt vòng.

**Kill** vẫn flatten tay một symbol đang chọn trên ticker; không tự flatten khi mở trang hay khi hết giờ quét.

Không tự chạy khi mở trang. Cặp mới phải duyệt; không tự thêm allowlist.

## 2. Hệ thống tự giữ (không hiện thành cửa trên UI)

- Chỉ Demo; `BITGET_ENV` live và `GROK_TRADER_ALLOW_LIVE` bị từ chối.
- Chỉ symbol trong allowlist. Allowlist trống thì không POST.
- AI chọn long / short / `NO_TRADE` trong hạn mức Mandate. Risk Engine chặn trước khi gửi.
- Lỗi / timeout / sai schema AI → `NO_TRADE`, không bịa lệnh.
- Có vị thế thì quét đúng side đang mở. Chưa có vị thế thì quét long và short để AI được mở một bên.
- Thiếu last/mark của một cặp thì bỏ cặp đó, không bịa giá.
- `ADJUST_SL` vẫn dry-run. `zone_loss_limit` không phải cam kết lỗ tuyệt đối.

Checkbox xác nhận, chọn hướng, chọn một symbol để chạy — không thuộc Dự phòng 2.

## 3. Một tick Chạy

`POST /api/demo-cycle` với `scope=allowlist`. Nút Chạy chính là cửa; server/CLI vẫn gửi cờ Demo thầm (không hiện checkbox).

Thứ tự: GET mới → sổ equity một lần → với mỗi cặp đã duyệt: protect (flatten opt-in nếu chạm SL/loss) → scan nếu tới giờ → POST place/cancel/close + TPSL OPEN trong whitelist → GET reconcile. Live khóa.

## 4. Chưa nằm trong thử này

- Live, WebSocket, tự chạy khi mở trang.
- Kill flatten cả allowlist.
- Đổi số Mandate, nới allowlist, hay bỏ Risk Engine.
- Thay thế đặc tả frontend-local / AI như bản chốt.
