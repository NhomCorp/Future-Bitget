# Kế hoạch DCA ladder – Bitget USDT-M (BTCUSDT, ETHUSDT) – vốn 524.87 USDT

Lập lúc 2026-10-20 ~02:00 (UTC+7). Tài khoản đang trống: không có vị thế, không có lệnh chờ/lệnh plan. Equity futures **524.87 USDT**.
Mọi số liệu lấy từ API chỉ đọc (GET) + nến 1m public. Không đặt/sửa/huỷ lệnh nào.

---
## 0. Kết luận trước (nói thẳng)
1. **Kiểu micro-grid hiện tại (bước 0.2%, TP 0.3%) không có lợi thế sau phí**, kể cả khi hạ đòn bẩy xuống 8x:
   mô phỏng 180 ngày **−41%** khi có stop (phí = 158% lãi gộp), và **cháy tài khoản** khi không có stop (cả trong 90 ngày tăng giá gần đây).
2. Vùng tham số còn dương sau phí là **thang thưa**: 5 lớp cách nhau 1.5%, khối lượng đều, TP 1.2% tính từ giá trung bình,
   **hedge cả 2 chiều, cả BTC lẫn ETH**, tổng notional tối đa ≈5x equity, **stop cứng −5…−7% equity cho mỗi thang**.
   Trong 180 ngày (gồm 90 ngày giảm −20% và 90 ngày tăng +25%) nhóm này dương ở 12/12 biến thể lân cận (cap 4–6x, stop 5–7%).
3. **Lợi thế mỏng và không chắc chắn.** Khi quét rộng 62k + 101k bộ tham số thì trung vị là **lỗ** (−15…−30% mỗi 90 ngày),
   chỉ khoảng 1% số bộ dương ở cả 2 coin và cả 2 giai đoạn. Bộ khuyến nghị được chọn trên chính dữ liệu này → kết quả thật sẽ kém hơn backtest.
4. **Mục tiêu 700k VND/ngày (~27 USDT/ngày = 5.1%/ngày) là không thực tế ở mức rủi ro này.** Phương án mặc định ra trung bình
   ~1.1 USDT/ngày (~29k VND/ngày); phương án mạnh nhất cũng chỉ ~1.2–2 USDT/ngày; chỉ 1.7–6.7% số ngày đạt ≥700k VND.
   Để đạt 700k/ngày phải dùng notional 50–100x equity như trước → chính là trạng thái từng cách thanh lý 0.06% (xem mục 6).

---
## 1. Phương án MẶC ĐỊNH (khuyến nghị)
| Thông số | Giá trị |
|---|---|
| Cặp / chế độ | BTCUSDT + ETHUSDT, Hedge mode, Cross. 4 thang: BTC Long, BTC Short, ETH Long, ETH Short |
| Tổng exposure tối đa | **5x equity = 2,624 USDT** (mỗi thang tối đa **1.25x = 656 USDT**) |
| Đòn bẩy cài trên sàn | 10x là đủ (chỉ để giữ margin thấp; rủi ro do notional quyết định, không phải con số leverage) |
| Số lớp | **5** (lớp 1 + 4 lớp DCA) |
| Khoảng cách | **1.5% cố định** giữa các lớp (≈ 2–3 ATR(14) 1h hiện tại: BTC 0.49%, ETH 0.76%). Tổng thang phủ ~5.9% |
| Khối lượng | **đều nhau**: ~131 USDT/lớp (BTC 0.0016, ETH 0.05) |
| Chốt lời | **TP1 = +1.2% từ giá TB → đóng 50%**; sau TP1 **ngừng DCA**, phần còn lại TP2 = +2.4% từ giá TB cũ, hoặc thoát hoà vốn nếu giá quay về giá TB |
| Stop cứng | **−7% equity cho mỗi thang** (~−37 USDT ≈ −0.97M VND), đặt ngay khi mở lớp 1; với thang đầy nằm ở ~−8.5…−9% từ giá lớp 1 |
| Phí | Lệnh vào và TP: post-only maker 0.02%; stop: taker 0.06% |

**Backtest (1 tài khoản cross chung BTC+ETH, nến 1m, phí + funding thật, thanh lý & stop có mô phỏng, vốn đầu 524.87):**
| Giai đoạn | Lợi nhuận | Max DD | Stop bị hit | Phí / lãi gộp | USDT/ngày | VND/ngày | Ngày tệ nhất |
|---|---|---|---|---|---|---|---|
| 180 ngày (04-22 → 10-20) | **+38.0%** (→724) | 24.9% | 28 | 26.8% | 1.11 | ~29k | −57.9 USDT |
| 90 ngày giảm (BTC −20%) | +6.2% | 18.8% | 17 | 37.8% | 0.36 | ~9k | −53.5 |
| 90 ngày tăng (BTC +24%) | +30.7% | 26.3% | 10 | 17.6% | 1.79 | ~47k | −65.3 |
Không cháy tài khoản. 484 chu kỳ, win rate 94%, chu kỳ tệ nhất −50 USDT, ngày dương 67%. Luôn có vị thế (time in market 100%).
Notional thực tế cao nhất 4.0x equity; tỉ lệ duy trì (MM/equity) cao nhất chỉ 1.8%.

## 2. Hai phương án khác
| | AN TOÀN | MẠNH TAY |
|---|---|---|
| Tổng cap | **3x** (mỗi thang 0.75x ≈ 394 USDT, ~79 USDT/lớp) | **8x** (mỗi thang 2x ≈ 1,050 USDT, ~210 USDT/lớp) |
| Thang | giống mặc định (5 lớp, 1.5%, đều, TP1 1.2%/50%, TP2 2.4%) | giống mặc định |
| Stop | **−5% equity/thang** | −7% equity/thang |
| 180 ngày | +22.9%, DD 19.0%, 23 stop, 0.67 USDT/ngày (~17k VND) | +41.6%, DD 29.1%, 49 stop, 1.21 USDT/ngày (~32k VND) |
| 90 ngày giảm / tăng | −1.4% / +20.8% | +30.7% / +16.0% |
| Ngày tệ nhất | −37 USDT | −92 USDT |
| Phí / lãi gộp | 24.9% | 42.3% |
Ghi chú: biến thể 8x với khối lượng tăng dần x1.3 cho +73% / 180 ngày nhưng −2.5% ở giai đoạn giảm → quá mong manh, không khuyến nghị.
Nâng cap lên 10x với cùng thang làm kết quả **kém đi** (+19%, DD 28.5%) – thêm rủi ro không thêm lợi nhuận.

## 3. Quy tắc vận hành
**Khi nào mở thang**
- Hedge luôn bật: mỗi coin có 1 thang Long và 1 thang Short chạy độc lập. Khi một thang đóng (TP2/hoà vốn/stop) → mở thang mới cùng chiều ngay ở giá hiện tại (lệnh post-only sát giá).
- Lớp 1 = 1/5 cap của thang. Đặt sẵn 4 lệnh limit DCA cách nhau 1.5% + lệnh stop cứng ngay lúc mở (dùng `ladder.py` để in giá/khối lượng).
- Bộ lọc xu hướng (ADX 4h > 30, hay chỉ vào khi giá lệch xa EMA50 1h) **không cải thiện** kết quả của nhóm thang thưa → không bắt buộc. Nếu muốn dùng: chỉ được dùng để *bỏ qua* việc mở thang mới, không được dùng làm lý do bỏ stop.

**Tối đa lớp / ngừng DCA**
- Tối đa 5 lớp. **Không thêm lớp thứ 6**, không "nhồi tay" ngoài thang.
- Sau TP1 (đã đóng 50%) → huỷ các lệnh DCA còn lại của thang đó.

**Giới hạn cùng chiều BTC+ETH**
- Tổng notional Long (BTC+ETH) ≤ **2.5x equity** (≈1,312 USDT); tương tự cho Short. BTC và ETH tương quan 0.87 (lợi nhuận 1h, 180 ngày) nên 2 thang cùng chiều đầy cùng lúc ≈ một thang 2.5x.
- Tổng notional mọi vị thế ≤ **5x equity**. Kiểm tra lại mỗi khi equity thay đổi >10% (tính lại khối lượng thang theo equity mới lúc mở thang).

**TP / scale-out**: TP1 1.2% (50%) → TP2 2.4% hoặc thoát hoà vốn. TP luôn ≥1.2% nên phí maker 2 chiều (0.04%) chỉ ~3% lợi nhuận mỗi lần chốt.

**Dừng khẩn cấp**
- Stop cứng −7% equity/thang, **không được dời ra xa, không được huỷ**.
- (Khuyến nghị thêm, chưa backtest) Equity giảm ≥20% so với đỉnh gần nhất → đóng hết, nghỉ 24h, rồi chạy lại ở phương án AN TOÀN.
- Không bao giờ để notional > 5x equity, kể cả khi "đang gồng sắp về".

## 4. Bảng thang mẫu (phương án mặc định, equity 524.87, giá live lúc ~02:00 UTC+7)
Liq trong bảng tính cho riêng 1 thang dùng cả equity (MMR BTC 0.4%, ETH 0.5%); khi chạy đủ 4 thang thì giá thanh lý thực tế gần hơn nhưng vẫn rất xa vì tổng notional ≤5x.

**ETHUSDT Long** (ATR 1h 0.76%, 4h 1.59%)
| Lớp | Giá | Δ% | ETH | USDT | TB | TP1 (+1.2%) | TP2 (+2.4%) |
|---|---|---|---|---|---|---|---|
| 1 | 2400.82 | 0 | 0.05 | 120.0 | 2400.82 | 2429.63 | 2458.44 |
| 2 | 2364.81 | −1.50 | 0.05 | 118.2 | 2382.81 | 2411.41 | 2440.00 |
| 3 | 2329.34 | −2.98 | 0.05 | 116.5 | 2364.99 | 2393.37 | 2421.75 |
| 4 | 2294.40 | −4.43 | 0.05 | 114.7 | 2347.34 | 2375.51 | 2403.68 |
| 5 | 2259.98 | −5.87 | 0.05 | 113.0 | 2329.87 | 2357.83 | 2385.78 |
Stop cứng 2182.91 (−9.08% từ lớp 1), lỗ ≈37 USDT. Liq ước tính ~232 (rất xa).

**ETHUSDT Short**: lớp 2400.82 / 2436.83 / 2473.38 / 2510.49 / 2548.14 (0.05 ETH mỗi lớp), TB đầy 2473.93, TP1 2444.25, TP2 2414.56, **stop 2620.89**.

**BTCUSDT Long** (ATR 1h 0.49%, 4h 0.97%)
| Lớp | Giá | Δ% | BTC | USDT | TB | TP1 | TP2 |
|---|---|---|---|---|---|---|---|
| 1 | 81950.1 | 0 | 0.0016 | 131.1 | 81950.1 | 82933.5 | 83916.9 |
| 2 | 80720.8 | −1.50 | 0.0016 | 129.2 | 81335.5 | 82311.5 | 83287.5 |
| 3 | 79510.0 | −2.98 | 0.0016 | 127.2 | 80727.0 | 81695.7 | 82664.4 |
| 4 | 78317.4 | −4.43 | 0.0016 | 125.3 | 80124.6 | 81086.1 | 82047.6 |
| 5 | 77142.6 | −5.87 | 0.0017 | 131.1 | 79498.7 | 80452.7 | 81406.7 |
Stop cứng 74962.8 (−8.53%), lỗ ≈37 USDT.

**BTCUSDT Short**: lớp 81950.1 / 83179.4 / 84427.0 / 85693.4 / 86978.8 (0.0016/0.0015…), TB đầy 84412.9, TP1 83400.0, TP2 82387.0, **stop 89247.2**.

CSV đầy đủ: `out/plan_{ETHUSDT,BTCUSDT}_{long,short}.csv`.

## 5. Cách backtest
- Dữ liệu: nến 1m Bitget USDT-M, 2026-04-22 → 2026-10-20 (180 ngày, 259,199 nến/coin, đã vá hết khoảng trống), funding thật 8h (long trả / short nhận).
- Thứ tự trong mỗi nến 1m (thận trọng): khớp lớp DCA ở cực trị bất lợi → stop → kiểm tra thanh lý (equity tại cực trị bất lợi ≤ MMR × notional) → TP ở cực trị thuận lợi.
- Kích thước thang tính theo equity lúc mở thang (có lãi kép). Phí maker 0.02% vào/TP, taker 0.06% stop/hoà vốn.
- Quét: giai đoạn 1 = 62,208 bộ × 2 coin × 3 giai đoạn; giai đoạn 2 = 101,088 bộ (thang thưa/hình học); giai đoạn 3 = 2,592 bộ trong tài khoản chung 4 thang; cuối cùng kiểm tra lân cận của bộ được chọn.
- Kết quả chi tiết: `results/` (grid*.csv, combined_grid.csv, final_eval.csv). Biểu đồ: `equity_top3.png`.

## 6. Nhìn lại giai đoạn 2026-10-09 → 10-20 01:47 (bỏ lệnh ETH Long cuối, giá TB 2393.78)
24 vị thế đóng: 22 thắng / 2 thua, ròng **+451.97 USDT** (gộp +573.35, phí −122.01 = 20.8% lãi gộp, funding +0.64).
Lệnh tốt nhất +68.70 (BTC short), tệ nhất −14.46 (ETH short 10-19 19:06). Phần lớn lãi đến vào 10-19/10-20 (+315).
Notional lớn nhất 34,051 USDT ≈ **95x equity** (10-20 01:07). Gần thanh lý nhất: **10-15 20:52** – equity ~28 USDT vs 6,020 USDT notional (218x),
MM ≈ 87% equity theo giá đóng nến (>100% theo cực trị nến 1m) – chỉ cần thêm ~0.06% là thanh lý. Các lần sát khác: 10-09 00:26 (~90%), 10-20 01:07 (~46%), 10-19 18:34 (~45%).
=> Kết quả tốt là thật, nhưng đến từ việc chấp nhận rủi ro cháy tài khoản. Backtest của chính kiểu này ở 8x không stop cháy tài khoản.

## 7. Lưu ý
- Backtest không có trượt giá, giả định lệnh post-only luôn khớp đúng giá; nến 1m không biết thứ tự đỉnh/đáy bên trong.
- MMR dùng tier 1 (BTC 0.4%, ETH 0.5%), không tính phí thanh lý; với notional ≤5x thì thanh lý gần như không thể, rủi ro chính là stop liên tiếp.
- 180 ngày chỉ có 2 chế độ thị trường; một cú chạy mạnh một chiều (VD BTC +11.6% trong 24h tới 2026-08-20 18:05 UTC+7) sẽ hit stop của cả thang BTC và ETH cùng chiều (≈ −14% equity).
- Chọn tham số trên chính dữ liệu đã test → kỳ vọng thực tế thấp hơn. Nên chạy thử phương án AN TOÀN 2–4 tuần, theo dõi bằng journal, rồi mới nâng lên mặc định.
