# Spec: La bàn dự án Future Bitget

- Trạng thái: Chờ chủ sở hữu duyệt
- Phạm vi: Tài liệu định vị code và đặc tả, không thay đổi logic giao dịch
- Ngày: 2026-10-21

## 1. Mục tiêu

Tạo một la bàn ngắn, có thể tra cứu trước khi sửa code, để xác định đúng file và tài liệu cần chọc vào mà không phải đọc lại toàn bộ repo. La bàn phải phản ánh repo hiện tại là Python toolset, không có frontend web; nếu sau này xuất hiện frontend thì bổ sung nhánh frontend riêng.

## 2. Đầu vào và đầu ra

### Đầu vào

- Cây thư mục và tên module hiện có.
- Các tài liệu nguồn: `README.md`, `spec/SPEC.md`, `specs/zone-auto-trade-ai-plan.md`, `planner/PLAN.md`.
- Quan hệ phụ thuộc đã xác định từ import và luồng lệnh.

### Đầu ra

- File `COMPASS.md` ở thư mục gốc.
- Bảng tra cứu theo khu vực: giao diện CLI, backend/API, chiến lược/risk, dữ liệu/journal, backtest, spec.
- Mỗi khu vực có file bắt đầu, trách nhiệm, file liên quan, và điểm cần kiểm tra trước khi sửa.
- Bản đồ luồng chính từ yêu cầu đến preview, execute, sync và journal.
- Quy tắc cập nhật la bàn khi thêm module hoặc đổi luồng.

## 3. Ràng buộc nghiệp vụ

1. La bàn chỉ mô tả vị trí và trách nhiệm đã xác minh, không tự biến dự thảo thành hành vi triển khai.
2. Phải phân biệt rõ đặc tả cũ trong `spec/SPEC.md` với định hướng zone trong `specs/zone-auto-trade-ai-plan.md`.
3. Không gọi khu vực hiện tại là frontend nếu repo chưa có UI frontend.
4. Các phần liên quan đặt lệnh, live trading, margin, risk và AI phải trỏ về spec nguồn trước khi sửa.
5. La bàn không chứa secret, token, dữ liệu tài khoản thật hoặc kết quả cần bảo mật.
6. Khi thông tin chưa xác minh, ghi trạng thái chưa xác minh thay vì đoán.
7. Không sửa code, cài gói, tạo migration, deploy, push hoặc merge trong phạm vi này.

## 4. Lỗi và cách xử lý

- Không tìm thấy module được nêu trong la bàn: đánh dấu `chưa có` và không tạo file thay thế.
- Hai tài liệu mô tả khác nhau: ghi cả hai nguồn, nêu tài liệu ưu tiên theo trạng thái và không tự hợp nhất nghiệp vụ.
- Không xác định được luồng phụ thuộc: ghi `cần xác minh`, kèm lệnh hoặc file cần kiểm tra ở lần cập nhật sau.
- Module mới chưa có mục trong la bàn: bổ sung mục la bàn trong cùng thay đổi với module đó.

## 5. Nội dung dự kiến của `COMPASS.md`

- Quy ước đọc nhanh và thứ tự tra cứu.
- Khu vực CLI và entry point: `bg.py`, `monitor.py`, các script hiện có.
- Khu vực Bitget adapter/trader: `trader/bgapi.py`, `trader/ta.py`, `trader/snap.py`.
- Khu vực planner/backtest: `planner/`, `backtest/`.
- Khu vực journal/profile: `journal/`, `profile/`.
- Khu vực spec và quyết định nghiệp vụ: `spec/SPEC.md`, `specs/zone-auto-trade-ai-plan.md`, `planner/PLAN.md`.
- Những phần chưa có: frontend, executor production, sync production, state machine zone, ledger loss-budget, AI pipeline.
- Bảng "việc cần sửa thì bắt đầu ở đâu" cho các nhóm thay đổi phổ biến.

## 6. Test case chính

1. Người sửa logic ladder tra được `planner/ladder.py`, `planner/PLAN.md` và spec liên quan mà không cần quét toàn repo.
2. Người sửa API Bitget tra được `trader/bgapi.py` và cảnh báo rằng module trader chưa sẵn sàng live.
3. Người sửa journal tra được `journal/` và các ràng buộc audit trong hai spec.
4. Người sửa risk/zone thấy rõ phải đọc `specs/zone-auto-trade-ai-plan.md` trước, đồng thời biết `spec/SPEC.md` là đặc tả khác.
5. Người tìm frontend thấy trạng thái `chưa có frontend`, không bị trỏ nhầm vào script backend.
6. Khi một file thuộc hai khu vực, la bàn chỉ rõ khu vực chính và liên kết chéo.
7. Tên file trong la bàn đều tồn tại tại thời điểm tạo tài liệu hoặc được đánh dấu `chưa có`.

## 7. Tiêu chí nghiệm thu

- `COMPASS.md` tồn tại ở root và có đủ các mục trong phần 5.
- Có ít nhất một bảng tra cứu theo khu vực và một bảng theo loại thay đổi.
- Có sơ đồ luồng chính và phần khoảng trống hiện tại.
- Không có kết luận triển khai trái với các spec nguồn.
- Các test case chính được kiểm tra bằng tìm kiếm tên file và đọc các điểm neo liên quan.
