# SPEC v2 – PHẦN BỔ SUNG (BẢN NHÁP) – DCA-ladder bán tự động Bitget USDT-M

| | |
|---|---|
| Trạng thái | **NHÁP**, chờ chủ duyệt. Tài liệu này **bổ sung/thay thế từng mục** của `SPEC.md` v1.0; mục nào không nhắc tới thì giữ nguyên SPEC.md |
| Ngày | 2026-10-20 (UTC+7) |
| Chủ sở hữu | Trung Hieu |
| Đầu vào | `SPEC.md` v1.0, `REVIEW_2026-10-20.md` (6 nghiêm trọng N1–N6, 14 quan trọng Q-1…Q-14, 14 nhỏ m1–m14), quyết định của chủ ngày 2026-10-20 |
| Số liệu ví dụ | E = **524.7 USDT**, maker 0.02%, taker 0.06%, ETH tick 0.01/lot 0.01, BTC tick 0.1/lot 0.0001, anchor ETH 2400.00, BTC 81647.2, MMR sàn ETH 0.5% / BTC 0.4%. Mọi con số tính lại bằng `Decimal` (script `/workspace/scratch/spec_v2/calc*.py`) |

> Quy ước giữ như SPEC.md ("PHẢI/NÊN/CÓ THỂ"). Ký hiệu **[→ SPEC x.y]** = mục của SPEC.md bị thay thế/sửa. Mọi giờ hiển thị theo UTC+7.

---

## 0. Tóm tắt thay đổi so với SPEC.md

| # | Thay đổi | Thay thế/sửa |
|---|---|---|
| C1 | Bỏ `--variant safe/default/aggressive`. Thay bằng **hồ sơ khẩu vị** (3 bậc: Thận trọng / Cân bằng / Mạo hiểm có kiểm soát), đặt một lần qua 6 câu hỏi, có phiên bản | 4.2, A.2 `variant`, Q1, Q3 |
| C2 | Công cụ **tự đề xuất** plan (chiều, anchor, lớp) từ hồ sơ + đèn thị trường; người dùng **sửa** (chat → `plan edit`, hoặc file) rồi **duyệt một phiên bản cụ thể** | 2.1–2.4 |
| C3 | Plan có **phiên bản bất biến** (`<root>.vN` + hash); mỗi lần sửa = tính lại toàn bộ + chạy lại mọi kiểm tra + diff; phiên bản cũ mất hiệu lực | 2.3 |
| C4 | Thang đang chạy **được sửa tự do trong trần hồ sơ**, qua cùng luồng preview → diff → duyệt. Hai bất biến cứng (chế độ **Kiểm soát**; Nonstop: §6B.5): luôn có SL trên sàn; lỗ xấu nhất sau sửa ≤ ngân sách lỗ/thang và mọi kiểm tra tài khoản PASS | 1.5 dòng "không đổi tham số tại chỗ", 5.3 |
| C5 | **Chia vốn**: phần an toàn (Wide) + "xô mạo hiểm" ≤ 20% cho Scalp, ngân sách lỗ khoá riêng, không vay phần an toàn | 4.12.2, 4.12.5 |
| C6 | Đầu ra thị trường dạng **đèn xanh/vàng/đỏ + 1 câu**; chỉ đề xuất chiều xanh; đỏ cần gõ lý do (trước cổng 6.8) / bị chặn (sau cổng) | 2.3 dòng AVOID, R21 |
| C7 | Vận hành: bản tin sáng 07:05, thông báo sự kiện, **ranh giới ngày 07:00 UTC+7** cho mọi bộ đếm, khoá tự động | R18–R20, 4.12.5 |
| C8 | Sửa N1–N6: bỏ `aggressive`; định nghĩa lại R14 & giới hạn số thang; `kill` giữ SL; TP dạng trigger không chiếm vị thế; execute dùng E đóng băng + "bất biến được duyệt"; sửa ví dụ Scalp | xem §9 |
| C9 | Kiểm tra mới R26–R30 (R27 tách R27w/R27s); CLI mới; test U20–U74, D18–D39 (U49, D29 đã rút), B6–B9 | 5.2, 2.2, 10 |
| C10 | **`reduce`**: giảm vị thế chủ động (chỉ đóng) để đẩy giá thanh lý xa, cả Wide và Scalp; preview liq một leg + xấu nhất toàn TK (có lớp chờ); **P1 chỉ market và luôn huỷ mọi lớp chờ của leg trước khi đóng**, vòng đời là máy trạng thái có phục hồi (kết quả không xác định → PENDING_RECONCILE, không tự gửi lại); **tắt cứng tới khi D26 chứng minh SL cấp vị thế vẫn bao phần còn lại** (chỉ `position_persist`; `preplace_guard` ngoài phạm vi); mọi đường đóng một phần chủ động đi qua cùng executor và cổng, `ladder close` chỉ 100%; nhánh chỉ-huỷ `entry_adjust` không gửi lệnh đóng; dùng được cả khi đang khoá; watcher cảnh báo thanh lý theo bậc và dựng sẵn đề xuất (không tự chạy). Maker → P1b, tự tìm khối lượng → P2 | mới (§6A); bổ sung 4.8, 4.12.3c |
| C11 | Sửa theo review lần 2: schema + băm canonical (§5.4/§5.6), ràng buộc Wide/Scalp (§3.5), nhật ký bước & phục hồi `applied_partial` (§6.5), khoá ngày định nghĩa duy nhất (§8.4), kỳ vọng backtest trung thực (§2.6), cổng pha (§9.7) | 5.1, R8–R20, 1.3, Phụ lục C, 10 |
| C12 | Sửa theo review lần 3 (không thêm tính năng): bỏ `preplace_guard` khỏi P1; chặn đường đóng một phần vòng qua cổng; TP sau reduce theo trạng thái; trạng thái UNKNOWN khi phục hồi + một `expires_at` bất biến; bộ kiểm tham số theo chế độ R27w/R27s; mốc ngày lưu DB / dựng lại / UNKNOWN chặn tăng rủi ro; reduce P1 huỷ mọi lớp chờ; câu chữ khoá ngày; chỉ số B9; kiểm chế độ tài khoản; sổ xô ghi phí/funding theo sự kiện | §2.5, 3.1, 5.2, 5.6, 6.1, 6.5, 6A, 8.4, 9.7, 10–12 |
| C13 | **Hai chế độ vận hành**: Kiểm soát (mọi thứ ở trên: SL bắt buộc, TP bắt buộc, WCL ≤ ngân sách) và **Nonstop** (DCA "gối lệnh", SL/TP tuỳ chọn, khi thanh lý tới gần chỉ cảnh báo, không tự giảm/đóng); chốt chặn trước khi duyệt N1–N4 + xác nhận rủi ro; xô Nonstop riêng; phạm vi từng bất biến; pha PN | mới (§6B); bổ sung 4.12, 8.2(3) |

### 0.1 Trạng thái các điểm review (2026-10-20, vòng 5)

Quy ước: "đã sửa ở mức đặc tả, chờ kiểm thử" = có điều khoản và test được viết trong tài liệu này, **chưa có mã, chưa chạy test nào**. Không điểm nào dưới đây được coi là đã kiểm chứng trên sàn.

| Điểm | Điều khoản | Test | Trạng thái |
|---|---|---|---|
| Bỏ `preplace_guard` khỏi P1 | §6A.0, §10.3 | U48 | đã sửa ở mức đặc tả, chờ kiểm thử |
| Bịt đường vòng `ladder close --pct` | §6A.0, §6.1 | U48 | đã sửa ở mức đặc tả, chờ kiểm thử |
| Reduce P1 huỷ mọi lớp chờ (`cancel_all`) | §6A.4, §5.6 | U42 | đã sửa ở mức đặc tả, chờ kiểm thử |
| TP sau reduce theo trạng thái | §6A.5 | U55, U42 | đã sửa ở mức đặc tả, chờ kiểm thử |
| Bộ kiểm tham số tách Wide / Scalp (R27w / R27s) | §2.5 | U25, U54 | đã sửa ở mức đặc tả, chờ kiểm thử |
| Mốc ngày lưu DB / dựng lại / UNKNOWN | §8.4 | U57, D33 | đã sửa ở mức đặc tả, chờ kiểm thử (nhánh dựng lại tắt tới D33) |
| Bỏ ngoại lệ SAFE (số kỳ vọng chỉ từ B9) | §2.6 | U53 | đã sửa ở mức đặc tả, chờ kiểm thử |
| V5-1 Hash vòng tròn với mã xác nhận Nonstop | §5.4, §6B.3 | U67 | đã sửa ở mức đặc tả, chờ kiểm thử |
| V5-2 Vốn Wide bỏ sót xô Nonstop → một sổ phân bổ chung | §3.1, §6B.1 | U68 | đã sửa ở mức đặc tả, chờ kiểm thử |
| V5-3 Trần hồ sơ vs hằng cứng → trần hiệu lực `min(…)` | §3.5 mục 4a, §2.3, §2.4, §6B.2 N1 | U69 | đã sửa ở mức đặc tả, chờ kiểm thử |
| V5-4 Reduce leg Nonstop không SL bị chặn ở CLOSING; U63 mâu thuẫn | §6A.8 (`sl_policy`), §6B.4 | U70, U63 | đã sửa ở mức đặc tả, chờ kiểm thử |
| V5-5 Đóng UNKNOWN + phiên bản mới có thể đóng quá | §6A.8 khoá `UNRESOLVED_CLOSE`, §8.4 | U71, D38 | một phần: hành vi của sàn với lệnh close khi size đã 0 chưa kiểm chứng (D38) |
| V5-6 Phạm vi `expires_at` | §6A.8, §6.5 mục 7 | U72 | đã sửa ở mức đặc tả, chờ kiểm thử |
| V5-7 Khoá chống trùng của sổ + chia funding 3 phần | §3.1 | U58 | một phần: cách chia funding chưa so với bill thật (D33) |
| V5-8 Đóng 100%: lớp chờ, thủ tục thường / khẩn | §6A.10, §6A.0, §9.3 | U73, U74, D39 | đã sửa ở mức đặc tả, chờ kiểm thử |
| V5-9 N2 theo đường khớp, bỏ quy đổi bội số | §6B.2 N2, §6B.8 | U60 | một phần: mô hình liq chưa so với `liquidationPrice` thật (D35); ngưỡng C32 chưa chốt |

---

## 1. Luồng sử dụng mới [→ SPEC 2.1, 2.3, 2.4]

### 1.1 Nguyên tắc

1. **Không bao giờ** có lệnh *mở* vị thế nếu chủ chưa duyệt đúng một phiên bản plan (`version_id` + `hash`). Không có ngoại lệ (P4 "tự mở lại" vẫn ngoài phạm vi).
2. Công cụ đề xuất; người quyết định. Trợ lý chat chỉ là "người phiên dịch" lời nói → lệnh CLI, và PHẢI in lại lệnh đã dịch kèm diff trước khi hỏi duyệt.
3. Mọi giới hạn lấy từ **hồ sơ đang hiệu lực**; muốn to hơn thì đổi hồ sơ (lệnh riêng, có xác nhận, có thời gian chờ), không vượt trần theo từng plan.
4. Có hai chế độ vận hành: **Kiểm soát** (mặc định, toàn bộ tài liệu trừ §6B) và **Nonstop** (§6B, pha PN). Nguyên tắc 1–3 áp cho cả hai; các bất biến về SL/ngân sách lỗ chỉ áp cho Kiểm soát, phạm vi ghi ở §6B.5.

### 1.2 Sơ đồ

```mermaid
sequenceDiagram
    autonumber
    participant A as Anh (chủ)
    participant C as Trợ lý chat
    participant T as Công cụ (CLI)
    participant W as Watcher (VPS)
    participant X as Bitget

    W->>T: 07:05 UTC+7: digest (chỉ GET public + read-only)
    T->>X: GET ticker/candles/account/positions
    T-->>C: digest + đề xuất 7Q2X.v1 (đèn xanh, rủi ro, lãi)
    C-->>A: "Hôm nay nên mở ETH long… Duyệt không?"
    A->>C: "Giảm còn 4 lớp, cách 2%, lỗ tối đa 20 USDT"
    C->>T: plan edit 7Q2X.v1 --layers 4 --spacing 2 --max-loss 20
    T->>T: tính lại SL/size/liq/exposure + chạy R1–R30
    T-->>C: 7Q2X.v2 + diff v1→v2 (v1 = superseded)
    C-->>A: diff + "Duyệt 7Q2X.v2 (hash 9f3a1c)?"
    A->>C: "Duyệt"
    C->>T: execute 7Q2X.v2 --confirm --hash 9f3a1c
    T->>T: kiểm hạn/E/giá theo bất biến được duyệt (§9.5), chạy lại R1–R30
    T->>X: entry post-only (+ preset SL nếu D7 đạt)
    X-->>W: WS orders/positions: fill L1
    W->>X: pos_loss (mark) → xác nhận; TP1/TP2 profit_plan
    W-->>C: "ETH long: khớp lớp 1 @2400.00…"
    A->>C: "Huỷ lớp 4, dời SL xuống 2150"
    C->>T: ladder edit 7Q2X --remove-layer 4 --sl 2150
    T-->>C: 7Q2X.v3 (running edit) + diff + lỗ xấu nhất
    A->>C: "Duyệt"
    C->>T: ladder apply 7Q2X.v3 --confirm --hash …
    T->>X: thứ tự an toàn: huỷ entry → xác nhận → sửa SL (modify)
    W-->>C: TP1 / BE / TP2 / SL / lỗi / khoá ngày
    W-->>C: Cảnh báo thanh lý: cách 9.47% < 10% (bậc) + đề xuất reduce 7Q2X.v5 dựng sẵn
    A->>C: "Giảm 30%, huỷ lớp chờ"
    C->>T: reduce 7Q2X --pct 30
    T-->>C: preview hiện tại/sau (size, liq 1 leg & xấu nhất, realized, WCL, SL, bộ đếm ngày)
    A->>C: "Duyệt"
    C->>T: reduce apply 7Q2X.v5 --confirm --hash …
    T->>X: RECONCILING (hedge_mode/crossed/holdSide) → huỷ mọi lớp chờ + TP → close market → xác minh pos_loss + đặt TP theo trạng thái (§6A.8)
```

### 1.3 Ví dụ chat (trích)

```
Trợ lý: [Bản tin 07:05] Vốn 524.7 USDT. Hôm qua +0.0. Không khoá.
  Hôm nay nên mở ETH long (đèn xanh: "4h đi ngang, biến động bình thường").
  Nếu sai hẳn: mất tối đa 23.4 USDT (~24.4 nếu trượt giá).
  Mỗi lần chốt lời: ~0.27 USDT nếu chỉ khớp lớp 1; ~1.8 USDT nếu khớp đủ 5 lớp.
  An toàn nghĩa là lãi mỗi lần nhỏ. Duyệt 7Q2X.v1 không?
Anh:    Giảm còn 4 lớp, cách 2%, lỗ tối đa 20 USDT.
Trợ lý: Em chạy: plan edit 7Q2X.v1 --layers 4 --spacing 2 --max-loss 20
        → 7Q2X.v2 (v1 hết hiệu lực). [diff §5.5]. Mọi kiểm tra PASS. Duyệt 7Q2X.v2?
Anh:    Duyệt.
Trợ lý: execute 7Q2X.v2 --confirm --hash 9f3a1c → đã đặt 4 lệnh chờ, SL 2211.26 sẽ đặt khi khớp lớp 1.
```

Quy tắc cho trợ lý: câu mơ hồ ("an toàn hơn chút") → hỏi lại bằng lựa chọn cụ thể, không đoán; "Duyệt"/"OK" chỉ áp cho phiên bản **mới nhất vừa hiển thị**; nếu plan đã hết hạn → `plan refresh` → hiển thị diff → hỏi duyệt lại (không tự execute bản làm mới).

---

## 2. Hồ sơ khẩu vị ("hồ sơ") [→ SPEC 4.2, A.2 `variant`/`risk`]

### 2.1 Bộ câu hỏi (hỏi một lần, bằng chat hoặc `profile quiz`)

| # | Câu hỏi (nguyên văn hiển thị) | Lựa chọn |
|---|---|---|
| P1 | "Nếu một thang thua tới điểm cắt lỗ, anh chấp nhận mất tối đa bao nhiêu % vốn cho thang đó?" | a) 3% · b) 5% · c) 7% |
| P2 | "Trong một ngày, lỗ bao nhiêu % thì anh muốn công cụ ngừng gửi lệnh mở mới đến 7h sáng hôm sau? (Lệnh chờ đã treo vẫn có thể khớp nếu không huỷ.)" | a) 3% · b) 5% · c) 8% |
| P3 | "Trong một tuần, lỗ bao nhiêu % thì ngừng gửi lệnh mở mới đến 7h sáng thứ Hai tuần sau?" | a) 6% · b) 10% · c) 15% |
| P4 | "Anh có muốn để riêng một phần nhỏ vốn để đánh nhanh (Scalp) không? Phần này có ngân sách lỗ riêng, hết là khoá." | a) Không · b) 10% vốn · c) 20% vốn |
| P5 | "Tối đa bao nhiêu thang chạy cùng lúc?" | 1 / 2 / 3 / 4 |
| P6 | (tuỳ chọn) "Có khung giờ nào không muốn mở lệnh mới không?" | danh sách khoảng giờ UTC+7, vd `20:30–22:30` |

**Quy tắc ánh xạ (xác định, không cảm tính):**
- **Bậc = theo P1**: a → Thận trọng, b → Cân bằng, c → Mạo hiểm có kiểm soát.
- P2, P3, P5: giá trị dùng = `min(câu trả lời, trần của bậc)`. Chọn lỏng hơn trần → công cụ báo "đã giới hạn về X theo bậc".
- P4: Thận trọng → luôn 0%; Cân bằng → tối đa 10%; Mạo hiểm → tối đa 20%. Chọn vượt → hạ về trần và báo.
- P6: lưu nguyên; áp R26.

### 2.2 Bảng tham số theo bậc (đều nằm trong Phụ lục A)

`E` = equity tài khoản; `E_wide` = phần vốn an toàn (§3). Wide luôn N = 5, d = 1.5%, TP1 +1.2% đóng 50%, TP2 +2.4%, BE như SPEC 4.5.

| Tham số | Thận trọng | Cân bằng | Mạo hiểm có kiểm soát | Hằng cứng (A) |
|---|---|---|---|---|
| Lỗ tối đa mỗi thang Wide `s` | 3% `E_wide` | 5% `E_wide` | 7% `E_wide` | ≤ 7% |
| Cap mỗi thang `capLeg` | 0.45× `E_wide` | 0.75× `E_wide` | 1.25× `E_wide` | ≤ 2.0× |
| Số thang Wide tối đa (cả P5) | 2 | 4 | 3 | ≤ 4 |
| Cap cùng chiều Wide | 0.9× E | 1.5× E | 2.0× E | ≤ 2.5× |
| Cap tổng (Wide + Scalp) | 0.9× E | 3.0× E (4.5× nếu có xô 10%) | 7.0× E | Wide ≤ 8×; có Scalp ≤ 20× |
| Cap cùng chiều (Wide + Scalp) | – | 3.0× E (chỉ khi có xô) | 5.0× E | ≤ 15× |
| R14: Σ lỗ-tại-SL mọi thang (định nghĩa §9.2) | ≤ 7% E | ≤ 21% E | ≤ 25% E | 25% / 30% có Scalp |
| Khoá ngày (P2, trần) | 3% | 5% | 8% | ≤ 10% Wide, ≤ 15% Scalp |
| Khoá tuần (P3, trần) | 6% | 10% | 15% | ≤ 15% (mới) |
| DD breaker (đỉnh 30 ngày) | 10% | 15% | 20% | ≤ 25% (mới) |
| Chuỗi stop | SL thứ 2 trong 24 h → khoá mở mới 12 h | như trái | như trái | – |
| Xô mạo hiểm (P4, trần) | 0% | 10% | 20% | ≤ 20% (mới) |
| Lỗ tối đa mỗi thang Scalp (gồm trượt 0.3%) | – | 2.5% E | 5% E | ≤ 15% |
| Ngân sách lỗ của xô / kỳ | – | 5% E | 10% E | = 50% xô |
| Đòn bẩy cài sàn (chỉ ký quỹ) | 10× | 10× (20× nếu có xô) | 20× | ≤ 50× (§9.7) |

Lý do chọn: Cân bằng dùng tham số giống SAFE; kết quả backtest SAFE là **kết quả lịch sử của cấu hình khác** (cách chạy khác công cụ, §2.6), không phải kỳ vọng của bậc – **chưa có số kỳ vọng nào cho tới B9**. Thận trọng = SAFE thu nhỏ theo tỉ lệ (cùng `s/capLeg` = 6.67% → cùng vị trí SL) – **chưa backtest**. Mạo hiểm = tham số DEFAULT nhưng trên 80% vốn và **tối đa 3 thang** (giải N2) – **chưa backtest đúng cấu hình này → phải qua B6 + B9 trước khi bật live và trước khi hiển thị bất kỳ con số kỳ vọng nào** (§11).

Kết quả số (E = 524.7, size thật sau làm tròn, TP đóng bằng lệnh trigger-market = taker):

| Bậc / thang | Notional đầy | SL | SL ngoài lớp 5 | Lỗ tại SL | +trượt 0.3% | Lãi TP1 chỉ lớp 1 | Lãi TP1 đầy thang |
|---|---|---|---|---|---|---|---|
| Thận trọng BTC long | 213.57 (0.41×) | 73978.4 | −3.75% | 13.99 | 14.59 | 0.18 | 1.15 |
| Thận trọng ETH long | 185.27 (78.5% cap, lot thô) | 2174.58 | −3.75% | 11.44 | 11.96 | 0.27 | 1.04 |
| Cân bằng ETH long | 349.36 (0.67×) | 2174.58 | −3.75% | 23.44 | 24.42 | 0.27 | 1.83 |
| Cân bằng ETH short | 370.96 | 2634.71 | +3.43% | 24.55 | 25.74 | 0.27 | 1.94 |
| Cân bằng BTC long | 372.04 | 73978.4 | −3.75% | 24.63 | 25.67 | 0.37 | 2.04 |
| Cân bằng BTC short | 378.60 | 89632.2 | +3.43% | 25.06 | 26.27 | 0.37 | 2.08 |
| Mạo hiểm ETH long (E_wide 419.76) | 465.81 (0.89×E) | 2199.43 | −2.65% | 26.29 | 27.60 | 0.54 | 2.61 |
| Mạo hiểm BTC long | 506.86 | 74823.7 | −2.65% | 28.37 | 29.81 | 0.55 | 2.84 |
| Mạo hiểm ETH short | 494.62 | 2608.36 | +2.40% | 27.47 | 29.03 | 0.54 | 2.77 |

R14: Cân bằng 4 thang = 97.68 USDT = **18.62% E** (≤ 21%; vẫn ≤ 21% đến khi E còn ~465). Thận trọng 2 thang BTC = 27.91 = 5.32%. Mạo hiểm 3 thang Wide = 83.87 = 15.98%; + 1 thang Scalp (25.39 gồm trượt) = **20.82%** ≤ 25%.

> Ghi chú Thận trọng: ETH lot 0.01 ≈ 24 USDT quá thô cho lớp ~47 USDT (chỉ dùng 78.5% cap). Bộ đề xuất (§4) ưu tiên BTC ở bậc này.

### 2.3 Lưu trữ & phiên bản

- Bảng `risk_profiles(version PK, created_at, effective_at, status[pending|active|superseded|cancelled], tier, answers_json, params_json, params_hash, change_kind[lower|raise|init], reason)`; bản người đọc `state/profiles/profile_v{N}.yaml` (chỉ đọc; sửa tay file → hash lệch → công cụ từ chối khởi động hồ sơ đó).
- `params_json` là **tham số đã giải** (bảng 2.2 sau khi áp min), không phải câu trả lời thô → plan chỉ đọc `params`.
- Mỗi plan lưu `profile_version` + `params_hash`. Execute/apply yêu cầu `profile_version == active` (R27).

```yaml
schema: profile.v1
version: 3
status: active
tier: can_bang
created_at: 2026-10-20T09:40:00+07:00
effective_at: 2026-10-20T09:40:00+07:00
answers: {P1: b, P2: b, P3: b, P4: a, P5: 4, P6: ["20:30-22:30"]}
params:
  wide: {s_pct: 5, cap_leg_x: 0.75, max_ladders: 4, samedir_x: 1.5, layers: 5, spacing_pct: 1.5,
         tp1_pct: 1.2, tp1_fraction: 0.5, tp2_pct: 2.4}
  account: {total_x: 3.0, sl_budget_pct: 21, daily_stop_pct: 5, weekly_stop_pct: 10, dd_breaker_pct: 15,
            stop_chain: {count: 2, window_h: 24, lock_h: 12}, no_trade: ["20:30-22:30"], leverage: 10}
  bucket: {share_pct: 0}
  nonstop: null   # PN; chỉ Mạo hiểm (C30): {share_pct, samedir_x, total_x}; samedir_x ≤ trần cùng chiều của hồ sơ, total_x ≤ account.total_x (§3.5 mục 4a)
params_hash: 4be1…
```

### 2.4 Quy tắc đổi hồ sơ

| Loại đổi | Hiệu lực | Lý do |
|---|---|---|
| **Hạ rủi ro** (bậc thấp hơn, hoặc bất kỳ tham số chặt hơn) | **Ngay lập tức** sau `profile set … --confirm` | Không bao giờ nên trì hoãn việc an toàn hơn |
| **Tăng rủi ro** (bất kỳ tham số lỏng hơn, kể cả tăng xô) | `pending`, tự hiệu lực sau **24 h**; huỷ được trong thời gian chờ; thông báo khi hiệu lực | Chống "gỡ" sau thua lỗ (tilt); 24 h = qua một ranh giới ngày |
| Tăng khi đang có khoá ngày/tuần/DD/xô | **Từ chối** | Không dùng đổi hồ sơ để thoát khoá |
| Tăng lần 2 trong 7 ngày | **Từ chối** | Hạn chế leo thang |
| Hỗn hợp (vừa chặt vừa lỏng) | Coi là tăng | Đơn giản, an toàn |
| Bật Nonstop / đổi `params.nonstop.*` (PN) | như mọi tham số: lỏng hơn = tăng (pending 24 h…), chặt hơn hoặc tắt = hạ; `profile set` từ chối nếu `params.nonstop.*` > trần tương ứng của hồ sơ hoặc > hằng cứng | Không có đường nào để trần Nonstop vượt trần hồ sơ (§3.5 mục 4a) |

Ảnh hưởng: hồ sơ mới hiệu lực → mọi plan chưa execute mất hiệu lực (phải `plan refresh`); thang đang chạy **không bị ép thu nhỏ**, nhưng mọi chỉnh sửa *làm tăng lỗ xấu nhất* phải về trong trần mới (§6.3); R14/cap tài khoản cho thang mới dùng trần mới.

### 2.5 Hồ sơ đi vào preview/kiểm tra – bộ kiểm tham số theo chế độ

- Bộ đề xuất (§4) sinh tham số **bằng** trần hồ sơ (hoặc thấp hơn nếu bị thu nhỏ).
- R27 (mới) gồm phần chung (`profile_version == active`, số thang theo §3.5) và **hai bộ kiểm tham số riêng theo `mode` của plan**: **R27w** (Wide) và **R27s** (Scalp). Không có giới hạn spacing/TP/số lớp nào áp chung cho cả hai chế độ; `plan edit`, `ladder edit`, `execute`, `ladder apply` đều gọi đúng bộ theo `mode` (R11/R13 của SPEC cũng theo chế độ như SPEC 5.2 dòng "Scalp mode").

| Tham số | Wide – R27w | Scalp – R27s (hằng cứng SPEC 4.12.2 + §3.4) |
|---|---|---|
| Số lớp N | 1–5 | 1–12 (mặc định 4) |
| Khoảng cách lớp kề `d` (cả giá khớp thật khi sửa thang chạy) | ≥ 1.0% | ≥ 0.15% (cứng), ≤ 0.30% (mặc định 0.20%) |
| Hệ số size `mult` | – (size đều theo budget/N) | 0.80–1.00 (cứng ≤ 1.00, cấm tăng dần) |
| Quy mô | `budget ≤ capLeg × E_wide` | lớp đầu ≤ 5× E (cứng); size giải ngược từ `L` (§3.4) |
| Lỗ tối đa | `max_loss ≤ s × E_wide` | `L ≤ per_ladder_scalp` của bậc (§2.2) và ≤ 15% E (cứng); gồm trượt 0.3% |
| TP1 / TP_a | 0.6–2.0% | ≥ 0.12% (cứng), mặc định +0.15% |
| TP2 / TP_b | ≥ TP1 + 0.4%, ≤ 4% | TP_a ≤ TP_b ≤ 0.30% (mặc định +0.20%) |
| Phần chốt ở TP1 / TP_a | 0.3–1.0 | 0.3–1.0 (mặc định 0.5) |
| SL | R13: cách lớp cuối ≥ 1.0% | `SL = P_N × (1 − sg·sl_gap)`, `sl_gap` = 1.0% (cấu hình `scalp.sl_gap_pct`) |
| Liq khi thêm lớp | R15 | ≥ max(3%, ngưỡng cảnh báo bậc) (SPEC 4.12.3c, C22) |
| Số thang | ≤ `max_ladders` bậc | ≤ 1 cùng lúc (C28) + R28 |

- Ví dụ §3.4 (4 lớp, d 0.20%, TP_a 0.15% / TP_b 0.20%, mult 0.87, L 26.235) PASS R27s; cùng plan đưa vào R27w sẽ FAIL (spacing, TP) – đúng là lỗi cũ; U54 kiểm cả hai chiều.
- Ngưỡng R9/R10/R14/R18–R20 lấy từ `params.account` và ma trận §3.5.

### 2.6 Kỳ vọng backtest – số nào còn dùng được [→ SPEC 1.3, Phụ lục C; review Q-3]

| Cấu hình trong công cụ | Số liệu đang có | Còn áp dụng? |
|---|---|---|
| Cân bằng (tham số = SAFE: 0.75×/5%, 4 thang, 100% E) | `final_eval.csv` SAFE (TP maker, BE khác, mở lại thang ngay, L1 khớp ngay) | **Không áp dụng** – kết quả lịch sử của cấu hình khác. **Không hiển thị** trong digest/README/`status`; **chưa kiểm định** cho tới B9 |
| Cân bằng + xô 10% | không có | **chưa kiểm định** |
| Thận trọng (0.45×/3%, 2 thang) | không có | **chưa kiểm định** (không được suy tuyến tính từ SAFE vì làm tròn lot và số thang khác) |
| Mạo hiểm (DEFAULT trên 80% E, ≤ 3 thang) | DEFAULT / AGGR trong `final_eval.csv` là **4 thang trên 100% E**, AGGR không có cap cùng chiều | **Không áp dụng** – kết quả lịch sử của cấu hình khác; không hiển thị |
| Scalp trong xô (§3.4) | `REPORT.txt` bản thuần hoá (tham số khác) −62%/60 ngày | **chưa kiểm định**; chỉ hiển thị cảnh báo SPEC 4.12 |

Quy tắc: README, `status`, digest chỉ in số kỳ vọng lấy từ **B9** (nguồn duy nhất) với `config_hash` trùng `params_hash` của hồ sơ đang dùng (Mạo hiểm cần thêm B6, xô cần B8). Không có → in "Kỳ vọng lãi: chưa kiểm định bằng backtest cho cấu hình này". **Không có ngoại lệ** (bỏ ngoại lệ SAFE của bản trước). Nếu tài liệu cần nhắc số cũ thì chỉ được gọi là "kết quả lịch sử của cấu hình khác", không đặt cạnh tên bậc, không phải kỳ vọng.

---

## 3. Chia vốn an toàn / mạo hiểm [→ SPEC 4.12.2, 4.12.5, mới]

### 3.1 Sổ phân bổ vốn (một sổ chung) trên một tài khoản cross

Một tài khoản cross không thể tách ký quỹ → tách **về sổ sách và quy tắc**, còn kiểm tra thanh lý/exposure luôn dùng **toàn tài khoản**. Có **một** sổ chung `alloc_ledger` cho cả ba phần vốn: **Wide** (`wide`), **xô Scalp** (`scalp`), **xô Nonstop** (`nonstop`, PN – §6B). Vị thế/lệnh tay và mọi khoản không gán được thuộc `wide`.

**Phân bổ (dòng `alloc`)**: khi xô được kích hoạt hoặc `bucket refill`: `E_risk_base = share_scalp × E_now`, `E_ns_base = share_ns × E_now` (đóng băng cho kỳ); mỗi lần cấp là một cặp dòng nội bộ `alloc` (−X ở `wide`, +X ở xô) nên tổng không đổi. `budget_risk = 50% × E_risk_base` (USDT, đóng băng cho kỳ).

**Mô hình dòng sổ (chọn một mô hình duy nhất)**: **nhiều dòng sổ cho một sự kiện nguồn**, mỗi dòng có khoá duy nhất `(source_kind, source_id, line_type, ledger)`:

| `line_type` | Nguồn (`source_kind`, `source_id`) | `amount` | Ghi vào |
|---|---|---|---|
| `open_fee` | fill mở (`fill`, `tradeId`; WS `fill`, đối soát `GET /api/v2/mix/order/fills`, `tradeSide=open`) | `totalFee` của fill (âm) | sổ của leg |
| `close_pnl` | fill đóng (`fill`, `tradeId`) – TP, SL, reduce, `ladder close`, kill, thanh lý | `profit` của fill | sổ của leg |
| `close_fee` | **cùng** fill đóng (`fill`, cùng `tradeId`) | `totalFee` của fill (âm) | sổ của leg |
| `funding` | bill funding (`bill`, `billId`; `businessType=contract_settle_fee`, `GET /api/v2/mix/account/bill`) | phần chia (dưới) | **mỗi** sổ có leg trên symbol đó – tối đa 3 dòng cho 1 bill |
| `alloc` / `sweep` | nội bộ (`internal`, `op_id`) | cấp vốn / quét số dư xô về `wide` | cặp dòng ± |
| `transfer` | bill chuyển tiền vào/ra (`bill`, `billId`) | `amount` | `wide` |
| `unattributed` | bill khác không gán được (`bill`, `billId`) | `amount` | `wide` + CAO |

Vì khoá gồm `line_type` (và `ledger`), `close_pnl` và `close_fee` của cùng một `tradeId` là **hai dòng khác khoá**, không bao giờ đè nhau; ghi lại sự kiện cũ (khởi động lại, đối soát 15 phút) → trùng khoá → bỏ qua. Ghi **ngay khi sự kiện xảy ra** (không đợi đóng thang).

**Chia funding** (bill chỉ có `symbol`, không có holdSide): với bill `F` của symbol S, phần lý thuyết của từng sổ `f_k = −sg·Q_k·mark·fundingRate` (Q_k = size các leg của sổ k trên S tại mốc; rate từ `GET /api/v2/mix/market/history-fund-rate`). Ghi `scalp = round2(f_scalp)`, `nonstop = round2(f_nonstop)` (chỉ khi sổ có leg trên S), và **`wide = F − scalp − nonstop`** (phần dư, gồm làm tròn và vị thế tay) → **ba phần luôn cộng đúng bằng `F`**. Nếu `|F − Σ_k f_k| > max(0.01, 1% |F|)` → CAO "funding lệch mô hình" (ghi lại cho D33). Cách chia theo mô hình này **chưa kiểm chứng** với bill thật (D33).

**Số dư từng phần** tại t: `E_k(t) = Σ amount (mọi dòng của sổ k) + upnl_k(t)` (k = wide, scalp, nonstop; `upnl_k` = Σ uPnL mark của leg thuộc sổ k), với `E_wide` lúc khởi tạo sổ = E. Ký hiệu cũ: `E_risk = E_scalp`, `E_ns = E_nonstop`.

**Đẳng thức đối soát** (kiểm mỗi 15 phút và trước mọi hành động tăng rủi ro): `E_wide(t) + E_risk(t) + E_ns(t) = E(t)` (equity tài khoản theo mark), dung sai `alloc.reconcile_tol_usdt` (0.05). Lệch → tải lại fills/bill thiếu; còn lệch → `unattributed` không giải thích được → CAO + **chặn mọi hành động tăng rủi ro** (như cột "Bộ đếm UNKNOWN" §8.4) tới khi đẳng thức đạt.

**Vốn Wide dùng để tính size**: `E_wide_sizing(t) = E(t) − max(0, E_risk(t)) − max(0, E_ns(t))` (đóng băng ở preview). Ví dụ E = 524.70, xô Scalp 10% và xô Nonstop 10% vừa cấp: `E_wide_sizing = 524.70 − 52.47 − 52.47 = 419.76` (công thức cũ `E − E_risk` cho 472.23 – **sai**, đã bỏ).

**Xô âm**: xô không bị chặn dưới 0 (Nonstop không có SL; Scalp có thể trượt/gap). Khi `E_risk(t) < 0` hoặc `E_ns(t) < 0`: phần âm **đã nằm trong E** (lỗ thật trên ký quỹ chung), và `max(0, ·)` ở công thức trên làm `E_wide_sizing` = E − phần dương còn lại → **phần thiếu của xô trừ thẳng vào vốn Wide dùng để tính size** (C41). Xô âm = xô khoá (§3.2, 6B.1); `deficit_k = −E_k` hiển thị ở `bucket status`.

**Refill / quét**: `bucket refill [--nonstop] --confirm` (theo §3.2): (1) ghi `sweep` chuyển toàn bộ số dư **đã thực hiện** của xô (dương hoặc âm) về `wide`; (2) cấp mới `alloc = share × E_now`. Chỉ được refill khi xô **không còn leg mở và không còn lệnh chờ** (uPnL = 0); nếu không → từ chối "còn thang đang mở trong xô".

**Tắt xô / hạ share khi còn vị thế**: `profile set --bucket 0` hoặc `--nonstop-bucket 0` (hạ rủi ro, hiệu lực ngay) **chỉ** chặn mở thang mới trong xô đó; vốn đã phân bổ **không** được giải phóng: sổ xô giữ nguyên (`alloc` cũ, mọi dòng mới của leg còn mở vẫn ghi vào xô), `E_wide_sizing` vẫn trừ phần dương của xô. Giải phóng (`sweep` về `wide`) **tự động** chỉ khi mọi leg của xô có size 0 **và** không còn lệnh chờ **và** đẳng thức đối soát đạt.

**Ngân sách đã dùng (Scalp)**: `realized_risk` = Σ `amount` dòng của sổ `scalp` trong kỳ, trừ `alloc`/`sweep`; `used = max(0, −realized_risk) + Σ worst_loss(thang Scalp đang mở)` với `worst_loss` = WCL §6.3 (lỗ tại SL + trượt 0.3%) **trừ phần đã ghi sổ** (phí mở của lớp đã khớp và `realized_leg`), để không tính hai lần. Lãi Scalp **không** làm tăng `budget_risk` trong kỳ (lãi ở lại xô, cuối kỳ quét về `wide` qua refill).
- R28 (mở thang Scalp): `used + worst_loss(thang mới) ≤ budget_risk` **và** `worst_loss(thang mới) ≤ per_ladder_scalp` (bảng 2.2).
- Wide không bao giờ được tính trên vốn xô; Scalp/Nonstop không bao giờ được dùng `E_wide` hay phần ngân sách R14 dành cho Wide (chia ngân sách R14 và mọi cap dùng chung: §3.5).

### 3.2 Khoá xô

- Khoá khi `budget_risk − used_realized < 50% × per_ladder_scalp` (không đủ cho một thang nhỏ) hoặc `realized` lỗ ≥ `budget_risk`.
- Khi khoá: huỷ mọi entry Scalp chưa khớp; thang Scalp đang có vị thế giữ SL/TP; không mở Scalp mới.
- **Mở khoá**: sớm nhất **07:00 UTC+7 ngày 1 tháng sau VÀ ≥ 7 ngày kể từ lúc khoá**, rồi chủ chạy `bucket refill --confirm` (không tự refill). Refill: `E_risk_base = share × E_now`; bị từ chối nếu đang khoá ngày/tuần/DD. Đây là cấp vốn mới cho kỳ mới, không phải "vay" giữa kỳ.
- Lỗ vượt ngân sách do trượt/gap: ghi `overshoot`, hiển thị; kỳ sau `budget_risk` trừ đi `overshoot`. Xô âm, refill/quét và tắt xô khi còn vị thế: §3.1.
- Thành thật trong README/UX: tách xô là **kỷ luật sổ sách**; trên sàn, lỗ Scalp vẫn trừ vào cùng ký quỹ cross. Vì vậy:

### 3.3 Kiểm tra toàn tài khoản (không đổi bản chất)

R9/R10/R14/R15/R16 dùng **E toàn tài khoản** và **mọi thang (Wide + Scalp + vị thế/lệnh tay)** ở kịch bản xấu nhất (SPEC 4.8(b), sửa m9: thang ngược chiều không tính lãi, vẫn tính MM). Ví dụ Mạo hiểm đầy (BTC-L, ETH-S, BTC-S Wide + ETH-L Scalp, tất cả khớp đủ): tổng 2990.39 USDT = **5.70× E**, cùng chiều long 3.79× E, short 1.90× E; giá giảm đồng loạt **~25.8%** (từ giá TB, cách tính bảo thủ) mới tới thanh lý ước tính, trong khi SL xa nhất phía long cách giá TB 5.52% → R15 PASS.

### 3.4 Scalp trong xô – tham số & ví dụ [thay ví dụ SPEC 4.12.4]

Sizing **ngược từ lỗ tối đa** (dễ hiểu cho người không chuyên: "mất tối đa X USDT nếu giá đi ngược thêm 1% sau lớp cuối"):
- N = 4 (mặc định, ≤ 12 cứng), d = 0.20%, mult 0.87, `SL = P_N × (1 − sg·1.0%)` (làm tròn theo bảng 4.9).
- Chọn notional lớp đầu `X` sao cho `lỗ_tại_SL(size thiết kế) + Q·SL·0.003 = L_scalp`; `q_i = floor(X·mult^(i−1)/P_i)`; kiểm lại với size đã làm tròn ≤ L_scalp.
- TP_a +0.15% (50%) / TP_b +0.20% như SPEC 4.12.2. Mọi kiểm tra R8–R17 bản Scalp áp dụng, cộng R28 và bộ kiểm tham số **R27s** (§2.5).

Ví dụ Mạo hiểm, ETH long, P₁ 2400.00, `L_scalp` = 5% × 524.7 = 26.235 → X = 468.08 (0.89× E):

| Lớp | Giá | Δ% | ETH | Notional | ×E lũy kế | Giá TB | TP_a | TP_b |
|---|---|---|---|---|---|---|---|---|
| S1 | 2400.00 | 0.00 | 0.19 | 456.00 | 0.87 | 2400.00 | 2403.60 | 2404.80 |
| S2 | 2395.20 | −0.20 | 0.17 | 407.18 | 1.65 | 2397.73 | 2401.33 | 2402.53 |
| S3 | 2390.40 | −0.40 | 0.14 | 334.66 | 2.28 | 2395.68 | 2399.28 | 2400.48 |
| S4 | 2385.62 | −0.60 | 0.12 | 286.27 | 2.83 | 2393.73 | 2397.33 | 2398.53 |

SL **2361.77** (−1.59% từ L1, −1.34% từ TB). Lỗ tại SL 20.99; +trượt 0.3% = 25.39 (≤ 26.235); trượt 1% = 35.64 (phải hiển thị). Lãi nếu chỉ lớp 1 về TP: **~0.62 USDT**; cả thang: ~2.01 USDT. Cân bằng (xô 10%, L 13.118): size 0.09/0.08/0.07/0.06, cùng SL, lỗ 10.12 / 12.24 (trượt 0.3%), lãi lớp 1 ~0.30 USDT.

### 3.5 Ràng buộc Wide/Scalp cùng tồn tại [giải các điểm mở của SPEC 4.12.5, R8–R10, R14]

1. **Một thang mỗi (symbol, holdSide), bất kể chế độ** (Wide, Scalp, và Nonstop §6B.6; giữ SPEC 4.11/4.12.5). Thang đang tồn tại thắng: `propose` bỏ qua cặp đó; `propose --mode wide` trên cặp đang có Scalp (hoặc ngược lại) → R6 FAIL "đang có thang Scalp ETH long; đóng/huỷ trước".
2. **Số thang**: Wide ≤ `max_ladders` của bậc; Scalp ≤ 1 cùng lúc (câu hỏi C28) và luôn bị R28 chặn thêm; tổng ≤ 4 (2 symbol × 2 chiều). Ví dụ Cân bằng có xô: khi Scalp đang mở, Wide còn tối đa 3.
3. **Bộ đếm exposure dùng chung**: `exposure_worst`, `same_dir_worst` (SPEC 5.1) luôn gồm mọi leg: Wide, Scalp, vị thế/lệnh tay.
4. **Ma trận cap – mọi kiểm tra áp dụng đều phải PASS (cái chặt nhất thắng):**

| Kiểm tra | Áp lên | Mẫu số | Ngưỡng |
|---|---|---|---|
| R8 cap thang Wide | thang Wide | `E_wide` | `capLeg` bậc (≤ cứng 2.0×) |
| R10w cùng chiều Wide | Σ thang Wide cùng chiều | E | bậc 0.9 / 1.5 / 2.0× (≤ cứng 2.5×) |
| R9w tổng Wide | Σ thang Wide | E | ≤ cứng 8× |
| Thông số Scalp (first_x, mult, d, số lớp, liq ≥ max(3%, ngưỡng cảnh báo)) | thang Scalp | E | SPEC 4.12.2 + §3.4 |
| R28 ngân sách xô | thang Scalp | `budget_risk` | §3.1 |
| R9a tổng tài khoản | mọi leg | E | bậc 0.9 / 3.0 (4.5 có xô) / 7.0× (≤ cứng 8×, 20× khi có Scalp) |
| R10a cùng chiều tài khoản | mọi leg cùng chiều | E | bậc – / 3.0 (có xô) / 5.0× (≤ cứng 15×) |
| R14 tổng rủi ro | mọi leg | E | bậc; **phần Wide ≤ bậc − `per_ladder_scalp`** khi xô > 0 (giữ chỗ cho 1 thang Scalp); phần Scalp do R28 |
| R15/R16/R17 | tài khoản / symbol | – | như SPEC, R16 theo Q-4 |

   **4a. Trần hiệu lực** (mọi kiểm tra có cả trần hồ sơ và hằng cứng: R8, R9w, R9a, R10w, R10a, R14, N1): `limit_eff = min(trần hồ sơ đang hiệu lực, trần theo chế độ trong hồ sơ hoặc cấu hình nếu có, hằng cứng)`. Hằng cứng chỉ là **giới hạn trên cho giá trị của hồ sơ/cấu hình** (kiểm khi `profile set` / khởi động: vượt → từ chối), **không bao giờ** thay thế trần hồ sơ khi kiểm plan. Ô "–" của bảng 2.2 (vd Thận trọng cùng chiều Wide + Scalp) = không có xô nên chỉ có leg Wide, dùng R10w. Thông báo FAIL in đủ các số và số nào thắng, vd "R10a: 6.10× > 5.00× (hồ sơ Mạo hiểm; cấu hình Nonstop 15×; cứng 15×)". Nonstop **không** có trần riêng vượt hồ sơ: `params.nonstop.{samedir_x, total_x}` (nếu có) chỉ được ≤ trần tương ứng của hồ sơ (§2.3) – muốn Nonstop lớn hơn thì phải nâng trần hồ sơ theo quy tắc tăng rủi ro §2.4, vẫn ≤ hằng cứng (C33).

   Hệ quả: Scalp lớn không làm FAIL R10w của Wide nhưng có thể làm FAIL R10a → `propose` thu nhỏ Wide (bước 6 §4) hoặc bỏ ứng viên. Ví dụ Mạo hiểm: R14 phần Wide ≤ 25% − 5% = 20% (3 thang Wide 15.98% ✓), toàn TK 20.82% ✓.
5. **Leverage theo symbol dùng chung**: nếu symbol có Scalp (20×), thang Wide trên cùng symbol cũng chạy ở 20× (chỉ ảnh hưởng ký quỹ; R16 tính theo leverage thật).
6. Sửa thang chạy (§6), `reduce`/`entry_adjust` (§6A) chạy lại cùng ma trận (chỉ phần làm tăng rủi ro mới có thể FAIL).

---

## 4. Đề xuất plan tự động (`propose`) [mới; `preview` cũ thành trường hợp riêng]

Thuần hàm: `propose(profile, bucket_state, account_snapshot, open_legs, lights, contracts, tickers, now) → [plan v1]`, xác định (cùng đầu vào → cùng kết quả).

1. **Ứng viên** = {BTC, ETH} × {long, short} trừ: (symbol, chiều) đã có thang công cụ hoặc vị thế/lệnh tay (R6/R7); đang trong giờ cấm (R26); đang có khoá (ngày/tuần/DD/chuỗi stop).
2. **Lọc đèn**: chỉ giữ **xanh**. Vàng: không đề xuất, nhưng nêu trong digest "có thể nếu anh muốn" (người dùng tự gọi `propose --symbol --side`). Đỏ/xám: không đề xuất.
3. **Chỗ trống**: `slots = max_ladders − số thang Wide đang mở`; headroom R10 cùng chiều, R14, R9.
4. **Xếp hạng** (theo thứ tự, hoà thì xét tiêu chí sau): (a) làm **cân bằng sổ** (giảm |long − short| notional); (b) hiệu quả làm tròn `notional_thật / cap` cao hơn (ở E này BTC thường thắng); (c) ít lý do vàng hơn ở TF 4h/1d; (d) BTC trước ETH.
5. **Tham số**: N, d, TP theo hồ sơ; `budget = capLeg × E_wide`; `max_loss = s × E_wide`; anchor = giá maker tốt nhất (long `bidPr`, short `askPr`), `anchor.mode = market_shift` (§9.5). `levels` chỉ khi cổng 6.8 đạt.
6. **Thu nhỏ khi vướng headroom**: nếu R10/R14/R9 FAIL chỉ vì headroom → giảm `budget` và `max_loss` cùng tỉ lệ theo bước 10% (giữ `s/capLeg` → SL không đổi) đến khi PASS; dưới 50% trần hoặc lớp < size tối thiểu → bỏ ứng viên. Plan ghi "thu nhỏ còn 70% vì R14".
7. Tối đa **2 đề xuất**/lần. Mỗi đề xuất có câu tóm tắt chuẩn (§8.2).

Scalp **không bao giờ được đề xuất tự động** (giữ tinh thần SPEC 4.12): người dùng gọi `propose --mode scalp --symbol --side`; công cụ chỉ dựng plan theo §3.4.

---

## 5. Sửa plan (trước khi execute)

### 5.1 Lệnh

```
plan show  <ref> [--json]
plan edit  <ref> [--side long|short] [--layers N] [--spacing PCT] [--anchor PRICE|market]
                 [--layer IDX=PRICE]... [--remove-layer IDX]... [--budget USDT]
                 [--max-loss USDT|PCT%] [--tp1 PCT] [--tp1-frac F] [--tp2 PCT]
plan import <file.yaml>          # sửa bằng file
plan diff  <refA> <refB>
plan refresh <ref>               # cùng tham số, dữ liệu thị trường mới
plan list [--active]
```
`<ref>` = `root.vN` (vd `7Q2X.v2`) hoặc `version_id` 8 ký tự.

### 5.2 Trường được sửa & ràng buộc

Giới hạn số theo chế độ lấy từ bảng §2.5 (R27w / R27s); bảng dưới chỉ nêu cách áp.

| Trường | Wide | Scalp |
|---|---|---|
| `side` | đổi chiều = dựng lại thang từ anchor phía kia (bid↔ask); đèn của chiều mới áp dụng | như Wide |
| `layers` | 1 ≤ N ≤ 5; bớt lớp = bỏ lớp sâu nhất | 1 ≤ N ≤ 12; thêm/bớt lớp → giải lại size từ `L` (§3.4) |
| `spacing` | ≥ 1.0%; hình học như SPEC 4.3 | 0.15–0.30%; hình học như SPEC 4.12.3 |
| `anchor` | giá cụ thể → `anchor.mode = fixed`; `market` → `market_shift` | như Wide |
| `layer IDX=PRICE` | `mode=fixed`; cách lớp kề ≥ 1.0%; đơn điệu theo chiều | cách lớp kề ≥ 0.15%; đơn điệu theo chiều |
| `remove-layer` | đánh số lại; N ≥ 1 | như Wide, giải lại size |
| `budget` | ≤ `capLeg × E_wide`; ngân sách/lớp = budget/N (đều) | không dùng (size giải từ `max-loss`) → lỗi "Scalp tính size từ lỗ tối đa" |
| `max-loss` | ≤ `s × E_wide`; nhập `%` → % của E (hiển thị cả hai) | ≤ `per_ladder_scalp`; nhập `%` → % của E |
| `tp1`, `tp1-frac`, `tp2` | TP1/phần chốt/TP2 theo R27w | `tp1` = TP_a, `tp1-frac` = phần chốt ở TP_a, `tp2` = TP_b, theo R27s |

Không sửa được: symbol, mode (Wide↔Scalp – tạo plan mới), hằng cứng, tham số tài khoản (đổi qua `profile`), `mult` của Scalp (lấy từ cấu hình).

Vượt trần → lỗi rõ ràng: `"max-loss 35 USDT vượt trần hồ sơ Cân bằng (26.24 USDT = 5% E_wide). Muốn cao hơn: 'profile set …' (tăng rủi ro, hiệu lực sau 24 h)."` – không có cờ override.

### 5.3 Thứ tự tính lại (mỗi lần sửa)

1. Giá lớp (fixed/hình học, làm tròn 4.9) → 2. size `q_i = floor(B/P_i)` → 3. SL theo SPEC 4.6 với **Q thiết kế** và `L = max_loss` → 4. TP/BE → 5. liq (4.8a/b), exposure → 6. R1–R30 → 7. đèn → 8. hash. Plan FAIL vẫn được lưu thành phiên bản (để xem diff), nhưng không execute được; công cụ gợi ý cách sửa cụ thể (vd "R13: SL chỉ cách lớp 5 0.80%; giảm 1 lớp, hoặc max-loss ≥ 17 USDT, hoặc giảm budget").

### 5.4 Phiên bản

- `root_id`: 4 ký tự base32 (vd `7Q2X`); `version_id`: 8 ký tự base32 ngẫu nhiên, duy nhất, dùng trong clientOid (thay `plan_id` của SPEC 7.5; định dạng clientOid không đổi).
- Phiên bản **bất biến**. Sửa → phiên bản mới `vN+1` với `parent`; mọi phiên bản cũ cùng root chuyển `superseded` (không execute được). Mỗi root chỉ có tối đa 1 phiên bản `executed/running`.
- `content_hash` = SHA-256(`canonical_json(hash_content)`); DB lưu đủ 64 hex, hiển thị 6 hex đầu.
  - `hash_content` = **mọi trường** của phiên bản trừ `status`, `content_hash`, `edit_log[].text` (lời chat thô) và thời điểm đo của checks; tức gồm `schema, root_id, version, version_id, parent, kind, env, created_at, expires_at, profile{version, params_hash}, regime, mode, symbol, side, anchor, frozen, params, layers, derived, checks{id,status,value,limit}, light, override_reason` với `regime: nonstop` cả khối `nonstop` (`liq_all_fill`, `multiple_all_fill_x`, `fill_path`, `min_d_pct`, `limits_eff`, `sl_present`, `tp_present`), và, với `kind ∈ {reduce, entry_adjust}`, **toàn bộ** khối `reduce`/`entry_adjust` (§5.6: leg, close_qty, qty_source input + resolved, exec_mode, sl_mode, entry_actions, preconditions gồm `sl_policy`, tolerances, `prior_unknown_op`, expected_after, steps, client_oids).
  - **Không** thuộc `hash_content` (và không nằm trong bản ghi plan): mã xác nhận Nonstop. Trình tự cố định: (1) dựng phiên bản; (2) băm → `content_hash`; (3) suy mã `ack_expected = "NS-" + content_hash[0:6] + "-" + fmt2(min_d_pct)` (hàm tất định của nội dung đã băm); (4) khi duyệt, mã anh gõ được ghi vào bảng riêng `approvals(approval_id, version_id, content_hash, ack_entered, ack_expected, result[accepted|rejected], channel, created_at)`. Ghi `approvals` **không** đổi bản ghi plan nên không đổi hash (6B.3, U67).
  - `canonical_json`: UTF-8; khoá sắp xếp theo thứ tự byte; không khoảng trắng (`,` và `:`); giá/size/USDT là **chuỗi Decimal** định dạng cố định theo `pricePlace`/`volumePlace` của symbol (vd `"2385.62"`, `"0.64"`), USDT 2 chữ số, tỉ lệ % 4 chữ số (`"0.3000"`); thời gian = số nguyên epoch ms UTC; boolean/null theo JSON; mảng giữ thứ tự (lớp theo `idx` tăng dần); **cấm float JSON** (gặp float → lỗi).
  - `execute`/`apply`: (1) đọc bản ghi DB, băm lại → phải bằng `content_hash` đã lưu (phát hiện sửa DB/file); (2) `--hash` của người dùng phải là tiền tố (≥ 6 hex) của hash đó; (3) mọi tham số gửi sàn (giá, size, `close_qty`, clientOid) **chỉ** lấy từ bản ghi đã băm; ngoại lệ có kiểm soát duy nhất là `market_shift` §9.5 (dung sai nằm trong hash).
- Sửa bằng file: `plan show <ref> --yaml > plans/7Q2X/edit.yaml`, chỉ sửa `params`/`layers`, chạy `plan import`. Trường `derived/checks/frozen` trong file bị bỏ qua và tính lại. File của phiên bản đã lưu (`plans/7Q2X/v2.yaml`) chỉ để đọc; sửa tay → hash lệch → phiên bản đó bị đánh dấu `invalid`.
- Hết hiệu lực khi: có phiên bản mới; > 10 phút (`HARD_PLAN_TTL`); hồ sơ đổi; E lệch > 1% so với `frozen.equity`; giá vượt dung sai `market_shift`; snapshot tài khoản đổi làm một kiểm tra đổi trạng thái (vd thang khác vừa execute).

### 5.5 Định dạng diff (ví dụ v1 → v2, Cân bằng ETH long, E 524.7)

```
7Q2X.v1 → 7Q2X.v2   (lệnh: plan edit 7Q2X.v1 --layers 4 --spacing 2 --max-loss 20)
Trường            v1                         v2
Số lớp            5                          4
Khoảng cách       1.5%                       2.0%
Ngân sách/lớp     78.71                      98.38
Lớp (giá × ETH)   2400.00×0.03 … 2259.20×0.03  2400.00×0.04, 2352.00×0.04, 2304.96×0.04, 2258.86×0.04
Notional đầy      349.36 (0.67×E)            372.63 (0.71×E)
Giá TB đầy        2329.07                    2328.96
SL                2174.58 (−9.39% L1)        2211.26 (−7.86% L1; ngoài lớp cuối 2.11%)
Lỗ tại SL         23.44 (+trượt 24.42)       19.12 (+trượt 20.18)
Lãi TP1 lớp 1     0.27                       0.54
Lãi TP1 đầy       1.83                       2.09
R14 (riêng thang) 4.47%                      3.64%
Kiểm tra          R1–R30 PASS                R1–R30 PASS (không đổi trạng thái)
hash              1c07e2                     9f3a1c
```
Ví dụ FAIL: `--max-loss 15` giữ 5 lớp → SL 2241.08, chỉ cách lớp 5 **0.80%** → R13 FAIL (≥ 1%).

### 5.6 Schema plan (`plan.v2`, YAML/JSON)

```yaml
schema: plan.v2
root_id: 7Q2X
version: 2
version_id: K7Q2M9XB
parent: K7Q2M9XA
status: proposed   # proposed|superseded|invalid|expired|executed|running|closed|failed|applied_partial|aborted
kind: open         # open | running_edit | reduce | entry_adjust
created_at: 2026-10-20T07:12:40+07:00
expires_at: 2026-10-20T07:22:40+07:00
env: live
profile: {version: 3, tier: can_bang, params_hash: 4be1…}
regime: kiem_soat  # kiem_soat | nonstop (§6B); thiếu = kiem_soat
mode: wide        # kiem_soat: wide | scalp; nonstop: dca
symbol: ETHUSDT
side: long
anchor: {mode: market_shift, price: 2400.00, shift_tol_pct: 0.3}
frozen: {equity: 524.70, equity_wide: 524.70, bid: 2400.00, ask: 2400.01, mark: 2400.10,
         contracts_hash: 3e9a…, mmr: 0.005, ts: 2026-10-20T07:12:40+07:00}
params: {layers: 4, spacing_pct: 2.0, budget_usdt: 393.53, max_loss_usdt: 20.00,
         tp1_pct: 1.2, tp1_fraction: 0.5, tp2_pct: 2.4, tp_mode: plan_market, working_ttl_h: 24}
layers:
  - {idx: 1, price: 2400.00, size: 0.04, source: auto}
  - {idx: 2, price: 2352.00, size: 0.04, source: auto}
  - {idx: 3, price: 2304.96, size: 0.04, source: auto}
  - {idx: 4, price: 2258.86, size: 0.04, source: auto}
derived: {notional: 372.63, avg_full: 2328.96, sl: 2211.26, sl_gap_last_pct: 2.11,
          loss_at_sl: 19.12, loss_slip03: 20.18, be_full: 2332.45,
          tp1_l1_net: 0.54, tp1_full_net: 2.09, tp2_full_net: 4.32,
          exposure_after_x: 0.71, samedir_after_x: 0.71, r14_after_pct: 3.64, move_to_liq_pct: null}
checks: [{id: R13, status: PASS, value: "2.11%", limit: ">=1.0%"}]   # đủ R1–R30
light: {color: xanh, reason: "4h đi ngang, biến động bình thường.", raw_flag: OK, gate_passed: false}
override_reason: null
edit_log: [{from: K7Q2M9XA, cmd: "plan edit 7Q2X.v1 --layers 4 --spacing 2 --max-loss 20",
            source: chat, text: "Giảm còn 4 lớp, cách 2%, lỗ tối đa 20 USDT"}]
content_hash: 9f3a1c…
```
DB: bảng `plans` của SPEC 8.1 thêm cột `root_id, version, parent, kind, profile_version, anchor_mode, frozen_json, light_json, override_reason, reduce_json, observed_state_json`. Bảng mới: `approvals` (§5.4), `alloc_ledger` (§3.1), `leg_locks` (6A.8).
**Mở rộng schema cho `kind: reduce` và `kind: entry_adjust`** (YAML hiển thị giờ ISO cho người đọc; dạng băm dùng epoch ms – §5.4):

```yaml
schema: plan.v2
root_id: 7Q2X
version: 4
version_id: K7Q2M9XD
parent: K7Q2M9XC
kind: reduce              # open | running_edit | reduce | entry_adjust
status: proposed          # + aborted
created_at: 2026-10-20T10:19:40+07:00
expires_at: 2026-10-20T10:21:40+07:00      # = created_at + 120 s; bất biến; hạn duy nhất cho MỌI lần gửi (6A.8)
reduce:
  leg: {root_id: 7Q2X, symbol: ETHUSDT, hold_side: long, mode: scalp}
  qty_source: {type: pct, input: "30", resolved: "0.64", rounding: floor_lot}   # type: pct | qty (| target ở P2)
  close_qty: "0.64"
  exec_mode: market       # P1 chỉ market; maker từ P1b
  sl_mode: position_persist          # giá trị hợp lệ duy nhất khi tạo được reduce ở P1
  entry_policy: cancel_all           # P1: bắt buộc; keep / huỷ một phần = pha sau
  entry_actions: []       # P1: liệt kê MỌI lớp chờ của leg, tất cả action: cancel; {idx, client_oid, price, qty, action}
  tp_actions: [{role: T1, client_oid: "gsc1-K7Q2M9XA-EL-T1-3", action: cancel}, {role: T2, client_oid: "gsc1-K7Q2M9XA-EL-T2-3", action: cancel}]
  preconditions:
    account_mode: {product_type: USDT-FUTURES, margin_coin: USDT, pos_mode: hedge_mode, margin_mode: crossed}
    leg_state: ACTIVE     # ACTIVE | TP1_DONE | PROTECT_ONLY – quyết định TP sau đóng (6A.5)
    sl_policy: required   # required (Kiểm soát) | approved (Nonstop có SL) | none (Nonstop không SL) – điều kiện SL ở RECONCILING / CLOSING / UPDATING_PROTECTION (6A.8)
    position_size: "2.14"
    avg_price: "2393.63"
    pending_entries: []
    sl: {plan_type: pos_loss, client_oid: "gsc1-K7Q2M9XA-EL-SL-0", trigger: "2359.09", trigger_type: mark_price}
    tp: [{role: T1, size: "1.07", trigger: "2397.33", filled: "0"}, {role: T2, size: "1.07", trigger: "2398.53", filled: "0"}]
    mark: "2385.62"
    equity_frozen: "506.53"
    snapshot_at: 2026-10-20T10:19:38+07:00
  tolerances: {mark_drift_pct: "0.3000", equity_drift_pct: "1.0000", reconcile_window_s: 120}
  prior_unknown_op: null  # {op_id, client_oid, qty} nếu leg vừa được gỡ khoá UNRESOLVED_CLOSE bằng `ops clear` mà X vẫn chưa xác định; preview in tổng có thể đóng = close_qty + qty (6A.8)
  expected_after:
    position_size: "1.50"
    protection: {sl_count: 1, plan_type: pos_loss, trigger: "2359.09", covers: position}   # chỉ khi position_size > 0; sl_policy none → sl_count: 0
    tp_rule: active_no_t1_fill   # 6A.5 dòng 1; size thật tính lại ở UPDATING_PROTECTION
    tp_sizes_if_full_fill: ["0.75", "0.75"]
    liq_one_leg: "2058.84"
    liq_worst: "2058.84"
    wcl: "61.01"
    realized_est: "-6.35"
    daily_counter_after: "-19.09"
  steps: [RECONCILING, CANCELLING_ENTRIES, CLOSING, UPDATING_PROTECTION]
  client_oids: {close: "gsc1-K7Q2M9XD-EL-X1-0"}
content_hash: 5d20b7…
```
`kind: entry_adjust` dùng cùng khối (tên `entry_adjust`) nhưng **không có** `close_qty`, `exec_mode`, `qty_source`, `entry_policy`, `tp_actions`; `entry_actions` phải có ≥ 1 `cancel` và được chọn lớp; `steps: [RECONCILING, CANCELLING_ENTRIES]`. Ví dụ 6A.7(B): `entry_actions: [{idx: 4, client_oid: "gsc1-K7Q2M9XA-EL-E4-0", price: "2385.62", qty: "0.43", action: cancel}]`, `expected_after: {position_size: "1.71", liq_worst: "2099.79", wcl: "65.76"}`. Kiểm khi tạo `kind: reduce` ở P1: `entry_policy = cancel_all` và `entry_actions` khớp đúng tập lớp chờ của leg (mọi lớp, đều `cancel`), nếu không → từ chối.



---

## 6. Sửa khi thang đang chạy [→ SPEC 1.5 "không đổi tham số tại chỗ", 5.3; quyết định của chủ 2026-10-20]

### 6.1 Phạm vi

Được sửa **tự do trong trần hồ sơ**: thêm/bớt/dời/đổi size các **lớp chưa khớp**, đổi TP1/TP2/`tp1_fraction`, đổi SL (gần hơn hoặc xa hơn – xa hơn có điều kiện, §6.3), đổi `max_loss`/`budget` trong trần, đóng toàn bộ (`ladder close`). Đóng **một phần** chỉ qua `reduce` (§6A, cùng executor và cổng `REDUCE_SL_MODE`).
Không sửa: symbol, chiều, lớp đã khớp (giá/size là sự thật của sàn), số lớp tổng (đã khớp + chưa khớp) vượt giới hạn của chế độ (Wide 5, Scalp 12), khoảng cách giữa mọi lớp kề (kể cả giá khớp thật) dưới mức tối thiểu của chế độ (Wide 1.0%, Scalp 0.15%), hằng cứng. Kiểm bằng R27w/R27s theo `mode` (§2.5).
Trạng thái `TP1_DONE`: chỉ sửa TP2, SL, đóng; **không thêm entry** (giữ quy tắc "ngừng DCA sau TP1" đã backtest – xem câu hỏi C8).

Lệnh: `ladder edit <root> [các cờ như plan edit, áp cho lớp chưa khớp] [--sl PRICE|be] [--add-layer PRICE[:SIZE]]... [--size IDX=QTY]...` → tạo phiên bản `kind: running_edit` (vd `7Q2X.v3`) + diff → `ladder apply <ref> --confirm --hash <h>`. `ladder close <root> --confirm` = đóng **100%** bằng `close-positions` (holdSide), không có `--pct`. Mọi đóng một phần (kể cả vì thanh lý) dùng `reduce` – market ở P1, tắt tới khi D26 đạt; chỉ huỷ lớp chờ dùng `entries` – §6A. Cùng TTL 10 phút, cùng R1–R30 (phần áp dụng).

### 6.2 Bất biến cứng (mọi lúc, kể cả giữa các bước áp dụng)

Phạm vi: I1 và I2 là bất biến của chế độ **Kiểm soát**. Leg Nonstop: §6B.5 (không SL → không áp; có SL đã duyệt → I1n).

- **(I1) Luôn có SL trên sàn**: mọi leg Kiểm soát có vị thế có đúng 1 `pos_loss` (mark price). Không bao giờ huỷ-rồi-đặt; không có khoảng hở khi thay.
- **(I2) Lỗ xấu nhất ≤ ngân sách**: sau sửa, `WCL ≤ L_run` và R9/R10/R14/R15/R16 (toàn tài khoản) PASS.

### 6.3 Lỗ xấu nhất (WCL) và quy tắc SL

Với vị thế thật (Q_f lớp đã khớp ở giá khớp thật) + mọi lớp chưa khớp còn lại (size **thật** đã làm tròn), giả định tất cả khớp rồi chạm SL:

`WCL(SL) = sg·(C_all − Q_all·SL) + m·C_all + t·Q_all·SL + max(0, −realized_leg)`

(long: `C_all − Q_all·SL`; short: `Q_all·SL − C_all`; `C_all = Σ q·P`; `realized_leg` = PnL đã thực hiện của leg – lãi đã chốt **không** dùng làm đệm; Scalp cộng thêm `Q_all·SL·0.003`.)

`L_run = min(max_loss của phiên bản, s × E_wide_now)` (E đóng băng lúc tạo phiên bản sửa).

- SL **mặc định giữ nguyên**. Nếu `WCL(SL hiện tại) > L_run` → SL **tự động dời gần lại** tới giá nhỏ nhất (long: giá cao nhất cần thiết) sao cho `WCL = L_run` (làm tròn theo 4.9). Ví dụ: thêm/dồn lớp ⇒ SL tự kéo gần.
- **SL xa hơn chỉ khi người dùng yêu cầu rõ** và `WCL(SL mới) ≤ L_run` (vd sau khi bớt lớp/giảm size). Công cụ không bao giờ tự dời SL xa ra. Đây là đánh đổi có chủ ý: dời xa = giữ lỗ lâu hơn, nhưng tổng lỗ vẫn bị chặn bởi ngân sách.
- Ngoại lệ ngân sách cũ: nếu thang đang vượt `L_run` (vd E giảm) thì sửa **không làm tăng WCL** (đổi TP, huỷ lớp, dời SL gần) vẫn được; sửa làm tăng WCL phải đưa về ≤ `L_run`.
- SL mới phải nằm đúng phía so với mark hiện tại (long: SL < mark − 0.1%); nếu không → từ chối, gợi ý `ladder close` (100%).
- Mọi lớp chưa khớp nằm ngoài SL mới (hoặc cách SL < khoảng cách tối thiểu của chế độ: Wide 1% theo R13, Scalp `sl_gap`) bị huỷ trong cùng phiên bản.

Ví dụ (Cân bằng ETH long v1, đã khớp L1 2400.00 & L2 2364.00, mỗi lớp 0.03; SL 2174.58; `L_run` = 26.235; trần notional 393.53):

| Sửa | Notional | WCL tại SL cũ | Kết quả |
|---|---|---|---|
| Không sửa | 349.36 | 23.44 | – |
| Dồn lớp 3–5 cách 1% (2340.36 / 2316.95 / 2293.78), lớp 3 → 0.04 | 374.86 | **27.21 > 26.235** | SL tự dời gần: **2180.67** (WCL 26.23) |
| Huỷ lớp 5 | 281.59 | 20.85 | SL được phép xa tới **2129.66** (WCL 26.23); anh yêu cầu 2150.00 → WCL 23.80 → OK |
| Lớp 3 và 4 → 0.05 / 0.04 | 418.87 | – | **FAIL R27** (vượt trần notional 393.53) |

### 6.4 Thứ tự áp dụng an toàn (`ladder apply`)

Tách diff thành các bước, chạy tuần tự dưới khoá trạng thái (watcher tạm dừng re-price TP của leg, vẫn xử lý SL), **đọc lại trạng thái sàn trước mỗi bước**:

1. `SL_TIGHTEN` (nếu SL mới gần hơn) – trước mọi thứ.
2. `CANCEL_ENTRY` (huỷ/dời: phần huỷ của lệnh cũ) – chờ xác nhận `cancelled` hoặc phát hiện đã `filled`.
3. Tính lại WCL từ trạng thái thật. Nếu lệnh định huỷ đã khớp → WCL có thể khác: nếu > L_run với SL hiện tại → tự `SL_TIGHTEN` tới mức ngân sách (luôn được phép, chỉ giảm rủi ro), các bước còn lại được đánh giá lại; nếu không còn khớp phiên bản đã duyệt → dừng, `applied_partial`, báo và đề xuất phiên bản mới.
4. `TP_UPDATE` (huỷ/đặt lại profit_plan theo giá TB thật).
5. `PLACE_ENTRY` (lớp mới/dời/đổi size) – chỉ khi `WCL(trạng thái sau bước) ≤ L_run` với SL **đang có trên sàn**.
6. `SL_LOOSEN` (nếu SL mới xa hơn) – **cuối cùng**, chỉ khi WCL tính từ trạng thái thật sau bước 2–5 ≤ L_run.

Cơ chế thay SL (I1):
- Chính: `modify-tpsl-order` trên chính `pos_loss` hiện có (`size:""`); sàn giữ trigger cũ cho tới khi chấp nhận trigger mới. Xác nhận qua `orders-plan-pending` (±1 tick).
- Nếu modify không dùng được: D20 xác định sàn có cho 2 `pos_loss` cùng lúc không. Có → **đặt mới trước, xác nhận, rồi huỷ cũ**. Không (đặt mới tự thay cũ) → lệnh đặt mới chính là phép thay nguyên tử. **Cấm** huỷ trước rồi đặt.
- Thất bại: modify/đặt mới bị từ chối → SL cũ vẫn còn (không hở). `SL_TIGHTEN` thất bại → huỷ toàn bộ phiên bản trước khi làm bước rủi ro nào, báo. `SL_LOOSEN` thất bại → giữ SL chặt hơn (an toàn), phiên bản `applied_partial`. Sau bất kỳ lỗi nào, watcher đối soát: SL trên sàn phải = `sl_price` của **phiên bản đang chạy cuối cùng đã áp đủ**; lệch → sửa về giá đó (chỉ gần hơn hoặc bằng, không bao giờ xa hơn giá đã xác nhận).
- Phát hiện leg `sl_required` (Kiểm soát) hoặc leg Nonstop có SL đã duyệt mà không có SL > 1 vòng → KHẨN + `on_sl_failure` (SPEC Q4; Nonstop: chỉ KHẨN + đặt lại SL đã duyệt, không `close_leg` – §6B.5). Leg Nonstop không có SL: không làm gì.
- Bị ngắt giữa chừng (crash, mất mạng) → phục hồi theo §6.5.

### 6.5 Nhật ký bước & phục hồi khi bị ngắt giữa chừng (`applied_partial`)

Áp cho `execute`, `ladder apply`, `reduce apply`, `entries apply`.

- Bảng `op_journal(op_id PK, version_id, leg_id, kind, step_no, step_kind, call_kind[place|cancel|modify], risk[reduce|increase], client_oid, intent_json, status[planned|sent|confirmed|failed|skipped|rolled_back|unknown], exch_ref, created_at, updated_at)`. Mọi bước được ghi `planned` kèm clientOid xác định (`{prefix}-{version_id}-{leg}-{role}{idx}-{rev}`) **trước khi gửi**, chuyển `sent` ngay trước HTTP, `confirmed` sau khi xác minh trên sàn; cập nhật nguyên tử cùng trạng thái leg.
- Phân loại rủi ro: **giảm rủi ro** = huỷ entry, SL_TIGHTEN, đóng vị thế, đặt bảo vệ, cập nhật TP; **tăng rủi ro** = PLACE_ENTRY (kể cả dời/đổi size), SL_LOOSEN, đặt entry ở `execute`.
- Phân loại lời gọi: `cancel` và `modify` (đặt trigger về đúng giá trị đích) là **idempotent** → được gửi lại; `place` (place-order, place-tpsl-order) **không** idempotent → kết quả phân loại `FOUND` / `REJECTED` / `VERIFIED_NOT_RECEIVED` / `UNKNOWN` như 6A.8; `UNKNOWN` không bao giờ được coi là chưa gửi.
- Khởi động lại / mất kết nối khi op chưa kết thúc → leg vào `RECOVERING` (chặn mọi op khác của leg), reconcile REST đầy đủ; mỗi bước `sent` chưa `confirmed` → truy vấn theo clientOid (`order/detail`, `orders-plan-pending`, `fills`) để phân loại (Q-9).
- Quy tắc:
  1. Bước `cancel`/`modify` giảm rủi ro (huỷ entry, SL_TIGHTEN): **hoàn tất tiến** (gửi lại được, ≤ 2 lần, truy vấn trước).
  2. Bước `place` giảm rủi ro (đóng vị thế, đặt TP, đặt `pos_loss` của execute): `FOUND` → tiếp tục; `UNKNOWN` → `PENDING_RECONCILE` (6A.8), **không gửi lại**; chỉ gửi lại khi `VERIFIED_NOT_RECEIVED` và `now < expires_at` của phiên bản (cùng clientOid). Ngoại lệ duy nhất: watcher đặt `pos_loss` khi đọc `orders-plan-pending` thấy leg **cần SL** (Kiểm soát, hoặc Nonstop có SL đã duyệt) có vị thế mà không có SL (I1/I1n) – thiếu SL nguy hiểm hơn thừa SL; nếu sau đó thấy 2 `pos_loss` (tuỳ kết quả D20) thì huỷ bản thừa sau khi bản còn lại đã xác nhận.
  3. Bước tăng rủi ro chưa `confirmed`: **không bao giờ gửi lại**. Nếu thực tế đã tồn tại trên sàn: kiểm I2 với SL thật – WCL ≤ L_run → giữ và ghi nhận; ngược lại huỷ entry đó (nếu chưa khớp) hoặc SL_TIGHTEN về mức ngân sách (nếu đã khớp).
  4. SL_LOOSEN chưa `confirmed` → không gửi lại; SL giữ ở mức chặt hơn đã xác nhận.
  5. `execute` dở: huỷ mọi entry chưa khớp của plan (như SPEC 7.4(b)), giữ SL nếu đã có vị thế, không đặt nốt lớp thiếu.
  6. Kết thúc phục hồi: phiên bản → `applied_partial` (hoặc `aborted` nếu chưa có ghi nào) với `observed_state` (giá/size thật từng lớp, SL thật, TP thật, vị thế, các op `unknown`) lưu DB; mọi sửa tiếp theo tính diff **từ `observed_state`**; phần chưa làm chỉ được tiếp tục bằng **phiên bản mới được duyệt**.
  7. `expires_at` của phiên bản là hạn duy nhất cho quyền gửi **lệnh mới** (lệnh đóng mới, kể cả gửi lại; mọi bước tăng rủi ro); phục hồi không gia hạn. Đối soát, hoàn tất huỷ đã bắt đầu, bảo vệ SL/TP và dọn lệnh cho thao tác **đã gửi trước hạn** vẫn chạy sau hạn theo quy tắc đã duyệt (6A.8).
- Gửi lại tối đa `HARD_REDUCE_MAX_RESEND = 2` lần, chỉ cho lời gọi idempotent hoặc `VERIFIED_NOT_RECEIVED`; vượt → `FAILED_SAFE` + CAO. Bất biến I1 do watcher giữ song song suốt quá trình (thiếu SL → đặt ngay).


---

## 6A. Giảm vị thế chủ động để đẩy giá thanh lý (`reduce`) [mới; áp cho cả Wide và Scalp]

> Phạm vi: §6A viết cho chế độ **Kiểm soát**. Leg Nonstop: không có bản dựng sẵn; reduce do anh tự gọi dùng cùng executor và cùng cổng, số SL kỳ vọng theo §6B.5.

> Ý của chủ: "Nhiều khi đóng 1 phần vị thế không phải vì có lãi, mà vì muốn giảm volume vị thế để giá thanh lý xa hơn." `reduce` là thao tác **chỉ đóng** (close-only), làm được bất kể lãi/lỗ, không bao giờ mở thêm vị thế.

### 6A.0 Phân pha, cờ tính năng và mọi đường đóng một phần (bắt buộc đọc trước)

| Khả năng | Pha | Cờ | Điều kiện bật |
|---|---|---|---|
| `entry_adjust` (chỉ huỷ lớp chờ, **không** gửi lệnh đóng) | P1 | luôn bật | U45, D31 |
| `reduce` **market** (`--pct`/`--qty`, **luôn huỷ mọi lớp chờ của leg trước khi đóng**) | P1 | `REDUCE_SL_MODE` (hằng trong mã) = `position_persist` | **chỉ khi D26 đạt** (+ D28); ghi `docs/decisions.md`; đổi hằng = đổi mã + review |
| `reduce` **maker** (post-only + timeout), gồm `scalp scaleout` | P1b | `reduce_maker_enabled` (mặc định false) | reduce market đã bật + U41, D27 |
| Giữ lớp chờ / huỷ một phần lớp chờ trong `reduce` | pha sau (P2) | không có ở P1 | thiết kế riêng + test riêng |
| `--target-liq-distance` (tự tìm khối lượng) | P2 | `reduce_target_enabled` (mặc định false) | U39 đạt + 4 tuần dùng reduce market không sự cố |
| `preplace_guard` (đặt trước SL theo size dự kiến) | **ngoài phạm vi – tắt** | không có (giá trị này bị xoá khỏi `REDUCE_SL_MODE`) | chỉ xét lại khi có bản thiết kế bảo vệ **size thật** ở **mọi** bước (close khớp một phần, close bị từ chối, fill trễ) được viết và kiểm chứng riêng |

Vì sao loại `preplace_guard` khỏi P1: lệnh bảo vệ G có size cố định = `Q_after` **dự kiến**. Ví dụ vị thế 2.14, định đóng 0.64 → G = 1.50; nếu close chỉ khớp 0.20 thì còn 1.94 mà G chỉ che 1.50 → **0.44 không có SL** (đúng tình huống `pos_loss` đã mất, là lý do dùng G); lớp chờ còn giữ mà khớp thêm thì phần hở lớn hơn. D29 cũ không chứng minh được U47 trong các trường hợp này, nên không có cách bật nào ở P1.

- `REDUCE_SL_MODE ∈ {disabled, position_persist}`, **mặc định `disabled` trong mã**: cấu hình/biến môi trường không bật được. Khi `disabled`, lệnh `reduce` trả: "Tính năng giảm vị thế một phần đang tắt cho tới khi Demo D26 chứng minh SL vẫn còn và bao đúng phần còn lại sau khi đóng một phần. Hiện chỉ dùng được: `entries` (huỷ lớp chờ), `ladder close` (đóng hẳn 100%), `kill --close-positions`."
- `reduce` không chặn go-live P1; P1 có thể chạy live với reduce tắt.

**Mọi đường đóng một phần chủ động đi qua cùng executor 6A.8 và cùng cổng `REDUCE_SL_MODE`.** Danh sách đầy đủ các đường đóng trong công cụ:

| Đường | Một phần? | Quy tắc (r3) |
|---|---|---|
| `reduce apply` | có | executor 6A.8; cổng `position_persist` |
| `ladder close <root> --confirm` | **không** – luôn 100% | **thủ tục thường §6A.10**: huỷ mọi lớp chờ + TP → bắt fill trễ → `close-positions` (holdSide) size thật → xác nhận size 0 → dọn SL/lệnh sót (D28, D39, U73); không có `--pct`. Đóng một phần = `reduce` |
| `scalp scaleout` (SPEC 4.12.3, limit post-only một phần) | có | = reduce maker (P1b) qua executor 6A.8, cùng `entry_policy: cancel_all` (bỏ tuỳ chọn giữ DCA của SPEC 4.12.3); bị từ chối khi reduce hoặc maker tắt |
| `kill --close-positions`, `on_sl_failure: close_leg` (SPEC 8.2(3)), `fail_execute` của `pos_loss`/BE (§9.4), Q-7 khi SL/BE đã vượt trigger | không – luôn 100% | **thủ tục khẩn §6A.10**: `close-positions` (holdSide) ngay → huỷ mọi lớp chờ + TP → vòng kiểm tới khi size 0 và 0 entry; test U31, U32, U74, D23, D28, D39 |
| Q-7 khi **TP** đã vượt trigger lúc đặt/đặt lại TP | (cũ: đóng ngay phần TP bằng market) | **Không đóng một phần.** Không gửi lệnh đóng; bỏ qua TP đó + CAO "TP{n} chưa đặt được vì giá đã vượt; SL vẫn trên sàn"; watcher thử đặt lại khi mark quay về phía hợp lệ (§9.7 Q-7) |
| TP1/TP2 `profit_plan` do sàn kích hoạt | do sàn | không phải đóng chủ động; SL sau TP do D9/D18 kiểm (SPEC 4.5, §9.4) |
| Liq khẩn, DRIFT, vị thế/lệnh tay | – | **không** có đóng tự động một phần; chỉ cảnh báo + bản dựng sẵn chờ duyệt |

Không có đường đóng một phần nào khác. U48 kiểm bằng test + quét mã: mọi lời gọi `place-order tradeSide=close` có `size` < vị thế chỉ xuất phát từ executor 6A.8.

### 6A.1 Lệnh (P1)

```
reduce <root> --pct N | --qty Q                        # market-only; luôn huỷ MỌI lớp chờ của leg trước khi đóng
reduce show <ref> | reduce apply <ref> --confirm --hash H | reduce status <op_id>
entries <root> --cancel IDX[,IDX...] | --cancel-all    # entry_adjust (chỉ huỷ, được chọn lớp)
entries apply <ref> --confirm --hash H
ladder close <root> --confirm                          # đóng 100% (close-positions holdSide); không có --pct
```
- `--exec maker` (P1b), `--target-liq-distance X` (P2), `--entries keep` / `--cancel-idx` (pha sau) bị từ chối với thông báo pha/cờ.
- `shrink` (thu size lớp chờ) **không** thuộc reduce vì phải đặt lại lệnh mở (vi phạm close-only): dùng `ladder edit --size IDX=QTY` (luồng §6), và chỉ có tác dụng nếu không reduce sau đó (reduce P1 huỷ mọi lớp chờ).
- Lệnh đóng: `place-order`, `orderType=market`, `tradeSide=close`, hedge mode SPEC 7.3 (**đóng long = `side=buy`; đóng short = `side=sell`**; không gửi `reduceOnly`), `productType=USDT-FUTURES`, `marginMode=crossed`, `size = close_qty` floor theo lot, `clientOid` role `X`. 0 < `close_qty` < vị thế: phần còn lại ≥ `minTradeNum`. `close_qty` = vị thế → không phải reduce: dùng `ladder close`.
- **Nhánh chỉ-huỷ**: nếu khối lượng giảm giải ra = 0 (vd `--qty 0`, hoặc phương án chỉ cần huỷ lớp) → công cụ **không** tạo `kind: reduce`; tạo `kind: entry_adjust` và nói rõ "không gửi lệnh đóng". Không có đường code nào gửi lệnh close với size 0.
- Được phép khi đang khoá (ngày/tuần/DD/chuỗi stop/xô/bộ đếm UNKNOWN §8.4), khi `kill` ở `PROTECT_ONLY`, khi hồ sơ `pending`. Không được khi leg đang `RECONCILING`/`RECOVERING`/`PENDING_RECONCILE`, có khoá `UNRESOLVED_CLOSE` (6A.8), có `DRIFT` (Q-10), hoặc đang có một op khác trên leg (khoá op theo leg).

### 6A.2 Mô hình thanh lý dùng trong preview [mở rộng SPEC 4.8]

- Điều kiện thanh lý cross: `W + Σ uPnL(P) ≤ Σ mmr_j·|Q_j|·P_j`, `W` = số dư ví sau mọi phí đã trả, mark price, `mmr = max(bậc MMR từ API theo notional, mmr_floor cấu hình)` (ETH 0.5%, BTC 0.4% ở ví dụ).
- **Một leg**: công thức đóng SPEC 4.8(a) với W thật hiện tại – chỉ tham khảo.
- **Xấu nhất toàn tài khoản (con số quyết định)**: mọi giá cùng chiều leg đang xét di chuyển bất lợi cùng x% từ mark (BTC/ETH tương quan ≈ 1); **lớp entry chờ cùng chiều được coi là khớp tại giá của nó khi giá đi qua** (có phí maker); leg ngược chiều: tính MM, **không** tính lãi (m9); SL **không** được giả định là chạy. Bisection → `liq_dist_worst` và giá liq tương ứng.
- Preview **luôn** in `liq_dist_worst` hiện tại (có lớp chờ) và sau thao tác (reduce P1: không còn lớp chờ của leg) để tránh "giảm ảo". Mô hình vẫn tính được trường hợp giữ lớp (dùng cho `entry_adjust` chọn lớp và cho pha sau).

### 6A.3 Thực thi

- **P1: chỉ market.** Taker 0.06%; trượt giá ước tính `close_qty × mark × 0.1%` in trong preview (cấu hình).
- P1b (sau khi bật cờ): `--exec auto` = market khi `liq_dist_worst` < ngưỡng khẩn (5%, sàn cứng 3%), ngược lại maker post-only ở giá tốt nhất phía đóng (đóng long: `askPr`; đóng short: `bidPr`), đặt lại 1 lần nếu bị từ chối, timeout 60 s → huỷ phần còn lại và hỏi (market / đặt lại / dừng); rơi dưới khẩn khi đang chờ → KHẨN + đề xuất market, không tự chuyển. Limit close luôn < 100% vị thế (N4).

### 6A.4 Lớp DCA chưa khớp

- **P1 `reduce`: luôn huỷ mọi lớp chờ của leg** (`entry_policy: cancel_all`) trước khi đóng. Không có `keep` hay huỷ một phần trong reduce ở P1 (pha sau). Hệ quả: sau khi huỷ xong, vị thế của leg chỉ còn có thể tăng do một fill đang bay đúng lúc huỷ (khi đó op dừng `FAILED_SAFE`, 6A.8); `position_persist` bao size thật.
- `entry_adjust` vẫn chọn được lớp (mặc định huỷ lớp sâu nhất trước) vì không có lệnh đóng.
- Đề xuất: nếu huỷ lớp (một phần hoặc hết) đã đạt mục tiêu (ngưỡng cảnh báo của bậc + 2 điểm, 6A.6) → `entry_adjust`; nếu không → `reduce` (huỷ hết lớp chờ + đóng).
- Huỷ lớp và huỷ TP luôn chạy **trước** lệnh đóng (state machine 6A.8).

### 6A.5 Bảo vệ SL và TP khi giảm

Cam kết: **khi leg còn vị thế, không có đường nào để phần vị thế còn lại không có SL trên sàn**, kể cả trong lúc chuyển tiếp. "Đặt lại SL sau khi đóng" **không** phải là cơ chế hợp lệ.

**Chế độ duy nhất ở P1: `position_persist`** (chỉ khi D26 đạt). D26 phải chứng minh trên Demo hedge mode rằng sau một lệnh close một phần, `pos_loss` cấp vị thế (a) vẫn tồn tại, (b) trigger không đổi, (c) khi kích hoạt đóng **đúng toàn bộ phần còn lại**. Khi đó reduce không đụng SL; bước `UPDATING_PROTECTION` chỉ **xác minh**. Nếu runtime vẫn phát hiện SL mất (trái với D26) → sự cố sàn: watcher đặt `pos_loss` ngay (quy tắc I1 chung), KHẨN, và **tự chuyển `REDUCE_SL_MODE` hiệu lực về `disabled`** (cờ runtime ghi DB; chỉ mở lại bằng lệnh có xác nhận sau khi điều tra).

Nếu D26 FAIL: reduce một phần giữ `disabled` (C24). Không có chế độ thay thế ở P1 (6A.0).

**Điều kiện kết thúc về SL**: (leg Nonstop không có SL: 0 SL, §6B.5) nếu còn vị thế (`Q_after > 0`) → đúng 1 `pos_loss` cấp vị thế, trigger = SL của phiên bản (±1 tick). Nếu `Q_after = 0` → điều kiện "1 SL" **không áp dụng**: dọn mọi lệnh còn sót của leg, không đặt SL/TP mới.

**TP sau khi đóng – theo trạng thái leg đọc từ sàn, không theo tỉ lệ cố định.** TP cũ của leg đã bị huỷ ở bước `CANCELLING_ENTRIES` (TP không phải bảo vệ; huỷ trước để không còn TP lớn hơn vị thế sau khi đóng). Ở `UPDATING_PROTECTION`, công cụ đọc `single-position`, các fill theo clientOid T1/T2 của leg và trạng thái leg, rồi áp:

| Trạng thái sau khi đóng | TP đặt lại | SL |
|---|---|---|
| `ACTIVE`, T1 **chưa khớp gì** | `qT1 = floor_lot(f1 · Q_after)`, `qT2 = Q_after − qT1`; nếu `qT1 < minTradeNum` → không đặt T1, `qT2 = Q_after` | xác minh pos_loss |
| `ACTIVE`, T1 **đã khớp một phần** `x` (trước khi bị huỷ) | nghĩa vụ TP1 còn lại `r = max(0, floor_lot(f1 · (Q_after + x)) − x)`; `qT1 = r` (nếu `r < minTradeNum` → 0), `qT2 = Q_after − qT1`. Không tự chuyển `TP1_DONE`, không tự dời SL về BE (BE chỉ theo sự kiện T1 executed – Q-5); CAO "TP1 đã khớp một phần {x}" | xác minh pos_loss |
| `TP1_DONE` (SL đã ở BE) | không đặt T1; `qT2 = Q_after` | xác minh pos_loss ở BE |
| `PROTECT_ONLY` (`kill`) | **không** tạo TP | xác minh pos_loss |
| `Q_after = 0` (SL/TP kích hoạt đồng thời, hoặc đóng nhiều hơn dự định) | không đặt; huỷ mọi TP/entry còn sót của leg; leg → `CLOSED` | không đặt mới; huỷ plan còn sót |

Lỗi đặt TP → CAO, thử lại theo quy tắc bước `place` (§6.5: kết quả không xác định thì không gửi lại); TP thiếu không chặn `DONE`.

### 6A.6 Ngân sách, bộ đếm, cảnh báo

- **WCL mới** = lỗ tại SL của phần còn lại + `max(0, −realized_leg)` (§6.3; reduce P1 không còn lớp chờ). Lỗ chốt ra **tiêu ngân sách thang/xô**; lãi không làm đệm. Sổ xô ghi theo sự kiện (§3.1).
- Khoá ngày/tuần/DD: theo định nghĩa duy nhất §8.4 (E theo mark) → reduce chỉ làm bộ đếm xấu thêm **phí đóng + trượt** (lỗ đã nằm trong uPnL). Preview in "bộ đếm ngày: −X → −(X + phí) / ngưỡng −Y". Chạm ngưỡng → khoá kích hoạt, reduce vẫn chạy xong.
- Chuỗi stop (R20): reduce không tính là SL. Journal: một dòng mỗi reduce/entry_adjust (`close_reason=reduce`, liq trước/sau).
- **Cảnh báo thanh lý** (watcher, mỗi 60 s + theo mark tối đa 1 lần/5 s): ngưỡng theo bậc 30% / 20% / 10% (Thận trọng / Cân bằng / Mạo hiểm), khẩn 5%. Dưới ngưỡng → CAO + bảng phương án cố định (entry_adjust nếu có lớp chờ; reduce 20/30/50%) và **dựng sẵn** một phiên bản: `entry_adjust` nếu riêng huỷ lớp đạt ngưỡng + 2 điểm, nếu không thì reduce **30%** (huỷ mọi lớp chờ; P1 không tự giải khối lượng; P2 thay bằng `--target-liq-distance`). **Không bao giờ tự thực thi** (ngoại lệ duy nhất: các đường đóng 100% ở bảng 6A.0). Chống lặp: báo lại khi xấu thêm ≥ 2 điểm hoặc rơi lại sau khi hồi > ngưỡng + 2; dưới khẩn → KHẨN mỗi 5 phút. Khi `REDUCE_SL_MODE = disabled`, bản dựng sẵn chỉ có thể là `entry_adjust` hoặc `ladder close` (100%).
- Quan hệ với quy tắc Scalp "liq ≥ 3% khi thêm lớp" (SPEC 4.12.3c): kiểm tra thêm lớp/mở plan dùng `max(3%, ngưỡng cảnh báo bậc)`.

### 6A.7 Ví dụ số (E = 524.7, ETH mmr 0.5%, không có vị thế khác; script `/workspace/scratch/spec_v2/reduce.py`)

Thang Scalp 4 lớp theo SPEC 4.12.4 đã sửa (first 3×, mult 0.87, d 0.2%, SL 15% E): lớp 2400.00 / 2395.20 / 2390.40 / 2385.62, size 0.65 / 0.57 / 0.49 / 0.43, **SL 2359.09**. (Cấu hình này vượt trần Scalp của mọi bậc §2.2 – dùng làm ví dụ vì liq gần.)

**(A) Giá về lớp 4, mark 2385.62, khớp đủ 4 lớp**: Q 2.14 ETH, TB 2393.63, notional 5105.23 (10.08× E theo mark, E_mark 506.53). Liq ước tính **2159.72 = cách mark 9.47%** (một leg = toàn TK). WCL 77.98. Không còn lớp chờ → chỉ có `reduce`. Trạng thái `ACTIVE`, T1 chưa khớp → TP sau giảm theo dòng 1 bảng 6A.5.

| Giảm (market) | Khối lượng | Realized (gồm phí) | Liq mới (cách mark) | WCL mới | Notional còn | TP1 / TP2 sau | Bộ đếm ngày đổi thêm |
|---|---|---|---|---|---|---|---|
| 20% | 0.42 | −4.17 | 2101.99 (11.89%) | 66.84 | 4103.27 (8.10×) | 0.86 / 0.86 | −0.60 (phí) |
| **30%** | 0.64 | **−6.35** | **2058.84 (13.70%)** | **61.01** | 3578.43 (7.06×) | 0.75 / 0.75 | −0.92 |
| **50%** | 1.07 | **−10.62** | **1923.28 (19.38%)** | **49.61** | 2552.61 (5.04×) | 0.53 / 0.54 | −1.53 |

Ví dụ khớp một phần: định đóng 0.64 nhưng lệnh market chỉ khớp 0.20 (kết thúc) → `Q_after` thật = 1.94, `pos_loss` bao 1.94 (position_persist), TP1/TP2 = 0.97 / 0.97; phần 0.44 chưa đóng **không** được gửi lại tự động – cần phiên bản mới.

- (P1b) 30% bằng maker: realized −5.74, phí 0.31 thay vì 0.92 – có thể không khớp.
- (P2) `--target-liq-distance 10` → 0.11 ETH (5.1%) → 10.01%; `12` → 0.44 ETH (20.6%) → 12.03%.
- Bậc Mạo hiểm (cảnh báo 10%): watcher báo ở 9.47% và dựng sẵn reduce 30% (→ 13.70%).

**(B) Giá về lớp 3, mark 2390.40, khớp L1–L3 (Q 1.71, TB 2395.65), L4 0.43 còn chờ**: liq một leg 2099.79 (12.16%) nhưng **xấu nhất có L4 khớp: 2159.72 (9.65%)**.

| Phương án (P1) | Loại | Lệnh đóng gửi đi | Liq xấu nhất (cách mark) | WCL |
|---|---|---|---|---|
| **Chỉ huỷ L4** | **`entry_adjust`** | **không có** | **2099.79 (12.16%)** | **65.76** |
| Giảm 30% (0.51, realized −3.65) – reduce luôn huỷ L4 | reduce | 0.51 market | 1971.78 (17.51%) | 49.80 |
| Giảm 50% (0.85, realized −6.09) – reduce luôn huỷ L4 | reduce | 0.85 market | 24.61% | 39.16 |

Chỉ để kiểm mô hình liq (U38), **không có ở P1**: giảm 30% giữ L4 → 12.81% / WCL 62.02; thu L4 → 0.30 rồi giảm 30% giữ L4 → 13.95% / 58.32; giảm 50% giữ L4 → 16.30% / 51.38.

Với mục tiêu 10% (ngưỡng Mạo hiểm): huỷ L4 đã cho 12.16% ≥ 10% + 2 → watcher dựng sẵn **`entry_adjust` (huỷ L4), không có lệnh đóng**.

**Wide (ngắn gọn)**: Cân bằng, ETH long đủ 5 lớp (0.15 @ TB 2329.07, mark 2259.20) + BTC long đủ 5 lớp (mark 76857.4) + 2 short mỗi bên 1 lớp: liq xấu nhất cách mark **~71.7%**. Giảm 0.07 ETH (~50%) realized −5.02 → ~92.8%, WCL ETH-L 23.44 → 17.52. Preview Wide PHẢI ghi: "Thanh lý đang rất xa; giảm chủ yếu làm giảm lỗ nếu chạm SL, và sẽ chốt lỗ {x} USDT ngay."

### 6A.8 Vòng đời reduce (P1, market-only) – máy trạng thái

```
PROPOSED ─apply(hash ok, now < expires_at)─► APPROVED ─► RECONCILING ─► CANCELLING_ENTRIES ─► CLOSING ─► UPDATING_PROTECTION ─► DONE
   │hết hạn/superseded              │lệch/sai chế độ TK  │lớp đã khớp/lỗi huỷ   │từ chối rõ  │kết quả không xác định
   ▼                                ▼                    ▼                      ▼            ▼
 EXPIRED                        ABORTED (0 ghi)      FAILED_SAFE            FAILED_SAFE   PENDING_RECONCILE ─xác định được─► UPDATING_PROTECTION
                                                                                              └─hết cửa sổ─► FAILED_SAFE (close_unknown)
 khởi động lại khi op chưa kết thúc ─► RECOVERING ─► (tiến tiếp theo quy tắc dưới | PENDING_RECONCILE | FAILED_SAFE)
 entry_adjust: PROPOSED → APPROVED → RECONCILING → CANCELLING_ENTRIES → DONE
```

**Hạn (`expires_at`) – phạm vi**: mỗi phiên bản reduce/entry_adjust có một `expires_at = created_at + 120 s`, nằm trong hash, **bất biến**; duyệt không gia hạn, crash không gia hạn, không có "120 s tính từ lúc duyệt". `expires_at` **chỉ** chấm dứt quyền: (a) duyệt (`apply`); (b) gửi một **lệnh đóng mới** (`place-order` close, kể cả gửi lại sau crash theo `VERIFIED_NOT_RECEIVED`) – kiểm `now < expires_at` ngay trước HTTP; (c) bất kỳ bước tăng rủi ro nào. `expires_at` **không** chặn phần tiếp theo của thao tác **đã gửi trước hạn**: đối soát (`PENDING_RECONCILE`, RECOVERING), hoàn tất huỷ lớp chờ/TP đã bắt đầu (giảm rủi ro, idempotent), `UPDATING_PROTECTION` (đặt lại TP theo bảng 6A.5, xác minh/giữ SL), dọn lệnh sót, đặt lại TP ở `FAILED_SAFE` – các bước này chạy theo đúng quy tắc của phiên bản đã duyệt, kể cả sau hạn (U72).

**Kết quả của một bước `place` (gửi lệnh mới)** được phân loại:
- `FOUND` – sàn trả về lệnh theo clientOid (live/filled/partially filled/cancelled) hoặc response HTTP thành công có `orderId`.
- `REJECTED` – response HTTP có mã lỗi nghiệp vụ rõ ràng (lệnh không được tạo).
- `VERIFIED_NOT_RECEIVED` – **chỉ** một trong hai: (a) journal cho thấy bước còn `planned`, chưa từng chuyển `sent` (crash trước HTTP); (b) cơ chế chống trùng đã kiểm chứng: D32 chứng minh sàn từ chối mọi lệnh trùng clientOid với lệnh đã được nhận (kể cả đã khớp/đã huỷ) trong ≥ 24 h, bằng một mã lỗi xác định, và không bao giờ tạo lệnh thứ hai → khi đó gửi lại **cùng clientOid** là an toàn.
- `UNKNOWN` – mọi trường hợp khác: timeout, mất kết nối, HTTP 5xx, truy vấn lỗi, dữ liệu chậm, hoặc truy vấn "không thấy". **"Không thấy" không bao giờ được coi là "chưa gửi".**

| Chuyển | Điều kiện trước | Gọi sàn | Xác minh | Timeout | Khi lỗi |
|---|---|---|---|---|---|
| PROPOSED → APPROVED | `REDUCE_SL_MODE = position_persist` (trừ entry_adjust); phiên bản mới nhất; `now < expires_at`; lệch mark ≤ 0.3%; hash canonical khớp (§5.4); không có op khác trên leg; leg không DRIFT / PENDING_RECONCILE | – | ghi `op_journal` (op_id, version_id, các bước dự kiến + clientOid) **trước** | – | từ chối, giữ PROPOSED |
| APPROVED → RECONCILING | khoá trạng thái leg; watcher tạm dừng re-price TP leg (vẫn giữ SL) | REST `account` (`productType=USDT-FUTURES`, `marginCoin=USDT`), `single-position`, `orders-pending` (symbol), `orders-plan-pending` (profit_loss), ticker | **chế độ tài khoản**: `posMode = hedge_mode`, `marginMode = crossed`, productType `USDT-FUTURES`, leg có vị thế đúng `holdSide` (long/short) và `marginMode = crossed` ở cấp vị thế; **trạng thái**: size vị thế = snapshot; tập lệnh chờ = snapshot; tập TP = snapshot; số `pos_loss` = số kỳ vọng (Kiểm soát / Nonstop có SL: đúng 1, trigger = snapshot; Nonstop không SL: 0, §6B.5); trạng thái leg (ACTIVE/TP1_DONE/PROTECT_ONLY) = snapshot; mark trong 0.3%; E trong 1%; `close_qty` vẫn hợp lệ; `now < expires_at` | 10 s | bất kỳ lệch nào → `ABORTED` (chưa ghi gì lên sàn), thông báo giá trị thật, gợi ý phiên bản mới |
| → CANCELLING_ENTRIES | RECONCILING đạt | reduce: `cancel-order` **mọi** lớp chờ của leg + `cancel-plan-order` mọi TP (`profit_plan`) của leg, theo clientOid; entry_adjust: chỉ các lớp đã chọn, TP giữ nguyên | `order/detail` = `cancelled`; TP không còn trong `orders-plan-pending`; size vị thế không đổi | 10 s/lệnh; huỷ là idempotent → gửi lại tối đa 2 lần (truy vấn trước) | lớp đã `filled`/khớp một phần → `FAILED_SAFE` (không đóng; giữ các huỷ đã làm; đặt lại TP theo bảng 6A.5 cho size thật; đề xuất phiên bản mới); lỗi khác → `FAILED_SAFE` (cũng đặt lại TP) |
| → CLOSING | SL đúng `sl_policy` của leg (đọc lại, như RECONCILING): `required` / `approved` → `pos_loss` còn trên sàn, trigger = snapshot; `none` (Nonstop không SL) → **0** `pos_loss` (thấy SL lạ → `FAILED_SAFE`, không đóng); `now < expires_at` kiểm ngay trước HTTP | journal `sent` → `place-order` market close `close_qty` (clientOid `X`) | `order/detail?clientOid=X` filled; `single-position` size = trước − filled (± lot) | 10 s | `FOUND` filled đủ → UPDATING_PROTECTION; `FOUND` kết thúc với khớp một phần → ghi thực tế, UPDATING_PROTECTION với size thật, phần chưa đóng **không** gửi lại; `REJECTED` → `FAILED_SAFE` (đặt lại TP); size giảm nhiều hơn (SL/TP đồng thời) → đối soát → UPDATING_PROTECTION (có thể `Q_after = 0`); `UNKNOWN` → **PENDING_RECONCILE, không gửi lại** |
| CLOSING → PENDING_RECONCILE | kết quả `UNKNOWN` | không gửi lệnh mới nào cho leg (watcher vẫn giữ I1: thiếu SL → đặt `pos_loss`) | mỗi 2 s trong `reconcile_window_s` = 120 s: `order/detail?clientOid=X`, `fills` (`GET /api/v2/mix/order/fills`, symbol, từ lúc `sent`), `single-position`, WS `orders`/`fill` | 120 s | xác định được (lệnh X thấy ở bất kỳ trạng thái nào, hoặc fill có orderId của X) → xử lý như `FOUND`; hết cửa sổ vẫn không xác định → `FAILED_SAFE (close_unknown)` + leg giữ **khoá `UNRESOLVED_CLOSE`** (dưới): CAO; **không bao giờ tự gửi lại**; dò nền mỗi 60 s trong 24 h; **không** được tạo/duyệt reduce mới cho leg khi khoá còn. Gửi lại tự động chỉ khi `VERIFIED_NOT_RECEIVED` **và** `now < expires_at` (cùng clientOid) |
| → UPDATING_PROTECTION | close đã xác định | đọc `single-position`, `orders-plan-pending`, fill T1/T2; đặt TP theo bảng 6A.5 (`place-tpsl-order profit_plan`, clientOid rev+1); `Q_after = 0` → huỷ lệnh còn sót | `Q_after > 0`: theo `sl_policy` – `required`/`approved`: đúng 1 SL cấp vị thế, trigger = SL phiên bản (±1 tick); `none`: 0 SL; TP đúng bảng 6A.5 (Nonstop: chỉ khi plan có TP); `Q_after = 0`: không còn lệnh nào của leg | 30 s (chạy cả sau `expires_at`) | thiếu SL khi còn vị thế (chỉ `required`/`approved`) → KHẨN + đặt `pos_loss` ngay + `REDUCE_SL_MODE` runtime → disabled; TP lỗi → CAO, theo quy tắc bước `place`, không chặn DONE |
| → DONE | mọi xác minh đạt | – | ghi journal, WCL, liq sau thực tế; nhả khoá; thông báo "Reduce xong" | – | – |
| `FAILED_SAFE` | – | không gửi thêm lệnh đóng; chỉ đặt lại TP theo bảng 6A.5 nếu TP đã bị huỷ | bất biến I1 (còn vị thế → có SL) giữ; phiên bản = `applied_partial` (nếu đã ghi) / `aborted` | – | thông báo trạng thái thật + phương án; **không tự thử đóng lại** |

**Khoá `UNRESOLVED_CLOSE` (P1)** – đặt ngay khi một lệnh đóng của leg có kết quả `UNKNOWN` (vào `PENDING_RECONCILE`), từ `reduce`, `ladder close` hoặc thủ tục khẩn (6A.10). Ghi DB `leg_locks(leg_id, kind=unresolved_close, op_id, client_oid, qty_max, created_at, cleared_at, cleared_by[resolved|ops_clear], note)` **trước** khi trả lời người dùng; nạp lại khi khởi động (sống qua restart, không có TTL ngầm).
- **Bị chặn** khi khoá còn (trên leg và cặp (symbol, holdSide) đó): tạo/duyệt `reduce` mới; `execute` mở thang mới; `ladder apply` có PLACE_ENTRY hoặc SL_LOOSEN; watcher đặt/đặt lại lớp entry.
- **Luôn được**: đối soát/dò nền; `entries --cancel*` (entry_adjust); bảo vệ SL (I1/I1n, SL_TIGHTEN, watcher đặt `pos_loss` thiếu); đặt lại TP theo size thật (TP là lệnh trigger trên vị thế, không gửi lệnh đóng ngay); `kill` (PROTECT_ONLY).
- **Đường đóng khẩn khi đang khoá**: chỉ `ladder close` (thủ tục thường 6A.10) hoặc `kill --close-positions --confirm-close` (thủ tục khẩn 6A.10). Cả hai dùng `close-positions` theo **size thật** của sàn, không gửi size tự tính, nên X nếu đã khớp thì size đọc được đã nhỏ hơn – không có "đóng quá" do cộng dồn hai khối lượng. Sau đó leg `CLOSED`, khoá **vẫn giữ** (chặn mở lại cùng (symbol, holdSide), để X nếu còn sống không đóng vào vị thế mới) tới khi được gỡ. Hành vi của sàn với một lệnh close khi size đã 0 **chưa kiểm chứng** (D38).
- **Gỡ khoá**: tự động khi X xác định được (thấy lệnh X ở bất kỳ trạng thái nào, hoặc fill có orderId của X) → xử lý như `FOUND`, `cleared_by=resolved`; hoặc sau ≥ 24 h dò nền không thấy dấu vết, bằng `ops clear <op_id> --confirm` (C42; preview in qty X, số lần dò, size hiện tại).
- **Không có "duyệt bất chấp" ở P1.** Sau khi gỡ bằng `ops clear` (X vẫn chưa xác định), trong 24 h kế tiếp mọi preview `reduce` của leg PHẢI in **tổng khối lượng có thể bị đóng** = `close_qty` mới + `qty_X` (và `min(tổng, size hiện tại)`), không chỉ câu cảnh báo chung; `prior_unknown_op {op_id, client_oid, qty}` nằm trong hash.

**RECOVERING** (khởi động lại hoặc mất kết nối giữa op; chạy trong reconcile §6.5): đọc `op_journal`, chụp REST đầy đủ (gồm kiểm chế độ tài khoản như RECONCILING), với từng bước:
- `CANCELLING_ENTRIES` dở → hoàn tất huỷ (idempotent). Sau đó chỉ tiếp tục sang CLOSING nếu `now < expires_at` **và** đối soát lại đạt; ngược lại `FAILED_SAFE` + đặt lại TP.
- `CLOSING` còn `planned` (chưa `sent`) → `VERIFIED_NOT_RECEIVED (a)`: được gửi nếu `now < expires_at` và đối soát lại đạt; ngược lại `FAILED_SAFE`.
- `CLOSING` đã `sent` → truy vấn: `FOUND` → tiếp tục như bảng (kể cả khi đã quá `expires_at`: UPDATING_PROTECTION vẫn chạy); mọi kết quả khác → `PENDING_RECONCILE` + khoá `UNRESOLVED_CLOSE` (không gửi lại; trừ `VERIFIED_NOT_RECEIVED (b)` với cùng clientOid và `now < expires_at`).
- `UPDATING_PROTECTION` dở → luôn hoàn tất tiến; bước đặt TP đã `sent` mà không thấy → `UNKNOWN`, không đặt lại tới khi xác định (TP không phải bảo vệ).
- Không bao giờ có bước mở vị thế trong reduce, nên không có gì "mở" để tiếp tục. Quyền thực thi không bao giờ được kéo dài sau crash.

### 6A.9 Preview & schema (tóm tắt; schema đầy đủ ở §5.6)

```
REDUCE 7Q2X.v4 (kind: reduce)  ETH long (Scalp)  mark 2385.62  exec: market  SL mode: position_persist
Tài khoản           hedge_mode / crossed / USDT-FUTURES (kiểm lại ở RECONCILING)
                    Hiện tại            Sau giảm 30% (close_qty 0.64 = pct 30 → floor lot)
Size                2.14 ETH            1.50 ETH
Notional            5105.23 (10.08×E)   3578.43 (7.06×E)
Liq 1 leg           2159.72 (9.47%)     2058.84 (13.70%)
Liq xấu nhất TK     2159.72 (9.47%)     2058.84 (13.70%)   [lớp chờ: không có; reduce luôn huỷ mọi lớp chờ]
Realized phần đóng  –                   −6.35 USDT (gồm phí mở chia tỉ lệ + phí đóng taker)
WCL thang           77.98               61.01 (đã gồm −6.35)
SL (pos_loss)       2359.09             2359.09 (giữ nguyên; xác minh sau khi đóng)
TP1/TP2 size        1.07 / 1.07         0.75 / 0.75 (trạng thái ACTIVE, T1 chưa khớp; huỷ trước khi đóng, đặt lại theo size thật)
Bộ đếm ngày         −18.17              −19.09 / khoá ở −41.98 (8%)
Phương án:  20% → 11.89% | 30% → 13.70% | 50% → 19.38%
Hết hạn 10:21:40 UTC+7 (cố định, không gia hạn)   hash 5d20b7   Duyệt 7Q2X.v4?
```
(Bộ đếm ngày giả định E đầu ngày = 524.7.)

### 6A.10 Đóng 100%: thủ tục thường và thủ tục khẩn

Áp cho mọi đường đóng hết một leg (bảng 6A.0). Cả hai thủ tục đều đóng **size thật đọc từ sàn** bằng `close-positions` (`productType=USDT-FUTURES`, `symbol`, `holdSide`) – không gửi size tự tính – và đều kết thúc bằng điều kiện: **size leg = 0 VÀ không còn lệnh entry/TP/SL nào của leg trên sàn** (`orders-pending` + `orders-plan-pending` lọc tiền tố công cụ và `posSide`).

**Thủ tục thường** – `ladder close <root> --confirm` (leg không có sự cố SL):
1. `RECONCILING`: kiểm chế độ tài khoản như 6A.8 (hedge / crossed / USDT-FUTURES); leg không `RECOVERING`, không có op khác. Lệch → dừng, 0 lệnh gửi.
2. `CANCELLING_ENTRIES`: huỷ **mọi** lớp chờ của leg + mọi TP (theo clientOid); chờ `cancelled` hoặc phát hiện `filled`/khớp một phần. SL **giữ nguyên**.
3. `SETTLING`: chờ `ladder_close.settle_s` (2 s), đọc `fills` (từ lúc bắt đầu op) + `single-position` để bắt **fill trễ** của lớp vừa huỷ; size thật = size sàn sau bước này.
4. `CLOSING`: `close-positions` holdSide (đóng đúng size thật, kể cả phần vừa khớp trễ).
5. `CONFIRM_ZERO`: `single-position` size = 0 (đối soát REST, tối đa 30 s); chưa 0 (vd fill trễ hơn nữa) → lặp lại 3–4, tối đa `emergency_max_loops` (3) lần, rồi KHẨN.
6. `CLEANUP`: chỉ khi size = 0 đã xác nhận → huỷ SL (`pos_loss`) và mọi lệnh còn sót của leg; xác nhận không còn lệnh nào; leg → `CLOSED`.

Lỗi ở bước 2 (huỷ bị từ chối/UNKNOWN) → **không** đóng, `FAILED_SAFE`, SL giữ, CAO + gợi ý thủ tục khẩn (`kill --close-positions --confirm-close`). Lỗi ở bước 4 (`close-positions` UNKNOWN) → như 6A.8: không gửi lại mù, đối soát `single-position`; leg vào khoá `UNRESOLVED_CLOSE` (6A.8) nếu vẫn không xác định.

**Thủ tục khẩn** – `kill --close-positions --confirm-close`, `on_sl_failure: close_leg` (SPEC 8.2(3)), `fail_execute` của `pos_loss`/BE (§9.4), Q-7 SL/BE đã vượt trigger (`kill --close-positions` do anh gõ áp cho mọi leg của công cụ, kể cả Nonstop; ba kích hoạt tự động còn lại chỉ áp leg Kiểm soát – Nonstop: §6B.5):
1. Leg → `EMERGENCY_CLOSING` (ghi DB trước): watcher **ngừng mọi** đặt/đặt lại entry và TP của leg; mọi lệnh mở của leg bị coi là không được phép.
2. `close-positions` holdSide **ngay** (ưu tiên giảm exposure; không chờ huỷ entry).
3. Huỷ **mọi** lớp chờ + TP của leg (song song, idempotent, tối đa 2 lần gửi lại mỗi lệnh).
4. Vòng kiểm: đọc `single-position` + `orders-pending`; size > 0 (một entry đã khớp trước khi bị huỷ) → `close-positions` lại; còn lệnh entry → huỷ lại. Lặp tới khi **size = 0 và 0 lệnh entry**, tối đa `emergency_max_loops` (3) vòng, mỗi vòng ≤ 10 s; hết vòng mà chưa đạt → KHẨN mỗi phút, tiếp tục vòng mỗi 30 s (không bao giờ đặt entry).
5. `CLEANUP` như thủ tục thường; leg → `CLOSED`. Leg đã `EMERGENCY_CLOSING`/`CLOSED` **không bao giờ** được watcher đặt lại entry (kể cả sau `resume`); muốn giao dịch tiếp phải là plan mới (`execute`).

Bảo đảm: không còn lệnh entry nào của leg trên sàn khi thủ tục khẩn kết thúc, nên không có lớp sót nào mở lại vị thế sau đó; nếu một entry khớp trong lúc thủ tục chạy thì vòng kiểm (bước 4) đóng nó. Hai thủ tục đều không áp `expires_at` (không phải phiên bản `reduce`); quyền gửi `close-positions` của thủ tục khẩn không phụ thuộc khoá ngày/kill (bảng 8.4 "Luôn được").

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

- Bật bằng `profile set --nonstop-bucket N --confirm` + xác nhận rủi ro khi bật (6B.3). Đây là **tăng rủi ro** theo §2.4: `pending` 24 h, bị từ chối khi đang khoá, tối đa 1 lần tăng/7 ngày. Tắt (`--nonstop-bucket 0`) = hạ rủi ro, hiệu lực ngay; thang Nonstop đang chạy không bị đóng, chỉ chặn mở thang Nonstop mới; **vốn đã phân bổ cho xô Nonstop không được giải phóng** cho tới khi mọi leg Nonstop về size 0, hết lệnh chờ và sổ đối soát đạt (§3.1).
- **Bậc hồ sơ** (câu hỏi C30, mặc định): Thận trọng **không** bật được; Cân bằng **không**; Mạo hiểm có kiểm soát **được**.
- **Xô Nonstop**: sổ `nonstop` trong **sổ phân bổ chung** `alloc_ledger` (§3.1): `alloc = share_ns × E_now` khi bật/refill; cùng mô hình dòng (khoá `(source_kind, source_id, line_type, ledger)`), cùng chia funding, cùng đẳng thức đối soát `E_wide + E_risk + E_ns = E`, cùng quy tắc xô âm / refill / tắt khi còn vị thế; `E_ns(t)` theo §3.1 và `E_wide_sizing` trừ `max(0, E_ns)`.
- Trần: `share_ns` theo C31 (mặc định đề xuất 10% E); **tổng xô Scalp + xô Nonstop ≤ `HARD_RISK_BUCKET_MAX` = 20% E** (dùng chung hằng có sẵn, không thêm hằng mới).
- Khoá xô Nonstop: `E_ns(t) ≤ 50% × E_ns_base` (cùng tỉ lệ 50% như xô Scalp) → chặn mở thang Nonstop mới và thêm lớp; **không** tự đóng hay huỷ gì (6B.4). Mở khoá: như §3.2 (mốc tháng + `bucket refill --nonstop --confirm`).
- Vì không có SL, khoá xô **không giới hạn được lỗ**: lỗ thực tế có thể vượt xô tới mức thanh lý toàn tài khoản. Preview và README PHẢI ghi câu này.

### 6B.2 Chốt chặn trước khi duyệt (mọi `execute` và mọi `ladder apply` làm tăng rủi ro của thang Nonstop)

| # | Kiểm tra | PASS | Ghi chú |
|---|---|---|---|
| N1 | **Bội số** | notional khi **khớp đủ mọi lớp** của thang Nonstop + mọi leg khác: cùng chiều ≤ `min(trần cùng chiều hồ sơ, params.nonstop.samedir_x, nonstop.max_multiple_x, cứng 15×)`, tổng ≤ `min(account.total_x hồ sơ, params.nonstop.total_x, cứng 20×)` (§3.5 mục 4a). Hồ sơ Mạo hiểm hiện tại: cùng chiều **5×**, tổng **7×** | R10w (2.5× cùng chiều Wide) **không** áp cho Nonstop; hằng cứng **không** thay trần hồ sơ (C33) |
| N2 | **Thanh lý theo đường khớp** | với **mọi** k = 1…N: `d_k ≥ nonstop.min_liq_fill_path_pct` (C32 – **chưa chốt**, đề xuất 3%) **và**, với k < N, lớp k+1 tới được trước thanh lý (long: `liq_k < P_{k+1}`) | Với từng k: giả định lớp 1…k của thang đã khớp (lớp đã khớp thật dùng giá/size thật) và mark = `P_k`; mô hình xấu nhất toàn tài khoản §6A.2 (lớp chờ cùng chiều của leg khác có giá đã bị vượt coi như khớp; leg ngược chiều chỉ tính MM) → `liq_k`, `d_k = sg·(P_k − liq_k)/P_k`. Lưu `fill_path [{k, price, liq, d_pct}]` và `min_d_pct` trong plan (trong hash); preview in cả đường. **Không** dùng quy đổi bội số ↔ khoảng cách nào để cho phép (6B.8). Mọi `ladder apply` tăng rủi ro tính lại toàn bộ đường từ trạng thái thật |
| N3 | **Xô** | xô Nonstop đang bật, không khoá; `share_ns` và tổng xô ≤ trần | 6B.1 |
| N4 | **Xác nhận rủi ro** | mã xác nhận của đúng phiên bản (6B.3) | mỗi lần duyệt |
| R27n | **Tham số thang** (C40, mặc định đề xuất) | 1–12 lớp; `d` ≥ 0.10%; `mult` 0.80–1.00; lớp đầu ≤ 10× E; TP nếu có ≥ 0.10% (preview in lãi ròng sau phí 0.02% + 0.06%); SL nếu có: phía đúng, ngoài lớp cuối ≥ `d`, và **nằm trước giá liq khớp đủ** (long: SL > liq) – nếu không thì FAIL "SL vô dụng vì thanh lý trước" | thay R27w/R27s cho `mode: dca` |
| R16/R17 | ký quỹ, đòn bẩy | như SPEC (R16 80% `crossedMaxAvailable` như Scalp; leverage ≤ `HARD_LEVERAGE_MAX_PER_SYMBOL` = 50) | hệ quả: notional khớp đủ ≲ 40× E (ký quỹ ban đầu = notional/leverage) |

Các kiểm tra chung vẫn áp: R1–R7 (dữ liệu, symbol, 1 thang mỗi (symbol, holdSide) – 6B.6), R23 post-only, R26 giờ cấm, R27 phần chung, R29 phiên bản, R30 đèn, khoá §8.4.

### 6B.3 Xác nhận rủi ro (bắt buộc)

- **Khi bật Nonstop**: CLI yêu cầu gõ đúng câu: `TÔI HIỂU: KHÔNG CÓ SL, CÓ THỂ MẤT TOÀN BỘ TÀI KHOẢN` (lưu vào hồ sơ: thời điểm, phiên bản hồ sơ).
- **Mỗi lần duyệt plan Nonstop** (`execute` / `ladder apply` tăng rủi ro): `--ack NS-<6 hex đầu của content_hash>-<min_d_pct 2 chữ số>` (vd `NS-a41c09-2.30`). Mã **không** nằm trong `hash_content`: phiên bản được băm trước, mã suy ra từ hash (và `min_d_pct` đã nằm trong nội dung băm), mã anh gõ được ghi vào bảng `approvals` tách khỏi plan (§5.4) – nhập mã không đổi hash. Đổi qty/SL/entry → phiên bản mới → hash mới → mã mới (U67). Mã lấy từ preview của **đúng** phiên bản; sai/thiếu → `approvals.result = rejected`, R29 FAIL. Trợ lý chat **không được** tự điền mã: chỉ chuyển nguyên văn mã anh gõ (quy tắc §1.1 mục 2; công cụ không phân biệt được ai gõ – đây là quy tắc cho trợ lý, ghi rõ là giới hạn).
- Preview Nonstop PHẢI có, ở đầu và không thể tắt:

```
NONSTOP 9KD2.v1  ETH long (dca)   ⚠ KHÔNG CÓ SL   TP: +0.15% (lãi ròng ~0.07%/lần)
Khớp đủ 4 lớp:   notional 17173.74 USDT = 32.73× vốn (E 524.70)
Thanh lý nếu khớp đủ (ước tính, mmr 0.5%): 2334.19 = cách lớp cuối 2.30% / cách lớp 1 2.74%
Đường khớp d_k:  L1 9.56% → L2 4.79% → L3 3.16% → L4 2.30%   (min 2.30% ở L4)
Nếu bị thanh lý: mất tới gần như TOÀN BỘ tài khoản (~524 USDT), không chỉ xô Nonstop (52.47)
Chốt chặn: N1 FAIL (32.73× > 5.00× – cùng chiều hiệu lực = min(hồ sơ Mạo hiểm 5×, cấu hình 15×, cứng 15×))
           N2 FAIL (min d_k 2.30% ở L4 < 3% – ngưỡng đề xuất, chưa chốt)
Mã xác nhận: NS-a41c09-2.30   (gõ: execute 9KD2.v1 --confirm --hash a41c09 --ack NS-a41c09-2.30)
```
(Ví dụ minh hoạ dùng thang ~30× ở 6B.8; hash minh hoạ.)

### 6B.4 Khi đang chạy: chỉ cảnh báo

- Cảnh báo `ns_*` **không bao giờ** gây ra lệnh can thiệp (huỷ, đóng, reduce, SL mới, phiên bản dựng sẵn). Việc quản lý lệnh **theo plan** vẫn chạy độc lập với cảnh báo và được gắn `cause=plan` trong journal. Watcher **không** gửi lệnh nào cho leg Nonstop ngoài: (a) entry/TP đã duyệt (đặt lại TP sau mỗi fill như Scalp SPEC 4.12.3, nếu có TP); (b) SL đã duyệt (nếu có, I1n). **Không** dựng sẵn reduce, **không** tự reduce/đóng, **không** tự huỷ lớp chờ (kể cả khi khoá ngày, khoá xô, hay khi liq tới gần – khác với quy tắc huỷ lớp của Scalp SPEC 4.12.3c; xem C36).
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
| §6A reduce: RECONCILING "đúng 1 `pos_loss`", điều kiện CLOSING, điều kiện kết thúc "đúng 1 SL", bảng TP 6A.5, U42/U47/U55 | giữ nguyên (`sl_policy: required`) | `sl_policy: none`: số SL kỳ vọng = **0** ở RECONCILING **và CLOSING** (thấy SL lạ → ABORTED / FAILED_SAFE + CAO, không đụng); kết thúc: 0 SL; TP chỉ đặt lại nếu plan có TP (U70) | `sl_policy: approved`: số SL kỳ vọng = 1 (như Kiểm soát) |
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
- **Cap 2.5× cùng chiều**: đó là R10w của Wide (cứng 2.5×) – **không áp** cho Nonstop; trần cùng chiều toàn tài khoản R10a **có áp** với trần hiệu lực `min(hồ sơ, Nonstop, cứng)` (N1, §3.5 mục 4a; Mạo hiểm hiện tại 5×).
- **Khoá ngày**: chặn mở Nonstop mới (6B.5). Nonstop không được dùng để "gỡ" sau khi Kiểm soát bị khoá.

### 6B.7 Pha và cổng

- **PN** (không thuộc P1/P1b): bật được khi (1) cổng Demo P1 của Kiểm soát đạt (Q-13); (2) sổ phân bổ chung đạt (U58, U68); (3) U59–U67, U69 (phần Nonstop), U70 và D34–D37 đạt; (4) chủ trả lời C30–C40. Câu hỏi C39 (mặc định: như vậy, không chờ thêm 4 tuần live).
- Trước PN: `regime: nonstop` bị từ chối ở `propose`/`plan import`/`execute` với thông báo pha.

### 6B.8 Tính toán minh hoạ – thanh lý theo đường khớp, kiểu thang của chủ

> **Đây là phép tính, không phải dữ liệu sàn.** Script `/workspace/scratch/spec_v2/r4/nonstop_liq.py` + `/workspace/scratch/spec_v2/r5/nonstop_fillpath.py` (Decimal). Giả định: ETHUSDT long, P₁ 2400.00, E = 524.7, cross, không có vị thế khác, `mmr` 0.5% (MMR bậc thật theo notional có thể cao hơn → liq **gần hơn**), phí mở maker 0.02%, size floor lot 0.01, giá floor tick 0.01. Công thức §6A.2: `W + Q(P − A) ≤ mmr·Q·P`, `W = E − phí mở`. Kiểu thang theo chủ: `d` 0.11–0.18%, `mult` 0.87, lớp đầu ~10× E.

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

- Script vòng 5: `/workspace/scratch/spec_v2/r5/nonstop_fillpath.py` (dùng lại hàm của `r4/nonstop_liq.py`). `d_k` = khoảng cách thanh lý từ giá lớp k ngay khi lớp k khớp (lớp 1…k đã khớp). Cột N2 = PASS/FAIL theo quy tắc 6B.2 với ngưỡng 3% / 2% / 1% (để so sánh; C32 chưa chốt).
- Khớp với số người review tái tạo: 16.34× → 2260.44 / 5.39%; 32.73× → 2334.19 / 2.30%; 60.05× → 2359.36 / 0.21%.
- Với lớp đầu 10× và `mult` 0.87, tổng chuỗi vô hạn chỉ là 10/(1 − 0.87) = **76.9×** → 95× không đạt được nếu không tăng lớp đầu hoặc `mult`. Ở ~95×, `d_k` âm từ L9 (lớp đầu 15×) / L10 (mult 0.97): **thanh lý xảy ra trước khi các lớp cuối kịp khớp**, chỉ 8/13 và 9/12 lớp tới được.
- **Bỏ quy đổi bội số ↔ khoảng cách** (bản v5 có dòng "≥ 3% ⇔ ≲ 28.5×"): đó chỉ là xấp xỉ coi cả thang như một lớp, **không** được dùng làm quy tắc cho phép. Phản ví dụ: thang ~25.64× (lớp đầu 5×, 8 lớp) chỉ có `d_8` = 2.78% → **FAIL** ở 3%, trong khi quy đổi cũ sẽ cho qua. N2 luôn tính từng thang theo đường khớp (U60).
- **Hệ quả**: với hồ sơ Mạo hiểm hiện tại (trần cùng chiều 5×, tổng 7×), **mọi** thang trong bảng (≥ 16×) FAIL N1 trước cả N2. Kiểu 30–95× của chủ cần (a) nâng trần hồ sơ (tăng rủi ro §2.4, ≤ hằng cứng 15× / 20×) và (b) nếu > 15× cùng chiều: nâng hằng cứng và leverage 50 (đổi mã + review), và (c) hạ N2 xuống dưới mức ~2% / ~0.2% của đường khớp – đều là quyết định của chủ (C32, C33); tài liệu này **không** tự chốt.

---

## 7. Phân tích thị trường – đầu ra cho người không chuyên [→ SPEC 6.4 đầu ra, 2.3 dòng AVOID, R21]

### 7.1 Đèn

| Đèn | Nguồn (SPEC 6.4) | Trước cổng 6.8 | Sau cổng 6.8 đạt |
|---|---|---|---|
| **Xanh** | OK | được đề xuất | được đề xuất |
| **Vàng** | CAUTION | không đề xuất tự động; được mở nếu anh yêu cầu (cảnh báo) | như trái |
| **Đỏ** | AVOID | cảnh báo mạnh; execute cần `--reason "<lý do anh gõ, ≥ 10 ký tự>"` (lưu log, nhật ký) | **chặn** (R30 FAIL, không override) |
| **Xám** | thiếu dữ liệu (`data_quality` lỗi, nến cũ > 2 phút) | coi như vàng | coi như vàng |

Nhãn bắt buộc mọi nơi hiển thị đèn: **"Bộ lọc rủi ro, không phải dự báo."**

### 7.2 Định dạng

```
ETH long   XANH  4h đi ngang, biến động bình thường.
ETH short  VÀNG  Khung 1 ngày và 4 giờ đều đang thiên tăng – thang short dễ bị kéo sâu.
BTC long   ĐỎ    Nến 1 giờ vừa rồi biến động gấp 3.4 lần mức thường – chờ thị trường dịu lại.
BTC short  XANH  Không có tín hiệu bất lợi đáng kể.
(Bộ lọc rủi ro, không phải dự báo.)
```
- Một câu = lý do ưu tiên cao nhất: AVOID trước, rồi CAUTION theo thứ tự trong SPEC 6.4. Mỗi `reason_code` có một mẫu câu tiếng Việt thường (không thuật ngữ) + số đo; chi tiết kỹ thuật ở `ta --json`.
- `ta --simple` in đúng 4 dòng trên. Digest dùng cùng nguồn.

### 7.3 "TA-lite" trong P1

Đề xuất tự động cần đèn từ P1, nên đưa các điều kiện chỉ cần nến + ticker vào P1 (hiển thị/lọc đề xuất, **không chặn**): 4h ADX/DI + cấu trúc 4h, sốc 1h (biên độ/ATR1h), ATR1h phân vị, bias 1d/4h, funding. OI/long-short, phân kỳ RSI, BB squeeze, `levels`: giữ P2. Trước khi có TA-lite, mọi chiều = xám → không có đề xuất tự động (chỉ `propose --symbol --side` thủ công).

---

## 8. Vận hành hằng ngày & thông báo [→ SPEC R18–R20, 4.12.5, Q-12]

### 8.1 Ranh giới thời gian

- **Ngày giao dịch = [07:00, 07:00) UTC+7** (= 00:00 UTC, trùng mốc funding và mốc ngày của sàn). Áp cho khoá ngày (cả Wide và Scalp, thay "00:00 UTC+7" của SPEC), thống kê ngày, digest.
- **Tuần = từ thứ Hai 07:00 UTC+7.**

### 8.2 Bản tin sáng (07:05 UTC+7, `digest`)

Nội dung: equity, PnL hôm qua/tuần, khoá đang có, thang đang chạy (khớp mấy lớp, cách SL bao xa), đèn 4 dòng, ≤ 2 đề xuất. Câu đề xuất chuẩn (số lấy từ `derived`, không viết tay):

> "Hôm nay nên mở **{SYMBOL} {chiều}** ({đèn}: {lý do}). Nếu sai hẳn: mất tối đa **{loss_at_sl} USDT** (~{loss_slip03} nếu trượt giá). Mỗi lần chốt: ~**{tp1_l1_net} USDT** nếu chỉ khớp lớp 1, ~**{tp1_full_net} USDT** nếu khớp đủ. An toàn nghĩa là lãi mỗi lần nhỏ. Duyệt **{ref}** không?"

Ví dụ Cân bằng: ETH long 23.4 / 24.4 / 0.27 / 1.83; BTC short 25.1 / 26.3 / 0.37 / 2.08. Dòng thành thật cố định cuối digest lấy từ §2.6: cho tới khi B9 đạt với đúng `config_hash` – **mọi bậc**: "Kỳ vọng lãi: chưa kiểm định bằng backtest cho cấu hình này." Sau B9: in số B9. Không in số SAFE hay DEFAULT.
Đề xuất trong digest hết hạn sau 10 phút; trả lời muộn → trợ lý `plan refresh` → nếu rủi ro/size không đổi in "làm mới, rủi ro không đổi" nhưng **vẫn hỏi duyệt phiên bản mới**.

### 8.3 Thông báo sự kiện (watcher → kênh Q6)

| Sự kiện | Mức | Mẫu |
|---|---|---|
| Fill lớp k | INFO | "ETH long: khớp lớp 2 @2364.00. Đang giữ 0.06 ETH, giá TB 2382.00. SL 2174.58 (lỗ nếu chạm ~… USDT). TP1 2410.59." |
| TP1 | INFO | "Chốt TP1 +{x} USDT. Đã huỷ lớp còn lại, SL về hoà vốn {BE}." |
| TP2 / BE | INFO | "Đóng thang: {lý do}, ròng {pnl} USDT. Hôm nay: {pnl_day}." |
| SL | CAO | "Cắt lỗ ETH long: −{x} USDT (dự kiến −{y}). Hôm nay −{d}% / khoá ở −{lim}%." |
| WORKING hết hạn (24 h, lớp 1 chưa khớp) | INFO | "Đã huỷ thang chờ ETH long (24 h không khớp). Đề xuất mới trong digest." |
| Khoá ngày/tuần/DD/chuỗi stop/xô/bộ đếm UNKNOWN | CAO | "Đã chặn gửi lệnh mở mới đến {thời điểm UTC+7}. Lệnh chờ Wide đang treo vẫn có thể khớp (huỷ: `entries {root} --cancel-all`). Thang đang chạy giữ nguyên SL/TP." |
| Cảnh báo thanh lý (§6A.6) | CAO / KHẨN (< 5%) | "Thanh lý (xấu nhất toàn TK) cách {d}% < ngưỡng {th}%. Đề xuất giảm {qty} {coin} ({pct}%) → {d2}%, chốt {realized} USDT. Duyệt {ref}?" |
| Reduce / entry_adjust xong | INFO | "Đã giảm {qty} @ {price} (market), realized {x} USDT. Liq {d}% → {d2}%. SL {sl} vẫn trên sàn (đã xác minh)." / "Đã huỷ lớp {idx}, không đóng vị thế. Liq xấu nhất {d}% → {d2}%." |
| Reduce FAILED_SAFE / RECOVERING / PENDING_RECONCILE | CAO | "Giảm vị thế dừng ở bước {step}: {lý do}. Trạng thái thật: {size}, SL {sl} trên sàn. Chưa đóng thêm. Đề xuất: {ref}." |
| Hồ sơ pending hiệu lực | INFO | "Hồ sơ v4 (Mạo hiểm) bắt đầu hiệu lực." |
| Lỗi đặt lệnh/đối soát/DRIFT | CAO | mô tả + việc công cụ đã làm |
| Leg cần SL mà không có SL, WS chết, `fail_execute` | KHẨN | + hành động tự động đã chạy |
| Nonstop `ns_liq` / `ns_multiple` (§6B.4) | CAO / KHẨN, **không tắt được** | "NONSTOP ETH long (không SL): thanh lý cách mark {d}% (khớp nốt lớp chờ: {d_all}%), {x}× vốn. Công cụ không tự giảm/đóng. …" |

### 8.4 Khoá – định nghĩa duy nhất (giải Q-12) [→ SPEC R18–R20, 4.12.2 dòng "Lỗ ngày", 4.12.5 "Khoá ngày", A.2 `risk.daily_loss_pct`/`scalp.daily_loss_pct`]

- **Ranh giới**: ngày = [07:00, 07:00) UTC+7, tuần từ thứ Hai 07:00 UTC+7, **ở mọi nơi**; mọi "00:00 UTC+7" trong SPEC (R19, 4.12.2, 4.12.5) được thay bằng 07:00 UTC+7.
- **Mốc** `E_day_start` (tương tự `E_week_start`), theo thứ tự ưu tiên:
  1. **Mốc đã lưu**: watcher chụp `accountEquity` (mark) lúc 07:00:00 ± 5 s và ghi ngay vào bảng `day_marks(period[day|week], start_ts, equity, source[live|reconstructed], captured_at, inputs_hash)` trong DB (sống qua khởi động lại). Khởi động lại trong ngày → **dùng mốc đã lưu**, không chụp lại. Ví dụ: 07:00 E = 500.00 (đã lưu); VPS khởi động lại lúc E = 450.00 → `daily_pnl` = −50.00, không bị bỏ sót.
  2. **Dựng lại từ lịch sử** (khi không có mốc đã lưu, vd VPS tắt lúc 07:00): `E_day_start = W_07 + uPnL_07`.
     - `W_07` (số dư ví lúc 07:00) = `balance` của bill cuối cùng có `cTime < 07:00` trong `GET /api/v2/mix/account/bill` (`productType=USDT-FUTURES`, phân trang `idLessThan` tới hết, khoảng ≤ 30 ngày/lần gọi); đối chiếu bằng `W_now − Σ(amount + fee)` của các bill từ 07:00 tới nay – hai cách phải khớp ±0.01 USDT.
     - `uPnL_07 = Σ_leg sg·Q_07·(mark_07 − A_07)`: `Q_07`, `A_07` dựng ngược từ vị thế hiện tại (`GET /api/v2/mix/position/all-position`) trừ các fill từ 07:00 (`GET /api/v2/mix/order/fills`, theo symbol, `startTime` = 07:00; tài liệu ghi `fill-history` không hỗ trợ Demo nên không dùng); vị thế đã đóng hẳn sau 07:00 lấy thêm từ `GET /api/v2/mix/position/history-position`; `mark_07` = giá mở nến 1 phút 07:00 của `GET /api/v2/mix/market/history-mark-candles` (public).
     - Chuyển tiền trong ngày (bill `trans_from_*` / `trans_to_*`) ghi vào `net_transfers_today`.
     - Điều kiện chấp nhận: (i) hai cách tính `W_07` khớp; (ii) mọi leg có `Q_07 ≥ 0` và `A_07 > 0` khi `Q_07 > 0`; (iii) mọi trang bill/fill tải đủ, không lỗi; (iv) có nến mark 07:00 cho mọi symbol có vị thế. Sai một điều kiện → nhánh 3.
     - **Chưa kiểm chứng**: tên endpoint và trường (`balance`, `amount`, `fee`, `businessType`, `cTime`) lấy từ tài liệu Bitget v2 (đọc 2026-10-20), chưa gọi thử. Nhánh này **tắt** (`day_mark.reconstruct_enabled: false`) cho tới khi D33 đạt; trước đó luôn đi nhánh 3.
  3. **Không có mốc và không dựng lại được → bộ đếm = `UNKNOWN`**: chặn **mọi hành động tăng rủi ro** (cột "Bộ đếm UNKNOWN" ở bảng dưới), hành động giảm rủi ro luôn được. Không gắn nhãn rồi chạy tiếp như bình thường. Hết `UNKNOWN` khi chụp được mốc kế tiếp (07:00 ngày sau; tuần: thứ Hai 07:00) hoặc khi dựng lại thành công (thử lại mỗi 15 phút nếu nhánh 2 bật). Digest/`lock status` in "Bộ đếm ngày không xác định từ {thời điểm} – chặn mở mới tới {mốc}".
- **Tính gì**: `daily_pnl = E_now − E_day_start − net_transfers_today` theo mark ⇒ gồm **lỗ/lãi đã thực hiện + chưa thực hiện**, mọi phí (kể cả phí đóng của `reduce`/`ladder close`), funding; chuyển tiền vào/ra (phát hiện qua bill tài khoản, hoặc E nhảy không kèm fill → CAO, cần anh xác nhận) bị loại. **Một bộ đếm cho toàn tài khoản (Wide + Scalp)**. Khoá ngày riêng của Scalp ở SPEC 4.12.5 (10% E, lỗ Scalp thực hiện + chưa) **bỏ**; Scalp bị giới hạn thêm bởi ngân sách xô §3.
- **Kích hoạt**: `daily_pnl ≤ −daily% × E_day_start` (ngưỡng theo bậc §2.2). Không tự mở khi E hồi trong ngày.
- **Khoá nghĩa là gì**: khoá = **chặn gửi thêm lệnh mở** – công cụ không gửi lệnh entry mới nào (execute, lớp thêm/dời/đổi size qua `ladder apply`, watcher đặt lại lớp Scalp). Khoá **không** có nghĩa "ngừng mở vị thế": **lệnh entry Wide đã treo sẵn trên sàn vẫn có thể khớp** và làm vị thế tăng trong lúc khoá, trừ khi bị huỷ (`entries <root> --cancel-all`, `cancel <root>`); mặc định công cụ không tự huỷ chúng (C12). Khoá cũng không giới hạn lỗ của thang đang chạy (SL làm việc đó).

| Khoá | Công thức | Mở khoá |
|---|---|---|
| Ngày | như trên | 07:00 UTC+7 hôm sau, tự động; không mở sớm |
| Tuần | như trên theo `E_week_start` | thứ Hai 07:00 UTC+7 |
| Bộ đếm UNKNOWN | không có mốc và không dựng lại được | mốc kế tiếp chụp được, hoặc dựng lại thành công |
| DD | `E_now < (1 − dd%) × max(E 30 ngày)` | tự động sau **7 ngày**: đặt lại đỉnh = E_now và **ép bậc Thận trọng 7 ngày** |
| Chuỗi stop | SL thứ 2 trong 24 h cuộn (reduce/đóng tay không tính) | sau 12 h |
| Xô | §3.2 | §3.2 |
| Giờ cấm (P6) | `now ∈ no_trade` | hết khung giờ |
| Sổ phân bổ lệch | đẳng thức §3.1 `E_wide + E_risk + E_ns = E` không đạt sau khi tải lại | đẳng thức đạt lại; trong lúc lệch: như cột "Bộ đếm UNKNOWN" |
| Đóng chưa xác định (`UNRESOLVED_CLOSE`, **theo leg**) | lệnh đóng của leg có kết quả UNKNOWN (6A.8) | X xác định được, hoặc `ops clear` sau ≥ 24 h; được/chặn theo 6A.8 (chặn `reduce`, `execute` cùng (symbol, holdSide), PLACE_ENTRY, SL_LOOSEN; `ladder close`/`kill --close-positions` được) |

**Được / bị chặn khi khoá:**

| Hành động | Khoá ngày/tuần/DD/chuỗi stop | Bộ đếm UNKNOWN | Khoá xô | Giờ cấm |
|---|---|---|---|---|
| `execute` plan mở mới | Chặn (Wide + Scalp) | Chặn | Chặn Scalp | Chặn |
| `ladder apply` làm tăng WCL hoặc có PLACE_ENTRY | Chặn | Chặn | Chặn (thang Scalp) | Chặn |
| `ladder apply` không tăng WCL và không đặt entry (TP, SL gần hơn, huỷ lớp) | Được | Được | Được | Được |
| Watcher đặt/đặt lại lớp entry (Scalp) | Chặn | Chặn | Chặn | Chặn |
| `entries` (entry_adjust), `cancel`, `reduce`, `ladder close`, `kill` | **Luôn được** | **Luôn được** | **Luôn được** | **Luôn được** |
| `bucket refill`, tăng hồ sơ | Chặn | Chặn | – (refill theo §3.2) | Được |
| `propose`/digest | Không đề xuất; in "đang khoá đến …" | Không đề xuất; in lý do | Không đề xuất Scalp | Không đề xuất |
| Lệnh entry Wide **đã treo** trên sàn | Giữ, **vẫn có thể khớp** (C12) | Giữ, vẫn có thể khớp | – | Giữ |

Tự động khi khoá ngày/tuần/DD: huỷ entry Scalp chưa khớp; lệnh chờ Wide giữ nguyên. Nonstop (§6B.5): khoá chặn mở thang Nonstop mới và thêm lớp; lệnh chờ Nonstop **không** bị huỷ và vẫn có thể khớp; không có hành động đóng nào. Lỗ chốt bởi `reduce` đã nằm trong E theo mark nên khoá ngày/tuần/DD chỉ thêm phí + trượt; ngân sách thang/xô thì tính đủ (§6A.6).

---

## 9. Sửa các lỗi nghiêm trọng (và quan trọng liên quan) từ review

### 9.1 N1 – `aggressive` không bao giờ PASS R13 [→ SPEC 4.2, A.2, Q3, Phụ lục C]
**Quy tắc:** xoá biến thể `aggressive` và cờ `--variant`. Bậc "Mạo hiểm có kiểm soát" dùng tham số DEFAULT (capLeg 1.25, s 7%) trên `E_wide` = 80% E, ≤ 3 thang: SL ngoài lớp 5 **2.65% long / 2.40% short** → R13 PASS. Test U20 bắt buộc: *mọi bậc công bố PASS R13 với contracts bảng 4.1, cả 2 symbol, 2 chiều*. Phụ lục C: ghi chú "AGGR là kết quả tham khảo, không phải cấu hình có trong công cụ".

### 9.2 N2 – R14 chặn thang thứ 4 [→ SPEC R14, A.1 `HARD_TOTAL_SL_BUDGET`, 4.11]
**Định nghĩa R14 mới:** `Σ_legs WCL_leg / E_now ≤ sl_budget_pct (bậc)`, với `WCL_leg` theo §6.3 (size thật, giá khớp thật cho phần đã khớp, SL hiện tại; leg ở `TP1_DONE` với SL ≥ BE: `max(0, lỗ tại BE)` ≈ 0; Scalp gồm trượt 0.3%). Số thang tối đa do **hồ sơ** quy định (Cân bằng 4, Mạo hiểm 3) sao cho R14 không phải là thứ "bất ngờ" chặn: Cân bằng 18.62% ≤ 21%; Mạo hiểm 20.82% ≤ 25%. Hằng cứng giữ 25% / 30%.

### 9.3 N3 – `kill` xoá SL [→ SPEC 2.2 dòng `kill`, 9.5, 2.4 bước 4]
- `kill` (mặc định) = **chế độ bảo vệ**: tạo `state/KILL`, huỷ mọi **entry** và **TP** của công cụ (lọc tiền tố), **giữ** `pos_loss`/BE, watcher **tiếp tục chạy** ở chế độ `PROTECT_ONLY` (chỉ đảm bảo SL, đối soát, cảnh báo; không đặt entry/TP). Xác nhận đầu ra: "mỗi leg Kiểm soát còn vị thế có đúng 1 SL"; leg Nonstop không SL được liệt kê riêng: "KHÔNG có SL" (§6B.5).
- `kill --close-positions --confirm-close` = **thủ tục khẩn §6A.10** cho từng (symbol, holdSide) của công cụ: `close-positions` → huỷ mọi lớp chờ + TP → vòng kiểm tới khi size = 0 và 0 entry (xác nhận REST) → mới huỷ SL còn lại. Thất bại đóng → giữ SL, KHẨN.
- `resume --confirm` = xoá `state/KILL` + `selftest` → watcher về chế độ thường (đặt lại TP theo phiên bản đang chạy; **không** đặt lại entry đã huỷ – muốn thì `ladder edit`).

### 9.4 N4 – TP limit chiếm 100% vị thế [→ SPEC 4.5, 7.3, 7.4(d), 7.6(1)]
**Mặc định mới `tp_mode: plan_market`**: TP1/TP2 là `place-tpsl-order planType=profit_plan`, `size = qTP`, `triggerType=fill_price`, **`executePrice = "0"` (market)** → không chiếm vị thế lúc chờ, cũng không để lại limit treo nếu giá quay đầu sau trigger. Chi phí: phí đóng taker thay maker – TP1 đầy thang ETH Cân bằng 1.83 thay vì 1.89 USDT; lớp 1: 0.27 thay vì 0.28. Mọi số "lãi" trong tài liệu này đã tính theo taker.
- Không còn lệnh close limit nào treo trong thiết kế mặc định (trừ `scalp scaleout` – xem dưới). Fallback chỉ dùng nếu D18 FAIL: `limit_partial` với `Σ size TP ≤ Q − 1 lot`.
- Watcher PHẢI xử lý `orders-algo status=fail_execute`: với `pos_loss`/BE của leg Kiểm soát → `close-positions` (holdSide) ngay + KHẨN (leg Nonstop có SL: chỉ KHẨN, §6B.5); với TP → đặt lại 1 lần, vẫn lỗi → CAO.
- Scalp TP_a/TP_b: dùng cùng `plan_market` (phí taker 0.06% làm lãi TP_a mỏng: TP 0.15% − 0.02% − 0.06% = 0.07% notional; đã tính trong §3.4). `scalp scaleout` (limit post-only) phải giữ `Σ close limit ≤ Q − 1 lot` và chạy qua executor reduce (maker, P1b, §6A.0) – tắt khi reduce tắt.
- D9 chạy cả trước TP1 (TP1+TP2 chờ) và sau TP1 (TP2 + BE).

### 9.5 N5 – execute gần như luôn bị huỷ bởi quy tắc 1 tick [→ SPEC 2.3 dòng 115, 4.3 anchor, R5, R23]
Phát hiện bổ sung khi tính lại: theo SPEC 4.6 với Q thiết kế, **SL không phụ thuộc E** (C, Q, L đều tỉ lệ với E; kiểm E = 500 / 524.7 / 550 đều cho 2174.58). Thứ thật sự nhảy theo E là **size đã làm tròn** (BTC: E 520 → lớp 4 0.0009; 524.7 → 0.0010) và **L tính bằng USDT**.
**Quy tắc mới:**
1. `frozen.equity` lúc tạo phiên bản dùng cho B, L, size. Execute: `|E_now/E_frozen − 1| ≤ 1%`, vượt → plan hết hiệu lực (refresh).
2. **Bất biến được duyệt** (cái anh thật sự duyệt): symbol, chiều, số lớp, **size từng lớp**, khoảng cách tương đối, TP%, `max_loss` USDT, notional ≤ đã duyệt × 1.003.
3. `anchor.mode = fixed`: giá giữ nguyên; R23 (post-only) FAIL → plan hết hiệu lực.
   `anchor.mode = market_shift` (mặc định cho đề xuất): tại execute, `k = bid_now/P1` (long; short dùng ask), nếu `|k − 1| ≤ 0.3%` → mọi giá lớp = `round(P_i × k)` theo 4.9, **size giữ nguyên**, SL tính lại theo 4.6 với `L` giữ nguyên; kiểm lỗ thật ≤ max_loss và notional ≤ đã duyệt × 1.003. Đạt → execute, in "đã dịch thang {k−1:+.2%}" trong kết quả. Không đạt → hết hiệu lực.
4. So sánh "lệch 1 tick" của SPEC 2.3 bị bỏ; thay bằng kiểm tra bất biến ở (2) và R1–R30 không đổi trạng thái.

### 9.6 N6 – ví dụ Scalp 4.12.4 sai [→ SPEC 4.12.4, U3, D15]
- Ví dụ cũ (first 3×, 15% E) sửa đúng theo R10: dừng ở **lớp 4**, size 0.65/0.57/0.49/0.43, notional 5122.38 (9.76× E, E = 524.87), **SL 2359.09**, lỗ thực tế 77.98. Câu "BTC long cùng quy mô → ETH còn lớp 4–5" thay bằng "→ ETH không mở được lớp nào".
- Ví dụ chuẩn mới thay thế bằng §3.4 (xô mạo hiểm, 4 lớp, 5% E). Cấu hình first 3× / SL 15% chỉ còn như minh hoạ rủi ro; trần Scalp theo bậc (2.5% / 5% E mỗi thang) thấp hơn nhiều.

### 9.7 Phát hiện quan trọng liên quan luồng mới

| Review | Quy tắc đề xuất | Thay |
|---|---|---|
| Q-1 | Sửa câu "SL/BE giống backtest" → "SL chặt hơn backtest ~0.08% vì tính phí; BE = A·(1+0.15%)". B1/B2 chạy cùng mã. Thêm B7 đo ảnh hưởng của BE và `plan_market` | 4.5, 4.6 |
| Q-2 | U2 chỉ so giá lớp/TP (±1 tick) và size; oracle SL = công thức 4.6 | U2 |
| Q-3 | Digest/README chỉ in số kỳ vọng từ B9 cho đúng cấu hình; trước đó "chưa kiểm định"; số cũ = "kết quả lịch sử của cấu hình khác" (§2.6) | 1.3, Phụ lục C |
| Q-4 | R16 = `notional plan mới / leverage ≤ 50% crossedMaxAvailable` (Scalp 80%). Mạo hiểm/xô cần 20× (vd Scalp 1484 USDT / 20 = 74 USDT ký quỹ) | R16 |
| Q-5 | TP1_DONE theo **sự kiện lệnh** (`profit_plan` T1 executed theo clientOid), debounce fill 1–2 s; fill trễ sau TP1: tính lại A từ `openPriceAvg`, TP2 cho toàn bộ phần còn, BE theo A mới | 8.2 bước 5 |
| Q-6 | `working_ttl_h` = 24 (tham số plan); hết hạn → CANCELLED + thông báo | 8.2 |
| Q-7 | Trước khi đặt SL/BE/TP kiểm mark: SL/BE đã vượt trigger → `close-positions` **100%** ngay; TP đã vượt trigger → **không** đóng một phần: bỏ qua TP đó + CAO, đặt lại khi mark quay về phía hợp lệ (§6A.0) | 4.5, 8.2 |
| Q-8 | Preset SL chỉ ở lớp 1; sau fill đầu `modify-tpsl-order` sang `mark_price` và xác nhận | 7.4(a) |
| Q-9 | Trước mỗi lần gửi lại: `order/detail?clientOid=`; filled/cancelled → không gửi lại; **không thấy ≠ chưa gửi**: lệnh `place` đã `sent` mà không thấy = UNKNOWN, không gửi lại trừ `VERIFIED_NOT_RECEIVED` (§6.5, 6A.8) | 7.5, 8.5(3) |
| Q-10 | Phát hiện vị thế lớn hơn tổng fill công cụ → CAO, dừng re-price TP, **chặn mọi `ladder edit` làm tăng WCL** của leg đó, hỏi anh | 8.2 |
| Q-11 | Một hằng `HARD_LEVERAGE_MAX_PER_SYMBOL = 50`; bậc quy định leverage cài (10×/20×); công cụ chỉ `set-leverage` khi symbol không có vị thế/lệnh; còn lại `selftest` hướng dẫn hạ tay | R17, A.1 |
| Q-12 | §8.4 | R18–R20 |
| Q-13 | Cổng **P1** = U1–U2, U4–U16, U19a, U20–U25, U28–U38, U40, U42–U48, U50, U52, U53, U55–U57, U69 (phần Kiểm soát), U73, U74, phần Wide của U44/U51/U68, D1–D14, D16–D23, D25, D30, D31, D39. **Bật `reduce` market** (không chặn go-live P1) = D26 + D28 + U71 + U72 + D38 (chỉ `position_persist`). **Tự gửi lại lệnh `place` sau crash** (tuỳ chọn; không có thì không bao giờ tự gửi lại) = D32. **Dựng lại mốc ngày** (tuỳ chọn; không có thì đi nhánh UNKNOWN) = D33. **P1b** = U3', U19b, U26–U27, U41 (maker), U54, U58, phần Scalp của U44/U51/U68, D15, D24, D27. **P2** = U17–U18, U39 (+ cổng 6.8). **Hiển thị số kỳ vọng** của một bậc = B9 (Mạo hiểm + B6, xô + B8). **PN (Nonstop)** = cổng Demo P1 đạt + U58 + U59–U67 + U68 (sổ nonstop) + U69 (phần Nonstop) + U70 + D34–D37 + C30–C40 đã trả lời (§6B.7). Đã rút: U49, D29. Demo Wide ≥ 20 thang, Scalp ≥ 10 trước khi bật xô | 10, 11 |
| Q-14 | Sửa 1.5 ("micro-grid không stop, không trần" ngoài phạm vi; Scalp có trần thì trong phạm vi). **B4 thành cổng**: bật xô mạo hiểm live chỉ sau B8 + chủ ký duyệt | 1.5, 10.5 |
| m1 | U1: SL short **2634.71** | U1 |
| m6/m12 | Thêm hằng (§10.3) và bảng DB `risk_profiles`, `bucket_ledger`, `locks`, `kill_state`, `scalp_journal` | A.1, 8.1 |
| m13 | 1 chân/plan (bỏ `--legs`) | 2.2 |

---

## 10. CLI mới / đổi [→ SPEC 2.2]

| Lệnh | Mô tả | Gửi lệnh lên sàn? |
|---|---|---|
| `profile quiz [--answers JSON]` | Bộ câu hỏi §2.1 → hồ sơ đề xuất + bảng tham số | Không |
| `profile set --tier T [--daily N --weekly N --bucket N --max-ladders N --no-trade ...] --confirm` | Tạo phiên bản hồ sơ (hạ: ngay; tăng: pending 24 h) | Không |
| `profile show / history / cancel-pending` | | Không |
| `bucket status` / `bucket refill --confirm` | Sổ phân bổ §3.1: số dư Wide/Scalp/Nonstop, đẳng thức đối soát, `deficit`; refill bị từ chối khi xô còn leg mở | Không |
| (PN) `profile set --nonstop-bucket N --confirm` + câu xác nhận; `propose --regime nonstop --symbol S --side L/S`; `execute <ref> --confirm --hash H --ack NS-…`; `bucket refill --nonstop --confirm`; `alerts list` (`alerts mute` từ chối `ns_*`) | §6B | Có (execute) |
| `propose [--symbol S --side L/S] [--mode wide|scalp] [--max 2]` | Sinh plan v1 (§4). `preview` cũ = `propose --symbol --side` | Không |
| `plan show/edit/import/diff/refresh/list` | §5 | Không |
| `execute <ref> --confirm --hash H [--reason "..."]` | Thay `execute <plan_id> --confirm`; `--reason` chỉ cho đèn đỏ trước cổng | Có |
| `ladder edit <root> ...` / `ladder apply <ref> --confirm --hash H` / `ladder close <root> --confirm` | §6; `ladder close` = 100% theo thủ tục thường §6A.10, không có `--pct` | Có (apply/close) |
| `reduce <root> --pct N \| --qty Q` / `reduce show <ref>` / `reduce apply <ref> --confirm --hash H` / `reduce status <op_id>` | §6A – chỉ đóng, **market-only ở P1, luôn huỷ mọi lớp chờ của leg**, tắt cứng tới khi D26 đạt; đường duy nhất để đóng một phần; dùng được khi khoá/kill. `--exec maker` = P1b, `--target-liq-distance` = P2, `--entries keep`/`--cancel-idx` = pha sau (từ chối) | Có (apply) |
| `entries <root> --cancel IDX[,…] \| --cancel-all` / `entries apply <ref> --confirm --hash H` | `entry_adjust`: chỉ huỷ lớp chờ, không bao giờ gửi lệnh đóng; luôn bật | Có (apply) |
| `ops list` / `ops show <op_id>` | Nhật ký bước §6.5, trạng thái RECOVERING/PENDING_RECONCILE/FAILED_SAFE, khoá `UNRESOLVED_CLOSE` | Không |
| `ops clear <op_id> --confirm` | Gỡ khoá `UNRESOLVED_CLOSE` sau ≥ 24 h dò nền không thấy X (6A.8, C42); preview in qty X, số lần dò, size hiện tại | Không |
| `liq [--json]` | Liq một leg + xấu nhất toàn TK cho mọi leg, ngưỡng cảnh báo bậc | Không |
| `cancel <root>` | Huỷ entry chưa khớp + TP; giữ SL nếu còn vị thế | Có |
| `kill` / `kill --close-positions --confirm-close` / `resume --confirm` | §9.3; `--close-positions` = thủ tục khẩn §6A.10 | Có |
| `digest [--send]` | §8.2 | Không |
| `lock status` | khoá đang có, thời điểm mở (UTC+7) | Không |
| `ta --simple` | 4 dòng đèn §7.2 | Không |
| Bỏ | `--variant`, `--legs`, `--override-avoid` (thay bằng `--reason`), `scalp preview/execute` (gộp vào `propose --mode scalp` / `execute`) | – |

### 10.1 Kiểm tra mới (bổ sung bảng 5.2)

| # | Kiểm tra | PASS | FAIL |
|---|---|---|---|
| R26 | Giờ cấm | `now ∉ no_trade` | Chặn execute/propose |
| R27 | Trần hồ sơ + tham số theo chế độ | R27w (Wide) hoặc R27s (Scalp) theo `mode` của plan (§2.5); `profile_version == active` | Chặn |
| R28 | Ngân sách xô (Scalp) | §3.1 | Chặn |
| R29 | Phiên bản hợp lệ | mới nhất của root, chưa hết hạn, `--hash` khớp, bất biến §9.5 giữ | Chặn, gợi ý refresh |
| R30 | Đèn | thay R21: xanh/vàng PASS(vàng = WARN); đỏ: trước cổng cần `--reason`, sau cổng FAIL | Chặn / cảnh báo |
| R14' | Tổng rủi ro | định nghĩa §9.2 | Chặn |
| R19' | Khoá ngày/tuần/DD | §8.4 | Chặn mở mới |

### 10.2 Cấu hình (thay khối `variant`/`risk` của A.2)

```yaml
profile_file: state/profiles/active.yaml   # không sửa tay
day_boundary_local: "07:00"
digest_time_local: "07:05"
wide: {tp_mode: plan_market, working_ttl_h: 24, be_buffer_pct: 0.05}
scalp: {layers: 4, spacing_pct: 0.20, mult: 0.87, sl_gap_pct: 1.0, slip_budget_pct: 0.3}
plan: {ttl_s: 600, equity_drift_pct: 1.0, market_shift_tol_pct: 0.3}
profile_rules: {raise_cooldown_h: 24, max_raises_per_7d: 1}
bucket: {loss_budget_frac: 0.5, min_lock_days: 7}
reduce: {plan_ttl_s: 120,   # expires_at = created_at + plan_ttl_s, bất biến (6A.8)
         drift_pct: 0.3, equity_drift_pct: 1.0, slip_est_pct: 0.1,
         step_timeout_s: 10, protect_timeout_s: 30, max_resend: 2, reconcile_window_s: 120,
         maker_enabled: false, maker_timeout_s: 60, urgent_liq_pct: 5,   # P1b
         target_enabled: false,                                          # P2
         alert_liq_pct: {than_trong: 30, can_bang: 20, mao_hiem: 10}, alert_hysteresis_pts: 2, alert_default_pct: 30}
# REDUCE_SL_MODE KHÔNG có trong cấu hình: là hằng trong mã (§10.3)
nonstop:   # PN, §6B – mọi giá trị dưới đây là ĐỀ XUẤT chờ C30–C40, chưa chốt
  enabled_tiers: [mao_hiem]          # C30
  bucket_share_pct: 10               # C31; Scalp + Nonstop ≤ HARD_RISK_BUCKET_MAX 20
  max_ladders: 1                     # C31
  min_liq_fill_path_pct: 3           # C32 (đề xuất, chưa chốt); áp cho MỌI d_k của đường khớp (6B.2 N2)
  max_multiple_x: 15                 # C33; chỉ siết thêm – trần hiệu lực = min(hồ sơ, cấu hình này, cứng) (§3.5 mục 4a)
  alert_liq_pct: [10, 5, 3]          # C34; + KHẨN dưới min_liq_fill_path_pct
  alert_multiple_x: 10               # C34; nhắc lại mỗi +5×
  alert_repeat_min: {cao: 30, khan: 5}
  alert_hysteresis: {liq_pts: 1, multiple_x: 1}
  dca_bounds: {layers_max: 12, spacing_min_pct: 0.10, mult: [0.80, 1.00], first_x_max: 10, tp_min_pct: 0.10}   # C40
day_mark: {capture_tol_s: 5, reconstruct_enabled: false, reconstruct_retry_min: 15}   # bật dựng lại chỉ sau D33 (§8.4)
alloc: {reconcile_tol_usdt: 0.05, reconcile_every_min: 15, funding_model_tol_pct: 1.0}   # §3.1
ladder_close: {settle_s: 2, confirm_zero_timeout_s: 30, emergency_max_loops: 3, emergency_retry_s: 30}   # §6A.10
unresolved_close: {probe_every_s: 60, probe_h: 24}   # 6A.8; gỡ sau probe_h chỉ bằng ops clear
```

### 10.3 Hằng cứng mới (Phụ lục A.1)

`HARD_MAX_WIDE_LADDERS = 4`, `HARD_WEEKLY_STOP_MAX = 15%`, `HARD_DD_BREAKER_MAX = 25%`, `HARD_RISK_BUCKET_MAX = 20%`, `HARD_LEVERAGE_MAX_PER_SYMBOL = 50` (thay 2 hằng leverage cũ), `HARD_PROFILE_RAISE_COOLDOWN_MIN = 24h`, `HARD_PLAN_EQUITY_DRIFT = 1%`, `HARD_MARKET_SHIFT_TOL = 0.3%`, `HARD_TP_MODE_DEFAULT = plan_market`, `HARD_REDUCE_URGENT_MIN = 3%` (ngưỡng khẩn không được cấu hình thấp hơn), `HARD_REDUCE_CLOSE_ONLY = true` (mã `reduce` không có đường gọi `tradeSide=open`), **`REDUCE_SL_MODE = disabled`** (giá trị khác duy nhất là `position_persist`, chỉ đặt được bằng thay đổi mã sau khi D26 đạt và ghi `docs/decisions.md`; runtime chỉ được hạ về `disabled`; `preplace_guard` không tồn tại trong P1), `HARD_REDUCE_MAX_RESEND = 2` (chỉ cho lời gọi idempotent hoặc `VERIFIED_NOT_RECEIVED`), `HARD_LADDER_CLOSE_PCT = 100`, `HARD_SCALP_MAX_CONCURRENT = 1` (theo C28).

Nonstop (§6B, PN) **không thêm và không nới** hằng cứng nào. Mọi hằng cứng (R9a 20×, R10a 15×, `HARD_LEVERAGE_MAX_PER_SYMBOL = 50`, `HARD_RISK_BUCKET_MAX = 20%` – Scalp + Nonstop cộng chung) là **giới hạn trên của giá trị hồ sơ/cấu hình**; khi kiểm plan dùng trần hiệu lực `min(hồ sơ, cấu hình, hằng)` (§3.5 mục 4a) – hằng cứng không bao giờ thay trần hồ sơ (C33).

---

## 11. Test mới

### 11.1 Unit (tiếp U1–U19; số liệu E = 524.7 trừ khi ghi khác)

| ID | Nội dung |
|---|---|
| U1 (sửa) | SL short safe = **2634.71** (m1) |
| U3' (thay U3) | Ví dụ 4.12.4 sửa: 4 lớp 0.65/0.57/0.49/0.43, SL 2359.09, lỗ 77.98 (E 524.87) |
| U19a/U19b | Tách: khoá/chuỗi stop/DD của Wide (P1) và khoá Scalp/xô (P1b), ranh giới 07:00 UTC+7 |
| U20 | Mọi bậc × symbol × chiều PASS R13; số bảng 2.2 khớp (±1 tick / 0.01 USDT) |
| U21 | Quiz: ánh xạ P1→bậc, min(P2/P3/P5, trần), P4 theo bậc; đầu vào ngoài miền → lỗi |
| U22 | Đổi hồ sơ: hạ ngay; tăng pending 24 h; tăng bị từ chối khi có khoá / lần 2 trong 7 ngày; hỗn hợp = tăng; plan cũ mất hiệu lực |
| U23 | Phiên bản: sửa → vN+1, cũ `superseded`; execute bản cũ/hash sai/file sửa tay → từ chối; 1 root chỉ 1 bản executed |
| U24 | Edit v1→v2 §5.5: SL 2211.26, lỗ 19.12, notional 372.63; `--max-loss 15` 5 lớp → R13 FAIL (0.80%) với gợi ý |
| U25 | (Wide, R27w) Vượt trần: budget > capLeg×E_wide, max-loss > s×E_wide, layers 6, spacing 0.9% → lỗi R27, thông điệp hướng tới `profile set` |
| U26 | Sizing Scalp §3.4: size 0.19/0.17/0.14/0.12, SL 2361.77, lỗ 20.99 / 25.39; bản 2.5%: 0.09/0.08/0.07/0.06 |
| U27 | Sổ xô: E_risk/E_wide theo fill giả lập; R28; khoá khi hết ngân sách; không refill trước mốc; lãi không tăng ngân sách; overshoot trừ kỳ sau |
| U28 | WCL running edit §6.3: (a) dồn lớp → SL tự dời 2180.67; (b) huỷ lớp 5 → SL xa tối đa 2129.66, yêu cầu 2150.00 OK, 2120.00 FAIL; (c) vượt trần notional FAIL; property test 10.000 bộ: sau mọi sửa được chấp nhận `WCL ≤ L_run` |
| U29 | (Kiểm soát) Thứ tự áp dụng §6.4 (sàn giả lập): SL_TIGHTEN trước PLACE_ENTRY; SL_LOOSEN sau cùng; lệnh định huỷ đã khớp → tự siết SL + `applied_partial`; modify SL lỗi → không bước rủi ro nào chạy; **không bao giờ có thời điểm leg có vị thế mà 0 pos_loss** (kiểm trên mọi trạng thái trung gian) |
| U30 | Không tự dời SL xa: mọi đường code dời SL xa đều xuất phát từ phiên bản đã duyệt có `--sl` rõ ràng |
| U31 | `kill` → mỗi leg **Kiểm soát** còn vị thế đúng 1 pos_loss (leg Nonstop không SL: liệt kê "KHÔNG có SL", không tạo SL), watcher `PROTECT_ONLY`; `kill --close-positions` huỷ SL chỉ sau size = 0 |
| U32 | `plan_market`: không có close limit treo; `fail_execute` của pos_loss → close-positions + KHẨN |
| U33 | E đóng băng & `market_shift`: SL không đổi với E 500/524.7/550; dịch 0.2% → execute với size giữ nguyên; dịch 0.4% hoặc E lệch 1.2% → từ chối; BTC size đổi do E → từ chối |
| U34 | Đèn: map OK/CAUTION/AVOID/thiếu dữ liệu; đề xuất chỉ xanh; đỏ trước cổng cần `--reason` ≥ 10 ký tự; sau cổng FAIL không override; nhãn "không phải dự báo" có trong mọi đầu ra |
| U35 | `propose` xác định; xếp hạng §4.4; thu nhỏ theo bước 10% giữ nguyên SL; bỏ ứng viên dưới 50% trần |
| U36 | Digest/thông báo: số liệu lấy từ `derived` (không lệch), có câu thành thật, giờ UTC+7 |
| U37 | R14' tính với size thật/giá khớp thật/TP1_DONE ≈ 0/Scalp + trượt; Cân bằng 4 thang 18.62%; Mạo hiểm 3 Wide + Scalp 20.82% |
| U38 | Mô hình liq 6A.2: (A) 2159.72 / 9.47%; giảm 20/30/50% → 11.89 / 13.70 / 19.38%, realized −4.17 / −6.35 / −10.62, WCL 66.84 / 61.01 / 49.61 (±0.01); (B) xấu nhất có L4 = 9.65% vs một leg 12.16%; giảm 30% keep / cancel = 12.81 / 17.51%, WCL 62.02 / 49.80; chỉ huỷ L4 (entry_adjust) 12.16% / WCL 65.76; giá trị mô hình cho trường hợp giữ lớp (không có ở P1): (thu L4 0.30 + giảm 30%) 13.95% / 58.32, giảm 50% giữ 16.30% / 51.38; TP sau giảm 20/30/50% (A) = 0.86/0.86, 0.75/0.75, 0.53/0.54; Wide ~71.7% → ~92.8% |
| U39 | **(P2)** `--target-liq-distance`: (A) 10% → 0.11 ETH, 12% → 0.44 ETH; (B) keep 10% → 0.08, cancel → 0; đơn điệu theo k; không đạt → thông báo + gợi ý cancel; mmr = max(API bậc, floor) |
| U40 | Close-only: bảng hedge mode (đóng long = buy+close, đóng short = sell+close), không `reduceOnly`, không đường nào tạo `tradeSide=open`; size floor lot, phần còn lại ≥ minTradeNum hoặc 0; 100% → `close-positions` có holdSide. **RECONCILING kiểm chế độ tài khoản trước khi gửi**: `posMode ≠ hedge_mode` (vd `one_way_mode`), `marginMode ≠ crossed` (TK hoặc vị thế `isolated`), productType ≠ `USDT-FUTURES`, leg không có vị thế đúng `holdSide` → mỗi trường hợp `ABORTED`, **0 lệnh gửi**, thông báo giá trị thật |
| U41 | **(P1b)** Chọn thực thi khi bật maker: liq < 5% → market; ≥ 5% → maker ở ask/bid, đặt lại 1 lần khi bị từ chối, timeout 60 s → hỏi; rơi dưới khẩn khi đang chờ → KHẨN + đề xuất, không tự chuyển; khớp một phần cập nhật Q/TP/WCL |
| U42 | Thứ tự: huỷ **mọi** lớp chờ + mọi TP của leg trước, xác nhận, rồi mới close (không có keep/shrink trong reduce P1; `kind: reduce` với `entry_policy ≠ cancel_all` hoặc thiếu một lớp chờ → từ chối); lớp định huỷ đã khớp → `FAILED_SAFE`, TP đặt lại cho size thật; TP sau đóng theo bảng 6A.5 – (a) ACTIVE, T1 chưa khớp: 0.75/0.75 từ 1.50, khớp một phần 0.20 → 0.97/0.97 từ 1.94; (b) ACTIVE, T1 đã khớp một phần x → TP1 còn lại `floor(f1·(Q'+x)) − x`, không dời BE; (c) TP1_DONE → chỉ T2 = Q'; (d) PROTECT_ONLY → không TP; (e) Q' = 0 → dọn lệnh sót, không đặt SL/TP; SL giá không đổi; đúng 1 pos_loss **chỉ khi Q' > 0** |
| U43 | Bộ đếm: khoá ngày/tuần chỉ thêm phí + trượt (vd −18.17 → −19.09); WCL & ngân sách xô tính realized một phần; không tính vào chuỗi stop; reduce chạy được khi khoá ngày/tuần/DD/xô và `PROTECT_ONLY`, bị chặn khi `RECONCILING`/`DRIFT` |
| U44 | Cảnh báo thanh lý: ngưỡng theo bậc, hysteresis 2 điểm, KHẨN mỗi 5 phút dưới 5%, bản dựng sẵn = entry_adjust nếu riêng huỷ lớp đạt ngưỡng + 2, nếu không reduce 30% huỷ mọi lớp chờ (P1; không tự giải khối lượng), chỉ entry_adjust/`ladder close` 100% khi `REDUCE_SL_MODE = disabled`; **không bao giờ tự thực thi**; kiểm tra thêm lớp Scalp dùng `max(3%, ngưỡng bậc)` |
| U45 | `entry_adjust`: khối lượng giải ra = 0 → tạo `kind: entry_adjust`, **0 lời gọi `place-order tradeSide=close`** (kiểm mock); ví dụ 6A.7(B) huỷ L4 → 12.16% / WCL 65.76; chạy được khi `REDUCE_SL_MODE = disabled` và khi đang khoá; `--qty 0` với `kind: reduce` bị từ chối |
| U46 | Băm canonical §5.4: vector cố định (bản ghi → chuỗi canonical → SHA-256); đổi bất kỳ trường nào của `hash_content` (close_qty, qty_source, exec_mode, entry_actions, preconditions, tolerances, expires_at) → hash khác; đổi `status`/`edit_log.text` → hash không đổi; float trong bản ghi → lỗi; bản ghi DB/file bị sửa → execute/apply từ chối; `--hash` sai tiền tố → từ chối |
| U47 | Máy trạng thái reduce 6A.8 (sàn giả lập): mọi chuyển hợp lệ; tiêm lỗi ở từng bước (timeout, từ chối, lớp đã khớp khi huỷ, SL đổi trigger / size đổi trước RECONCILING, sai chế độ TK, khớp một phần, SL kích hoạt đồng thời → Q' = 0, kết quả UNKNOWN) → đúng trạng thái kết thúc; **không gửi close khi RECONCILING lệch**; không gửi close khi `now ≥ expires_at`; trên **mọi** trạng thái trung gian **khi còn vị thế** leg có ≥ 1 SL bao trọn vị thế; khi vị thế về 0 không đặt SL/TP mới |
| U48 | `REDUCE_SL_MODE` và **mọi đường đóng một phần** (bảng 6A.0): `disabled` → `reduce` từ chối với thông báo; `entries` và `ladder close` (100%) vẫn được; `ladder close --pct 30` → lỗi "không có --pct; dùng reduce"; `scalp scaleout` bị từ chối khi reduce/maker tắt; Q-7 nhánh TP đã vượt trigger → 0 lệnh đóng, CAO; `kill --close-positions`/`on_sl_failure`/`fail_execute` chỉ gửi `close-positions` 100%; quét mã: mọi `place-order tradeSide=close` với size < vị thế chỉ từ executor 6A.8; giá trị `preplace_guard` không parse được; không có khoá cấu hình/biến môi trường nào bật được; runtime phát hiện SL mất sau reduce → hạ về `disabled`, KHẨN, đặt pos_loss |
| U49 | **Rút ở r3** (`preplace_guard` ngoài phạm vi, §6A.0). ID không dùng lại |
| U50 | Phục hồi §6.5 + RECOVERING 6A.8: crash sau mỗi trạng thái bước (planned/sent/confirmed) của `execute`, `ladder apply`, `reduce apply`, `entries apply` → hành động đúng quy tắc; bước tăng rủi ro không bao giờ gửi lại; `cancel`/`modify` gửi lại được; close `planned` chưa `sent` → chỉ gửi nếu `now < expires_at` (cùng một `expires_at` của phiên bản, không tính lại từ lúc duyệt hay lúc khởi động) và đối soát đạt; close `sent` + không thấy → PENDING_RECONCILE, 0 lần gửi lại (khi chưa có D32); crash sau `expires_at` → không gửi; `observed_state` đúng; tiếp tục chỉ bằng phiên bản mới |
| U51 | Ràng buộc Wide/Scalp §3.5: 1 thang/(symbol, holdSide) qua mọi chế độ; ma trận cap (cái chặt nhất thắng, R10w vs R10a); R14 phần Wide = bậc − per_ladder_scalp; `propose` bỏ cặp có Scalp; Cân bằng có xô: Wide ≤ 3 khi Scalp mở; Scalp ≤ 1; leverage symbol dùng chung |
| U52 | Khoá §8.4: ranh giới 06:59:59 / 07:00:00 UTC+7 (ngày) và thứ Hai 07:00 (tuần); chuyển tiền bị loại; phí reduce tính vào; không mở khi E hồi; ma trận được/chặn đủ các ô (gồm cột UNKNOWN); khoá không huỷ lệnh chờ Wide và mô phỏng lệnh chờ Wide khớp trong lúc khoá → vị thế tăng, thông báo đúng câu "chặn gửi lệnh mở mới… vẫn có thể khớp"; không còn khoá ngày Scalp riêng; không còn cờ `day_start_late` |
| U53 | Nhãn kỳ vọng §2.6: digest/status/README chỉ in số từ B9 có `config_hash` khớp; trước B9 **mọi bậc, kể cả Cân bằng**, in "chưa kiểm định bằng backtest"; chuỗi "+38", "+41.6", "+22.9", "0.67 USDT/ngày", "cận trên" không xuất hiện trong đầu ra cho bậc nào |
| U54 | **(P1b) Scalp end-to-end** (sàn giả lập): `propose --mode scalp --symbol ETHUSDT --side long` với ví dụ §3.4 → v1 PASS R27s (4 lớp, d 0.20%, TP_a 0.15%, TP_b 0.20%); `plan edit v1 --tp2 0.25` → v2 PASS R27s (size không đổi 0.19/0.17/0.14/0.12); `execute v2 --confirm --hash` → 4 lệnh post-only đúng giá/size của v2, clientOid `gsc1-`; hồi quy: cùng plan qua R27w → FAIL (chứng minh validator tách đúng); Scalp `--spacing 0.14` / `--layers 13` / `--tp1 0.10` / `--budget` → lỗi R27s đúng thông điệp |
| U55 | TP sau reduce theo trạng thái (bảng 6A.5): đủ 5 dòng; khớp một phần close; T1 đã khớp một phần trước khi bị huỷ; TP không được đặt khi PROTECT_ONLY; Q' = 0 → không có lệnh mới nào, lệnh sót bị huỷ, leg CLOSED; FAILED_SAFE sau khi đã huỷ TP → TP đặt lại cho size thật |
| U56 | **Sàn nhận lệnh nhưng phản hồi và dữ liệu tra cứu đều trễ**: mock nhận close X và khớp, HTTP timeout, `order/detail` trả "không thấy" trong 40 s, `fills`/`single-position` cập nhật ở giây 45 → op ở PENDING_RECONCILE, **0 lần gửi lại**, giây 45 xác định filled → UPDATING_PROTECTION với size thật; biến thể không bao giờ xuất hiện trong 120 s → FAILED_SAFE `close_unknown`, phiên bản mới có `prior_unknown_op` và cảnh báo trong preview; biến thể lỗi 5xx; biến thể đã có D32 (mock từ chối trùng clientOid) → gửi lại cùng clientOid chỉ khi `now < expires_at`; biến thể TP `place` UNKNOWN → không đặt TP lần hai |
| U57 | Mốc ngày §8.4: (a) mốc 07:00 E = 500.00 đã lưu, khởi động lại lúc E = 450.00 → `daily_pnl` = −50.00 (khoá Cân bằng 5% = −25.00 kích hoạt); (b) không có mốc, `reconstruct_enabled=false` → UNKNOWN: `execute`, `ladder apply` có PLACE_ENTRY, watcher đặt lớp Scalp, `bucket refill`, tăng hồ sơ bị chặn; `reduce`/`entries`/`cancel`/`ladder close`/`kill`/SL_TIGHTEN được; (c) dựng lại với bill/fill/nến giả lập → đúng `E_day_start` (±0.01); (d) hai cách tính `W_07` lệch, thiếu trang, lỗi endpoint, thiếu nến mark → UNKNOWN; (e) hết UNKNOWN ở mốc 07:00 kế tiếp; tuần tương tự với thứ Hai 07:00 |
| U58 | **(P1b; sổ `nonstop` ở PN)** Sổ phân bổ §3.1 – mô hình dòng: fill mở L1 → 1 dòng `open_fee` ghi ngay, `used` tăng ngay; **một** fill đóng → **2 dòng** `close_pnl` + `close_fee` cùng `tradeId`, khoá `(fill, tradeId, line_type, ledger)` khác nhau, cả hai được ghi (hồi quy lỗi trùng khoá cũ); phát lại cùng fill/bill (khởi động lại, đối soát 15 phút) → 0 dòng mới; funding: bill F trên symbol chỉ có Wide → 1 dòng `wide = F`; symbol có Wide + Scalp + Nonstop → 3 dòng, `scalp`/`nonstop` = round2(f_k), `wide = F − scalp − nonstop`, **tổng 3 dòng = F đúng tới 0.01** (property test 10.000 bill ngẫu nhiên: long/short, rate âm/dương, Q = 0 ở một sổ); lệch mô hình > max(0.01, 1%) → CAO; `worst_loss` của thang đang mở không tính lại phí mở/realized đã ghi; R28 dùng giá trị mới ngay |
| U59 | (PN) Tách chế độ: `regime` trong schema + hash; plan cũ không có `regime` → `kiem_soat`, mọi test Kiểm soát cũ không đổi kết quả; R27n: Nonstop không SL/không TP PASS; TP 0.10% PASS + in lãi ròng 0.02%; TP 0.09% FAIL; `d` 0.09% FAIL; 13 lớp FAIL; SL nằm sau giá liq khớp đủ → FAIL "SL vô dụng"; trước PN → từ chối |
| U60 | (PN) N2 theo **đường khớp** (6B.2, mô hình §6A.2): tái tạo bảng 6B.8 (±0.01): 16.34× → 2260.44 / 5.39%; 32.73× → 2334.19, đường 9.56 / 4.79 / 3.16 / 2.30%; 60.05× → 2359.36 / 0.21%; **25.64× (5× / 0.87 / 0.15% / 8) → min d_k 2.78% ở L8 → FAIL ở 3%** (bằng chứng không dùng quy đổi bội số); ~95× → 8/13 lớp tới được → FAIL "không khớp đủ được trước thanh lý"; mô hình liq giả lập cho `d_k` không đơn điệu → FAIL đúng ở lớp có min (kiểm **mọi** k, không chỉ lớp cuối); `ladder apply` trên thang đã khớp 2 lớp → đường tính từ giá/size khớp thật; leg khác cùng chiều + lớp chờ của nó → liq gần hơn; leg ngược chiều chỉ tính MM; ngưỡng đọc từ `nonstop.min_liq_fill_path_pct`; quét mã: không có bảng/hàm quy đổi bội số ↔ khoảng cách trong đường kiểm |
| U61 | (PN) N1/N3 + sổ Nonstop: N1 dùng trần hiệu lực (U69), tính mọi leg khi khớp đủ; R10w không áp; tổng xô Scalp + Nonstop > 20% → từ chối; sổ `nonstop` ghi theo mô hình dòng §3.1 (như U58); khoá xô ở 50% → chặn mở mới, **0 lệnh huỷ/đóng**; preview in "có thể mất toàn bộ tài khoản" |
| U62 | (PN) Xác nhận rủi ro: bật Nonstop cần đúng câu, là tăng rủi ro (pending 24 h, từ chối khi khoá, 1 lần/7 ngày, bậc theo C30); mỗi `execute`/`ladder apply` tăng rủi ro cần `--ack NS-<hash6>-<min_d_pct>` của đúng phiên bản; mã của phiên bản cũ → R29 FAIL; preview có "KHÔNG CÓ SL", liq khớp đủ (giá + %), đường `d_k`, bội số × vốn, trần hiệu lực |
| U63 | (PN) Cảnh báo 6B.4: vào mức → báo ngay; leo mức → báo ngay; ở yên → nhắc 30 / 5 phút; hồi + trễ 1 điểm / 1× mới thoát; tin "đã hồi"; `alerts mute` / giờ yên lặng bị từ chối với `ns_*`; KHẨN qua chat + email; **cảnh báo `ns_*` gây ra 0 lệnh can thiệp** (mock sàn: 0 `cancel-order`, 0 `place-order tradeSide=close`, 0 `close-positions`, 0 `pos_loss` mới, 0 phiên bản reduce dựng sẵn do cảnh báo); trong cùng kịch bản, quản lý TP/SL **theo plan** vẫn chạy và được phép: fill lớp mới → đặt lại TP đã duyệt (nếu plan có TP); leg có SL đã duyệt bị mất → đặt lại đúng giá (I1n); các lệnh này mang `cause=plan` và không bị tính là can thiệp |
| U64 | (PN) Phạm vi SL §6B.5: leg Nonstop không SL → SPEC 8.2(3) không đặt `pos_loss`, không `close_leg`, `fail_execute`/Q-7 không áp; Nonstop có SL bị mất → đặt lại đúng giá + KHẨN, không `close_leg`; reduce RECONCILING kỳ vọng 0 SL (thấy SL lạ → ABORTED); §6.5 ngoại lệ đặt `pos_loss` không áp cho leg không SL; R14 không cộng leg không SL và preview Kiểm soát in câu cảnh báo khi có Nonstop mở |
| U65 | (PN) Cùng tồn tại 6B.6: Nonstop + Kiểm soát cùng (symbol, holdSide) → R6 FAIL; khác chiều → được; tổng thang ≤ 4, Nonstop ≤ 1; leverage symbol dùng chung; khoá ngày/tuần/DD/UNKNOWN chặn `execute` Nonstop và thêm lớp, lệnh chờ Nonstop không bị huỷ |
| U66 | (PN) Thanh lý: bill `burst_long_loss_query` / `force_close_long` → KHẨN, tắt Nonstop (bật lại theo 6B.1), tính 1 SL trong chuỗi stop, sổ Nonstop ghi lỗ |
| U67 | (PN) Mã xác nhận không vòng tròn (§5.4, 6B.3): `hash_content` không có trường `ack*`; đổi qty một lớp / SL / giá entry → phiên bản mới, `content_hash` khác **và** `ack_expected` khác; ghi `approvals` (mã đúng, mã sai) → băm lại bản ghi plan cho đúng `content_hash` cũ (không đổi); `ack_expected` tính lại từ bản ghi đã lưu = mã trong preview; mã của phiên bản cha → rejected; mã đúng hash nhưng sai `min_d_pct` → rejected |
| U68 | Sổ phân bổ chung §3.1 (phần Wide: P1; xô Scalp: P1b; xô Nonstop: PN): (a) E 524.70, xô Scalp 10% + Nonstop 10% vừa cấp → `E_wide_sizing` = **419.76** (không phải 472.23); share 0 → `E_wide_sizing = E`; (b) chuỗi sự kiện giả lập (fill mở/đóng ở cả 3 sổ, funding 3 phần, chuyển tiền, bill lạ) → đẳng thức `E_wide + E_risk + E_ns = E` giữ (±0.05) sau mỗi sự kiện; bỏ một fill khỏi luồng → đẳng thức lệch → chặn tăng rủi ro; tải lại → hết lệch; (c) xô Nonstop âm −20.00 → `E_wide_sizing` = E − max(0, E_risk) (phần thiếu trừ vào Wide), xô khoá, `deficit` 20.00 hiển thị; (d) `bucket refill` khi xô còn leg mở → từ chối; sau khi đóng hết → `sweep` (âm hoặc dương) về `wide` + `alloc` mới = share × E_now, tổng không đổi; (e) `--nonstop-bucket 0` khi còn vị thế Nonstop → chặn mở mới, `alloc` giữ, `E_wide_sizing` không tăng; leg về 0 + hết lệnh chờ → tự `sweep` |
| U69 | Trần hiệu lực §3.5 mục 4a (Kiểm soát: P1; Nonstop: PN): Mạo hiểm (cùng chiều 5×, tổng 7×) – thang Nonstop/Scalp/Wide đưa cùng chiều lên 6.10× → R10a/N1 FAIL với thông báo nêu 5× của hồ sơ (không phải 15×); tổng 7.5× → FAIL theo 7× (không phải 20×); Cân bằng không xô → R9a dùng 3.0×; hồ sơ có `params.nonstop.samedir_x` 6× > 5× → `profile set` từ chối; giá trị hồ sơ > hằng cứng → từ chối; cấu hình `nonstop.max_multiple_x` 3× → trần hiệu lực 3×; quét mã: mọi so sánh cap đi qua một hàm `limit_eff(...)` |
| U70 | (PN) Reduce leg Nonstop **không SL** đầy đủ (sàn giả lập, `REDUCE_SL_MODE = position_persist`): `reduce <root> --pct 30` → preview `sl_policy: none` → `reduce apply --confirm --hash` → RECONCILING (0 SL kỳ vọng, đạt) → CANCELLING_ENTRIES (mọi lớp chờ + TP) → CLOSING (không đòi `pos_loss`) → UPDATING_PROTECTION (TP đặt lại nếu plan có TP; xác minh 0 SL; **0** lệnh `pos_loss` được tạo) → **DONE**; biến thể có một SL lạ trên sàn trước CLOSING → FAILED_SAFE, không đóng; biến thể `sl_policy: approved` mất SL trước CLOSING → không đóng; biến thể Kiểm soát không đổi kết quả U47 |
| U71 | Khoá `UNRESOLVED_CLOSE` (6A.8): close X → UNKNOWN → khoá ghi DB trước khi trả lời; **khởi động lại** → khoá nạp lại, vẫn chặn; khi khoá: `reduce` mới, `execute` cùng (symbol, holdSide), `ladder apply` có PLACE_ENTRY/SL_LOOSEN, watcher đặt lớp → từ chối; `entries --cancel`, SL_TIGHTEN, watcher đặt `pos_loss` thiếu, đặt lại TP theo size thật, `kill` → được; `ladder close` khi khoá → `close-positions` size thật; mock X khớp muộn sau đó → không có lệnh đóng thứ hai do công cụ, tổng đóng ≤ size ban đầu; khoá giữ sau `CLOSED` và chặn `execute` mở lại; X xác định được → tự gỡ (`resolved`); `ops clear` trước 24 h → từ chối; sau 24 h → gỡ, preview reduce kế tiếp in "tổng có thể đóng = 0.30 (mới) + 0.64 (X) = 0.94; size hiện tại 2.14" |
| U72 | Phạm vi `expires_at` (6A.8, §6.5 mục 7): close gửi lúc `expires_at − 5 s`, phản hồi trễ, xác định `FOUND` filled lúc `expires_at + 30 s` → UPDATING_PROTECTION chạy, TP đặt lại theo bảng 6A.5, dọn lệnh sót, DONE; **0** lệnh đóng mới sau hạn; CANCELLING_ENTRIES bắt đầu trước hạn, xong sau hạn → không CLOSING, `FAILED_SAFE` + đặt lại TP; RECOVERING sau hạn với CLOSING `planned` → không gửi, `FAILED_SAFE` + đặt lại TP; RECOVERING sau hạn với CLOSING `sent` + `FOUND` → UPDATING_PROTECTION hoàn tất |
| U73 | `ladder close` thủ tục thường §6A.10 (sàn giả lập): có 2 lớp chờ; lớp 4 khớp trong lúc huỷ → SETTLING bắt fill trễ → `close-positions` đóng size thật (gồm lớp 4) → size 0 → mới huỷ SL; huỷ lớp bị từ chối/UNKNOWN → không đóng, FAILED_SAFE, SL giữ, gợi ý thủ tục khẩn; fill trễ hơn sau CLOSING → lặp ≤ 3 → size 0; kết thúc: 0 lệnh của leg trên sàn; sai chế độ TK → 0 lệnh |
| U74 | Thủ tục khẩn §6A.10: `kill --close-positions`, `on_sl_failure: close_leg`, `fail_execute` SL, Q-7 SL vượt trigger → `EMERGENCY_CLOSING` ghi DB trước; `close-positions` gửi **trước** huỷ entry; entry khớp ngay sau close → vòng kiểm đóng lại; huỷ entry lỗi lần đầu → gửi lại; kết thúc chỉ khi size 0 **và** 0 entry; watcher không đặt entry/TP cho leg ở `EMERGENCY_CLOSING`/`CLOSED` (kể cả sau `resume`); hết 3 vòng chưa đạt → KHẨN mỗi phút, tiếp tục mỗi 30 s; SL chỉ huỷ sau size 0; Nonstop không SL: chỉ `kill --close-positions` kích hoạt, ba kích hoạt tự động không áp |

### 11.2 Demo (tiếp D1–D17)

| ID | Kịch bản | Kỳ vọng |
|---|---|---|
| D18 | TP `profit_plan` market + `pos_loss` cùng tồn tại; SL kích hoạt trước TP | Đóng hết vị thế; TP không chặn SL |
| D19 | `modify-tpsl-order` pos_loss dời gần rồi dời xa | Không có thời điểm nào thiếu SL (log `orders-plan-pending` mỗi 1 s) |
| D20 | Đặt pos_loss thứ 2 khi đã có 1 (B.3 #8) | Ghi nhận: cùng tồn tại / thay thế / lỗi → chọn nhánh §6.4 |
| D21 | Running edit: dời 2 lớp, thêm size, SL tự siết; và huỷ lớp + SL xa | Thứ tự §6.4 đúng; lệnh cũ huỷ, lệnh mới clientOid rev+1 |
| D22 | Running edit trong lúc lớp định huỷ khớp | `applied_partial`, SL tự siết, thông báo |
| D23 | `kill` khi có 2 leg có vị thế; `resume` | SL còn nguyên; TP đặt lại sau resume |
| D24 | Xô mạo hiểm: 2 lần SL Scalp → khoá xô | Entry Scalp huỷ, Wide không ảnh hưởng |
| D25 | Một ngày đầy đủ: digest → sửa → duyệt → fill → TP1 → khoá ngày giả lập | Thông báo đúng mẫu, đúng giờ UTC+7 |
| D26 | **Cổng `position_persist`** (cổng duy nhất để bật reduce một phần). Hedge mode, có cả long và short ETH: (1) market `buy+close` 30% long; (2) `orders-plan-pending` mỗi 1 s trong 60 s: `pos_loss` long luôn tồn tại, trigger không đổi; (3) cho mark chạm SL → đóng **đúng toàn bộ phần còn lại**, short nguyên; (4) lặp sau khi một lệnh entry đặt tay khớp sau reduce (mô phỏng fill đang bay) – SL vẫn bao size mới; (5) ghi lại giá trị `posMode`/`marginMode` mà `account` và `single-position` trả về (dùng cho U40) | Mọi bước đạt → được đặt `REDUCE_SL_MODE = position_persist`. Bất kỳ bước nào FAIL → reduce một phần giữ `disabled` (C24); không có phương án thay thế ở P1 |
| D27 | **(P1b)** Reduce maker post-only ở ask: khớp một phần, timeout 60 s, huỷ phần còn lại | Phần khớp ghi đúng; lệnh limit close không làm SL đóng thiếu (kết hợp D9) |
| D28 | Reduce market khi đang khoá ngày và khi `kill` PROTECT_ONLY (sau khi reduce bật); `ladder close` (100%) | Được phép; 100% dùng `close-positions` holdSide, xác nhận size = 0 rồi mới huỷ SL/TP |
| D29 | **Rút ở r3** (`preplace_guard` ngoài phạm vi, §6A.0). ID không dùng lại | – |
| D30 | Kill tiến trình khi reduce đang ở CANCELLING_ENTRIES, CLOSING (đã gửi, chưa xác nhận) và UPDATING_PROTECTION; và khi `ladder apply` đang ở PLACE_ENTRY | Khởi động lại → RECOVERING đúng §6.5/6A.8; không lệnh trùng; không bước tăng rủi ro nào gửi lại |
| D31 | `entries --cancel` khi đang khoá ngày và khi `REDUCE_SL_MODE = disabled` | Chỉ huỷ lớp; không có lệnh đóng nào trên sàn |
| D32 | **Chống trùng clientOid** (cơ chế cho `VERIFIED_NOT_RECEIVED (b)`): gửi lệnh với clientOid X (được nhận, rồi khớp / bị huỷ / còn treo); gửi lại đúng X sau 1 phút, 1 h, 24 h; lặp với `place-tpsl-order` | Mọi lần gửi lại bị từ chối bằng **một mã lỗi xác định** và không tạo lệnh thứ hai → được bật gửi lại cùng clientOid khi `now < expires_at`. Bất kỳ lần nào tạo lệnh mới hoặc mã lỗi không ổn định → **không bao giờ tự gửi lại** lệnh `place` đã `sent` |
| D33 | **Dựng lại mốc ngày** (§8.4 nhánh 2): watcher lưu mốc 07:00 thật; sau đó tắt watcher, có fill/funding/chuyển tiền nội bộ trong ngày, rồi dựng lại từ `account/bill`, `order/fills`, `position/history-position`, `market/history-mark-candles`; đồng thời ghi bill funding có/không có holdSide | Sai lệch so với mốc thật ≤ 0.05 USDT trong 5 ngày thử → được bật `reconstruct_enabled`; ghi cách chia funding Wide/Scalp có khớp bill không (U58). FAIL → giữ tắt, luôn đi nhánh UNKNOWN |
| D34 | (PN) Thang Nonstop nhỏ không SL trên Demo (vốn Demo nhỏ để bội số thật): khớp vài lớp | Watcher không đặt SL, không đóng/huỷ gì; TP mỏng (nếu có) đặt lại sau mỗi fill; cảnh báo `ns_*` đúng mức và đúng nhịp |
| D35 | (PN) So liq ước tính (§6A.2, 6B.8) với `liquidationPrice` của `single-position` khi thang Nonstop khớp nhiều lớp | Sai lệch ghi lại; nếu ước tính **xa** hơn giá sàn > 0.1% giá → hiệu chỉnh `mmr_floor` trước khi bật PN |
| D36 | (PN) Khoá ngày giả lập khi có lệnh chờ Nonstop | Không gửi lệnh mở mới; lệnh chờ đã treo vẫn khớp được; không có lệnh huỷ/đóng tự động |
| D37 | (PN) `kill` khi có leg Nonstop không SL và leg Kiểm soát | Entry + TP huỷ; leg Kiểm soát giữ SL; leg Nonstop còn vị thế không SL và được in rõ |
| D38 | **Lệnh đóng khi size đã 0 / sau UNKNOWN** (Demo, hedge mode): (1) đóng hết leg bằng `close-positions`; gửi `place-order` market `tradeSide=close` size 0.01 cho leg đó; (2) giữ một lệnh close limit (post-only, xa giá) rồi `close-positions` leg; quan sát lệnh limit bị huỷ / vẫn treo / khớp; (3) ghi mã lỗi | Ghi lại hành vi thật. Nếu sàn từ chối close khi size 0 và tự huỷ lệnh close treo khi vị thế về 0 → ghi vào `docs/decisions.md`; nếu không → giữ khoá `UNRESOLVED_CLOSE` như 6A.8 và thêm bước huỷ lệnh close treo vào CLEANUP. Không chặn P1 (reduce tắt) |
| D39 | **Đóng 100% có lớp chờ** (Demo): (a) `ladder close` khi còn 2 lớp chờ, một lớp được đặt sát giá để khớp trong lúc huỷ; (b) `kill --close-positions` với lớp chờ sát giá | (a) size 0, 0 lệnh của leg, SL huỷ sau cùng; (b) size 0 và 0 entry khi kết thúc; không có vị thế mở lại trong 10 phút theo dõi; log thời gian từng bước |

### 11.3 Backtest (tiếp B1–B5)

- **B6** (cổng bật bậc Mạo hiểm): DEFAULT trên 80% vốn, tối đa 3 thang, cap cùng chiều 2.0×, cùng engine; báo cáo 2 nửa kỳ. Và Thận trọng (0.45×/3%, 2 thang) để có số kỳ vọng hiển thị.
- **B7**: ảnh hưởng `plan_market` (taker TP) và BE theo spec so với `final_eval.csv`.
- **B8** (thay B4, là cổng): Scalp theo §3.4 với ngân sách xô, khoá xô, phí taker; chủ ký duyệt trước khi bật xô live.
- **B9** (cổng hiển thị kỳ vọng §2.6): chạy lại Cân bằng / Thận trọng / Mạo hiểm bằng **mã của công cụ** (B2) với TP `plan_market` (taker), BE theo spec, L1 post-only có mô hình khớp, độ trễ mở lại = tới digest kế tiếp (≤ 24 h) và chỉ chiều đèn xanh, khoá ngày/tuần §8.4; xuất `config_hash`. Đây là nguồn duy nhất cho số kỳ vọng hiển thị.

---

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
| C32 | (Nonstop) Ngưỡng thanh lý tối thiểu theo **đường khớp** (N2): mọi `d_k` (khoảng cách liq từ giá lớp k khi lớp k vừa khớp) | **Đề xuất 3%** (= mức "liq ≥ 3%" của SPEC 4.12.2). Không có quy đổi ra bội số: mỗi thang phải tính (vd 25.64× → 2.78% FAIL; 21.66× → 3.70% PASS). Lựa chọn khác: 2%, 1%. Kiểu 30–95× hiện tại của anh không qua 3% |
| C33 | (Nonstop) Trần bội số | **Trần hiệu lực = min(hồ sơ, cấu hình Nonstop, hằng cứng)**; hằng cứng không thay trần hồ sơ. Với hồ sơ Mạo hiểm hiện tại: **5× cùng chiều / 7× tổng** cho mọi leg kể cả Nonstop. Muốn lớn hơn: nâng trần hồ sơ (tăng rủi ro §2.4, ≤ 15× / 20× cứng); > 15× = đổi hằng + leverage 50 (đổi mã + review). Mặc định: giữ như vậy, không có trần Nonstop riêng vượt hồ sơ |
| C34 | (Nonstop) Ngưỡng cảnh báo | `ns_liq` < 10% / 5% (CAO), < 3% và < N2 (KHẨN); `ns_multiple` > **10×** và mỗi +5×; nhắc 30 / 5 phút; trễ 1 điểm / 1× |
| C35 | (Nonstop) Cho Nonstop và Kiểm soát cùng symbol + cùng chiều? | **Không** (hedge mode gộp vị thế, SL Kiểm soát sẽ đóng cả phần Nonstop); khác chiều thì được |
| C36 | (Nonstop) Khoá ngày/tuần/DD/xô với Nonstop | **Chặn** mở thang mới và thêm lớp; **không** tự huỷ lệnh chờ Nonstop (chúng vẫn có thể khớp); không tự đóng |
| C37 | (Nonstop) Reduce do anh tự gọi trên leg Nonstop | Dùng **cùng cổng** `REDUCE_SL_MODE` (D26); `ladder close` 100% và `entries` luôn được; không bao giờ dựng sẵn |
| C38 | (Nonstop) Khi bị thanh lý / SL Nonstop `fail_execute` | Thanh lý → KHẨN, tắt Nonstop, tính 1 SL trong chuỗi stop; `fail_execute` SL Nonstop → chỉ KHẨN, không tự đóng |
| C39 | (Nonstop) Pha | **PN**: sau cổng Demo P1 của Kiểm soát + U58 + U59–U67 + U68 (sổ nonstop) + U69 (phần Nonstop) + U70 + D34–D37 (§6B.7); không chờ thêm thời gian live |
| C40 | (Nonstop) Giới hạn thang `dca` (R27n) | 1–12 lớp; `d` ≥ 0.10%; `mult` 0.80–1.00; lớp đầu ≤ 10× E; TP nếu có ≥ 0.10%; SL nếu có phải trước giá liq khớp đủ |
| C41 | Xô âm (lỗ Scalp/Nonstop vượt vốn đã cấp): phần thiếu trừ vào vốn Wide dùng để tính size ngay (`E_wide_sizing = E − max(0, E_risk) − max(0, E_ns)`), xô khoá, refill chỉ khi xô không còn leg mở | Có |
| C42 | Khoá `UNRESOLVED_CLOSE` (lệnh đóng chưa xác định): chỉ gỡ khi xác định được, hoặc sau ≥ 24 h bằng `ops clear --confirm`; không có duyệt bất chấp ở P1 | Có |

(Q1, Q3 của SPEC 12 được thay bằng C1/C2; Q7 thay bằng bảng 2.2/§8.4; Q13 thay bằng C5/C6; các Q khác giữ nguyên.)
