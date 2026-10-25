# Kho kinh nghiệm (dự thảo)

- Trạng thái: **Dự thảo 2026-10-23**, chưa duyệt, **chưa triển khai**
- Không phải dataset học đang chạy và không tự sửa policy/mandate
- Liên quan: [`user-style-profile.md`](user-style-profile.md), [`zone-auto-trade-ai-plan.md`](zone-auto-trade-ai-plan.md) mục 3.2

## 1. Ý tưởng

Nhật ký lệnh là camera giao thông: ghi hết, không tự viết luật mới. Kho kinh nghiệm là **sổ bài học có version**, tách khỏi Mandate.

Mỗi lần chu kỳ Demo quyết định (kể cả `NO_TRADE`) có thể ghi một thẻ:

- tình huống đã biết tại `decision_ts` (symbol, side, TA compact, rule phong cách đã áp);
- hành động đã chọn / bị risk chặn;
- kết quả sau này (fill, PnL đã tách, có follow style hay không);
- nhãn người: hữu ích / bỏ / chưa chắc.

Học **offline**. Không nhét vài lệnh mới vào model đang phục vụ. Không tự ghi `user_style.yaml`. Không đụng vốn, đòn bẩy, lỗ ngày.

## 2. Ba lớp, không trộn

| Lớp | Việc | Tự động? |
|---|---|---|
| Nhật ký lệnh | Fills, vị thế, phí | Có, append-only |
| Kho kinh nghiệm | Thẻ bài học + outcome | Ghi thẻ tự động; **rút rule phải người xác nhận** |
| Phong cách đã nạp | `profile/user_style.yaml` | Chỉ khi chủ dự án xác nhận version mới |

Nếu digest journal mâu thuẫn YAML đang active, **YAML thắng**.

## 3. Cách rút bài (khi làm)

1. Gom thẻ theo thesis (fade 1h, scale-out, hedge…) không theo từng lệnh lẻ.
2. Báo cáo ngoài mẫu: net PnL, drawdown, thời gian giữ, phí — không lấy win-rate làm đủ.
3. Ứng viên rule mới hiện cho người dùng (cùng schema phong cách). Chỉ sau xác nhận mới append version vào YAML.
4. Model/strategy mới nếu có phải version + paper/shadow trước khi gắn mandate mới. Không đổi giữa episode.

## 4. Cố ý chưa làm

- Decision-opportunity dataset production
- Pipeline huấn luyện/eval
- Tự cập nhật YAML hoặc prompt từ PnL
- Học từ hành động AI rồi lấy đó làm ground-truth cho chính AI
