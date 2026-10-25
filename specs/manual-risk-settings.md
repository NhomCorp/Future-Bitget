# Spec nháp: Cài đặt thủ công risk policy

- Trạng thái: Dự thảo cập nhật theo mandate cấp vốn và quyền AI tự chủ; phần local Demo/dry-run hiện có đã triển khai
- Phạm vi: Cơ chế người dùng tự nhập và quản lý các chỉ số risk trong frontend local Demo/dry-run
- GET Demo từ Tổng quan, không gửi lệnh; form Kết nối chỉ ghi Demo key vào `.env` local. Không bật live

## 1. Mục tiêu

Người dùng có thể tự cấu hình các chỉ số theo khẩu vị rủi ro thay vì phụ thuộc giá trị hard-code hoặc gợi ý của hệ thống. Gợi ý nếu có chỉ là giá trị điền sẵn; policy chỉ được áp dụng sau khi người dùng xác nhận.

## 2. Phạm vi cấu hình

### Cấp subaccount/mandate (mô phỏng local)

- `granted_capital`: người dùng nhập số vốn tối đa AI được phép quản lý; đây không phải mức lỗ tối đa.
- `ai_autonomy`: vẫn thuộc cùng mandate/policy object, nhưng nhập trên **trang Quyền AI** (không nằm trong form khẩu vị Mandate). Người dùng chọn `PROPOSAL_ONLY`, `MANAGED_ZONE` hoặc `AUTONOMOUS_WITHIN_MANDATE`. Đổi mode tạo policy version mới, copy các field khẩu vị còn lại.
- `daily_loss_limit_pct`: người dùng chỉnh được; giá trị mặc định khi mở form là 20% equity đầu ngày, nhưng vẫn phải được người dùng lưu/xác nhận.
- Khi backend có snapshot equity, risk gate tính `daily_loss_threshold_usdt = day_start_equity × daily_loss_limit_pct / 100`; reset và freshness theo ngày UTC.
- `daily_loss_action`: người dùng chọn `FREEZE_ENTRY` hoặc `EMERGENCY_FLATTEN`.
- `max_consecutive_losses` và `loss_streak_cooldown`: người dùng tự nhập; không được bỏ qua khi mandate bật.
- `daily_reset_time_utc`: cố định `00:00 UTC`.
- `drawdown_limit_pct` hoặc `drawdown_limit_usdt`: người dùng tự nhập.
- `drawdown_reference`: bắt buộc người dùng chọn trước khi kích hoạt drawdown gate; không tự suy đoán mốc tính.
- `max_leverage`: người dùng tự nhập.
- `position_review_interval`: người dùng set chu kỳ quét vị thế, đơn vị **phút**, số nguyên **1–240**. Form có nút gợi ý 5 / 15 / 30 / 60; gợi ý chỉ điền ô, không tự lưu, không điền sẵn mặc định. Field nằm trên Mandate; lưu tạo policy version mới. Scheduler paper **đã có** CLI tick/loop local; frontend không tự chạy bot. Chi tiết nghiệp vụ: [`ai-agent-autonomous-trading.md`](ai-agent-autonomous-trading.md) mục 5.3.
- `symbol_allowlist`: chỉ nhận symbol người dùng đã duyệt (trang Đề xuất cặp: duyệt ứng viên, thêm tay, hoặc gỡ). Lần lưu Mandate đầu được trống; trống thì không tạo zone và AI không được trade. Symbol gợi ý/sàng lọc không tự được thêm. Mỗi lần duyệt, thêm tay hoặc gỡ tạo policy version mới.
- Các giới hạn daily loss/drawdown áp dụng toàn subaccount/mandate theo scope đã lưu.

### Cấp zone

- `zone_loss_limit_usdt`.
- `max_order_risk_usdt` hoặc tỷ lệ risk theo policy.
- `sl_pct` và lựa chọn có dùng strategic SL hay không.

### Chính sách cố định, chỉ hiển thị

- `margin_mode = isolated`.
- Entry/DCA/TP là limit.
- Strategic stop khi được bật, emergency close và kill switch là market reduce-only.
- `ai_autonomy` quyết định quyền khởi tạo: `PROPOSAL_ONLY`, `MANAGED_ZONE` hoặc `AUTONOMOUS_WITHIN_MANDATE`. Chọn trên trang Quyền AI, không trên form Mandate. Mode tự chủ không được bật nếu chưa có mandate. Frontend không tự POST khi mở trang; tick Demo trên Tổng quan mới được POST whitelist sau xác nhận.

## 3. Luồng sử dụng

1. Người dùng mở trang Mandate, nhập `granted_capital` và giới hạn subaccount, rồi xác nhận/lưu một policy version local. Allowlist có thể trống ở bước này. Lần lưu đầu, nếu chưa có quyền AI, frontend gán `MANAGED_ZONE` để object policy đủ schema.
2. Trang Đề xuất cặp GET public ticker, xếp ứng viên theo khối lượng 24h. Người dùng duyệt mới đưa symbol vào allowlist (version mới). Từ chối thì không vào. Không tự duyệt.
3. Trang Quyền AI chỉ lưu được sau khi đã có Mandate version. Chọn mode rồi lưu = version mới (copy field khẩu vị). Chưa có Mandate thì control bị disable.
4. Tạo zone thủ công trên Bàn zone khi đã có policy và allowlist không trống; mode `AUTONOMOUS_WITHIN_MANDATE` trên frontend local chỉ lưu cấu hình, không tự tạo zone. Zone lưu snapshot policy version tại thời điểm tạo.
5. Trước khi mandate/zone chuyển ACTIVE, hiển thị tóm tắt để người dùng xác nhận.
6. Sau khi ACTIVE, snapshot policy không sửa đè; thay đổi được lưu thành version mới và chỉ áp dụng cho episode mới.
7. Thiếu giá trị bắt buộc, sai số, drawdown chưa có reference, allowlist trống hoặc symbol ngoài allowlist thì không cho kích hoạt.

## 4. Lưu trữ và tính toán

- Dữ liệu policy hiện được lưu local trong `localStorage`; không gửi ra ngoài trình duyệt.
- Thay đổi schema local storage phải có version/migration hoặc xử lý dữ liệu cũ an toàn.
- Frontend Demo hiện chỉ có dữ liệu zone observation, không có account equity thật. Daily loss theo phần trăm equity đầu ngày và drawdown trên UI chỉ lưu/cấu hình trong policy.
- Đường Python local đã có snapshot GET Demo (`trading/equity_snapshot.py`) và sổ equity append-only; thiếu `day_start` hoặc stale thì risk engine không tăng rủi ro. Đây chưa phải trigger production và chưa xác minh tài khoản Demo.
- Không dùng số liệu giả để mô phỏng account equity nếu người dùng chưa nhập rõ.

## 5. Validation và an toàn

- Các giới hạn phần trăm/USDT/leverage phải là số hữu hạn và dương khi được bật.
- Giới hạn có thể tắt chỉ khi policy còn hard loss control khác theo rule đã duyệt.
- Không tự nới limit, thêm symbol, cấp thêm vốn hoặc kích hoạt policy từ gợi ý.
- Không gồng lệnh hoặc mở lệnh mới để gỡ lỗ; DCA chỉ hợp lệ khi mandate bật và có plan. Paper `ADJUST_SL`: siết luôn được nếu stop hợp lệ; nới được nếu remaining loss-to-SL còn trong hard limit (dự thảo AI mục 4.7). P0 [`zone-policy-decisions.md`](zone-policy-decisions.md) mục 7 vẫn cấm nới SL tăng rủi ro cho tới khi chốt.
- UI luôn ghi rõ Demo/dry-run và không kết nối sàn.

## 6. Test case chính

1. Lưu và tải lại policy local đã nhập.
2. Từ chối số âm, số không hữu hạn và giá trị sai định dạng.
3. Không cho áp dụng policy nếu drawdown đang bật nhưng chưa chọn reference.
4. Symbol được gợi ý/sàng lọc không tự vào allowlist; user phải duyệt hoặc thêm tay. Symbol ngoài allowlist không tạo zone active, kể cả khi AI đề xuất. Allowlist trống thì không tạo zone.
5. Mode `AUTONOMOUS_WITHIN_MANDATE` chỉ tạo zone khi có `granted_capital`, mandate đã xác nhận và còn vốn hợp lệ.
6. Daily loss chạm ngưỡng khóa entry theo `daily_loss_action`; loss streak chạm ngưỡng tạo cooldown.
7. Zone lưu policy version tại lúc tạo; sửa policy không âm thầm đổi cấu hình zone hiện có.
8. Policy cũ không có field mới được xử lý an toàn, không làm trang trắng. Policy cũ thiếu `position_review_interval` vẫn tải; lưu mới thì bắt buộc 1–240 phút.
9. Không có request mạng ngoài và không tạo lệnh giao dịch.
10. Nút gợi ý 5/15/30/60 chỉ điền ô chu kỳ quét; không tự lưu policy.

## 7. Ngoài phạm vi

- Frontend gọi Bitget hoặc hiện equity sàn.
- Coi snapshot GET local là trigger production hoặc đã xác minh Demo.
- Đồng bộ cấu hình giữa các thiết bị hoặc backend.
- Gửi/cancel/đóng lệnh Demo hoặc live.
- Tự động chọn symbol hoặc tự điều chỉnh giới hạn.
