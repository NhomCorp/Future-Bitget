# Spec: Risk policy theo zone

- Trạng thái: Dự thảo cập nhật 2026-10-22, giữ các quyết định P0 Demo/dry-run đã có và bổ sung contract cho mandate AI tự chủ
- Phạm vi: Risk policy theo zone/mandate cho bot Bitget USDT-M Futures
- Không bật lệnh live trong phạm vi tài liệu này

## 1. Mục tiêu

Cho phép mỗi zone có bộ giới hạn rủi ro độc lập, được tạo bởi người dùng hoặc bởi AI trong `AUTONOMOUS_WITHIN_MANDATE`. Zone có thể dùng loss budget, stop theo phần trăm giá, hoặc đồng thời cả hai. Khi cả hai được bật, điều kiện nào chạm trước thì kích hoạt quy trình dừng zone.

AI được tự chọn hành động trong policy đã duyệt khi mandate cho phép, nhưng không được nới, tắt hoặc tăng bất kỳ giới hạn rủi ro nào. `granted_capital` là trần vốn quản lý, không phải mức lỗ được phép.

## 2. Đầu vào cấu hình

Mỗi zone phải lưu một phiên bản cấu hình bất biến sau khi bắt đầu, tối thiểu gồm:

- `zone_id`, `mandate_id`, `subaccount_id`, `symbol`, `side` (`long` hoặc `short`)
- `ai_autonomy` và nguồn tạo zone (`user` hoặc `ai_within_mandate`)
- `granted_capital`, `capital_currency` và vốn còn khả dụng theo mandate
- `zone_loss_limit_usdt` tùy chọn, lớn hơn 0 nếu bật
- `sl_pct` tùy chọn, lớn hơn 0 nếu bật
- `ref_price`, là giá tham chiếu được khóa tại thời điểm mở zone
- `max_order_risk_usdt` hoặc tỷ lệ rủi ro theo policy
- `daily_loss_limit_usdt`, `daily_loss_scope` và quy tắc reset
- `drawdown_limit_usdt` hoặc tỷ lệ, `drawdown_scope` và `drawdown_reference`
- `max_consecutive_losses`, phạm vi đếm và cooldown
- `daily_loss_action`: `FREEZE_ENTRY` hoặc `EMERGENCY_FLATTEN`
- `allow_average_down` và DCA plan nếu được bật
- `symbol_allowlist`, `max_leverage`, `margin_mode = isolated`
- `entry_order_type = limit`, `dca_order_type = limit`, `take_profit_order_type = limit`
- `strategic_stop_mode`, `emergency_order_type = market_reduce_only`, `kill_switch_order_type = market_reduce_only`
- phí, funding và phiên bản policy dùng để tính risk
- trạng thái zone và thời điểm mở/đóng

Hệ thống có thể đề xuất giá trị giới hạn hoặc symbol dựa trên dữ liệu, nhưng người dùng phải xác nhận policy/mandate trước khi AI được phép tự mở zone. Trong mode `AUTONOMOUS_WITHIN_MANDATE`, AI được tạo zone mới chỉ khi mandate đã bật, symbol nằm trong allowlist và còn vốn/exposure hợp lệ. Gợi ý không tự trở thành cấu hình. Giá trị chưa xác định hoặc còn `TBD` phải chặn hành động làm tăng rủi ro.

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

AI được tự mở zone/episode mới chỉ trong `AUTONOMOUS_WITHIN_MANDATE` đã được người dùng xác nhận. AI không được tự:

- tăng `granted_capital`, margin, exposure hoặc leverage;
- thay đổi `zone_loss_limit_usdt`, `sl_pct` hoặc `ref_price` sau khi zone bắt đầu;
- tăng size, số lớp hoặc DCA vượt plan;
- nới SL theo hướng tăng rủi ro, mở lệnh mới để gỡ lỗ hoặc bỏ qua cooldown;
- bỏ qua trạng thái `STOPPING`, `UNKNOWN`, liquidation warning hoặc hard limit.

`PROPOSAL_ONLY` không tạo order intent. `MANAGED_ZONE` không được tự mở zone. `AUTONOMOUS_WITHIN_MANDATE` vẫn phải qua Risk Engine và execution boundary.

P0 chỉ cho phép bot deterministic chạy Demo/dry-run. AI proposal-only và mode tự chủ chỉ được đưa vào sau khi state machine, ledger, reconcile và kiểm thử kỹ thuật đạt cổng P0 đến P3.

## 6. Tiêu chí kiểm thử chính

1. Chỉ bật loss budget, chạm đúng ngưỡng sau khi có realized và unrealized PnL.
2. Chỉ bật `sl_pct`, kiểm tra đúng chiều Long và Short.
3. Bật cả hai, xác nhận điều kiện đến trước kích hoạt; kiểm tra `BOTH` khi cùng reconcile.
4. Option còn lại `disabled` không gây trigger giả.
5. DCA không làm thay đổi `ref_price`.
6. Realized loss không bị cấp lại sau khi giảm size.
7. Partial fill, timeout sau gửi lệnh, lệnh trùng và restart không tạo thêm rủi ro.
8. Lỗi mạng hoặc trạng thái không xác định chuyển `UNKNOWN` và không mở thêm lệnh.
9. AI proposal hoặc autonomous order vượt hard limit bị từ chối trước khi gọi adapter gửi lệnh.
10. Khi daily loss chạm ngưỡng, `FREEZE_ENTRY` chặn entry nhưng cho phép reduce/close/protective action; `EMERGENCY_FLATTEN` hủy pending và tạo emergency close idempotent.
12. `AUTONOMOUS_WITHIN_MANDATE` chỉ tạo zone trong allowlist và vốn còn lại; `MANAGED_ZONE` từ chối zone chưa được mở.
13. Toàn bộ test dùng mock/Demo, không dùng credential hoặc tài khoản thật.
