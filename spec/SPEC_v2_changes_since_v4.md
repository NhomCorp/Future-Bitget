# SPEC v2 – Thay đổi kể từ bản v4 (vòng 4)

Tác giả: trhieu6179
Ngày: 2026-10-20 (UTC+7)
Bản gốc so sánh: `SPEC_v2_additions_draft.md` 1100 dòng tại commit 58b9ba5 (bản sao `draft_v4_1100.md`). Bản mới: 1276 dòng.
Phạm vi: chỉ phần thay đổi, lấy từ `diff -U1` thật giữa hai bản. Mức tài liệu (spec): chưa có mã, chưa chạy test nào, không gọi endpoint riêng của Bitget. SPEC.md và REVIEW_2026-10-20.md không đổi (sha256 OK).

## 1. Bảng trạng thái

| Yêu cầu | Trạng thái | Điều khoản | Test |
|---|---|---|---|
| A. Chốt C12, C20, C21, C24, C25, C27, C29 theo mặc định, bỏ khỏi danh sách mở | XONG | §12.1 (đã chốt), §12.2 (còn mở) | không cần test mới; các test cũ của các điều này giữ nguyên |
| B. Tách chế độ Kiểm soát / Nonstop (`regime`, vào hash, plan cũ = kiem_soat) | XONG | §0 C13, §1.1 nguyên tắc 4, §5.4, §5.6, §6B.0 | U59 |
| B. Nonstop: SL/TP tuỳ chọn, giới hạn thang `dca` (R27n) | XONG (giới hạn là đề xuất C40) | §6B.2 | U59 |
| B. Gần thanh lý chỉ cảnh báo, không dựng reduce, không tự giảm/đóng; vẫn bán tự động | XONG | §6B.3, §6B.4, ghi chú phạm vi §6A, §8.3 | U63, U64, D34 |
| B. Chốt chặn 1: xô Nonstop có trần % cứng + sổ; nói rõ cross margin thanh lý ăn cả tài khoản, kiểm tra theo đó | XONG (tỉ lệ 10% là đề xuất C31) | §6B.0, §6B.1, §6B.2 N1/N3, §10.2, §10.3 | U61 |
| B. Chốt chặn 2: khoảng cách thanh lý tối thiểu khi khớp đủ mọi lớp | MỘT PHẦN: cơ chế + công thức xong; **ngưỡng chưa chốt** (đề xuất 3%, C32); mô hình liq ước tính chưa so với `liquidationPrice` thật của sàn | §6B.2 N2, §6B.8, §6A.2 | U60 (giá trị tính), D35 (so với sàn, chưa chạy) |
| B. Chốt chặn 3: xác nhận rủi ro khi bật + mỗi lần duyệt; preview có "không có SL", liq khớp đủ, bội số × vốn | XONG | §6B.3, §10 CLI `--ack` | U62 |
| B. Cảnh báo khi chạy (ngưỡng liq, bội số > X), không tắt được, khử trùng + nhắc lại + trễ | XONG (ngưỡng là đề xuất C34) | §6B.4, §8.3, §10 (`alerts mute` từ chối `ns_*`) | U63, D34 |
| B. Thu hẹp bất biến "SL luôn trên sàn" về Kiểm soát; liệt kê mọi điều/test/bất biến giả định có SL và cách áp cho Nonstop | XONG | §6B.5 (bảng), §6.2, §6.4, §6.5, §6A, §8.4, §9.3, §9.4; U29/U31 ghi "(Kiểm soát)" | U64, U31, D37 |
| B. Tương tác với bậc hồ sơ | XONG dưới dạng câu hỏi (C30, mặc định chỉ Mạo hiểm) | §6B.1 | U62 |
| B. Cùng tồn tại cùng symbol + chiều (mặc định không), khoá ngày, trần 2.5× | XONG dưới dạng câu hỏi (C35, C36, C33) | §6B.6, §8.4 | U65, D36 |
| B. Phát hiện thanh lý → KHẨN + tắt Nonstop | MỘT PHẦN: hành vi xong; tên `businessType` của bill (`burst_*_loss_query`, `force_close_*`) **chưa kiểm** với tài liệu Bitget | §6B.5 dòng R20, C38 | U66 |
| B. Pha: không trong P1, sau cổng Demo Kiểm soát | XONG | §6B.7, §9.7 Q-13 (cổng PN) | (cổng) |
| B. Test unit + Demo cho chốt chặn mới | XONG ở mức spec (U59–U66, D34–D37); chưa có mã | §11 | U59–U66, D34–D37 |
| B. Script tính toán kiểu của anh 30×/60×/95× trên 524.7 USDT | XONG; là **tính toán**, không phải dữ liệu sàn; script ở scratch, không đưa vào repo | §6B.8 | U60 tái tạo các số |
| C. Changelog này | XONG | – | – |

Phát hiện cần anh biết: với các hằng cứng hiện có (R10a 15× cùng chiều, R9a 20×, leverage ≤ 50) và N2 đề xuất 3%, kiểu 34–95× hiện tại **không qua** được; ~95× với lớp đầu 10× / mult 0.87 còn không khớp đủ được trước thanh lý (§6B.8). Spec không nới hằng nào (C33).

## 2. Câu hỏi cho chủ – mới / đổi

Đã chốt (chuyển sang §12.1, theo mặc định): C12, C20, C21, C24, C25, C27, C29.

Mới (§12.2):

| # | Câu hỏi | Mặc định đề xuất |
|---|---|---|
| C30 | (Nonstop) Bậc hồ sơ nào được bật Nonstop? | Chỉ **Mạo hiểm có kiểm soát**; Thận trọng và Cân bằng không |
| C31 | (Nonstop) Tỉ lệ xô Nonstop và số thang | **10% E**; Scalp + Nonstop ≤ 20% E (hằng có sẵn); tối đa **1** thang Nonstop |
| C32 | (Nonstop) Ngưỡng thanh lý tối thiểu khi khớp đủ mọi lớp (N2), đo từ giá lớp cuối | **Đề xuất 3%** (= mức "liq ≥ 3%" của SPEC 4.12.2; theo 6B.8 ≈ ≤ 28× E). Lựa chọn khác: 2% (≈ 40×), 1% (≈ 66×, cần leverage > 50). Kiểu 34–95× hiện tại của anh không qua 3% |
| C33 | (Nonstop) Trần bội số | **Giữ hằng cứng hiện có**: R10a 15× cùng chiều, R9a 20× tổng, leverage ≤ 50; nâng = đổi mã + review |
| C34 | (Nonstop) Ngưỡng cảnh báo | `ns_liq` < 10% / 5% (CAO), < 3% và < N2 (KHẨN); `ns_multiple` > **10×** và mỗi +5×; nhắc 30 / 5 phút; trễ 1 điểm / 1× |
| C35 | (Nonstop) Cho Nonstop và Kiểm soát cùng symbol + cùng chiều? | **Không** (hedge mode gộp vị thế, SL Kiểm soát sẽ đóng cả phần Nonstop); khác chiều thì được |
| C36 | (Nonstop) Khoá ngày/tuần/DD/xô với Nonstop | **Chặn** mở thang mới và thêm lớp; **không** tự huỷ lệnh chờ Nonstop (chúng vẫn có thể khớp); không tự đóng |
| C37 | (Nonstop) Reduce do anh tự gọi trên leg Nonstop | Dùng **cùng cổng** `REDUCE_SL_MODE` (D26); `ladder close` 100% và `entries` luôn được; không bao giờ dựng sẵn |
| C38 | (Nonstop) Khi bị thanh lý / SL Nonstop `fail_execute` | Thanh lý → KHẨN, tắt Nonstop, tính 1 SL trong chuỗi stop; `fail_execute` SL Nonstop → chỉ KHẨN, không tự đóng |
| C39 | (Nonstop) Pha | **PN**: sau cổng Demo P1 của Kiểm soát + U58 + U59–U66 + D34–D37; không chờ thêm thời gian live |
| C40 | (Nonstop) Giới hạn thang `dca` (R27n) | 1–12 lớp; `d` ≥ 0.10%; `mult` 0.80–1.00; lớp đầu ≤ 10× E; TP nếu có ≥ 0.10%; SL nếu có phải trước giá liq khớp đủ |

## 3. Phần mới / thay toàn bộ (in đầy đủ)

#### §6B (mới)

## 6B. Chế độ vận hành Nonstop ("gối lệnh", SL/TP không bắt buộc) [mới; yêu cầu của chủ 2026-10-20; **chưa có trong P1**]

> Ý của chủ: chạy kiểu DCA "gối lệnh" quen dùng: thang dày, TP mỏng hoặc không có, gần như không có SL; khi giá thanh lý tới gần thì công cụ **chỉ cảnh báo**. Công cụ vẫn là **bán tự động**: không bao giờ đặt lệnh nếu anh chưa duyệt.

### 6B.0 Hai chế độ vận hành

| | **Kiểm soát** (`regime: kiem_soat`) | **Nonstop** (`regime: nonstop`) |
|---|---|---|
| Gồm | Wide và Scalp – toàn bộ phần còn lại của tài liệu này | thang DCA dày (`mode: dca`), chỉ trong chế độ này |
| SL | **bắt buộc**, luôn trên sàn (I1) | **tuỳ chọn**; nếu anh đặt thì công cụ giữ nó trên sàn (I1n, 6B.5) |
| TP | bắt buộc TP1/TP2 (hoặc TP_a/TP_b) | **tuỳ chọn**; có thể rất mỏng (≥ 0.10%) hoặc không có |
| Giới hạn lỗ | WCL ≤ ngân sách hồ sơ (I2, R14) | **không có giới hạn lỗ hữu hạn**: thay bằng các chốt chặn trước khi duyệt N1–N4 (6B.2) |
| Khi thanh lý tới gần | cảnh báo + dựng sẵn đề xuất chờ duyệt (§6A.6) | **chỉ cảnh báo**, không dựng đề xuất reduce, không tự giảm/đóng/huỷ (6B.4) |
| Đặt lệnh | chỉ sau khi duyệt đúng phiên bản + hash | như trái, **cộng** bước xác nhận rủi ro mỗi lần duyệt (6B.3) |
| Pha | P1 / P1b | **PN** – sau khi Kiểm soát qua cổng Demo P1 (6B.7) |

- Trường `regime` nằm trong plan (§5.6), trong `hash_content` (§5.4) và trong hồ sơ. Mặc định `kiem_soat`; plan cũ không có trường này được đọc là `kiem_soat`.
- **Thành thật về cross margin**: tài khoản là cross, nên **thanh lý của thang Nonstop lấy ký quỹ của cả tài khoản**, không chỉ của xô Nonstop. Một lần thanh lý có thể mất **gần như toàn bộ E** (kể cả phần "an toàn" của Wide). Xô Nonstop (6B.1) là kỷ luật sổ sách; mọi chốt chặn về thanh lý và bội số (N1, N2) vì vậy tính trên **E toàn tài khoản với mọi leg**.

### 6B.1 Bật Nonstop, bậc hồ sơ, xô Nonstop

- Bật bằng `profile set --nonstop-bucket N --confirm` + xác nhận rủi ro khi bật (6B.3). Đây là **tăng rủi ro** theo §2.4: `pending` 24 h, bị từ chối khi đang khoá, tối đa 1 lần tăng/7 ngày. Tắt (`--nonstop-bucket 0`) = hạ rủi ro, hiệu lực ngay; thang Nonstop đang chạy không bị đóng, chỉ chặn mở thang Nonstop mới.
- **Bậc hồ sơ** (câu hỏi C30, mặc định): Thận trọng **không** bật được; Cân bằng **không**; Mạo hiểm có kiểm soát **được**.
- **Xô Nonstop**: `E_ns_base = share_ns × E` khi bật/refill; sổ `nonstop_ledger` dùng **đúng cách ghi theo sự kiện** của §3.1 (`open_fee`, `close_pnl`, `close_fee`, `funding`, khoá `tradeId`/`billId`); `E_ns(t) = E_ns_base + realized_ns + upnl_ns`.
- Trần: `share_ns` theo C31 (mặc định đề xuất 10% E); **tổng xô Scalp + xô Nonstop ≤ `HARD_RISK_BUCKET_MAX` = 20% E** (dùng chung hằng có sẵn, không thêm hằng mới).
- Khoá xô Nonstop: `E_ns(t) ≤ 50% × E_ns_base` (cùng tỉ lệ 50% như xô Scalp) → chặn mở thang Nonstop mới và thêm lớp; **không** tự đóng hay huỷ gì (6B.4). Mở khoá: như §3.2 (mốc tháng + `bucket refill --nonstop --confirm`).
- Vì không có SL, khoá xô **không giới hạn được lỗ**: lỗ thực tế có thể vượt xô tới mức thanh lý toàn tài khoản. Preview và README PHẢI ghi câu này.

### 6B.2 Chốt chặn trước khi duyệt (mọi `execute` và mọi `ladder apply` làm tăng rủi ro của thang Nonstop)

| # | Kiểm tra | PASS | Ghi chú |
|---|---|---|---|
| N1 | **Bội số** | notional khi **khớp đủ mọi lớp** của thang Nonstop + mọi leg khác (cùng chiều / tổng) ≤ trần R10a / R9a hiện có (cứng 15× / 20× E) và ≤ `nonstop.max_multiple_x` (C33) | R10w (2.5× cùng chiều Wide) **không** áp cho Nonstop; R10a/R9a tài khoản **có** áp |
| N2 | **Thanh lý khi khớp đủ** | `liq_dist_all_fill` ≥ `nonstop.min_liq_all_fill_pct` (C32 – **chưa chốt**, đề xuất 3%) | tính bằng mô hình xấu nhất toàn tài khoản §6A.2: mọi lớp Nonstop **và** mọi lớp chờ của leg khác cùng chiều coi như đã khớp, leg ngược chiều chỉ tính MM; khoảng cách đo **từ giá lớp cuối** (lúc khớp đủ, mark ≈ giá lớp cuối). Giá liq ≥ giá lớp cuối (long) = thang không khớp đủ được trước thanh lý → FAIL |
| N3 | **Xô** | xô Nonstop đang bật, không khoá; `share_ns` và tổng xô ≤ trần | 6B.1 |
| N4 | **Xác nhận rủi ro** | mã xác nhận của đúng phiên bản (6B.3) | mỗi lần duyệt |
| R27n | **Tham số thang** (C40, mặc định đề xuất) | 1–12 lớp; `d` ≥ 0.10%; `mult` 0.80–1.00; lớp đầu ≤ 10× E; TP nếu có ≥ 0.10% (preview in lãi ròng sau phí 0.02% + 0.06%); SL nếu có: phía đúng, ngoài lớp cuối ≥ `d`, và **nằm trước giá liq khớp đủ** (long: SL > liq) – nếu không thì FAIL "SL vô dụng vì thanh lý trước" | thay R27w/R27s cho `mode: dca` |
| R16/R17 | ký quỹ, đòn bẩy | như SPEC (R16 80% `crossedMaxAvailable` như Scalp; leverage ≤ `HARD_LEVERAGE_MAX_PER_SYMBOL` = 50) | hệ quả: notional khớp đủ ≲ 40× E (ký quỹ ban đầu = notional/leverage) |

Các kiểm tra chung vẫn áp: R1–R7 (dữ liệu, symbol, 1 thang mỗi (symbol, holdSide) – 6B.6), R23 post-only, R26 giờ cấm, R27 phần chung, R29 phiên bản, R30 đèn, khoá §8.4.

### 6B.3 Xác nhận rủi ro (bắt buộc)

- **Khi bật Nonstop**: CLI yêu cầu gõ đúng câu: `TÔI HIỂU: KHÔNG CÓ SL, CÓ THỂ MẤT TOÀN BỘ TÀI KHOẢN` (lưu vào hồ sơ: thời điểm, phiên bản hồ sơ).
- **Mỗi lần duyệt plan Nonstop** (`execute` / `ladder apply` tăng rủi ro): `--ack NS-<6 hex hash>-<liq_dist_all_fill 2 chữ số>` (vd `NS-a41c09-2.30`). Mã lấy từ preview của **đúng** phiên bản; sai/thiếu → R29 FAIL. Trợ lý chat **không được** tự điền mã: chỉ chuyển nguyên văn mã anh gõ (quy tắc §1.1 mục 2; công cụ không phân biệt được ai gõ – đây là quy tắc cho trợ lý, ghi rõ là giới hạn).
- Preview Nonstop PHẢI có, ở đầu và không thể tắt:

```
NONSTOP 9KD2.v1  ETH long (dca)   ⚠ KHÔNG CÓ SL   TP: +0.15% (lãi ròng ~0.07%/lần)
Khớp đủ 4 lớp:   notional 17173.74 USDT = 32.7× vốn (E 524.70)
Thanh lý nếu khớp đủ (ước tính, mmr 0.5%): 2334.19 = cách lớp cuối 2.30% / cách lớp 1 2.74%
Nếu bị thanh lý: mất tới gần như TOÀN BỘ tài khoản (~524 USDT), không chỉ xô Nonstop (52.47)
Chốt chặn: N1 FAIL (32.7× > 15×)  N2 FAIL (2.30% < 3% – ngưỡng đề xuất, chưa chốt)
Mã xác nhận: NS-a41c09-2.30   (gõ: execute 9KD2.v1 --confirm --hash a41c09 --ack NS-a41c09-2.30)
```
(Ví dụ minh hoạ dùng thang ~30× ở 6B.8; hash minh hoạ.)

### 6B.4 Khi đang chạy: chỉ cảnh báo

- Watcher **không** gửi lệnh nào cho leg Nonstop ngoài: (a) entry/TP đã duyệt (đặt lại TP sau mỗi fill như Scalp SPEC 4.12.3, nếu có TP); (b) SL đã duyệt (nếu có, I1n). **Không** dựng sẵn reduce, **không** tự reduce/đóng, **không** tự huỷ lớp chờ (kể cả khi khoá ngày, khoá xô, hay khi liq tới gần – khác với quy tắc huỷ lớp của Scalp SPEC 4.12.3c; xem C36).
- **Hai loại cảnh báo** (ngưỡng ở C34):
  - `ns_liq`: khoảng cách thanh lý xấu nhất toàn tài khoản **từ mark**, in hai số: hiện tại (lớp đã khớp) và nếu khớp nốt các lớp chờ. Mức đề xuất: < 10% CAO, < 5% CAO, < 3% KHẨN, < N2 KHẨN.
  - `ns_multiple`: bội số notional đang mở / E > X (đề xuất 10×) và mỗi bậc +5× sau đó.
- **Chống lặp / nhắc lại**: khoá chống trùng `(leg, kind, level)`. Báo ngay khi **vào** một mức xấu hơn (leo mức → báo ngay, không chờ). Ở yên trong mức: nhắc lại mỗi **30 phút** (CAO) / **5 phút** (KHẨN). Ra khỏi mức chỉ khi tốt hơn ngưỡng + **1 điểm %** (`ns_liq`) hoặc − **1×** (`ns_multiple`) – tránh nhấp nháy; ra khỏi mức thì gửi 1 tin "đã hồi về …". Mỗi tin có: giá liq, khoảng cách, bội số, lớp chờ còn lại, và câu cố định "Công cụ không tự giảm/đóng. Anh có thể tự chạy: `entries <root> --cancel-all`, `ladder close <root>`, hoặc `reduce` (nếu được phép – 6B.6)."
- **Không tắt được**: `alerts mute` / giờ yên lặng từ chối với `ns_*` ("cảnh báo Nonstop không tắt được"); KHẨN gửi cả kênh chat và email (Q6). Lỗi gửi → thử lại theo hàng đợi, ghi log; không có cờ nào bỏ qua.

### 6B.5 Phạm vi của các bất biến và điều khoản giả định có SL

Quy tắc chung: mỗi leg mang cờ `sl_required` = `true` (Kiểm soát) hoặc `false` (Nonstop không có SL). Leg Nonstop **có** SL đã duyệt mang `sl_present = true` và chịu I1n: SL đó phải luôn trên sàn, chỉ thay bằng cách §6.4 (modify / đặt-mới-rồi-huỷ), không bao giờ tự dời xa, không bao giờ tự thêm SL cho leg không có.

| Điều khoản / test | Kiểm soát | Nonstop không SL | Nonstop có SL |
|---|---|---|---|
| I1 "luôn có SL" (§6.2), SPEC 8.2(3) "SL trước tiên", `on_sl_failure: close_leg` | giữ nguyên | **không áp dụng**: watcher không đặt `pos_loss`, không `close_leg` (U64) | I1n: thiếu SL → đặt lại đúng giá đã duyệt + KHẨN; `on_sl_failure` = chỉ KHẨN, **không** `close_leg` (đóng = hành động tự động, trái 6B.4) |
| I2, WCL, `L_run` (§6.2–6.3) | giữ nguyên | không có WCL hữu hạn → thay bằng N1–N3 với trạng thái thật | WCL theo §6.3 được tính và hiển thị; thêm điều kiện SL trước liq (R27n) |
| R13 (SL cách lớp cuối), R15 (liq sau SL) | giữ nguyên | không áp; thay bằng N2 | R27n mục SL thay R13; N2 thay R15 |
| R14 Σ lỗ tại SL (§9.2), U37 | giữ nguyên cho leg Kiểm soát | leg không SL **không** cộng vào R14 (lỗ không hữu hạn); khi có leg Nonstop mở, preview mọi plan Kiểm soát in: "Cam kết lỗ tối đa chỉ đúng cho từng thang Kiểm soát; thanh lý do Nonstop có thể mất toàn bộ tài khoản" | WCL cộng vào R14 |
| R8, R10w, thông số Scalp, R28 | giữ nguyên | không áp | không áp |
| R9a / R10a / R16 / R17, ma trận §3.5 | giữ nguyên | áp (N1), tính mọi leg | áp |
| §6.4 thứ tự `ladder apply` | giữ nguyên | bỏ SL_TIGHTEN/SL_LOOSEN; PLACE_ENTRY chỉ khi N1–N2 PASS với trạng thái thật | như Kiểm soát cho bước SL; PLACE_ENTRY theo N1–N2 |
| §6.5 phục hồi | giữ nguyên | như cũ, trừ: ngoại lệ "watcher đặt `pos_loss` khi thiếu" không áp; quy tắc 3 "kiểm I2" → kiểm N1–N2 | ngoại lệ áp cho SL đã duyệt |
| §6A reduce: RECONCILING "đúng 1 `pos_loss`", điều kiện kết thúc "đúng 1 SL", bảng TP 6A.5, U42/U47/U55 | giữ nguyên | số SL kỳ vọng = **0** (thấy SL lạ → ABORTED + CAO, không đụng); kết thúc: 0 SL; TP chỉ đặt lại nếu plan có TP | số SL kỳ vọng = 1 (như Kiểm soát) |
| §6A.0 cổng `REDUCE_SL_MODE` | giữ nguyên | reduce do **anh tự gọi** dùng **cùng cổng** (C37: D26 cũng là bằng chứng đóng một phần đúng leg trong hedge mode); `ladder close` 100% và `entries` luôn được | như trái |
| §6A.6 cảnh báo + dựng sẵn | giữ nguyên | **không dựng sẵn**; chỉ cảnh báo 6B.4 | như trái |
| §8.4 khoá ngày/tuần/DD/UNKNOWN | giữ nguyên | **chặn mở thang Nonstop mới và thêm lớp** (C36); lệnh chờ Nonstop đã treo **không** bị huỷ và **vẫn có thể khớp**; bộ đếm ngày gồm uPnL Nonstop (một bộ đếm toàn TK) → Nonstop lỗ sâu có thể khoá mở mới cho cả Kiểm soát | như trái |
| Chuỗi stop R20 | giữ nguyên | không có SL; **thanh lý** (bill `burst_*_loss_query` / `force_close_*`) → KHẨN, tắt Nonstop (bật lại theo 6B.1), tính như 1 SL trong chuỗi (C38) | SL kích hoạt tính như Kiểm soát |
| `kill` (§9.3), U31, D23 | giữ nguyên | huỷ entry + TP; leg còn vị thế **không có bảo vệ nào** – kết quả `kill` in rõ "ETH long Nonstop: KHÔNG có SL"; xác nhận "mỗi leg Kiểm soát có đúng 1 SL" chỉ áp cho leg Kiểm soát | giữ SL |
| `fail_execute` pos_loss (§9.4), Q-7 nhánh SL/BE, U32 | giữ nguyên | không áp (không có SL) | `fail_execute` của SL Nonstop → KHẨN, **không** tự `close-positions` (C38 hỏi lại) |
| U29 / U47 "không có thời điểm leg có vị thế mà 0 SL" | giữ nguyên | chỉ áp cho leg `sl_required`; leg Nonstop không SL kiểm ngược lại: **0 lệnh SL** được tạo | áp cho SL đã duyệt |
| Kỳ vọng §2.6 / B9 | giữ nguyên | không có backtest → digest in "chưa kiểm định bằng backtest" | như trái |

### 6B.6 Cùng tồn tại với Kiểm soát

- **Cùng symbol + cùng chiều**: hedge mode **gộp** mọi lệnh cùng (symbol, holdSide) thành một vị thế, nên một thang Nonstop và một thang Kiểm soát cùng ETH long sẽ dùng chung giá TB, chung `pos_loss` cấp vị thế (SL của Kiểm soát sẽ đóng cả phần Nonstop) → **không cho phép** (giữ quy tắc §3.5 mục 1 "một thang mỗi (symbol, holdSide) bất kể chế độ", R6 FAIL). Câu hỏi C35, mặc định: không.
- **Cùng symbol, khác chiều** (vd Nonstop ETH long + Wide ETH short): được, theo ma trận §3.5; leverage symbol dùng chung (§3.5 mục 5).
- **Số thang**: tổng mọi chế độ ≤ 4 (2 symbol × 2 chiều); Nonstop ≤ 1 cùng lúc (C31, mặc định 1).
- **Cap 2.5× cùng chiều**: đó là R10w của Wide (cứng 2.5×) – **không áp** cho Nonstop; trần cùng chiều toàn tài khoản R10a (cứng 15×) **có áp** (N1).
- **Khoá ngày**: chặn mở Nonstop mới (6B.5). Nonstop không được dùng để "gỡ" sau khi Kiểm soát bị khoá.

### 6B.7 Pha và cổng

- **PN** (không thuộc P1/P1b): bật được khi (1) cổng Demo P1 của Kiểm soát đạt (Q-13); (2) sổ xô theo sự kiện đạt (U58); (3) U59–U66 và D34–D37 đạt; (4) chủ trả lời C30–C40. Câu hỏi C39 (mặc định: như vậy, không chờ thêm 4 tuần live).
- Trước PN: `regime: nonstop` bị từ chối ở `propose`/`plan import`/`execute` với thông báo pha.

### 6B.8 Tính toán minh hoạ – thanh lý khi khớp đủ, kiểu thang của chủ

> **Đây là phép tính, không phải dữ liệu sàn.** Script `/workspace/scratch/spec_v2/r4/nonstop_liq.py` (Decimal). Giả định: ETHUSDT long, P₁ 2400.00, E = 524.7, cross, không có vị thế khác, `mmr` 0.5% (MMR bậc thật theo notional có thể cao hơn → liq **gần hơn**), phí mở maker 0.02%, size floor lot 0.01, giá floor tick 0.01. Công thức §6A.2: `W + Q(P − A) ≤ mmr·Q·P`, `W = E − phí mở`. Kiểu thang theo chủ: `d` 0.11–0.18%, `mult` 0.87, lớp đầu ~10× E.

| Kịch bản | lớp đầu / mult / d / số lớp | Notional khớp đủ (×E) | Q ETH | Giá TB | Giá lớp cuối | Liq ước tính | Cách lớp cuối | Cách giá TB | Cách lớp 1 |
|---|---|---|---|---|---|---|---|---|---|
| ~15× (lớp đầu 5×, để so sánh) | 5× / 0.87 / 0.15% / 4 | 16.3× | 3.58 | 2395.23 | 2389.21 | 2260.44 | 5.39% | 5.63% | 5.81% |
| ~20× (lớp đầu 5×) | 5× / 0.87 / 0.15% / 6 | 21.7× | 4.75 | 2392.45 | 2382.05 | 2293.94 | 3.70% | 4.12% | 4.42% |
| ~25× (lớp đầu 5×) | 5× / 0.87 / 0.15% / 8 | 25.6× | 5.63 | 2390.01 | 2374.91 | 2308.84 | 2.78% | 3.40% | 3.80% |
| **~30×** | 10× / 0.87 / 0.15% / 4 | 32.7× | 7.17 | 2395.22 | 2389.21 | 2334.19 | **2.30%** | 2.55% | 2.74% |
| **~60×** | 10× / 0.87 / 0.15% / 11 | 60.0× | 13.20 | 2386.83 | 2364.24 | 2359.36 | **0.21%** | 1.15% | 1.69% |
| ~60×, d 0.11% | 10× / 0.87 / 0.11% / 11 | 60.0× | 13.18 | 2390.35 | 2373.73 | 2362.83 | 0.46% | 1.15% | 1.55% |
| ~60×, d 0.18% | 10× / 0.87 / 0.18% / 11 | 60.0× | 13.21 | 2384.22 | 2357.14 | 2356.76 | 0.02% | 1.15% | 1.80% |
| **~95×** (lớp đầu 15×) | 15× / 0.87 / 0.15% / 13 | 96.1× | 21.15 | 2385.08 | 2357.15 | 2372.61 | **−0.66%** (liq **trên** lớp cuối) | 0.52% | 1.14% |
| ~95× (mult 0.97, 12 lớp) | 10× / 0.97 / 0.15% / 12 | 101.8× | 22.42 | 2381.54 | 2360.69 | 2370.46 | −0.41% | 0.47% | 1.23% |

- Với lớp đầu 10× và `mult` 0.87, tổng chuỗi vô hạn chỉ là 10/(1 − 0.87) = **76.9×** → 95× không đạt được nếu không tăng lớp đầu hoặc `mult`. Ở ~95×, **thanh lý xảy ra trước khi các lớp cuối kịp khớp** (khoảng cách âm) – thang không bao giờ khớp đủ được.
- Lũy tiến ở thang ~60× (d 0.15%): khoảng cách liq từ giá lớp vừa khớp = 9.56% (L1, 10×) → 4.79% (L2, 18.6×) → 3.16% (L3, 26.2×) → 2.30% (L4, 32.7×) → 1.76% (L5) → 1.36% → 1.06% → 0.80% → 0.58% → 0.39% → 0.21% (L11, 60×).
- Quy đổi xấp xỉ (coi cả thang như 1 lớp tại giá cuối): liq ≥ 10% ⇔ ≲ 9.6× E; ≥ 5% ⇔ ≲ 18.2×; ≥ 3% ⇔ ≲ 28.5×; ≥ 2% ⇔ ≲ 39.8×; ≥ 1% ⇔ ≲ 66×.
- **Hệ quả cho ngưỡng N2 (C32)**: ngưỡng đề xuất 3% (= mức tối thiểu "liq ≥ 3% khi thêm lớp" đã có ở SPEC 4.12.2) cho phép khoảng ≤ 28× E; kiểu 34–95× của chủ **không qua** N2 ở 3%, và cũng **không qua** trần cứng hiện có R10a 15× / R9a 20× / leverage 50 (N1, R16). Muốn chạy 30–60× thì phải hạ N2 về ~2% / ~0.2% **và** nâng hằng cứng – đó là quyết định của chủ (C32, C33), tài liệu này **không** tự chốt.

---

#### §12 (thay toàn bộ: tách 12.1 đã chốt / 12.2 còn mở, thêm C30–C40)

## 12. Câu hỏi cho chủ

### 12.1 Đã chốt (2026-10-20)

| # | Quyết định | Trạng thái |
|---|---|---|
| C12 | Khoá ngày **không** huỷ lệnh chờ Wide; các lệnh này vẫn có thể khớp trong lúc khoá (khoá chỉ chặn gửi lệnh mở mới, §8.4) | đã chốt 2026-10-20 (theo mặc định) |
| C20 | P1: reduce `cancel_all` – luôn huỷ mọi lớp chờ của leg trước khi đóng; giữ/huỷ một phần = pha sau; `entry_adjust` được chọn lớp | đã chốt 2026-10-20 (theo mặc định) |
| C21 | Bản dựng sẵn khi cảnh báo thanh lý = reduce 30% + huỷ mọi lớp chờ (hoặc entry_adjust nếu chỉ huỷ lớp đã đủ); ngưỡng 30% / 20% / 10% (Thận trọng / Cân bằng / Mạo hiểm); không tự chạy | đã chốt 2026-10-20 (theo mặc định) |
| C24 | Không có `preplace_guard`. Nếu D26 FAIL: reduce một phần giữ tắt; chỉ `entries` và `ladder close` 100% | đã chốt 2026-10-20 (theo mặc định) |
| C25 | Chỉ gửi lại khi `VERIFIED_NOT_RECEIVED` và trước `expires_at` cố định; ngược lại cảnh báo + duyệt phiên bản mới | đã chốt 2026-10-20 (theo mặc định) |
| C27 | Chỉ hiển thị số kỳ vọng từ B9 cho đúng cấu hình; không có ngoại lệ SAFE | đã chốt 2026-10-20 (theo mặc định) |
| C29 | Mốc ngày/tuần không có và không dựng lại được → chặn mọi hành động tăng rủi ro tới mốc kế tiếp (tuần: tới thứ Hai 07:00 UTC+7) | đã chốt 2026-10-20 (theo mặc định) |

### 12.2 Còn mở

| # | Câu hỏi | Mặc định đề xuất |
|---|---|---|
| C1 | Bảng tham số 3 bậc (§2.2) – đồng ý các con số? | Đồng ý; bắt đầu live ở **Cân bằng** (Thận trọng nếu muốn tuần 1 nhỏ hơn) |
| C2 | Bậc Mạo hiểm chỉ được bật sau B6 đạt **và** 4 tuần live Cân bằng không sự cố? | Có |
| C3 | Ranh giới ngày 07:00 UTC+7 (thay 00:00) cho mọi bộ đếm; tuần từ thứ Hai 07:00 | Có |
| C4 | Tăng rủi ro hồ sơ: chờ 24 h, tối đa 1 lần/7 ngày, cấm khi đang khoá | Có |
| C5 | Ngân sách lỗ xô = 50% xô (Cân bằng 5% E, Mạo hiểm 10% E); mỗi thang Scalp 2.5% / 5% E | Có |
| C6 | Xô khoá đến 07:00 ngày 1 tháng sau và ≥ 7 ngày, rồi phải `bucket refill --confirm` (= share × E lúc đó) | Có |
| C7 | Đèn đỏ sau khi cổng 6.8 đạt: chặn cứng, không override | Chặn cứng |
| C8 | Thang đã TP1 (`TP1_DONE`): cấm thêm entry khi sửa | Cấm |
| C9 | WCL không dùng lãi đã chốt của thang làm đệm để dời SL xa | Không dùng |
| C10 | TP mặc định là trigger-market (taker, không chiếm vị thế), chấp nhận mất ~0.04% notional mỗi lần chốt | Có |
| C11 | Đề xuất dùng `market_shift` (dịch nguyên thang ≤ 0.3%, size & lỗ tối đa giữ nguyên) mà không hỏi lại | Có |
| C13 | DD breaker: tự mở sau 7 ngày + ép Thận trọng 7 ngày | Có |
| C14 | Thang chờ (chưa khớp lớp 1) tự huỷ sau 24 h | 24 h |
| C15 | Leverage: công cụ chỉ tự đặt khi symbol không có vị thế; tài khoản đang 125–150× thì anh hạ tay trước go-live | Có |
| C16 | Bậc Thận trọng ưu tiên BTC vì ETH lot 0.01 quá thô ở mức vốn này | Có |
| C17 | Giờ và kênh gửi digest | 07:05 UTC+7, kênh chat trợ lý (+ email cho mức CAO/KHẨN, theo Q6) |
| C18 | **(P1b)** Ngưỡng khẩn của `reduce` (dưới mức này `auto` chọn market) | **5%** khoảng cách liq xấu nhất toàn TK, mọi bậc (sàn cứng 3%) |
| C19 | Kiểu thực thi | **P1: chỉ market.** Từ P1b (sau U41 + D27): mặc định maker post-only khi ≥ ngưỡng khẩn, chờ 60 s rồi hỏi |
| C22 | Kiểm tra thêm lớp Scalp dùng `max(3%, ngưỡng cảnh báo bậc)` thay vì chỉ 3% | Có |
| C23 | Lỗ chốt bởi `reduce` tiêu ngân sách thang/xô (lãi không bù), nhưng không tính là SL trong chuỗi stop | Có |
| C26 | Bỏ khoá ngày riêng của Scalp (SPEC 4.12.5), chỉ giữ khoá ngày toàn tài khoản + ngân sách xô | Có |
| C28 | Số thang Scalp tối đa cùng lúc | 1 |
| C30 | (Nonstop) Bậc hồ sơ nào được bật Nonstop? | Chỉ **Mạo hiểm có kiểm soát**; Thận trọng và Cân bằng không |
| C31 | (Nonstop) Tỉ lệ xô Nonstop và số thang | **10% E**; Scalp + Nonstop ≤ 20% E (hằng có sẵn); tối đa **1** thang Nonstop |
| C32 | (Nonstop) Ngưỡng thanh lý tối thiểu khi khớp đủ mọi lớp (N2), đo từ giá lớp cuối | **Đề xuất 3%** (= mức "liq ≥ 3%" của SPEC 4.12.2; theo 6B.8 ≈ ≤ 28× E). Lựa chọn khác: 2% (≈ 40×), 1% (≈ 66×, cần leverage > 50). Kiểu 34–95× hiện tại của anh không qua 3% |
| C33 | (Nonstop) Trần bội số | **Giữ hằng cứng hiện có**: R10a 15× cùng chiều, R9a 20× tổng, leverage ≤ 50; nâng = đổi mã + review |
| C34 | (Nonstop) Ngưỡng cảnh báo | `ns_liq` < 10% / 5% (CAO), < 3% và < N2 (KHẨN); `ns_multiple` > **10×** và mỗi +5×; nhắc 30 / 5 phút; trễ 1 điểm / 1× |
| C35 | (Nonstop) Cho Nonstop và Kiểm soát cùng symbol + cùng chiều? | **Không** (hedge mode gộp vị thế, SL Kiểm soát sẽ đóng cả phần Nonstop); khác chiều thì được |
| C36 | (Nonstop) Khoá ngày/tuần/DD/xô với Nonstop | **Chặn** mở thang mới và thêm lớp; **không** tự huỷ lệnh chờ Nonstop (chúng vẫn có thể khớp); không tự đóng |
| C37 | (Nonstop) Reduce do anh tự gọi trên leg Nonstop | Dùng **cùng cổng** `REDUCE_SL_MODE` (D26); `ladder close` 100% và `entries` luôn được; không bao giờ dựng sẵn |
| C38 | (Nonstop) Khi bị thanh lý / SL Nonstop `fail_execute` | Thanh lý → KHẨN, tắt Nonstop, tính 1 SL trong chuỗi stop; `fail_execute` SL Nonstop → chỉ KHẨN, không tự đóng |
| C39 | (Nonstop) Pha | **PN**: sau cổng Demo P1 của Kiểm soát + U58 + U59–U66 + D34–D37; không chờ thêm thời gian live |
| C40 | (Nonstop) Giới hạn thang `dca` (R27n) | 1–12 lớp; `d` ≥ 0.10%; `mult` 0.80–1.00; lớp đầu ≤ 10× E; TP nếu có ≥ 0.10%; SL nếu có phải trước giá liq khớp đủ |

(Q1, Q3 của SPEC 12 được thay bằng C1/C2; Q7 thay bằng bảng 2.2/§8.4; Q13 thay bằng C5/C6; các Q khác giữ nguyên.)

Các dòng cũ bị bỏ khỏi bảng mở (nội dung mặc định nay ở §12.1):

````diff
-| C12 | Khoá ngày: giữ nguyên lệnh chờ Wide (không tự huỷ). Hệ quả: các lệnh này **vẫn có thể khớp** trong lúc khoá (khoá chỉ chặn gửi lệnh mở mới, §8.4) | Giữ nguyên |
-| C20 | Lớp DCA chưa khớp khi reduce | **P1: reduce luôn huỷ mọi lớp chờ của leg trước khi đóng**; giữ/huỷ một phần = pha sau; riêng huỷ lớp đã đủ → `entry_adjust` (vẫn chọn được lớp, không đóng) |
-| C21 | Ngưỡng cảnh báo thanh lý theo bậc | 30% / 20% / 10% (Thận trọng / Cân bằng / Mạo hiểm); chỉ cảnh báo + dựng sẵn entry_adjust hoặc reduce 30% huỷ mọi lớp chờ (P1), không tự chạy |
-| C24 | Nếu D26 FAIL thì sao? (`preplace_guard` đã bị loại khỏi P1 vì chỉ bao size dự kiến) | **Giữ reduce một phần tắt**; dùng `entries` và `ladder close` (100%); chỉ xem lại khi có bản thiết kế bảo vệ size thật ở mọi bước được viết và kiểm chứng |
-| C25 | Sau crash, có gửi lại lệnh đóng đã duyệt không? | Chỉ khi **chắc chắn chưa tới sàn** (`VERIFIED_NOT_RECEIVED`: chưa từng gửi, hoặc D32 đạt và gửi lại cùng clientOid) **và** trước `expires_at` cố định (120 s từ lúc tạo phiên bản) và mark lệch ≤ 0.3%; kết quả không xác định → không gửi lại, báo, cần duyệt phiên bản mới |
-| C27 | Chỉ hiển thị số kỳ vọng từ B9 cho đúng cấu hình, không ngoại lệ (kể cả Cân bằng); số backtest cũ chỉ được gọi là "kết quả lịch sử của cấu hình khác" | Có |
-| C29 | Không có mốc ngày/tuần và không dựng lại được → chặn mọi hành động tăng rủi ro tới mốc kế tiếp (tuần: có thể tới thứ Hai 07:00) | Có |
````

---

## 4. Các sửa còn lại (trước / sau, diff thật, ngữ cảnh 1 dòng)

Gồm §0 (C4, C13), §1.1, §3.5, §5.4, §5.6, §6.2, §6.4, §6.5, §6A (ghi chú phạm vi, điều kiện SL, RECONCILING), §8.3, §8.4, §9.3, §9.4, §9.7, §10 (CLI, cấu hình `nonstop:`, hằng cứng), §11 (U29, U31, U59–U66, D34–D37). Khối diff dùng rào 4 dấu backtick vì bên trong có dòng ``` của tài liệu gốc.

````diff
@@ -21,3 +21,3 @@
 | C3 | Plan có **phiên bản bất biến** (`<root>.vN` + hash); mỗi lần sửa = tính lại toàn bộ + chạy lại mọi kiểm tra + diff; phiên bản cũ mất hiệu lực | 2.3 |
-| C4 | Thang đang chạy **được sửa tự do trong trần hồ sơ**, qua cùng luồng preview → diff → duyệt. Hai bất biến cứng: luôn có SL trên sàn; lỗ xấu nhất sau sửa ≤ ngân sách lỗ/thang và mọi kiểm tra tài khoản PASS | 1.5 dòng "không đổi tham số tại chỗ", 5.3 |
+| C4 | Thang đang chạy **được sửa tự do trong trần hồ sơ**, qua cùng luồng preview → diff → duyệt. Hai bất biến cứng (chế độ **Kiểm soát**; Nonstop: §6B.5): luôn có SL trên sàn; lỗ xấu nhất sau sửa ≤ ngân sách lỗ/thang và mọi kiểm tra tài khoản PASS | 1.5 dòng "không đổi tham số tại chỗ", 5.3 |
 | C5 | **Chia vốn**: phần an toàn (Wide) + "xô mạo hiểm" ≤ 20% cho Scalp, ngân sách lỗ khoá riêng, không vay phần an toàn | 4.12.2, 4.12.5 |
@@ -30,2 +30,3 @@
 | C12 | Sửa theo review lần 3 (không thêm tính năng): bỏ `preplace_guard` khỏi P1; chặn đường đóng một phần vòng qua cổng; TP sau reduce theo trạng thái; trạng thái UNKNOWN khi phục hồi + một `expires_at` bất biến; bộ kiểm tham số theo chế độ R27w/R27s; mốc ngày lưu DB / dựng lại / UNKNOWN chặn tăng rủi ro; reduce P1 huỷ mọi lớp chờ; câu chữ khoá ngày; chỉ số B9; kiểm chế độ tài khoản; sổ xô ghi phí/funding theo sự kiện | §2.5, 3.1, 5.2, 5.6, 6.1, 6.5, 6A, 8.4, 9.7, 10–12 |
+| C13 | **Hai chế độ vận hành**: Kiểm soát (mọi thứ ở trên: SL bắt buộc, TP bắt buộc, WCL ≤ ngân sách) và **Nonstop** (DCA "gối lệnh", SL/TP tuỳ chọn, khi thanh lý tới gần chỉ cảnh báo, không tự giảm/đóng); chốt chặn trước khi duyệt N1–N4 + xác nhận rủi ro; xô Nonstop riêng; phạm vi từng bất biến; pha PN | mới (§6B); bổ sung 4.12, 8.2(3) |
 
@@ -40,2 +41,3 @@
 3. Mọi giới hạn lấy từ **hồ sơ đang hiệu lực**; muốn to hơn thì đổi hồ sơ (lệnh riêng, có xác nhận, có thời gian chờ), không vượt trần theo từng plan.
+4. Có hai chế độ vận hành: **Kiểm soát** (mặc định, toàn bộ tài liệu trừ §6B) và **Nonstop** (§6B, pha PN). Nguyên tắc 1–3 áp cho cả hai; các bất biến về SL/ngân sách lỗ chỉ áp cho Kiểm soát, phạm vi ghi ở §6B.5.
 
@@ -287,3 +289,3 @@
 
-1. **Một thang mỗi (symbol, holdSide), bất kể chế độ** (giữ SPEC 4.11/4.12.5). Thang đang tồn tại thắng: `propose` bỏ qua cặp đó; `propose --mode wide` trên cặp đang có Scalp (hoặc ngược lại) → R6 FAIL "đang có thang Scalp ETH long; đóng/huỷ trước".
+1. **Một thang mỗi (symbol, holdSide), bất kể chế độ** (Wide, Scalp, và Nonstop §6B.6; giữ SPEC 4.11/4.12.5). Thang đang tồn tại thắng: `propose` bỏ qua cặp đó; `propose --mode wide` trên cặp đang có Scalp (hoặc ngược lại) → R6 FAIL "đang có thang Scalp ETH long; đóng/huỷ trước".
 2. **Số thang**: Wide ≤ `max_ladders` của bậc; Scalp ≤ 1 cùng lúc (câu hỏi C28) và luôn bị R28 chặn thêm; tổng ≤ 4 (2 symbol × 2 chiều). Ví dụ Cân bằng có xô: khi Scalp đang mở, Wide còn tối đa 3.
@@ -371,3 +373,3 @@
 - `content_hash` = SHA-256(`canonical_json(hash_content)`); DB lưu đủ 64 hex, hiển thị 6 hex đầu.
-  - `hash_content` = **mọi trường** của phiên bản trừ `status`, `content_hash`, `edit_log[].text` (lời chat thô) và thời điểm đo của checks; tức gồm `schema, root_id, version, version_id, parent, kind, env, created_at, expires_at, profile{version, params_hash}, mode, symbol, side, anchor, frozen, params, layers, derived, checks{id,status,value,limit}, light, override_reason` và, với `kind ∈ {reduce, entry_adjust}`, **toàn bộ** khối `reduce`/`entry_adjust` (§5.6: leg, close_qty, qty_source input + resolved, exec_mode, sl_mode, entry_actions, preconditions, tolerances, expected_after, steps, client_oids).
+  - `hash_content` = **mọi trường** của phiên bản trừ `status`, `content_hash`, `edit_log[].text` (lời chat thô) và thời điểm đo của checks; tức gồm `schema, root_id, version, version_id, parent, kind, env, created_at, expires_at, profile{version, params_hash}, regime, mode, symbol, side, anchor, frozen, params, layers, derived, checks{id,status,value,limit}, light, override_reason` với `regime: nonstop` cả khối `nonstop` (N1–N4: `liq_all_fill`, `multiple_all_fill_x`, `ack_code`, `sl_present`, `tp_present`), và, với `kind ∈ {reduce, entry_adjust}`, **toàn bộ** khối `reduce`/`entry_adjust` (§5.6: leg, close_qty, qty_source input + resolved, exec_mode, sl_mode, entry_actions, preconditions, tolerances, expected_after, steps, client_oids).
   - `canonical_json`: UTF-8; khoá sắp xếp theo thứ tự byte; không khoảng trắng (`,` và `:`); giá/size/USDT là **chuỗi Decimal** định dạng cố định theo `pricePlace`/`volumePlace` của symbol (vd `"2385.62"`, `"0.64"`), USDT 2 chữ số, tỉ lệ % 4 chữ số (`"0.3000"`); thời gian = số nguyên epoch ms UTC; boolean/null theo JSON; mảng giữ thứ tự (lớp theo `idx` tăng dần); **cấm float JSON** (gặp float → lỗi).
@@ -412,3 +414,4 @@
 profile: {version: 3, tier: can_bang, params_hash: 4be1…}
-mode: wide
+regime: kiem_soat  # kiem_soat | nonstop (§6B); thiếu = kiem_soat
+mode: wide        # kiem_soat: wide | scalp; nonstop: dca
 symbol: ETHUSDT
@@ -503,3 +506,5 @@
 
-- **(I1) Luôn có SL trên sàn**: mọi leg có vị thế có đúng 1 `pos_loss` (mark price). Không bao giờ huỷ-rồi-đặt; không có khoảng hở khi thay.
+Phạm vi: I1 và I2 là bất biến của chế độ **Kiểm soát**. Leg Nonstop: §6B.5 (không SL → không áp; có SL đã duyệt → I1n).
+
+- **(I1) Luôn có SL trên sàn**: mọi leg Kiểm soát có vị thế có đúng 1 `pos_loss` (mark price). Không bao giờ huỷ-rồi-đặt; không có khoảng hở khi thay.
 - **(I2) Lỗ xấu nhất ≤ ngân sách**: sau sửa, `WCL ≤ L_run` và R9/R10/R14/R15/R16 (toàn tài khoản) PASS.
@@ -546,3 +551,3 @@
 - Thất bại: modify/đặt mới bị từ chối → SL cũ vẫn còn (không hở). `SL_TIGHTEN` thất bại → huỷ toàn bộ phiên bản trước khi làm bước rủi ro nào, báo. `SL_LOOSEN` thất bại → giữ SL chặt hơn (an toàn), phiên bản `applied_partial`. Sau bất kỳ lỗi nào, watcher đối soát: SL trên sàn phải = `sl_price` của **phiên bản đang chạy cuối cùng đã áp đủ**; lệch → sửa về giá đó (chỉ gần hơn hoặc bằng, không bao giờ xa hơn giá đã xác nhận).
-- Phát hiện leg có vị thế mà không có SL > 1 vòng → KHẨN + `on_sl_failure` (SPEC Q4).
+- Phát hiện leg `sl_required` (Kiểm soát) hoặc leg Nonstop có SL đã duyệt mà không có SL > 1 vòng → KHẨN + `on_sl_failure` (SPEC Q4; Nonstop: chỉ KHẨN + đặt lại SL đã duyệt, không `close_leg` – §6B.5). Leg Nonstop không có SL: không làm gì.
 - Bị ngắt giữa chừng (crash, mất mạng) → phục hồi theo §6.5.
@@ -559,3 +564,3 @@
   1. Bước `cancel`/`modify` giảm rủi ro (huỷ entry, SL_TIGHTEN): **hoàn tất tiến** (gửi lại được, ≤ 2 lần, truy vấn trước).
-  2. Bước `place` giảm rủi ro (đóng vị thế, đặt TP, đặt `pos_loss` của execute): `FOUND` → tiếp tục; `UNKNOWN` → `PENDING_RECONCILE` (6A.8), **không gửi lại**; chỉ gửi lại khi `VERIFIED_NOT_RECEIVED` và `now < expires_at` của phiên bản (cùng clientOid). Ngoại lệ duy nhất: watcher đặt `pos_loss` khi đọc `orders-plan-pending` thấy leg có vị thế mà không có SL (I1) – thiếu SL nguy hiểm hơn thừa SL; nếu sau đó thấy 2 `pos_loss` (tuỳ kết quả D20) thì huỷ bản thừa sau khi bản còn lại đã xác nhận.
+  2. Bước `place` giảm rủi ro (đóng vị thế, đặt TP, đặt `pos_loss` của execute): `FOUND` → tiếp tục; `UNKNOWN` → `PENDING_RECONCILE` (6A.8), **không gửi lại**; chỉ gửi lại khi `VERIFIED_NOT_RECEIVED` và `now < expires_at` của phiên bản (cùng clientOid). Ngoại lệ duy nhất: watcher đặt `pos_loss` khi đọc `orders-plan-pending` thấy leg **cần SL** (Kiểm soát, hoặc Nonstop có SL đã duyệt) có vị thế mà không có SL (I1/I1n) – thiếu SL nguy hiểm hơn thừa SL; nếu sau đó thấy 2 `pos_loss` (tuỳ kết quả D20) thì huỷ bản thừa sau khi bản còn lại đã xác nhận.
   3. Bước tăng rủi ro chưa `confirmed`: **không bao giờ gửi lại**. Nếu thực tế đã tồn tại trên sàn: kiểm I2 với SL thật – WCL ≤ L_run → giữ và ghi nhận; ngược lại huỷ entry đó (nếu chưa khớp) hoặc SL_TIGHTEN về mức ngân sách (nếu đã khớp).
@@ -572,2 +577,4 @@
 
+> Phạm vi: §6A viết cho chế độ **Kiểm soát**. Leg Nonstop: không có bản dựng sẵn; reduce do anh tự gọi dùng cùng executor và cùng cổng, số SL kỳ vọng theo §6B.5.
+
 > Ý của chủ: "Nhiều khi đóng 1 phần vị thế không phải vì có lãi, mà vì muốn giảm volume vị thế để giá thanh lý xa hơn." `reduce` là thao tác **chỉ đóng** (close-only), làm được bất kể lãi/lỗ, không bao giờ mở thêm vị thế.
@@ -646,3 +653,3 @@
 
-**Điều kiện kết thúc về SL**: nếu còn vị thế (`Q_after > 0`) → đúng 1 `pos_loss` cấp vị thế, trigger = SL của phiên bản (±1 tick). Nếu `Q_after = 0` → điều kiện "1 SL" **không áp dụng**: dọn mọi lệnh còn sót của leg, không đặt SL/TP mới.
+**Điều kiện kết thúc về SL**: (leg Nonstop không có SL: 0 SL, §6B.5) nếu còn vị thế (`Q_after > 0`) → đúng 1 `pos_loss` cấp vị thế, trigger = SL của phiên bản (±1 tick). Nếu `Q_after = 0` → điều kiện "1 SL" **không áp dụng**: dọn mọi lệnh còn sót của leg, không đặt SL/TP mới.
 
@@ -723,3 +730,3 @@
 | PROPOSED → APPROVED | `REDUCE_SL_MODE = position_persist` (trừ entry_adjust); phiên bản mới nhất; `now < expires_at`; lệch mark ≤ 0.3%; hash canonical khớp (§5.4); không có op khác trên leg; leg không DRIFT / PENDING_RECONCILE | – | ghi `op_journal` (op_id, version_id, các bước dự kiến + clientOid) **trước** | – | từ chối, giữ PROPOSED |
-| APPROVED → RECONCILING | khoá trạng thái leg; watcher tạm dừng re-price TP leg (vẫn giữ SL) | REST `account` (`productType=USDT-FUTURES`, `marginCoin=USDT`), `single-position`, `orders-pending` (symbol), `orders-plan-pending` (profit_loss), ticker | **chế độ tài khoản**: `posMode = hedge_mode`, `marginMode = crossed`, productType `USDT-FUTURES`, leg có vị thế đúng `holdSide` (long/short) và `marginMode = crossed` ở cấp vị thế; **trạng thái**: size vị thế = snapshot; tập lệnh chờ = snapshot; tập TP = snapshot; đúng 1 `pos_loss` trigger = snapshot; trạng thái leg (ACTIVE/TP1_DONE/PROTECT_ONLY) = snapshot; mark trong 0.3%; E trong 1%; `close_qty` vẫn hợp lệ; `now < expires_at` | 10 s | bất kỳ lệch nào → `ABORTED` (chưa ghi gì lên sàn), thông báo giá trị thật, gợi ý phiên bản mới |
+| APPROVED → RECONCILING | khoá trạng thái leg; watcher tạm dừng re-price TP leg (vẫn giữ SL) | REST `account` (`productType=USDT-FUTURES`, `marginCoin=USDT`), `single-position`, `orders-pending` (symbol), `orders-plan-pending` (profit_loss), ticker | **chế độ tài khoản**: `posMode = hedge_mode`, `marginMode = crossed`, productType `USDT-FUTURES`, leg có vị thế đúng `holdSide` (long/short) và `marginMode = crossed` ở cấp vị thế; **trạng thái**: size vị thế = snapshot; tập lệnh chờ = snapshot; tập TP = snapshot; số `pos_loss` = số kỳ vọng (Kiểm soát / Nonstop có SL: đúng 1, trigger = snapshot; Nonstop không SL: 0, §6B.5); trạng thái leg (ACTIVE/TP1_DONE/PROTECT_ONLY) = snapshot; mark trong 0.3%; E trong 1%; `close_qty` vẫn hợp lệ; `now < expires_at` | 10 s | bất kỳ lệch nào → `ABORTED` (chưa ghi gì lên sàn), thông báo giá trị thật, gợi ý phiên bản mới |
 | → CANCELLING_ENTRIES | RECONCILING đạt | reduce: `cancel-order` **mọi** lớp chờ của leg + `cancel-plan-order` mọi TP (`profit_plan`) của leg, theo clientOid; entry_adjust: chỉ các lớp đã chọn, TP giữ nguyên | `order/detail` = `cancelled`; TP không còn trong `orders-plan-pending`; size vị thế không đổi | 10 s/lệnh; huỷ là idempotent → gửi lại tối đa 2 lần (truy vấn trước) | lớp đã `filled`/khớp một phần → `FAILED_SAFE` (không đóng; giữ các huỷ đã làm; đặt lại TP theo bảng 6A.5 cho size thật; đề xuất phiên bản mới); lỗi khác → `FAILED_SAFE` (cũng đặt lại TP) |
@@ -822,3 +953,4 @@
 | Lỗi đặt lệnh/đối soát/DRIFT | CAO | mô tả + việc công cụ đã làm |
-| Leg không có SL, WS chết, `fail_execute` | KHẨN | + hành động tự động đã chạy |
+| Leg cần SL mà không có SL, WS chết, `fail_execute` | KHẨN | + hành động tự động đã chạy |
+| Nonstop `ns_liq` / `ns_multiple` (§6B.4) | CAO / KHẨN, **không tắt được** | "NONSTOP ETH long (không SL): thanh lý cách mark {d}% (khớp nốt lớp chờ: {d_all}%), {x}× vốn. Công cụ không tự giảm/đóng. …" |
 
@@ -863,3 +995,3 @@
 
-Tự động khi khoá ngày/tuần/DD: huỷ entry Scalp chưa khớp; lệnh chờ Wide giữ nguyên. Lỗ chốt bởi `reduce` đã nằm trong E theo mark nên khoá ngày/tuần/DD chỉ thêm phí + trượt; ngân sách thang/xô thì tính đủ (§6A.6).
+Tự động khi khoá ngày/tuần/DD: huỷ entry Scalp chưa khớp; lệnh chờ Wide giữ nguyên. Nonstop (§6B.5): khoá chặn mở thang Nonstop mới và thêm lớp; lệnh chờ Nonstop **không** bị huỷ và vẫn có thể khớp; không có hành động đóng nào. Lỗ chốt bởi `reduce` đã nằm trong E theo mark nên khoá ngày/tuần/DD chỉ thêm phí + trượt; ngân sách thang/xô thì tính đủ (§6A.6).
 
@@ -876,3 +1008,3 @@
 ### 9.3 N3 – `kill` xoá SL [→ SPEC 2.2 dòng `kill`, 9.5, 2.4 bước 4]
-- `kill` (mặc định) = **chế độ bảo vệ**: tạo `state/KILL`, huỷ mọi **entry** và **TP** của công cụ (lọc tiền tố), **giữ** `pos_loss`/BE, watcher **tiếp tục chạy** ở chế độ `PROTECT_ONLY` (chỉ đảm bảo SL, đối soát, cảnh báo; không đặt entry/TP). Xác nhận đầu ra: "mỗi leg còn vị thế có đúng 1 SL".
+- `kill` (mặc định) = **chế độ bảo vệ**: tạo `state/KILL`, huỷ mọi **entry** và **TP** của công cụ (lọc tiền tố), **giữ** `pos_loss`/BE, watcher **tiếp tục chạy** ở chế độ `PROTECT_ONLY` (chỉ đảm bảo SL, đối soát, cảnh báo; không đặt entry/TP). Xác nhận đầu ra: "mỗi leg Kiểm soát còn vị thế có đúng 1 SL"; leg Nonstop không SL được liệt kê riêng: "KHÔNG có SL" (§6B.5).
 - `kill --close-positions --confirm-close` = `close-positions` theo từng (symbol, holdSide) của công cụ → đợi size = 0 (xác nhận REST) → mới huỷ SL/TP còn lại. Thất bại đóng → giữ SL, KHẨN.
@@ -883,3 +1015,3 @@
 - Không còn lệnh close limit nào treo trong thiết kế mặc định (trừ `scalp scaleout` – xem dưới). Fallback chỉ dùng nếu D18 FAIL: `limit_partial` với `Σ size TP ≤ Q − 1 lot`.
-- Watcher PHẢI xử lý `orders-algo status=fail_execute`: với `pos_loss`/BE → `close-positions` (holdSide) ngay + KHẨN; với TP → đặt lại 1 lần, vẫn lỗi → CAO.
+- Watcher PHẢI xử lý `orders-algo status=fail_execute`: với `pos_loss`/BE của leg Kiểm soát → `close-positions` (holdSide) ngay + KHẨN (leg Nonstop có SL: chỉ KHẨN, §6B.5); với TP → đặt lại 1 lần, vẫn lỗi → CAO.
 - Scalp TP_a/TP_b: dùng cùng `plan_market` (phí taker 0.06% làm lãi TP_a mỏng: TP 0.15% − 0.02% − 0.06% = 0.07% notional; đã tính trong §3.4). `scalp scaleout` (limit post-only) phải giữ `Σ close limit ≤ Q − 1 lot` và chạy qua executor reduce (maker, P1b, §6A.0) – tắt khi reduce tắt.
@@ -916,3 +1048,3 @@
 | Q-12 | §8.4 | R18–R20 |
-| Q-13 | Cổng **P1** = U1–U2, U4–U16, U19a, U20–U25, U28–U38, U40, U42–U48, U50, U52, U53, U55–U57, phần Wide của U44/U51, D1–D14, D16–D23, D25, D30, D31. **Bật `reduce` market** (không chặn go-live P1) = D26 + D28 (chỉ `position_persist`). **Tự gửi lại lệnh `place` sau crash** (tuỳ chọn; không có thì không bao giờ tự gửi lại) = D32. **Dựng lại mốc ngày** (tuỳ chọn; không có thì đi nhánh UNKNOWN) = D33. **P1b** = U3', U19b, U26–U27, U41 (maker), U54, U58, phần Scalp của U44/U51, D15, D24, D27. **P2** = U17–U18, U39 (+ cổng 6.8). **Hiển thị số kỳ vọng** của một bậc = B9 (Mạo hiểm + B6, xô + B8). Đã rút: U49, D29. Demo Wide ≥ 20 thang, Scalp ≥ 10 trước khi bật xô | 10, 11 |
+| Q-13 | Cổng **P1** = U1–U2, U4–U16, U19a, U20–U25, U28–U38, U40, U42–U48, U50, U52, U53, U55–U57, phần Wide của U44/U51, D1–D14, D16–D23, D25, D30, D31. **Bật `reduce` market** (không chặn go-live P1) = D26 + D28 (chỉ `position_persist`). **Tự gửi lại lệnh `place` sau crash** (tuỳ chọn; không có thì không bao giờ tự gửi lại) = D32. **Dựng lại mốc ngày** (tuỳ chọn; không có thì đi nhánh UNKNOWN) = D33. **P1b** = U3', U19b, U26–U27, U41 (maker), U54, U58, phần Scalp của U44/U51, D15, D24, D27. **P2** = U17–U18, U39 (+ cổng 6.8). **Hiển thị số kỳ vọng** của một bậc = B9 (Mạo hiểm + B6, xô + B8). **PN (Nonstop)** = cổng Demo P1 đạt + U58 + U59–U66 + D34–D37 + C30–C40 đã trả lời (§6B.7). Đã rút: U49, D29. Demo Wide ≥ 20 thang, Scalp ≥ 10 trước khi bật xô | 10, 11 |
 | Q-14 | Sửa 1.5 ("micro-grid không stop, không trần" ngoài phạm vi; Scalp có trần thì trong phạm vi). **B4 thành cổng**: bật xô mạo hiểm live chỉ sau B8 + chủ ký duyệt | 1.5, 10.5 |
@@ -932,2 +1064,3 @@
 | `bucket status` / `bucket refill --confirm` | Sổ xô §3 | Không |
+| (PN) `profile set --nonstop-bucket N --confirm` + câu xác nhận; `propose --regime nonstop --symbol S --side L/S`; `execute <ref> --confirm --hash H --ack NS-…`; `bucket refill --nonstop --confirm`; `alerts list` (`alerts mute` từ chối `ns_*`) | §6B | Có (execute) |
 | `propose [--symbol S --side L/S] [--mode wide|scalp] [--max 2]` | Sinh plan v1 (§4). `preview` cũ = `propose --symbol --side` | Không |
@@ -977,2 +1110,13 @@
 # REDUCE_SL_MODE KHÔNG có trong cấu hình: là hằng trong mã (§10.3)
+nonstop:   # PN, §6B – mọi giá trị dưới đây là ĐỀ XUẤT chờ C30–C40, chưa chốt
+  enabled_tiers: [mao_hiem]          # C30
+  bucket_share_pct: 10               # C31; Scalp + Nonstop ≤ HARD_RISK_BUCKET_MAX 20
+  max_ladders: 1                     # C31
+  min_liq_all_fill_pct: 3            # C32 (đề xuất)
+  max_multiple_x: 15                 # C33; ≤ R10a cứng 15× cùng chiều
+  alert_liq_pct: [10, 5, 3]          # C34; + KHẨN dưới min_liq_all_fill_pct
+  alert_multiple_x: 10               # C34; nhắc lại mỗi +5×
+  alert_repeat_min: {cao: 30, khan: 5}
+  alert_hysteresis: {liq_pts: 1, multiple_x: 1}
+  dca_bounds: {layers_max: 12, spacing_min_pct: 0.10, mult: [0.80, 1.00], first_x_max: 10, tp_min_pct: 0.10}   # C40
 day_mark: {capture_tol_s: 5, reconstruct_enabled: false, reconstruct_retry_min: 15}   # bật dựng lại chỉ sau D33 (§8.4)
@@ -984,2 +1128,4 @@
 
+Nonstop (§6B, PN) **không thêm và không nới** hằng cứng nào: R9a 20×, R10a 15×, `HARD_LEVERAGE_MAX_PER_SYMBOL = 50`, `HARD_RISK_BUCKET_MAX = 20%` (Scalp + Nonstop cộng chung) áp nguyên cho leg Nonstop (C33). Các ngưỡng `nonstop.*` ở §10.2 là cấu hình, chỉ được siết dưới các hằng này.
+
 ---
@@ -1004,5 +1150,5 @@
 | U28 | WCL running edit §6.3: (a) dồn lớp → SL tự dời 2180.67; (b) huỷ lớp 5 → SL xa tối đa 2129.66, yêu cầu 2150.00 OK, 2120.00 FAIL; (c) vượt trần notional FAIL; property test 10.000 bộ: sau mọi sửa được chấp nhận `WCL ≤ L_run` |
-| U29 | Thứ tự áp dụng §6.4 (sàn giả lập): SL_TIGHTEN trước PLACE_ENTRY; SL_LOOSEN sau cùng; lệnh định huỷ đã khớp → tự siết SL + `applied_partial`; modify SL lỗi → không bước rủi ro nào chạy; **không bao giờ có thời điểm leg có vị thế mà 0 pos_loss** (kiểm trên mọi trạng thái trung gian) |
+| U29 | (Kiểm soát) Thứ tự áp dụng §6.4 (sàn giả lập): SL_TIGHTEN trước PLACE_ENTRY; SL_LOOSEN sau cùng; lệnh định huỷ đã khớp → tự siết SL + `applied_partial`; modify SL lỗi → không bước rủi ro nào chạy; **không bao giờ có thời điểm leg có vị thế mà 0 pos_loss** (kiểm trên mọi trạng thái trung gian) |
 | U30 | Không tự dời SL xa: mọi đường code dời SL xa đều xuất phát từ phiên bản đã duyệt có `--sl` rõ ràng |
-| U31 | `kill` → mỗi leg còn vị thế đúng 1 pos_loss, watcher `PROTECT_ONLY`; `kill --close-positions` huỷ SL chỉ sau size = 0 |
+| U31 | `kill` → mỗi leg **Kiểm soát** còn vị thế đúng 1 pos_loss (leg Nonstop không SL: liệt kê "KHÔNG có SL", không tạo SL), watcher `PROTECT_ONLY`; `kill --close-positions` huỷ SL chỉ sau size = 0 |
 | U32 | `plan_market`: không có close limit treo; `fail_execute` của pos_loss → close-positions + KHẨN |
@@ -1034,2 +1180,10 @@
 | U58 | **(P1b)** Sổ xô theo sự kiện §3.1: fill mở L1 → `open_fee` ghi ngay, `used` tăng ngay; fill đóng (TP/SL/reduce) → `close_pnl` + `close_fee`; funding tại mốc → `funding` (symbol chỉ Scalp: toàn bộ; symbol Wide + Scalp: chia theo `Q_scalp·mark·rate`); khởi động lại → không ghi trùng (khoá `tradeId`/`billId`); `worst_loss` của thang đang mở không tính lại phí mở/realized đã ghi; R28 dùng giá trị mới ngay |
+| U59 | (PN) Tách chế độ: `regime` trong schema + hash; plan cũ không có `regime` → `kiem_soat`, mọi test Kiểm soát cũ không đổi kết quả; R27n: Nonstop không SL/không TP PASS; TP 0.10% PASS + in lãi ròng 0.02%; TP 0.09% FAIL; `d` 0.09% FAIL; 13 lớp FAIL; SL nằm sau giá liq khớp đủ → FAIL "SL vô dụng"; trước PN → từ chối |
+| U60 | (PN) N2 khớp đủ (mô hình §6A.2): tái tạo bảng 6B.8 (±0.01): ~30× 2334.19 / 2.30%; ~60× 2359.36 / 0.21%; ~95× liq trên lớp cuối → FAIL "không khớp đủ được trước thanh lý"; có leg khác cùng chiều + lớp chờ của nó → liq gần hơn; leg ngược chiều chỉ tính MM; ngưỡng đọc từ cấu hình |
+| U61 | (PN) N1/N3 + sổ Nonstop: R10a/R9a tính mọi leg khi khớp đủ; R10w không áp; `max_multiple_x`; tổng xô Scalp + Nonstop > 20% → từ chối; sổ ghi phí mở/đóng/funding theo sự kiện (như U58); khoá xô ở 50% → chặn mở mới, **0 lệnh huỷ/đóng**; preview in "có thể mất toàn bộ tài khoản" |
+| U62 | (PN) Xác nhận rủi ro: bật Nonstop cần đúng câu, là tăng rủi ro (pending 24 h, từ chối khi khoá, 1 lần/7 ngày, bậc theo C30); mỗi `execute`/`ladder apply` tăng rủi ro cần `--ack` khớp hash + liq của đúng phiên bản; mã của phiên bản cũ → R29 FAIL; preview có "KHÔNG CÓ SL", liq khớp đủ (giá + %), bội số × vốn |
+| U63 | (PN) Cảnh báo 6B.4: vào mức → báo ngay; leo mức → báo ngay; ở yên → nhắc 30 / 5 phút; hồi + trễ 1 điểm / 1× mới thoát; tin "đã hồi"; `alerts mute` / giờ yên lặng bị từ chối với `ns_*`; KHẨN qua chat + email; **watcher gửi 0 lệnh** (mock) và **không** tạo phiên bản reduce dựng sẵn |
+| U64 | (PN) Phạm vi SL §6B.5: leg Nonstop không SL → SPEC 8.2(3) không đặt `pos_loss`, không `close_leg`, `fail_execute`/Q-7 không áp; Nonstop có SL bị mất → đặt lại đúng giá + KHẨN, không `close_leg`; reduce RECONCILING kỳ vọng 0 SL (thấy SL lạ → ABORTED); §6.5 ngoại lệ đặt `pos_loss` không áp cho leg không SL; R14 không cộng leg không SL và preview Kiểm soát in câu cảnh báo khi có Nonstop mở |
+| U65 | (PN) Cùng tồn tại 6B.6: Nonstop + Kiểm soát cùng (symbol, holdSide) → R6 FAIL; khác chiều → được; tổng thang ≤ 4, Nonstop ≤ 1; leverage symbol dùng chung; khoá ngày/tuần/DD/UNKNOWN chặn `execute` Nonstop và thêm lớp, lệnh chờ Nonstop không bị huỷ |
+| U66 | (PN) Thanh lý: bill `burst_long_loss_query` / `force_close_long` → KHẨN, tắt Nonstop (bật lại theo 6B.1), tính 1 SL trong chuỗi stop, sổ Nonstop ghi lỗ |
 
@@ -1055,2 +1209,6 @@
 | D33 | **Dựng lại mốc ngày** (§8.4 nhánh 2): watcher lưu mốc 07:00 thật; sau đó tắt watcher, có fill/funding/chuyển tiền nội bộ trong ngày, rồi dựng lại từ `account/bill`, `order/fills`, `position/history-position`, `market/history-mark-candles`; đồng thời ghi bill funding có/không có holdSide | Sai lệch so với mốc thật ≤ 0.05 USDT trong 5 ngày thử → được bật `reconstruct_enabled`; ghi cách chia funding Wide/Scalp có khớp bill không (U58). FAIL → giữ tắt, luôn đi nhánh UNKNOWN |
+| D34 | (PN) Thang Nonstop nhỏ không SL trên Demo (vốn Demo nhỏ để bội số thật): khớp vài lớp | Watcher không đặt SL, không đóng/huỷ gì; TP mỏng (nếu có) đặt lại sau mỗi fill; cảnh báo `ns_*` đúng mức và đúng nhịp |
+| D35 | (PN) So liq ước tính (§6A.2, 6B.8) với `liquidationPrice` của `single-position` khi thang Nonstop khớp nhiều lớp | Sai lệch ghi lại; nếu ước tính **xa** hơn giá sàn > 0.1% giá → hiệu chỉnh `mmr_floor` trước khi bật PN |
+| D36 | (PN) Khoá ngày giả lập khi có lệnh chờ Nonstop | Không gửi lệnh mở mới; lệnh chờ đã treo vẫn khớp được; không có lệnh huỷ/đóng tự động |
+| D37 | (PN) `kill` khi có leg Nonstop không SL và leg Kiểm soát | Entry + TP huỷ; leg Kiểm soát giữ SL; leg Nonstop còn vị thế không SL và được in rõ |
````
