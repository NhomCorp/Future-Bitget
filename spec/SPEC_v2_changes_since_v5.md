# SPEC v2 – Thay đổi kể từ bản v5 (vòng 5)

Tác giả: trhieu6179
Ngày: 2026-10-20 (UTC+7)
Bản gốc so sánh: `SPEC_v2_additions_draft.md` 1276 dòng tại commit ce48936 (bản sao `draft_v5_1276.md`). Bản mới: 1376 dòng.
Phạm vi: chỉ phần thay đổi, lấy từ `diff -U1` thật giữa hai bản (mục 4). Mức đặc tả: chưa có mã, chưa chạy test nào, không gọi endpoint riêng của Bitget. Không thêm tính năng: mọi thay đổi là sửa 8 điểm review + bảng thanh lý. SPEC.md và REVIEW_2026-10-20.md không đổi (sha256 OK).

## 1. Bảng đối chiếu (điểm → điều khoản → test → trạng thái)

Quy ước: **XONG** = có điều khoản + test viết trong tài liệu (mức đặc tả, chờ kiểm thử); **MỘT PHẦN** = còn phụ thuộc hành vi sàn chưa kiểm chứng hoặc quyết định chưa chốt; **CHƯA XỬ LÝ** = không có.

| Điểm | Điều khoản | Test | Trạng thái |
|---|---|---|---|
| Các điểm review đã chấp nhận (bỏ `preplace_guard`, bịt `ladder close --pct`, reduce huỷ mọi lớp chờ, TP theo trạng thái, R27w/R27s, mốc ngày UNKNOWN, bỏ ngoại lệ SAFE) → ghi "đã sửa ở mức đặc tả, chờ kiểm thử" | §0.1 (bảng mới) | U48, U42, U55, U25, U54, U57, D33, U53 (không đổi) | XONG (chỉ đổi cách ghi trạng thái) |
| 1. Hash vòng tròn: `ack_code` ra khỏi `hash_content`; băm trước, suy mã từ hash; mã anh gõ ở bảng `approvals` | §5.4, §5.6 (DB), §6B.3 | U67 (mới), U62 (sửa) | XONG |
| 2. Vốn Wide bỏ sót xô Nonstop → một sổ phân bổ chung `alloc_ledger`, đẳng thức `E_wide + E_risk + E_ns = E`, xô âm, refill/quét, tắt xô khi còn vị thế không giải phóng vốn | §3.1 (viết lại), §3.2, §6B.1, §8.4 (khoá "sổ lệch"), §10 CLI, §10.2 `alloc` | U68 (mới), U58 (sửa) | XONG (cách xử lý xô âm là mặc định chờ chủ: C41) |
| 3. Trần hồ sơ vs hằng cứng → `limit_eff = min(hồ sơ, cấu hình chế độ, hằng)`; hằng không thay trần hồ sơ; `params.nonstop` trong schema hồ sơ chỉ được ≤ trần hồ sơ; quy tắc đổi hồ sơ cho Nonstop | §3.5 mục 4a, §2.3, §2.4, §6B.2 N1, §6B.3 preview, §6B.6, §10.2, §10.3 | U69 (mới), U61 (sửa) | XONG |
| 4a. Reduce leg Nonstop không SL bị chặn ở CLOSING → điều kiện SL theo `sl_policy` (required / approved / none) ở RECONCILING, CLOSING, UPDATING_PROTECTION | §6A.8, §5.6 (`sl_policy`), §6B.5 | U70 (mới: approval → DONE) | XONG |
| 4b. U63 mâu thuẫn với việc đặt lại TP/SL theo plan | §6B.4 | U63 (sửa: 0 lệnh can thiệp do cảnh báo; TP/SL theo plan vẫn chạy, `cause=plan`) | XONG |
| 5. UNKNOWN close + phiên bản mới có thể đóng quá → khoá `UNRESOLVED_CLOSE` theo leg, lưu DB qua restart; được/chặn; đường đóng khẩn; gỡ khoá; không có duyệt bất chấp ở P1, sau `ops clear` preview in tổng có thể đóng | §6A.8, §6A.1, §5.6 `prior_unknown_op`, §8.4, §10 `ops clear` | U71 (mới, có restart), D38 (mới) | MỘT PHẦN: hành vi của sàn với lệnh close khi size đã 0 / lệnh close treo khi vị thế về 0 chưa kiểm chứng (D38 chưa chạy) |
| 6. `expires_at` quá rộng → chỉ chấm dứt quyền duyệt, gửi lệnh đóng mới, bước tăng rủi ro; đối soát / dọn / bảo vệ cho thao tác đã gửi trước hạn vẫn chạy | §6A.8, §6.5 mục 7, RECOVERING | U72 (mới) | XONG |
| 7. Khoá chống trùng của sổ: chọn mô hình **nhiều dòng / sự kiện**, khoá `(source_kind, source_id, line_type, ledger)`; funding chia 3 sổ, Wide = phần dư nên luôn cộng đúng bill | §3.1 | U58 (sửa, property test) | MỘT PHẦN: cách chia funding theo `Q·mark·rate` chưa so với bill thật (D33) |
| 8. Đóng 100%: thủ tục thường (huỷ lớp → bắt fill trễ → đóng size thật → xác nhận 0 → dọn) và thủ tục khẩn (đóng ngay → huỷ → vòng kiểm tới size 0 và 0 entry) | §6A.10 (mới), §6A.0, §9.3, §10 CLI, §10.2 `ladder_close` | U73, U74, D39 (mới) | XONG |
| Bảng thanh lý Nonstop: N2 tính theo **đường khớp** (mọi `d_k`, lớp kế tiếp tới được), bỏ quy đổi bội số làm quy tắc; số khớp với người review (16.34× / 32.73× / 60.05×) | §6B.2 N2, §6B.8 (bảng mới), §10.2 `min_liq_fill_path_pct`, C32 | U60 (sửa) | MỘT PHẦN: mô hình liq chưa so với `liquidationPrice` thật (D35 chưa chạy); ngưỡng C32 chưa chốt |
| Cổng pha cập nhật theo test mới | §9.7 Q-13, §6B.7, C39 | – | XONG |

Còn mở / một phần (tổng hợp): D38 (lệnh close khi size 0), D33 (chia funding vs bill thật), D35 (liq ước tính vs sàn), các câu hỏi C30–C42 chưa có trả lời của chủ, tên `businessType` của bill thanh lý (từ vòng 4, chưa kiểm). Hệ quả cần anh biết: với trần hiệu lực, hồ sơ Mạo hiểm hiện tại chỉ cho **5× cùng chiều / 7× tổng** cho mọi leg kể cả Nonstop, nên mọi thang trong bảng 6B.8 (≥ 16×) FAIL N1.

## 2. Câu hỏi cho chủ – đổi / mới

| # | Câu hỏi | Mặc định đề xuất | Đổi gì |
|---|---|---|---|
| C32 | (Nonstop) Ngưỡng thanh lý tối thiểu theo **đường khớp** (N2): mọi `d_k` (khoảng cách liq từ giá lớp k khi lớp k vừa khớp) | **Đề xuất 3%** (= mức "liq ≥ 3%" của SPEC 4.12.2). Không có quy đổi ra bội số: mỗi thang phải tính (vd 25.64× → 2.78% FAIL; 21.66× → 3.70% PASS). Lựa chọn khác: 2%, 1%. Kiểu 30–95× hiện tại của anh không qua 3% | đổi: ngưỡng áp cho mọi d_k của đường khớp; bỏ quy đổi "≈ ≤ 28×" |
| C33 | (Nonstop) Trần bội số | **Trần hiệu lực = min(hồ sơ, cấu hình Nonstop, hằng cứng)**; hằng cứng không thay trần hồ sơ. Với hồ sơ Mạo hiểm hiện tại: **5× cùng chiều / 7× tổng** cho mọi leg kể cả Nonstop. Muốn lớn hơn: nâng trần hồ sơ (tăng rủi ro §2.4, ≤ 15× / 20× cứng); > 15× = đổi hằng + leverage 50 (đổi mã + review). Mặc định: giữ như vậy, không có trần Nonstop riêng vượt hồ sơ | đổi: trần hiệu lực min(…); Mạo hiểm = 5× / 7×, không còn "giữ 15× / 20×" |
| C39 | (Nonstop) Pha | **PN**: sau cổng Demo P1 của Kiểm soát + U58 + U59–U67 + U68 (sổ nonstop) + U69 (phần Nonstop) + U70 + D34–D37 (§6B.7); không chờ thêm thời gian live | đổi: danh sách test của cổng PN |
| C41 | Xô âm (lỗ Scalp/Nonstop vượt vốn đã cấp): phần thiếu trừ vào vốn Wide dùng để tính size ngay (`E_wide_sizing = E − max(0, E_risk) − max(0, E_ns)`), xô khoá, refill chỉ khi xô không còn leg mở | Có | mới (điểm 2) |
| C42 | Khoá `UNRESOLVED_CLOSE` (lệnh đóng chưa xác định): chỉ gỡ khi xác định được, hoặc sau ≥ 24 h bằng `ops clear --confirm`; không có duyệt bất chấp ở P1 | Có | mới (điểm 5) |

## 3. Kết quả tính đường khớp (tính toán, không phải dữ liệu sàn)

Script `/workspace/scratch/spec_v2/r5/nonstop_fillpath.py` (Decimal, ETH long, P₁ 2400.00, E 524.7, mmr 0.5%, phí mở maker 0.02%, 1 leg). Bảng giống §6B.8.

| Kịch bản | lớp đầu / mult / d / số lớp | ×E khớp đủ | Liq khớp đủ | d_k theo từng lớp (%) | min d_k (lớp) | Lớp tới được trước liq | N2 3% | N2 2% | N2 1% |
|---|---|---|---|---|---|---|---|---|---|
| ~15× (lớp đầu 5×) | 5× / 0.87 / 0.15% / 4 | 16.34× | 2260.44 | 19.64 / 10.18 / 7.02 / 5.39 | 5.39% (L4) | 4/4 | PASS | PASS | PASS |
| ~20× (lớp đầu 5×) | 5× / 0.87 / 0.15% / 6 | 21.66× | 2293.94 | 19.64 / 10.18 / 7.02 / 5.39 / 4.38 / 3.70 | 3.70% (L6) | 6/6 | PASS | PASS | PASS |
| ~25× (lớp đầu 5×) | 5× / 0.87 / 0.15% / 8 | 25.64× | 2308.84 | 19.64 / 10.18 / 7.02 / 5.39 / 4.38 / 3.70 / 3.19 / 2.78 | 2.78% (L8) | 8/8 | FAIL | PASS | PASS |
| ~30× | 10× / 0.87 / 0.15% / 4 | 32.73× | 2334.19 | 9.56 / 4.79 / 3.16 / 2.30 | 2.30% (L4) | 4/4 | FAIL | PASS | PASS |
| ~60× | 10× / 0.87 / 0.15% / 11 | 60.05× | 2359.36 | 9.56 / 4.79 / 3.16 / 2.30 / 1.76 / 1.36 / 1.06 / 0.80 / 0.58 / 0.39 / 0.21 | 0.21% (L11) | 11/11 | FAIL | FAIL | FAIL |
| ~60×, d 0.11% | 10× / 0.87 / 0.11% / 11 | 60.04× | 2362.83 | 9.56 / 4.81 / 3.20 / 2.37 / 1.85 / 1.48 / 1.20 / 0.97 / 0.78 / 0.61 / 0.46 | 0.46% (L11) | 11/11 | FAIL | FAIL | FAIL |
| ~60×, d 0.18% | 10× / 0.87 / 0.18% / 11 | 60.03× | 2356.76 | 9.56 / 4.78 / 3.12 / 2.25 / 1.69 / 1.28 / 0.95 / 0.68 / 0.44 / 0.22 / 0.02 | 0.02% (L11) | 11/11 | FAIL | FAIL | FAIL |
| ~95× (lớp đầu 15×) | 15× / 0.87 / 0.15% / 13 | 96.14× | 2372.61 | 6.20 / 2.99 / 1.87 / 1.28 / 0.88 / 0.59 / 0.35 / 0.15 / -0.03 / -0.20 / -0.36 / -0.51 / -0.66 | -0.66% (L13) | 8/13 | FAIL | FAIL | FAIL |
| ~95× (mult 0.97, 12 lớp) | 10× / 0.97 / 0.15% / 12 | 101.76× | 2370.46 | 9.56 / 4.52 / 2.79 / 1.89 / 1.31 / 0.90 / 0.59 / 0.33 / 0.11 / -0.08 / -0.25 / -0.41 | -0.41% (L12) | 9/12 | FAIL | FAIL | FAIL |

## 4. Diff thật (`diff -U1 draft_v5_1276.md SPEC_v2_additions_draft.md`)

Khối diff dùng rào 4 dấu backtick vì bên trong có dòng ``` của tài liệu gốc.

````diff
@@ -26,3 +26,3 @@
 | C8 | Sửa N1–N6: bỏ `aggressive`; định nghĩa lại R14 & giới hạn số thang; `kill` giữ SL; TP dạng trigger không chiếm vị thế; execute dùng E đóng băng + "bất biến được duyệt"; sửa ví dụ Scalp | xem §9 |
-| C9 | Kiểm tra mới R26–R30 (R27 tách R27w/R27s); CLI mới; test U20–U58, D18–D33 (U49, D29 đã rút), B6–B9 | 5.2, 2.2, 10 |
+| C9 | Kiểm tra mới R26–R30 (R27 tách R27w/R27s); CLI mới; test U20–U74, D18–D39 (U49, D29 đã rút), B6–B9 | 5.2, 2.2, 10 |
 | C10 | **`reduce`**: giảm vị thế chủ động (chỉ đóng) để đẩy giá thanh lý xa, cả Wide và Scalp; preview liq một leg + xấu nhất toàn TK (có lớp chờ); **P1 chỉ market và luôn huỷ mọi lớp chờ của leg trước khi đóng**, vòng đời là máy trạng thái có phục hồi (kết quả không xác định → PENDING_RECONCILE, không tự gửi lại); **tắt cứng tới khi D26 chứng minh SL cấp vị thế vẫn bao phần còn lại** (chỉ `position_persist`; `preplace_guard` ngoài phạm vi); mọi đường đóng một phần chủ động đi qua cùng executor và cổng, `ladder close` chỉ 100%; nhánh chỉ-huỷ `entry_adjust` không gửi lệnh đóng; dùng được cả khi đang khoá; watcher cảnh báo thanh lý theo bậc và dựng sẵn đề xuất (không tự chạy). Maker → P1b, tự tìm khối lượng → P2 | mới (§6A); bổ sung 4.8, 4.12.3c |
@@ -32,2 +32,25 @@
 
+### 0.1 Trạng thái các điểm review (2026-10-20, vòng 5)
+
+Quy ước: "đã sửa ở mức đặc tả, chờ kiểm thử" = có điều khoản và test được viết trong tài liệu này, **chưa có mã, chưa chạy test nào**. Không điểm nào dưới đây được coi là đã kiểm chứng trên sàn.
+
+| Điểm | Điều khoản | Test | Trạng thái |
+|---|---|---|---|
+| Bỏ `preplace_guard` khỏi P1 | §6A.0, §10.3 | U48 | đã sửa ở mức đặc tả, chờ kiểm thử |
+| Bịt đường vòng `ladder close --pct` | §6A.0, §6.1 | U48 | đã sửa ở mức đặc tả, chờ kiểm thử |
+| Reduce P1 huỷ mọi lớp chờ (`cancel_all`) | §6A.4, §5.6 | U42 | đã sửa ở mức đặc tả, chờ kiểm thử |
+| TP sau reduce theo trạng thái | §6A.5 | U55, U42 | đã sửa ở mức đặc tả, chờ kiểm thử |
+| Bộ kiểm tham số tách Wide / Scalp (R27w / R27s) | §2.5 | U25, U54 | đã sửa ở mức đặc tả, chờ kiểm thử |
+| Mốc ngày lưu DB / dựng lại / UNKNOWN | §8.4 | U57, D33 | đã sửa ở mức đặc tả, chờ kiểm thử (nhánh dựng lại tắt tới D33) |
+| Bỏ ngoại lệ SAFE (số kỳ vọng chỉ từ B9) | §2.6 | U53 | đã sửa ở mức đặc tả, chờ kiểm thử |
+| V5-1 Hash vòng tròn với mã xác nhận Nonstop | §5.4, §6B.3 | U67 | đã sửa ở mức đặc tả, chờ kiểm thử |
+| V5-2 Vốn Wide bỏ sót xô Nonstop → một sổ phân bổ chung | §3.1, §6B.1 | U68 | đã sửa ở mức đặc tả, chờ kiểm thử |
+| V5-3 Trần hồ sơ vs hằng cứng → trần hiệu lực `min(…)` | §3.5 mục 4a, §2.3, §2.4, §6B.2 N1 | U69 | đã sửa ở mức đặc tả, chờ kiểm thử |
+| V5-4 Reduce leg Nonstop không SL bị chặn ở CLOSING; U63 mâu thuẫn | §6A.8 (`sl_policy`), §6B.4 | U70, U63 | đã sửa ở mức đặc tả, chờ kiểm thử |
+| V5-5 Đóng UNKNOWN + phiên bản mới có thể đóng quá | §6A.8 khoá `UNRESOLVED_CLOSE`, §8.4 | U71, D38 | một phần: hành vi của sàn với lệnh close khi size đã 0 chưa kiểm chứng (D38) |
+| V5-6 Phạm vi `expires_at` | §6A.8, §6.5 mục 7 | U72 | đã sửa ở mức đặc tả, chờ kiểm thử |
+| V5-7 Khoá chống trùng của sổ + chia funding 3 phần | §3.1 | U58 | một phần: cách chia funding chưa so với bill thật (D33) |
+| V5-8 Đóng 100%: lớp chờ, thủ tục thường / khẩn | §6A.10, §6A.0, §9.3 | U73, U74, D39 | đã sửa ở mức đặc tả, chờ kiểm thử |
+| V5-9 N2 theo đường khớp, bỏ quy đổi bội số | §6B.2 N2, §6B.8 | U60 | một phần: mô hình liq chưa so với `liquidationPrice` thật (D35); ngưỡng C32 chưa chốt |
+
 ---
@@ -186,2 +209,3 @@
   bucket: {share_pct: 0}
+  nonstop: null   # PN; chỉ Mạo hiểm (C30): {share_pct, samedir_x, total_x}; samedir_x ≤ trần cùng chiều của hồ sơ, total_x ≤ account.total_x (§3.5 mục 4a)
 params_hash: 4be1…
@@ -198,2 +222,3 @@
 | Hỗn hợp (vừa chặt vừa lỏng) | Coi là tăng | Đơn giản, an toàn |
+| Bật Nonstop / đổi `params.nonstop.*` (PN) | như mọi tham số: lỏng hơn = tăng (pending 24 h…), chặt hơn hoặc tắt = hạ; `profile set` từ chối nếu `params.nonstop.*` > trần tương ứng của hồ sơ hoặc > hằng cứng | Không có đường nào để trần Nonstop vượt trần hồ sơ (§3.5 mục 4a) |
 
@@ -239,19 +264,39 @@
 
-### 3.1 Sổ phụ (sub-ledger) trên một tài khoản cross
+### 3.1 Sổ phân bổ vốn (một sổ chung) trên một tài khoản cross
+
+Một tài khoản cross không thể tách ký quỹ → tách **về sổ sách và quy tắc**, còn kiểm tra thanh lý/exposure luôn dùng **toàn tài khoản**. Có **một** sổ chung `alloc_ledger` cho cả ba phần vốn: **Wide** (`wide`), **xô Scalp** (`scalp`), **xô Nonstop** (`nonstop`, PN – §6B). Vị thế/lệnh tay và mọi khoản không gán được thuộc `wide`.
+
+**Phân bổ (dòng `alloc`)**: khi xô được kích hoạt hoặc `bucket refill`: `E_risk_base = share_scalp × E_now`, `E_ns_base = share_ns × E_now` (đóng băng cho kỳ); mỗi lần cấp là một cặp dòng nội bộ `alloc` (−X ở `wide`, +X ở xô) nên tổng không đổi. `budget_risk = 50% × E_risk_base` (USDT, đóng băng cho kỳ).
+
+**Mô hình dòng sổ (chọn một mô hình duy nhất)**: **nhiều dòng sổ cho một sự kiện nguồn**, mỗi dòng có khoá duy nhất `(source_kind, source_id, line_type, ledger)`:
+
+| `line_type` | Nguồn (`source_kind`, `source_id`) | `amount` | Ghi vào |
+|---|---|---|---|
+| `open_fee` | fill mở (`fill`, `tradeId`; WS `fill`, đối soát `GET /api/v2/mix/order/fills`, `tradeSide=open`) | `totalFee` của fill (âm) | sổ của leg |
+| `close_pnl` | fill đóng (`fill`, `tradeId`) – TP, SL, reduce, `ladder close`, kill, thanh lý | `profit` của fill | sổ của leg |
+| `close_fee` | **cùng** fill đóng (`fill`, cùng `tradeId`) | `totalFee` của fill (âm) | sổ của leg |
+| `funding` | bill funding (`bill`, `billId`; `businessType=contract_settle_fee`, `GET /api/v2/mix/account/bill`) | phần chia (dưới) | **mỗi** sổ có leg trên symbol đó – tối đa 3 dòng cho 1 bill |
+| `alloc` / `sweep` | nội bộ (`internal`, `op_id`) | cấp vốn / quét số dư xô về `wide` | cặp dòng ± |
+| `transfer` | bill chuyển tiền vào/ra (`bill`, `billId`) | `amount` | `wide` |
+| `unattributed` | bill khác không gán được (`bill`, `billId`) | `amount` | `wide` + CAO |
+
+Vì khoá gồm `line_type` (và `ledger`), `close_pnl` và `close_fee` của cùng một `tradeId` là **hai dòng khác khoá**, không bao giờ đè nhau; ghi lại sự kiện cũ (khởi động lại, đối soát 15 phút) → trùng khoá → bỏ qua. Ghi **ngay khi sự kiện xảy ra** (không đợi đóng thang).
+
+**Chia funding** (bill chỉ có `symbol`, không có holdSide): với bill `F` của symbol S, phần lý thuyết của từng sổ `f_k = −sg·Q_k·mark·fundingRate` (Q_k = size các leg của sổ k trên S tại mốc; rate từ `GET /api/v2/mix/market/history-fund-rate`). Ghi `scalp = round2(f_scalp)`, `nonstop = round2(f_nonstop)` (chỉ khi sổ có leg trên S), và **`wide = F − scalp − nonstop`** (phần dư, gồm làm tròn và vị thế tay) → **ba phần luôn cộng đúng bằng `F`**. Nếu `|F − Σ_k f_k| > max(0.01, 1% |F|)` → CAO "funding lệch mô hình" (ghi lại cho D33). Cách chia theo mô hình này **chưa kiểm chứng** với bill thật (D33).
 
-Một tài khoản cross không thể tách ký quỹ → tách **về sổ sách và quy tắc**, còn kiểm tra thanh lý/exposure luôn dùng **toàn tài khoản**.
+**Số dư từng phần** tại t: `E_k(t) = Σ amount (mọi dòng của sổ k) + upnl_k(t)` (k = wide, scalp, nonstop; `upnl_k` = Σ uPnL mark của leg thuộc sổ k), với `E_wide` lúc khởi tạo sổ = E. Ký hiệu cũ: `E_risk = E_scalp`, `E_ns = E_nonstop`.
 
-- Khi hồ sơ có xô được kích hoạt (hoặc `bucket refill`): `E_risk_base = share × E` (đóng băng), `budget_risk = 50% × E_risk_base` (USDT, đóng băng cho kỳ).
-- Tại thời điểm t:
-  - `realized_risk(t)` = Σ `amount` trong `bucket_ledger` của kỳ, **ghi theo sự kiện ngay khi xảy ra** (không đợi đóng thang):
-    - `open_fee`: mỗi fill mở của leg Scalp (WS `fill`; đối soát `GET /api/v2/mix/order/fills`, `tradeSide=open`): `amount = totalFee` (âm) của fill.
-    - `close_pnl` + `close_fee`: mỗi fill đóng của leg Scalp (TP, SL, reduce, `ladder close`, kill): `profit` và `totalFee` của fill.
-    - `funding`: bill `businessType=contract_settle_fee` (`GET /api/v2/mix/account/bill`) tại mỗi mốc funding. Bill chỉ có `symbol`, không có holdSide: symbol chỉ có leg Scalp → ghi toàn bộ; symbol có cả Wide và Scalp → phần Scalp = `−sg·Q_scalp·mark·fundingRate` (rate từ `GET /api/v2/mix/market/history-fund-rate`, Q/mark tại mốc), phần còn lại thuộc Wide. Cách chia này **chưa kiểm chứng** với bill thật (D33 ghi nhận).
-    - Khoá chính `event_id` = `tradeId` (fill) / `billId` (bill) → khởi động lại không ghi trùng; đối soát lại mỗi 15 phút.
-  - `upnl_risk(t)` = Σ uPnL (mark) của thang Scalp đang mở.
-  - `E_risk(t) = E_risk_base + realized_risk + upnl_risk`; `E_wide(t) = E(t) − E_risk(t)`.
-- Wide luôn tính size/ngân sách theo `E_wide` (đóng băng ở preview); Scalp tính theo ngân sách xô.
-- **Ngân sách đã dùng** `used = max(0, −realized_risk) + Σ worst_loss(thang Scalp đang mở)` với `worst_loss` = WCL §6.3 (lỗ tại SL + trượt 0.3%) **trừ phần đã ghi sổ** (phí mở của lớp đã khớp và `realized_leg`), để không tính hai lần. Lãi Scalp **không** làm tăng `budget_risk` trong kỳ (lãi ở lại xô, cuối kỳ quét về phần an toàn qua refill).
-- R28 (mới, mở thang Scalp): `used + worst_loss(thang mới) ≤ budget_risk` **và** `worst_loss(thang mới) ≤ per_ladder_scalp` (bảng 2.2).
-- Wide không bao giờ được tính trên `E_risk`; Scalp không bao giờ được dùng `E_wide` hay phần ngân sách R14 dành cho Wide (chia ngân sách R14 và mọi cap dùng chung: §3.5).
+**Đẳng thức đối soát** (kiểm mỗi 15 phút và trước mọi hành động tăng rủi ro): `E_wide(t) + E_risk(t) + E_ns(t) = E(t)` (equity tài khoản theo mark), dung sai `alloc.reconcile_tol_usdt` (0.05). Lệch → tải lại fills/bill thiếu; còn lệch → `unattributed` không giải thích được → CAO + **chặn mọi hành động tăng rủi ro** (như cột "Bộ đếm UNKNOWN" §8.4) tới khi đẳng thức đạt.
+
+**Vốn Wide dùng để tính size**: `E_wide_sizing(t) = E(t) − max(0, E_risk(t)) − max(0, E_ns(t))` (đóng băng ở preview). Ví dụ E = 524.70, xô Scalp 10% và xô Nonstop 10% vừa cấp: `E_wide_sizing = 524.70 − 52.47 − 52.47 = 419.76` (công thức cũ `E − E_risk` cho 472.23 – **sai**, đã bỏ).
+
+**Xô âm**: xô không bị chặn dưới 0 (Nonstop không có SL; Scalp có thể trượt/gap). Khi `E_risk(t) < 0` hoặc `E_ns(t) < 0`: phần âm **đã nằm trong E** (lỗ thật trên ký quỹ chung), và `max(0, ·)` ở công thức trên làm `E_wide_sizing` = E − phần dương còn lại → **phần thiếu của xô trừ thẳng vào vốn Wide dùng để tính size** (C41). Xô âm = xô khoá (§3.2, 6B.1); `deficit_k = −E_k` hiển thị ở `bucket status`.
+
+**Refill / quét**: `bucket refill [--nonstop] --confirm` (theo §3.2): (1) ghi `sweep` chuyển toàn bộ số dư **đã thực hiện** của xô (dương hoặc âm) về `wide`; (2) cấp mới `alloc = share × E_now`. Chỉ được refill khi xô **không còn leg mở và không còn lệnh chờ** (uPnL = 0); nếu không → từ chối "còn thang đang mở trong xô".
+
+**Tắt xô / hạ share khi còn vị thế**: `profile set --bucket 0` hoặc `--nonstop-bucket 0` (hạ rủi ro, hiệu lực ngay) **chỉ** chặn mở thang mới trong xô đó; vốn đã phân bổ **không** được giải phóng: sổ xô giữ nguyên (`alloc` cũ, mọi dòng mới của leg còn mở vẫn ghi vào xô), `E_wide_sizing` vẫn trừ phần dương của xô. Giải phóng (`sweep` về `wide`) **tự động** chỉ khi mọi leg của xô có size 0 **và** không còn lệnh chờ **và** đẳng thức đối soát đạt.
+
+**Ngân sách đã dùng (Scalp)**: `realized_risk` = Σ `amount` dòng của sổ `scalp` trong kỳ, trừ `alloc`/`sweep`; `used = max(0, −realized_risk) + Σ worst_loss(thang Scalp đang mở)` với `worst_loss` = WCL §6.3 (lỗ tại SL + trượt 0.3%) **trừ phần đã ghi sổ** (phí mở của lớp đã khớp và `realized_leg`), để không tính hai lần. Lãi Scalp **không** làm tăng `budget_risk` trong kỳ (lãi ở lại xô, cuối kỳ quét về `wide` qua refill).
+- R28 (mở thang Scalp): `used + worst_loss(thang mới) ≤ budget_risk` **và** `worst_loss(thang mới) ≤ per_ladder_scalp` (bảng 2.2).
+- Wide không bao giờ được tính trên vốn xô; Scalp/Nonstop không bao giờ được dùng `E_wide` hay phần ngân sách R14 dành cho Wide (chia ngân sách R14 và mọi cap dùng chung: §3.5).
 
@@ -262,3 +307,3 @@
 - **Mở khoá**: sớm nhất **07:00 UTC+7 ngày 1 tháng sau VÀ ≥ 7 ngày kể từ lúc khoá**, rồi chủ chạy `bucket refill --confirm` (không tự refill). Refill: `E_risk_base = share × E_now`; bị từ chối nếu đang khoá ngày/tuần/DD. Đây là cấp vốn mới cho kỳ mới, không phải "vay" giữa kỳ.
-- Lỗ vượt ngân sách do trượt/gap: ghi `overshoot`, hiển thị; kỳ sau `budget_risk` trừ đi `overshoot`.
+- Lỗ vượt ngân sách do trượt/gap: ghi `overshoot`, hiển thị; kỳ sau `budget_risk` trừ đi `overshoot`. Xô âm, refill/quét và tắt xô khi còn vị thế: §3.1.
 - Thành thật trong README/UX: tách xô là **kỷ luật sổ sách**; trên sàn, lỗ Scalp vẫn trừ vào cùng ký quỹ cross. Vì vậy:
@@ -306,2 +351,4 @@
 
+   **4a. Trần hiệu lực** (mọi kiểm tra có cả trần hồ sơ và hằng cứng: R8, R9w, R9a, R10w, R10a, R14, N1): `limit_eff = min(trần hồ sơ đang hiệu lực, trần theo chế độ trong hồ sơ hoặc cấu hình nếu có, hằng cứng)`. Hằng cứng chỉ là **giới hạn trên cho giá trị của hồ sơ/cấu hình** (kiểm khi `profile set` / khởi động: vượt → từ chối), **không bao giờ** thay thế trần hồ sơ khi kiểm plan. Ô "–" của bảng 2.2 (vd Thận trọng cùng chiều Wide + Scalp) = không có xô nên chỉ có leg Wide, dùng R10w. Thông báo FAIL in đủ các số và số nào thắng, vd "R10a: 6.10× > 5.00× (hồ sơ Mạo hiểm; cấu hình Nonstop 15×; cứng 15×)". Nonstop **không** có trần riêng vượt hồ sơ: `params.nonstop.{samedir_x, total_x}` (nếu có) chỉ được ≤ trần tương ứng của hồ sơ (§2.3) – muốn Nonstop lớn hơn thì phải nâng trần hồ sơ theo quy tắc tăng rủi ro §2.4, vẫn ≤ hằng cứng (C33).
+
    Hệ quả: Scalp lớn không làm FAIL R10w của Wide nhưng có thể làm FAIL R10a → `propose` thu nhỏ Wide (bước 6 §4) hoặc bỏ ứng viên. Ví dụ Mạo hiểm: R14 phần Wide ≤ 25% − 5% = 20% (3 thang Wide 15.98% ✓), toàn TK 20.82% ✓.
@@ -373,3 +420,4 @@
 - `content_hash` = SHA-256(`canonical_json(hash_content)`); DB lưu đủ 64 hex, hiển thị 6 hex đầu.
-  - `hash_content` = **mọi trường** của phiên bản trừ `status`, `content_hash`, `edit_log[].text` (lời chat thô) và thời điểm đo của checks; tức gồm `schema, root_id, version, version_id, parent, kind, env, created_at, expires_at, profile{version, params_hash}, regime, mode, symbol, side, anchor, frozen, params, layers, derived, checks{id,status,value,limit}, light, override_reason` với `regime: nonstop` cả khối `nonstop` (N1–N4: `liq_all_fill`, `multiple_all_fill_x`, `ack_code`, `sl_present`, `tp_present`), và, với `kind ∈ {reduce, entry_adjust}`, **toàn bộ** khối `reduce`/`entry_adjust` (§5.6: leg, close_qty, qty_source input + resolved, exec_mode, sl_mode, entry_actions, preconditions, tolerances, expected_after, steps, client_oids).
+  - `hash_content` = **mọi trường** của phiên bản trừ `status`, `content_hash`, `edit_log[].text` (lời chat thô) và thời điểm đo của checks; tức gồm `schema, root_id, version, version_id, parent, kind, env, created_at, expires_at, profile{version, params_hash}, regime, mode, symbol, side, anchor, frozen, params, layers, derived, checks{id,status,value,limit}, light, override_reason` với `regime: nonstop` cả khối `nonstop` (`liq_all_fill`, `multiple_all_fill_x`, `fill_path`, `min_d_pct`, `limits_eff`, `sl_present`, `tp_present`), và, với `kind ∈ {reduce, entry_adjust}`, **toàn bộ** khối `reduce`/`entry_adjust` (§5.6: leg, close_qty, qty_source input + resolved, exec_mode, sl_mode, entry_actions, preconditions gồm `sl_policy`, tolerances, `prior_unknown_op`, expected_after, steps, client_oids).
+  - **Không** thuộc `hash_content` (và không nằm trong bản ghi plan): mã xác nhận Nonstop. Trình tự cố định: (1) dựng phiên bản; (2) băm → `content_hash`; (3) suy mã `ack_expected = "NS-" + content_hash[0:6] + "-" + fmt2(min_d_pct)` (hàm tất định của nội dung đã băm); (4) khi duyệt, mã anh gõ được ghi vào bảng riêng `approvals(approval_id, version_id, content_hash, ack_entered, ack_expected, result[accepted|rejected], channel, created_at)`. Ghi `approvals` **không** đổi bản ghi plan nên không đổi hash (6B.3, U67).
   - `canonical_json`: UTF-8; khoá sắp xếp theo thứ tự byte; không khoảng trắng (`,` và `:`); giá/size/USDT là **chuỗi Decimal** định dạng cố định theo `pricePlace`/`volumePlace` của symbol (vd `"2385.62"`, `"0.64"`), USDT 2 chữ số, tỉ lệ % 4 chữ số (`"0.3000"`); thời gian = số nguyên epoch ms UTC; boolean/null theo JSON; mảng giữ thứ tự (lớp theo `idx` tăng dần); **cấm float JSON** (gặp float → lỗi).
@@ -439,3 +487,3 @@
 ```
-DB: bảng `plans` của SPEC 8.1 thêm cột `root_id, version, parent, kind, profile_version, anchor_mode, frozen_json, light_json, override_reason, reduce_json, observed_state_json`.
+DB: bảng `plans` của SPEC 8.1 thêm cột `root_id, version, parent, kind, profile_version, anchor_mode, frozen_json, light_json, override_reason, reduce_json, observed_state_json`. Bảng mới: `approvals` (§5.4), `alloc_ledger` (§3.1), `leg_locks` (6A.8).
 **Mở rộng schema cho `kind: reduce` và `kind: entry_adjust`** (YAML hiển thị giờ ISO cho người đọc; dạng băm dùng epoch ms – §5.4):
@@ -464,2 +512,3 @@
     leg_state: ACTIVE     # ACTIVE | TP1_DONE | PROTECT_ONLY – quyết định TP sau đóng (6A.5)
+    sl_policy: required   # required (Kiểm soát) | approved (Nonstop có SL) | none (Nonstop không SL) – điều kiện SL ở RECONCILING / CLOSING / UPDATING_PROTECTION (6A.8)
     position_size: "2.14"
@@ -473,6 +522,6 @@
   tolerances: {mark_drift_pct: "0.3000", equity_drift_pct: "1.0000", reconcile_window_s: 120}
-  prior_unknown_op: null  # op_id nếu có lệnh đóng trước của leg còn UNKNOWN (preview phải cảnh báo)
+  prior_unknown_op: null  # {op_id, client_oid, qty} nếu leg vừa được gỡ khoá UNRESOLVED_CLOSE bằng `ops clear` mà X vẫn chưa xác định; preview in tổng có thể đóng = close_qty + qty (6A.8)
   expected_after:
     position_size: "1.50"
-    protection: {sl_count: 1, plan_type: pos_loss, trigger: "2359.09", covers: position}   # chỉ khi position_size > 0
+    protection: {sl_count: 1, plan_type: pos_loss, trigger: "2359.09", covers: position}   # chỉ khi position_size > 0; sl_policy none → sl_count: 0
     tp_rule: active_no_t1_fill   # 6A.5 dòng 1; size thật tính lại ở UPDATING_PROTECTION
@@ -569,3 +618,3 @@
   6. Kết thúc phục hồi: phiên bản → `applied_partial` (hoặc `aborted` nếu chưa có ghi nào) với `observed_state` (giá/size thật từng lớp, SL thật, TP thật, vị thế, các op `unknown`) lưu DB; mọi sửa tiếp theo tính diff **từ `observed_state`**; phần chưa làm chỉ được tiếp tục bằng **phiên bản mới được duyệt**.
-  7. `expires_at` của phiên bản là hạn duy nhất cho mọi lần gửi; phục hồi không gia hạn.
+  7. `expires_at` của phiên bản là hạn duy nhất cho quyền gửi **lệnh mới** (lệnh đóng mới, kể cả gửi lại; mọi bước tăng rủi ro); phục hồi không gia hạn. Đối soát, hoàn tất huỷ đã bắt đầu, bảo vệ SL/TP và dọn lệnh cho thao tác **đã gửi trước hạn** vẫn chạy sau hạn theo quy tắc đã duyệt (6A.8).
 - Gửi lại tối đa `HARD_REDUCE_MAX_RESEND = 2` lần, chỉ cho lời gọi idempotent hoặc `VERIFIED_NOT_RECEIVED`; vượt → `FAILED_SAFE` + CAO. Bất biến I1 do watcher giữ song song suốt quá trình (thiếu SL → đặt ngay).
@@ -602,5 +651,5 @@
 | `reduce apply` | có | executor 6A.8; cổng `position_persist` |
-| `ladder close <root> --confirm` | **không** – luôn 100% | `close-positions` (holdSide); không có `--pct`; xác nhận size = 0 rồi mới huỷ SL/TP (D28). Đóng một phần = `reduce` |
+| `ladder close <root> --confirm` | **không** – luôn 100% | **thủ tục thường §6A.10**: huỷ mọi lớp chờ + TP → bắt fill trễ → `close-positions` (holdSide) size thật → xác nhận size 0 → dọn SL/lệnh sót (D28, D39, U73); không có `--pct`. Đóng một phần = `reduce` |
 | `scalp scaleout` (SPEC 4.12.3, limit post-only một phần) | có | = reduce maker (P1b) qua executor 6A.8, cùng `entry_policy: cancel_all` (bỏ tuỳ chọn giữ DCA của SPEC 4.12.3); bị từ chối khi reduce hoặc maker tắt |
-| `kill --close-positions`, `on_sl_failure: close_leg` (SPEC 8.2(3)), `fail_execute` của `pos_loss`/BE (§9.4), Q-7 khi SL/BE đã vượt trigger | không – luôn 100% | `close-positions` (holdSide); quy tắc riêng đã có và đã có test: U31, U32, D23, D28 |
+| `kill --close-positions`, `on_sl_failure: close_leg` (SPEC 8.2(3)), `fail_execute` của `pos_loss`/BE (§9.4), Q-7 khi SL/BE đã vượt trigger | không – luôn 100% | **thủ tục khẩn §6A.10**: `close-positions` (holdSide) ngay → huỷ mọi lớp chờ + TP → vòng kiểm tới khi size 0 và 0 entry; test U31, U32, U74, D23, D28, D39 |
 | Q-7 khi **TP** đã vượt trigger lúc đặt/đặt lại TP | (cũ: đóng ngay phần TP bằng market) | **Không đóng một phần.** Không gửi lệnh đóng; bỏ qua TP đó + CAO "TP{n} chưa đặt được vì giá đã vượt; SL vẫn trên sàn"; watcher thử đặt lại khi mark quay về phía hợp lệ (§9.7 Q-7) |
@@ -624,3 +673,3 @@
 - **Nhánh chỉ-huỷ**: nếu khối lượng giảm giải ra = 0 (vd `--qty 0`, hoặc phương án chỉ cần huỷ lớp) → công cụ **không** tạo `kind: reduce`; tạo `kind: entry_adjust` và nói rõ "không gửi lệnh đóng". Không có đường code nào gửi lệnh close với size 0.
-- Được phép khi đang khoá (ngày/tuần/DD/chuỗi stop/xô/bộ đếm UNKNOWN §8.4), khi `kill` ở `PROTECT_ONLY`, khi hồ sơ `pending`. Không được khi leg đang `RECONCILING`/`RECOVERING`/`PENDING_RECONCILE`, có `DRIFT` (Q-10), hoặc đang có một op khác trên leg (khoá op theo leg).
+- Được phép khi đang khoá (ngày/tuần/DD/chuỗi stop/xô/bộ đếm UNKNOWN §8.4), khi `kill` ở `PROTECT_ONLY`, khi hồ sơ `pending`. Không được khi leg đang `RECONCILING`/`RECOVERING`/`PENDING_RECONCILE`, có khoá `UNRESOLVED_CLOSE` (6A.8), có `DRIFT` (Q-10), hoặc đang có một op khác trên leg (khoá op theo leg).
 
@@ -719,3 +768,3 @@
 
-**Hạn duy nhất**: mỗi phiên bản reduce/entry_adjust có một `expires_at = created_at + 120 s`, nằm trong hash, **bất biến**. Mọi nhánh có gửi lệnh (apply, gửi close, gửi lại sau crash) đều kiểm `now < expires_at` ngay trước HTTP. Duyệt không gia hạn; crash không gia hạn; không có "120 s tính từ lúc duyệt".
+**Hạn (`expires_at`) – phạm vi**: mỗi phiên bản reduce/entry_adjust có một `expires_at = created_at + 120 s`, nằm trong hash, **bất biến**; duyệt không gia hạn, crash không gia hạn, không có "120 s tính từ lúc duyệt". `expires_at` **chỉ** chấm dứt quyền: (a) duyệt (`apply`); (b) gửi một **lệnh đóng mới** (`place-order` close, kể cả gửi lại sau crash theo `VERIFIED_NOT_RECEIVED`) – kiểm `now < expires_at` ngay trước HTTP; (c) bất kỳ bước tăng rủi ro nào. `expires_at` **không** chặn phần tiếp theo của thao tác **đã gửi trước hạn**: đối soát (`PENDING_RECONCILE`, RECOVERING), hoàn tất huỷ lớp chờ/TP đã bắt đầu (giảm rủi ro, idempotent), `UPDATING_PROTECTION` (đặt lại TP theo bảng 6A.5, xác minh/giữ SL), dọn lệnh sót, đặt lại TP ở `FAILED_SAFE` – các bước này chạy theo đúng quy tắc của phiên bản đã duyệt, kể cả sau hạn (U72).
 
@@ -732,5 +781,5 @@
 | → CANCELLING_ENTRIES | RECONCILING đạt | reduce: `cancel-order` **mọi** lớp chờ của leg + `cancel-plan-order` mọi TP (`profit_plan`) của leg, theo clientOid; entry_adjust: chỉ các lớp đã chọn, TP giữ nguyên | `order/detail` = `cancelled`; TP không còn trong `orders-plan-pending`; size vị thế không đổi | 10 s/lệnh; huỷ là idempotent → gửi lại tối đa 2 lần (truy vấn trước) | lớp đã `filled`/khớp một phần → `FAILED_SAFE` (không đóng; giữ các huỷ đã làm; đặt lại TP theo bảng 6A.5 cho size thật; đề xuất phiên bản mới); lỗi khác → `FAILED_SAFE` (cũng đặt lại TP) |
-| → CLOSING | `pos_loss` còn trên sàn (đọc lại); `now < expires_at` kiểm ngay trước HTTP | journal `sent` → `place-order` market close `close_qty` (clientOid `X`) | `order/detail?clientOid=X` filled; `single-position` size = trước − filled (± lot) | 10 s | `FOUND` filled đủ → UPDATING_PROTECTION; `FOUND` kết thúc với khớp một phần → ghi thực tế, UPDATING_PROTECTION với size thật, phần chưa đóng **không** gửi lại; `REJECTED` → `FAILED_SAFE` (đặt lại TP); size giảm nhiều hơn (SL/TP đồng thời) → đối soát → UPDATING_PROTECTION (có thể `Q_after = 0`); `UNKNOWN` → **PENDING_RECONCILE, không gửi lại** |
-| CLOSING → PENDING_RECONCILE | kết quả `UNKNOWN` | không gửi lệnh mới nào cho leg (watcher vẫn giữ I1: thiếu SL → đặt `pos_loss`) | mỗi 2 s trong `reconcile_window_s` = 120 s: `order/detail?clientOid=X`, `fills` (`GET /api/v2/mix/order/fills`, symbol, từ lúc `sent`), `single-position`, WS `orders`/`fill` | 120 s | xác định được (lệnh X thấy ở bất kỳ trạng thái nào, hoặc fill có orderId của X) → xử lý như `FOUND`; hết cửa sổ vẫn không xác định → `FAILED_SAFE (close_unknown)`: CAO; **không bao giờ tự gửi lại**; tiếp tục dò nền mỗi 60 s trong 24 h; phiên bản reduce mới chỉ được tạo từ trạng thái quan sát và preview của nó PHẢI cảnh báo "lệnh đóng trước chưa xác định; nếu nó khớp muộn, tổng khối lượng đóng có thể lớn hơn dự định" (trường `prior_unknown_op` trong hash). Gửi lại tự động chỉ khi `VERIFIED_NOT_RECEIVED` **và** `now < expires_at` (cùng clientOid) |
-| → UPDATING_PROTECTION | close đã xác định | đọc `single-position`, `orders-plan-pending`, fill T1/T2; đặt TP theo bảng 6A.5 (`place-tpsl-order profit_plan`, clientOid rev+1); `Q_after = 0` → huỷ lệnh còn sót | `Q_after > 0`: đúng 1 SL cấp vị thế, trigger = SL phiên bản (±1 tick), TP đúng bảng 6A.5; `Q_after = 0`: không còn lệnh nào của leg | 30 s | thiếu SL khi còn vị thế → KHẨN + đặt `pos_loss` ngay + `REDUCE_SL_MODE` runtime → disabled; TP lỗi → CAO, theo quy tắc bước `place`, không chặn DONE |
+| → CLOSING | SL đúng `sl_policy` của leg (đọc lại, như RECONCILING): `required` / `approved` → `pos_loss` còn trên sàn, trigger = snapshot; `none` (Nonstop không SL) → **0** `pos_loss` (thấy SL lạ → `FAILED_SAFE`, không đóng); `now < expires_at` kiểm ngay trước HTTP | journal `sent` → `place-order` market close `close_qty` (clientOid `X`) | `order/detail?clientOid=X` filled; `single-position` size = trước − filled (± lot) | 10 s | `FOUND` filled đủ → UPDATING_PROTECTION; `FOUND` kết thúc với khớp một phần → ghi thực tế, UPDATING_PROTECTION với size thật, phần chưa đóng **không** gửi lại; `REJECTED` → `FAILED_SAFE` (đặt lại TP); size giảm nhiều hơn (SL/TP đồng thời) → đối soát → UPDATING_PROTECTION (có thể `Q_after = 0`); `UNKNOWN` → **PENDING_RECONCILE, không gửi lại** |
+| CLOSING → PENDING_RECONCILE | kết quả `UNKNOWN` | không gửi lệnh mới nào cho leg (watcher vẫn giữ I1: thiếu SL → đặt `pos_loss`) | mỗi 2 s trong `reconcile_window_s` = 120 s: `order/detail?clientOid=X`, `fills` (`GET /api/v2/mix/order/fills`, symbol, từ lúc `sent`), `single-position`, WS `orders`/`fill` | 120 s | xác định được (lệnh X thấy ở bất kỳ trạng thái nào, hoặc fill có orderId của X) → xử lý như `FOUND`; hết cửa sổ vẫn không xác định → `FAILED_SAFE (close_unknown)` + leg giữ **khoá `UNRESOLVED_CLOSE`** (dưới): CAO; **không bao giờ tự gửi lại**; dò nền mỗi 60 s trong 24 h; **không** được tạo/duyệt reduce mới cho leg khi khoá còn. Gửi lại tự động chỉ khi `VERIFIED_NOT_RECEIVED` **và** `now < expires_at` (cùng clientOid) |
+| → UPDATING_PROTECTION | close đã xác định | đọc `single-position`, `orders-plan-pending`, fill T1/T2; đặt TP theo bảng 6A.5 (`place-tpsl-order profit_plan`, clientOid rev+1); `Q_after = 0` → huỷ lệnh còn sót | `Q_after > 0`: theo `sl_policy` – `required`/`approved`: đúng 1 SL cấp vị thế, trigger = SL phiên bản (±1 tick); `none`: 0 SL; TP đúng bảng 6A.5 (Nonstop: chỉ khi plan có TP); `Q_after = 0`: không còn lệnh nào của leg | 30 s (chạy cả sau `expires_at`) | thiếu SL khi còn vị thế (chỉ `required`/`approved`) → KHẨN + đặt `pos_loss` ngay + `REDUCE_SL_MODE` runtime → disabled; TP lỗi → CAO, theo quy tắc bước `place`, không chặn DONE |
 | → DONE | mọi xác minh đạt | – | ghi journal, WCL, liq sau thực tế; nhả khoá; thông báo "Reduce xong" | – | – |
@@ -738,2 +787,9 @@
 
+**Khoá `UNRESOLVED_CLOSE` (P1)** – đặt ngay khi một lệnh đóng của leg có kết quả `UNKNOWN` (vào `PENDING_RECONCILE`), từ `reduce`, `ladder close` hoặc thủ tục khẩn (6A.10). Ghi DB `leg_locks(leg_id, kind=unresolved_close, op_id, client_oid, qty_max, created_at, cleared_at, cleared_by[resolved|ops_clear], note)` **trước** khi trả lời người dùng; nạp lại khi khởi động (sống qua restart, không có TTL ngầm).
+- **Bị chặn** khi khoá còn (trên leg và cặp (symbol, holdSide) đó): tạo/duyệt `reduce` mới; `execute` mở thang mới; `ladder apply` có PLACE_ENTRY hoặc SL_LOOSEN; watcher đặt/đặt lại lớp entry.
+- **Luôn được**: đối soát/dò nền; `entries --cancel*` (entry_adjust); bảo vệ SL (I1/I1n, SL_TIGHTEN, watcher đặt `pos_loss` thiếu); đặt lại TP theo size thật (TP là lệnh trigger trên vị thế, không gửi lệnh đóng ngay); `kill` (PROTECT_ONLY).
+- **Đường đóng khẩn khi đang khoá**: chỉ `ladder close` (thủ tục thường 6A.10) hoặc `kill --close-positions --confirm-close` (thủ tục khẩn 6A.10). Cả hai dùng `close-positions` theo **size thật** của sàn, không gửi size tự tính, nên X nếu đã khớp thì size đọc được đã nhỏ hơn – không có "đóng quá" do cộng dồn hai khối lượng. Sau đó leg `CLOSED`, khoá **vẫn giữ** (chặn mở lại cùng (symbol, holdSide), để X nếu còn sống không đóng vào vị thế mới) tới khi được gỡ. Hành vi của sàn với một lệnh close khi size đã 0 **chưa kiểm chứng** (D38).
+- **Gỡ khoá**: tự động khi X xác định được (thấy lệnh X ở bất kỳ trạng thái nào, hoặc fill có orderId của X) → xử lý như `FOUND`, `cleared_by=resolved`; hoặc sau ≥ 24 h dò nền không thấy dấu vết, bằng `ops clear <op_id> --confirm` (C42; preview in qty X, số lần dò, size hiện tại).
+- **Không có "duyệt bất chấp" ở P1.** Sau khi gỡ bằng `ops clear` (X vẫn chưa xác định), trong 24 h kế tiếp mọi preview `reduce` của leg PHẢI in **tổng khối lượng có thể bị đóng** = `close_qty` mới + `qty_X` (và `min(tổng, size hiện tại)`), không chỉ câu cảnh báo chung; `prior_unknown_op {op_id, client_oid, qty}` nằm trong hash.
+
 **RECOVERING** (khởi động lại hoặc mất kết nối giữa op; chạy trong reconcile §6.5): đọc `op_journal`, chụp REST đầy đủ (gồm kiểm chế độ tài khoản như RECONCILING), với từng bước:
@@ -741,3 +797,3 @@
 - `CLOSING` còn `planned` (chưa `sent`) → `VERIFIED_NOT_RECEIVED (a)`: được gửi nếu `now < expires_at` và đối soát lại đạt; ngược lại `FAILED_SAFE`.
-- `CLOSING` đã `sent` → truy vấn: `FOUND` → tiếp tục như bảng; mọi kết quả khác → `PENDING_RECONCILE` (không gửi lại; trừ `VERIFIED_NOT_RECEIVED (b)` với cùng clientOid và `now < expires_at`).
+- `CLOSING` đã `sent` → truy vấn: `FOUND` → tiếp tục như bảng (kể cả khi đã quá `expires_at`: UPDATING_PROTECTION vẫn chạy); mọi kết quả khác → `PENDING_RECONCILE` + khoá `UNRESOLVED_CLOSE` (không gửi lại; trừ `VERIFIED_NOT_RECEIVED (b)` với cùng clientOid và `now < expires_at`).
 - `UPDATING_PROTECTION` dở → luôn hoàn tất tiến; bước đặt TP đã `sent` mà không thấy → `UNKNOWN`, không đặt lại tới khi xác định (TP không phải bảo vệ).
@@ -765,2 +821,25 @@
 
+### 6A.10 Đóng 100%: thủ tục thường và thủ tục khẩn
+
+Áp cho mọi đường đóng hết một leg (bảng 6A.0). Cả hai thủ tục đều đóng **size thật đọc từ sàn** bằng `close-positions` (`productType=USDT-FUTURES`, `symbol`, `holdSide`) – không gửi size tự tính – và đều kết thúc bằng điều kiện: **size leg = 0 VÀ không còn lệnh entry/TP/SL nào của leg trên sàn** (`orders-pending` + `orders-plan-pending` lọc tiền tố công cụ và `posSide`).
+
+**Thủ tục thường** – `ladder close <root> --confirm` (leg không có sự cố SL):
+1. `RECONCILING`: kiểm chế độ tài khoản như 6A.8 (hedge / crossed / USDT-FUTURES); leg không `RECOVERING`, không có op khác. Lệch → dừng, 0 lệnh gửi.
+2. `CANCELLING_ENTRIES`: huỷ **mọi** lớp chờ của leg + mọi TP (theo clientOid); chờ `cancelled` hoặc phát hiện `filled`/khớp một phần. SL **giữ nguyên**.
+3. `SETTLING`: chờ `ladder_close.settle_s` (2 s), đọc `fills` (từ lúc bắt đầu op) + `single-position` để bắt **fill trễ** của lớp vừa huỷ; size thật = size sàn sau bước này.
+4. `CLOSING`: `close-positions` holdSide (đóng đúng size thật, kể cả phần vừa khớp trễ).
+5. `CONFIRM_ZERO`: `single-position` size = 0 (đối soát REST, tối đa 30 s); chưa 0 (vd fill trễ hơn nữa) → lặp lại 3–4, tối đa `emergency_max_loops` (3) lần, rồi KHẨN.
+6. `CLEANUP`: chỉ khi size = 0 đã xác nhận → huỷ SL (`pos_loss`) và mọi lệnh còn sót của leg; xác nhận không còn lệnh nào; leg → `CLOSED`.
+
+Lỗi ở bước 2 (huỷ bị từ chối/UNKNOWN) → **không** đóng, `FAILED_SAFE`, SL giữ, CAO + gợi ý thủ tục khẩn (`kill --close-positions --confirm-close`). Lỗi ở bước 4 (`close-positions` UNKNOWN) → như 6A.8: không gửi lại mù, đối soát `single-position`; leg vào khoá `UNRESOLVED_CLOSE` (6A.8) nếu vẫn không xác định.
+
+**Thủ tục khẩn** – `kill --close-positions --confirm-close`, `on_sl_failure: close_leg` (SPEC 8.2(3)), `fail_execute` của `pos_loss`/BE (§9.4), Q-7 SL/BE đã vượt trigger (`kill --close-positions` do anh gõ áp cho mọi leg của công cụ, kể cả Nonstop; ba kích hoạt tự động còn lại chỉ áp leg Kiểm soát – Nonstop: §6B.5):
+1. Leg → `EMERGENCY_CLOSING` (ghi DB trước): watcher **ngừng mọi** đặt/đặt lại entry và TP của leg; mọi lệnh mở của leg bị coi là không được phép.
+2. `close-positions` holdSide **ngay** (ưu tiên giảm exposure; không chờ huỷ entry).
+3. Huỷ **mọi** lớp chờ + TP của leg (song song, idempotent, tối đa 2 lần gửi lại mỗi lệnh).
+4. Vòng kiểm: đọc `single-position` + `orders-pending`; size > 0 (một entry đã khớp trước khi bị huỷ) → `close-positions` lại; còn lệnh entry → huỷ lại. Lặp tới khi **size = 0 và 0 lệnh entry**, tối đa `emergency_max_loops` (3) vòng, mỗi vòng ≤ 10 s; hết vòng mà chưa đạt → KHẨN mỗi phút, tiếp tục vòng mỗi 30 s (không bao giờ đặt entry).
+5. `CLEANUP` như thủ tục thường; leg → `CLOSED`. Leg đã `EMERGENCY_CLOSING`/`CLOSED` **không bao giờ** được watcher đặt lại entry (kể cả sau `resume`); muốn giao dịch tiếp phải là plan mới (`execute`).
+
+Bảo đảm: không còn lệnh entry nào của leg trên sàn khi thủ tục khẩn kết thúc, nên không có lớp sót nào mở lại vị thế sau đó; nếu một entry khớp trong lúc thủ tục chạy thì vòng kiểm (bước 4) đóng nó. Hai thủ tục đều không áp `expires_at` (không phải phiên bản `reduce`); quyền gửi `close-positions` của thủ tục khẩn không phụ thuộc khoá ngày/kill (bảng 8.4 "Luôn được").
+
 ## 6B. Chế độ vận hành Nonstop ("gối lệnh", SL/TP không bắt buộc) [mới; yêu cầu của chủ 2026-10-20; **chưa có trong P1**]
@@ -786,5 +865,5 @@
 
-- Bật bằng `profile set --nonstop-bucket N --confirm` + xác nhận rủi ro khi bật (6B.3). Đây là **tăng rủi ro** theo §2.4: `pending` 24 h, bị từ chối khi đang khoá, tối đa 1 lần tăng/7 ngày. Tắt (`--nonstop-bucket 0`) = hạ rủi ro, hiệu lực ngay; thang Nonstop đang chạy không bị đóng, chỉ chặn mở thang Nonstop mới.
+- Bật bằng `profile set --nonstop-bucket N --confirm` + xác nhận rủi ro khi bật (6B.3). Đây là **tăng rủi ro** theo §2.4: `pending` 24 h, bị từ chối khi đang khoá, tối đa 1 lần tăng/7 ngày. Tắt (`--nonstop-bucket 0`) = hạ rủi ro, hiệu lực ngay; thang Nonstop đang chạy không bị đóng, chỉ chặn mở thang Nonstop mới; **vốn đã phân bổ cho xô Nonstop không được giải phóng** cho tới khi mọi leg Nonstop về size 0, hết lệnh chờ và sổ đối soát đạt (§3.1).
 - **Bậc hồ sơ** (câu hỏi C30, mặc định): Thận trọng **không** bật được; Cân bằng **không**; Mạo hiểm có kiểm soát **được**.
-- **Xô Nonstop**: `E_ns_base = share_ns × E` khi bật/refill; sổ `nonstop_ledger` dùng **đúng cách ghi theo sự kiện** của §3.1 (`open_fee`, `close_pnl`, `close_fee`, `funding`, khoá `tradeId`/`billId`); `E_ns(t) = E_ns_base + realized_ns + upnl_ns`.
+- **Xô Nonstop**: sổ `nonstop` trong **sổ phân bổ chung** `alloc_ledger` (§3.1): `alloc = share_ns × E_now` khi bật/refill; cùng mô hình dòng (khoá `(source_kind, source_id, line_type, ledger)`), cùng chia funding, cùng đẳng thức đối soát `E_wide + E_risk + E_ns = E`, cùng quy tắc xô âm / refill / tắt khi còn vị thế; `E_ns(t)` theo §3.1 và `E_wide_sizing` trừ `max(0, E_ns)`.
 - Trần: `share_ns` theo C31 (mặc định đề xuất 10% E); **tổng xô Scalp + xô Nonstop ≤ `HARD_RISK_BUCKET_MAX` = 20% E** (dùng chung hằng có sẵn, không thêm hằng mới).
@@ -797,4 +876,4 @@
 |---|---|---|---|
-| N1 | **Bội số** | notional khi **khớp đủ mọi lớp** của thang Nonstop + mọi leg khác (cùng chiều / tổng) ≤ trần R10a / R9a hiện có (cứng 15× / 20× E) và ≤ `nonstop.max_multiple_x` (C33) | R10w (2.5× cùng chiều Wide) **không** áp cho Nonstop; R10a/R9a tài khoản **có** áp |
-| N2 | **Thanh lý khi khớp đủ** | `liq_dist_all_fill` ≥ `nonstop.min_liq_all_fill_pct` (C32 – **chưa chốt**, đề xuất 3%) | tính bằng mô hình xấu nhất toàn tài khoản §6A.2: mọi lớp Nonstop **và** mọi lớp chờ của leg khác cùng chiều coi như đã khớp, leg ngược chiều chỉ tính MM; khoảng cách đo **từ giá lớp cuối** (lúc khớp đủ, mark ≈ giá lớp cuối). Giá liq ≥ giá lớp cuối (long) = thang không khớp đủ được trước thanh lý → FAIL |
+| N1 | **Bội số** | notional khi **khớp đủ mọi lớp** của thang Nonstop + mọi leg khác: cùng chiều ≤ `min(trần cùng chiều hồ sơ, params.nonstop.samedir_x, nonstop.max_multiple_x, cứng 15×)`, tổng ≤ `min(account.total_x hồ sơ, params.nonstop.total_x, cứng 20×)` (§3.5 mục 4a). Hồ sơ Mạo hiểm hiện tại: cùng chiều **5×**, tổng **7×** | R10w (2.5× cùng chiều Wide) **không** áp cho Nonstop; hằng cứng **không** thay trần hồ sơ (C33) |
+| N2 | **Thanh lý theo đường khớp** | với **mọi** k = 1…N: `d_k ≥ nonstop.min_liq_fill_path_pct` (C32 – **chưa chốt**, đề xuất 3%) **và**, với k < N, lớp k+1 tới được trước thanh lý (long: `liq_k < P_{k+1}`) | Với từng k: giả định lớp 1…k của thang đã khớp (lớp đã khớp thật dùng giá/size thật) và mark = `P_k`; mô hình xấu nhất toàn tài khoản §6A.2 (lớp chờ cùng chiều của leg khác có giá đã bị vượt coi như khớp; leg ngược chiều chỉ tính MM) → `liq_k`, `d_k = sg·(P_k − liq_k)/P_k`. Lưu `fill_path [{k, price, liq, d_pct}]` và `min_d_pct` trong plan (trong hash); preview in cả đường. **Không** dùng quy đổi bội số ↔ khoảng cách nào để cho phép (6B.8). Mọi `ladder apply` tăng rủi ro tính lại toàn bộ đường từ trạng thái thật |
 | N3 | **Xô** | xô Nonstop đang bật, không khoá; `share_ns` và tổng xô ≤ trần | 6B.1 |
@@ -809,3 +888,3 @@
 - **Khi bật Nonstop**: CLI yêu cầu gõ đúng câu: `TÔI HIỂU: KHÔNG CÓ SL, CÓ THỂ MẤT TOÀN BỘ TÀI KHOẢN` (lưu vào hồ sơ: thời điểm, phiên bản hồ sơ).
-- **Mỗi lần duyệt plan Nonstop** (`execute` / `ladder apply` tăng rủi ro): `--ack NS-<6 hex hash>-<liq_dist_all_fill 2 chữ số>` (vd `NS-a41c09-2.30`). Mã lấy từ preview của **đúng** phiên bản; sai/thiếu → R29 FAIL. Trợ lý chat **không được** tự điền mã: chỉ chuyển nguyên văn mã anh gõ (quy tắc §1.1 mục 2; công cụ không phân biệt được ai gõ – đây là quy tắc cho trợ lý, ghi rõ là giới hạn).
+- **Mỗi lần duyệt plan Nonstop** (`execute` / `ladder apply` tăng rủi ro): `--ack NS-<6 hex đầu của content_hash>-<min_d_pct 2 chữ số>` (vd `NS-a41c09-2.30`). Mã **không** nằm trong `hash_content`: phiên bản được băm trước, mã suy ra từ hash (và `min_d_pct` đã nằm trong nội dung băm), mã anh gõ được ghi vào bảng `approvals` tách khỏi plan (§5.4) – nhập mã không đổi hash. Đổi qty/SL/entry → phiên bản mới → hash mới → mã mới (U67). Mã lấy từ preview của **đúng** phiên bản; sai/thiếu → `approvals.result = rejected`, R29 FAIL. Trợ lý chat **không được** tự điền mã: chỉ chuyển nguyên văn mã anh gõ (quy tắc §1.1 mục 2; công cụ không phân biệt được ai gõ – đây là quy tắc cho trợ lý, ghi rõ là giới hạn).
 - Preview Nonstop PHẢI có, ở đầu và không thể tắt:
@@ -814,6 +893,8 @@
 NONSTOP 9KD2.v1  ETH long (dca)   ⚠ KHÔNG CÓ SL   TP: +0.15% (lãi ròng ~0.07%/lần)
-Khớp đủ 4 lớp:   notional 17173.74 USDT = 32.7× vốn (E 524.70)
+Khớp đủ 4 lớp:   notional 17173.74 USDT = 32.73× vốn (E 524.70)
 Thanh lý nếu khớp đủ (ước tính, mmr 0.5%): 2334.19 = cách lớp cuối 2.30% / cách lớp 1 2.74%
+Đường khớp d_k:  L1 9.56% → L2 4.79% → L3 3.16% → L4 2.30%   (min 2.30% ở L4)
 Nếu bị thanh lý: mất tới gần như TOÀN BỘ tài khoản (~524 USDT), không chỉ xô Nonstop (52.47)
-Chốt chặn: N1 FAIL (32.7× > 15×)  N2 FAIL (2.30% < 3% – ngưỡng đề xuất, chưa chốt)
+Chốt chặn: N1 FAIL (32.73× > 5.00× – cùng chiều hiệu lực = min(hồ sơ Mạo hiểm 5×, cấu hình 15×, cứng 15×))
+           N2 FAIL (min d_k 2.30% ở L4 < 3% – ngưỡng đề xuất, chưa chốt)
 Mã xác nhận: NS-a41c09-2.30   (gõ: execute 9KD2.v1 --confirm --hash a41c09 --ack NS-a41c09-2.30)
@@ -824,3 +905,3 @@
 
-- Watcher **không** gửi lệnh nào cho leg Nonstop ngoài: (a) entry/TP đã duyệt (đặt lại TP sau mỗi fill như Scalp SPEC 4.12.3, nếu có TP); (b) SL đã duyệt (nếu có, I1n). **Không** dựng sẵn reduce, **không** tự reduce/đóng, **không** tự huỷ lớp chờ (kể cả khi khoá ngày, khoá xô, hay khi liq tới gần – khác với quy tắc huỷ lớp của Scalp SPEC 4.12.3c; xem C36).
+- Cảnh báo `ns_*` **không bao giờ** gây ra lệnh can thiệp (huỷ, đóng, reduce, SL mới, phiên bản dựng sẵn). Việc quản lý lệnh **theo plan** vẫn chạy độc lập với cảnh báo và được gắn `cause=plan` trong journal. Watcher **không** gửi lệnh nào cho leg Nonstop ngoài: (a) entry/TP đã duyệt (đặt lại TP sau mỗi fill như Scalp SPEC 4.12.3, nếu có TP); (b) SL đã duyệt (nếu có, I1n). **Không** dựng sẵn reduce, **không** tự reduce/đóng, **không** tự huỷ lớp chờ (kể cả khi khoá ngày, khoá xô, hay khi liq tới gần – khác với quy tắc huỷ lớp của Scalp SPEC 4.12.3c; xem C36).
 - **Hai loại cảnh báo** (ngưỡng ở C34):
@@ -845,3 +926,3 @@
 | §6.5 phục hồi | giữ nguyên | như cũ, trừ: ngoại lệ "watcher đặt `pos_loss` khi thiếu" không áp; quy tắc 3 "kiểm I2" → kiểm N1–N2 | ngoại lệ áp cho SL đã duyệt |
-| §6A reduce: RECONCILING "đúng 1 `pos_loss`", điều kiện kết thúc "đúng 1 SL", bảng TP 6A.5, U42/U47/U55 | giữ nguyên | số SL kỳ vọng = **0** (thấy SL lạ → ABORTED + CAO, không đụng); kết thúc: 0 SL; TP chỉ đặt lại nếu plan có TP | số SL kỳ vọng = 1 (như Kiểm soát) |
+| §6A reduce: RECONCILING "đúng 1 `pos_loss`", điều kiện CLOSING, điều kiện kết thúc "đúng 1 SL", bảng TP 6A.5, U42/U47/U55 | giữ nguyên (`sl_policy: required`) | `sl_policy: none`: số SL kỳ vọng = **0** ở RECONCILING **và CLOSING** (thấy SL lạ → ABORTED / FAILED_SAFE + CAO, không đụng); kết thúc: 0 SL; TP chỉ đặt lại nếu plan có TP (U70) | `sl_policy: approved`: số SL kỳ vọng = 1 (như Kiểm soát) |
 | §6A.0 cổng `REDUCE_SL_MODE` | giữ nguyên | reduce do **anh tự gọi** dùng **cùng cổng** (C37: D26 cũng là bằng chứng đóng một phần đúng leg trong hedge mode); `ladder close` 100% và `entries` luôn được | như trái |
@@ -860,3 +941,3 @@
 - **Số thang**: tổng mọi chế độ ≤ 4 (2 symbol × 2 chiều); Nonstop ≤ 1 cùng lúc (C31, mặc định 1).
-- **Cap 2.5× cùng chiều**: đó là R10w của Wide (cứng 2.5×) – **không áp** cho Nonstop; trần cùng chiều toàn tài khoản R10a (cứng 15×) **có áp** (N1).
+- **Cap 2.5× cùng chiều**: đó là R10w của Wide (cứng 2.5×) – **không áp** cho Nonstop; trần cùng chiều toàn tài khoản R10a **có áp** với trần hiệu lực `min(hồ sơ, Nonstop, cứng)` (N1, §3.5 mục 4a; Mạo hiểm hiện tại 5×).
 - **Khoá ngày**: chặn mở Nonstop mới (6B.5). Nonstop không được dùng để "gỡ" sau khi Kiểm soát bị khoá.
@@ -865,25 +946,26 @@
 
-- **PN** (không thuộc P1/P1b): bật được khi (1) cổng Demo P1 của Kiểm soát đạt (Q-13); (2) sổ xô theo sự kiện đạt (U58); (3) U59–U66 và D34–D37 đạt; (4) chủ trả lời C30–C40. Câu hỏi C39 (mặc định: như vậy, không chờ thêm 4 tuần live).
+- **PN** (không thuộc P1/P1b): bật được khi (1) cổng Demo P1 của Kiểm soát đạt (Q-13); (2) sổ phân bổ chung đạt (U58, U68); (3) U59–U67, U69 (phần Nonstop), U70 và D34–D37 đạt; (4) chủ trả lời C30–C40. Câu hỏi C39 (mặc định: như vậy, không chờ thêm 4 tuần live).
 - Trước PN: `regime: nonstop` bị từ chối ở `propose`/`plan import`/`execute` với thông báo pha.
 
-### 6B.8 Tính toán minh hoạ – thanh lý khi khớp đủ, kiểu thang của chủ
+### 6B.8 Tính toán minh hoạ – thanh lý theo đường khớp, kiểu thang của chủ
 
-> **Đây là phép tính, không phải dữ liệu sàn.** Script `/workspace/scratch/spec_v2/r4/nonstop_liq.py` (Decimal). Giả định: ETHUSDT long, P₁ 2400.00, E = 524.7, cross, không có vị thế khác, `mmr` 0.5% (MMR bậc thật theo notional có thể cao hơn → liq **gần hơn**), phí mở maker 0.02%, size floor lot 0.01, giá floor tick 0.01. Công thức §6A.2: `W + Q(P − A) ≤ mmr·Q·P`, `W = E − phí mở`. Kiểu thang theo chủ: `d` 0.11–0.18%, `mult` 0.87, lớp đầu ~10× E.
+> **Đây là phép tính, không phải dữ liệu sàn.** Script `/workspace/scratch/spec_v2/r4/nonstop_liq.py` + `/workspace/scratch/spec_v2/r5/nonstop_fillpath.py` (Decimal). Giả định: ETHUSDT long, P₁ 2400.00, E = 524.7, cross, không có vị thế khác, `mmr` 0.5% (MMR bậc thật theo notional có thể cao hơn → liq **gần hơn**), phí mở maker 0.02%, size floor lot 0.01, giá floor tick 0.01. Công thức §6A.2: `W + Q(P − A) ≤ mmr·Q·P`, `W = E − phí mở`. Kiểu thang theo chủ: `d` 0.11–0.18%, `mult` 0.87, lớp đầu ~10× E.
 
-| Kịch bản | lớp đầu / mult / d / số lớp | Notional khớp đủ (×E) | Q ETH | Giá TB | Giá lớp cuối | Liq ước tính | Cách lớp cuối | Cách giá TB | Cách lớp 1 |
+| Kịch bản | lớp đầu / mult / d / số lớp | ×E khớp đủ | Liq khớp đủ | d_k theo từng lớp (%) | min d_k (lớp) | Lớp tới được trước liq | N2 3% | N2 2% | N2 1% |
 |---|---|---|---|---|---|---|---|---|---|
-| ~15× (lớp đầu 5×, để so sánh) | 5× / 0.87 / 0.15% / 4 | 16.3× | 3.58 | 2395.23 | 2389.21 | 2260.44 | 5.39% | 5.63% | 5.81% |
-| ~20× (lớp đầu 5×) | 5× / 0.87 / 0.15% / 6 | 21.7× | 4.75 | 2392.45 | 2382.05 | 2293.94 | 3.70% | 4.12% | 4.42% |
-| ~25× (lớp đầu 5×) | 5× / 0.87 / 0.15% / 8 | 25.6× | 5.63 | 2390.01 | 2374.91 | 2308.84 | 2.78% | 3.40% | 3.80% |
-| **~30×** | 10× / 0.87 / 0.15% / 4 | 32.7× | 7.17 | 2395.22 | 2389.21 | 2334.19 | **2.30%** | 2.55% | 2.74% |
-| **~60×** | 10× / 0.87 / 0.15% / 11 | 60.0× | 13.20 | 2386.83 | 2364.24 | 2359.36 | **0.21%** | 1.15% | 1.69% |
-| ~60×, d 0.11% | 10× / 0.87 / 0.11% / 11 | 60.0× | 13.18 | 2390.35 | 2373.73 | 2362.83 | 0.46% | 1.15% | 1.55% |
-| ~60×, d 0.18% | 10× / 0.87 / 0.18% / 11 | 60.0× | 13.21 | 2384.22 | 2357.14 | 2356.76 | 0.02% | 1.15% | 1.80% |
-| **~95×** (lớp đầu 15×) | 15× / 0.87 / 0.15% / 13 | 96.1× | 21.15 | 2385.08 | 2357.15 | 2372.61 | **−0.66%** (liq **trên** lớp cuối) | 0.52% | 1.14% |
-| ~95× (mult 0.97, 12 lớp) | 10× / 0.97 / 0.15% / 12 | 101.8× | 22.42 | 2381.54 | 2360.69 | 2370.46 | −0.41% | 0.47% | 1.23% |
-
-- Với lớp đầu 10× và `mult` 0.87, tổng chuỗi vô hạn chỉ là 10/(1 − 0.87) = **76.9×** → 95× không đạt được nếu không tăng lớp đầu hoặc `mult`. Ở ~95×, **thanh lý xảy ra trước khi các lớp cuối kịp khớp** (khoảng cách âm) – thang không bao giờ khớp đủ được.
-- Lũy tiến ở thang ~60× (d 0.15%): khoảng cách liq từ giá lớp vừa khớp = 9.56% (L1, 10×) → 4.79% (L2, 18.6×) → 3.16% (L3, 26.2×) → 2.30% (L4, 32.7×) → 1.76% (L5) → 1.36% → 1.06% → 0.80% → 0.58% → 0.39% → 0.21% (L11, 60×).
-- Quy đổi xấp xỉ (coi cả thang như 1 lớp tại giá cuối): liq ≥ 10% ⇔ ≲ 9.6× E; ≥ 5% ⇔ ≲ 18.2×; ≥ 3% ⇔ ≲ 28.5×; ≥ 2% ⇔ ≲ 39.8×; ≥ 1% ⇔ ≲ 66×.
-- **Hệ quả cho ngưỡng N2 (C32)**: ngưỡng đề xuất 3% (= mức tối thiểu "liq ≥ 3% khi thêm lớp" đã có ở SPEC 4.12.2) cho phép khoảng ≤ 28× E; kiểu 34–95× của chủ **không qua** N2 ở 3%, và cũng **không qua** trần cứng hiện có R10a 15× / R9a 20× / leverage 50 (N1, R16). Muốn chạy 30–60× thì phải hạ N2 về ~2% / ~0.2% **và** nâng hằng cứng – đó là quyết định của chủ (C32, C33), tài liệu này **không** tự chốt.
+| ~15× (lớp đầu 5×) | 5× / 0.87 / 0.15% / 4 | 16.34× | 2260.44 | 19.64 / 10.18 / 7.02 / 5.39 | 5.39% (L4) | 4/4 | PASS | PASS | PASS |
+| ~20× (lớp đầu 5×) | 5× / 0.87 / 0.15% / 6 | 21.66× | 2293.94 | 19.64 / 10.18 / 7.02 / 5.39 / 4.38 / 3.70 | 3.70% (L6) | 6/6 | PASS | PASS | PASS |
+| ~25× (lớp đầu 5×) | 5× / 0.87 / 0.15% / 8 | 25.64× | 2308.84 | 19.64 / 10.18 / 7.02 / 5.39 / 4.38 / 3.70 / 3.19 / 2.78 | 2.78% (L8) | 8/8 | FAIL | PASS | PASS |
+| ~30× | 10× / 0.87 / 0.15% / 4 | 32.73× | 2334.19 | 9.56 / 4.79 / 3.16 / 2.30 | 2.30% (L4) | 4/4 | FAIL | PASS | PASS |
+| ~60× | 10× / 0.87 / 0.15% / 11 | 60.05× | 2359.36 | 9.56 / 4.79 / 3.16 / 2.30 / 1.76 / 1.36 / 1.06 / 0.80 / 0.58 / 0.39 / 0.21 | 0.21% (L11) | 11/11 | FAIL | FAIL | FAIL |
+| ~60×, d 0.11% | 10× / 0.87 / 0.11% / 11 | 60.04× | 2362.83 | 9.56 / 4.81 / 3.20 / 2.37 / 1.85 / 1.48 / 1.20 / 0.97 / 0.78 / 0.61 / 0.46 | 0.46% (L11) | 11/11 | FAIL | FAIL | FAIL |
+| ~60×, d 0.18% | 10× / 0.87 / 0.18% / 11 | 60.03× | 2356.76 | 9.56 / 4.78 / 3.12 / 2.25 / 1.69 / 1.28 / 0.95 / 0.68 / 0.44 / 0.22 / 0.02 | 0.02% (L11) | 11/11 | FAIL | FAIL | FAIL |
+| ~95× (lớp đầu 15×) | 15× / 0.87 / 0.15% / 13 | 96.14× | 2372.61 | 6.20 / 2.99 / 1.87 / 1.28 / 0.88 / 0.59 / 0.35 / 0.15 / -0.03 / -0.20 / -0.36 / -0.51 / -0.66 | -0.66% (L13) | 8/13 | FAIL | FAIL | FAIL |
+| ~95× (mult 0.97, 12 lớp) | 10× / 0.97 / 0.15% / 12 | 101.76× | 2370.46 | 9.56 / 4.52 / 2.79 / 1.89 / 1.31 / 0.90 / 0.59 / 0.33 / 0.11 / -0.08 / -0.25 / -0.41 | -0.41% (L12) | 9/12 | FAIL | FAIL | FAIL |
+
+- Script vòng 5: `/workspace/scratch/spec_v2/r5/nonstop_fillpath.py` (dùng lại hàm của `r4/nonstop_liq.py`). `d_k` = khoảng cách thanh lý từ giá lớp k ngay khi lớp k khớp (lớp 1…k đã khớp). Cột N2 = PASS/FAIL theo quy tắc 6B.2 với ngưỡng 3% / 2% / 1% (để so sánh; C32 chưa chốt).
+- Khớp với số người review tái tạo: 16.34× → 2260.44 / 5.39%; 32.73× → 2334.19 / 2.30%; 60.05× → 2359.36 / 0.21%.
+- Với lớp đầu 10× và `mult` 0.87, tổng chuỗi vô hạn chỉ là 10/(1 − 0.87) = **76.9×** → 95× không đạt được nếu không tăng lớp đầu hoặc `mult`. Ở ~95×, `d_k` âm từ L9 (lớp đầu 15×) / L10 (mult 0.97): **thanh lý xảy ra trước khi các lớp cuối kịp khớp**, chỉ 8/13 và 9/12 lớp tới được.
+- **Bỏ quy đổi bội số ↔ khoảng cách** (bản v5 có dòng "≥ 3% ⇔ ≲ 28.5×"): đó chỉ là xấp xỉ coi cả thang như một lớp, **không** được dùng làm quy tắc cho phép. Phản ví dụ: thang ~25.64× (lớp đầu 5×, 8 lớp) chỉ có `d_8` = 2.78% → **FAIL** ở 3%, trong khi quy đổi cũ sẽ cho qua. N2 luôn tính từng thang theo đường khớp (U60).
+- **Hệ quả**: với hồ sơ Mạo hiểm hiện tại (trần cùng chiều 5×, tổng 7×), **mọi** thang trong bảng (≥ 16×) FAIL N1 trước cả N2. Kiểu 30–95× của chủ cần (a) nâng trần hồ sơ (tăng rủi ro §2.4, ≤ hằng cứng 15× / 20×) và (b) nếu > 15× cùng chiều: nâng hằng cứng và leverage 50 (đổi mã + review), và (c) hạ N2 xuống dưới mức ~2% / ~0.2% của đường khớp – đều là quyết định của chủ (C32, C33); tài liệu này **không** tự chốt.
 
@@ -981,2 +1063,4 @@
 | Giờ cấm (P6) | `now ∈ no_trade` | hết khung giờ |
+| Sổ phân bổ lệch | đẳng thức §3.1 `E_wide + E_risk + E_ns = E` không đạt sau khi tải lại | đẳng thức đạt lại; trong lúc lệch: như cột "Bộ đếm UNKNOWN" |
+| Đóng chưa xác định (`UNRESOLVED_CLOSE`, **theo leg**) | lệnh đóng của leg có kết quả UNKNOWN (6A.8) | X xác định được, hoặc `ops clear` sau ≥ 24 h; được/chặn theo 6A.8 (chặn `reduce`, `execute` cùng (symbol, holdSide), PLACE_ENTRY, SL_LOOSEN; `ladder close`/`kill --close-positions` được) |
 
@@ -1009,3 +1093,3 @@
 - `kill` (mặc định) = **chế độ bảo vệ**: tạo `state/KILL`, huỷ mọi **entry** và **TP** của công cụ (lọc tiền tố), **giữ** `pos_loss`/BE, watcher **tiếp tục chạy** ở chế độ `PROTECT_ONLY` (chỉ đảm bảo SL, đối soát, cảnh báo; không đặt entry/TP). Xác nhận đầu ra: "mỗi leg Kiểm soát còn vị thế có đúng 1 SL"; leg Nonstop không SL được liệt kê riêng: "KHÔNG có SL" (§6B.5).
-- `kill --close-positions --confirm-close` = `close-positions` theo từng (symbol, holdSide) của công cụ → đợi size = 0 (xác nhận REST) → mới huỷ SL/TP còn lại. Thất bại đóng → giữ SL, KHẨN.
+- `kill --close-positions --confirm-close` = **thủ tục khẩn §6A.10** cho từng (symbol, holdSide) của công cụ: `close-positions` → huỷ mọi lớp chờ + TP → vòng kiểm tới khi size = 0 và 0 entry (xác nhận REST) → mới huỷ SL còn lại. Thất bại đóng → giữ SL, KHẨN.
 - `resume --confirm` = xoá `state/KILL` + `selftest` → watcher về chế độ thường (đặt lại TP theo phiên bản đang chạy; **không** đặt lại entry đã huỷ – muốn thì `ladder edit`).
@@ -1048,3 +1132,3 @@
 | Q-12 | §8.4 | R18–R20 |
-| Q-13 | Cổng **P1** = U1–U2, U4–U16, U19a, U20–U25, U28–U38, U40, U42–U48, U50, U52, U53, U55–U57, phần Wide của U44/U51, D1–D14, D16–D23, D25, D30, D31. **Bật `reduce` market** (không chặn go-live P1) = D26 + D28 (chỉ `position_persist`). **Tự gửi lại lệnh `place` sau crash** (tuỳ chọn; không có thì không bao giờ tự gửi lại) = D32. **Dựng lại mốc ngày** (tuỳ chọn; không có thì đi nhánh UNKNOWN) = D33. **P1b** = U3', U19b, U26–U27, U41 (maker), U54, U58, phần Scalp của U44/U51, D15, D24, D27. **P2** = U17–U18, U39 (+ cổng 6.8). **Hiển thị số kỳ vọng** của một bậc = B9 (Mạo hiểm + B6, xô + B8). **PN (Nonstop)** = cổng Demo P1 đạt + U58 + U59–U66 + D34–D37 + C30–C40 đã trả lời (§6B.7). Đã rút: U49, D29. Demo Wide ≥ 20 thang, Scalp ≥ 10 trước khi bật xô | 10, 11 |
+| Q-13 | Cổng **P1** = U1–U2, U4–U16, U19a, U20–U25, U28–U38, U40, U42–U48, U50, U52, U53, U55–U57, U69 (phần Kiểm soát), U73, U74, phần Wide của U44/U51/U68, D1–D14, D16–D23, D25, D30, D31, D39. **Bật `reduce` market** (không chặn go-live P1) = D26 + D28 + U71 + U72 + D38 (chỉ `position_persist`). **Tự gửi lại lệnh `place` sau crash** (tuỳ chọn; không có thì không bao giờ tự gửi lại) = D32. **Dựng lại mốc ngày** (tuỳ chọn; không có thì đi nhánh UNKNOWN) = D33. **P1b** = U3', U19b, U26–U27, U41 (maker), U54, U58, phần Scalp của U44/U51/U68, D15, D24, D27. **P2** = U17–U18, U39 (+ cổng 6.8). **Hiển thị số kỳ vọng** của một bậc = B9 (Mạo hiểm + B6, xô + B8). **PN (Nonstop)** = cổng Demo P1 đạt + U58 + U59–U67 + U68 (sổ nonstop) + U69 (phần Nonstop) + U70 + D34–D37 + C30–C40 đã trả lời (§6B.7). Đã rút: U49, D29. Demo Wide ≥ 20 thang, Scalp ≥ 10 trước khi bật xô | 10, 11 |
 | Q-14 | Sửa 1.5 ("micro-grid không stop, không trần" ngoài phạm vi; Scalp có trần thì trong phạm vi). **B4 thành cổng**: bật xô mạo hiểm live chỉ sau B8 + chủ ký duyệt | 1.5, 10.5 |
@@ -1063,3 +1147,3 @@
 | `profile show / history / cancel-pending` | | Không |
-| `bucket status` / `bucket refill --confirm` | Sổ xô §3 | Không |
+| `bucket status` / `bucket refill --confirm` | Sổ phân bổ §3.1: số dư Wide/Scalp/Nonstop, đẳng thức đối soát, `deficit`; refill bị từ chối khi xô còn leg mở | Không |
 | (PN) `profile set --nonstop-bucket N --confirm` + câu xác nhận; `propose --regime nonstop --symbol S --side L/S`; `execute <ref> --confirm --hash H --ack NS-…`; `bucket refill --nonstop --confirm`; `alerts list` (`alerts mute` từ chối `ns_*`) | §6B | Có (execute) |
@@ -1068,9 +1152,10 @@
 | `execute <ref> --confirm --hash H [--reason "..."]` | Thay `execute <plan_id> --confirm`; `--reason` chỉ cho đèn đỏ trước cổng | Có |
-| `ladder edit <root> ...` / `ladder apply <ref> --confirm --hash H` / `ladder close <root> --confirm` | §6; `ladder close` = 100% (`close-positions` holdSide), không có `--pct` | Có (apply/close) |
+| `ladder edit <root> ...` / `ladder apply <ref> --confirm --hash H` / `ladder close <root> --confirm` | §6; `ladder close` = 100% theo thủ tục thường §6A.10, không có `--pct` | Có (apply/close) |
 | `reduce <root> --pct N \| --qty Q` / `reduce show <ref>` / `reduce apply <ref> --confirm --hash H` / `reduce status <op_id>` | §6A – chỉ đóng, **market-only ở P1, luôn huỷ mọi lớp chờ của leg**, tắt cứng tới khi D26 đạt; đường duy nhất để đóng một phần; dùng được khi khoá/kill. `--exec maker` = P1b, `--target-liq-distance` = P2, `--entries keep`/`--cancel-idx` = pha sau (từ chối) | Có (apply) |
 | `entries <root> --cancel IDX[,…] \| --cancel-all` / `entries apply <ref> --confirm --hash H` | `entry_adjust`: chỉ huỷ lớp chờ, không bao giờ gửi lệnh đóng; luôn bật | Có (apply) |
-| `ops list` / `ops show <op_id>` | Nhật ký bước §6.5, trạng thái RECOVERING/PENDING_RECONCILE/FAILED_SAFE | Không |
+| `ops list` / `ops show <op_id>` | Nhật ký bước §6.5, trạng thái RECOVERING/PENDING_RECONCILE/FAILED_SAFE, khoá `UNRESOLVED_CLOSE` | Không |
+| `ops clear <op_id> --confirm` | Gỡ khoá `UNRESOLVED_CLOSE` sau ≥ 24 h dò nền không thấy X (6A.8, C42); preview in qty X, số lần dò, size hiện tại | Không |
 | `liq [--json]` | Liq một leg + xấu nhất toàn TK cho mọi leg, ngưỡng cảnh báo bậc | Không |
 | `cancel <root>` | Huỷ entry chưa khớp + TP; giữ SL nếu còn vị thế | Có |
-| `kill` / `kill --close-positions --confirm-close` / `resume --confirm` | §9.3 | Có |
+| `kill` / `kill --close-positions --confirm-close` / `resume --confirm` | §9.3; `--close-positions` = thủ tục khẩn §6A.10 | Có |
 | `digest [--send]` | §8.2 | Không |
@@ -1114,5 +1199,5 @@
   max_ladders: 1                     # C31
-  min_liq_all_fill_pct: 3            # C32 (đề xuất)
-  max_multiple_x: 15                 # C33; ≤ R10a cứng 15× cùng chiều
-  alert_liq_pct: [10, 5, 3]          # C34; + KHẨN dưới min_liq_all_fill_pct
+  min_liq_fill_path_pct: 3           # C32 (đề xuất, chưa chốt); áp cho MỌI d_k của đường khớp (6B.2 N2)
+  max_multiple_x: 15                 # C33; chỉ siết thêm – trần hiệu lực = min(hồ sơ, cấu hình này, cứng) (§3.5 mục 4a)
+  alert_liq_pct: [10, 5, 3]          # C34; + KHẨN dưới min_liq_fill_path_pct
   alert_multiple_x: 10               # C34; nhắc lại mỗi +5×
@@ -1122,2 +1207,5 @@
 day_mark: {capture_tol_s: 5, reconstruct_enabled: false, reconstruct_retry_min: 15}   # bật dựng lại chỉ sau D33 (§8.4)
+alloc: {reconcile_tol_usdt: 0.05, reconcile_every_min: 15, funding_model_tol_pct: 1.0}   # §3.1
+ladder_close: {settle_s: 2, confirm_zero_timeout_s: 30, emergency_max_loops: 3, emergency_retry_s: 30}   # §6A.10
+unresolved_close: {probe_every_s: 60, probe_h: 24}   # 6A.8; gỡ sau probe_h chỉ bằng ops clear
 ```
@@ -1128,3 +1216,3 @@
 
-Nonstop (§6B, PN) **không thêm và không nới** hằng cứng nào: R9a 20×, R10a 15×, `HARD_LEVERAGE_MAX_PER_SYMBOL = 50`, `HARD_RISK_BUCKET_MAX = 20%` (Scalp + Nonstop cộng chung) áp nguyên cho leg Nonstop (C33). Các ngưỡng `nonstop.*` ở §10.2 là cấu hình, chỉ được siết dưới các hằng này.
+Nonstop (§6B, PN) **không thêm và không nới** hằng cứng nào. Mọi hằng cứng (R9a 20×, R10a 15×, `HARD_LEVERAGE_MAX_PER_SYMBOL = 50`, `HARD_RISK_BUCKET_MAX = 20%` – Scalp + Nonstop cộng chung) là **giới hạn trên của giá trị hồ sơ/cấu hình**; khi kiểm plan dùng trần hiệu lực `min(hồ sơ, cấu hình, hằng)` (§3.5 mục 4a) – hằng cứng không bao giờ thay trần hồ sơ (C33).
 
@@ -1179,8 +1267,8 @@
 | U57 | Mốc ngày §8.4: (a) mốc 07:00 E = 500.00 đã lưu, khởi động lại lúc E = 450.00 → `daily_pnl` = −50.00 (khoá Cân bằng 5% = −25.00 kích hoạt); (b) không có mốc, `reconstruct_enabled=false` → UNKNOWN: `execute`, `ladder apply` có PLACE_ENTRY, watcher đặt lớp Scalp, `bucket refill`, tăng hồ sơ bị chặn; `reduce`/`entries`/`cancel`/`ladder close`/`kill`/SL_TIGHTEN được; (c) dựng lại với bill/fill/nến giả lập → đúng `E_day_start` (±0.01); (d) hai cách tính `W_07` lệch, thiếu trang, lỗi endpoint, thiếu nến mark → UNKNOWN; (e) hết UNKNOWN ở mốc 07:00 kế tiếp; tuần tương tự với thứ Hai 07:00 |
-| U58 | **(P1b)** Sổ xô theo sự kiện §3.1: fill mở L1 → `open_fee` ghi ngay, `used` tăng ngay; fill đóng (TP/SL/reduce) → `close_pnl` + `close_fee`; funding tại mốc → `funding` (symbol chỉ Scalp: toàn bộ; symbol Wide + Scalp: chia theo `Q_scalp·mark·rate`); khởi động lại → không ghi trùng (khoá `tradeId`/`billId`); `worst_loss` của thang đang mở không tính lại phí mở/realized đã ghi; R28 dùng giá trị mới ngay |
+| U58 | **(P1b; sổ `nonstop` ở PN)** Sổ phân bổ §3.1 – mô hình dòng: fill mở L1 → 1 dòng `open_fee` ghi ngay, `used` tăng ngay; **một** fill đóng → **2 dòng** `close_pnl` + `close_fee` cùng `tradeId`, khoá `(fill, tradeId, line_type, ledger)` khác nhau, cả hai được ghi (hồi quy lỗi trùng khoá cũ); phát lại cùng fill/bill (khởi động lại, đối soát 15 phút) → 0 dòng mới; funding: bill F trên symbol chỉ có Wide → 1 dòng `wide = F`; symbol có Wide + Scalp + Nonstop → 3 dòng, `scalp`/`nonstop` = round2(f_k), `wide = F − scalp − nonstop`, **tổng 3 dòng = F đúng tới 0.01** (property test 10.000 bill ngẫu nhiên: long/short, rate âm/dương, Q = 0 ở một sổ); lệch mô hình > max(0.01, 1%) → CAO; `worst_loss` của thang đang mở không tính lại phí mở/realized đã ghi; R28 dùng giá trị mới ngay |
 | U59 | (PN) Tách chế độ: `regime` trong schema + hash; plan cũ không có `regime` → `kiem_soat`, mọi test Kiểm soát cũ không đổi kết quả; R27n: Nonstop không SL/không TP PASS; TP 0.10% PASS + in lãi ròng 0.02%; TP 0.09% FAIL; `d` 0.09% FAIL; 13 lớp FAIL; SL nằm sau giá liq khớp đủ → FAIL "SL vô dụng"; trước PN → từ chối |
-| U60 | (PN) N2 khớp đủ (mô hình §6A.2): tái tạo bảng 6B.8 (±0.01): ~30× 2334.19 / 2.30%; ~60× 2359.36 / 0.21%; ~95× liq trên lớp cuối → FAIL "không khớp đủ được trước thanh lý"; có leg khác cùng chiều + lớp chờ của nó → liq gần hơn; leg ngược chiều chỉ tính MM; ngưỡng đọc từ cấu hình |
-| U61 | (PN) N1/N3 + sổ Nonstop: R10a/R9a tính mọi leg khi khớp đủ; R10w không áp; `max_multiple_x`; tổng xô Scalp + Nonstop > 20% → từ chối; sổ ghi phí mở/đóng/funding theo sự kiện (như U58); khoá xô ở 50% → chặn mở mới, **0 lệnh huỷ/đóng**; preview in "có thể mất toàn bộ tài khoản" |
-| U62 | (PN) Xác nhận rủi ro: bật Nonstop cần đúng câu, là tăng rủi ro (pending 24 h, từ chối khi khoá, 1 lần/7 ngày, bậc theo C30); mỗi `execute`/`ladder apply` tăng rủi ro cần `--ack` khớp hash + liq của đúng phiên bản; mã của phiên bản cũ → R29 FAIL; preview có "KHÔNG CÓ SL", liq khớp đủ (giá + %), bội số × vốn |
-| U63 | (PN) Cảnh báo 6B.4: vào mức → báo ngay; leo mức → báo ngay; ở yên → nhắc 30 / 5 phút; hồi + trễ 1 điểm / 1× mới thoát; tin "đã hồi"; `alerts mute` / giờ yên lặng bị từ chối với `ns_*`; KHẨN qua chat + email; **watcher gửi 0 lệnh** (mock) và **không** tạo phiên bản reduce dựng sẵn |
+| U60 | (PN) N2 theo **đường khớp** (6B.2, mô hình §6A.2): tái tạo bảng 6B.8 (±0.01): 16.34× → 2260.44 / 5.39%; 32.73× → 2334.19, đường 9.56 / 4.79 / 3.16 / 2.30%; 60.05× → 2359.36 / 0.21%; **25.64× (5× / 0.87 / 0.15% / 8) → min d_k 2.78% ở L8 → FAIL ở 3%** (bằng chứng không dùng quy đổi bội số); ~95× → 8/13 lớp tới được → FAIL "không khớp đủ được trước thanh lý"; mô hình liq giả lập cho `d_k` không đơn điệu → FAIL đúng ở lớp có min (kiểm **mọi** k, không chỉ lớp cuối); `ladder apply` trên thang đã khớp 2 lớp → đường tính từ giá/size khớp thật; leg khác cùng chiều + lớp chờ của nó → liq gần hơn; leg ngược chiều chỉ tính MM; ngưỡng đọc từ `nonstop.min_liq_fill_path_pct`; quét mã: không có bảng/hàm quy đổi bội số ↔ khoảng cách trong đường kiểm |
+| U61 | (PN) N1/N3 + sổ Nonstop: N1 dùng trần hiệu lực (U69), tính mọi leg khi khớp đủ; R10w không áp; tổng xô Scalp + Nonstop > 20% → từ chối; sổ `nonstop` ghi theo mô hình dòng §3.1 (như U58); khoá xô ở 50% → chặn mở mới, **0 lệnh huỷ/đóng**; preview in "có thể mất toàn bộ tài khoản" |
+| U62 | (PN) Xác nhận rủi ro: bật Nonstop cần đúng câu, là tăng rủi ro (pending 24 h, từ chối khi khoá, 1 lần/7 ngày, bậc theo C30); mỗi `execute`/`ladder apply` tăng rủi ro cần `--ack NS-<hash6>-<min_d_pct>` của đúng phiên bản; mã của phiên bản cũ → R29 FAIL; preview có "KHÔNG CÓ SL", liq khớp đủ (giá + %), đường `d_k`, bội số × vốn, trần hiệu lực |
+| U63 | (PN) Cảnh báo 6B.4: vào mức → báo ngay; leo mức → báo ngay; ở yên → nhắc 30 / 5 phút; hồi + trễ 1 điểm / 1× mới thoát; tin "đã hồi"; `alerts mute` / giờ yên lặng bị từ chối với `ns_*`; KHẨN qua chat + email; **cảnh báo `ns_*` gây ra 0 lệnh can thiệp** (mock sàn: 0 `cancel-order`, 0 `place-order tradeSide=close`, 0 `close-positions`, 0 `pos_loss` mới, 0 phiên bản reduce dựng sẵn do cảnh báo); trong cùng kịch bản, quản lý TP/SL **theo plan** vẫn chạy và được phép: fill lớp mới → đặt lại TP đã duyệt (nếu plan có TP); leg có SL đã duyệt bị mất → đặt lại đúng giá (I1n); các lệnh này mang `cause=plan` và không bị tính là can thiệp |
 | U64 | (PN) Phạm vi SL §6B.5: leg Nonstop không SL → SPEC 8.2(3) không đặt `pos_loss`, không `close_leg`, `fail_execute`/Q-7 không áp; Nonstop có SL bị mất → đặt lại đúng giá + KHẨN, không `close_leg`; reduce RECONCILING kỳ vọng 0 SL (thấy SL lạ → ABORTED); §6.5 ngoại lệ đặt `pos_loss` không áp cho leg không SL; R14 không cộng leg không SL và preview Kiểm soát in câu cảnh báo khi có Nonstop mở |
@@ -1188,2 +1276,10 @@
 | U66 | (PN) Thanh lý: bill `burst_long_loss_query` / `force_close_long` → KHẨN, tắt Nonstop (bật lại theo 6B.1), tính 1 SL trong chuỗi stop, sổ Nonstop ghi lỗ |
+| U67 | (PN) Mã xác nhận không vòng tròn (§5.4, 6B.3): `hash_content` không có trường `ack*`; đổi qty một lớp / SL / giá entry → phiên bản mới, `content_hash` khác **và** `ack_expected` khác; ghi `approvals` (mã đúng, mã sai) → băm lại bản ghi plan cho đúng `content_hash` cũ (không đổi); `ack_expected` tính lại từ bản ghi đã lưu = mã trong preview; mã của phiên bản cha → rejected; mã đúng hash nhưng sai `min_d_pct` → rejected |
+| U68 | Sổ phân bổ chung §3.1 (phần Wide: P1; xô Scalp: P1b; xô Nonstop: PN): (a) E 524.70, xô Scalp 10% + Nonstop 10% vừa cấp → `E_wide_sizing` = **419.76** (không phải 472.23); share 0 → `E_wide_sizing = E`; (b) chuỗi sự kiện giả lập (fill mở/đóng ở cả 3 sổ, funding 3 phần, chuyển tiền, bill lạ) → đẳng thức `E_wide + E_risk + E_ns = E` giữ (±0.05) sau mỗi sự kiện; bỏ một fill khỏi luồng → đẳng thức lệch → chặn tăng rủi ro; tải lại → hết lệch; (c) xô Nonstop âm −20.00 → `E_wide_sizing` = E − max(0, E_risk) (phần thiếu trừ vào Wide), xô khoá, `deficit` 20.00 hiển thị; (d) `bucket refill` khi xô còn leg mở → từ chối; sau khi đóng hết → `sweep` (âm hoặc dương) về `wide` + `alloc` mới = share × E_now, tổng không đổi; (e) `--nonstop-bucket 0` khi còn vị thế Nonstop → chặn mở mới, `alloc` giữ, `E_wide_sizing` không tăng; leg về 0 + hết lệnh chờ → tự `sweep` |
+| U69 | Trần hiệu lực §3.5 mục 4a (Kiểm soát: P1; Nonstop: PN): Mạo hiểm (cùng chiều 5×, tổng 7×) – thang Nonstop/Scalp/Wide đưa cùng chiều lên 6.10× → R10a/N1 FAIL với thông báo nêu 5× của hồ sơ (không phải 15×); tổng 7.5× → FAIL theo 7× (không phải 20×); Cân bằng không xô → R9a dùng 3.0×; hồ sơ có `params.nonstop.samedir_x` 6× > 5× → `profile set` từ chối; giá trị hồ sơ > hằng cứng → từ chối; cấu hình `nonstop.max_multiple_x` 3× → trần hiệu lực 3×; quét mã: mọi so sánh cap đi qua một hàm `limit_eff(...)` |
+| U70 | (PN) Reduce leg Nonstop **không SL** đầy đủ (sàn giả lập, `REDUCE_SL_MODE = position_persist`): `reduce <root> --pct 30` → preview `sl_policy: none` → `reduce apply --confirm --hash` → RECONCILING (0 SL kỳ vọng, đạt) → CANCELLING_ENTRIES (mọi lớp chờ + TP) → CLOSING (không đòi `pos_loss`) → UPDATING_PROTECTION (TP đặt lại nếu plan có TP; xác minh 0 SL; **0** lệnh `pos_loss` được tạo) → **DONE**; biến thể có một SL lạ trên sàn trước CLOSING → FAILED_SAFE, không đóng; biến thể `sl_policy: approved` mất SL trước CLOSING → không đóng; biến thể Kiểm soát không đổi kết quả U47 |
+| U71 | Khoá `UNRESOLVED_CLOSE` (6A.8): close X → UNKNOWN → khoá ghi DB trước khi trả lời; **khởi động lại** → khoá nạp lại, vẫn chặn; khi khoá: `reduce` mới, `execute` cùng (symbol, holdSide), `ladder apply` có PLACE_ENTRY/SL_LOOSEN, watcher đặt lớp → từ chối; `entries --cancel`, SL_TIGHTEN, watcher đặt `pos_loss` thiếu, đặt lại TP theo size thật, `kill` → được; `ladder close` khi khoá → `close-positions` size thật; mock X khớp muộn sau đó → không có lệnh đóng thứ hai do công cụ, tổng đóng ≤ size ban đầu; khoá giữ sau `CLOSED` và chặn `execute` mở lại; X xác định được → tự gỡ (`resolved`); `ops clear` trước 24 h → từ chối; sau 24 h → gỡ, preview reduce kế tiếp in "tổng có thể đóng = 0.30 (mới) + 0.64 (X) = 0.94; size hiện tại 2.14" |
+| U72 | Phạm vi `expires_at` (6A.8, §6.5 mục 7): close gửi lúc `expires_at − 5 s`, phản hồi trễ, xác định `FOUND` filled lúc `expires_at + 30 s` → UPDATING_PROTECTION chạy, TP đặt lại theo bảng 6A.5, dọn lệnh sót, DONE; **0** lệnh đóng mới sau hạn; CANCELLING_ENTRIES bắt đầu trước hạn, xong sau hạn → không CLOSING, `FAILED_SAFE` + đặt lại TP; RECOVERING sau hạn với CLOSING `planned` → không gửi, `FAILED_SAFE` + đặt lại TP; RECOVERING sau hạn với CLOSING `sent` + `FOUND` → UPDATING_PROTECTION hoàn tất |
+| U73 | `ladder close` thủ tục thường §6A.10 (sàn giả lập): có 2 lớp chờ; lớp 4 khớp trong lúc huỷ → SETTLING bắt fill trễ → `close-positions` đóng size thật (gồm lớp 4) → size 0 → mới huỷ SL; huỷ lớp bị từ chối/UNKNOWN → không đóng, FAILED_SAFE, SL giữ, gợi ý thủ tục khẩn; fill trễ hơn sau CLOSING → lặp ≤ 3 → size 0; kết thúc: 0 lệnh của leg trên sàn; sai chế độ TK → 0 lệnh |
+| U74 | Thủ tục khẩn §6A.10: `kill --close-positions`, `on_sl_failure: close_leg`, `fail_execute` SL, Q-7 SL vượt trigger → `EMERGENCY_CLOSING` ghi DB trước; `close-positions` gửi **trước** huỷ entry; entry khớp ngay sau close → vòng kiểm đóng lại; huỷ entry lỗi lần đầu → gửi lại; kết thúc chỉ khi size 0 **và** 0 entry; watcher không đặt entry/TP cho leg ở `EMERGENCY_CLOSING`/`CLOSED` (kể cả sau `resume`); hết 3 vòng chưa đạt → KHẨN mỗi phút, tiếp tục mỗi 30 s; SL chỉ huỷ sau size 0; Nonstop không SL: chỉ `kill --close-positions` kích hoạt, ba kích hoạt tự động không áp |
 
@@ -1213,2 +1309,4 @@
 | D37 | (PN) `kill` khi có leg Nonstop không SL và leg Kiểm soát | Entry + TP huỷ; leg Kiểm soát giữ SL; leg Nonstop còn vị thế không SL và được in rõ |
+| D38 | **Lệnh đóng khi size đã 0 / sau UNKNOWN** (Demo, hedge mode): (1) đóng hết leg bằng `close-positions`; gửi `place-order` market `tradeSide=close` size 0.01 cho leg đó; (2) giữ một lệnh close limit (post-only, xa giá) rồi `close-positions` leg; quan sát lệnh limit bị huỷ / vẫn treo / khớp; (3) ghi mã lỗi | Ghi lại hành vi thật. Nếu sàn từ chối close khi size 0 và tự huỷ lệnh close treo khi vị thế về 0 → ghi vào `docs/decisions.md`; nếu không → giữ khoá `UNRESOLVED_CLOSE` như 6A.8 và thêm bước huỷ lệnh close treo vào CLEANUP. Không chặn P1 (reduce tắt) |
+| D39 | **Đóng 100% có lớp chờ** (Demo): (a) `ladder close` khi còn 2 lớp chờ, một lớp được đặt sát giá để khớp trong lúc huỷ; (b) `kill --close-positions` với lớp chờ sát giá | (a) size 0, 0 lệnh của leg, SL huỷ sau cùng; (b) size 0 và 0 entry khi kết thúc; không có vị thế mở lại trong 10 phút theo dõi; log thời gian từng bước |
 
@@ -1265,4 +1363,4 @@
 | C31 | (Nonstop) Tỉ lệ xô Nonstop và số thang | **10% E**; Scalp + Nonstop ≤ 20% E (hằng có sẵn); tối đa **1** thang Nonstop |
-| C32 | (Nonstop) Ngưỡng thanh lý tối thiểu khi khớp đủ mọi lớp (N2), đo từ giá lớp cuối | **Đề xuất 3%** (= mức "liq ≥ 3%" của SPEC 4.12.2; theo 6B.8 ≈ ≤ 28× E). Lựa chọn khác: 2% (≈ 40×), 1% (≈ 66×, cần leverage > 50). Kiểu 34–95× hiện tại của anh không qua 3% |
-| C33 | (Nonstop) Trần bội số | **Giữ hằng cứng hiện có**: R10a 15× cùng chiều, R9a 20× tổng, leverage ≤ 50; nâng = đổi mã + review |
+| C32 | (Nonstop) Ngưỡng thanh lý tối thiểu theo **đường khớp** (N2): mọi `d_k` (khoảng cách liq từ giá lớp k khi lớp k vừa khớp) | **Đề xuất 3%** (= mức "liq ≥ 3%" của SPEC 4.12.2). Không có quy đổi ra bội số: mỗi thang phải tính (vd 25.64× → 2.78% FAIL; 21.66× → 3.70% PASS). Lựa chọn khác: 2%, 1%. Kiểu 30–95× hiện tại của anh không qua 3% |
+| C33 | (Nonstop) Trần bội số | **Trần hiệu lực = min(hồ sơ, cấu hình Nonstop, hằng cứng)**; hằng cứng không thay trần hồ sơ. Với hồ sơ Mạo hiểm hiện tại: **5× cùng chiều / 7× tổng** cho mọi leg kể cả Nonstop. Muốn lớn hơn: nâng trần hồ sơ (tăng rủi ro §2.4, ≤ 15× / 20× cứng); > 15× = đổi hằng + leverage 50 (đổi mã + review). Mặc định: giữ như vậy, không có trần Nonstop riêng vượt hồ sơ |
 | C34 | (Nonstop) Ngưỡng cảnh báo | `ns_liq` < 10% / 5% (CAO), < 3% và < N2 (KHẨN); `ns_multiple` > **10×** và mỗi +5×; nhắc 30 / 5 phút; trễ 1 điểm / 1× |
@@ -1272,4 +1370,6 @@
 | C38 | (Nonstop) Khi bị thanh lý / SL Nonstop `fail_execute` | Thanh lý → KHẨN, tắt Nonstop, tính 1 SL trong chuỗi stop; `fail_execute` SL Nonstop → chỉ KHẨN, không tự đóng |
-| C39 | (Nonstop) Pha | **PN**: sau cổng Demo P1 của Kiểm soát + U58 + U59–U66 + D34–D37; không chờ thêm thời gian live |
+| C39 | (Nonstop) Pha | **PN**: sau cổng Demo P1 của Kiểm soát + U58 + U59–U67 + U68 (sổ nonstop) + U69 (phần Nonstop) + U70 + D34–D37 (§6B.7); không chờ thêm thời gian live |
 | C40 | (Nonstop) Giới hạn thang `dca` (R27n) | 1–12 lớp; `d` ≥ 0.10%; `mult` 0.80–1.00; lớp đầu ≤ 10× E; TP nếu có ≥ 0.10%; SL nếu có phải trước giá liq khớp đủ |
+| C41 | Xô âm (lỗ Scalp/Nonstop vượt vốn đã cấp): phần thiếu trừ vào vốn Wide dùng để tính size ngay (`E_wide_sizing = E − max(0, E_risk) − max(0, E_ns)`), xô khoá, refill chỉ khi xô không còn leg mở | Có |
+| C42 | Khoá `UNRESOLVED_CLOSE` (lệnh đóng chưa xác định): chỉ gỡ khi xác định được, hoặc sau ≥ 24 h bằng `ops clear --confirm`; không có duyệt bất chấp ở P1 | Có |
````
