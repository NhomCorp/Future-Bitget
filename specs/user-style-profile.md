# Spec: Module nạp và gộp profile phong cách người dùng

- Trạng thái: Dự thảo 2026-10-22, chờ duyệt
- Phạm vi: Schema YAML, luật kiểm tra, luật gộp và test mẫu cho profile phong cách
- Không phải hard limit: nội dung profile chỉ là input chiến lược cho AI, không ghi đè risk engine hay mandate

## 1. Mục tiêu

Cho phép người dùng khai báo phong cách, thói quen, điều kiện không giao dịch và ghi chú kinh nghiệm dưới dạng file YAML có cấu trúc. Hệ thống nạp, kiểm tra và gộp các bản ghi để cung cấp context cho AI. Nội dung không được chạm vào giới hạn rủi ro, vốn, leverage hoặc bất kỳ hard limit nào.

## 2. Schema

Mỗi bản ghi trong `profile/user_style.yaml` tuân thủ schema sau:

```yaml
entries:
  - id: "avoid-us-news"            # định danh duy nhất, kebab-case
    version: 1                      # số nguyên, tăng dần khi sửa cùng id
    kind: "no_trade"                # no_trade | preference | note
    source: "user"                  # luôn là user; channel phân biệt nguồn nhập
    channel: "manual"               # manual | mcp_chat
    status: "active"                # active | retired
    effective_from: "2026-10-22T00:00:00+07:00"
    effective_to: null              # ISO-8601 hoặc null nếu vô hạn
    scope: ["all"]                  # danh sách symbol hoặc ["all"]
    priority: 10                    # số nguyên, cao hơn = ưu tiên cao hơn khi merge
    rule: "Không mở vị thế mới trong ±30 phút quanh sự kiện macro Mỹ"
    condition:                      # chỉ bắt buộc khi kind = no_trade
      event_in: ["NFP", "CPI", "FOMC"]
      window_min: 30
    tags: ["macro", "news"]
```

### 2.1 Trường `kind`

| Giá trị | Ý nghĩa | `condition` | Tác động |
|---|---|---|---|
| `no_trade` | Điều kiện cấm giao dịch | Bắt buộc, máy đọc được | Risk engine hoặc pre-filter chặn trước khi AI đề xuất |
| `preference` | Ưu tiên mềm | Tùy chọn | AI dùng để xếp hạng cơ hội, không chặn cứng |
| `note` | Ghi chú kinh nghiệm | Không | Context bổ sung cho AI, không ảnh hưởng logic chặn |

### 2.2 Trường `source` và `channel`

- `source` luôn là `user`. Mọi bản ghi đều thể hiện ý chí người dùng, dù nhập qua form, file hay chat.
- `channel` phân biệt đường nhập: `manual` (sửa file trực tiếp), `mcp_chat` (qua chat MCP). Khi nhập qua MCP, AI phải đọc lại nội dung và chờ người dùng xác nhận trước khi ghi.
- Không có `source: journal_digest`. Dữ liệu rút từ journal nằm riêng ở `journal/style_digest.py`, không trộn vào file này.

### 2.3 Bất biến và phiên bản

- Không sửa hoặc xóa bản ghi cũ. Sửa = thêm entry cùng `id`, `version` tăng, mang toàn bộ nội dung mới.
- Tại thời điểm đánh giá, chọn version cao nhất đã tới `effective_from` cho mỗi `id`, rồi kiểm tra status và khoảng hiệu lực `[effective_from, effective_to)`. Không quay về version cũ khi version mới retired hoặc hết hiệu lực.
- Dừng một rule bằng cách thêm version `status: retired`, ghi thời điểm dừng trong `effective_from` và `effective_to`. Không đổi status trên bản ghi lịch sử.
- Version mới thay thế version cũ từ thời điểm có hiệu lực; thời điểm kết thúc bản cũ được suy ra khi đọc, không ghi đè file lịch sử.

## 3. Kiểm tra khi nạp

Khi load file, hệ thống phải từ chối toàn bộ file nếu phát hiện lỗi nghiêm trọng, hoặc từ chối từng entry nếu lỗi cục bộ:

### 3.1 Từ chối entry

- Thiếu trường bắt buộc: `id`, `version`, `kind`, `source`, `channel`, `status`, `effective_from`, `scope`, `rule`.
- `kind = no_trade` nhưng thiếu `condition` hoặc `condition` không parse được.
- `source` khác `user`.
- `status` khác `active`/`retired`.
- `effective_from` > `effective_to` (khi `effective_to` khác null).
- `rule` hoặc `condition` chứa tham chiếu đến leverage, margin, loss limit, granted_capital, max_zones, daily_loss, drawdown, max_order_risk hoặc bất kỳ hard limit nào. Đây là vùng cấm tuyệt đối.
- `scope` chứa symbol không hợp lệ.

### 3.2 Cảnh báo nhưng vẫn nạp

- `priority` trùng giữa hai entry cùng `kind` và `scope` overlap.
- Entry `retired` nhưng không có `effective_to`.
- `tags` rỗng.

### 3.3 Từ chối toàn file

- YAML không parse được.
- Cấu trúc gốc không phải mapping có key `entries` là list.
- Phát hiện `id` trùng nhau mà `version` cũng trùng.

## 4. Luật gộp (merge)

Khi nhiều entry cùng áp dụng tại thời điểm quyết định:

1. Chọn version theo mục 2.3 tại timestamp quyết định; chỉ áp dụng bản `active` trong khoảng hiệu lực. Version tương lai không thay thế bản hiện hành.
2. Với `no_trade`: **OR logic**. Bất kỳ entry nào match `condition` thì chặn. Không cần so priority.
3. Với `preference` và `note`: xếp theo `priority` giảm dần; bằng priority thì `effective_from` mới hơn đứng trước.
4. Xung đột giữa `preference` trái ngược nhau: lấy entry `priority` cao hơn; bằng priority thì lấy `effective_from` mới hơn. Ghi log cảnh báo xung đột.
5. Entry `source: user` từ `channel: mcp_chat` có trọng ngang bằng `channel: manual`. Không phân cấp.

Dữ liệu từ `journal/style_digest.py` được truyền riêng như một context block độc lập, không tham gia merge với `user_style.yaml`. Nếu dữ liệu journal mâu thuẫn với entry `user` đang active, entry `user` thắng.

## 5. Tích hợp MCP chat

Khi người dùng yêu cầu thêm/sửa profile qua chat:

1. AI diễn giải yêu cầu thành entry YAML đầy đủ.
2. AI hiển thị entry dự kiến và hỏi xác nhận.
3. Chỉ sau khi người dùng xác nhận, AI ghi entry mới vào file.
4. Nếu sửa, thêm version active mới; nếu dừng, thêm version retired theo mục 2.3. Tuyệt đối không sửa entry cũ.
5. Ghi log audit: timestamp, channel, nội dung yêu cầu gốc, entry đã ghi.

## 6. Test mẫu

| Mã | Mô tả | Kỳ vọng |
|---|---|---|
| T1 | Nạp file hợp lệ 3 entry | PASS, 3 entry active |
| T2 | Entry `no_trade` thiếu `condition` | REJECT entry, log lỗi |
| T3 | Entry chứa từ khóa `leverage` trong rule | REJECT entry |
| T4 | Hai entry cùng id/version | REJECT toàn file |
| T5 | Entry `retired` không có `effective_to` | WARN, vẫn nạp |
| T6 | Merge 2 preference trái dấu, priority khác | Lấy priority cao |
| T7 | Merge 2 preference cùng priority | Lấy effective_from mới hơn |
| T8 | no_trade match condition | Chặn trước AI |
| T9 | Journal digest mâu thuẫn user entry | User entry thắng |
| T10 | MCP chat chưa xác nhận | Không ghi file |
| T11 | Entry hết hiệu lực (effective_to < now) | Loại khỏi merge |
| T12 | Source khác user | REJECT entry |

## 7. Tính năng Chat AI phân tích kỹ thuật (Technical Analysis Chat)

Hệ thống cung cấp giao diện chat để người dùng yêu cầu phân tích kỹ thuật trên symbol cụ thể. AI nhận dữ liệu thị trường thực tế qua adapter nội bộ, áp dụng các indicator đã có trong `trader/ta.py`, và trả về nhận định kèm mức giá quan trọng.

### 7.1 Nguyên tắc hoạt động

- **Chỉ đọc:** Chat TA chỉ được gọi các tool read-only (`read_market_snapshot`, `read_ta_indicators`). Tuyệt đối không tạo order intent hay sửa cấu hình.
- **Dữ liệu thực:** AI phải lấy dữ liệu mới nhất từ sàn hoặc cache gần nhất, không suy diễn từ dữ liệu cũ.
- **Tuân thủ profile:** Kết quả phân tích phải tôn trọng các rule `no_trade` và `preference` trong `user_style.yaml`. Ví dụ: nếu đang trong vùng cấm tin Mỹ, AI phải cảnh báo rõ thay vì đưa ra điểm vào lệnh ngay.
- **Không cam kết:** Mọi nhận định đều mang tính tham khảo chiến lược, không phải tín hiệu chắc chắn.

### 7.2 Schema yêu cầu và phản hồi

**Yêu cầu từ người dùng:**
```json
{
  "symbol": "BTCUSDT",
  "timeframes": ["1h", "4h", "1d"],
  "indicators": ["RSI", "EMA", "BollingerBands"], 
  "question": "Xu hướng hiện tại thế nào? Có vùng hỗ trợ nào gần không?"
}
```

**Phản hồi từ AI:**
```json
{
  "symbol": "BTCUSDT",
  "current_price": 65000.5,
  "trend_analysis": {
    "short_term": "Giảm nhẹ",
    "medium_term": "Tích lũy",
    "long_term": "Tăng"
  },
  "key_levels": {
    "support": [64500, 63800],
    "resistance": [65800, 66500]
  },
  "indicator_values": {
    "RSI_4h": 45.2,
    "EMA_200_1d": 62000
  },
  "profile_check": {
    "blocked_by_no_trade": false,
    "active_preferences_applied": ["prefer-btc-long-dip"]
  },
  "conclusion": "Giá đang test lại EMA200 ngày. RSI 4h trung tính. Vùng hỗ trợ gần nhất 64500. Lưu ý: Không nên mở lệnh mới do sắp có tin CPI trong 15 phút nữa."
}
```

### 7.3 Tích hợp với hệ thống

- Module chat TA dùng chung adapter dữ liệu với bot tự trade để đảm bảo tính nhất quán.
- Kết quả chat có thể được lưu vào journal dưới dạng `note` nếu người dùng đánh dấu là hữu ích.
- Không dùng chat TA để bypass các hard limit risk. Dù AI phân tích "cơ hội tốt", nếu risk engine chặn thì vẫn không được giao dịch.

## 8. Ngoài phạm vi

- Form frontend local: **đã có** `#/phong-cach` + `GET|POST /api/user-style` (append-only). Spec schema/merge vẫn dự thảo.
- Tự động trích xuất phong cách từ journal: giữ riêng ở `style_digest.py`.
- Validation semantic sâu của `condition` (ví dụ kiểm tra event calendar): thuộc module data provider, không thuộc module profile.
- Mã hóa hoặc bảo mật đặc biệt cho file: file không chứa secret; quyền truy cập file theo OS permission thông thường.
- Chat TA không thay thế việc ra quyết định cuối cùng của người dùng hoặc bot tự động trong mandate.

</contents>