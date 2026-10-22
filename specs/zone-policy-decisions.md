# Quyết định policy zone và quyền AI

- Trạng thái: Dự thảo cập nhật 2026-10-22, chờ chủ dự án duyệt cho thay đổi quyền tự chủ AI
- Phạm vi: Chốt tham số nghiệp vụ cho Demo/dry-run và định nghĩa cổng cho AI tự chủ
- Không cấp quyền gửi lệnh live và không thay thế bước xác minh Bitget Demo

## 1. Nguyên tắc cấu hình

Các giới hạn rủi ro phải được cấu hình theo policy/mandate/zone, không hard-code một con số duy nhất. Người dùng là bên cấp vốn và xác nhận mandate. AI được tự chủ về phân tích, chiến thuật và thời điểm trong `AUTONOMOUS_WITHIN_MANDATE`, nhưng không có quyền thay đổi mandate hoặc hard limits.

Mandate phải phân biệt:

- `granted_capital`: vốn tối đa AI được phép quản lý;
- margin và exposure đang dùng;
- rủi ro danh nghĩa mỗi lệnh;
- loss budget theo zone/episode;
- daily loss, drawdown và chuỗi lệnh lỗ liên tiếp.

`granted_capital` không phải mức lỗ được phép. Không tự cấp thêm vốn, không tự nạp/chuyển margin và không cấp lại loss budget sau khi giảm size.

Sau khi zone/episode bắt đầu:

- cấu hình được khóa bất biến cho episode đang chạy;
- thay đổi phải tạo phiên bản policy/mandate mới và áp dụng cho episode mới;
- không được dùng tính linh hoạt để nới hard limit trong lúc đang có vị thế;
- giá trị thiếu, không hợp lệ hoặc chưa được người dùng xác nhận phải chặn thực thi tăng rủi ro.

Hệ thống có thể đưa ra giá trị gợi ý dựa trên dữ liệu và policy, nhưng gợi ý chỉ mang tính tham khảo. Người dùng phải xác nhận trước khi mandate được kích hoạt.

## 2. Bảng quyết định

| Mục | Quyết định | Cách áp dụng | Trạng thái |
|---|---|---|---|
| `zone_loss_limit` tối đa mỗi zone | Linh hoạt theo người dùng | Cấu hình theo zone/mandate. Hệ thống gợi ý mức phù hợp với vốn được cấp, exposure và policy; không tự tăng hoặc tự cấp ngân sách. | Đã chốt nguyên tắc, con số cụ thể để cấu hình |
| Rủi ro tối đa mỗi lệnh | Linh hoạt theo người dùng | Cấu hình theo zone/mandate. Risk engine kiểm tra độc lập và bắt buộc nhỏ hơn hoặc phù hợp với loss budget còn lại. | Đã chốt nguyên tắc, con số cụ thể để cấu hình |
| `daily_loss_limit`, `drawdown_limit`, chuỗi lỗ | Người dùng tự cấu hình | Cấp subaccount/mandate. `daily_loss_limit_pct` tính từ equity đầu ngày; `max_consecutive_losses` và cooldown được lưu rõ. Frontend local chỉ lưu policy, chưa tính từ equity thật. Đường Python local có snapshot GET và sổ `day_start` khi đã có quan sát trước 00:00 UTC; thiếu/stale thì không tăng rủi ro. Chưa xác minh Demo, chưa phải trigger production. | Đã chốt nguyên tắc; CLI/paper có thể tính khi sổ local đủ, frontend chưa |
| Symbol | Allowlist mở rộng | Người dùng xác nhận symbol được phép. Hệ thống có thể gợi ý cặp dựa trên metadata sàn, thanh khoản, spread, biến động và điều kiện policy. Gợi ý không tự thêm symbol vào allowlist. | Đã chốt nguyên tắc |
| Leverage tối đa | Cấu hình được, giá trị cụ thể chưa chốt | Lưu trong mandate/zone và kiểm tra trước mọi intent. Không cho thực thi khi chưa có giá trị hợp lệ và chưa xác minh giới hạn thực tế trên Demo. | Chưa chốt giá trị |
| Margin mode | Isolated | Mỗi zone dùng isolated margin. Người dùng tự thêm ký quỹ thủ công; bot không tự nạp, chuyển hoặc cấp thêm margin. Cần xác minh position mode và semantics trên Demo. | Đã chốt định hướng, chờ xác minh Demo |
| Loại lệnh | Limit ưu tiên | Entry, DCA và TP dùng limit. Market chỉ được dùng với `reduce-only` cho strategic SL khi được bật, emergency close và kill switch. Không dùng market để tăng rủi ro. | Đã chốt nguyên tắc, chờ xác minh API |
| Khi chạm loss limit/daily loss | Dừng entry và xử lý vị thế theo mandate | Hủy entry/DCA chưa khớp, chặn mọi hành động tăng size hoặc margin. `daily_loss_action` chọn `FREEZE_ENTRY` hoặc `EMERGENCY_FLATTEN`; reconcile trạng thái thực tế. | Đã chốt nguyên tắc |
| Chuỗi lệnh lỗ | Cooldown bắt buộc | Khi đạt `max_consecutive_losses`, khóa entry, chuyển `COOLDOWN`; không reset bằng cách đổi symbol, zone, model hoặc strategy. | Đã chốt nguyên tắc, con số cần nhập |
| Quyền AI | Tự chủ trong mandate | `PROPOSAL_ONLY` chỉ ghi proposal; `MANAGED_ZONE` chỉ quản lý zone đã mở; `AUTONOMOUS_WITHIN_MANDATE` được tự mở/quản lý/đóng vị thế trong allowlist và vốn được cấp sau khi qua cổng. AI không sửa mandate. | Định hướng mới, chờ chủ dự án duyệt |

## 3. Quy tắc risk bắt buộc

1. `granted_capital`, `zone_loss_limit`, rủi ro mỗi lệnh, daily loss, drawdown, chuỗi lỗ, leverage và allowlist đều là hard limit sau khi policy được xác nhận.
2. Gợi ý của hệ thống không phải là quyền thực thi. Người dùng phải xác nhận cấu hình và symbol trước khi mở zone hoặc bật `AUTONOMOUS_WITHIN_MANDATE`.
3. Khi chạm `zone_loss_limit` hoặc hard limit liên quan, zone chuyển `STOPPING`, hủy entry/DCA, chặn tăng rủi ro và đóng toàn bộ vị thế còn lại.
4. Khi chạm `daily_loss_limit`, khóa entry mới và thực hiện `daily_loss_action` đã cấu hình.
5. Khi đạt `max_consecutive_losses`, chuyển `COOLDOWN`; không được reset bằng cách đổi symbol, zone, model hoặc strategy.
6. Lỗ đã thực hiện không được cấp lại chỉ vì vị thế giảm size hoặc được đóng một phần.
7. Không được nới SL theo hướng tăng rủi ro, tăng size để bù lỗ, hoặc dùng lệnh mới để gỡ lệnh đang lỗ.
8. Isolated không được mô tả là cô lập tuyệt đối cho tới khi được xác minh bằng cấu hình và trạng thái thực tế trên Bitget Demo.
9. Market reduce-only chỉ được dùng cho các đường thoát đã nêu, không dùng để mở hoặc tăng vị thế.
10. Khi timeout, partial fill, mất kết nối hoặc trạng thái không xác định, hệ thống phải reconcile trước khi có hành động mới; không gửi lệnh bù theo giả định.
11. AI không được thay đổi policy, nới limit, thêm symbol, tăng leverage, cấp margin, sửa mandate, nạp/chuyển vốn hoặc bỏ emergency protection.

## 4. Các giá trị cần nhập khi tạo policy/zone

Các trường sau phải có trong form/config trước khi cho phép chạy:

- `granted_capital` và `capital_currency`;
- `ai_autonomy`;
- `zone_loss_limit_usdt` hoặc quy tắc tính tương đương;
- `max_order_risk_usdt` hoặc tỷ lệ đã được policy định nghĩa;
- `daily_loss_limit_usdt` hoặc tỷ lệ;
- `drawdown_limit_usdt` hoặc tỷ lệ và mốc vốn tham chiếu;
- `max_consecutive_losses` và cooldown;
- `daily_loss_action = FREEZE_ENTRY | EMERGENCY_FLATTEN`;
- `symbol_allowlist`;
- `max_leverage`;
- `margin_mode = isolated`;
- `entry_order_type = limit`;
- `dca_order_type = limit`;
- `tp_order_type = limit`;
- `sl_order_type = market_reduce_only` khi strategic SL được bật;
- emergency close và kill switch là `market_reduce_only`;
- `nonstop` và trạng thái strategic SL;
- xác nhận người dùng trước khi policy có hiệu lực.

Không được coi policy là đầy đủ nếu các trường còn `TBD`, đặc biệt là leverage, phạm vi daily loss/drawdown và công thức tính của chúng.

## 5. Cơ chế cài đặt thủ công

- Người dùng nhập các giới hạn subaccount và zone trong frontend local; không hard-code khẩu vị rủi ro.
- Policy được lưu thành version append-only trong local storage. Lưu policy mới tạo version tiếp theo, không sửa lịch sử.
- Zone mới bắt buộc chọn symbol từ allowlist, trừ mode `AUTONOMOUS_WITHIN_MANDATE` có thể để AI chọn symbol trong allowlist; cả hai trường hợp đều lưu snapshot policy version tại lúc tạo.
- Mandate/zone đang chạy không đổi snapshot policy; thay đổi phải tạo version mới.
- Giá trị mặc định 20% daily loss chỉ là gợi ý trong form, không tự kích hoạt.
- Daily loss/drawdown trên frontend vẫn chỉ là cấu hình local. Đường Python local có snapshot GET (`trader/equity_cli.py`, `trading/equity_snapshot.py`): daily loss dùng `day_start_equity × daily_loss_limit_pct / 100`, reset và freshness theo ngày UTC; `day_start_equity` là snapshot cuối trước 00:00 UTC, không lấy equity giữa ngày làm đầu ngày. Thiếu/stale thì không tăng rủi ro. Chưa xác minh trên tài khoản Demo.
- `AUTONOMOUS_WITHIN_MANDATE` không được bật từ frontend local Demo/dry-run nếu chưa có xác nhận mandate và cổng kỹ thuật tương ứng.


## 6. Tiêu chí chấp nhận

- Người dùng có thể tạo policy với các giới hạn khác nhau cho từng zone/mandate.
- Hệ thống hiển thị gợi ý nhưng không tự ghi đè lựa chọn của người dùng.
- Zone/mandate đang chạy không thể bị AI hoặc thao tác thường thay đổi limit.
- Symbol được gợi ý không tự trở thành allowlist.
- `AUTONOMOUS_WITHIN_MANDATE` chỉ tạo zone trong allowlist và vốn được cấp, sau khi mandate được xác nhận.
- Entry/DCA/TP bị từ chối nếu dùng market; các đường thoát được nêu mới được dùng market reduce-only.
- Chạm loss limit tạo chuỗi hủy lệnh tăng rủi ro, đóng vị thế, reconcile và audit.
- Chạm daily loss hoặc loss streak tạo cooldown/freeze theo mandate.
- AI proposal/order vượt hard limit bị từ chối trước khi gọi adapter gửi lệnh.
