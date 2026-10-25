# Spec định hướng: Bot futures theo zone và AI học phong cách

- Trạng thái: Dự thảo cập nhật 2026-10-22, chờ chủ sở hữu duyệt
- Phạm vi: Định hướng sản phẩm và các cổng triển khai, chưa phải thông số giao dịch đã chốt
- Thứ tự ưu tiên: Bot tự trade có giới hạn lỗ theo mandate/zone, sau đó AI học phong cách và đề xuất, cuối cùng mới xét tự thực thi tự động trong mandate đã cấp

## 1. Mục tiêu

Xây bot tự quản lý vị thế Bitget USDT-M Futures. Người dùng cấp vốn, allowlist và mandate với các giới hạn rủi ro; AI có thể tự phân tích và tự mở/quản lý/đóng vị thế trong mandate sau khi mode tự chủ được bật. Bot dừng tăng rủi ro khi không thể chứng minh trạng thái an toàn, không tự nạp margin và không thể thay đổi hard limits. Sau khi dữ liệu quyết định đủ tin cậy, AI học cách người dùng đánh và kết hợp kiến thức/phong cách đã được người dùng nạp; việc học chỉ tạo phiên bản model/strategy mới qua quy trình đánh giá, không tự sửa policy đang chạy.

Vốn được cấp là trần quản lý, không phải mức lỗ được phép. Cần tách rõ vốn được cấp, margin, exposure, rủi ro mỗi lệnh, loss budget, daily loss, drawdown và chuỗi lỗ liên tiếp.

Ưu tiên hiển thị giá dạng số và khoảng cách/rủi ro theo phần trăm; volume là thông tin phụ. Mọi kết quả PnL phải tách gross, phí, funding và net.

## 2. Mô hình subaccount và zone

- Subaccount Bitget là phạm vi tài khoản mà bot được phép vận hành.
- Bot hỗ trợ nhiều symbol và cả Long lẫn Short.
- **Mỗi zone là một cấu hình giao dịch độc lập gắn với một vị thế**: gồm symbol, side, isolated margin, hạn mức lỗ, target lợi nhuận, policy entry/DCA/đóng, chế độ Kiểm soát hoặc Nonstop và các tham số riêng khác.
- Các zone được cấu hình riêng, nên target có thể khác nhau, ví dụ Zone 1 đặt 2%, Zone 2 đặt 10%. Đây là cấu hình do người dùng chọn trong giới hạn policy; không bị giới hạn chỉ ở 2% hoặc 5%.
- Với mỗi cặp định danh `subaccount + symbol + side`, bot chỉ cho phép **một zone đang hoạt động** và zone đó quản lý tối đa một vị thế. Có thể lưu nhiều cấu hình mẫu cho cùng symbol/side, nhưng không chạy đồng thời nhiều zone cùng định danh nếu Bitget position mode không thể cô lập chúng.
- Mỗi zone chạy bằng **isolated margin** trên subaccount. Đây là yêu cầu vận hành, phải xác minh lại bằng Demo và trạng thái thực tế từ Bitget trước khi live.
- Zone có `zone_loss_limit` riêng, là giới hạn lỗ tối đa của vị thế, không phải một subaccount riêng.
- Không chuyển ngân sách giữa các zone; không tự nạp/chuyển margin.
- Nếu Bitget hoặc cấu hình tài khoản không bảo đảm vị thế isolated của zone không ảnh hưởng đến zone khác, bot phải chặn live và không mô tả zone là cô lập tuyệt đối.

### 2.1 Ngân sách lỗ và mục tiêu lợi nhuận

`zone_loss_limit` là mức lỗ ròng tối đa được policy cho phép cho vòng đời vị thế, tính trên tổng kết quả của các lệnh thuộc zone:

`zone_net_pnl = realized_pnl + unrealized_pnl - fees - funding_paid + funding_received`

Mục tiêu lợi nhuận được nhập theo phần trăm và tính trên hạn mức zone:

`target_net_profit = zone_loss_limit × target_profit_pct / 100`

`target_net_profit` là số **net**, đã trừ phí và funding. Mỗi zone được chọn `target_profit_pct` riêng, ví dụ Zone 1 = 2% và Zone 2 = 10%. Giá trị phải nằm trong policy/hard limits đã được duyệt, không được dùng target cao để vượt `zone_loss_limit`, exposure, liquidation hoặc các giới hạn an toàn khác. Công cụ phải hiển thị đồng thời phần trăm mục tiêu, số USDT tương ứng và cách tính. Giá trị đã chọn được ghi vào zone/plan version và không được thay đổi sau khi zone bắt đầu; muốn đổi phải đóng zone hiện tại và mở zone mới.

Cần thống nhất dấu kế toán theo dữ liệu Bitget và tránh trừ lặp phí/funding. Lỗ đã thực hiện không được xoá hoặc cấp lại hạn mức chỉ vì vị thế giảm size. Các khoản nạp/chuyển thủ công được ghi là can thiệp ngoài hệ thống, không tự tăng `zone_loss_limit`.

Giới hạn này là ngưỡng điều khiển của bot, không phải cam kết tuyệt đối về mức lỗ thực tế. Gap, trượt giá, phí, funding, lỗi sàn và thanh lý có thể làm lỗ vượt ngưỡng. Spec triển khai phải định nghĩa buffer, trigger stop, xử lý khẩn cấp và mức vượt tối đa được chấp nhận; nếu không thể kiểm soát/đo được, bot không được mở zone.

## 3. Phạm vi chức năng

### 3.1 Bot tự trade

- Người dùng cấp vốn, mở mandate, chọn allowlist, side, giới hạn vốn/risk và policy giao dịch. Có thể khởi tạo mandate ở cấp subaccount rồi để AI tự tạo zone trong phạm vi đó.
- Bot tạo plan phiên bản hóa gồm giá/điều kiện entry, DCA, đóng từng phần, TP, SL, ngân sách, phí/funding dự kiến và kiểm tra rủi ro.
- Quyền tự trade của bot/AI chỉ áp dụng cho mandate đã cấu hình và được bật. Không tự tăng vốn, margin, leverage hoặc giới hạn.
- Trong mode `MANAGED_ZONE`, người dùng phải mở zone trước. Trong mode `AUTONOMOUS_WITHIN_MANDATE`, AI được tự mở zone/episode mới nếu còn vốn/exposure và zone policy hợp lệ.
- DCA không bị dừng theo đồng hồ; chỉ dừng theo điều kiện policy, ngân sách, vị thế, lỗi hoặc lệnh bảo vệ. Average-down chỉ được phép khi mandate bật và có plan cụ thể.
- Có chế độ Kiểm soát: SL và TP bắt buộc hợp lệ. Có chế độ Nonstop: SL/TP có thể tuỳ chọn, nhưng cảnh báo liquidation bắt buộc và các hard limit vẫn áp dụng. Nonstop không đồng nghĩa bỏ giám sát, bỏ emergency policy hay cho phép dùng vốn vô hạn.
- Không gồng lệnh: không nới SL theo hướng tăng rủi ro, không tăng size để bù lỗ, không mở lệnh mới chỉ để gỡ lỗ. Khi đạt daily loss hoặc chuỗi lỗ tối đa, khóa entry theo mandate và xử lý vị thế đang mở theo policy.
- Không đóng chỉ vì thời gian giữ; vẫn phải xử lý SL, liquidation, mất kết nối, trạng thái không xác định và lệnh khẩn cấp.
- Mọi thay đổi plan tạo phiên bản mới, không sửa đè phiên bản đã duyệt. Hồ sơ rủi ro là trần cứng.
- Theo dõi trạng thái lệnh theo hai trục: `order_role` (entry, DCA, reduce, TP, protective stop, emergency close) và `order_status` (pending, partial, filled, cancelled, unknown).
- Cặp lệnh gồm hai chân được đặt cùng lúc và liên kết bằng `pair_id`. Nếu chân đóng khớp trước chân mở, ghi nhận là `reduce`, không gán nhầm thành vị thế mở. Nếu chỉ một chân khớp, xử lý theo vị thế thực tế trên sàn: reconcile size/side, tính lại ngân sách và lệnh bảo vệ, không giả định chân còn lại đã khớp. PnL theo cặp lệnh phải ghi fills, phí và funding, đồng thời reconcile với PnL/vị thế Bitget.

### 3.2 Học phong cách và kiến thức người dùng

- Thu cả quyết định có giao dịch và cơ hội quyết định không giao dịch.
- Snapshot chỉ chứa dữ liệu đã biết tại `decision_ts`; lưu `feature_asof_ts`, nguồn và phiên bản dữ liệu.
- Người dùng có thể nạp profile phong cách, thói quen, mức ưu tiên, chiến thuật, điều kiện không giao dịch và ghi chú kinh nghiệm. Mỗi bản ghi có version, nguồn, thời điểm áp dụng và phạm vi; nội dung này chỉ là input chiến lược, không được vượt hard limits.
- Dữ liệu thị trường và kết quả giao dịch được dùng để huấn luyện/ranking/evaluation offline. Không tự cập nhật model hoặc policy đang phục vụ live chỉ từ một vài lệnh mới.
- Phân biệt hành động của chủ tài khoản, hành động của bot và hành động của AI. AI không tự tạo ground-truth cho chính nó.
- Giữ nhật ký gốc append-only; nhãn như take-profit, rebalance, risk-reduction, protective-stop và emergency-close được lưu riêng với việc mẫu có đủ điều kiện học phong cách hay không.
- Đánh giá theo thời gian/episode, ngoài mẫu; báo cáo net PnL, drawdown, tail loss, thời gian giữ vốn và chi phí. Không xem số episode cố định là bảo đảm đủ ý nghĩa thống kê.
- Model/strategy mới phải có version và qua shadow/paper evaluation trước khi được gắn vào mandate mới. Không thay model giữa episode đang chạy nếu chưa có quy trình chuyển đổi được phê duyệt.

### 3.3 AI agent

- AI học/ranking hành động và giải thích dựa trên dữ liệu đã ghi; chế độ thực thi được điều khiển bởi `ai_autonomy` trong mandate.
- TA envelope, policy deterministic và risk engine kiểm tra mọi proposal/order intent. AI không tự tính hoặc ghi đè size, margin, liquidation, giới hạn lỗ, symbol/side allowlist hay hard limits.
- AI được tự chọn thời điểm, symbol, side và chiến thuật trong allowlist khi mode `AUTONOMOUS_WITHIN_MANDATE` đã được bật. Đây là quyền tự chủ có giới hạn, không phải quyền tùy ý.
- Dự thảo chu kỳ (chưa chốt P0): mỗi lần quét phân tích rồi ra phương án linh hoạt theo tình huống (0–nhiều hành động, trong mandate); nới SL được nếu Risk Engine duyệt — khác P0 mục 7 cho tới khi chốt. Paper đợt D đã code combo/`ADJUST_SL` local, không POST. Chi tiết: [`ai-agent-autonomous-trading.md`](ai-agent-autonomous-trading.md) mục 5.3.
- AI không tự thay model/policy trong lúc có vị thế, không tự nạp kiến thức chưa version hóa vào live context và không tự cấp thêm vốn.
- Quyền AI tự gửi lệnh chỉ được bật sau cổng hiệu quả và kỹ thuật đạt, phạm vi vốn nhỏ, kill switch, key trade không có withdrawal và xác nhận chủ tài khoản.

### 3.4 Kết nối Tailscale

Ngoài phạm vi MVP giao dịch. Pha sau có gateway riêng qua mạng Tailscale; xác thực/phân quyền vẫn do ứng dụng đảm nhiệm. Mặc định quyền đọc; thao tác lệnh có allowlist, xác nhận, audit log. Không cấp shell hoặc API Bitget tuỳ ý cho AI.

## 4. Dữ liệu và kiểm toán

Tối thiểu mỗi zone cần `zone_id`, `zone_config_version`, `subaccount_id`, symbol, side, isolated margin mode, `zone_loss_limit`, `target_profit_pct` tùy chỉnh theo zone, mẫu số mục tiêu (`zone_loss_limit`), target net PnL USDT, policy entry/DCA/exits, `plan_version`, model/policy version, trạng thái, thời điểm mở/đóng.

Ledger phải là sự kiện chỉ ghi thêm, số dư được tính lại từ sự kiện. Ghi riêng vốn/giới hạn được cấp, margin giữ chỗ/đã dùng, realized/unrealized PnL, phí, funding, deposits/transfers, fills, lệnh và điều chỉnh. Cần chốt cách tránh tính trùng phí/funding khi tính PnL zone.

## 5. Các giai đoạn và cổng

### P0: Chốt spec và xác minh API

Chốt định nghĩa zone, hạch toán lỗ, isolated margin/position mode, mục tiêu lợi nhuận, semantics của hai chân đặt đồng thời, policy DCA, Kiểm soát/Nonstop và điều kiện emergency. Xác minh API Bitget, subaccount, Demo, trigger theo mark, semantics reduce/close, partial fills, funding, liquidation và quyền key.

Cổng: tất cả quyết định nghiệp vụ có câu trả lời; hành vi API chưa xác minh được liệt kê thành test Demo.

### P1: Nền tảng bot chỉ trên Demo

Tái sử dụng adapter đọc Bitget, journal và backtest hiện có sau khi rà soát; xây client/executor an toàn, state machine zone, ledger, idempotency/clientOid, reconcile REST/WebSocket, cảnh báo và kill policy. Mọi phép tính giá/size/tiền dùng Decimal hoặc tick/lot integer.

Cổng: test được restart, reconnect, timeout sau gửi lệnh, lệnh trùng, partial fill, sửa/huỷ lệnh, nạp thủ công, vị thế ngoài bot, state unknown, kill và sai lệch ledger. Không bật live.

### P2: Policy bot và kiểm thử chiến lược

Định nghĩa chiến lược tự trade cụ thể thay vì chỉ có TA envelope. Dùng cùng logic tính toán/risk giữa backtest và bot; mô phỏng mark price, DCA-liq từng bước, phí, funding, fill/slippage và episode chưa đóng. So sánh baseline khóa trước với policy bot trên cùng điều kiện.

Cổng: báo cáo ngoài mẫu/forward test, bất định và rủi ro đuôi; không dùng cấu hình chọn trên test làm baseline độc lập.

### P3: Demo vận hành có giới hạn

Chạy số zone/symbol và mức ngân sách Demo giới hạn. Kiểm thử vòng đời đầy đủ, lệnh bảo vệ, kill, reconcile, khoảng trống kết nối, các thao tác manual. Tách Demo kỹ thuật khỏi Demo đánh giá chiến lược.

Cổng: toàn bộ kịch bản kỹ thuật đạt; không có mismatch chưa giải thích; báo cáo Demo ghi rõ phạm vi và giới hạn. Demo kỹ thuật không chứng minh lợi thế.

### P4: Thu dữ liệu và AI proposal-only

Ghi decision opportunities, hành động được duyệt/sửa/từ chối và kết quả. Xây baseline không AI; huấn luyện/đánh giá theo chia tách thời gian; chạy shadow/proposal-only, không có quyền gửi lệnh.

Cổng: AI cải thiện tiêu chí đã định so với baseline trên dữ liệu không dùng để chọn, không vi phạm hard limits; nếu không, giữ bot deterministic và tiếp tục thu dữ liệu.

### P5: AI execute có giới hạn

Chỉ sau khi P1–P4 đạt: mở một mandate nhỏ với vốn được cấp rõ ràng, policy/model ghim phiên bản, xác nhận rõ của chủ trước khi bật `AUTONOMOUS_WITHIN_MANDATE`, giới hạn tốc độ/size, giới hạn chuỗi lỗ, cooldown, kill độc lập và nhật ký audit. AI được tự mở và quản lý vị thế trong allowlist của mandate; không được tự tăng vốn hoặc policy. Mở rộng từng bước, mỗi lần có phê duyệt riêng.

### P6: Tailscale gateway

Sau khi API nội bộ và audit ổn định; quyền đọc trước, quyền thao tác hạn chế sau. Tailscale không thay thế xác thực ứng dụng.

## 6. Phạm vi không làm ở MVP

- Không tự tăng `granted_capital`, margin, leverage hoặc hard limits.
- Không tự nạp/chuyển margin.
- Không cho AI tự thay policy, model hoặc allowlist đang chạy.
- Không cho AI gọi Bitget ngoài executor và tool allowlist.
- Không khẳng định zone là ví cô lập tuyệt đối nếu chưa kiểm chứng bằng cấu hình/tài khoản Bitget.
- Không tuyên bố lỗ thực tế không thể vượt `zone_loss_limit`.
- Không dùng kết quả backtest hiện tại làm bằng chứng live nếu thiếu mark/liquidation path, fill/slippage, phí và funding phù hợp.

## 7. Quyết định cần chủ sở hữu chốt trước khi triển khai

1. Mức lỗ zone tính là `max loss` ròng từ hạn mức zone; lỗ đã thực hiện có tiếp tục ăn vào hạn mức đến hết episode không? Dự thảo đề xuất: có.
2. Khi chạm/nguy cơ vượt zone limit, hành động nào bắt buộc: huỷ entry/DCA, market close toàn bộ, hay chuyển trạng thái cảnh báo? Dự thảo đề xuất: chặn tăng rủi ro, kích hoạt lệnh bảo vệ đã duyệt; nếu không xác nhận được trạng thái/đóng an toàn thì emergency policy riêng.
3. Nonstop có cho phép không đặt SL trên sàn, hay chỉ bỏ SL chiến lược nhưng vẫn bắt buộc có giới hạn/emergency protection? Dự thảo đề xuất: có thể bỏ SL chiến lược, không bỏ hard loss control và emergency policy.
4. **Mỗi zone có target lợi nhuận riêng:** target là net trên hạn mức zone, có thể khác nhau giữa các zone, ví dụ Zone 1 = 2%, Zone 2 = 10%. `target_profit_pct` được khóa từ lúc mở zone; phải nằm trong policy/hard limits và không được dùng để nới giới hạn lỗ hoặc exposure.
5. Hai chân của cặp lệnh được đặt đồng thời. Nếu chân đóng khớp trước, ghi nhận là `reduce`; nếu chỉ một chân khớp, xử lý theo vị thế thực tế sau reconcile, không giả định chân còn lại đã khớp.
6. Bot hỗ trợ nhiều symbol, Long và Short. Với mỗi `subaccount + symbol + side` chỉ có một zone hoạt động; mỗi zone chạy isolated margin trên subaccount.
7. Khi AI qua các cổng, `AUTONOMOUS_WITHIN_MANDATE` cho phép tự mở và quản lý vị thế trong mandate hay vẫn cần xác nhận từng zone/plan? Bản dự thảo đề xuất: cho phép tự chạy trong mandate đã được người dùng bật rõ ràng; không cần xác nhận từng lệnh.

## 8. Đối chiếu với repo hiện tại

- Đã có: Python toolset; Bitget REST helper có dry-run và khóa live; read-only monitor; journal SQLite/JSONL append-oriented; TA; planner và backtest; profile/digest phong cách.
- Tái sử dụng có điều kiện: adapter/key handling sau khi review bảo mật; schema/history journal; dữ liệu style; ladder/backtest và TA sau khi tách policy khỏi dữ liệu cũ.
- Chưa có: executor/sync production; state machine zone; ledger loss-budget; idempotent order lifecycle; subaccount/margin isolation; PnL theo pair; decision-opportunity dataset; AI training/evaluation pipeline; Tailscale gateway.
- Đang lệch: `spec/SPEC.md` mô tả tool bán tự động Wide/Scalp, Cross margin, giới hạn exposure theo equity và ưu tiên BTC/ETH; không phải spec cho bot tự trade theo zone loss-budget. Không triển khai trực tiếp theo các con số cũ trước khi thay spec.
- Kết quả backtest trong `planner/PLAN.md` được chính tài liệu đánh dấu mong manh, đã chọn tham số trên tập dữ liệu thử và thiếu slippage/một số kiểm chứng. Chỉ dùng nghiên cứu/thiết kế test, không dùng làm cổng live.
