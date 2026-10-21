# Spec: Risk policy theo zone

- Trạng thái: Đã duyệt cho P0 Demo/dry-run
- Phạm vi: P0 Demo/dry-run cho bot quản lý vị thế Bitget USDT-M Futures
- Không bật lệnh live trong phạm vi tài liệu này

## 1. Mục tiêu

Cho phép mỗi zone có bộ giới hạn rủi ro độc lập. Zone có thể dùng loss budget, stop theo phần trăm giá, hoặc đồng thời cả hai. Khi cả hai được bật, điều kiện nào chạm trước thì kích hoạt quy trình dừng zone.

AI chỉ được đề xuất hoặc chọn hành động trong policy đã duyệt. AI không được nới, tắt hoặc tăng bất kỳ giới hạn rủi ro nào sau khi zone bắt đầu.

## 2. Đầu vào cấu hình

Mỗi zone phải lưu một phiên bản cấu hình bất biến sau khi bắt đầu, tối thiểu gồm:

- `zone_id`, `symbol`, `side` (`long` hoặc `short`)
- `zone_loss_limit_usdt` tùy chọn, lớn hơn 0 nếu bật
- `sl_pct` tùy chọn, lớn hơn 0 nếu bật
- `ref_price`, là giá tham chiếu được khóa tại thời điểm mở zone
- phí, funding và phiên bản policy dùng để tính risk
- trạng thái zone và thời điểm mở/đóng

Ít nhất một trong `zone_loss_limit_usdt` hoặc `sl_pct` phải được bật. Giá trị `null` hoặc trạng thái `disabled` nghĩa là không dùng option đó, không được hiểu là giới hạn bằng 0.

## 3. Tính toán

### 3.1 Loss budget

Risk engine tính:

```text
zone_net_pnl = realized_pnl + unrealized_pnl - fees - funding_paid + funding_received
```

Điều kiện chạm loss budget:

```text
zone_net_pnl <= -zone_loss_limit_usdt
```

Lỗ đã thực hiện tiếp tục tính vào cùng ngân sách trong toàn bộ episode của zone. Giảm size hoặc đóng một phần không cấp lại ngân sách.

### 3.2 Stop theo giá

`ref_price` không thay đổi bởi DCA.

- Long: chạm khi `mark_price <= ref_price * (1 - sl_pct / 100)`
- Short: chạm khi `mark_price >= ref_price * (1 + sl_pct / 100)`

Trigger chính thức dùng mark price. Việc làm tròn theo tick và buffer bảo vệ phải được chốt trong bước xác minh Demo trước khi cho phép thực thi.

## 4. Quy tắc kích hoạt

- Chỉ bật loss budget: dừng khi loss budget chạm.
- Chỉ bật SL giá: dừng khi SL giá chạm.
- Bật cả hai: dùng phép OR, điều kiện nào chạm trước thì dừng.
- Ghi nguyên nhân là `LOSS_BUDGET`, `PRICE_SL` hoặc `BOTH` nếu cùng được phát hiện trong một lần reconcile.
- Không được dời ngưỡng theo hướng làm tăng rủi ro sau khi zone bắt đầu.

Khi trigger:

1. chuyển zone sang trạng thái `STOPPING`, idempotent;
2. hủy entry và DCA chưa khớp của chính zone;
3. chặn mọi hành động làm tăng size hoặc margin;
4. bảo đảm có lệnh đóng toàn bộ vị thế theo emergency policy đã duyệt;
5. reconcile với trạng thái thực tế trên sàn;
6. ghi event append-only và đóng episode khi size về 0.

Nếu không xác nhận được trạng thái lệnh hoặc vị thế, chuyển `UNKNOWN`, không mở thêm rủi ro và phát cảnh báo. `zone_loss_limit_usdt` là ngưỡng điều khiển, không phải cam kết lỗ thực tế không thể vượt do gap, slippage, phí, funding, lỗi sàn hoặc thanh lý.

## 5. Ràng buộc AI

AI không được tự:

- mở zone mới;
- thay đổi `zone_loss_limit_usdt`, `sl_pct` hoặc `ref_price`;
- tăng size, margin, exposure hoặc số lớp vượt plan;
- bỏ qua trạng thái `STOPPING`, `UNKNOWN`, liquidation warning hoặc hard limit.

P0 chỉ cho phép bot deterministic chạy Demo/dry-run. AI proposal-only chỉ được đưa vào sau khi state machine, ledger, reconcile và kiểm thử kỹ thuật đạt cổng P0 đến P3.

## 6. Tiêu chí kiểm thử chính

1. Chỉ bật loss budget, chạm đúng ngưỡng sau khi có realized và unrealized PnL.
2. Chỉ bật `sl_pct`, kiểm tra đúng chiều Long và Short.
3. Bật cả hai, xác nhận điều kiện đến trước kích hoạt; kiểm tra `BOTH` khi cùng reconcile.
4. Option còn lại `disabled` không gây trigger giả.
5. DCA không làm thay đổi `ref_price`.
6. Realized loss không bị cấp lại sau khi giảm size.
7. Partial fill, timeout sau gửi lệnh, lệnh trùng và restart không tạo thêm rủi ro.
8. Lỗi mạng hoặc trạng thái không xác định chuyển `UNKNOWN` và không mở thêm lệnh.
9. AI proposal vượt hard limit bị từ chối trước khi gọi adapter gửi lệnh.
10. Toàn bộ test dùng mock/Demo, không dùng credential hoặc tài khoản thật.
