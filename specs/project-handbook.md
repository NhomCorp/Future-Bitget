# Spec: Sổ tay làm việc riêng dự án Future Bitget

- Trạng thái: Chờ chủ sở hữu duyệt
- Phạm vi: Rule riêng của repo và tài liệu định hướng khi làm dự án
- Ngày: 2026-10-21

## 1. Mục tiêu

Biến tài liệu `COMPASS.md` từ một bản đồ file thành sổ tay làm việc riêng cho dự án Future Bitget. Sổ tay phải giúp người hoặc AI biết:

- thay đổi thuộc mảng nào;
- cần đọc tài liệu và file nào trước;
- quy tắc nghiệp vụ và an toàn nào áp dụng;
- khi nào phải cập nhật spec, code, vận hành hoặc la bàn;
- phần nào đã có, phần nào mới là định hướng.

## 2. Đầu ra

Tạo hoặc cập nhật đúng ba lớp tài liệu sau:

1. **`CLAUDE.md` ở root repo**
   - Chỉ chứa rule tự động áp dụng cho riêng dự án này.
   - Bắt buộc đọc `COMPASS.md` trước khi sửa.
   - Bắt buộc xác định mảng thay đổi và đọc spec liên quan.
   - Bắt buộc cập nhật `COMPASS.md` khi thêm module, đổi entrypoint hoặc đổi luồng.
   - Chứa các ràng buộc không được live-trade, không lộ secret, không tự coi dự thảo là triển khai, và yêu cầu kiểm tra phù hợp.
   - Không lặp lại toàn bộ rule global nếu không cần thiết.

2. **`COMPASS.md` ở root repo**
   - Đổi vai trò thành sổ tay tra cứu chính, vẫn giữ bản đồ file hiện có.
   - Chia theo các mảng: `spec`, `giao diện`, `backend/API`, `chiến lược/risk`, `dữ liệu/journal`, `backtest/TA`, `vận hành`, `bảo mật`, `kiểm thử`, `AI/zone` và `khoảng trống`.
   - Mỗi mảng có: mục đích, điểm bắt đầu, file/spec liên quan, quy tắc riêng, đầu ra cần kiểm tra và trạng thái `đã có/chưa có/chưa xác minh`.
   - Có bảng tra cứu theo loại công việc và checklist trước/sau thay đổi.
   - Có bản đồ luồng hiện tại và phân biệt rõ luồng được mô tả trong spec với luồng đã có trong code.

3. **Các spec nguồn hiện có**
   - Giữ `spec/SPEC.md` là đặc tả công cụ DCA-ladder bán tự động.
   - Giữ `specs/zone-auto-trade-ai-plan.md` là dự thảo bot zone/AI, chưa phải code đã triển khai.
   - Không hợp nhất hai spec nếu chưa có quyết định nghiệp vụ mới.
   - Có thể thêm liên kết từ `COMPASS.md`, nhưng không sửa nội dung nghiệp vụ của hai spec trong phạm vi này.

## 3. Các mảng trong sổ tay

### 3.1 Spec và quyết định nghiệp vụ

Phải chỉ rõ tài liệu nguồn, trạng thái duyệt, điểm xung đột và quy tắc không tự đoán khi thiếu quyết định.

### 3.2 Giao diện

Hiện repo chưa có frontend web. Giao diện hiện có là stdout/CLI-style script và các `main()` rải trong Python. Nếu thêm frontend hoặc CLI thống nhất, phải tạo mục mới và cập nhật luồng.

### 3.3 Backend/API và trader

Phải trỏ tới `bg.py`, `monitor.py`, `trader/bgapi.py`, cùng cảnh báo dry-run/live guard, read-only key/trade key và trạng thái chưa sẵn sàng live.

### 3.4 Chiến lược, ladder và risk

Phải trỏ tới `planner/ladder.py`, `planner/PLAN.md`, `trader/ta.py` và các phần risk trong spec. Không đổi tham số chiến lược mà không đối chiếu backtest và spec.

### 3.5 Dữ liệu, journal và PnL

Phải trỏ tới `journal/` và `profile/`; giữ audit append-oriented; phân biệt realized/unrealized PnL, fee và funding; không đưa dữ liệu thật hoặc secret vào tài liệu.

### 3.6 Backtest và TA

Phải ghi rõ backtest là nghiên cứu, không phải bằng chứng live; nêu các yếu tố cần kiểm tra như mark price, liquidation path, fill/slippage, fee, funding và ngoài mẫu.

### 3.7 Vận hành

Phải mô tả trạng thái hiện có của monitor, state cục bộ, journal sync và các phần chưa có như executor production, WebSocket reconcile production, zone state machine, loss-budget ledger và kill workflow hoàn chỉnh.

### 3.8 Bảo mật và an toàn giao dịch

Không log/in secret, không tự bật live POST, không tự deploy/push/merge, không dùng key thật để test, không mô tả giới hạn lỗ là cam kết tuyệt đối. Những hành động có khả năng gửi lệnh phải có dry-run/demo và xác nhận theo spec.

### 3.9 Kiểm thử và thay đổi

Mỗi thay đổi phải xác định kiểm tra phù hợp với mảng. Không chạy test hoặc build không liên quan nếu không cần. Khi thay đổi luồng hoặc file neo, cập nhật sổ tay trong cùng thay đổi.

### 3.10 AI và zone

Chỉ mô tả đây là định hướng/dự thảo theo `specs/zone-auto-trade-ai-plan.md`. Không tuyên bố đã có AI pipeline, zone state machine, ledger hoặc AI execute.

## 4. Quy tắc bắt buộc trong `CLAUDE.md`

1. Trước khi sửa file, đọc `COMPASS.md` và chọn đúng mảng.
2. Nếu thay đổi nghiệp vụ, đọc spec nguồn trước; nếu spec chưa chốt thì dừng ở mức hỏi/soạn spec, không tự triển khai.
3. Chỉ sửa file thuộc phạm vi được giao; muốn mở rộng phạm vi phải báo trước.
4. Không coi tài liệu định hướng là tính năng đã có.
5. Không thực hiện live trade, deploy, push, merge, cài gói hoặc xóa dữ liệu nếu chưa được yêu cầu rõ.
6. Không in secret, token, mật khẩu, header ký hoặc dữ liệu tài khoản thật.
7. Sau khi sửa, cập nhật `COMPASS.md` nếu cấu trúc, entrypoint, luồng, trạng thái hoặc quy tắc đã thay đổi.
8. Báo cáo cuối phải nêu file đổi, kiểm tra đã chạy, lỗi còn lại và trạng thái chưa xác minh.

## 5. Checklist nghiệm thu

- Có `CLAUDE.md` root và nội dung chỉ áp dụng cho repo này.
- `CLAUDE.md` yêu cầu đọc/cập nhật `COMPASS.md` đúng thời điểm.
- `COMPASS.md` có đủ các mảng spec, giao diện, backend/API, chiến lược/risk, dữ liệu/journal, backtest/TA, vận hành, bảo mật, kiểm thử và AI/zone.
- Mỗi mảng trỏ tới file tồn tại hoặc ghi rõ `chưa có`/`chưa xác minh`.
- Hai spec nguồn được phân biệt, không bị hợp nhất ngầm.
- Có checklist trước thay đổi và sau thay đổi.
- Không sửa logic giao dịch, không cài gói, không deploy và không thay đổi spec nghiệp vụ trong phạm vi này.
