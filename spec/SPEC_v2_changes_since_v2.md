# Thay đổi của SPEC_v2_additions_draft.md kể từ bản v2 (830 dòng)

- Tác giả: trhieu6179
- Ngày: 2026-10-20 (giờ UTC+7)
- **Bản gốc**: `spec/SPEC_v2_additions_draft.md` 830 dòng, commit `a376c52` (bản sao: `/workspace/scratch/spec_v2/draft_v2_830.md`, đã so `cmp` với `git show a376c52:…`, trùng khớp).
- **Bản mới**: `spec/SPEC_v2_additions_draft.md`, 1003 dòng.
- Cách lập: tài liệu này dựng từ `diff -u` thật giữa hai tệp trên, không dựng lại bằng tay. `SPEC.md` và `REVIEW_2026-10-20.md` không đổi (đã kiểm sha256).
- Lý do: góp ý của người review thứ hai (chủ đồng ý), gồm 6 quyết định: nhánh chỉ huỷ entry, schema + băm, bảo vệ SL khi reduce, U37 trong cổng P1, các lỗi cũ, và vòng đời reduce dạng market-only ở P1.

## 1. Đối chiếu góp ý review ↔ cách xử lý

| # | Góp ý | Xử lý | Ở đâu |
|---|---|---|---|
| R1 | Ví dụ "huỷ L4, giảm 0" phải là nhánh chỉ huỷ entry, không gửi lệnh close size = 0 | Thêm `kind: entry_adjust` (lệnh `entries`) không bao giờ gửi lệnh đóng; `reduce` với close_qty = 0 bị từ chối/chuyển sang entry_adjust; ví dụ (B) có dòng "chỉ huỷ L4 → liq xấu nhất 12.16%, WCL 65.76, 0 lệnh đóng"; luôn bật, dùng được khi khoá/cờ reduce tắt | §6A.0, 6A.1, 6A.4, 6A.7(B); §5.6 schema; U45, D31 |
| R2 | `kind: reduce`, qty, exec mode, lựa chọn entry phải nằm trong schema và hash | Schema đầy đủ cho reduce/entry_adjust: leg, close_qty (chuỗi đã làm tròn lot), qty_source (input + resolved), exec_mode, sl_mode, entry_actions từng lớp (keep/cancel; shrink chỉ qua `ladder edit`), preconditions snapshot (size, lớp chờ, mark, SL, E đóng băng), tolerances, expected_after, steps, client_oids, expires_at. Định nghĩa `canonical_json` (khoá sắp xếp, chuỗi Decimal, epoch ms, cấm float) và `hash_content` = mọi trường trừ status/lời chat/thời điểm đo; execute/apply băm lại bản ghi và so 64 hex | §5.4, §5.6, 6A.9; U46 |
| R3 | SL biến mất sau reduce thì "đặt lại sau đó" không đạt cam kết không hở | Bỏ "đặt lại sau". `REDUCE_SL_MODE` là hằng trong mã, mặc định `disabled` (không cấu hình nào bật được). D26 đạt → `position_persist`. D26 trượt → giữ tắt, hoặc làm `preplace_guard`: đặt trước SL `loss_plan` đúng size còn lại, xác nhận rồi mới đóng, rồi chuẩn hoá về đúng 1 SL; muốn bật phải qua D29 (kể cả kích hoạt kép không mở vị thế ngược). Không xác nhận được guard thì huỷ trước khi đóng | §6A.0, 6A.5, 6A.8; §10.3; U47–U49, D26, D29; C24 |
| R4 | U37 chưa có trong cổng P1 | Q-13 viết lại: P1 gồm U28–U38 (có U37), rà lại toàn bộ U/D theo pha: P1 / bật reduce / P1b / P2 / hiển thị kỳ vọng | §9.7 Q-13 |
| R5 | Lỗi cũ: ràng buộc Wide/Scalp, phục hồi applied_partial, khoá ngày, kỳ vọng backtest | §3.5 mới (ma trận ràng buộc), §6.5 mới (nhật ký bước + phục hồi), §8.4 viết lại (khoá ngày duy nhất 07:00), §2.6 mới (số kỳ vọng trung thực + B9) | §2.6, §3.5, §6.5, §8.4; U50–U53, D30, B9; C25–C28 |
| R6 | Chốt vòng đời reduce, market trước rồi mới maker và target | Máy trạng thái P1 market-only: PROPOSED → APPROVED → RECONCILING → CANCELLING_ENTRIES → CLOSING → UPDATING_PROTECTION → DONE, kèm FAILED_SAFE / RECOVERING; mỗi bước có điều kiện, lời gọi, cách xác minh, timeout, xử lý lỗi và phục hồi. Maker chuyển sang P1b (`maker_enabled=false`), `--target-liq-distance` sang P2 (`target_enabled=false`) | §6A.8, 6A.3, 6A.0; §10 CLI/config; U47, U50, D30; C18–C21 |

### 1.1 Em hiểu "lỗi cũ" là gì (cách diễn giải ghi rõ)

1. **Ràng buộc Wide/Scalp**: review N6 và Q-11, các điểm còn mở ở SPEC 4.12.5 (Scalp dùng chung leg/leverage/cap với Wide) và chỗ mơ hồ trong bản v2 của em: §3.1 nói "Scalp không dùng phần R14 của Wide" mà không định nghĩa phần đó. → §3.5.
2. **Phục hồi `applied_partial`**: review Q-5/Q-9 (crash giữa chuỗi lệnh) và §6.4 của em (chỉ có trạng thái `applied_partial`, chưa có quy tắc phục hồi). → §6.5: nhật ký bước, idempotent theo clientOid, đối soát khi khởi động lại, chỉ đi tiếp bước giảm rủi ro hoặc lùi về trạng thái an toàn, không bao giờ tự chạy tiếp bước mở/tăng rủi ro khi chưa có duyệt mới.
3. **Khoá ngày**: review Q-12. SPEC 4.12.5 lấy mốc 00:00, bản v2 lấy 07:00; Scalp và Wide định nghĩa khác nhau. → §8.4: một định nghĩa duy nhất (07:00 UTC+7 ở mọi nơi, thay 00:00 của SPEC 4.12.5), nói rõ cái gì được tính, và reduce/close/cancel/entry_adjust luôn được phép.
4. **Kỳ vọng backtest**: review Q-1, Q-3, N1/N2, Phụ lục C. Con số +38%/+41.6% của DEFAULT không áp được cho cấu hình mới. → §2.6: bảng số liệu nào dùng được, cấu hình chưa kiểm gắn nhãn "chưa kiểm định", cổng B9 trước khi hiển thị số.

## 2. Câu hỏi cho chủ: thay đổi và mới (mặc định)

| # | Thay đổi | Mặc định |
|---|---|---|
| C18 | Đổi: chỉ áp ở P1b | ngưỡng khẩn 5% |
| C19 | Đổi: P1 chỉ market; từ P1b mặc định maker khi ≥ ngưỡng khẩn | market (P1) |
| C20 | Đổi: chỉ keep/cancel; riêng huỷ đã đủ → entry_adjust; shrink chỉ qua `ladder edit` | huỷ lớp sâu nhất trước |
| C21 | Đổi: bản dựng sẵn = entry_adjust hoặc reduce 30% | 30/20/10% |
| C24 | Mới: D26 trượt thì làm preplace_guard (qua D29)? | Có, sau go-live P1 |
| C25 | Mới: gửi lại lệnh close đã duyệt sau crash? | Chỉ trong 120 s và lệch ≤ 0.3% |
| C26 | Mới: bỏ khoá ngày riêng của Scalp | Có |
| C27 | Mới: chỉ hiện số kỳ vọng đã qua B9 | Có (Cân bằng tạm hiện số SAFE, nhãn "cận trên") |
| C28 | Mới: số thang Scalp tối đa cùng lúc | 1 |

## 3. Phần mới (toàn văn)

### 2.6 Kỳ vọng backtest – số nào còn dùng được [→ SPEC 1.3, Phụ lục C; review Q-3]

| Cấu hình trong công cụ | Số liệu đang có | Còn áp dụng? |
|---|---|---|
| Cân bằng (tham số = SAFE: 0.75×/5%, 4 thang, 100% E) | `final_eval.csv` SAFE: +22.9%/180 ngày, DD 19.0%, 23 stop, ~0.67 USDT/ngày; nửa giảm −1.4% | **Chỉ là cận trên**: backtest đóng TP bằng maker (công cụ: taker `plan_market`), BE khác, mở lại thang ngay và L1 khớp ngay (công cụ: chờ duyệt, post-only). Hiển thị kèm nhãn "SAFE backtest – cận trên, chưa kiểm định với cách chạy của công cụ (B9)" |
| Cân bằng + xô 10% | không có | **chưa kiểm định** |
| Thận trọng (0.45×/3%, 2 thang) | không có | **chưa kiểm định** (không được suy tuyến tính từ SAFE vì làm tròn lot và số thang khác) |
| Mạo hiểm (DEFAULT trên 80% E, ≤ 3 thang) | DEFAULT +38.0% / AGGR +41.6% là **4 thang trên 100% E**, AGGR không có cap cùng chiều | **Không áp dụng**. Cấm hiển thị +38% / +41.6% cho bất kỳ bậc nào |
| Scalp trong xô (§3.4) | `REPORT.txt` bản thuần hoá (tham số khác) −62%/60 ngày | **chưa kiểm định**; chỉ hiển thị cảnh báo SPEC 4.12 |

Quy tắc: README, `status`, digest chỉ in số kỳ vọng lấy từ file kết quả backtest có `config_hash` trùng `params_hash` của hồ sơ đang dùng **và** B-test tương ứng đạt (B9; Mạo hiểm cần thêm B6, xô cần B8). Không có → in "chưa kiểm định bằng backtest". Ngoại lệ tạm thời duy nhất: dòng SAFE của Cân bằng với nhãn cận trên ở trên, cho tới khi có B9.

---

### 3.5 Ràng buộc Wide/Scalp cùng tồn tại [giải các điểm mở của SPEC 4.12.5, R8–R10, R14]

1. **Một thang mỗi (symbol, holdSide), bất kể chế độ** (giữ SPEC 4.11/4.12.5). Thang đang tồn tại thắng: `propose` bỏ qua cặp đó; `propose --mode wide` trên cặp đang có Scalp (hoặc ngược lại) → R6 FAIL "đang có thang Scalp ETH long; đóng/huỷ trước".
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

   Hệ quả: Scalp lớn không làm FAIL R10w của Wide nhưng có thể làm FAIL R10a → `propose` thu nhỏ Wide (bước 6 §4) hoặc bỏ ứng viên. Ví dụ Mạo hiểm: R14 phần Wide ≤ 25% − 5% = 20% (3 thang Wide 15.98% ✓), toàn TK 20.82% ✓.
5. **Leverage theo symbol dùng chung**: nếu symbol có Scalp (20×), thang Wide trên cùng symbol cũng chạy ở 20× (chỉ ảnh hưởng ký quỹ; R16 tính theo leverage thật).
6. Sửa thang chạy (§6), `reduce`/`entry_adjust` (§6A) chạy lại cùng ma trận (chỉ phần làm tăng rủi ro mới có thể FAIL).

---

### 5.6 (phần thêm) Schema cho reduce / entry_adjust

Chèn sau khối YAML §5.6, trước dòng "DB: bảng `plans`…" (dòng DB thêm cột `reduce_json, observed_state_json`; `status` thêm `aborted`; `kind` thêm `reduce | entry_adjust`).
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
expires_at: 2026-10-20T10:21:40+07:00      # TTL 120 s
reduce:
  leg: {root_id: 7Q2X, symbol: ETHUSDT, hold_side: long, mode: scalp}
  qty_source: {type: pct, input: "30", resolved: "0.64", rounding: floor_lot}   # type: pct | qty (| target ở P2)
  close_qty: "0.64"
  exec_mode: market       # P1 chỉ market; maker từ P1b
  sl_mode: position_persist          # = REDUCE_SL_MODE lúc tạo; preplace_guard thêm khối guard
  entry_actions: []       # mỗi lớp chờ: {idx, client_oid, price, qty, action: keep|cancel, new_qty}
  preconditions:
    position_size: "2.14"
    avg_price: "2393.63"
    pending_entries: []
    sl: {plan_type: pos_loss, client_oid: "gsc1-K7Q2M9XA-EL-SL-0", trigger: "2359.09", trigger_type: mark_price}
    tp: [{role: T1, size: "1.07", trigger: "2397.33"}, {role: T2, size: "1.07", trigger: "2398.53"}]
    mark: "2385.62"
    equity_frozen: "506.53"
    snapshot_at: 2026-10-20T10:19:38+07:00
  tolerances: {mark_drift_pct: "0.3000", equity_drift_pct: "1.0000"}
  expected_after:
    position_size: "1.50"
    protection: {sl_count: 1, plan_type: pos_loss, trigger: "2359.09", covers: position}
    tp_sizes: ["0.75", "0.75"]
    liq_one_leg: "2058.84"
    liq_worst: "2058.84"
    wcl: "61.01"
    realized_est: "-6.35"
    daily_counter_after: "-19.09"
  steps: [RECONCILING, CLOSING, UPDATING_PROTECTION]
  client_oids: {close: "gsc1-K7Q2M9XD-EL-X1-0"}
content_hash: 5d20b7…
```
`kind: entry_adjust` dùng cùng khối (tên `entry_adjust`) nhưng **không có** `close_qty`, `exec_mode`, `qty_source`; `entry_actions` phải có ≥ 1 `cancel`; `steps: [RECONCILING, CANCELLING_ENTRIES]`. Ví dụ 6A.7(B): `entry_actions: [{idx: 4, client_oid: "gsc1-K7Q2M9XA-EL-E4-0", price: "2385.62", qty: "0.43", action: cancel, new_qty: "0"}]`, `expected_after: {position_size: "1.71", liq_worst: "2099.79", wcl: "65.76"}`.

---

### 6.5 Nhật ký bước & phục hồi khi bị ngắt giữa chừng (`applied_partial`)

Áp cho `execute`, `ladder apply`, `reduce apply`, `entries apply`.

- Bảng `op_journal(op_id PK, version_id, leg_id, kind, step_no, step_kind, risk[reduce|increase], client_oid, intent_json, status[planned|sent|confirmed|failed|skipped|rolled_back], exch_ref, created_at, updated_at)`. Mọi bước được ghi `planned` kèm clientOid xác định (`{prefix}-{version_id}-{leg}-{role}{idx}-{rev}`) **trước khi gửi**, chuyển `sent` ngay trước HTTP, `confirmed` sau khi xác minh trên sàn; cập nhật nguyên tử cùng trạng thái leg.
- Phân loại: **giảm rủi ro** = huỷ entry, SL_TIGHTEN, đóng vị thế, đặt bảo vệ, cập nhật TP; **tăng rủi ro** = PLACE_ENTRY (kể cả dời/đổi size), SL_LOOSEN, đặt entry ở `execute`.
- Khởi động lại / mất kết nối khi op chưa kết thúc → leg vào `RECOVERING` (chặn mọi op khác của leg), reconcile REST đầy đủ; mỗi bước `sent` chưa `confirmed` → truy vấn theo clientOid (`order/detail`, `orders-plan-pending`) để biết đã tồn tại chưa (Q-9).
- Quy tắc:
  1. Bước giảm rủi ro: **hoàn tất tiến** nếu còn hợp lệ (huỷ entry, SL_TIGHTEN, cập nhật TP: luôn; đóng vị thế: theo RECOVERING của 6A.8).
  2. Bước tăng rủi ro chưa `confirmed`: **không bao giờ gửi lại**. Nếu thực tế đã tồn tại trên sàn: kiểm I2 với SL thật – WCL ≤ L_run → giữ và ghi nhận; ngược lại huỷ entry đó (nếu chưa khớp) hoặc SL_TIGHTEN về mức ngân sách (nếu đã khớp).
  3. SL_LOOSEN chưa `confirmed` → không gửi lại; SL giữ ở mức chặt hơn đã xác nhận.
  4. `execute` dở: huỷ mọi entry chưa khớp của plan (như SPEC 7.4(b)), giữ SL nếu đã có vị thế, không đặt nốt lớp thiếu.
  5. Kết thúc phục hồi: phiên bản → `applied_partial` (hoặc `aborted` nếu chưa có ghi nào) với `observed_state` (giá/size thật từng lớp, SL thật, TP thật, vị thế) lưu DB; mọi sửa tiếp theo tính diff **từ `observed_state`**; phần chưa làm chỉ được tiếp tục bằng **phiên bản mới được duyệt**.
- Mỗi bước tối đa 2 lần gửi lại (có truy vấn trước); vượt → `FAILED_SAFE` + CAO. Bất biến I1 do watcher giữ song song suốt quá trình (thiếu SL → đặt ngay).


---

---

### §6A: thay toàn bộ (bản cũ 6A.1–6A.8 ở commit a376c52, dòng 438–550)

## 6A. Giảm vị thế chủ động để đẩy giá thanh lý (`reduce`) [mới; áp cho cả Wide và Scalp]

> Ý của chủ: "Nhiều khi đóng 1 phần vị thế không phải vì có lãi, mà vì muốn giảm volume vị thế để giá thanh lý xa hơn." `reduce` là thao tác **chỉ đóng** (close-only), làm được bất kể lãi/lỗ, không bao giờ mở thêm vị thế.

### 6A.0 Phân pha & cờ tính năng (bắt buộc đọc trước)

| Khả năng | Pha | Cờ | Điều kiện bật |
|---|---|---|---|
| `entry_adjust` (chỉ huỷ lớp chờ, **không** gửi lệnh đóng) | P1 | luôn bật | U45, D31 |
| `reduce` **market** (giảm theo `--pct`/`--qty`) | P1 | `REDUCE_SL_MODE` (hằng trong mã) ≠ `disabled` | **D26 đạt** (→ `position_persist`) **hoặc** D29 đạt (→ `preplace_guard`); kết quả ghi `docs/decisions.md`; đổi hằng = đổi mã + review |
| `reduce` **maker** (post-only + timeout) | P1b | `reduce_maker_enabled` (mặc định false) | U41, D27 đạt |
| `--target-liq-distance` (tự tìm khối lượng) | P2 | `reduce_target_enabled` (mặc định false) | U39 đạt + 4 tuần dùng reduce market không sự cố |

- `REDUCE_SL_MODE` **mặc định `disabled` trong mã**: cấu hình không bật được. Khi `disabled`, lệnh `reduce` trả: "Tính năng giảm vị thế đang tắt cho tới khi Demo D26/D29 chứng minh SL vẫn còn sau khi đóng một phần. Hiện chỉ dùng được: `entries`, `ladder close` (đóng hẳn), `kill --close-positions`."
- `reduce` không chặn go-live P1; P1 có thể chạy live với reduce tắt.

### 6A.1 Lệnh (P1)

```
reduce <root> --pct N | --qty Q [--entries keep|cancel] [--cancel-idx I,J]   # market-only ở P1
reduce show <ref> | reduce apply <ref> --confirm --hash H | reduce status <op_id>
entries <root> --cancel IDX[,IDX...] | --cancel-all                           # entry_adjust (chỉ huỷ)
entries apply <ref> --confirm --hash H
```
- `--exec maker` (P1b) và `--target-liq-distance X` (P2) bị từ chối với thông báo pha/cờ khi chưa bật.
- `shrink` (thu size lớp chờ) **không** thuộc reduce ở P1 vì phải đặt lại lệnh mở (vi phạm close-only): dùng `ladder edit --size IDX=QTY` (luồng §6).
- Lệnh đóng: `place-order`, `orderType=market`, `tradeSide=close`, hedge mode SPEC 7.3 (**đóng long = `side=buy`; đóng short = `side=sell`**; không gửi `reduceOnly`), `size = close_qty` floor theo lot, `clientOid` role `X`. 0 < `close_qty` < vị thế: phần còn lại ≥ `minTradeNum`. `close_qty` = vị thế → không phải reduce: dùng `ladder close --pct 100` (`close-positions` có holdSide).
- **Nhánh chỉ-huỷ**: nếu khối lượng giảm giải ra = 0 (vd `--qty 0`, hoặc phương án trong bảng chỉ cần huỷ lớp) → công cụ **không** tạo `kind: reduce`; tạo `kind: entry_adjust` và nói rõ "không gửi lệnh đóng". Không có đường code nào gửi lệnh close với size 0.
- Được phép khi đang khoá (ngày/tuần/DD/chuỗi stop/xô), khi `kill` ở `PROTECT_ONLY`, khi hồ sơ `pending`. Không được khi leg đang `RECONCILING`/`RECOVERING`, có `DRIFT` (Q-10), hoặc đang có một op khác trên leg (khoá op theo leg).

### 6A.2 Mô hình thanh lý dùng trong preview [mở rộng SPEC 4.8]

- Điều kiện thanh lý cross: `W + Σ uPnL(P) ≤ Σ mmr_j·|Q_j|·P_j`, `W` = số dư ví sau mọi phí đã trả, mark price, `mmr = max(bậc MMR từ API theo notional, mmr_floor cấu hình)` (ETH 0.5%, BTC 0.4% ở ví dụ).
- **Một leg**: công thức đóng SPEC 4.8(a) với W thật hiện tại – chỉ tham khảo.
- **Xấu nhất toàn tài khoản (con số quyết định)**: mọi giá cùng chiều leg đang xét di chuyển bất lợi cùng x% từ mark (BTC/ETH tương quan ≈ 1); **lớp entry chờ cùng chiều được coi là khớp tại giá của nó khi giá đi qua** (có phí maker); leg ngược chiều: tính MM, **không** tính lãi (m9); SL **không** được giả định là chạy. Bisection → `liq_dist_worst` và giá liq tương ứng.
- Preview **luôn** in `liq_dist_worst` khi giữ lớp chờ và khi huỷ lớp chờ (tránh "giảm ảo").

### 6A.3 Thực thi

- **P1: chỉ market.** Taker 0.06%; trượt giá ước tính `close_qty × mark × 0.1%` in trong preview (cấu hình).
- P1b (sau khi bật cờ): `--exec auto` = market khi `liq_dist_worst` < ngưỡng khẩn (5%, sàn cứng 3%), ngược lại maker post-only ở giá tốt nhất phía đóng (đóng long: `askPr`; đóng short: `bidPr`), đặt lại 1 lần nếu bị từ chối, timeout 60 s → huỷ phần còn lại và hỏi (market / đặt lại / dừng); rơi dưới khẩn khi đang chờ → KHẨN + đề xuất market, không tự chuyển. Limit close luôn < 100% vị thế (N4).

### 6A.4 Lớp DCA chưa khớp

- P1: `keep` hoặc `cancel` (toàn bộ hoặc theo chỉ số). Mặc định đề xuất: nếu `liq_dist_worst(keep)` < mục tiêu (ngưỡng cảnh báo của bậc, 6A.6) → **cancel lớp sâu nhất trước** đến khi đạt; nếu chỉ huỷ lớp đã đạt → đề xuất **entry_adjust** (không đóng); nếu `keep` đã đạt → `keep`.
- Huỷ lớp luôn chạy **trước** lệnh đóng (state machine 6A.8).

### 6A.5 Bảo vệ SL khi giảm (không có khoảng hở)

Cam kết: **không có đường nào để phần vị thế còn lại không có SL trên sàn**, kể cả trong lúc chuyển tiếp. "Đặt lại SL sau khi đóng" **không** phải là cơ chế hợp lệ.

**Chế độ `position_persist`** (chỉ khi D26 đạt): D26 phải chứng minh trên Demo hedge mode rằng sau một lệnh close một phần, `pos_loss` cấp vị thế (a) vẫn tồn tại, (b) trigger không đổi, (c) khi kích hoạt đóng **đúng toàn bộ phần còn lại**. Khi đó reduce không đụng SL; bước `UPDATING_PROTECTION` chỉ **xác minh**. Nếu runtime vẫn phát hiện SL mất (trái với D26) → đây là sự cố sàn: watcher đặt `pos_loss` ngay (quy tắc I1 chung), KHẨN, và **tự chuyển `REDUCE_SL_MODE` hiệu lực về `disabled`** (cờ runtime ghi DB; chỉ mở lại bằng lệnh có xác nhận sau khi điều tra) – sự cố được ghi là vi phạm giả định, không phải đường thiết kế.

**Chế độ `preplace_guard`** (dùng nếu D26 FAIL; tự nó phải qua D29 trước khi bật):
1. **Đặt bảo vệ trước**: `place-tpsl-order planType=loss_plan`, `size = Q_after` (= vị thế − close_qty), `triggerPrice = SL hiện tại`, `triggerType=mark_price`, `executePrice=0`, `holdSide` của leg, clientOid role `G`.
2. **Xác nhận** qua `orders-plan-pending` (planType=profit_loss): lệnh G tồn tại, đúng size/trigger, trong 10 s. Không xác nhận được → truy vấn theo clientOid; nếu G có thì huỷ G; **dừng trước khi đóng** (`FAILED_SAFE`, không gửi close).
3. **Đóng** (market close `close_qty`).
4. **Chuẩn hoá về đúng 1 SL**: đọc lại: nếu `pos_loss` còn và đúng trigger → huỷ G (pos_loss tự theo size); nếu `pos_loss` mất → đặt `pos_loss` mới (cấp vị thế), xác nhận, **rồi** mới huỷ G. Trong lúc chuyển tiếp có 2 SL cùng trigger: chấp nhận được vì lệnh SL là lệnh **close** (hedge mode, `tradeSide=close` gắn holdSide) nên lệnh kích hoạt thứ hai chỉ đóng phần còn lại hoặc bị từ chối "insufficient position", **không thể mở vị thế ngược** – giả định này **[CXM → D29 phải chứng minh]**; nếu D29 cho thấy có thể mở ngược → `preplace_guard` bị loại, reduce giữ `disabled`.
5. Nếu thêm lớp chờ được giữ (`keep`) mà G có size cố định: G chỉ tồn tại trong bước chuyển tiếp; trạng thái cuối luôn là 1 `pos_loss` cấp vị thế. Nếu không thể đạt trạng thái cuối đó → reduce chỉ được với `--entries cancel` (vị thế không thể tăng sau đó).

TP sau khi đóng: đặt lại `profit_plan` theo `Q_after` (`qTP1 = floor(f1·Q_after)`, `qTP2 = Q_after − qTP1`); TP không phải bảo vệ, lỗi → CAO + thử lại.

### 6A.6 Ngân sách, bộ đếm, cảnh báo

- **WCL mới** = lỗ tại SL của phần còn lại + lớp chờ còn giữ + `max(0, −realized_leg)` (§6.3). Lỗ chốt ra **tiêu ngân sách thang/xô**; lãi không làm đệm. `realized_risk` §3.1 tính cả đóng một phần.
- Khoá ngày/tuần/DD: theo định nghĩa duy nhất §8.4 (E theo mark) → reduce chỉ làm bộ đếm xấu thêm **phí đóng + trượt** (lỗ đã nằm trong uPnL). Preview in "bộ đếm ngày: −X → −(X + phí) / ngưỡng −Y". Chạm ngưỡng → khoá kích hoạt, reduce vẫn chạy xong.
- Chuỗi stop (R20): reduce không tính là SL. Journal: một dòng mỗi reduce/entry_adjust (`close_reason=reduce`, liq trước/sau).
- **Cảnh báo thanh lý** (watcher, mỗi 60 s + theo mark tối đa 1 lần/5 s): ngưỡng theo bậc 30% / 20% / 10% (Thận trọng / Cân bằng / Mạo hiểm), khẩn 5%. Dưới ngưỡng → CAO + bảng phương án cố định (entry_adjust nếu có lớp chờ; reduce 20/30/50%) và **dựng sẵn** một phiên bản: entry_adjust nếu riêng huỷ lớp đạt ngưỡng + 2 điểm, nếu không thì reduce **30%** + cancel lớp sâu theo 6A.4 (P1 không tự giải khối lượng; P2 thay bằng `--target-liq-distance`). **Không bao giờ tự thực thi** (ngoại lệ duy nhất: `on_sl_failure` SPEC Q4, `fail_execute` §9.4). Chống lặp: báo lại khi xấu thêm ≥ 2 điểm hoặc rơi lại sau khi hồi > ngưỡng + 2; dưới khẩn → KHẨN mỗi 5 phút. Khi `REDUCE_SL_MODE = disabled`, bản dựng sẵn chỉ có thể là entry_adjust hoặc `ladder close` toàn phần.
- Quan hệ với quy tắc Scalp "liq ≥ 3% khi thêm lớp" (SPEC 4.12.3c): kiểm tra thêm lớp/mở plan dùng `max(3%, ngưỡng cảnh báo bậc)`.

### 6A.7 Ví dụ số (E = 524.7, ETH mmr 0.5%, không có vị thế khác; script `/workspace/scratch/spec_v2/reduce.py`)

Thang Scalp 4 lớp theo SPEC 4.12.4 đã sửa (first 3×, mult 0.87, d 0.2%, SL 15% E): lớp 2400.00 / 2395.20 / 2390.40 / 2385.62, size 0.65 / 0.57 / 0.49 / 0.43, **SL 2359.09**. (Cấu hình này vượt trần Scalp của mọi bậc §2.2 – dùng làm ví dụ vì liq gần.)

**(A) Giá về lớp 4, mark 2385.62, khớp đủ 4 lớp**: Q 2.14 ETH, TB 2393.63, notional 5105.23 (10.08× E theo mark, E_mark 506.53). Liq ước tính **2159.72 = cách mark 9.47%** (một leg = toàn TK). WCL 77.98. Không còn lớp chờ → chỉ có `reduce`.

| Giảm (market) | Khối lượng | Realized (gồm phí) | Liq mới (cách mark) | WCL mới | Notional còn | Bộ đếm ngày đổi thêm |
|---|---|---|---|---|---|---|
| 20% | 0.42 | −4.17 | 2101.99 (11.89%) | 66.84 | 4103.27 (8.10×) | −0.60 (phí) |
| **30%** | 0.64 | **−6.35** | **2058.84 (13.70%)** | **61.01** | 3578.43 (7.06×) | −0.92 |
| **50%** | 1.07 | **−10.62** | **1923.28 (19.38%)** | **49.61** | 2552.61 (5.04×) | −1.53 |

- (P1b) 30% bằng maker: realized −5.74, phí 0.31 thay vì 0.92 – có thể không khớp.
- (P2) `--target-liq-distance 10` → 0.11 ETH (5.1%) → 10.01%; `12` → 0.44 ETH (20.6%) → 12.03%.
- Bậc Mạo hiểm (cảnh báo 10%): watcher báo ở 9.47% và dựng sẵn reduce 30% (→ 13.70%).

**(B) Giá về lớp 3, mark 2390.40, khớp L1–L3 (Q 1.71, TB 2395.65), L4 0.43 còn chờ**: liq một leg 2099.79 (12.16%) nhưng **xấu nhất có L4 khớp: 2159.72 (9.65%)**.

| Phương án | Loại | Lệnh đóng gửi đi | Liq xấu nhất (cách mark) | WCL |
|---|---|---|---|---|
| **Chỉ huỷ L4** | **`entry_adjust`** | **không có** | **2099.79 (12.16%)** | **65.76** |
| Giảm 30% (0.51, realized −3.65), giữ L4 | reduce | 0.51 market | 2084.24 (12.81%) | 62.02 |
| Giảm 30%, huỷ L4 | reduce | 0.51 market | 1971.78 (17.51%) | 49.80 |
| (Thu L4 → 0.30 + giảm 30%) | `ladder edit` + reduce, 2 phiên bản | 0.51 market | 2057.04 (13.95%) | 58.32 |
| Giảm 50% (0.85, realized −6.09), giữ / huỷ L4 | reduce | 0.85 market | 16.30% / 24.61% | 51.38 / 39.16 |

Với mục tiêu 10% (ngưỡng Mạo hiểm): huỷ L4 đã cho 12.16% ≥ 10% + 2 → watcher dựng sẵn **`entry_adjust` (huỷ L4), không có lệnh đóng**.

**Wide (ngắn gọn)**: Cân bằng, ETH long đủ 5 lớp (0.15 @ TB 2329.07, mark 2259.20) + BTC long đủ 5 lớp (mark 76857.4) + 2 short mỗi bên 1 lớp: liq xấu nhất cách mark **~71.7%**. Giảm 0.07 ETH (~50%) realized −5.02 → ~92.8%, WCL ETH-L 23.44 → 17.52. Preview Wide PHẢI ghi: "Thanh lý đang rất xa; giảm chủ yếu làm giảm lỗ nếu chạm SL, và sẽ chốt lỗ {x} USDT ngay."

### 6A.8 Vòng đời reduce (P1, market-only) – máy trạng thái

```
PROPOSED ─apply(hash ok)─► APPROVED ─► RECONCILING ─► CANCELLING_ENTRIES ─► [GUARDING]* ─► CLOSING ─► UPDATING_PROTECTION ─► DONE
   │expire/superseded           │mismatch          │cancel lỗi/lớp đã khớp   │G không xác nhận   │close bị từ chối
   ▼                            ▼                  ▼                        ▼                   ▼
 EXPIRED                    ABORTED (0 ghi)     FAILED_SAFE              FAILED_SAFE         FAILED_SAFE
                 khởi động lại khi op chưa kết thúc ─► RECOVERING ─► (tiếp tục tiến | FAILED_SAFE)
 * GUARDING chỉ có ở REDUCE_SL_MODE = preplace_guard.   entry_adjust: PROPOSED → APPROVED → RECONCILING → CANCELLING_ENTRIES → DONE
```

| Chuyển | Điều kiện trước | Gọi sàn | Xác minh | Timeout | Khi lỗi |
|---|---|---|---|---|---|
| PROPOSED → APPROVED | `REDUCE_SL_MODE ≠ disabled` (trừ entry_adjust); phiên bản mới nhất; chưa hết hạn (120 s, lệch mark ≤ 0.3%); hash canonical khớp (§5.4); không có op khác trên leg; leg không DRIFT | – | ghi `op_journal` (op_id, version_id, bước dự kiến + clientOid) **trước** | – | từ chối, giữ PROPOSED |
| APPROVED → RECONCILING | khoá trạng thái leg; watcher tạm dừng re-price TP leg (vẫn giữ SL) | REST `single-position`, `orders-pending` (symbol), `orders-plan-pending` (profit_loss), `account`, ticker | khớp `preconditions`: size vị thế = snapshot; tập lệnh chờ = snapshot; đúng 1 `pos_loss` trigger = snapshot; mark trong 0.3%; E trong 1%; `close_qty` vẫn hợp lệ | 10 s | lệch → `ABORTED` (chưa ghi gì lên sàn), thông báo, gợi ý phiên bản mới |
| → CANCELLING_ENTRIES (bỏ qua nếu không huỷ) | RECONCILING đạt | `cancel-order` theo clientOid từng lớp | `order/detail` = `cancelled`; size vị thế không đổi | 10 s/lớp, gửi lại tối đa 2 lần (truy vấn trước khi gửi lại) | lớp đã `filled`/khớp một phần → `FAILED_SAFE` (không đóng; lớp còn lại đã huỷ giữ nguyên huỷ; tính lại, đề xuất phiên bản mới); lỗi khác → `FAILED_SAFE` |
| → GUARDING (`preplace_guard`) | như trên | `place-tpsl-order loss_plan` size `Q_after` (6A.5) | `orders-plan-pending` có G đúng size/trigger | 10 s | huỷ G nếu tồn tại → `FAILED_SAFE` **trước khi đóng** |
| → CLOSING | SL hợp lệ trên sàn (pos_loss, hoặc pos_loss + G) | `place-order` market close `close_qty` (clientOid `X`) | `order/detail` filled; `single-position` size = trước − close_qty (± lot) | 10 s; timeout → truy vấn clientOid, **không** gửi lại nếu đã tồn tại | bị từ chối → `FAILED_SAFE` (đã huỷ lớp = vẫn an toàn); khớp một phần → ghi thực tế, sang UPDATING_PROTECTION với size thật; size giảm nhiều hơn (SL/TP đồng thời) → đối soát rồi UPDATING_PROTECTION |
| → UPDATING_PROTECTION | close đã xác nhận | `position_persist`: chỉ đọc; `preplace_guard`: huỷ G hoặc đặt pos_loss rồi huỷ G (6A.5 bước 4); TP: huỷ/đặt `profit_plan` theo `Q_after` | đúng 1 SL cấp vị thế, trigger = SL phiên bản (±1 tick); TP size đúng | 30 s | thiếu SL → KHẨN + đặt pos_loss ngay + `REDUCE_SL_MODE` runtime → disabled; TP lỗi → CAO, thử lại, không chặn DONE |
| → DONE | mọi xác minh đạt | – | ghi journal, WCL, liq sau thực tế; nhả khoá; thông báo "Reduce xong" | – | – |
| `FAILED_SAFE` | – | không ghi thêm | bất biến I1 (có SL) giữ; phiên bản = `applied_partial` (nếu đã ghi) / `aborted` | – | thông báo trạng thái thật + phương án; **không tự thử đóng lại** |

**RECOVERING** (khởi động lại hoặc mất kết nối giữa op; chạy trong reconcile §6.5): đọc `op_journal`, chụp REST đầy đủ, với từng bước:
- `CANCELLING_ENTRIES` dở → hoàn tất huỷ (giảm rủi ro), rồi **dừng ở FAILED_SAFE** trừ khi bước CLOSING đủ điều kiện dưới đây.
- `CLOSING` đã `sent`: truy vấn clientOid `X`: filled → tiếp tục UPDATING_PROTECTION; không tồn tại → chỉ gửi lại nếu còn trong TTL 120 s từ lúc duyệt **và** mark lệch ≤ 0.3% **và** preconditions (trừ phần đã huỷ) còn đúng; nếu không → `FAILED_SAFE`, hỏi lại.
- `GUARDING` dở → nếu chưa đóng: huỷ G, `FAILED_SAFE`. `UPDATING_PROTECTION` dở → luôn hoàn tất tiến (an toàn).
- Không bao giờ có bước mở vị thế trong reduce, nên không có gì "mở" để tiếp tục.

### 6A.9 Preview & schema (tóm tắt; schema đầy đủ ở §5.6)

```
REDUCE 7Q2X.v4 (kind: reduce)  ETH long (Scalp)  mark 2385.62  exec: market  SL mode: position_persist
                    Hiện tại            Sau giảm 30% (close_qty 0.64 = pct 30 → floor lot)
Size                2.14 ETH            1.50 ETH
Notional            5105.23 (10.08×E)   3578.43 (7.06×E)
Liq 1 leg           2159.72 (9.47%)     2058.84 (13.70%)
Liq xấu nhất TK     2159.72 (9.47%)     2058.84 (13.70%)   [lớp chờ: không có]
Realized phần đóng  –                   −6.35 USDT (gồm phí mở chia tỉ lệ + phí đóng taker)
WCL thang           77.98               61.01 (đã gồm −6.35)
SL (pos_loss)       2359.09             2359.09 (giữ nguyên; xác minh sau khi đóng)
TP1/TP2 size        1.07 / 1.07         0.75 / 0.75
Bộ đếm ngày         −18.17              −19.09 / khoá ở −41.98 (8%)
Phương án:  20% → 11.89% | 30% → 13.70% | 50% → 19.38%
Hết hạn 10:21:40 UTC+7   hash 5d20b7   Duyệt 7Q2X.v4?
```
(Bộ đếm ngày giả định E đầu ngày = 524.7.)

---

### §8.4: thay toàn bộ (bản cũ ở commit a376c52, dòng 617–628)

### 8.4 Khoá – định nghĩa duy nhất (giải Q-12) [→ SPEC R18–R20, 4.12.2 dòng "Lỗ ngày", 4.12.5 "Khoá ngày", A.2 `risk.daily_loss_pct`/`scalp.daily_loss_pct`]

- **Ranh giới**: ngày = [07:00, 07:00) UTC+7, tuần từ thứ Hai 07:00 UTC+7, **ở mọi nơi**; mọi "00:00 UTC+7" trong SPEC (R19, 4.12.2, 4.12.5) được thay bằng 07:00 UTC+7.
- **Mốc**: `E_day_start` = `accountEquity` (mark) của snapshot đầu tiên ≥ 07:00:00 (watcher chụp lúc 07:00:00 ± 5 s). VPS không chạy lúc đó → snapshot đầu tiên sau đó, gắn cờ `day_start_late` trong digest. `E_week_start` tương tự.
- **Tính gì**: `daily_pnl = E_now − E_day_start − net_transfers_today` theo mark ⇒ gồm **lỗ/lãi đã thực hiện + chưa thực hiện**, mọi phí (kể cả phí đóng của `reduce`/`ladder close`), funding; chuyển tiền vào/ra (phát hiện qua bill tài khoản, hoặc E nhảy không kèm fill → CAO, cần anh xác nhận) bị loại. **Một bộ đếm cho toàn tài khoản (Wide + Scalp)**. Khoá ngày riêng của Scalp ở SPEC 4.12.5 (10% E, lỗ Scalp thực hiện + chưa) **bỏ**; Scalp bị giới hạn thêm bởi ngân sách xô §3.
- **Kích hoạt**: `daily_pnl ≤ −daily% × E_day_start` (ngưỡng theo bậc §2.2). Không tự mở khi E hồi trong ngày.

| Khoá | Công thức | Mở khoá |
|---|---|---|
| Ngày | như trên | 07:00 UTC+7 hôm sau, tự động; không mở sớm |
| Tuần | như trên theo `E_week_start` | thứ Hai 07:00 UTC+7 |
| DD | `E_now < (1 − dd%) × max(E 30 ngày)` | tự động sau **7 ngày**: đặt lại đỉnh = E_now và **ép bậc Thận trọng 7 ngày** |
| Chuỗi stop | SL thứ 2 trong 24 h cuộn (reduce/đóng tay không tính) | sau 12 h |
| Xô | §3.2 | §3.2 |
| Giờ cấm (P6) | `now ∈ no_trade` | hết khung giờ |

**Được / bị chặn khi khoá:**

| Hành động | Khoá ngày/tuần/DD/chuỗi stop | Khoá xô | Giờ cấm |
|---|---|---|---|
| `execute` plan mở mới | Chặn (Wide + Scalp) | Chặn Scalp | Chặn |
| `ladder apply` làm tăng WCL | Chặn | Chặn (thang Scalp) | Chặn |
| `ladder apply` không tăng WCL (TP, SL gần hơn, huỷ lớp) | Được | Được | Được |
| `entries` (entry_adjust), `cancel`, `reduce`, `ladder close`, `kill` | **Luôn được** | **Luôn được** | **Luôn được** |
| `bucket refill`, tăng hồ sơ | Chặn | – (refill theo §3.2) | Được |
| `propose`/digest | Không đề xuất; in "đang khoá đến …" | Không đề xuất Scalp | Không đề xuất |

Tự động khi khoá ngày/tuần/DD: huỷ entry Scalp chưa khớp; thang Wide giữ nguyên. Ghi rõ trong UX: khoá **chỉ chặn mở mới**, không giới hạn lỗ của thang đang chạy (SL làm việc đó). Lỗ chốt bởi `reduce` đã nằm trong E theo mark nên khoá ngày/tuần/DD chỉ thêm phí + trượt; ngân sách thang/xô thì tính đủ (§6A.6).

---

## 4. Các sửa còn lại (trước/sau, diff thật, ngữ cảnh 1 dòng)

Gồm §0 (C9, C10, C11 mới), mermaid, §2.2, §3.1, §5.4 (định nghĩa hash), §5.6 status/kind, §6 lệnh ladder, §8.2, §8.3, §9.7 Q-3/Q-13, §10 CLI/config/hằng cứng, §11 (U38–U53, D26–D31, B9), §12.

```diff
@@ -26,4 +26,5 @@
 | C8 | Sửa N1–N6: bỏ `aggressive`; định nghĩa lại R14 & giới hạn số thang; `kill` giữ SL; TP dạng trigger không chiếm vị thế; execute dùng E đóng băng + "bất biến được duyệt"; sửa ví dụ Scalp | xem §9 |
-| C9 | Kiểm tra mới R26–R30; CLI mới; test U20–U44, D18–D28, B6–B8 | 5.2, 2.2, 10 |
-| C10 | **`reduce`**: giảm vị thế chủ động (chỉ đóng) để đẩy giá thanh lý xa, cả Wide và Scalp; preview liq một leg + xấu nhất toàn TK (có lớp chờ); maker/market theo ngưỡng khẩn; dùng được cả khi đang khoá; watcher cảnh báo thanh lý theo bậc và dựng sẵn đề xuất (không tự chạy) | mới (§6A); bổ sung 4.8, 4.12.3c |
+| C9 | Kiểm tra mới R26–R30; CLI mới; test U20–U53, D18–D31, B6–B9 | 5.2, 2.2, 10 |
+| C10 | **`reduce`**: giảm vị thế chủ động (chỉ đóng) để đẩy giá thanh lý xa, cả Wide và Scalp; preview liq một leg + xấu nhất toàn TK (có lớp chờ); **P1 chỉ market**, vòng đời là máy trạng thái có phục hồi; **tắt cứng tới khi D26/D29 chứng minh SL không hở**; nhánh chỉ-huỷ `entry_adjust` không gửi lệnh đóng; dùng được cả khi đang khoá; watcher cảnh báo thanh lý theo bậc và dựng sẵn đề xuất (không tự chạy). Maker → P1b, tự tìm khối lượng → P2 | mới (§6A); bổ sung 4.8, 4.12.3c |
+| C11 | Sửa theo review lần 2: schema + băm canonical (§5.4/§5.6), ràng buộc Wide/Scalp (§3.5), nhật ký bước & phục hồi `applied_partial` (§6.5), khoá ngày định nghĩa duy nhất (§8.4), kỳ vọng backtest trung thực (§2.6), cổng pha (§9.7) | 5.1, R8–R20, 1.3, Phụ lục C, 10 |
 
@@ -75,3 +76,3 @@
     A->>C: "Giảm 30%, huỷ lớp chờ"
-    C->>T: reduce 7Q2X --pct 30 --layers cancel
+    C->>T: reduce 7Q2X --pct 30 --entries cancel
     T-->>C: preview hiện tại/sau (size, liq 1 leg & xấu nhất, realized, WCL, SL, bộ đếm ngày)
@@ -79,3 +80,3 @@
     C->>T: reduce apply 7Q2X.v5 --confirm --hash …
-    T->>X: huỷ lớp chờ → xác nhận → close (market/maker) → đặt lại TP size; xác nhận pos_loss còn nguyên
+    T->>X: RECONCILING → huỷ lớp chờ → xác nhận → close market → xác minh pos_loss + đặt lại TP size (§6A.8)
 ```
@@ -142,3 +143,3 @@
 
-Lý do chọn: Cân bằng = đúng phương án SAFE đã backtest (+22.9%/180 ngày, DD 19%). Thận trọng = SAFE thu nhỏ theo tỉ lệ (cùng `s/capLeg` = 6.67% → cùng vị trí SL). Mạo hiểm = tham số DEFAULT nhưng trên 80% vốn và **tối đa 3 thang** (giải N2) – **chưa backtest đúng cấu hình này → phải qua B6 trước khi bật live** (§11).
+Lý do chọn: Cân bằng dùng đúng tham số SAFE đã backtest (số liệu và giới hạn của nó: §2.6). Thận trọng = SAFE thu nhỏ theo tỉ lệ (cùng `s/capLeg` = 6.67% → cùng vị trí SL) – **chưa backtest**. Mạo hiểm = tham số DEFAULT nhưng trên 80% vốn và **tối đa 3 thang** (giải N2) – **chưa backtest đúng cấu hình này → phải qua B6 + B9 trước khi bật live và trước khi hiển thị bất kỳ con số kỳ vọng nào** (§11).
 
@@ -219,3 +232,3 @@
 - R28 (mới, mở thang Scalp): `used + worst_loss(thang mới) ≤ budget_risk` **và** `worst_loss(thang mới) ≤ per_ladder_scalp` (bảng 2.2).
-- Wide không bao giờ được tính trên `E_risk`; Scalp không bao giờ được dùng `E_wide` hay ngân sách R14 phần Wide.
+- Wide không bao giờ được tính trên `E_risk`; Scalp không bao giờ được dùng `E_wide` hay phần ngân sách R14 dành cho Wide (chia ngân sách R14 và mọi cap dùng chung: §3.5).
 
@@ -311,3 +347,6 @@
 - Phiên bản **bất biến**. Sửa → phiên bản mới `vN+1` với `parent`; mọi phiên bản cũ cùng root chuyển `superseded` (không execute được). Mỗi root chỉ có tối đa 1 phiên bản `executed/running`.
-- `content_hash` = SHA-256 của JSON chuẩn hoá (`params`, `layers`, `derived`, `frozen`, `profile.params_hash`); hiển thị 6 hex đầu. `execute`/`apply` bắt buộc `--hash` khớp.
+- `content_hash` = SHA-256(`canonical_json(hash_content)`); DB lưu đủ 64 hex, hiển thị 6 hex đầu.
+  - `hash_content` = **mọi trường** của phiên bản trừ `status`, `content_hash`, `edit_log[].text` (lời chat thô) và thời điểm đo của checks; tức gồm `schema, root_id, version, version_id, parent, kind, env, created_at, expires_at, profile{version, params_hash}, mode, symbol, side, anchor, frozen, params, layers, derived, checks{id,status,value,limit}, light, override_reason` và, với `kind ∈ {reduce, entry_adjust}`, **toàn bộ** khối `reduce`/`entry_adjust` (§5.6: leg, close_qty, qty_source input + resolved, exec_mode, sl_mode, entry_actions, preconditions, tolerances, expected_after, steps, client_oids).
+  - `canonical_json`: UTF-8; khoá sắp xếp theo thứ tự byte; không khoảng trắng (`,` và `:`); giá/size/USDT là **chuỗi Decimal** định dạng cố định theo `pricePlace`/`volumePlace` của symbol (vd `"2385.62"`, `"0.64"`), USDT 2 chữ số, tỉ lệ % 4 chữ số (`"0.3000"`); thời gian = số nguyên epoch ms UTC; boolean/null theo JSON; mảng giữ thứ tự (lớp theo `idx` tăng dần); **cấm float JSON** (gặp float → lỗi).
+  - `execute`/`apply`: (1) đọc bản ghi DB, băm lại → phải bằng `content_hash` đã lưu (phát hiện sửa DB/file); (2) `--hash` của người dùng phải là tiền tố (≥ 6 hex) của hash đó; (3) mọi tham số gửi sàn (giá, size, `close_qty`, clientOid) **chỉ** lấy từ bản ghi đã băm; ngoại lệ có kiểm soát duy nhất là `market_shift` §9.5 (dung sai nằm trong hash).
 - Sửa bằng file: `plan show <ref> --yaml > plans/7Q2X/edit.yaml`, chỉ sửa `params`/`layers`, chạy `plan import`. Trường `derived/checks/frozen` trong file bị bỏ qua và tính lại. File của phiên bản đã lưu (`plans/7Q2X/v2.yaml`) chỉ để đọc; sửa tay → hash lệch → phiên bản đó bị đánh dấu `invalid`.
@@ -344,4 +383,4 @@
 parent: K7Q2M9XA
-status: proposed   # proposed|superseded|invalid|expired|executed|running|closed|failed|applied_partial
-kind: open         # open | running_edit
+status: proposed   # proposed|superseded|invalid|expired|executed|running|closed|failed|applied_partial|aborted
+kind: open         # open | running_edit | reduce | entry_adjust
 created_at: 2026-10-20T07:12:40+07:00
@@ -386,3 +469,3 @@
 
-Lệnh: `ladder edit <root> [các cờ như plan edit, áp cho lớp chưa khớp] [--sl PRICE|be] [--add-layer PRICE[:SIZE]]... [--size IDX=QTY]...` → tạo phiên bản `kind: running_edit` (vd `7Q2X.v3`) + diff → `ladder apply <ref> --confirm --hash <h>`. `ladder close <root> --pct N --confirm` (đóng market một phần, cũng tạo phiên bản). Giảm vị thế vì thanh lý (có tính liq, lựa chọn lớp chờ, maker/market) dùng `reduce` – §6A. Cùng TTL 10 phút, cùng R1–R30 (phần áp dụng).
+Lệnh: `ladder edit <root> [các cờ như plan edit, áp cho lớp chưa khớp] [--sl PRICE|be] [--add-layer PRICE[:SIZE]]... [--size IDX=QTY]...` → tạo phiên bản `kind: running_edit` (vd `7Q2X.v3`) + diff → `ladder apply <ref> --confirm --hash <h>`. `ladder close <root> --pct N --confirm` (đóng market một phần, cũng tạo phiên bản). Giảm vị thế vì thanh lý (có tính liq, lựa chọn lớp chờ, market ở P1) dùng `reduce`; chỉ huỷ lớp chờ dùng `entries` – §6A. Cùng TTL 10 phút, cùng R1–R30 (phần áp dụng).
 
@@ -597,3 +729,3 @@
 
-Ví dụ Cân bằng: ETH long 23.4 / 24.4 / 0.27 / 1.83; BTC short 25.1 / 26.3 / 0.37 / 2.08. Dòng thành thật cố định cuối digest: "Kỳ vọng backtest phương án Cân bằng ~0.67 USDT/ngày (cận trên; thực tế thường kém hơn)."
+Ví dụ Cân bằng: ETH long 23.4 / 24.4 / 0.27 / 1.83; BTC short 25.1 / 26.3 / 0.37 / 2.08. Dòng thành thật cố định cuối digest lấy từ §2.6: với Cân bằng hiện là "Backtest SAFE (cùng tham số, TP maker, mở lại ngay): ~0.67 USDT/ngày – cận trên, chưa kiểm định với cách chạy của công cụ (B9)"; các bậc khác: "chưa kiểm định bằng backtest".
 Đề xuất trong digest hết hạn sau 10 phút; trả lời muộn → trợ lý `plan refresh` → nếu rủi ro/size không đổi in "làm mới, rủi ro không đổi" nhưng **vẫn hỏi duyệt phiên bản mới**.
@@ -611,3 +743,4 @@
 | Cảnh báo thanh lý (§6A.6) | CAO / KHẨN (< 5%) | "Thanh lý (xấu nhất toàn TK) cách {d}% < ngưỡng {th}%. Đề xuất giảm {qty} {coin} ({pct}%) → {d2}%, chốt {realized} USDT. Duyệt {ref}?" |
-| Reduce xong | INFO | "Đã giảm {qty} @ {price} ({maker/market}), realized {x} USDT. Liq {d}% → {d2}%. SL {sl} vẫn trên sàn." |
+| Reduce / entry_adjust xong | INFO | "Đã giảm {qty} @ {price} (market), realized {x} USDT. Liq {d}% → {d2}%. SL {sl} vẫn trên sàn (đã xác minh)." / "Đã huỷ lớp {idx}, không đóng vị thế. Liq xấu nhất {d}% → {d2}%." |
+| Reduce FAILED_SAFE / RECOVERING | CAO | "Giảm vị thế dừng ở bước {step}: {lý do}. Trạng thái thật: {size}, SL {sl} trên sàn. Chưa đóng thêm. Đề xuất: {ref}." |
 | Hồ sơ pending hiệu lực | INFO | "Hồ sơ v4 (Mạo hiểm) bắt đầu hiệu lực." |
@@ -670,3 +819,3 @@
 | Q-2 | U2 chỉ so giá lớp/TP (±1 tick) và size; oracle SL = công thức 4.6 | U2 |
-| Q-3 | Digest/README ghi kỳ vọng là **cận trên** (backtest mở lại ngay, MVP chờ duyệt) | 1.3 |
+| Q-3 | Digest/README ghi kỳ vọng là **cận trên**; chỉ số liệu đã kiểm định cho đúng cấu hình (§2.6, B9) | 1.3, Phụ lục C |
 | Q-4 | R16 = `notional plan mới / leverage ≤ 50% crossedMaxAvailable` (Scalp 80%). Mạo hiểm/xô cần 20× (vd Scalp 1484 USDT / 20 = 74 USDT ký quỹ) | R16 |
@@ -680,3 +829,3 @@
 | Q-12 | §8.4 | R18–R20 |
-| Q-13 | Cổng: P1 = U1–U2, U4–U16, U19a, U20–U25, U28–U36, U38–U44 (+ D26–D28); P1b = U3', U19b, U26–U27, D15, D24; Demo Wide ≥ 20 thang, Scalp ≥ 10 trước khi bật xô | 10, 11 |
+| Q-13 | Cổng **P1** = U1–U2, U4–U16, U19a, U20–U25, U28–U38, U40, U42–U53 (phần Wide của U44/U51; U49 chỉ khi chọn `preplace_guard`), D1–D14, D16–D23, D25, D30, D31. **Bật `reduce` market** (không chặn go-live P1) = D26 (`position_persist`) **hoặc** D29 + U49 (`preplace_guard`), cộng D28. **P1b** = U3', U19b, U26–U27, U41 (maker), phần Scalp của U44/U51, D15, D24, D27. **P2** = U17–U18, U39 (+ cổng 6.8). **Hiển thị số kỳ vọng** của một bậc = B9 (Mạo hiểm + B6, xô + B8). Demo Wide ≥ 20 thang, Scalp ≥ 10 trước khi bật xô | 10, 11 |
 | Q-14 | Sửa 1.5 ("micro-grid không stop, không trần" ngoài phạm vi; Scalp có trần thì trong phạm vi). **B4 thành cổng**: bật xô mạo hiểm live chỉ sau B8 + chủ ký duyệt | 1.5, 10.5 |
@@ -700,3 +849,5 @@
 | `ladder edit <root> ...` / `ladder apply <ref> --confirm --hash H` / `ladder close <root> --pct N --confirm` | §6 | Có (apply/close) |
-| `reduce <root> --pct N \| --qty Q \| --target-liq-distance X [--layers keep\|cancel\|shrink] [--exec auto\|maker\|market]` / `reduce apply <ref> --confirm --hash H` | §6A – chỉ đóng, dùng được khi khoá/kill | Có (apply) |
+| `reduce <root> --pct N \| --qty Q [--entries keep\|cancel] [--cancel-idx I,J]` / `reduce show <ref>` / `reduce apply <ref> --confirm --hash H` / `reduce status <op_id>` | §6A – chỉ đóng, **market-only ở P1**, tắt cứng tới khi D26/D29 đạt; dùng được khi khoá/kill. `--exec maker` = P1b, `--target-liq-distance` = P2 (từ chối khi cờ tắt) | Có (apply) |
+| `entries <root> --cancel IDX[,…] \| --cancel-all` / `entries apply <ref> --confirm --hash H` | `entry_adjust`: chỉ huỷ lớp chờ, không bao giờ gửi lệnh đóng; luôn bật | Có (apply) |
+| `ops list` / `ops show <op_id>` | Nhật ký bước §6.5, trạng thái RECOVERING/FAILED_SAFE | Không |
 | `liq [--json]` | Liq một leg + xấu nhất toàn TK cho mọi leg, ngưỡng cảnh báo bậc | Không |
@@ -732,4 +883,8 @@
 bucket: {loss_budget_frac: 0.5, min_lock_days: 7}
-reduce: {urgent_liq_pct: 5, maker_timeout_s: 60, plan_ttl_s: 120, drift_pct: 0.3,
-         alert_liq_pct: {than_trong: 30, can_bang: 20, mao_hiem: 10}, alert_hysteresis_pts: 2}
+reduce: {plan_ttl_s: 120, drift_pct: 0.3, equity_drift_pct: 1.0, slip_est_pct: 0.1,
+         step_timeout_s: 10, protect_timeout_s: 30, max_resend: 2,
+         maker_enabled: false, maker_timeout_s: 60, urgent_liq_pct: 5,   # P1b
+         target_enabled: false,                                          # P2
+         alert_liq_pct: {than_trong: 30, can_bang: 20, mao_hiem: 10}, alert_hysteresis_pts: 2, alert_default_pct: 30}
+# REDUCE_SL_MODE KHÔNG có trong cấu hình: là hằng trong mã (§10.3)
 ```
@@ -738,3 +893,3 @@
 
-`HARD_MAX_WIDE_LADDERS = 4`, `HARD_WEEKLY_STOP_MAX = 15%`, `HARD_DD_BREAKER_MAX = 25%`, `HARD_RISK_BUCKET_MAX = 20%`, `HARD_LEVERAGE_MAX_PER_SYMBOL = 50` (thay 2 hằng leverage cũ), `HARD_PROFILE_RAISE_COOLDOWN_MIN = 24h`, `HARD_PLAN_EQUITY_DRIFT = 1%`, `HARD_MARKET_SHIFT_TOL = 0.3%`, `HARD_TP_MODE_DEFAULT = plan_market`, `HARD_REDUCE_URGENT_MIN = 3%` (ngưỡng khẩn không được cấu hình thấp hơn), `HARD_REDUCE_CLOSE_ONLY = true` (mã `reduce` không có đường gọi `tradeSide=open`).
+`HARD_MAX_WIDE_LADDERS = 4`, `HARD_WEEKLY_STOP_MAX = 15%`, `HARD_DD_BREAKER_MAX = 25%`, `HARD_RISK_BUCKET_MAX = 20%`, `HARD_LEVERAGE_MAX_PER_SYMBOL = 50` (thay 2 hằng leverage cũ), `HARD_PROFILE_RAISE_COOLDOWN_MIN = 24h`, `HARD_PLAN_EQUITY_DRIFT = 1%`, `HARD_MARKET_SHIFT_TOL = 0.3%`, `HARD_TP_MODE_DEFAULT = plan_market`, `HARD_REDUCE_URGENT_MIN = 3%` (ngưỡng khẩn không được cấu hình thấp hơn), `HARD_REDUCE_CLOSE_ONLY = true` (mã `reduce` không có đường gọi `tradeSide=open`), **`REDUCE_SL_MODE = disabled`** (giá trị `position_persist`/`preplace_guard` chỉ đặt được bằng thay đổi mã sau khi D26/D29 đạt và ghi `docs/decisions.md`; runtime chỉ được hạ về `disabled`), `HARD_REDUCE_MAX_RESEND = 2`, `HARD_SCALP_MAX_CONCURRENT = 1` (theo C28).
 
@@ -769,9 +924,18 @@
 | U37 | R14' tính với size thật/giá khớp thật/TP1_DONE ≈ 0/Scalp + trượt; Cân bằng 4 thang 18.62%; Mạo hiểm 3 Wide + Scalp 20.82% |
-| U38 | Mô hình liq 6A.2: (A) 2159.72 / 9.47%; giảm 20/30/50% → 11.89 / 13.70 / 19.38%, realized −4.17 / −6.35 / −10.62, WCL 66.84 / 61.01 / 49.61 (±0.01); (B) xấu nhất có L4 = 9.65% vs một leg 12.16%; giảm 30% keep / shrink / cancel = 12.81 / 13.95 / 17.51%, WCL 62.02 / 58.32 / 49.80; Wide ~71.7% → ~92.8% |
-| U39 | `--target-liq-distance`: (A) 10% → 0.11 ETH, 12% → 0.44 ETH; (B) keep 10% → 0.08, cancel → 0; đơn điệu theo k; không đạt → thông báo + gợi ý cancel; mmr = max(API bậc, floor) |
+| U38 | Mô hình liq 6A.2: (A) 2159.72 / 9.47%; giảm 20/30/50% → 11.89 / 13.70 / 19.38%, realized −4.17 / −6.35 / −10.62, WCL 66.84 / 61.01 / 49.61 (±0.01); (B) xấu nhất có L4 = 9.65% vs một leg 12.16%; giảm 30% keep / cancel = 12.81 / 17.51%, WCL 62.02 / 49.80; chỉ huỷ L4 (entry_adjust) 12.16% / WCL 65.76; (thu L4 0.30 qua `ladder edit` + giảm 30%) 13.95% / 58.32; Wide ~71.7% → ~92.8% |
+| U39 | **(P2)** `--target-liq-distance`: (A) 10% → 0.11 ETH, 12% → 0.44 ETH; (B) keep 10% → 0.08, cancel → 0; đơn điệu theo k; không đạt → thông báo + gợi ý cancel; mmr = max(API bậc, floor) |
 | U40 | Close-only: bảng hedge mode (đóng long = buy+close, đóng short = sell+close), không `reduceOnly`, không đường nào tạo `tradeSide=open`; size floor lot, phần còn lại ≥ minTradeNum hoặc 0; 100% → `close-positions` có holdSide |
-| U41 | Chọn thực thi: liq < 5% → market; ≥ 5% → maker ở ask/bid, đặt lại 1 lần khi bị từ chối, timeout 60 s → hỏi; rơi dưới khẩn khi đang chờ → KHẨN + đề xuất, không tự chuyển; khớp một phần cập nhật Q/TP/WCL |
-| U42 | Thứ tự: huỷ/thu lớp chờ trước, xác nhận, rồi mới close; lớp định huỷ đã khớp → dừng và hỏi; sau reduce: TP size = floor(f1·Q') / Q' − qTP1; SL giá không đổi; đúng 1 pos_loss |
+| U41 | **(P1b)** Chọn thực thi khi bật maker: liq < 5% → market; ≥ 5% → maker ở ask/bid, đặt lại 1 lần khi bị từ chối, timeout 60 s → hỏi; rơi dưới khẩn khi đang chờ → KHẨN + đề xuất, không tự chuyển; khớp một phần cập nhật Q/TP/WCL |
+| U42 | Thứ tự: huỷ lớp chờ trước, xác nhận, rồi mới close (không có shrink trong reduce); lớp định huỷ đã khớp → dừng và hỏi; sau reduce: TP size = floor(f1·Q') / Q' − qTP1; SL giá không đổi; đúng 1 pos_loss |
 | U43 | Bộ đếm: khoá ngày/tuần chỉ thêm phí + trượt (vd −18.17 → −19.09); WCL & ngân sách xô tính realized một phần; không tính vào chuỗi stop; reduce chạy được khi khoá ngày/tuần/DD/xô và `PROTECT_ONLY`, bị chặn khi `RECONCILING`/`DRIFT` |
-| U44 | Cảnh báo thanh lý: ngưỡng theo bậc, hysteresis 2 điểm, KHẨN mỗi 5 phút dưới 5%, đề xuất dựng sẵn đúng mục tiêu ngưỡng + 2; **không bao giờ tự thực thi**; kiểm tra thêm lớp Scalp dùng `max(3%, ngưỡng bậc)` |
+| U44 | Cảnh báo thanh lý: ngưỡng theo bậc, hysteresis 2 điểm, KHẨN mỗi 5 phút dưới 5%, bản dựng sẵn = entry_adjust nếu riêng huỷ lớp đạt ngưỡng + 2, nếu không reduce 30% (P1; không tự giải khối lượng), chỉ entry_adjust/`ladder close` khi `REDUCE_SL_MODE = disabled`; **không bao giờ tự thực thi**; kiểm tra thêm lớp Scalp dùng `max(3%, ngưỡng bậc)` |
+| U45 | `entry_adjust`: khối lượng giải ra = 0 → tạo `kind: entry_adjust`, **0 lời gọi `place-order tradeSide=close`** (kiểm mock); ví dụ 6A.7(B) huỷ L4 → 12.16% / WCL 65.76; chạy được khi `REDUCE_SL_MODE = disabled` và khi đang khoá; `--qty 0` với `kind: reduce` bị từ chối |
+| U46 | Băm canonical §5.4: vector cố định (bản ghi → chuỗi canonical → SHA-256); đổi bất kỳ trường nào của `hash_content` (close_qty, qty_source, exec_mode, entry_actions, preconditions, tolerances, expires_at) → hash khác; đổi `status`/`edit_log.text` → hash không đổi; float trong bản ghi → lỗi; bản ghi DB/file bị sửa → execute/apply từ chối; `--hash` sai tiền tố → từ chối |
+| U47 | Máy trạng thái reduce 6A.8 (sàn giả lập): mọi chuyển hợp lệ; tiêm lỗi ở từng bước (timeout, từ chối, lớp đã khớp khi huỷ, SL đổi trigger / size đổi trước RECONCILING, khớp một phần, SL kích hoạt đồng thời) → đúng trạng thái kết thúc; **không gửi close khi RECONCILING lệch**; trên **mọi** trạng thái trung gian leg có vị thế có ≥ 1 SL bao trọn vị thế |
+| U48 | `REDUCE_SL_MODE`: `disabled` → `reduce` từ chối với thông báo, `entries`/`ladder close` vẫn được; không có khoá cấu hình/biến môi trường nào bật được; runtime phát hiện SL mất sau reduce → hạ về `disabled`, KHẨN, đặt pos_loss |
+| U49 | `preplace_guard` (mock): thứ tự G → xác nhận → close → chuẩn hoá; G không xác nhận → không close, huỷ G; pos_loss còn → huỷ G; pos_loss mất → đặt pos_loss, xác nhận, rồi mới huỷ G; trạng thái cuối đúng 1 SL cấp vị thế |
+| U50 | Phục hồi §6.5 + RECOVERING 6A.8: crash sau mỗi trạng thái bước (planned/sent/confirmed) của `execute`, `ladder apply`, `reduce apply`, `entries apply` → hành động đúng quy tắc; bước tăng rủi ro không bao giờ gửi lại; close chỉ gửi lại trong TTL 120 s & lệch ≤ 0.3%; idempotent theo clientOid (truy vấn trước khi gửi); `observed_state` đúng; tiếp tục chỉ bằng phiên bản mới |
+| U51 | Ràng buộc Wide/Scalp §3.5: 1 thang/(symbol, holdSide) qua mọi chế độ; ma trận cap (cái chặt nhất thắng, R10w vs R10a); R14 phần Wide = bậc − per_ladder_scalp; `propose` bỏ cặp có Scalp; Cân bằng có xô: Wide ≤ 3 khi Scalp mở; Scalp ≤ 1; leverage symbol dùng chung |
+| U52 | Khoá §8.4: ranh giới 06:59:59 / 07:00:00 UTC+7 (ngày) và thứ Hai 07:00 (tuần); mốc trễ `day_start_late`; chuyển tiền bị loại; phí reduce tính vào; không mở khi E hồi; ma trận được/chặn đủ các ô; không còn khoá ngày Scalp riêng |
+| U53 | Nhãn kỳ vọng §2.6: digest/status/README chỉ in số có `config_hash` khớp + B-id đạt; cấu hình chưa kiểm → "chưa kiểm định bằng backtest"; chuỗi "+38" / "+41.6" không xuất hiện cho bậc nào |
 
@@ -789,5 +953,8 @@
 | D25 | Một ngày đầy đủ: digest → sửa → duyệt → fill → TP1 → khoá ngày giả lập | Thông báo đúng mẫu, đúng giờ UTC+7 |
-| D26 | **Reduce một phần trong hedge mode** khi có cả long và short cùng symbol: market `buy+close` 30% long | Chỉ long giảm đúng size, short nguyên; `pos_loss` long **vẫn tồn tại, trigger không đổi, áp cho size còn lại** (đọc `orders-plan-pending` + cho mark chạm SL trên Demo → đóng đúng phần còn lại) |
-| D27 | Reduce maker post-only ở ask: khớp một phần, timeout 60 s, huỷ phần còn lại | Phần khớp ghi đúng; lệnh limit close không làm SL đóng thiếu (kết hợp D9) |
-| D28 | Reduce khi đang khoá ngày và khi `kill` PROTECT_ONLY; reduce 100% | Được phép; 100% dùng `close-positions` holdSide, rồi mới huỷ SL/TP |
+| D26 | **Cổng `position_persist`**. Hedge mode, có cả long và short ETH: (1) market `buy+close` 30% long; (2) `orders-plan-pending` mỗi 1 s trong 60 s: `pos_loss` long luôn tồn tại, trigger không đổi; (3) cho mark chạm SL → đóng **đúng toàn bộ phần còn lại**, short nguyên; (4) lặp với một lớp entry khớp sau reduce | Mọi bước đạt → được đặt `REDUCE_SL_MODE = position_persist`. Bất kỳ bước nào FAIL → không bật; xem D29 |
+| D27 | **(P1b)** Reduce maker post-only ở ask: khớp một phần, timeout 60 s, huỷ phần còn lại | Phần khớp ghi đúng; lệnh limit close không làm SL đóng thiếu (kết hợp D9) |
+| D28 | Reduce market khi đang khoá ngày và khi `kill` PROTECT_ONLY (sau khi reduce bật); `ladder close --pct 100` | Được phép; 100% dùng `close-positions` holdSide, xác nhận size = 0 rồi mới huỷ SL/TP |
+| D29 | **Cổng `preplace_guard`** (chỉ khi D26 FAIL): đặt `loss_plan` size Q_after cùng trigger khi đã có `pos_loss`; đóng 30%; cho mark chạm trigger khi cả 2 SL còn | 2 SL cùng tồn tại được; kích hoạt kép **không mở vị thế ngược**, short không bị ảnh hưởng; kết thúc còn đúng 1 SL cấp vị thế. FAIL → reduce giữ `disabled` |
+| D30 | Kill tiến trình khi reduce đang ở CANCELLING_ENTRIES, CLOSING (đã gửi, chưa xác nhận) và UPDATING_PROTECTION; và khi `ladder apply` đang ở PLACE_ENTRY | Khởi động lại → RECOVERING đúng §6.5/6A.8; không lệnh trùng; không bước tăng rủi ro nào gửi lại |
+| D31 | `entries --cancel` khi đang khoá ngày và khi `REDUCE_SL_MODE = disabled` | Chỉ huỷ lớp; không có lệnh đóng nào trên sàn |
 
@@ -798,2 +965,3 @@
 - **B8** (thay B4, là cổng): Scalp theo §3.4 với ngân sách xô, khoá xô, phí taker; chủ ký duyệt trước khi bật xô live.
+- **B9** (cổng hiển thị kỳ vọng §2.6): chạy lại Cân bằng / Thận trọng / Mạo hiểm bằng **mã của công cụ** (B2) với TP `plan_market` (taker), BE theo spec, L1 post-only có mô hình khớp, độ trễ mở lại = tới digest kế tiếp (≤ 24 h) và chỉ chiều đèn xanh, khoá ngày/tuần §8.4; xuất `config_hash`. Đây là nguồn duy nhất cho số kỳ vọng hiển thị.
 
@@ -822,8 +990,13 @@
 | C17 | Giờ và kênh gửi digest | 07:05 UTC+7, kênh chat trợ lý (+ email cho mức CAO/KHẨN, theo Q6) |
-| C18 | Ngưỡng khẩn của `reduce` (dưới mức này mặc định market) | **5%** khoảng cách liq xấu nhất toàn TK, mọi bậc (sàn cứng 3%) |
-| C19 | Kiểu thực thi mặc định khi không khẩn | **Maker post-only** ở giá tốt nhất, chờ 60 s rồi hỏi (market / đặt lại / dừng) |
-| C20 | Lớp DCA chưa khớp khi reduce | **Huỷ lớp sâu nhất trước** nếu giữ lớp làm liq xấu nhất < mục tiêu; ngược lại giữ; `shrink` là phương án hiển thị |
-| C21 | Ngưỡng cảnh báo thanh lý theo bậc | 30% / 20% / 10% (Thận trọng / Cân bằng / Mạo hiểm); chỉ cảnh báo + dựng sẵn đề xuất, không tự chạy |
+| C18 | **(P1b)** Ngưỡng khẩn của `reduce` (dưới mức này `auto` chọn market) | **5%** khoảng cách liq xấu nhất toàn TK, mọi bậc (sàn cứng 3%) |
+| C19 | Kiểu thực thi | **P1: chỉ market.** Từ P1b (sau U41 + D27): mặc định maker post-only khi ≥ ngưỡng khẩn, chờ 60 s rồi hỏi |
+| C20 | Lớp DCA chưa khớp khi reduce | P1: `keep`/`cancel`; **huỷ lớp sâu nhất trước** nếu giữ lớp làm liq xấu nhất < mục tiêu; riêng huỷ đã đủ → `entry_adjust` (không đóng); thu size lớp chỉ qua `ladder edit` |
+| C21 | Ngưỡng cảnh báo thanh lý theo bậc | 30% / 20% / 10% (Thận trọng / Cân bằng / Mạo hiểm); chỉ cảnh báo + dựng sẵn entry_adjust hoặc reduce 30% (P1), không tự chạy |
 | C22 | Kiểm tra thêm lớp Scalp dùng `max(3%, ngưỡng cảnh báo bậc)` thay vì chỉ 3% | Có |
 | C23 | Lỗ chốt bởi `reduce` tiêu ngân sách thang/xô (lãi không bù), nhưng không tính là SL trong chuỗi stop | Có |
+| C24 | Nếu D26 FAIL: làm `preplace_guard` (phải qua D29) hay giữ reduce tắt? | Làm `preplace_guard` sau go-live P1; trong lúc chờ dùng `entries` và `ladder close` |
+| C25 | Sau crash, có gửi lại lệnh đóng đã duyệt mà chưa tới sàn không? | Chỉ khi còn trong 120 s từ lúc duyệt và mark lệch ≤ 0.3%; ngược lại dừng an toàn và hỏi |
+| C26 | Bỏ khoá ngày riêng của Scalp (SPEC 4.12.5), chỉ giữ khoá ngày toàn tài khoản + ngân sách xô | Có |
+| C27 | Chỉ hiển thị số kỳ vọng đã qua B9 cho đúng cấu hình; tạm thời Cân bằng hiện số SAFE với nhãn "cận trên" | Có |
+| C28 | Số thang Scalp tối đa cùng lúc | 1 |
```
