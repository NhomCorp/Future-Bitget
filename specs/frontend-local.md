# Spec frontend local

## 1. Mục tiêu
Tạo một giao diện web chạy local để xem và mô phỏng luồng zone foundation hiện có: `preview -> status -> sync`. Giao diện chỉ phục vụ Demo/dry-run, giúp kiểm tra luồng và trạng thái trước khi có backend/frontend production.

## 2. Phạm vi

### Có
- Trang dashboard hiển thị danh sách zone local với: zone ID, symbol, side, state, giá tham chiếu và net PnL gần nhất.
- Form policy subaccount/mandate local: `granted_capital`, autonomy mode, daily loss limit, daily loss action, loss streak/cooldown, drawdown limit/unit/reference, max leverage và symbol allowlist; giá trị 20% daily loss được điền sẵn nhưng phải lưu/xác nhận.
- Policy lưu version trong local storage; zone mới lưu snapshot policy version. Với mode `MANAGED_ZONE`, zone phải được người dùng tạo; mode `AUTONOMOUS_WITHIN_MANDATE` chỉ được hiển thị/cấu hình, không thực thi tự động trong frontend local.
- Form tạo zone preview với các đầu vào: symbol từ allowlist, side (`long`/`short`), ref price, zone loss limit, max order risk và SL percent tùy chọn.
- Chọn một zone để ghi một observation dry-run: mark price, realized PnL, unrealized PnL, fees, funding paid/received.
- Hiển thị kết quả sync, trạng thái zone và cờ triggered/reason nếu có.
- Dữ liệu mô phỏng được lưu local để reload trang không mất dữ liệu.
- Có trạng thái rỗng, loading giả lập tối thiểu và thông báo lỗi dễ hiểu.

### Không có
- Không gọi Bitget hoặc bất kỳ API bên ngoài nào.
- Không đọc hoặc yêu cầu API key, trade key, mật khẩu hay dữ liệu tài khoản thật.
- Không gửi, sửa, hủy lệnh và không tự động giao dịch, kể cả khi policy chọn `AUTONOMOUS_WITHIN_MANDATE`.
- Không thay đổi logic risk, công thức PnL hoặc state machine trong Python.
- Không yêu cầu dashboard production, đăng nhập, phân quyền hay deploy.

## 3. Đầu vào và đầu ra

### Đầu vào
- Dữ liệu form preview và observation theo các trường ở trên.
- Dữ liệu zone/observation mock lưu trong local storage của trình duyệt.

### Đầu ra
- Danh sách zone và trạng thái hiện tại.
- Chi tiết observation mới nhất.
- Thông báo thành công hoặc lỗi validation/local storage.
- Có thể reset dữ liệu Demo về trạng thái rỗng bằng thao tác rõ ràng.

## 4. Ràng buộc nghiệp vụ
- Mặc định zone mới ở trạng thái `PREVIEW`; chỉ chuyển `ACTIVE` qua thao tác rõ ràng.
- Chỉ cho sync zone đã tồn tại; không cho nhập zone ID tùy ý để ghi đè zone khác.
- Số tiền và giá phải là số hữu hạn; symbol viết hoa; side chỉ nhận `long` hoặc `short`.
- Triggered/reason chỉ là kết quả mô phỏng local, không phải cam kết giới hạn lỗ thực tế.
- UI phải gắn nhãn rõ `Demo/dry-run` và cảnh báo không kết nối sàn.

## 5. Lỗi cần xử lý
- Bỏ trống hoặc sai định dạng trường bắt buộc.
- Giá trị số không hữu hạn hoặc không hợp lệ.
- Không tìm thấy zone được chọn.
- Local storage bị lỗi hoặc đầy.
- Dữ liệu lưu cũ sai schema: bỏ qua an toàn và hiển thị lỗi không chứa dữ liệu nhạy cảm.

## 6. Test case chính
1. Mở trang lần đầu: thấy nhãn Demo/dry-run và trạng thái rỗng.
2. Tạo preview hợp lệ: zone xuất hiện với state `PREVIEW` và ID sinh tự động.
3. Tạo form thiếu symbol/ref price: không tạo zone, hiện lỗi tại trường tương ứng.
4. Chuyển zone sang `ACTIVE`: trạng thái trên danh sách và chi tiết được cập nhật.
5. Sync observation hợp lệ: hiển thị observation mới nhất và kết quả triggered/reason mô phỏng.
6. Reload trang: zone và observation vẫn còn từ local storage.
7. Chọn zone không tồn tại hoặc dữ liệu local hỏng: hiện lỗi an toàn, không làm trang trắng.
8. Reset Demo: danh sách trở về rỗng sau xác nhận rõ ràng.

## 7. Tiêu chí chấp nhận
- Chạy được hoàn toàn trên local bằng một lệnh được ghi trong README.
- Người dùng thực hiện được đầy đủ luồng preview, status và sync mà không cần credential.
- Không có request mạng tới Bitget hoặc dịch vụ bên ngoài.
- Các test case chính ở mục 6 chạy đúng.
- Đã triển khai trong frontend local; chưa có backend, Bitget API hoặc giao dịch live.
