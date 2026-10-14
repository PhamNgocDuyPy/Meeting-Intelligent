# 📋 BỘ TÌNH HUỐNG KIỂM THỬ TIÊU BIỂU (TEST CASES) — MEETING INTEL

Tài liệu này tổng hợp các tình huống kiểm thử tiêu biểu đối chiếu trực tiếp giữa Transcript cuộc họp gốc, Nhãn chuẩn (Ground Truth), Kết quả thực tế từ pipeline và Bài học rút ra. Mọi trích dẫn thời gian và phát biểu đều được kiểm chứng nguyên văn từ dữ liệu gốc.

---

## 1. Bảng Tổng Hợp 6 Tình Huống Tiêu Biểu

| # | Loại tình huống | Cuộc họp & Dữ liệu nguồn | Kỳ vọng tham chiếu (Gold Standard) | Kết quả thực tế (`outputs/eval_gemini_none.json`) | Đánh giá | Điều học được |
|---|---|---|---|---|---|---|
| **1** | **Xử lý tốt: Đổi A sang B** | **`m01`**<br>• [00:00:20] Minh: *"Ban đầu mình đề xuất dùng Firebase."*<br>• [00:01:10] Quân: *"Mình hơi lo vendor lock-in."*<br>• [00:05:40] Minh: *"Ok, vậy là mình đổi ý. Chốt Supabase cho backend Aurora, bỏ Firebase."* | Chốt Supabase; Firebase bị thay thế (`rejected_options: ["Firebase"]`). | `status: "decided"`<br>`final_option: "Supabase"`<br>`rejected_options: ["Firebase"]` | **ĐẠT** (Core Loop) | Động cơ luật theo dòng thời gian bắt được mốc kết luận muộn nhất và lưu vết phương án bị thay thế, không bị đánh lừa bởi phát biểu đầu giờ. |
| **2** | **Xử lý tốt: Chặn gán nhầm người nhận việc** | **`g10`**<br>• [00:00:48] Hà: *"Quân làm phần đăng nhập, xong trước ngày 18/11 nhé."*<br>• [00:01:30] Quân: *"Ok, mình nhận."*<br>• [00:02:11] Nam: *"Mình sẽ viết tài liệu cho phần giao diện."*<br>• [00:02:36] Hà: *"Còn phần kiểm thử tự động thì chắc Đạt làm được nhỉ."*<br>• [00:03:00] Đạt: *"Để em xem đã."* | Quân có hạn 18/11; Nam không hạn; Đạt không được gán việc. | • Đăng nhập: `assignee: "Quân"`, `deadline: "2026-11-18"`<br>• Tài liệu UI: `assignee: "Nam"`, `deadline: null`<br>• Test: `assignee: null`, cờ `assignee_only_mentioned` | **ĐẠT** | Regex `HEDGE` (`chắc`, `nhỉ`, `xem đã`) kết hợp kiểm tra 2 phát biểu kế tiếp chặn đứng việc biến người chỉ bị nhắc tên thành người chịu trách nhiệm. |
| **3** | **Tình huống khó: Chốt có điều kiện chưa xảy ra** | **`m05`**<br>• [00:04:00] Huy: *"Ok, chốt Stripe, với điều kiện Phúc xác nhận phí giao dịch tổng cộng dưới 2%."*<br>• [00:04:30] Phúc: *"Mình cần hỏi lại bên Stripe, chưa có số chính thức."* | Không được để `Đã chốt`; phải là `Nghiêng về` hoặc `Chưa chốt`. | `status: "leaning"`<br>`leaning_option: "Stripe"`<br>Cờ: `conditional`<br>Quote: *"với điều kiện Phúc xác nhận phí giao dịch tổng cộng dưới 2%"* | **ĐẠT** | Bắt được cờ điều kiện tiên quyết giúp doanh nghiệp không triển khai non khi điều kiện tài chính chưa được phê duyệt. |
| **4** | **Tình huống khó: Người chốt không có quyền, người có quyền xác nhận sau** | **`g02`**<br>• [00:03:58] Trang: *"Vậy chốt ảnh chụp thật nhé."* (Trang là QA Lead, không có quyền chốt design)<br>• [00:04:18] Lan: *"Ừ, mình đồng ý ảnh chụp thật."* (Lan là Design Lead có thẩm quyền xác nhận sau) | Hợp lệ hóa quyết định sau khi có thẩm quyền xác nhận. | `status: "decided"`<br>`final_option: "ảnh chụp thật"`<br>`rejected_options: ["minh họa phẳng"]` | **ĐẠT** | Ma trận vai trò (`people.yaml` & `decision_rights.yaml`) cho phép động cơ luật hợp lệ hóa quyết định dựa trên thẩm quyền thực tế. |
| **5** | **Thất bại thực tế 1: Bỏ sót việc phụ trao đổi nhanh** | **`m01`**<br>• [00:04:10] Minh: *"Để mình nhắn riêng anh Phúc xin duyệt khoản ngân sách này."* | Bóc tách đủ 2 công việc (Việc dựng Supabase của Quân và Việc xin ngân sách của Minh). | Bóc tách trúng việc của Quân; bỏ sót việc xin ngân sách của Minh (`tasks: 1/2`, `tasks_ok: False`). | **CHƯA ĐẠT** *(Thiếu Việc Phụ)* | **Thất bại thực tế:** Các trao đổi nhanh mang tính chất "nhắn riêng / tiện thể" dễ bị LLM bỏ qua nếu prompt tập trung quá nhiều vào các kết luận chính. Cần cải thiện few-shot prompt về việc phát sinh. |
| **6** | **Thất bại thực tế 2: Bỏ sót câu hỏi khảo sát bên lề** | **`m07`**<br>• [00:03:15] Hà: *"Ai thích xuất biểu đồ dạng ảnh hay bảng số liệu thì nhắn trên kênh chung nhé."* | Ghi nhận câu hỏi mở / khảo sát ý kiến chưa chốt. | Quyết định về format báo cáo đạt chuẩn, nhưng bỏ sót câu hỏi mở về biểu đồ (`items_ok: False`). | **CHƯA ĐẠT** *(Sót Câu Hỏi Mở)* | **Thất bại thực tế:** Tỷ lệ đạt 90.0% phản ánh đúng thực tế 2 ca `m01` và `m07` bị trượt do thiếu thông tin mở rộng, dù phần quyết định cốt lõi đều đạt 100%. |
| **7** | **Xung đột định nghĩa: Gold lạc quan vs Pipeline bảo vệ an toàn** | **`indep_m05`**<br>• [09:01:18] Việt: *"Vậy chúng ta có thể cân nhắc phát hành MVP chỉ với thanh toán QR vào ngày 25/10, hoãn trả góp..."*<br>• [09:01:32] Dũng: *"Đồng ý, ngày 25/10 là khả thi nếu chúng ta tập trung hoàn thiện module QR..."* | Nemotron gán nhãn lạc quan chốt ngày 25/10 (`status: "decided"`). | `status: "leaning"` (Nghiêng về)<br>Hệ thống giữ an toàn do Việt chỉ "cân nhắc" và Dũng "khả thi nếu". | **ĐÚNG THEO TRANSCRIPT** *(Gold sai định nghĩa)* | **Phát hiện đối soát:** Việt chỉ đề xuất ("cân nhắc"), Dũng đồng ý kèm điều kiện ("khả thi nếu"), không ai chốt dứt khoát. Pipeline tuân thủ 4 điều kiện nên không bịa quyết định chốt non, dù gold tự sinh của Nemotron ghi nhãn lạc quan. |
| **8** | **Báo động giả Evaluator: Lệch chuỗi con bộ chấm cứng** | **`indep_m04`**<br>• [09:00:12] Huy: *"Theo tôi, màn hình onboarding có thể bị bỏ để tiết kiệm thời gian..."*<br>• [09:00:38] Viết: *"Huy, tôi là người có thẩm quyền cuối cùng... và tôi quyết định giữ lại màn hình onboarding."* | Giữ lại màn hình onboarding (`status: "decided"`). | Pipeline chốt: `Giữ lại màn onboarding`<br>Bộ chấm: `fo_ok = False` do thiếu chữ "lại màn" khi so khớp cụm `"giữ onboarding"`. | **FALSE ALARM** *(Lỗi Bộ Chấm)* | **Bài học đối soát:** Huy chỉ nêu đề xuất ("có thể bị bỏ..."), Viết chốt theo đúng thẩm quyền. Pipeline thực chất quyết định đúng theo transcript và đúng thẩm quyền của Viết, nhưng bộ chấm chuỗi cứng `_hit()` phạt nhầm thành Lỗi Nghiêm trọng do sai khác từ nối ngữ cảnh. |


---

## 2. Chi Tiết Từng Tình Huống

### Tình huống 1 (`m01`): Đổi ý kiến từ A sang B
- **Bối cảnh:** Họp kỹ thuật chọn nền tảng backend cho dự án Aurora.
- **Diễn biến:** Đầu họp, Minh đề xuất dùng Firebase. Quân lo ngại vendor lock-in. Sau khi thảo luận chi phí và hạ tầng, Minh tuyên bố đổi ý và chốt Supabase.
- **Xử lý của hệ thống:** Nhãn `reverse` được gắn kèm trích dẫn nguyên văn *"Ok, vậy là mình đổi ý. Chốt Supabase cho backend Aurora, bỏ Firebase"*. Động cơ luật nhận diện phương án cũ và đưa Firebase vào `rejected_options`, chốt Supabase là `final_option`.

### Tình huống 2 (`g10`): Phân loại giao việc và chặn gán nhầm
- **Bối cảnh:** Họp phân công công việc sprint.
- **Diễn biến:** Hà giao việc đăng nhập cho Quân có hạn rõ ràng; Nam tự nhận viết tài liệu không hạn; Hà hỏi Đạt *"chắc Đạt làm được nhỉ"*, Đạt trả lời do dự *"để em xem đã"*.
- **Xử lý của hệ thống:** Đạt không bị gán việc (`assignee: null`), hệ thống gắn cờ cảnh báo `assignee_only_mentioned`. Tránh được việc biến người chỉ bị hỏi thành người chịu trách nhiệm.

### Tình huống 3 (`m05`): Quyết định có điều kiện chưa xảy ra
- **Bối cảnh:** Họp chọn cổng thanh toán Aurora.
- **Diễn biến:** Huy chốt Stripe nhưng kèm điều kiện: *"với điều kiện Phúc xác nhận phí giao dịch tổng cộng dưới 2%"*. Phúc trả lời chưa có số chính thức.
- **Xử lý của hệ thống:** Nhận diện cờ `conditional`, tự động hạ trạng thái từ `decided` về `leaning`.

### Tình huống 4 (`g02`): Hợp lệ hóa thẩm quyền muộn hơn
- **Bối cảnh:** Họp thống nhất phong cách hình ảnh giao diện.
- **Diễn biến:** Trang (QA Lead) chốt *"ảnh chụp thật"*. Theo ma trận `decision_rights.yaml`, nhóm design chỉ có Design Lead (Lan) hoặc Head of Product (Huy) được chốt. Đến phát biểu kế tiếp, Lan lên tiếng đồng ý.
- **Xử lý của hệ thống:** Ban đầu gắn cờ `needs_authority_confirmation`, sau đó hợp lệ hóa thành `decided` khi phát biểu của Lan xuất hiện.

### Tình huống 5 & 6 (`m01` & `m07`): Hai thất bại thực tế của LLM
- Trong lần chạy thực tế với mô hình `gemini-3.1-flash-lite`, cả 20 cuộc họp đều **đạt 100% độ chính xác về trạng thái quyết định (0 lỗi chốt nhầm, 0 hạ oan)**.
- Hai ca bị đánh giá Chưa Đạt (`m01` và `m07`) đều xuất phát từ việc LLM bỏ sót các đầu việc phụ hoặc câu hỏi khảo sát ý kiến bên lề trong phần trao đổi nhanh cuối giờ. Đây là bài học thực nghiệm quan trọng được phản ánh minh bạch trong báo cáo.

### Tình huống 7 (`indep_m05`): Xung đột định nghĩa — Gold lạc quan của model sinh vs Hệ thống bảo vệ an toàn
- **Bối cảnh:** Họp xác định phạm vi phát hành MVP dự án Nova.
- **Diễn biến:** PM Việt nói: *"Vậy chúng ta có thể cân nhắc phát hành MVP chỉ với thanh toán QR vào ngày 25/10, hoãn trả góp sang Phase 2"*. Tech Lead Dũng phản hồi: *"Đồng ý, ngày 25/10 là khả thi nếu chúng ta tập trung hoàn thiện module QR và kiểm thử"*.
- **Xử lý của hệ thống:** Pipeline nhận diện phát biểu của Việt chỉ là đề xuất thảo luận ("cân nhắc") và phản hồi của Dũng là tán thành có điều kiện ("khả thi nếu"), không có phát biểu chốt dứt khoát không ràng buộc. Hệ thống xếp chủ đề vào trạng thái `leaning` (Nghiêng về).
- **Đánh giá nghiệp vụ (Human Adjudication):** Đáp án gold tự sinh của Nemotron vội vã đánh dấu `decided`. Tuy nhiên theo định nghĩa 4 điều kiện khắt khe của hệ thống, quyết định này chưa đủ điều kiện để chốt. Đây không phải là thất bại của pipeline mà là minh chứng cho thấy pipeline hoạt động đúng nguyên tắc: không tự ý bịa hoặc hợp thức hóa một quyết định khi những người trong cuộc họp chưa chốt dứt khoát.

### Tình huống 8 (`indep_m04`): Báo động giả của bộ chấm so khớp chuỗi (String Matching False Alarm)
- **Bối cảnh:** Họp rà soát phạm vi thiết kế màn hình Onboarding.
- **Diễn biến:** Designer Huy chỉ nêu đề xuất cá nhân: *"Theo tôi, màn hình onboarding có thể bị bỏ để tiết kiệm thời gian phát triển"*. PM Viết (người có thẩm quyền duy nhất về product scope) lập tức khẳng định: *"Huy, tôi là người có thẩm quyền cuối cùng về product scope, và tôi quyết định giữ lại màn hình onboarding"*.
- **Xử lý của hệ thống:** Extractor và Rules Engine nhận diện thẩm quyền của Viết, loại bỏ đề xuất của Huy và xuất ra quyết định chốt: `final_option = "Giữ lại màn onboarding"`, `superseded = ["Loại bỏ màn onboarding"]`.
- **Vấn đề đo lường:** Bộ chấm tự động `_hit()` trong `evaluate.py` tìm kiếm cụm từ khóa con `"giữ onboarding"` trong chuỗi `"giu lai man onboarding"`. Do thiếu chữ *"lại màn"*, hàm trả về `False` và đánh dấu nhầm thành Lỗi Nghiêm Trọng (Critical Error). Sau khi đối soát thủ công (Human Adjudication), ca này được xác nhận là Pipeline đã xử lý đúng theo transcript và đúng thẩm quyền thực tế.

