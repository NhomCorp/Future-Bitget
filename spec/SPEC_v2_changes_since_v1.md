# SPEC v2 – Thay đổi kể từ bản bổ sung đầu tiên

| | |
|---|---|
| Tác giả | trhieu6179 |
| Ngày | 2026-10-20 (UTC+7) |
| Bản gốc (base) | `SPEC_v2_additions_draft.md` bản 685 dòng (09:42 UTC+7) |
| Bản mới | `SPEC_v2_additions_draft.md` bản hiện tại, 830 dòng |
| Nội dung | Chỉ các thay đổi. Phần lớn là mục mới **§6A – Giảm vị thế chủ động để đẩy giá thanh lý (`reduce`)** và các chỗ nối vào mục khác |

> Cách lập: không còn bản sao nguyên văn của bản gốc, nên bản gốc được dựng lại bằng cách đảo ngược chính xác các phép thay thế đã ghi trong lịch sử sửa. Sau đó chạy `diff -u` thật (bản dựng lại = 684 dòng; 104 dòng +/−; không có nội dung nào bị xoá ngoài các dòng được thay chữ nêu dưới đây).

---

## §0 Tóm tắt thay đổi

- **Sửa** dòng C9: `test U20–U37, D18–D25` → `test U20–U44, D18–D28`.
- **Thêm** dòng C10:

| # | Thay đổi | Thay thế/sửa |
|---|---|---|
| C10 | **`reduce`**: giảm vị thế chủ động (chỉ đóng) để đẩy giá thanh lý xa, cả Wide và Scalp; preview liq một leg + xấu nhất toàn TK (có lớp chờ); maker/market theo ngưỡng khẩn; dùng được cả khi đang khoá; watcher cảnh báo thanh lý theo bậc và dựng sẵn đề xuất (không tự chạy) | mới (§6A); bổ sung 4.8, 4.12.3c |

## §1.2 Sơ đồ luồng (mermaid)

**Thêm** vào cuối sequence diagram (sau dòng `W-->>C: TP1 / BE / TP2 / SL / lỗi / khoá ngày`):

```
    W-->>C: Cảnh báo thanh lý: cách 9.47% < 10% (bậc) + đề xuất reduce 7Q2X.v5 dựng sẵn
    A->>C: "Giảm 30%, huỷ lớp chờ"
    C->>T: reduce 7Q2X --pct 30 --layers cancel
    T-->>C: preview hiện tại/sau (size, liq 1 leg & xấu nhất, realized, WCL, SL, bộ đếm ngày)
    A->>C: "Duyệt"
    C->>T: reduce apply 7Q2X.v5 --confirm --hash …
    T->>X: huỷ lớp chờ → xác nhận → close (market/maker) → đặt lại TP size; xác nhận pos_loss còn nguyên
```

## §3.1 Sổ phụ xô mạo hiểm

- **Trước:** `realized_risk(t)` = Σ PnL ròng (gồm phí, funding) của các thang Scalp **đóng** từ đầu kỳ.
- **Sau:** `realized_risk(t)` = Σ PnL ròng (gồm phí, funding) của **mọi lệnh đóng** (toàn phần hoặc một phần, kể cả `reduce` §6A) của thang Scalp từ đầu kỳ.

## §6.1 Sửa khi thang đang chạy – phạm vi

**Thêm** sau câu về `ladder close`: "Giảm vị thế vì thanh lý (có tính liq, lựa chọn lớp chờ, maker/market) dùng `reduce` – §6A."

## §6A (MỚI) – toàn văn

### 6A. Giảm vị thế chủ động để đẩy giá thanh lý (`reduce`) [mới; áp cho cả Wide và Scalp]

> Ý của chủ: "Nhiều khi đóng 1 phần vị thế không phải vì có lãi, mà vì muốn giảm volume vị thế để giá thanh lý xa hơn." `reduce` là thao tác **chỉ đóng** (close-only), làm được bất kể lãi/lỗ, không bao giờ mở thêm vị thế.

#### 6A.1 Lệnh

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

#### 6A.2 Mô hình thanh lý dùng trong preview [mở rộng SPEC 4.8]

- Điều kiện thanh lý cross: `W + Σ uPnL(P) ≤ Σ mmr_j·|Q_j|·P_j`, `W` = số dư ví sau mọi phí đã trả, mark price, `mmr = max(bậc MMR từ API theo notional, mmr_floor cấu hình)` (ETH 0.5%, BTC 0.4% ở ví dụ).
- **Một leg**: công thức đóng SPEC 4.8(a) với W thật hiện tại (bỏ qua leg khác) – chỉ để tham khảo.
- **Xấu nhất toàn tài khoản (con số quyết định)**: mọi giá cùng chiều leg đang xét di chuyển bất lợi cùng x% từ mark hiện tại (BTC/ETH tương quan ≈ 1); **mỗi lớp entry chờ cùng chiều được coi là khớp tại giá của nó khi giá đi qua** (đúng đường đi, có phí maker); leg ngược chiều: tính MM, **không** tính lãi (m9); SL **không** được giả định là chạy (trường hợp SL lỗi/gap – lý do tồn tại của reduce). Tìm x nhỏ nhất bằng bisection → `liq_dist_worst` và giá liq tương ứng của symbol.
- "Giảm mà vẫn giữ lớp chờ" có thể là ảo: lớp chờ khớp lại kéo liq về chỗ cũ. Vì vậy preview **luôn** in cả hai: `liq_dist_worst` khi giữ lớp và khi huỷ/thu lớp.

#### 6A.3 Cách thực thi

| Điều kiện (`liq_dist_worst` trước khi giảm) | Mặc định `--exec auto` |
|---|---|
| < **ngưỡng khẩn** (mặc định 5% mọi bậc; ≥ `HARD_SCALP_MIN_LIQ_DIST` 3%) | **market** (taker 0.06%, khớp ngay) |
| ≥ ngưỡng khẩn | **maker**: limit post-only ở giá tốt nhất phía đóng (đóng long: `askPr`; đóng short: `bidPr`); bị từ chối post-only → đặt lại 1 lần theo giá tốt mới; sau **60 s** (cấu hình 30–300) phần chưa khớp bị huỷ và trợ lý hỏi: "market phần còn lại / đặt lại maker / dừng" |

- Khi lệnh maker đang chờ mà `liq_dist_worst` rơi dưới ngưỡng khẩn → thông báo KHẨN kèm đề xuất market phần còn lại (một lần duyệt), **không tự chuyển**.
- Lệnh limit đóng "chiếm" vị thế (N4): reduce maker luôn < 100% vị thế nên `pos_loss` vẫn còn phần không bị chiếm; giảm 100% chỉ bằng market/`close-positions`. Trong lúc lệnh maker chờ, watcher vẫn ưu tiên SL như thường.
- Khớp một phần: phần đã khớp là kết quả thật (ghi realized), cập nhật Q/A/TP/WCL ngay; phần còn lại theo quy tắc timeout.

#### 6A.4 Lớp DCA chưa khớp

- Lựa chọn rõ: `keep` (giữ nguyên), `cancel` (huỷ), `shrink` (thu size mỗi lớp còn lại theo cùng tỉ lệ giảm, floor theo lot; lớp < `minTradeNum` thì huỷ).
- **Mặc định đề xuất**: nếu `liq_dist_worst(keep)` < mục tiêu (với `--target-liq-distance`: chính X; với `--pct/--qty`: ngưỡng cảnh báo của hồ sơ 6A.6) → đề xuất **cancel các lớp sâu nhất trước** cho đến khi đạt; nếu `keep` đã đạt → `keep`. `shrink` luôn hiện như một phương án trong bảng.
- Thứ tự áp dụng (§6.4): **huỷ/thu lớp chờ TRƯỚC**, xác nhận, **rồi** mới gửi lệnh giảm (tránh lớp khớp đúng lúc đang giảm). Lớp định huỷ đã khớp → tính lại, báo, hỏi lại.

#### 6A.5 Sau khi giảm: SL, TP, ngân sách, bộ đếm

- **SL**: `pos_loss` là lệnh cấp vị thế, kỳ vọng tự áp cho phần còn lại (không cần sửa size) **[CXM → D26]**. Watcher PHẢI xác nhận sau mỗi reduce: đúng 1 `pos_loss`, trigger không đổi (±1 tick), và lệnh vẫn tồn tại khi size giảm. Nếu D26 cho thấy SL bị huỷ/gắn size cố định → đặt lại theo §6.4 (đặt mới trước, không huỷ trước), và đây trở thành bước bắt buộc của `reduce apply`. Giá SL **không đổi** do reduce (WCL giảm nên I2 vẫn giữ); muốn dời thì `ladder edit` riêng.
- **TP**: `profit_plan` có size cố định → sau khi phần giảm khớp, đặt lại `qTP1 = floor(f1·Q')`, `qTP2 = Q' − qTP1` (Q' = vị thế còn lại; nếu `qTP1 < minTradeNum` → 1 TP duy nhất). Giá TP giữ nguyên (giá TB không đổi khi đóng một phần).
- **WCL mới** = lỗ tại SL của phần còn lại + lớp chờ còn giữ + `max(0, −realized_leg)` (§6.3) – lỗ chốt ra **tiêu ngân sách thang**, lãi chốt ra **không** làm đệm.
- **Bộ đếm lỗ**:
  - Khoá ngày/tuần/DD đo bằng **E theo mark** (§8.4), nên lỗ đã nằm trong uPnL từ trước; reduce chỉ làm E đổi thêm đúng **phí đóng + trượt giá**. Preview in: "bộ đếm ngày: −X → −(X + phí) / ngưỡng −Y". Nếu điều này chạm ngưỡng → khoá kích hoạt nhưng reduce vẫn chạy.
  - Ngân sách thang (WCL) và ngân sách xô (Scalp): `realized_risk` §3.1 **tính cả đóng một phần** (sửa định nghĩa: "Σ PnL ròng của mọi lệnh đóng, toàn phần hoặc một phần, của thang Scalp").
  - Chuỗi stop (R20): reduce **không** tính là một lần SL.
  - Journal: mỗi reduce một dòng (`close_reason=reduce`, lý do người dùng nhập tuỳ chọn, liq trước/sau).
- Giảm 100% → leg `CLOSED(reduce)`, huỷ mọi lệnh còn lại của leg sau khi xác nhận size = 0.

#### 6A.6 Cảnh báo thanh lý chủ động (watcher)

| Bậc | Ngưỡng cảnh báo `liq_alert_pct` (xấu nhất toàn TK, từ mark) | Ngưỡng khẩn |
|---|---|---|
| Thận trọng | 30% | 5% |
| Cân bằng | 20% | 5% |
| Mạo hiểm có kiểm soát | 10% | 5% |

- Tính mỗi vòng đối soát (60 s) và theo mark WS (tối đa 1 lần/5 s). Dưới ngưỡng → thông báo CAO + **dựng sẵn** phiên bản reduce cho leg đóng góp nhiều MM nhất, mục tiêu = ngưỡng + 2 điểm %, lựa chọn lớp mặc định 6A.4 → "Duyệt 7Q2X.v5?" một chạm. **Không bao giờ tự thực thi** (ngoại lệ duy nhất vẫn là `on_sl_failure` của SPEC Q4 và `fail_execute` §9.4).
- Chống lặp: báo lại chỉ khi xấu thêm ≥ 2 điểm % hoặc sau khi đã hồi > ngưỡng + 2 điểm rồi rơi lại; dưới ngưỡng khẩn → KHẨN mỗi 5 phút.
- Quan hệ với quy tắc Scalp "liq ≥ 3% khi thêm lớp" (SPEC 4.12.3c): kiểm tra thêm lớp/mở plan dùng `max(3%, liq_alert_pct của bậc)` → công cụ không tự đặt một lớp mà ngay khi khớp đã kích hoạt cảnh báo. Hằng cứng 3% giữ nguyên làm sàn.

#### 6A.7 Ví dụ số (E = 524.7, ETH mmr 0.5%, không có vị thế khác; script `/workspace/scratch/spec_v2/reduce.py`)

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

#### 6A.8 Preview (định dạng)

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

## §8.3 Thông báo sự kiện

**Thêm** 2 dòng (trước dòng "Hồ sơ pending hiệu lực"):

| Sự kiện | Mức | Mẫu |
|---|---|---|
| Cảnh báo thanh lý (§6A.6) | CAO / KHẨN (< 5%) | "Thanh lý (xấu nhất toàn TK) cách {d}% < ngưỡng {th}%. Đề xuất giảm {qty} {coin} ({pct}%) → {d2}%, chốt {realized} USDT. Duyệt {ref}?" |
| Reduce xong | INFO | "Đã giảm {qty} @ {price} ({maker/market}), realized {x} USDT. Liq {d}% → {d2}%. SL {sl} vẫn trên sàn." |

## §8.4 Khoá

- **Trước:** "… Sửa thang chạy mà không tăng WCL vẫn được khi đang khoá."
- **Sau:** "… Sửa thang chạy mà không tăng WCL vẫn được khi đang khoá; `reduce` (§6A) **luôn** được khi đang khoá. Lỗ chốt ra bởi `reduce` đã nằm trong E theo mark nên với khoá ngày/tuần/DD chỉ thêm phí + trượt; với ngân sách thang/xô thì tính đủ (§6A.5); không tính là SL cho chuỗi stop."

## §9.7 Bảng phát hiện quan trọng (dòng Q-13)

- **Trước:** "Cổng: P1 = U1–U2, U4–U16, U19a, U20–U25, U28–U36; …"
- **Sau:** "Cổng: P1 = U1–U2, U4–U16, U19a, U20–U25, U28–U36, **U38–U44 (+ D26–D28)**; …" (phần P1b không đổi).

## §10 CLI, cấu hình, hằng cứng

**Lệnh mới** (thêm vào bảng §10, trước `cancel`):

| Lệnh | Mô tả | Gửi lệnh lên sàn? |
|---|---|---|
| `reduce <root> --pct N \| --qty Q \| --target-liq-distance X [--layers keep\|cancel\|shrink] [--exec auto\|maker\|market]` / `reduce apply <ref> --confirm --hash H` | §6A – chỉ đóng, dùng được khi khoá/kill | Có (apply) |
| `liq [--json]` | Liq một leg + xấu nhất toàn TK cho mọi leg, ngưỡng cảnh báo bậc | Không |

**Cấu hình mới** (§10.2, sau khối `bucket`):

```yaml
reduce: {urgent_liq_pct: 5, maker_timeout_s: 60, plan_ttl_s: 120, drift_pct: 0.3,
         alert_liq_pct: {than_trong: 30, can_bang: 20, mao_hiem: 10}, alert_hysteresis_pts: 2}
```

**Hằng cứng mới** (§10.3, nối sau `HARD_TP_MODE_DEFAULT = plan_market`):
- `HARD_REDUCE_URGENT_MIN = 3%`: ngưỡng khẩn không được cấu hình thấp hơn mức này.
- `HARD_REDUCE_CLOSE_ONLY = true`: mã `reduce` không có đường gọi `tradeSide=open`.

## §11 Test mới

**Unit** (nối sau U37):

| ID | Nội dung |
|---|---|
| U38 | Mô hình liq 6A.2: (A) 2159.72 / 9.47%; giảm 20/30/50% → 11.89 / 13.70 / 19.38%, realized −4.17 / −6.35 / −10.62, WCL 66.84 / 61.01 / 49.61 (±0.01); (B) xấu nhất có L4 = 9.65% vs một leg 12.16%; giảm 30% keep / shrink / cancel = 12.81 / 13.95 / 17.51%, WCL 62.02 / 58.32 / 49.80; Wide ~71.7% → ~92.8% |
| U39 | `--target-liq-distance`: (A) 10% → 0.11 ETH, 12% → 0.44 ETH; (B) keep 10% → 0.08, cancel → 0; đơn điệu theo k; không đạt → thông báo + gợi ý cancel; mmr = max(API bậc, floor) |
| U40 | Close-only: bảng hedge mode (đóng long = buy+close, đóng short = sell+close), không `reduceOnly`, không đường nào tạo `tradeSide=open`; size floor lot, phần còn lại ≥ minTradeNum hoặc 0; 100% → `close-positions` có holdSide |
| U41 | Chọn thực thi: liq < 5% → market; ≥ 5% → maker ở ask/bid, đặt lại 1 lần khi bị từ chối, timeout 60 s → hỏi; rơi dưới khẩn khi đang chờ → KHẨN + đề xuất, không tự chuyển; khớp một phần cập nhật Q/TP/WCL |
| U42 | Thứ tự: huỷ/thu lớp chờ trước, xác nhận, rồi mới close; lớp định huỷ đã khớp → dừng và hỏi; sau reduce: TP size = floor(f1·Q') / Q' − qTP1; SL giá không đổi; đúng 1 pos_loss |
| U43 | Bộ đếm: khoá ngày/tuần chỉ thêm phí + trượt (vd −18.17 → −19.09); WCL & ngân sách xô tính realized một phần; không tính vào chuỗi stop; reduce chạy được khi khoá ngày/tuần/DD/xô và `PROTECT_ONLY`, bị chặn khi `RECONCILING`/`DRIFT` |
| U44 | Cảnh báo thanh lý: ngưỡng theo bậc, hysteresis 2 điểm, KHẨN mỗi 5 phút dưới 5%, đề xuất dựng sẵn đúng mục tiêu ngưỡng + 2; **không bao giờ tự thực thi**; kiểm tra thêm lớp Scalp dùng `max(3%, ngưỡng bậc)` |

**Demo** (nối sau D25):

| ID | Kịch bản | Kỳ vọng |
|---|---|---|
| D26 | **Reduce một phần trong hedge mode** khi có cả long và short cùng symbol: market `buy+close` 30% long | Chỉ long giảm đúng size, short nguyên; `pos_loss` long **vẫn tồn tại, trigger không đổi, áp cho size còn lại** (đọc `orders-plan-pending` + cho mark chạm SL trên Demo → đóng đúng phần còn lại) |
| D27 | Reduce maker post-only ở ask: khớp một phần, timeout 60 s, huỷ phần còn lại | Phần khớp ghi đúng; lệnh limit close không làm SL đóng thiếu (kết hợp D9) |
| D28 | Reduce khi đang khoá ngày và khi `kill` PROTECT_ONLY; reduce 100% | Được phép; 100% dùng `close-positions` holdSide, rồi mới huỷ SL/TP |

## §12 Câu hỏi cho chủ (mới, nối sau C17)

| # | Câu hỏi | Mặc định đề xuất |
|---|---|---|
| C18 | Ngưỡng khẩn của `reduce` (dưới mức này mặc định market) | **5%** khoảng cách liq xấu nhất toàn TK, mọi bậc (sàn cứng 3%) |
| C19 | Kiểu thực thi mặc định khi không khẩn | **Maker post-only** ở giá tốt nhất, chờ 60 s rồi hỏi (market / đặt lại / dừng) |
| C20 | Lớp DCA chưa khớp khi reduce | **Huỷ lớp sâu nhất trước** nếu giữ lớp làm liq xấu nhất < mục tiêu; ngược lại giữ; `shrink` là phương án hiển thị |
| C21 | Ngưỡng cảnh báo thanh lý theo bậc | 30% / 20% / 10% (Thận trọng / Cân bằng / Mạo hiểm); chỉ cảnh báo + dựng sẵn đề xuất, không tự chạy |
| C22 | Kiểm tra thêm lớp Scalp dùng `max(3%, ngưỡng cảnh báo bậc)` thay vì chỉ 3% | Có |
| C23 | Lỗ chốt bởi `reduce` tiêu ngân sách thang/xô (lãi không bù), nhưng không tính là SL trong chuỗi stop | Có |

## Không đổi

§2, §4, §5, §7, §9.1–§9.6 và mọi phần còn lại của §1, §3, §6, §8–§12 giữ nguyên so với bản gốc.
