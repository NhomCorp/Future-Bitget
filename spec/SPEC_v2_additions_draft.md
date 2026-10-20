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
| C4 | Thang đang chạy **được sửa tự do trong trần hồ sơ**, qua cùng luồng preview → diff → duyệt. Hai bất biến cứng: luôn có SL trên sàn; lỗ xấu nhất sau sửa ≤ ngân sách lỗ/thang và mọi kiểm tra tài khoản PASS | 1.5 dòng "không đổi tham số tại chỗ", 5.3 |
| C5 | **Chia vốn**: phần an toàn (Wide) + "xô mạo hiểm" ≤ 20% cho Scalp, ngân sách lỗ khoá riêng, không vay phần an toàn | 4.12.2, 4.12.5 |
| C6 | Đầu ra thị trường dạng **đèn xanh/vàng/đỏ + 1 câu**; chỉ đề xuất chiều xanh; đỏ cần gõ lý do (trước cổng 6.8) / bị chặn (sau cổng) | 2.3 dòng AVOID, R21 |
| C7 | Vận hành: bản tin sáng 07:05, thông báo sự kiện, **ranh giới ngày 07:00 UTC+7** cho mọi bộ đếm, khoá tự động | R18–R20, 4.12.5 |
| C8 | Sửa N1–N6: bỏ `aggressive`; định nghĩa lại R14 & giới hạn số thang; `kill` giữ SL; TP dạng trigger không chiếm vị thế; execute dùng E đóng băng + "bất biến được duyệt"; sửa ví dụ Scalp | xem §9 |
| C9 | Kiểm tra mới R26–R30; CLI mới; test U20–U44, D18–D28, B6–B8 | 5.2, 2.2, 10 |
| C10 | **`reduce`**: giảm vị thế chủ động (chỉ đóng) để đẩy giá thanh lý xa, cả Wide và Scalp; preview liq một leg + xấu nhất toàn TK (có lớp chờ); maker/market theo ngưỡng khẩn; dùng được cả khi đang khoá; watcher cảnh báo thanh lý theo bậc và dựng sẵn đề xuất (không tự chạy) | mới (§6A); bổ sung 4.8, 4.12.3c |

---

## 1. Luồng sử dụng mới [→ SPEC 2.1, 2.3, 2.4]

### 1.1 Nguyên tắc

1. **Không bao giờ** có lệnh *mở* vị thế nếu chủ chưa duyệt đúng một phiên bản plan (`version_id` + `hash`). Không có ngoại lệ (P4 "tự mở lại" vẫn ngoài phạm vi).
2. Công cụ đề xuất; người quyết định. Trợ lý chat chỉ là "người phiên dịch" lời nói → lệnh CLI, và PHẢI in lại lệnh đã dịch kèm diff trước khi hỏi duyệt.
3. Mọi giới hạn lấy từ **hồ sơ đang hiệu lực**; muốn to hơn thì đổi hồ sơ (lệnh riêng, có xác nhận, có thời gian chờ), không vượt trần theo từng plan.

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
    C->>T: reduce 7Q2X --pct 30 --layers cancel
    T-->>C: preview hiện tại/sau (size, liq 1 leg & xấu nhất, realized, WCL, SL, bộ đếm ngày)
    A->>C: "Duyệt"
    C->>T: reduce apply 7Q2X.v5 --confirm --hash …
    T->>X: huỷ lớp chờ → xác nhận → close (market/maker) → đặt lại TP size; xác nhận pos_loss còn nguyên
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
| P2 | "Trong một ngày, lỗ bao nhiêu % thì anh muốn công cụ tự nghỉ đến 7h sáng hôm sau?" | a) 3% · b) 5% · c) 8% |
| P3 | "Trong một tuần, lỗ bao nhiêu % thì nghỉ đến 7h sáng thứ Hai tuần sau?" | a) 6% · b) 10% · c) 15% |
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

Lý do chọn: Cân bằng = đúng phương án SAFE đã backtest (+22.9%/180 ngày, DD 19%). Thận trọng = SAFE thu nhỏ theo tỉ lệ (cùng `s/capLeg` = 6.67% → cùng vị trí SL). Mạo hiểm = tham số DEFAULT nhưng trên 80% vốn và **tối đa 3 thang** (giải N2) – **chưa backtest đúng cấu hình này → phải qua B6 trước khi bật live** (§11).

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

Ảnh hưởng: hồ sơ mới hiệu lực → mọi plan chưa execute mất hiệu lực (phải `plan refresh`); thang đang chạy **không bị ép thu nhỏ**, nhưng mọi chỉnh sửa *làm tăng lỗ xấu nhất* phải về trong trần mới (§6.3); R14/cap tài khoản cho thang mới dùng trần mới.

### 2.5 Hồ sơ đi vào preview/kiểm tra

- Bộ đề xuất (§4) sinh tham số **bằng** trần hồ sơ (hoặc thấp hơn nếu bị thu nhỏ).
- R27 (mới) kiểm mọi trường của plan ≤ trần: `budget ≤ capLeg×E_wide`, `max_loss ≤ s×E_wide`, `layers ≤ 5`, `spacing ≥ 1.0%`, số thang ≤ `max_ladders`, TP1/TP2 trong khoảng cho phép (TP1 0.6–2.0%, TP2 ≥ TP1 + 0.4%, ≤ 4%; `tp1_fraction` 0.3–1.0).
- Ngưỡng R9/R10/R14/R18–R20 lấy từ `params.account`.

---

## 3. Chia vốn an toàn / mạo hiểm [→ SPEC 4.12.2, 4.12.5, mới]

### 3.1 Sổ phụ (sub-ledger) trên một tài khoản cross

Một tài khoản cross không thể tách ký quỹ → tách **về sổ sách và quy tắc**, còn kiểm tra thanh lý/exposure luôn dùng **toàn tài khoản**.

- Khi hồ sơ có xô được kích hoạt (hoặc `bucket refill`): `E_risk_base = share × E` (đóng băng), `budget_risk = 50% × E_risk_base` (USDT, đóng băng cho kỳ).
- Tại thời điểm t:
  - `realized_risk(t)` = Σ PnL ròng (gồm phí, funding) của **mọi lệnh đóng** (toàn phần hoặc một phần, kể cả `reduce` §6A) của thang Scalp từ đầu kỳ.
  - `upnl_risk(t)` = Σ uPnL (mark) của thang Scalp đang mở.
  - `E_risk(t) = E_risk_base + realized_risk + upnl_risk`; `E_wide(t) = E(t) − E_risk(t)`.
- Wide luôn tính size/ngân sách theo `E_wide` (đóng băng ở preview); Scalp tính theo ngân sách xô.
- **Ngân sách đã dùng** `used = max(0, −realized_risk) + Σ worst_loss(thang Scalp đang mở)` với `worst_loss` = lỗ tại SL + trượt 0.3%. Lãi Scalp **không** làm tăng `budget_risk` trong kỳ (lãi ở lại xô, cuối kỳ quét về phần an toàn qua refill).
- R28 (mới, mở thang Scalp): `used + worst_loss(thang mới) ≤ budget_risk` **và** `worst_loss(thang mới) ≤ per_ladder_scalp` (bảng 2.2).
- Wide không bao giờ được tính trên `E_risk`; Scalp không bao giờ được dùng `E_wide` hay ngân sách R14 phần Wide.

### 3.2 Khoá xô

- Khoá khi `budget_risk − used_realized < 50% × per_ladder_scalp` (không đủ cho một thang nhỏ) hoặc `realized` lỗ ≥ `budget_risk`.
- Khi khoá: huỷ mọi entry Scalp chưa khớp; thang Scalp đang có vị thế giữ SL/TP; không mở Scalp mới.
- **Mở khoá**: sớm nhất **07:00 UTC+7 ngày 1 tháng sau VÀ ≥ 7 ngày kể từ lúc khoá**, rồi chủ chạy `bucket refill --confirm` (không tự refill). Refill: `E_risk_base = share × E_now`; bị từ chối nếu đang khoá ngày/tuần/DD. Đây là cấp vốn mới cho kỳ mới, không phải "vay" giữa kỳ.
- Lỗ vượt ngân sách do trượt/gap: ghi `overshoot`, hiển thị; kỳ sau `budget_risk` trừ đi `overshoot`.
- Thành thật trong README/UX: tách xô là **kỷ luật sổ sách**; trên sàn, lỗ Scalp vẫn trừ vào cùng ký quỹ cross. Vì vậy:

### 3.3 Kiểm tra toàn tài khoản (không đổi bản chất)

R9/R10/R14/R15/R16 dùng **E toàn tài khoản** và **mọi thang (Wide + Scalp + vị thế/lệnh tay)** ở kịch bản xấu nhất (SPEC 4.8(b), sửa m9: thang ngược chiều không tính lãi, vẫn tính MM). Ví dụ Mạo hiểm đầy (BTC-L, ETH-S, BTC-S Wide + ETH-L Scalp, tất cả khớp đủ): tổng 2990.39 USDT = **5.70× E**, cùng chiều long 3.79× E, short 1.90× E; giá giảm đồng loạt **~25.8%** (từ giá TB, cách tính bảo thủ) mới tới thanh lý ước tính, trong khi SL xa nhất phía long cách giá TB 5.52% → R15 PASS.

### 3.4 Scalp trong xô – tham số & ví dụ [thay ví dụ SPEC 4.12.4]

Sizing **ngược từ lỗ tối đa** (dễ hiểu cho người không chuyên: "mất tối đa X USDT nếu giá đi ngược thêm 1% sau lớp cuối"):
- N = 4 (mặc định, ≤ 12 cứng), d = 0.20%, mult 0.87, `SL = P_N × (1 − sg·1.0%)` (làm tròn theo bảng 4.9).
- Chọn notional lớp đầu `X` sao cho `lỗ_tại_SL(size thiết kế) + Q·SL·0.003 = L_scalp`; `q_i = floor(X·mult^(i−1)/P_i)`; kiểm lại với size đã làm tròn ≤ L_scalp.
- TP_a +0.15% (50%) / TP_b +0.20% như SPEC 4.12.2. Mọi kiểm tra R8–R17 bản Scalp áp dụng, cộng R28.

Ví dụ Mạo hiểm, ETH long, P₁ 2400.00, `L_scalp` = 5% × 524.7 = 26.235 → X = 468.08 (0.89× E):

| Lớp | Giá | Δ% | ETH | Notional | ×E lũy kế | Giá TB | TP_a | TP_b |
|---|---|---|---|---|---|---|---|---|
| S1 | 2400.00 | 0.00 | 0.19 | 456.00 | 0.87 | 2400.00 | 2403.60 | 2404.80 |
| S2 | 2395.20 | −0.20 | 0.17 | 407.18 | 1.65 | 2397.73 | 2401.33 | 2402.53 |
| S3 | 2390.40 | −0.40 | 0.14 | 334.66 | 2.28 | 2395.68 | 2399.28 | 2400.48 |
| S4 | 2385.62 | −0.60 | 0.12 | 286.27 | 2.83 | 2393.73 | 2397.33 | 2398.53 |

SL **2361.77** (−1.59% từ L1, −1.34% từ TB). Lỗ tại SL 20.99; +trượt 0.3% = 25.39 (≤ 26.235); trượt 1% = 35.64 (phải hiển thị). Lãi nếu chỉ lớp 1 về TP: **~0.62 USDT**; cả thang: ~2.01 USDT. Cân bằng (xô 10%, L 13.118): size 0.09/0.08/0.07/0.06, cùng SL, lỗ 10.12 / 12.24 (trượt 0.3%), lãi lớp 1 ~0.30 USDT.

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

| Trường | Ràng buộc (ngoài R1–R30) |
|---|---|
| `side` | đổi chiều = dựng lại thang từ anchor phía kia (bid↔ask); đèn của chiều mới áp dụng |
| `layers` | 1 ≤ N ≤ 5 (cứng); bớt lớp = bỏ lớp sâu nhất |
| `spacing` | ≥ 1.0% (cứng); áp hình học như SPEC 4.3 |
| `anchor` | giá cụ thể → `anchor.mode = fixed`; `market` → `market_shift` |
| `layer IDX=PRICE` | đặt giá riêng 1 lớp → `mode=fixed`; khoảng cách với lớp kề ≥ 1.0%; thứ tự đơn điệu theo chiều |
| `remove-layer` | đánh số lại; N ≥ 1 |
| `budget` | ≤ `capLeg × E_wide`; ngân sách/lớp = budget/N (đều) |
| `max-loss` | ≤ `s × E_wide`; nhập `%` → % của E (hiển thị cả hai) |
| `tp1`, `tp1-frac`, `tp2` | khoảng ở §2.5 |

Không sửa được: symbol, mode (Wide↔Scalp – tạo plan mới), hằng cứng, tham số tài khoản (đổi qua `profile`).

Vượt trần → lỗi rõ ràng: `"max-loss 35 USDT vượt trần hồ sơ Cân bằng (26.24 USDT = 5% E_wide). Muốn cao hơn: 'profile set …' (tăng rủi ro, hiệu lực sau 24 h)."` – không có cờ override.

### 5.3 Thứ tự tính lại (mỗi lần sửa)

1. Giá lớp (fixed/hình học, làm tròn 4.9) → 2. size `q_i = floor(B/P_i)` → 3. SL theo SPEC 4.6 với **Q thiết kế** và `L = max_loss` → 4. TP/BE → 5. liq (4.8a/b), exposure → 6. R1–R30 → 7. đèn → 8. hash. Plan FAIL vẫn được lưu thành phiên bản (để xem diff), nhưng không execute được; công cụ gợi ý cách sửa cụ thể (vd "R13: SL chỉ cách lớp 5 0.80%; giảm 1 lớp, hoặc max-loss ≥ 17 USDT, hoặc giảm budget").

### 5.4 Phiên bản

- `root_id`: 4 ký tự base32 (vd `7Q2X`); `version_id`: 8 ký tự base32 ngẫu nhiên, duy nhất, dùng trong clientOid (thay `plan_id` của SPEC 7.5; định dạng clientOid không đổi).
- Phiên bản **bất biến**. Sửa → phiên bản mới `vN+1` với `parent`; mọi phiên bản cũ cùng root chuyển `superseded` (không execute được). Mỗi root chỉ có tối đa 1 phiên bản `executed/running`.
- `content_hash` = SHA-256 của JSON chuẩn hoá (`params`, `layers`, `derived`, `frozen`, `profile.params_hash`); hiển thị 6 hex đầu. `execute`/`apply` bắt buộc `--hash` khớp.
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
status: proposed   # proposed|superseded|invalid|expired|executed|running|closed|failed|applied_partial
kind: open         # open | running_edit
created_at: 2026-10-20T07:12:40+07:00
expires_at: 2026-10-20T07:22:40+07:00
env: live
profile: {version: 3, tier: can_bang, params_hash: 4be1…}
mode: wide
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
DB: bảng `plans` của SPEC 8.1 thêm cột `root_id, version, parent, kind, profile_version, anchor_mode, frozen_json, light_json, override_reason`.

---

## 6. Sửa khi thang đang chạy [→ SPEC 1.5 "không đổi tham số tại chỗ", 5.3; quyết định của chủ 2026-10-20]

### 6.1 Phạm vi

Được sửa **tự do trong trần hồ sơ**: thêm/bớt/dời/đổi size các **lớp chưa khớp**, đổi TP1/TP2/`tp1_fraction`, đổi SL (gần hơn hoặc xa hơn – xa hơn có điều kiện, §6.3), đổi `max_loss`/`budget` trong trần, đóng một phần/toàn bộ.
Không sửa: symbol, chiều, lớp đã khớp (giá/size là sự thật của sàn), số lớp tổng (đã khớp + chưa khớp) > 5, khoảng cách < 1% giữa mọi lớp kề (kể cả giá khớp thật), hằng cứng.
Trạng thái `TP1_DONE`: chỉ sửa TP2, SL, đóng; **không thêm entry** (giữ quy tắc "ngừng DCA sau TP1" đã backtest – xem câu hỏi C8).

Lệnh: `ladder edit <root> [các cờ như plan edit, áp cho lớp chưa khớp] [--sl PRICE|be] [--add-layer PRICE[:SIZE]]... [--size IDX=QTY]...` → tạo phiên bản `kind: running_edit` (vd `7Q2X.v3`) + diff → `ladder apply <ref> --confirm --hash <h>`. `ladder close <root> --pct N --confirm` (đóng market một phần, cũng tạo phiên bản). Giảm vị thế vì thanh lý (có tính liq, lựa chọn lớp chờ, maker/market) dùng `reduce` – §6A. Cùng TTL 10 phút, cùng R1–R30 (phần áp dụng).

### 6.2 Bất biến cứng (mọi lúc, kể cả giữa các bước áp dụng)

- **(I1) Luôn có SL trên sàn**: mọi leg có vị thế có đúng 1 `pos_loss` (mark price). Không bao giờ huỷ-rồi-đặt; không có khoảng hở khi thay.
- **(I2) Lỗ xấu nhất ≤ ngân sách**: sau sửa, `WCL ≤ L_run` và R9/R10/R14/R15/R16 (toàn tài khoản) PASS.

### 6.3 Lỗ xấu nhất (WCL) và quy tắc SL

Với vị thế thật (Q_f lớp đã khớp ở giá khớp thật) + mọi lớp chưa khớp còn lại (size **thật** đã làm tròn), giả định tất cả khớp rồi chạm SL:

`WCL(SL) = sg·(C_all − Q_all·SL) + m·C_all + t·Q_all·SL + max(0, −realized_leg)`

(long: `C_all − Q_all·SL`; short: `Q_all·SL − C_all`; `C_all = Σ q·P`; `realized_leg` = PnL đã thực hiện của leg – lãi đã chốt **không** dùng làm đệm; Scalp cộng thêm `Q_all·SL·0.003`.)

`L_run = min(max_loss của phiên bản, s × E_wide_now)` (E đóng băng lúc tạo phiên bản sửa).

- SL **mặc định giữ nguyên**. Nếu `WCL(SL hiện tại) > L_run` → SL **tự động dời gần lại** tới giá nhỏ nhất (long: giá cao nhất cần thiết) sao cho `WCL = L_run` (làm tròn theo 4.9). Ví dụ: thêm/dồn lớp ⇒ SL tự kéo gần.
- **SL xa hơn chỉ khi người dùng yêu cầu rõ** và `WCL(SL mới) ≤ L_run` (vd sau khi bớt lớp/giảm size). Công cụ không bao giờ tự dời SL xa ra. Đây là đánh đổi có chủ ý: dời xa = giữ lỗ lâu hơn, nhưng tổng lỗ vẫn bị chặn bởi ngân sách.
- Ngoại lệ ngân sách cũ: nếu thang đang vượt `L_run` (vd E giảm) thì sửa **không làm tăng WCL** (đổi TP, huỷ lớp, dời SL gần) vẫn được; sửa làm tăng WCL phải đưa về ≤ `L_run`.
- SL mới phải nằm đúng phía so với mark hiện tại (long: SL < mark − 0.1%); nếu không → từ chối, gợi ý `ladder close`.
- Mọi lớp chưa khớp nằm ngoài SL mới (hoặc cách SL < 1%) bị huỷ trong cùng phiên bản.

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
- Phát hiện leg có vị thế mà không có SL > 1 vòng → KHẨN + `on_sl_failure` (SPEC Q4).

---

## 6A. Giảm vị thế chủ động để đẩy giá thanh lý (`reduce`) [mới; áp cho cả Wide và Scalp]

> Ý của chủ: "Nhiều khi đóng 1 phần vị thế không phải vì có lãi, mà vì muốn giảm volume vị thế để giá thanh lý xa hơn." `reduce` là thao tác **chỉ đóng** (close-only), làm được bất kể lãi/lỗ, không bao giờ mở thêm vị thế.

### 6A.1 Lệnh

```
reduce <root> --pct N                 # N% vị thế hiện tại (floor theo lot)
reduce <root> --qty Q                 # khối lượng base coin
reduce <root> --target-liq-distance X # tìm mức giảm NHỎ NHẤT để khoảng cách liq (xấu nhất toàn TK) ≥ X%
        [--layers keep|cancel|shrink] # lớp DCA chưa khớp; mặc định: xem 6A.4
        [--exec auto|maker|market]    # mặc định auto (6A.3)
reduce apply <ref> --confirm --hash H
```
- Tạo phiên bản `kind: reduce` (vd `7Q2X.v4`) + preview; **phải duyệt** như mọi thay đổi (bán tự động). TTL **2 phút** hoặc lệch mark > 0.3% (giá trị nhạy theo giá hơn plan mở).
- Lệnh gửi: `place-order` với `tradeSide=close`, quy tắc hedge mode SPEC 7.3 (**đóng long = `side=buy` + `tradeSide=close`; đóng short = `side=sell` + `tradeSide=close`**; không gửi `reduceOnly`). `close-positions` chỉ dùng khi giảm 100% (= đóng hẳn leg). `size` = khối lượng giảm, floor theo lot, ≥ `minTradeNum`; phần còn lại phải ≥ `minTradeNum` hoặc = 0.
- Được phép **khi đang khoá** (ngày/tuần/DD/chuỗi stop/xô), khi `kill` ở chế độ `PROTECT_ONLY`, và khi hồ sơ đang `pending` – vì chỉ giảm rủi ro. Không được trong `RECONCILING` (đợi đối soát xong) hoặc khi leg có `DRIFT` chưa giải quyết (Q-10) – khi đó chỉ được `ladder close`/`kill --close-positions`.
- `--target-liq-distance`: duyệt k = 0,1,2,… lot (đơn điệu: giảm nhiều hơn → liq xa hơn), dừng ở k nhỏ nhất đạt mục tiêu theo **mô hình 6A.2 với lựa chọn lớp đã chọn**; không đạt kể cả 100% (vì lớp chờ còn giữ) → báo và gợi ý `--layers cancel`.

### 6A.2 Mô hình thanh lý dùng trong preview [mở rộng SPEC 4.8]

- Điều kiện thanh lý cross: `W + Σ uPnL(P) ≤ Σ mmr_j·|Q_j|·P_j`, `W` = số dư ví sau mọi phí đã trả, mark price, `mmr = max(bậc MMR từ API theo notional, mmr_floor cấu hình)` (ETH 0.5%, BTC 0.4% ở ví dụ).
- **Một leg**: công thức đóng SPEC 4.8(a) với W thật hiện tại (bỏ qua leg khác) – chỉ để tham khảo.
- **Xấu nhất toàn tài khoản (con số quyết định)**: mọi giá cùng chiều leg đang xét di chuyển bất lợi cùng x% từ mark hiện tại (BTC/ETH tương quan ≈ 1); **mỗi lớp entry chờ cùng chiều được coi là khớp tại giá của nó khi giá đi qua** (đúng đường đi, có phí maker); leg ngược chiều: tính MM, **không** tính lãi (m9); SL **không** được giả định là chạy (trường hợp SL lỗi/gap – lý do tồn tại của reduce). Tìm x nhỏ nhất bằng bisection → `liq_dist_worst` và giá liq tương ứng của symbol.
- "Giảm mà vẫn giữ lớp chờ" có thể là ảo: lớp chờ khớp lại kéo liq về chỗ cũ. Vì vậy preview **luôn** in cả hai: `liq_dist_worst` khi giữ lớp và khi huỷ/thu lớp.

### 6A.3 Cách thực thi

| Điều kiện (`liq_dist_worst` trước khi giảm) | Mặc định `--exec auto` |
|---|---|
| < **ngưỡng khẩn** (mặc định 5% mọi bậc; ≥ `HARD_SCALP_MIN_LIQ_DIST` 3%) | **market** (taker 0.06%, khớp ngay) |
| ≥ ngưỡng khẩn | **maker**: limit post-only ở giá tốt nhất phía đóng (đóng long: `askPr`; đóng short: `bidPr`); bị từ chối post-only → đặt lại 1 lần theo giá tốt mới; sau **60 s** (cấu hình 30–300) phần chưa khớp bị huỷ và trợ lý hỏi: "market phần còn lại / đặt lại maker / dừng" |

- Khi lệnh maker đang chờ mà `liq_dist_worst` rơi dưới ngưỡng khẩn → thông báo KHẨN kèm đề xuất market phần còn lại (một lần duyệt), **không tự chuyển**.
- Lệnh limit đóng "chiếm" vị thế (N4): reduce maker luôn < 100% vị thế nên `pos_loss` vẫn còn phần không bị chiếm; giảm 100% chỉ bằng market/`close-positions`. Trong lúc lệnh maker chờ, watcher vẫn ưu tiên SL như thường.
- Khớp một phần: phần đã khớp là kết quả thật (ghi realized), cập nhật Q/A/TP/WCL ngay; phần còn lại theo quy tắc timeout.

### 6A.4 Lớp DCA chưa khớp

- Lựa chọn rõ: `keep` (giữ nguyên), `cancel` (huỷ), `shrink` (thu size mỗi lớp còn lại theo cùng tỉ lệ giảm, floor theo lot; lớp < `minTradeNum` thì huỷ).
- **Mặc định đề xuất**: nếu `liq_dist_worst(keep)` < mục tiêu (với `--target-liq-distance`: chính X; với `--pct/--qty`: ngưỡng cảnh báo của hồ sơ 6A.6) → đề xuất **cancel các lớp sâu nhất trước** cho đến khi đạt; nếu `keep` đã đạt → `keep`. `shrink` luôn hiện như một phương án trong bảng.
- Thứ tự áp dụng (§6.4): **huỷ/thu lớp chờ TRƯỚC**, xác nhận, **rồi** mới gửi lệnh giảm (tránh lớp khớp đúng lúc đang giảm). Lớp định huỷ đã khớp → tính lại, báo, hỏi lại.

### 6A.5 Sau khi giảm: SL, TP, ngân sách, bộ đếm

- **SL**: `pos_loss` là lệnh cấp vị thế, kỳ vọng tự áp cho phần còn lại (không cần sửa size) **[CXM → D26]**. Watcher PHẢI xác nhận sau mỗi reduce: đúng 1 `pos_loss`, trigger không đổi (±1 tick), và lệnh vẫn tồn tại khi size giảm. Nếu D26 cho thấy SL bị huỷ/gắn size cố định → đặt lại theo §6.4 (đặt mới trước, không huỷ trước), và đây trở thành bước bắt buộc của `reduce apply`. Giá SL **không đổi** do reduce (WCL giảm nên I2 vẫn giữ); muốn dời thì `ladder edit` riêng.
- **TP**: `profit_plan` có size cố định → sau khi phần giảm khớp, đặt lại `qTP1 = floor(f1·Q')`, `qTP2 = Q' − qTP1` (Q' = vị thế còn lại; nếu `qTP1 < minTradeNum` → 1 TP duy nhất). Giá TP giữ nguyên (giá TB không đổi khi đóng một phần).
- **WCL mới** = lỗ tại SL của phần còn lại + lớp chờ còn giữ + `max(0, −realized_leg)` (§6.3) – lỗ chốt ra **tiêu ngân sách thang**, lãi chốt ra **không** làm đệm.
- **Bộ đếm lỗ**:
  - Khoá ngày/tuần/DD đo bằng **E theo mark** (§8.4), nên lỗ đã nằm trong uPnL từ trước; reduce chỉ làm E đổi thêm đúng **phí đóng + trượt giá**. Preview in: "bộ đếm ngày: −X → −(X + phí) / ngưỡng −Y". Nếu điều này chạm ngưỡng → khoá kích hoạt nhưng reduce vẫn chạy.
  - Ngân sách thang (WCL) và ngân sách xô (Scalp): `realized_risk` §3.1 **tính cả đóng một phần** (sửa định nghĩa: "Σ PnL ròng của mọi lệnh đóng, toàn phần hoặc một phần, của thang Scalp").
  - Chuỗi stop (R20): reduce **không** tính là một lần SL.
  - Journal: mỗi reduce một dòng (`close_reason=reduce`, lý do người dùng nhập tuỳ chọn, liq trước/sau).
- Giảm 100% → leg `CLOSED(reduce)`, huỷ mọi lệnh còn lại của leg sau khi xác nhận size = 0.

### 6A.6 Cảnh báo thanh lý chủ động (watcher)

| Bậc | Ngưỡng cảnh báo `liq_alert_pct` (xấu nhất toàn TK, từ mark) | Ngưỡng khẩn |
|---|---|---|
| Thận trọng | 30% | 5% |
| Cân bằng | 20% | 5% |
| Mạo hiểm có kiểm soát | 10% | 5% |

- Tính mỗi vòng đối soát (60 s) và theo mark WS (tối đa 1 lần/5 s). Dưới ngưỡng → thông báo CAO + **dựng sẵn** phiên bản reduce cho leg đóng góp nhiều MM nhất, mục tiêu = ngưỡng + 2 điểm %, lựa chọn lớp mặc định 6A.4 → "Duyệt 7Q2X.v5?" một chạm. **Không bao giờ tự thực thi** (ngoại lệ duy nhất vẫn là `on_sl_failure` của SPEC Q4 và `fail_execute` §9.4).
- Chống lặp: báo lại chỉ khi xấu thêm ≥ 2 điểm % hoặc sau khi đã hồi > ngưỡng + 2 điểm rồi rơi lại; dưới ngưỡng khẩn → KHẨN mỗi 5 phút.
- Quan hệ với quy tắc Scalp "liq ≥ 3% khi thêm lớp" (SPEC 4.12.3c): kiểm tra thêm lớp/mở plan dùng `max(3%, liq_alert_pct của bậc)` → công cụ không tự đặt một lớp mà ngay khi khớp đã kích hoạt cảnh báo. Hằng cứng 3% giữ nguyên làm sàn.

### 6A.7 Ví dụ số (E = 524.7, ETH mmr 0.5%, không có vị thế khác; script `/workspace/scratch/spec_v2/reduce.py`)

Thang Scalp 4 lớp theo SPEC 4.12.4 đã sửa (first 3×, mult 0.87, d 0.2%, SL 15% E): lớp 2400.00 / 2395.20 / 2390.40 / 2385.62, size 0.65 / 0.57 / 0.49 / 0.43, **SL 2359.09**. (Cấu hình này vượt trần Scalp của mọi bậc §2.2 – dùng làm ví dụ vì liq gần.)

**(A) Giá về lớp 4, mark 2385.62, khớp đủ 4 lớp**: Q 2.14 ETH, TB 2393.63, notional 5105.23 (10.08× E theo mark, E_mark 506.53). Liq ước tính **2159.72 = cách mark 9.47%** (một leg = toàn TK vì không có lớp chờ/vị thế khác). WCL 77.98.

| Giảm (market) | Khối lượng | Realized (gồm phí) | Liq mới (cách mark) | WCL mới | Notional còn | Bộ đếm ngày đổi thêm |
|---|---|---|---|---|---|---|
| 20% | 0.42 | −4.17 | 2101.99 (11.89%) | 66.84 | 4103.27 (8.10×) | −0.60 (phí) |
| **30%** | 0.64 | **−6.35** | **2058.84 (13.70%)** | **61.01** | 3578.43 (7.06×) | −0.92 |
| **50%** | 1.07 | **−10.62** | **1923.28 (19.38%)** | **49.61** | 2552.61 (5.04×) | −1.53 |

- 30% bằng maker (post-only ở ask): realized −5.74, phí 0.31 thay vì 0.92 – nhưng có thể không khớp.
- `--target-liq-distance 10` → giảm tối thiểu 0.11 ETH (5.1%) → 10.01%; `--target-liq-distance 12` → 0.44 ETH (20.6%) → 12.03%.
- Ở bậc Mạo hiểm (cảnh báo 10%) watcher đã báo từ lúc 9.47% và dựng sẵn đề xuất mục tiêu 12% (0.44 ETH).

**(B) Giá về lớp 3, mark 2390.40, khớp L1–L3 (Q 1.71, TB 2395.65), L4 0.43 còn chờ**: liq một leg 2099.79 (12.16%) nhưng **xấu nhất có tính L4 khớp: 2159.72 (9.65%)** – đúng chỗ "giảm ảo".

| Giảm 30% (0.51 ETH, realized −3.65) | Liq xấu nhất (cách mark) | WCL |
|---|---|---|
| keep L4 | 2084.24 (12.81%) | 62.02 |
| shrink L4 → 0.30 | 2057.04 (13.95%) | 58.32 |
| cancel L4 | **1971.78 (17.51%)** | **49.80** |

Giảm 50% (0.85, realized −6.09): keep 16.30% / WCL 51.38; cancel 24.61% / WCL 39.16. Với `--target-liq-distance 10`: keep cần giảm 0.08 ETH; cancel L4 thì không cần giảm (12.16%) → đề xuất mặc định là **cancel L4, giảm 0**.

**Wide (ngắn gọn)**: Cân bằng, ETH long đủ 5 lớp (0.15 @ TB 2329.07, mark 2259.20) + BTC long đủ 5 lớp (mark 76857.4) + 2 short mỗi bên 1 lớp: liq xấu nhất cách mark **~71.7%**. Giảm 0.07 ETH (~50%, floor lot) realized −5.02 → ~92.8%, WCL ETH-L 23.44 → 17.52. Preview Wide PHẢI ghi: "Thanh lý đang rất xa; giảm chủ yếu làm giảm lỗ nếu chạm SL, và sẽ chốt lỗ {x} USDT ngay."

### 6A.8 Preview (định dạng)

```
REDUCE 7Q2X.v4  ETH long (Scalp)   mark 2385.62   exec: market (liq 9.47% ≥ khẩn 5% → mặc định maker; anh chọn market)
                    Hiện tại            Sau giảm 30%
Size                2.14 ETH            1.50 ETH
Notional            5105.23 (10.08×E)   3578.43 (7.06×E)
Liq 1 leg           2159.72 (9.47%)     2058.84 (13.70%)
Liq xấu nhất TK     2159.72 (9.47%)     2058.84 (13.70%)   [lớp chờ: không có]
Realized phần đóng  –                   −6.35 USDT (gồm phí mở chia tỉ lệ + phí đóng taker)
WCL thang           77.98               61.01 (đã gồm −6.35)
SL (pos_loss)       2359.09             2359.09 (tự áp phần còn lại – watcher xác nhận)
TP1/TP2 size        1.07 / 1.07         0.75 / 0.75
Bộ đếm ngày         −18.17              −19.09 / khoá ở −41.98 (8%)
Phương án:  20% → 11.89% | 30% → 13.70% | 50% → 19.38% | mục tiêu 12% → 0.44 ETH
hash 5d20b7   Duyệt 7Q2X.v4?
```
(Bộ đếm ngày trong ví dụ giả định E đầu ngày = 524.7: E_mark 506.53 → −18.17; sau phí −19.09.)

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

Ví dụ Cân bằng: ETH long 23.4 / 24.4 / 0.27 / 1.83; BTC short 25.1 / 26.3 / 0.37 / 2.08. Dòng thành thật cố định cuối digest: "Kỳ vọng backtest phương án Cân bằng ~0.67 USDT/ngày (cận trên; thực tế thường kém hơn)."
Đề xuất trong digest hết hạn sau 10 phút; trả lời muộn → trợ lý `plan refresh` → nếu rủi ro/size không đổi in "làm mới, rủi ro không đổi" nhưng **vẫn hỏi duyệt phiên bản mới**.

### 8.3 Thông báo sự kiện (watcher → kênh Q6)

| Sự kiện | Mức | Mẫu |
|---|---|---|
| Fill lớp k | INFO | "ETH long: khớp lớp 2 @2364.00. Đang giữ 0.06 ETH, giá TB 2382.00. SL 2174.58 (lỗ nếu chạm ~… USDT). TP1 2410.59." |
| TP1 | INFO | "Chốt TP1 +{x} USDT. Đã huỷ lớp còn lại, SL về hoà vốn {BE}." |
| TP2 / BE | INFO | "Đóng thang: {lý do}, ròng {pnl} USDT. Hôm nay: {pnl_day}." |
| SL | CAO | "Cắt lỗ ETH long: −{x} USDT (dự kiến −{y}). Hôm nay −{d}% / khoá ở −{lim}%." |
| WORKING hết hạn (24 h, lớp 1 chưa khớp) | INFO | "Đã huỷ thang chờ ETH long (24 h không khớp). Đề xuất mới trong digest." |
| Khoá ngày/tuần/DD/chuỗi stop/xô | CAO | "Đã khoá mở lệnh mới đến {thời điểm UTC+7}. Thang đang chạy giữ nguyên SL/TP." |
| Cảnh báo thanh lý (§6A.6) | CAO / KHẨN (< 5%) | "Thanh lý (xấu nhất toàn TK) cách {d}% < ngưỡng {th}%. Đề xuất giảm {qty} {coin} ({pct}%) → {d2}%, chốt {realized} USDT. Duyệt {ref}?" |
| Reduce xong | INFO | "Đã giảm {qty} @ {price} ({maker/market}), realized {x} USDT. Liq {d}% → {d2}%. SL {sl} vẫn trên sàn." |
| Hồ sơ pending hiệu lực | INFO | "Hồ sơ v4 (Mạo hiểm) bắt đầu hiệu lực." |
| Lỗi đặt lệnh/đối soát/DRIFT | CAO | mô tả + việc công cụ đã làm |
| Leg không có SL, WS chết, `fail_execute` | KHẨN | + hành động tự động đã chạy |

### 8.4 Khoá (định nghĩa chính xác – giải Q-12)

| Khoá | Công thức | Hậu quả | Mở khoá |
|---|---|---|---|
| Ngày | `E_now − E_day_start ≤ −daily% × E_day_start` (mark, gồm uPnL, phí, funding; chuyển tiền vào/ra phát hiện qua bill → điều chỉnh mốc) | chặn execute/apply làm tăng WCL (Wide + Scalp); huỷ entry Scalp chưa khớp; thang Wide giữ nguyên | 07:00 UTC+7 hôm sau, tự động; không mở sớm |
| Tuần | như trên theo `E_week_start` | như trên | thứ Hai 07:00 |
| DD | `E_now < (1 − dd%) × max(E 30 ngày)` | như trên + gợi ý hạ hồ sơ | tự động sau **7 ngày**: đặt lại đỉnh = E_now và **ép bậc Thận trọng 7 ngày** (tránh kẹt 30 ngày) |
| Chuỗi stop | SL thứ 2 trong 24 h cuộn | chặn mở mới 12 h | tự động |
| Xô | §3.2 | chỉ Scalp | §3.2 |
| Giờ cấm (P6) | `now ∈ no_trade` | chặn execute/propose | hết khung giờ |

Ghi rõ trong UX: khoá **chỉ chặn mở mới**, không giới hạn lỗ của thang đang chạy (SL mới làm việc đó). Sửa thang chạy mà không tăng WCL vẫn được khi đang khoá; `reduce` (§6A) **luôn** được khi đang khoá. Lỗ chốt ra bởi `reduce` đã nằm trong E theo mark nên với khoá ngày/tuần/DD chỉ thêm phí + trượt; với ngân sách thang/xô thì tính đủ (§6A.5); không tính là SL cho chuỗi stop.

---

## 9. Sửa các lỗi nghiêm trọng (và quan trọng liên quan) từ review

### 9.1 N1 – `aggressive` không bao giờ PASS R13 [→ SPEC 4.2, A.2, Q3, Phụ lục C]
**Quy tắc:** xoá biến thể `aggressive` và cờ `--variant`. Bậc "Mạo hiểm có kiểm soát" dùng tham số DEFAULT (capLeg 1.25, s 7%) trên `E_wide` = 80% E, ≤ 3 thang: SL ngoài lớp 5 **2.65% long / 2.40% short** → R13 PASS. Test U20 bắt buộc: *mọi bậc công bố PASS R13 với contracts bảng 4.1, cả 2 symbol, 2 chiều*. Phụ lục C: ghi chú "AGGR là kết quả tham khảo, không phải cấu hình có trong công cụ".

### 9.2 N2 – R14 chặn thang thứ 4 [→ SPEC R14, A.1 `HARD_TOTAL_SL_BUDGET`, 4.11]
**Định nghĩa R14 mới:** `Σ_legs WCL_leg / E_now ≤ sl_budget_pct (bậc)`, với `WCL_leg` theo §6.3 (size thật, giá khớp thật cho phần đã khớp, SL hiện tại; leg ở `TP1_DONE` với SL ≥ BE: `max(0, lỗ tại BE)` ≈ 0; Scalp gồm trượt 0.3%). Số thang tối đa do **hồ sơ** quy định (Cân bằng 4, Mạo hiểm 3) sao cho R14 không phải là thứ "bất ngờ" chặn: Cân bằng 18.62% ≤ 21%; Mạo hiểm 20.82% ≤ 25%. Hằng cứng giữ 25% / 30%.

### 9.3 N3 – `kill` xoá SL [→ SPEC 2.2 dòng `kill`, 9.5, 2.4 bước 4]
- `kill` (mặc định) = **chế độ bảo vệ**: tạo `state/KILL`, huỷ mọi **entry** và **TP** của công cụ (lọc tiền tố), **giữ** `pos_loss`/BE, watcher **tiếp tục chạy** ở chế độ `PROTECT_ONLY` (chỉ đảm bảo SL, đối soát, cảnh báo; không đặt entry/TP). Xác nhận đầu ra: "mỗi leg còn vị thế có đúng 1 SL".
- `kill --close-positions --confirm-close` = `close-positions` theo từng (symbol, holdSide) của công cụ → đợi size = 0 (xác nhận REST) → mới huỷ SL/TP còn lại. Thất bại đóng → giữ SL, KHẨN.
- `resume --confirm` = xoá `state/KILL` + `selftest` → watcher về chế độ thường (đặt lại TP theo phiên bản đang chạy; **không** đặt lại entry đã huỷ – muốn thì `ladder edit`).

### 9.4 N4 – TP limit chiếm 100% vị thế [→ SPEC 4.5, 7.3, 7.4(d), 7.6(1)]
**Mặc định mới `tp_mode: plan_market`**: TP1/TP2 là `place-tpsl-order planType=profit_plan`, `size = qTP`, `triggerType=fill_price`, **`executePrice = "0"` (market)** → không chiếm vị thế lúc chờ, cũng không để lại limit treo nếu giá quay đầu sau trigger. Chi phí: phí đóng taker thay maker – TP1 đầy thang ETH Cân bằng 1.83 thay vì 1.89 USDT; lớp 1: 0.27 thay vì 0.28. Mọi số "lãi" trong tài liệu này đã tính theo taker.
- Không còn lệnh close limit nào treo trong thiết kế mặc định (trừ `scalp scaleout` – xem dưới). Fallback chỉ dùng nếu D18 FAIL: `limit_partial` với `Σ size TP ≤ Q − 1 lot`.
- Watcher PHẢI xử lý `orders-algo status=fail_execute`: với `pos_loss`/BE → `close-positions` (holdSide) ngay + KHẨN; với TP → đặt lại 1 lần, vẫn lỗi → CAO.
- Scalp TP_a/TP_b: dùng cùng `plan_market` (phí taker 0.06% làm lãi TP_a mỏng: TP 0.15% − 0.02% − 0.06% = 0.07% notional; đã tính trong §3.4). `scalp scaleout` (limit post-only) phải giữ `Σ close limit ≤ Q − 1 lot`.
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
| Q-3 | Digest/README ghi kỳ vọng là **cận trên** (backtest mở lại ngay, MVP chờ duyệt) | 1.3 |
| Q-4 | R16 = `notional plan mới / leverage ≤ 50% crossedMaxAvailable` (Scalp 80%). Mạo hiểm/xô cần 20× (vd Scalp 1484 USDT / 20 = 74 USDT ký quỹ) | R16 |
| Q-5 | TP1_DONE theo **sự kiện lệnh** (`profit_plan` T1 executed theo clientOid), debounce fill 1–2 s; fill trễ sau TP1: tính lại A từ `openPriceAvg`, TP2 cho toàn bộ phần còn, BE theo A mới | 8.2 bước 5 |
| Q-6 | `working_ttl_h` = 24 (tham số plan); hết hạn → CANCELLED + thông báo | 8.2 |
| Q-7 | Trước khi đặt SL/BE/TP kiểm mark: đã vượt trigger → đóng ngay phần tương ứng bằng `close-positions`/market | 4.5, 8.2 |
| Q-8 | Preset SL chỉ ở lớp 1; sau fill đầu `modify-tpsl-order` sang `mark_price` và xác nhận | 7.4(a) |
| Q-9 | Trước mỗi lần gửi lại: `order/detail?clientOid=`; filled/cancelled → không gửi lại | 7.5, 8.5(3) |
| Q-10 | Phát hiện vị thế lớn hơn tổng fill công cụ → CAO, dừng re-price TP, **chặn mọi `ladder edit` làm tăng WCL** của leg đó, hỏi anh | 8.2 |
| Q-11 | Một hằng `HARD_LEVERAGE_MAX_PER_SYMBOL = 50`; bậc quy định leverage cài (10×/20×); công cụ chỉ `set-leverage` khi symbol không có vị thế/lệnh; còn lại `selftest` hướng dẫn hạ tay | R17, A.1 |
| Q-12 | §8.4 | R18–R20 |
| Q-13 | Cổng: P1 = U1–U2, U4–U16, U19a, U20–U25, U28–U36, U38–U44 (+ D26–D28); P1b = U3', U19b, U26–U27, D15, D24; Demo Wide ≥ 20 thang, Scalp ≥ 10 trước khi bật xô | 10, 11 |
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
| `bucket status` / `bucket refill --confirm` | Sổ xô §3 | Không |
| `propose [--symbol S --side L/S] [--mode wide|scalp] [--max 2]` | Sinh plan v1 (§4). `preview` cũ = `propose --symbol --side` | Không |
| `plan show/edit/import/diff/refresh/list` | §5 | Không |
| `execute <ref> --confirm --hash H [--reason "..."]` | Thay `execute <plan_id> --confirm`; `--reason` chỉ cho đèn đỏ trước cổng | Có |
| `ladder edit <root> ...` / `ladder apply <ref> --confirm --hash H` / `ladder close <root> --pct N --confirm` | §6 | Có (apply/close) |
| `reduce <root> --pct N \| --qty Q \| --target-liq-distance X [--layers keep\|cancel\|shrink] [--exec auto\|maker\|market]` / `reduce apply <ref> --confirm --hash H` | §6A – chỉ đóng, dùng được khi khoá/kill | Có (apply) |
| `liq [--json]` | Liq một leg + xấu nhất toàn TK cho mọi leg, ngưỡng cảnh báo bậc | Không |
| `cancel <root>` | Huỷ entry chưa khớp + TP; giữ SL nếu còn vị thế | Có |
| `kill` / `kill --close-positions --confirm-close` / `resume --confirm` | §9.3 | Có |
| `digest [--send]` | §8.2 | Không |
| `lock status` | khoá đang có, thời điểm mở (UTC+7) | Không |
| `ta --simple` | 4 dòng đèn §7.2 | Không |
| Bỏ | `--variant`, `--legs`, `--override-avoid` (thay bằng `--reason`), `scalp preview/execute` (gộp vào `propose --mode scalp` / `execute`) | – |

### 10.1 Kiểm tra mới (bổ sung bảng 5.2)

| # | Kiểm tra | PASS | FAIL |
|---|---|---|---|
| R26 | Giờ cấm | `now ∉ no_trade` | Chặn execute/propose |
| R27 | Trần hồ sơ | mọi trường ≤ trần bậc (§2.5); `profile_version == active` | Chặn |
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
reduce: {urgent_liq_pct: 5, maker_timeout_s: 60, plan_ttl_s: 120, drift_pct: 0.3,
         alert_liq_pct: {than_trong: 30, can_bang: 20, mao_hiem: 10}, alert_hysteresis_pts: 2}
```

### 10.3 Hằng cứng mới (Phụ lục A.1)

`HARD_MAX_WIDE_LADDERS = 4`, `HARD_WEEKLY_STOP_MAX = 15%`, `HARD_DD_BREAKER_MAX = 25%`, `HARD_RISK_BUCKET_MAX = 20%`, `HARD_LEVERAGE_MAX_PER_SYMBOL = 50` (thay 2 hằng leverage cũ), `HARD_PROFILE_RAISE_COOLDOWN_MIN = 24h`, `HARD_PLAN_EQUITY_DRIFT = 1%`, `HARD_MARKET_SHIFT_TOL = 0.3%`, `HARD_TP_MODE_DEFAULT = plan_market`, `HARD_REDUCE_URGENT_MIN = 3%` (ngưỡng khẩn không được cấu hình thấp hơn), `HARD_REDUCE_CLOSE_ONLY = true` (mã `reduce` không có đường gọi `tradeSide=open`).

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
| U25 | Vượt trần: budget > capLeg×E_wide, max-loss > s×E_wide, layers 6, spacing 0.9% → lỗi R27, thông điệp hướng tới `profile set` |
| U26 | Sizing Scalp §3.4: size 0.19/0.17/0.14/0.12, SL 2361.77, lỗ 20.99 / 25.39; bản 2.5%: 0.09/0.08/0.07/0.06 |
| U27 | Sổ xô: E_risk/E_wide theo fill giả lập; R28; khoá khi hết ngân sách; không refill trước mốc; lãi không tăng ngân sách; overshoot trừ kỳ sau |
| U28 | WCL running edit §6.3: (a) dồn lớp → SL tự dời 2180.67; (b) huỷ lớp 5 → SL xa tối đa 2129.66, yêu cầu 2150.00 OK, 2120.00 FAIL; (c) vượt trần notional FAIL; property test 10.000 bộ: sau mọi sửa được chấp nhận `WCL ≤ L_run` |
| U29 | Thứ tự áp dụng §6.4 (sàn giả lập): SL_TIGHTEN trước PLACE_ENTRY; SL_LOOSEN sau cùng; lệnh định huỷ đã khớp → tự siết SL + `applied_partial`; modify SL lỗi → không bước rủi ro nào chạy; **không bao giờ có thời điểm leg có vị thế mà 0 pos_loss** (kiểm trên mọi trạng thái trung gian) |
| U30 | Không tự dời SL xa: mọi đường code dời SL xa đều xuất phát từ phiên bản đã duyệt có `--sl` rõ ràng |
| U31 | `kill` → mỗi leg còn vị thế đúng 1 pos_loss, watcher `PROTECT_ONLY`; `kill --close-positions` huỷ SL chỉ sau size = 0 |
| U32 | `plan_market`: không có close limit treo; `fail_execute` của pos_loss → close-positions + KHẨN |
| U33 | E đóng băng & `market_shift`: SL không đổi với E 500/524.7/550; dịch 0.2% → execute với size giữ nguyên; dịch 0.4% hoặc E lệch 1.2% → từ chối; BTC size đổi do E → từ chối |
| U34 | Đèn: map OK/CAUTION/AVOID/thiếu dữ liệu; đề xuất chỉ xanh; đỏ trước cổng cần `--reason` ≥ 10 ký tự; sau cổng FAIL không override; nhãn "không phải dự báo" có trong mọi đầu ra |
| U35 | `propose` xác định; xếp hạng §4.4; thu nhỏ theo bước 10% giữ nguyên SL; bỏ ứng viên dưới 50% trần |
| U36 | Digest/thông báo: số liệu lấy từ `derived` (không lệch), có câu thành thật, giờ UTC+7 |
| U37 | R14' tính với size thật/giá khớp thật/TP1_DONE ≈ 0/Scalp + trượt; Cân bằng 4 thang 18.62%; Mạo hiểm 3 Wide + Scalp 20.82% |
| U38 | Mô hình liq 6A.2: (A) 2159.72 / 9.47%; giảm 20/30/50% → 11.89 / 13.70 / 19.38%, realized −4.17 / −6.35 / −10.62, WCL 66.84 / 61.01 / 49.61 (±0.01); (B) xấu nhất có L4 = 9.65% vs một leg 12.16%; giảm 30% keep / shrink / cancel = 12.81 / 13.95 / 17.51%, WCL 62.02 / 58.32 / 49.80; Wide ~71.7% → ~92.8% |
| U39 | `--target-liq-distance`: (A) 10% → 0.11 ETH, 12% → 0.44 ETH; (B) keep 10% → 0.08, cancel → 0; đơn điệu theo k; không đạt → thông báo + gợi ý cancel; mmr = max(API bậc, floor) |
| U40 | Close-only: bảng hedge mode (đóng long = buy+close, đóng short = sell+close), không `reduceOnly`, không đường nào tạo `tradeSide=open`; size floor lot, phần còn lại ≥ minTradeNum hoặc 0; 100% → `close-positions` có holdSide |
| U41 | Chọn thực thi: liq < 5% → market; ≥ 5% → maker ở ask/bid, đặt lại 1 lần khi bị từ chối, timeout 60 s → hỏi; rơi dưới khẩn khi đang chờ → KHẨN + đề xuất, không tự chuyển; khớp một phần cập nhật Q/TP/WCL |
| U42 | Thứ tự: huỷ/thu lớp chờ trước, xác nhận, rồi mới close; lớp định huỷ đã khớp → dừng và hỏi; sau reduce: TP size = floor(f1·Q') / Q' − qTP1; SL giá không đổi; đúng 1 pos_loss |
| U43 | Bộ đếm: khoá ngày/tuần chỉ thêm phí + trượt (vd −18.17 → −19.09); WCL & ngân sách xô tính realized một phần; không tính vào chuỗi stop; reduce chạy được khi khoá ngày/tuần/DD/xô và `PROTECT_ONLY`, bị chặn khi `RECONCILING`/`DRIFT` |
| U44 | Cảnh báo thanh lý: ngưỡng theo bậc, hysteresis 2 điểm, KHẨN mỗi 5 phút dưới 5%, đề xuất dựng sẵn đúng mục tiêu ngưỡng + 2; **không bao giờ tự thực thi**; kiểm tra thêm lớp Scalp dùng `max(3%, ngưỡng bậc)` |

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
| D26 | **Reduce một phần trong hedge mode** khi có cả long và short cùng symbol: market `buy+close` 30% long | Chỉ long giảm đúng size, short nguyên; `pos_loss` long **vẫn tồn tại, trigger không đổi, áp cho size còn lại** (đọc `orders-plan-pending` + cho mark chạm SL trên Demo → đóng đúng phần còn lại) |
| D27 | Reduce maker post-only ở ask: khớp một phần, timeout 60 s, huỷ phần còn lại | Phần khớp ghi đúng; lệnh limit close không làm SL đóng thiếu (kết hợp D9) |
| D28 | Reduce khi đang khoá ngày và khi `kill` PROTECT_ONLY; reduce 100% | Được phép; 100% dùng `close-positions` holdSide, rồi mới huỷ SL/TP |

### 11.3 Backtest (tiếp B1–B5)

- **B6** (cổng bật bậc Mạo hiểm): DEFAULT trên 80% vốn, tối đa 3 thang, cap cùng chiều 2.0×, cùng engine; báo cáo 2 nửa kỳ. Và Thận trọng (0.45×/3%, 2 thang) để có số kỳ vọng hiển thị.
- **B7**: ảnh hưởng `plan_market` (taker TP) và BE theo spec so với `final_eval.csv`.
- **B8** (thay B4, là cổng): Scalp theo §3.4 với ngân sách xô, khoá xô, phí taker; chủ ký duyệt trước khi bật xô live.

---

## 12. Câu hỏi cho chủ

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
| C12 | Khoá ngày: giữ nguyên thang Wide chưa khớp lớp nào (không tự huỷ) | Giữ nguyên |
| C13 | DD breaker: tự mở sau 7 ngày + ép Thận trọng 7 ngày | Có |
| C14 | Thang chờ (chưa khớp lớp 1) tự huỷ sau 24 h | 24 h |
| C15 | Leverage: công cụ chỉ tự đặt khi symbol không có vị thế; tài khoản đang 125–150× thì anh hạ tay trước go-live | Có |
| C16 | Bậc Thận trọng ưu tiên BTC vì ETH lot 0.01 quá thô ở mức vốn này | Có |
| C17 | Giờ và kênh gửi digest | 07:05 UTC+7, kênh chat trợ lý (+ email cho mức CAO/KHẨN, theo Q6) |
| C18 | Ngưỡng khẩn của `reduce` (dưới mức này mặc định market) | **5%** khoảng cách liq xấu nhất toàn TK, mọi bậc (sàn cứng 3%) |
| C19 | Kiểu thực thi mặc định khi không khẩn | **Maker post-only** ở giá tốt nhất, chờ 60 s rồi hỏi (market / đặt lại / dừng) |
| C20 | Lớp DCA chưa khớp khi reduce | **Huỷ lớp sâu nhất trước** nếu giữ lớp làm liq xấu nhất < mục tiêu; ngược lại giữ; `shrink` là phương án hiển thị |
| C21 | Ngưỡng cảnh báo thanh lý theo bậc | 30% / 20% / 10% (Thận trọng / Cân bằng / Mạo hiểm); chỉ cảnh báo + dựng sẵn đề xuất, không tự chạy |
| C22 | Kiểm tra thêm lớp Scalp dùng `max(3%, ngưỡng cảnh báo bậc)` thay vì chỉ 3% | Có |
| C23 | Lỗ chốt bởi `reduce` tiêu ngân sách thang/xô (lãi không bù), nhưng không tính là SL trong chuỗi stop | Có |

(Q1, Q3 của SPEC 12 được thay bằng C1/C2; Q7 thay bằng bảng 2.2/§8.4; Q13 thay bằng C5/C6; các Q khác giữ nguyên.)
