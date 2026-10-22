# Spec frontend local

## 1. Mục tiêu
Tạo một giao diện web chạy local để xem và mô phỏng luồng zone foundation hiện có: `preview -> status -> sync`. Giao diện chỉ phục vụ Demo/dry-run, giúp kiểm tra luồng và trạng thái trước khi có backend/frontend production.

## 2. Phạm vi

### Có
- Một HTML local, nhiều view trong-trang (hash). Khung nav hai nhóm: Cấu hình (Kết nối, Cấu hình AI, Mandate, Quyền AI, Phong cách) và Vận hành (Tổng quan, Bàn zone, Nhật ký). Chi tiết IA ở mục 8.
- Bàn zone: danh sách zone local với zone ID, symbol, side, state, giá tham chiếu và net PnL gần nhất.
- Trang Cấu hình AI: form agent (`provider`, `model`, `base_url` khi OpenAI-compatible, `request_timeout`) và API key trên trang (hiện rõ, không che). Object riêng, version riêng; không chờ Mandate. Gemini: nhiều key ngang hàng, mỗi key một nhãn; khi gọi hoặc Check live bốc ngẫu nhiên một key. OpenAI-compatible: một key. Nút Check live ping provider (không lưu version, không giao dịch); dòng kết quả gần nhất lưu local, không chứa key. Key lưu localStorage máy này; notice/log không in giá trị key.
- Trang Mandate: form khẩu vị subaccount (`granted_capital`, daily loss limit/action, loss streak/cooldown, drawdown limit/unit/reference, max leverage, symbol allowlist). Không có select `ai_autonomy` trên trang này. Giá trị 20% daily loss được điền sẵn nhưng phải lưu/xác nhận.
- Trang Quyền AI: chọn `PROPOSAL_ONLY` / `MANAGED_ZONE` / `AUTONOMOUS_WITHIN_MANDATE` kèm giải thích từng mode. Cùng một policy object với Mandate; đổi mode tạo policy version mới (copy field mandate còn lại). Chưa có Mandate đã lưu thì không lưu được quyền AI. Không có field provider/model. Có dòng chỉ đọc cấu hình agent hiện tại.
- Policy lưu version trong local storage; zone mới lưu snapshot policy version. Với mode `MANAGED_ZONE`, zone phải được người dùng tạo; mode `AUTONOMOUS_WITHIN_MANDATE` chỉ được hiển thị/cấu hình, không thực thi tự động trong frontend local.
- Form tạo zone preview với các đầu vào: symbol từ allowlist, side (`long`/`short`), ref price, zone loss limit, max order risk và SL percent tùy chọn. Thiếu policy thì không tạo zone.
- Chọn một zone để ghi một observation dry-run: mark price, realized PnL, unrealized PnL, fees, funding paid/received.
- Hiển thị kết quả sync, trạng thái zone và cờ triggered/reason nếu có.
- Dữ liệu mô phỏng được lưu local để reload trang hoặc đổi view không mất dữ liệu.
- Có trạng thái rỗng, loading giả lập tối thiểu và thông báo lỗi dễ hiểu.
- Trang Tổng quan mock: thanh ticker (symbol từ allowlist, last/mark/funding nhập tay local, equity để trống nếu chưa có số local), phiếu soạn intent (side long/short, loại lệnh limit, giá, khối lượng; leverage/margin chỉ đọc từ policy), tab Vị thế / Lệnh chờ / Tài sản rỗng rõ. Không chart, không nhãn Mua/Bán, không POST.
- Trang Kết nối: status Demo/dry-run và env đủ/thiếu (`BITGET_ENV`, `BITGET_API_KEY`, `BITGET_API_SECRET`, `BITGET_PASSPHRASE`, `GROK_TRADER_ALLOW_LIVE`). Không form secret, không in giá trị. GET Bitget chưa nối. Key vẫn điền `.env`.
- Stub (layout + copy “chưa làm”) cho Phong cách, Nhật ký cho đến khi đợt tương ứng làm.

### Không có
- Không gọi Bitget. AI provider chỉ được gọi từ nút Check live trên trang Cấu hình AI.
- Không nhập trade key Bitget hay dữ liệu tài khoản thật. Key AI nhập trên trang Cấu hình AI, hiện rõ trên form, chỉ lưu local; notice/log không in giá trị.
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
9. Đổi view bằng nav/hash: dữ liệu localStorage (policy, agent config, zone, observation) vẫn còn; không bị reset.
10. Chưa lưu Mandate: trang Quyền AI disable lưu; form tạo zone không tạo được zone. Cấu hình AI vẫn lưu được.
11. Lưu Mandate rồi đổi quyền AI: policy version tăng; các field khẩu vị được copy, không mất. Agent-config version không đổi.
12. Mở Tổng quan khi trống: last/mark/funding trống, equity là —, tab vị thế/lệnh/tài sản rỗng rõ, không hiện số sàn bịa.
13. Nhập last/mark/funding local, đổi view rồi reload: số ticker local còn; không có request Bitget.
14. Phiếu intent không có nhãn Mua/Bán và không gửi lệnh. Chưa có policy thì leverage/margin là —; có policy thì chỉ đọc `max_leverage` và `margin_mode`.
15. Mở Cấu hình AI, lưu Gemini + model + timeout + ít nhất một key có nhãn: version v1; reload còn nhãn và key hiện rõ trên form.
16. Chọn OpenAI-compatible: hiện `base_url` và một ô API key; thiếu `base_url` hoặc key thì không lưu. Gemini ẩn `base_url`, hiện danh sách key ngang hàng.
17. Quyền AI và Bàn zone hiện dòng chỉ đọc `provider + model + version` và số key (Gemini: “xoay ngẫu nhiên”) hoặc “chưa cấu hình”. Notice/readout không in giá trị key. Form Quyền AI không có field provider.
18. Gemini thiếu nhãn hoặc key thì không lưu; thông báo lỗi không chứa giá trị key. Reset Demo xóa cả cấu hình AI và key.
19. Check live: bốc ngẫu nhiên một Gemini key (không chia chính/phụ), ping provider, hiện OK/lỗi theo nhãn trên trang (không in key); không tạo version mới. Reload còn dòng check gần nhất.
20. Mở Kết nối: thấy Demo/dry-run, từng biến env Đã có/Thiếu, GET Bitget “chưa nối”; không có ô nhập key/secret/passphrase.
21. `GET /api/connect-status` và notice/readout chỉ trả `present`/`missing` (và nhãn mode đã biết); không chứa giá trị key. Reload/đổi view không lộ secret.

## 7. Tiêu chí chấp nhận
- Chạy được hoàn toàn trên local bằng một lệnh được ghi trong README.
- Người dùng thực hiện được đầy đủ luồng preview, status và sync mà không cần credential.
- Không có request mạng tới Bitget. Check live được phép gọi AI provider.
- Các test case chính ở mục 6 chạy đúng.
- Đã triển khai trong frontend local; chưa có backend, Bitget API hoặc giao dịch live.

## 8. Kiến trúc thông tin (IA)

Một file HTML. `ai_autonomy` vẫn nằm trong cùng policy object (`STORAGE_KEY`, schema v4). Cấu hình agent là object riêng `agentConfig` + `agentConfigVersions`, không nằm trong `isPolicy` và không đổi version mandate. Đổi provider/model/key tạo agent-config version mới. Gemini: mọi key ngang hàng, bốc ngẫu nhiên. Check live ping provider; không phải đường giao dịch.

### Sơ đồ và thứ tự mở khóa

```text
Cấu hình:  Kết nối → Cấu hình AI → Mandate → Quyền AI → Phong cách
Vận hành:  Tổng quan    Bàn zone    Nhật ký
```

- Cấu hình AI không chờ Mandate: chọn model trước khi cấp vốn được.
- Mandate đã lưu version → mới cho chọn/lưu quyền AI → mới cho tạo zone.
- Gọi agent sau này cần cả cấu hình AI và quyền. Check live chỉ ping model, không tạo zone hay lệnh.
- Tổng quan xem được sớm, kể cả trống.
- Phong cách và Nhật ký chừa nav; form YAML / nhật ký proposal làm sau.
- `AUTONOMOUS_WITHIN_MANDATE` chỉ lưu cấu hình; frontend không tự giao dịch.
- Không đổi provider giữa episode đang chạy — UI Demo chỉ lưu; chưa có episode live.

### Từng trang

| Trang | Đợt | Nội dung |
|---|---|---|
| Kết nối | 3 | Chỉ status Demo/dry-run và env đủ/thiếu, không in giá trị, không form API key. `GET /api/connect-status` đọc `.env`/OS env, chỉ trả present/missing và nhãn mode. GET Bitget chưa nối. Key vẫn `.env`. |
| Cấu hình AI | 1 | Form `provider` (`gemini` / `openai_compatible`), `model`, `base_url` (chỉ OpenAI-compatible), `request_timeout`. Gemini: danh sách `{ nhãn, key }` ngang hàng, strategy `random`. OpenAI-compatible: một `api_key`. Key hiện rõ trên form. Nút Check live ping provider (bốc random nếu Gemini); dòng trạng thái check gần nhất lưu local, không chứa key, không tạo version. Lưu = agent-config version mới. Không temperature, không max output tokens, không sửa prompt hệ thống, không tự bật AUTONOMOUS. |
| Mandate | 1 | Form khẩu vị. Không có select quyền AI. Không có field provider. |
| Quyền AI | 1 | 3 mode + giải thích. Disable lưu nếu chưa có policy. Lưu = policy version mới, copy field mandate. Dòng chỉ đọc agent `provider + model + version` hoặc “chưa cấu hình”. Không có field provider. |
| Phong cách | sau (1 = stub) | Form YAML theo `specs/user-style-profile.md`; không phải hard limit. |
| Tổng quan | 2 | Thanh ticker (symbol, last/mark/funding trống hoặc nhập tay local, equity local nếu có). Trái: phiếu soạn intent (side, limit, giá, KL); leverage/margin chỉ đọc từ policy. Phải/dưới: tab Vị thế, Lệnh chờ, Tài sản — rỗng rõ, không bịa số sàn. Không chart. |
| Bàn zone | 1 | Form tạo + sổ + observation như mục 2. Thiếu policy thì không tạo zone. Dòng chỉ đọc cấu hình agent hiện tại. |
| Nhật ký | sau (1 = stub) | Proposal/risk sau. |

Key AI nhập trên trang Cấu hình AI, hiện rõ, lưu localStorage máy này. Gemini: mọi key ngang hàng, bốc ngẫu nhiên khi gọi/check. OpenAI-compatible: một key. Notice/log/lịch sử không in giá trị key. Check live đi qua `POST /api/ai-check` khi chạy `npm start`, hoặc gọi thẳng provider nếu proxy chưa có. Key Bitget không nhập trên web: trang Kết nối chỉ hiện Đã có/Thiếu qua `GET /api/connect-status` (cần `npm start`). `python -m http.server` không đọc được env.

Phiếu soạn intent không ghi nhãn Mua/Bán, không POST, không gửi lệnh. Nối GET Demo (`trader/bitget_readonly.py`) lên UI là đợt sau: phải sửa câu “Không gọi Bitget” ở mục 2 và hỏi duyệt trước khi làm.
