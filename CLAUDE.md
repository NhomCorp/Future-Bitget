# Rule dự án Future Bitget

## Bắt buộc tra cứu sổ tay

- Trước khi sửa bất kỳ file nào, đọc `COMPASS.md`, chọn đúng mảng công việc và chỉ đọc các file/spec liên quan được chỉ ra. Không quét lại toàn repo khi la bàn đã đủ điểm neo.
- Với thay đổi nghiệp vụ, giao dịch, risk, margin, PnL, funding hoặc API Bitget, đọc spec nguồn được nêu trong `COMPASS.md` trước khi sửa. Nếu spec chưa chốt hoặc có xung đột, dừng phần triển khai phụ thuộc quyết định đó và hỏi chủ dự án.
- Sau khi thay đổi cấu trúc, file neo, entrypoint, luồng dữ liệu, trạng thái tính năng hoặc quy tắc vận hành, cập nhật `COMPASS.md` trong cùng thay đổi. Không cập nhật la bàn cho thay đổi nội bộ không làm đổi cách định vị hay hiểu hệ thống.

## Phạm vi và nghiệp vụ

- Chỉ sửa file thuộc phạm vi được giao. Nêu rõ trước nếu cần mở rộng phạm vi.
- Phân biệt code đang có, đặc tả đã duyệt, dự thảo định hướng và hành vi chưa xác minh. Không mô tả dự thảo như tính năng đã triển khai.
- `spec/SPEC.md` và `specs/zone-auto-trade-ai-plan.md` là hai hướng/spec khác nhau. Không tự hợp nhất quyết định margin, chiến lược, risk hay vận hành giữa hai tài liệu.
- Repo hiện là các script Python; chưa có frontend web hoặc backend service production riêng.

## An toàn giao dịch và dữ liệu

- Không thực hiện lệnh live, không bật `GROK_TRADER_ALLOW_LIVE`, không dùng trade key hoặc tài khoản thật để kiểm thử nếu chủ dự án chưa yêu cầu rõ.
- Ưu tiên dry-run và Demo. Không coi dry-run hoặc backtest là xác nhận an toàn khi chạy live.
- Không tự deploy, push, merge, cài/nâng cấp gói, tạo/sửa migration hoặc xóa dữ liệu nếu chưa được yêu cầu rõ.
- Không in hoặc ghi secret, token, mật khẩu, header ký, key, hay dữ liệu tài khoản thật vào output, log, test hoặc tài liệu.
- Không mô tả `zone_loss_limit` hoặc stop là cam kết lỗ tối đa tuyệt đối; gap, slippage, phí, funding, lỗi sàn và thanh lý có thể gây vượt ngưỡng.
- Nếu semantics API hoặc trạng thái sàn chưa được xác minh, ghi rõ và không suy diễn.

## Kiểm tra và báo cáo

- Chọn test/lint/kiểm tra nhỏ nhất phù hợp với file và mảng thay đổi; không chạy bộ kiểm tra không liên quan.
- Không cài thêm gói để chạy kiểm tra nếu chưa được duyệt.
- Báo cáo ngắn bằng tiếng Việt: file thay đổi, kiểm tra đã chạy và kết quả, phần chưa kiểm tra hoặc chưa xác minh. Không tuyên bố pass nếu chưa chạy.
