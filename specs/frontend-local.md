# Spec frontend local

Thử nghiệm vận hành tối giản đang chạy trên Tổng quan: [`du-phong-2.md`](du-phong-2.md). Bản này vẫn mô tả khung frontend đã duyệt; Dự phòng 2 chưa thay thế các mục dưới đây.

## 1. Mục tiêu
Tạo một giao diện web chạy local để xem và mô phỏng luồng zone foundation hiện có: `preview -> status -> sync`. Giao diện chỉ phục vụ Demo/dry-run, giúp kiểm tra luồng và trạng thái trước khi có backend/frontend production.

## 2. Phạm vi

### Có
- Một HTML local, nhiều view trong-trang (hash). Khung nav bốn nhóm: Vận hành (Tổng quan, Bàn zone), Nền tảng (Kết nối, Cấu hình AI, Phong cách), Hạn mức (Mandate → Đề xuất cặp → Quyền AI), Chưa làm (Nhật ký). Hash mặc định `#/tong-quan`. Nav hiện checklist local (số zone, version agent/policy, số cặp đang áp dụng phong cách nếu đã đọc, mode AI); không GET, không in key. Chi tiết IA ở mục 8.
- Bàn zone: danh sách zone local với zone ID, symbol, side, state, giá tham chiếu và net PnL gần nhất.
- Trang Cấu hình AI: form agent (`provider`, `model`, `base_url` khi OpenAI-compatible, `request_timeout`) và API key trên trang (che ký tự giữa: 4 đầu + 4 cuối). Object riêng, version riêng; không chờ Mandate. Gemini: nhiều key ngang hàng, mỗi key một nhãn; khi gọi hoặc Check live bốc ngẫu nhiên một key. OpenAI-compatible: một key. Nút Check live ping provider (không lưu version, không giao dịch); dòng kết quả gần nhất lưu local, không chứa key. Key lưu localStorage máy này; notice/log không in giá trị key.
- Trang Mandate: form khẩu vị subaccount (`granted_capital`, daily loss limit/action, loss streak/cooldown, drawdown limit/unit/reference, max leverage, `position_review_interval` phút 1–240 kèm nút gợi ý 5/15/30/60 không tự lưu, `sl_pct`, `zone_loss_limit_usdt`, `max_order_risk_usdt`, `max_size`). Allowlist chỉ đọc (chip); lần lưu đầu được trống. Không có select `ai_autonomy` trên trang này. Giá trị 20% daily loss được điền sẵn nhưng phải lưu/xác nhận. Gợi ý chu kỳ quét không điền sẵn. Policy cũ thiếu 4 hạn mức lệnh vẫn tải được; chu kỳ Demo yêu cầu lưu lại đủ field.
- Trang Đề xuất cặp: GET public ticker USDT-M (`GET /api/pair-screen` → CLI rank theo khối lượng 24h), hiện ứng viên chờ duyệt. User duyệt mới thêm vào `symbol_allowlist` và tạo policy version mới. Từ chối thì không vào allowlist, không đề xuất lại. Thêm tay cũng là duyệt. Gỡ symbol khỏi allowlist tạo version mới. Đề xuất không tự thành policy. Cần Mandate đã lưu. GET Demo, không gửi lệnh.
- Trang Quyền AI: chọn `PROPOSAL_ONLY` / `MANAGED_ZONE` / `AUTONOMOUS_WITHIN_MANDATE` kèm giải thích từng mode. Cùng một policy object với Mandate; đổi mode tạo policy version mới (copy field mandate còn lại). Chưa có Mandate đã lưu thì không lưu được quyền AI. Không có field provider/model. Có dòng chỉ đọc cấu hình agent hiện tại.
- Policy lưu version trong local storage; zone mới lưu snapshot policy version. Với mode `MANAGED_ZONE`, zone phải được người dùng tạo; mode `AUTONOMOUS_WITHIN_MANDATE` chỉ được hiển thị/cấu hình, không thực thi tự động trong frontend local.
- Form tạo zone preview với các đầu vào: symbol từ allowlist, side (`long`/`short`), ref price, zone loss limit, max order risk và SL percent tùy chọn. Thiếu policy hoặc allowlist trống thì không tạo zone.
- Chọn một zone để ghi một observation dry-run: mark price, realized PnL, unrealized PnL, fees, funding paid/received.
- Hiển thị kết quả sync, trạng thái zone và cờ triggered/reason nếu có.
- Dữ liệu mô phỏng được lưu local để reload trang hoặc đổi view không mất dữ liệu.
- Có trạng thái rỗng, loading giả lập tối thiểu và thông báo lỗi dễ hiểu.
- Trang Tổng quan GET Demo: vào `#/tong-quan` gọi `GET /api/bitget-snapshot` một lần rồi poll mỗi 12 giây khi đang mở trang (ẩn tab thì dừng; nút làm mới tay vẫn còn; không POST). Hàng số nổi: số dư, khả dụng, lãi/lỗ chưa chốt, đếm vị thế/lệnh/fills; không bịa PnL đã chốt hay PnL ngày. Ticker last/mark/funding lấy từ snapshot nếu có; GET lỗi thì sửa tay local. Sổ đầy ngang tab Vị thế / Lệnh chờ / Lịch sử (fills) / Đối soát / Tài sản hiện số sàn đã lọc; thiếu/lỗi thì rỗng rõ, không bịa. Fills tối đa 20 bản gần nhất từ GET `/order/fills`. Đối soát so zone local với vị thế/fills sàn (chỉ đọc, không đổi state, không chạy PaperReconcile). Chu kỳ Demo và Kill gập dưới sổ; không còn phiếu intent trên UI. Chu kỳ Demo (`POST /api/demo-cycle`) chỉ chạy khi user bấm Chạy / Dừng, tick **Chạy trên Demo**, allowlist không trống, quyền `AUTONOMOUS_WITHIN_MANDATE`, Mandate đã có SL/lỗ zone/rủi ro/lệnh/trần KL; GET snapshot mới, ghi sổ equity (bootstrap ngày đầu), protect, flatten opt-in nếu mark chạm SL/loss, scan nếu tới giờ. Hạn mức lấy từ Mandate, không nhập lại trên Tổng quan. POST place/cancel/close + TPSL OPEN chỉ symbol đã duyệt; GET reconcile sau gửi. Có cấu hình AI thì gọi khi tới giờ quét; lỗi/timeout/sai schema → `NO_TRADE`. Không tự loop khi mở trang. Không bịa `day_start` từ checkbox UI. Kill Demo (`POST /api/demo-kill`) một tick xác nhận Demo, hủy pending và flatten symbol đang chọn trong allowlist, không qua AI, đồng thời dừng vòng. Live khóa. Không chart, không nhãn Mua/Bán. Tick cũ `POST /api/demo-scan` vẫn còn; CLI `--proposal` vẫn nhận phiếu intent.
- Trang Kết nối: status Demo/dry-run và env đủ/thiếu (`BITGET_ENV`, `BITGET_API_KEY`, `BITGET_API_SECRET`, `BITGET_PASSPHRASE`, `GROK_TRADER_ALLOW_LIVE`). Form Demo key ghi `.env` local (`POST /api/connect-credentials`): che ký tự giữa, xác nhận Demo, không trả giá trị, không localStorage, không bật live. `get_bitget=connected` khi endpoint snapshot sống. GET Demo, không gửi lệnh.
- Trang Phong cách: đọc/ghi `profile/user_style.yaml` qua `GET|POST /api/user-style` (Origin local, spawn [`trader/style_cli.py`](../trader/style_cli.py)). Danh sách latest version theo id; form thêm `preference` / `note` / `no_trade`; sửa = version mới; dừng = version `retired`. Cấm field/từ khóa hard limit. Không localStorage, không đè Mandate. Reset Demo trên trình duyệt không xóa YAML.
- Stub (layout + copy “chưa làm”) cho Nhật ký cho đến khi đợt tương ứng làm.

### Không có
- Node không ký Bitget. Snapshot/pair-screen đi Python CLI GET-only. Chu kỳ Demo spawn [`trader/demo_scan_cli.py`](../trader/demo_scan_cli.py) `cycle`; mặc định dry-run, POST chỉ khi user xác nhận + `--place-orders`. Cycle có thể gọi AI provider khi scan tới giờ (cùng quy tắc HTTPS công khai với Check live; key không ghi log). Kill Demo spawn [`trader/demo_kill_cli.py`](../trader/demo_kill_cli.py); không gọi PaperAgent. Không tự loop khi mở trang. Không live.
- Không nhập trade key live hay dữ liệu tài khoản thật. Key AI nhập trên trang Cấu hình AI, che ký tự giữa, chỉ lưu local; notice/log không in giá trị. Key Bitget Demo nhập trên trang Kết nối và ghi `.env` local; không lưu localStorage.
- Không tự giao dịch khi mở trang. `AUTONOMOUS_WITHIN_MANDATE` + allowlist trống thì không POST. Cặp mới vẫn phải user duyệt.
- Không đổi công thức PnL hay state machine SPEC từ frontend. Paper/risk Python đã có module riêng; Tổng quan GET không gọi chúng. Chu kỳ Demo mới gọi GET + protect + paper scan + dispatcher.
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
- UI phải gắn nhãn rõ `Demo/dry-run` và `GET Demo, không gửi lệnh`.

## 5. Lỗi cần xử lý
- Bỏ trống hoặc sai định dạng trường bắt buộc.
- Giá trị số không hữu hạn hoặc không hợp lệ.
- Không tìm thấy zone được chọn.
- Local storage bị lỗi hoặc đầy.
- Dữ liệu lưu cũ sai schema: bỏ qua an toàn và hiển thị lỗi không chứa dữ liệu nhạy cảm.
- `GET /api/bitget-snapshot` thiếu Origin local, `GROK_TRADER_ALLOW_LIVE=1`, `BITGET_ENV` live, thiếu key hoặc lỗi sàn: `{ ok: false, error }`, tab rỗng rõ, không dump secret/raw account.
- `GET /api/pair-screen` thiếu Origin local, `GROK_TRADER_ALLOW_LIVE=1` hoặc `BITGET_ENV` live: `{ ok: false, error }`; không duyệt hộ, không dump raw ticker.
- `GET|POST /api/user-style` thiếu Origin local: `{ ok: false, error }`. Rule/condition chứa từ khóa hard limit, `no_trade` thiếu condition, id không kebab-case: không ghi file. Không sửa/xóa entry cũ.

## 6. Test case chính
1. Mở trang lần đầu: thấy nhãn Demo/dry-run và trạng thái rỗng.
2. Tạo preview hợp lệ: zone xuất hiện với state `PREVIEW` và ID sinh tự động.
3. Tạo form thiếu symbol/ref price: không tạo zone, hiện lỗi tại trường tương ứng.
4. Chuyển zone sang `ACTIVE`: trạng thái trên danh sách và chi tiết được cập nhật.
5. Sync observation hợp lệ: hiển thị observation mới nhất và kết quả triggered/reason mô phỏng.
6. Reload trang: zone và observation vẫn còn từ local storage.
7. Chọn zone không tồn tại hoặc dữ liệu local hỏng: hiện lỗi an toàn, không làm trang trắng.
8. Reset Demo: danh sách trở về rỗng sau xác nhận rõ ràng.
9. Đổi view bằng nav/hash: dữ liệu localStorage (policy, agent config, zone, observation) vẫn còn; không bị reset.
10. Chưa lưu Mandate: trang Quyền AI disable lưu; trang Đề xuất cặp disable duyệt; form tạo zone không tạo được zone. Cấu hình AI vẫn lưu được.
11. Lưu Mandate rồi đổi quyền AI: policy version tăng; các field khẩu vị được copy, không mất. Agent-config version không đổi.
12. Mở Tổng quan khi GET lỗi hoặc trống: last/mark/funding giữ local nếu có, equity là —, tab vị thế/lệnh/fills/đối soát/tài sản rỗng rõ, không hiện số sàn bịa.
13. GET Demo thành công: tab hiện vị thế/lệnh/fills/tài sản đã lọc; ticker last/mark/funding điền từ snapshot nếu có. Tab Đối soát so zone local với vị thế/fills (Khớp / Chỉ local / Chỉ sàn / Preview), không đổi state. GET lỗi: số ticker local còn sửa được. Reload vẫn giữ ticker local; snapshot không lưu localStorage.
14. Tổng quan không còn phiếu intent. CLI `--proposal` vẫn nhận phiếu intent ngoài UI.
15. Mở Cấu hình AI, lưu Gemini + model + timeout + ít nhất một key có nhãn: version v1; reload còn nhãn và key che giữa trên form (4 đầu + 4 cuối).
16. Chọn OpenAI-compatible: hiện `base_url` và một ô API key; thiếu `base_url` hoặc key thì không lưu. Gemini ẩn `base_url`, hiện danh sách key ngang hàng.
17. Quyền AI và Bàn zone hiện dòng chỉ đọc `provider + model + version` và số key (Gemini: “xoay ngẫu nhiên”) hoặc “chưa cấu hình”. Notice/readout không in giá trị key. Form Quyền AI không có field provider.
18. Gemini thiếu nhãn hoặc key thì không lưu; thông báo lỗi không chứa giá trị key. Reset Demo xóa cả cấu hình AI và key.
19. Check live: bốc ngẫu nhiên một Gemini key (không chia chính/phụ), ping provider, hiện OK/lỗi theo nhãn trên trang (không in key); không tạo version mới. Reload còn dòng check gần nhất.
20. Mở Kết nối: thấy Demo/dry-run, từng biến env Đã có/Thiếu, GET Bitget “GET Demo đã nối”, và form Demo key (che giữa). Status không in giá trị.
21. `GET /api/connect-status` và notice/readout chỉ trả `present`/`missing` (và nhãn mode đã biết); không chứa giá trị key. Reload/đổi view không lộ secret.
22. Lưu Demo key trên Kết nối (đủ 3 ô + xác nhận Demo): `.env` được ghi, form trống lại, status chuyển Đã có; response/notice không chứa giá trị. Thiếu xác nhận Demo thì không ghi.
23. `POST /api/ai-check` từ Origin khác, `base_url` nội bộ, HTTP công khai, hoặc scheme lạ bị từ chối; không gửi key. Check live Gemini và mọi host OpenAI-compatible HTTPS công khai vẫn ping được. Local LLM (`localhost`) chỉ gọi thẳng từ trình duyệt.
24. Mandate: ô chu kỳ quét bắt buộc 1–240 phút; nút 5/15/30/60 chỉ điền ô, không lưu cho tới khi bấm Lưu policy. Lưu mới bắt buộc `sl_pct`, `zone_loss_limit_usdt`, `max_order_risk_usdt`, `max_size`. Policy cũ thiếu field vẫn tải được, form để trống, không trang trắng.
25. Mandate lần đầu lưu được với allowlist trống; chip đọc-only, không ô nhập tự do. Bàn zone vẫn chặn tạo zone đến khi có ít nhất một symbol đã duyệt.
26. Đề xuất cặp: bấm Đề xuất → GET public ticker, ứng viên hiện pending, allowlist không đổi. Duyệt một/nhiều cặp → policy version tăng, symbol vào allowlist. Từ chối → không vào allowlist, lần đề xuất sau bỏ qua. Reload còn pending/rejected.
27. Thêm tay một symbol hợp lệ → version mới, vào allowlist. Gỡ chip trên trang Đề xuất cặp → version mới, symbol ra khỏi allowlist. Đề xuất không tự thêm.
28. Chu kỳ Demo: allowlist trống / chưa AUTONOMOUS / chưa xác nhận Demo / Mandate thiếu hạn mức lệnh → không POST. Tick Chạy trên Demo + Chạy → POST chỉ symbol trong allowlist, hạn mức từ Mandate; live khóa. Không tự chạy khi mở trang. Dừng tắt timer.
29. Kill Demo: allowlist trống / symbol ngoài list / chưa xác nhận Demo → không POST. Một tick xác nhận → hủy pending rồi đóng vị thế symbol đang chọn; live khóa; không qua AI; dừng vòng đang chạy.
30. Cycle gọi AI: chưa cấu hình AI thì không gửi agent. Có cấu hình → gọi provider khi scan tới giờ. Timeout/sai JSON/sai schema → `NO_TRADE`, không POST. Notice/log không in key.
31. Mở Phong cách: GET YAML local, hiện latest version theo id. Form thêm preference hợp lệ → file thêm entry, danh sách cập nhật. Sửa một id → version tăng, bản cũ còn trong file.
32. Phong cách: rule có `leverage`/`margin`/vốn không lưu. Dừng một id → version `retired`, không còn applied. Reset Demo trên trình duyệt không xóa YAML.

## 7. Tiêu chí chấp nhận
- Chạy được hoàn toàn trên local bằng một lệnh được ghi trong README.
- Người dùng thực hiện được đầy đủ luồng preview, status và sync mà không cần credential.
- GET Demo qua `GET /api/bitget-snapshot` và `GET /api/pair-screen` (Origin local, spawn CLI, Demo only). Chu kỳ Demo qua `POST /api/demo-cycle` (xác nhận Demo, whitelist, GET mới + protect/scan, cấm live; có thể gọi AI khi tới giờ). Kill Demo qua `POST /api/demo-kill` (xác nhận Demo, whitelist, không qua AI). Phong cách qua `GET|POST /api/user-style` (YAML local, append-only, không hard limit). Check live được phép gọi AI provider. Đề xuất cặp không tự vào allowlist.
- Các test case chính ở mục 6 chạy đúng.
- Đã triển khai frontend local Demo GET + chu kỳ POST whitelist có Chạy/Dừng; chưa có backend production hoặc giao dịch live.

## 8. Kiến trúc thông tin (IA)

Một file HTML. `ai_autonomy` vẫn nằm trong cùng policy object (`STORAGE_KEY`, schema v4). Cấu hình agent là object riêng `agentConfig` + `agentConfigVersions`, không nằm trong `isPolicy` và không đổi version mandate. Đổi provider/model/key tạo agent-config version mới. Gemini: mọi key ngang hàng, bốc ngẫu nhiên. Check live ping provider; không phải đường giao dịch.

### Sơ đồ và thứ tự mở khóa

```text
Vận hành:  Tổng quan    Bàn zone
Nền tảng:  Kết nối → Cấu hình AI → Phong cách
Hạn mức:   Mandate → Đề xuất cặp → Quyền AI
Chưa làm:  Nhật ký
```

- Nav theo tần suất dùng: bàn làm việc trước, thiết lập sau. Hash trống hoặc không hợp lệ mở `#/tong-quan`.
- Nền tảng độc lập: Kết nối (Demo key) và Cấu hình AI không chờ Mandate; chọn model trước khi cấp vốn được.
- Hạn mức theo chuỗi mở khóa 1–3: Mandate đã lưu version → mới cho duyệt cặp vào allowlist và chọn/lưu quyền AI. Tạo zone cần policy và allowlist không trống.
- Checklist trên nav đọc localStorage (số zone, agent version, policy version, số symbol allowlist, mode AI rút gọn). Không GET thêm, không in key/secret.
- Gọi agent trên tick Demo cần cả cấu hình AI và quyền Tự chủ. Check live chỉ ping model, không tạo zone hay lệnh.
- Tổng quan xem được sớm, kể cả trống.
- Nhật ký chừa nav ở nhóm Chưa làm. Phong cách nằm Nền tảng, không phải hard limit.
- `AUTONOMOUS_WITHIN_MANDATE` không tự chạy khi mở trang; chu kỳ Demo trên Tổng quan mới được POST, chỉ whitelist.
- Không đổi provider giữa episode đang chạy — UI Demo chỉ lưu; chưa có episode live.

### Từng trang

| Trang | Đợt | Nội dung |
|---|---|---|
| Tổng quan | 2 | Hàng số nổi: số dư (equity), khả dụng, lãi/lỗ chưa chốt (asset hoặc tổng vị thế), số vị thế / lệnh chờ / fills. Không bịa PnL đã chốt hay PnL ngày. Thanh ticker (symbol allowlist; last/mark/funding từ GET Demo nếu có, sửa tay khi lỗi). Sổ đầy ngang: tab Vị thế, Lệnh chờ, Lịch sử (fills tối đa 20), Đối soát, Tài sản — số sàn đã lọc hoặc rỗng rõ. Card số bấm nhảy tab. Đối soát zone local với sàn, chỉ đọc. Fetch một lần khi vào trang + poll GET 12s khi đang mở (ẩn tab thì dừng); nút làm mới tay; không POST. Không chart. Hash mặc định. Điều khiển Demo gập dưới sổ: hướng + một tick Chạy trên Demo + Chạy/Dừng; hạn mức SL/lỗ/risk/KL lấy từ Mandate; GET mới, sổ equity, protect flatten opt-in, scan nếu tới giờ; POST whitelist; gọi AI nếu đã cấu hình. Không phiếu intent trên UI. Kill Demo: một tick xác nhận, flatten symbol đang chọn, không qua AI, dừng vòng. |
| Bàn zone | 1 | Form tạo + sổ + observation như mục 2. Thiếu policy thì không tạo zone. Dòng chỉ đọc cấu hình agent hiện tại. |
| Kết nối | 3 | Status Demo/dry-run và env đủ/thiếu, không in giá trị. Form Demo key ghi `.env` (`POST /api/connect-credentials`, Origin local, xác nhận Demo). `GET /api/connect-status` đọc `.env`/OS env, chỉ trả present/missing, nhãn mode và `get_bitget=connected`. GET Demo, không gửi lệnh. |
| Cấu hình AI | 1 | Form `provider` (`gemini` / `openai_compatible`), `model`, `base_url` (chỉ OpenAI-compatible), `request_timeout`. Gemini: danh sách `{ nhãn, key }` ngang hàng, strategy `random`. OpenAI-compatible: một `api_key`. Form che ký tự giữa. Nút Check live ping provider (bốc random nếu Gemini); `POST /api/ai-check` chỉ Origin local, OpenAI-compatible chỉ HTTPS public. Dòng trạng thái check gần nhất lưu local, không chứa key, không tạo version. Lưu = agent-config version mới. Không temperature, không max output tokens, không sửa prompt hệ thống, không tự bật AUTONOMOUS. |
| Mandate | 1 | Form khẩu vị, gồm `position_review_interval` (phút, 1–240, gợi ý 5/15/30/60 không tự lưu) và hạn mức lệnh `sl_pct` / `zone_loss_limit_usdt` / `max_order_risk_usdt` / `max_size` (chu kỳ Demo đọc từ đây). Allowlist chỉ đọc; trống được ở lần lưu đầu. Không có select quyền AI. Không có field provider. Chu kỳ quét paper chạy CLI local, trang này không tự tick. |
| Đề xuất cặp | 1 | GET public ticker, rank khối lượng 24h, user duyệt/từ chối/thêm tay/gỡ. Duyệt hoặc gỡ = policy version mới. Đề xuất không tự vào allowlist. Disable nếu chưa có Mandate. Không POST lệnh. |
| Quyền AI | 1 | 3 mode + giải thích. Disable lưu nếu chưa có policy. Lưu = policy version mới, copy field mandate. Dòng chỉ đọc agent `provider + model + version` hoặc “chưa cấu hình”. Không có field provider. |
| Nhật ký | sau (1 = stub) | Proposal/risk sau. |
| Phong cách | 1 | Form YAML theo `specs/user-style-profile.md`; `GET|POST /api/user-style` append-only; không phải hard limit. |

Key AI nhập trên trang Cấu hình AI, che ký tự giữa, lưu localStorage máy này. Gemini: mọi key ngang hàng, bốc ngẫu nhiên khi gọi/check. OpenAI-compatible: một key. Notice/log/lịch sử không in giá trị key. Check live đi qua `POST /api/ai-check` khi chạy `npm start` (Origin local; không gửi key tới URL nội bộ), hoặc gọi thẳng provider nếu proxy chưa có / URL local. Key Bitget Demo nhập trên trang Kết nối, ghi `.env` qua `POST /api/connect-credentials`; status vẫn chỉ hiện Đã có/Thiếu. `python -m http.server` không đọc/ghi được env.

Phiếu intent không còn trên UI; CLI `--proposal` vẫn nhận. GET Demo: Node `GET /api/bitget-snapshot` (chỉ `127.0.0.1` + Origin local) spawn [`trader/bitget_snapshot_cli.py`](../trader/bitget_snapshot_cli.py) → [`trader/bitget_readonly.py`](../trader/bitget_readonly.py) `snapshot()` (account, vị thế, lệnh chờ, fills `/order/fills`). Đề xuất cặp: Node `GET /api/pair-screen` spawn [`trader/pair_screen_cli.py`](../trader/pair_screen_cli.py) → public `tickers` rồi [`trading/pair_screen.py`](../trading/pair_screen.py) rank khối lượng 24h; frontend mới duyệt vào allowlist. Phong cách: Node `GET|POST /api/user-style` spawn [`trader/style_cli.py`](../trader/style_cli.py) → [`trading/style_load.py`](../trading/style_load.py) đọc/ghi `profile/user_style.yaml`; append-only, Origin local, không localStorage. Chu kỳ Demo: Node `POST /api/demo-cycle` spawn [`trader/demo_scan_cli.py`](../trader/demo_scan_cli.py) `cycle` → GET + equity + protect + scan; whitelist rỗng hoặc ngoài list thì không POST. Tick cũ: `POST /api/demo-scan` spawn `tick`. Kill Demo: Node `POST /api/demo-kill` spawn [`trader/demo_kill_cli.py`](../trader/demo_kill_cli.py); không gọi AI. Cấm khi `GROK_TRADER_ALLOW_LIVE=1` hoặc `BITGET_ENV` live. JSON đã lọc field; không dump raw account, không trả secret/header ký. Đối soát UI dùng snapshot + zone localStorage; không gọi [`trading/reconcile.py`](../trading/reconcile.py).

### Đợt sau: chu kỳ quét

Chi tiết nghiệp vụ: [`ai-agent-autonomous-trading.md`](ai-agent-autonomous-trading.md) mục 5.3. Dashboard GET **đã nối** (kèm fills gần nhất và đối soát UI với zone local). Field `position_review_interval` **đã có** trên form Mandate (phút, 1–240, gợi ý không tự lưu). Chu kỳ quét paper **đã có** CLI tick/loop local ([`trader/paper_scan_cli.py`](../trader/paper_scan_cli.py)): tới giờ gọi `PaperAgent.run()`, `plan_actions` 0–N; mặc định không POST, `--place-orders --i-confirm-demo` POST Demo trong whitelist. Frontend Tổng quan có **chu kỳ Demo** (`POST /api/demo-cycle` → [`trader/demo_scan_cli.py`](../trader/demo_scan_cli.py) `cycle`): GET mới, sổ equity bootstrap, protect flatten opt-in, scan nếu tới giờ; Chạy/Dừng timer, không tự loop khi mở trang; **Kill Demo** (`POST /api/demo-kill`). Đồng hồ bảo vệ paper **đã có** CLI local ([`trader/protect_clock_cli.py`](../trader/protect_clock_cli.py)), tách scan, module không POST. Chưa có: WebSocket.

- Chu kỳ quét thuộc agent: tới giờ phân tích lại rồi ra phương án (`plan_actions`). Nút Chạy trên Tổng quan bật timer frontend, không phải daemon Python.
- Đồng hồ bảo vệ (SL, fill, `UNKNOWN`) tách khỏi chu kỳ quét; UI không được hiểu hết giờ quét mới được canh stop.
