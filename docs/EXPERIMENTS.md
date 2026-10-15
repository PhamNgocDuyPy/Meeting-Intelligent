# BÁO CÁO THỰC NGHIỆM & KẾT LUẬN
*Người thực hiện: Nhóm phát triển Meeting Intel*  
*Cam kết: Báo cáo trung thực, khoa học dựa trên kết quả chạy thực tế; đánh giá khách quan vai trò của bộ quy tắc logic bằng code, mô hình kiểm toán Jev System One và kế hoạch dữ liệu cho kho tri thức.*

> [!NOTE]
> **Bảng Kê Cấu Hình Thực Nghiệm & Môi Trường Chạy:**
> - **Mô hình trích xuất (LLM Backend):** `gemini-3.1-flash-lite` (thiết lập `temperature = 0.0`, gọi qua API Google GenAI chính thức). Tên model được xác lập trong `.env` (`GEMINI_MODEL=gemini-3.1-flash-lite`) và ghi nhận trong trường `backend` của file kết quả `outputs/*.json`. *(Ghi chú giai đoạn: Trong giai đoạn phát triển và dò lỗi ban đầu, mô hình `gemini-2.5-flash` được dùng thử nghiệm; toàn bộ số liệu báo cáo chính thức nộp bài được chạy lại và đồng bộ hoàn toàn trên `gemini-3.1-flash-lite`).*
> - **Phiên bản Prompt bóc tách:** Prompt được thiết kế chuyên biệt để bóc tách thông tin thô, đã lược bỏ hoàn toàn các ví dụ mẫu cụ thể để đảm bảo AI tự suy luận khách quan, không bị rò rỉ dữ liệu kiểm thử.
> - **Phân tách Tập Dữ liệu (Tập Viết tay m* vs Tập Sinh theo khuôn g*):**
>   * **Tập phát triển viết tay (`m01`–`m08`):** Đạt **75.0%** (6/8 ca đạt; 2 ca chưa đạt là `m01` thiếu việc phụ Minh nhắn Phúc và `m07` thiếu câu hỏi mở khảo sát biểu đồ). Đây là con số phản ánh sát thực tế năng lực ngôn ngữ của LLM nhất; việc tinh chỉnh ranh giới `scope`/`release` của `m02` cũng là tối ưu trên tập dev này.
>   * **Tập sinh theo khuôn (không độc lập) (`g01`–`g12`):** Đạt **100.0%** (12/12 ca đạt). Tập này do script tự sinh theo kịch bản để kiểm tra bảng phân quyền theo chức danh; kết quả 12/12 chứng minh bộ quy tắc logic bằng code xử lý chuẩn xác các tình huống đã định hình, chứ chưa đại diện cho khả năng hiểu ngôn ngữ tự do ngoài đời.
>   * **Tổng thể 20 cuộc họp chuẩn nội bộ:** **90.0%** (18/20 ca đạt chuẩn; 0 lỗi chốt nhầm; 0 ca hạ oan quyết định đúng).
>   * **Tập kiểm nghiệm độc lập ngoài mẫu (`indep_m01`–`indep_m06`, do AI ngoài sinh):** Đạt **1/6 (16.7%) kết quả thô tự động** (được giữ làm số liệu chính thức; đối soát thủ công chỉ mang tính phân tích kỹ thuật phụ trợ).
> - **Ngày chạy & Đồng bộ Dữ liệu:** `2026-10-14`. Mọi bảng số liệu trong báo cáo được trích xuất trực tiếp từ các file kết quả thực tế trong thư mục `outputs/*.json` và được kiểm chứng tự động qua script.

---

## 1. Bản chất Giải pháp & Trọng tâm Hiện thực hóa

### 1.1. Quy trình cốt lõi được chứng minh
Đề bài yêu cầu: Biến biên bản cuộc họp thành dữ liệu có cấu trúc phục vụ công việc và kho tri thức, đặc biệt xử lý tình huống **ý kiến ban đầu thay đổi (đầu cuộc họp đề xuất phương án A, cuối cuộc họp chốt phương án B)**.

Hệ thống hiện thực hóa quy trình này qua kiến trúc **4 tầng bảo vệ độc lập**:
1. **Tầng 1 — Bắt buộc trích dẫn nguyên văn:** Mọi trích dẫn làm căn cứ do AI bóc tách bắt buộc phải là chuỗi ký tự có thật từng chữ trong biên bản. Nếu AI bịa trích dẫn, hệ thống sẽ phát hiện và loại bỏ ngay.
2. **Tầng 2 — Bộ quy tắc logic theo dòng thời gian:** Không để AI tự phán xét quyết định, mà dùng code lập trình kiểm tra tuần tự 4 điều kiện: (1) Có kết luận rõ ràng, không kèm điều kiện treo; (2) Đúng người có quyền theo quy chế công ty; (3) Không còn ai phản đối sau đó; (4) Không bị đổi ý hoặc hủy bỏ ở phát biểu muộn hơn. Phương án A được lưu vết là phương án bị thay thế (`rejected_options`), phương án B là phương án chốt (`final_option`).
3. **Tầng 3 — Chốt chặn kiểm toán an toàn (Mô hình Jev):** Gọi mô hình Jev qua API để đánh giá độc lập các câu hỏi then chốt (kết luận, phản đối, đổi ý, điều kiện ràng buộc, thẩm quyền và giao việc). Bộ phận này hoạt động theo nguyên tắc an toàn: chỉ cảnh báo hoặc hạ cấp khi nghi ngờ, tuyệt đối không tự tiện nâng cấp quyết định.
4. **Tầng 4 — Hàng đợi rà soát cho con người:** Các mục có dấu hiệu nghi vấn được gom vào hàng đợi trên giao diện web để người điều hành duyệt trước khi xuất dữ liệu.

*Lưu ý về Cấu hình Vận hành & Cờ lệnh:*
- **Cấu hình Vận hành Chính (Primary Operational Pipeline):** `python main.py eval --backend gemini --judge none` (hoặc `python main.py run <id> --backend gemini`). Tỷ lệ đạt: **75.0%** trên tập viết tay `m*`, **100.0%** trên tập sinh theo khuôn `g*` (trung bình 20 ca là **90.0%**; 0 lỗi chốt nhầm; 0 ca hạ oan quyết định đúng). *(Ghi chú lịch sử: Trong lần chạy trước với mô hình `gemini-2.5-flash`, pass rate từng ghi nhận 85% do `m02` bị gán sai `category` sang `release`; ở lần chạy chuẩn hóa đồng bộ với `gemini-3.1-flash-lite`, `m02` đạt chuẩn và pass rate là 90.0%).*
- **Tách bạch Cờ lệnh & Chế độ Bộ chấm (`--judge-mode advisory|downgrade`):**
  - **Chế độ Tự hạ cấp (`--judge-mode downgrade`):** Bộ chấm có quyền cưỡng bức hạ `decided` về `leaning`. Số liệu: Bắt được 2/2 điều kiện bị mất nhãn (`m05`, `g06`), nhưng **hạ oan 1/8 (12.5%) quyết định đúng** (`g12`), pass rate giảm xuống 85% (17/20 ca).
  - **Chế độ Cảnh báo Khuyến nghị (`--judge-mode advisory` - Mặc định trong pipeline):** Bộ chấm không bao giờ tự ý hạ cấp, giữ nguyên các quyết định đúng; cắm cờ cảnh báo (`judge:conditional`, `judge:objection_remaining`) vào trường `flags` để đưa vào hàng đợi cho PM xác nhận. Bắt được 2/2 ca điều kiện bị mất nhãn qua cờ cảnh báo. Gánh nặng duyệt thêm cho PM là **1/8 quyết định đúng** (12.5%, ca `g12`).

---

## 2. Số liệu Thực nghiệm Thực tế & Đánh giá Khách quan về Jev

### 2.1. Thử Nghiệm Đối Chứng Toàn Diện Các Phương Án Đánh Giá (Jev vs Gemini vs Không dùng)
Toàn bộ 20 cuộc họp chuẩn (`m01–m08`, `g01–g12`) được chạy thực tế qua các cấu hình đối chứng độc lập và lưu tại thư mục `outputs/`:
1. `gemini + none` (**Cấu hình chính thức khuyến nghị**): Gemini bóc tách nội dung thô + Bộ quy tắc logic bằng code.
2. `gemini + jev` (`--judge-mode downgrade`): Gemini + Bộ quy tắc logic + Jev tự động hạ cấp quyết định.
3. `gemini + jev` (`--judge-mode advisory`): Gemini + Bộ quy tắc logic + Jev đóng vai trò cảnh báo (Lưới an toàn).
4. `gemini + gemini` (`--judge-mode downgrade`): Gemini bóc tách + Mô hình Gemini thứ hai làm người chấm phản biện có schema.
5. `oracle + none` & `oracle + jev`: Nhãn tham chiếu chuẩn + Quy tắc logic / Jev (Mức trần lý tưởng để kiểm tra bộ quy tắc).

#### Bảng Đối chứng Hiệu năng Các Bộ Chấm trên Toàn bộ 20 Cuộc họp
Trích xuất trực tiếp từ kết quả đối chứng thực nghiệm lưu tại `outputs/judge_comparison_results.json`:

| Cấu hình Thử nghiệm | Chế độ Vận hành | Tỷ lệ Đạt (Pass Rate) | Lỗi Chốt Nhầm (Critical) | Hạ Oan Quyết Định Đúng | Bắt Điều Kiện Sót (True Positive) | Nhận xét Cơ chế & Đánh đổi |
|---|---|:---:|:---:|:---:|:---:|---|
| **Gemini + Không bộ chấm** *(Baseline)* | Thuần luật | **90%** (18/20) | **0** | **0 ca** (0%) | 0/2 (Sót điều kiện nếu LLM quên gán) | Nhanh nhất, không phụ thuộc API ngoài; nếu LLM mất cờ điều kiện thì luật chốt thẳng. |
| **Gemini + Jev Judge** *(Chế độ tự hạ cấp)* | `downgrade` | 85% (17/20) | **0** | **1 ca** (12.5%, `g12`) | **2/2 ca** (`m05`, `g06`) | Bắt được 100% điều kiện bị sót; nhưng nhạy cảm với câu do dự (`g12`) gây hạ oan 1 quyết định đúng. |
| **Gemini + Jev Judge** *(Khuyến nghị)* | `advisory` | **90%** (18/20) | **0** | **0 ca** (0%) | **2/2 ca** (Cắm cờ `judge:conditional`) | **Cân bằng an toàn:** Giữ nguyên quyết định đúng; cắm cờ 1 ca (`g12`, gánh nặng duyệt 12.5%) vào Review Queue để PM duyệt. |
| **Gemini + Gemini Judge** *(LLM có schema)* | `downgrade` | **90%** (18/20) | **0** | **0 ca** (0%) | **2/2 ca** (`m05`, `g06`) | Bắt tốt điều kiện, 0 hạ oan sau khi sửa lỗi trích dẫn người nói. *(Lưu ý: Đo trong mẫu in-sample cùng tập dùng để tìm lỗi).* |
| **Gemini + Gemini Judge** *(Cảnh báo)* | `advisory` | **90%** (18/20) | **0** | **0 ca** (0%) | **2/2 ca** (Cắm cờ cảnh báo) | Đạt 90% (khớp Baseline); gắn cờ cảnh báo vào Review Queue. |

*Lưu ý giải trình số liệu bảng đối chứng:*
1. **Đã lược bỏ đo lường độ trễ trên tập 20 cuộc họp:** Thời gian chạy đo được trên tập 20 cuộc họp bị chi phối bởi cơ chế cache đĩa nội bộ (`outputs/cache/`), không phản ánh độ trễ mạng hay tốc độ suy luận API thực tế của các mô hình; để đảm bảo tính khách quan khoa học, chúng tôi không đưa cột thời gian vào bảng này.
2. **Về kết quả của Gemini Judge và phát hiện sửa lỗi `pipeline.py:67`:** Ở các lần chạy thử nghiệm trước, Gemini Judge chỉ đạt 85% do trượt tiêu chuẩn giao việc tại `m08`. Khi đó chúng tôi phỏng đoán là do Gemini quá khắt khe với phát biểu của Trang. Tuy nhiên, qua quá trình rà soát mã nguồn chuyên sâu, nhóm phát hiện nguyên nhân gốc rễ là một lỗi lập trình tại `src/pipeline.py` (dòng 67): khi ghép chuỗi trích dẫn phát biểu để kiểm tra người nhận việc (`judge_task_assignee`), hàm đã vô tình bỏ quên tên người nói (`u.text` thay vì `f"{u.speaker}: {u.text}"`). Việc thiếu ngữ cảnh người nói khiến LLM judge không xác định được ai giao việc cho ai. Sau khi phục hồi tên người nói và chuẩn hóa định nghĩa xác suất $p$, cả `m08` và `g11` đều được nhận diện chính xác, đưa tỷ lệ đạt của Gemini Judge lên **90.0%** (khớp với Baseline trong mẫu). Số liệu cũ 85% trước khi sửa bug được lưu giữ trong phụ lục để đảm bảo tính minh bạch.
3. **Giải thích sự khác biệt bề ngoài giữa 0 ca hạ oan (bảng 20 ca) và FPR 40% (bài 60 câu độc lập):** Trong 20 cuộc họp chuẩn (`m01–m08`, `g01–g12`), chỉ có 8 quyết định đã chốt và các đoạn hội thoại có thể ít câu bẫy dạng này (dù `m05` và `g06` vốn có điều kiện), do đó Gemini Judge không bị đánh lừa. Ngược lại, bài 60 câu độc lập tập trung khai thác các câu hard-negative đặc biệt khó (như bẫy điều kiện bảo hành sau khi đã chốt) và dùng prompt phân loại nhị phân riêng biệt; điều này làm bộc lộ điểm mù của Gemini khi gặp từ khóa 'nếu' trong phát biểu đời thường.
4. **Số ca hạ oan của Jev ở chế độ tự hạ:** Chính xác là **1 ca trong số 8 quyết định đúng** (1/8 = 12.5%, ca `g12` do Minh do dự *"vẫn lo nhưng sẽ làm theo"* khiến Jev chấm câu hỏi phản đối $p=0.51$, vượt ngưỡng 0.50). Ca `m06` sau khi viết lại prompt đã không còn bị hạ oan; ca `g03` giữ nguyên trạng thái `decided`.

---

### 2.2. Đánh giá Khách quan: Jev Chưa Đủ Cơ Sở Chứng Minh Lợi Ích Trong Pipeline Tự Động
Soi chiếu cam kết tại Mục 5 Proposal:
> *"Chỉ cân nhắc tích hợp Jev nếu không có lỗi chốt nhầm nghiêm trọng hơn LLM đối chứng và thời gian duyệt giảm mà không tăng lỗi giao việc."*

Phân tích số liệu thực tế chỉ ra:
1. **Không xảy ra lỗi chốt nhầm ở bất kỳ chế độ nào:** Bộ quy tắc logic kiểm tra dòng thời gian bằng code đã ngăn chặn được 100% các ca chốt nhầm trên tập thử nghiệm. Cả Jev lẫn Gemini khi tham gia phản biện đều không phát hiện thêm lỗi chốt nhầm nào.
2. **Chi phí hạ oan quyết định đúng ở chế độ tự động hạ cấp (`downgrade`):**
   - Trong toàn bộ đáp án tham chiếu (`expected.json`), có chính xác **8 quyết định đã chốt (`decided`)**: `g01`, `g02`, `g03`, `g12`, `m01`, `m02`, `m06`, `m08`.
   - Khi bật Jev ở chế độ tự động hạ cấp, ca `g12` (Minh nói *"Ok, mình vẫn lo nhưng sẽ làm theo"*) bị câu hỏi phản đối của Jev đo $p = 0.51$ và tự ý hạ về `leaning`.
   - **Tỷ lệ hạ oan quyết định đúng là 1/8 (12.5%)**. Ở chế độ cảnh báo (`advisory`), ca `g12` bị gắn cờ `judge:objection_remaining`, đồng nghĩa với việc tạo thêm **gánh nặng duyệt là 1/8 quyết định đúng (12.5%)** cho PM.
3. **So sánh Jev vs Gemini làm bộ chấm:**
   - **Về độ chính xác:** Cả Jev và Gemini đều bắt được 2/2 điều kiện bị mất nhãn. Jev có điểm nhạy cảm biên với câu do dự của `g12` (hạ oan 1/8 ở chế độ tự hạ). Gemini Judge sau khi chuẩn hóa prompt đạt 0 ca hạ oan quyết định trên 20 cuộc họp (lưu ý: kết quả đo trong mẫu in-sample).
   - **Bài học từ ca `g11` (Ranh giới giao việc đơn phương):** Trong `g11`, Hà nói: *"Minh hoàn thành phần giao diện trước thứ Sáu"*. Đây là chỉ đạo trực tiếp từ Tech Lead nhưng Minh chưa lên tiếng phản hồi. Nếu bộ chấm câu hỏi thứ 6 áp dụng tiêu chuẩn quá khắt khe (đòi hỏi phải có hội thoại hai chiều xác nhận), hệ thống sẽ gây ra false rejection (loại nhầm người nhận việc hợp lệ). Việc chuẩn hóa prompt định nghĩa rõ $p$ là xác suất được giao rõ ràng hoặc tự nhận việc đã giải quyết dứt điểm ranh giới này.
   - **Về tính chuyên dụng:** Jev System One là endpoint chuyên dụng trả về xác suất nhị phân trực tiếp (noul) với định dạng chuẩn, trong khi Gemini Judge cần prompt chỉ dẫn phức tạp để kiểm soát ngữ nghĩa xác suất và tránh suy diễn lan man.
4. **Kết luận trung thực:** **Chưa đủ cơ sở thực nghiệm để đưa Jev (hoặc Gemini Judge) vào làm bộ tự động hạ cấp trong pipeline chính. Jev chỉ phát huy giá trị khi làm lưới an toàn cảnh báo (`--judge-mode advisory`).**

---

### 2.3. Khắc phục Rò rỉ Dữ liệu Prompt & Kiểm nghiệm Ngoài Mẫu Tinh chỉnh (Out-of-sample) trên 8 Tình huống Biên (n = 4 + 4)
Để giải quyết triệt để vấn đề chất lượng và tính khách quan của bộ chấm điều kiện, chúng tôi thực hiện ba bước chuẩn hóa:

1. **Nhận diện & Khắc phục Sai sót Phương pháp luận (Prompt Data Leakage):**
   - *Vấn đề đã nhận diện:* Trong phiên bản prompt trước, chỉ dẫn câu hỏi điều kiện có chứa các cụm từ ví dụ ("bật feature flag sau khi release", "nếu được thì..."). Điều này vô tình gây rò rỉ dữ liệu kiểm thử (data leakage), khiến mô hình được mớm trước đáp án thay vì tự suy luận theo nguyên lý. Ngoài ra, ca `g12` thực chất là lỗi do câu hỏi phản đối (`objection`), không thể dùng câu hỏi điều kiện để chứng minh là đã sửa.
   - *Biện pháp khắc phục:* Trong [`src/judge.py`](../src/judge.py), chúng tôi đã loại bỏ 100% các ví dụ cụ thể khỏi prompt. Chỉ dẫn mới chỉ nêu nguyên tắc ngữ nghĩa trừu tượng: phân biệt điều kiện tiên quyết để quyết định có hiệu lực (`prerequisite condition to approve/activate`) với các hành động diễn ra sau khi quyết định đã có hiệu lực hoặc các khẩu ngữ/nguyện vọng cá nhân.

2. **Quy trình Kiểm nghiệm Ngoài Mẫu Tinh chỉnh (Out-of-Sample Test):**
   - Chúng tôi kiểm tra mô hình trên **8 câu phát biểu hoàn toàn mới do chuyên gia phản biện cung cấp** (gồm 4 ca có điều kiện thật và 4 ca không điều kiện), ghi nhận tại [`outputs/blind_conditions_8_results.json`](../outputs/blind_conditions_8_results.json) qua script [`experiments/test_blind_conditions_8.py`](../experiments/test_blind_conditions_8.py).
   - *Ghi nhận thực nghiệm trung thực:*
     * **Lần chạy đầu tiên (`task-1883.log`):** Script ban đầu chỉ đo lường trên Jev System One và đã phân loại đúng **8/8 ca** (Recall 4/4 với $p \in [0.73, 0.95]$, FPR 0/4 với $p \in [0.18, 0.23]$).
     * **Lần chạy thứ hai:** Bổ sung nhánh đối chứng Gemini LLM vào script và ghi vào JSON (Gemini cũng đạt 8/8 ca với $p \ge 0.90$ cho 4 ca có điều kiện và $p \le 0.10$ cho 4 ca không điều kiện).

#### Bảng Kết quả Đo lường trên 8 Tình huống Biên Ngoài Mẫu Tinh chỉnh (Chạy Ngày 2026-10-14)

| # | Nhóm Kiểm thử | Câu phát biểu thực tế | Bản chất ngữ nghĩa | Nhãn Ground Truth | Xác suất Jev $p$ | Xử lý Jev ($p \ge 0.40$) | Xác suất Gemini $p$ | Kết quả Đánh giá |
|---|---|---|---|---|---|---|---|---|
| **1** | **Phải cắm cờ** | *"Chốt Stripe, nhưng phải đợi pháp chế ký xong hợp đồng đã."* | Điều kiện pháp lý tiên quyết | Có điều kiện (TP) | **0.96** | Cắm cờ (`judge:conditional`) | **0.95** | **ĐẠT** (True Positive) |
| **2** | **Phải cắm cờ** | *"Ok thống nhất dùng gói Pro, miễn là Finance duyệt ngân sách trước thứ Sáu."* | Điều kiện ngân sách có hạn chót | Có điều kiện (TP) | **0.71** | Cắm cờ (`judge:conditional`) | **0.95** | **ĐẠT** (True Positive) |
| **3** | **Phải cắm cờ** | *"Quyết định giữ Supabase, trừ khi bên bảo mật không cho lưu dữ liệu ở nước ngoài."* | Điều kiện loại trừ bảo mật | Có điều kiện (TP) | **0.88** | Cắm cờ (`judge:conditional`) | **0.90** | **ĐẠT** (True Positive) |
| **4** | **Phải cắm cờ** | *"Chốt release thứ Hai, còn nếu QA tìm ra lỗi mức cao thì dời lại."* | Điều kiện chất lượng hủy bỏ | Có điều kiện (TP) | **0.77** | Cắm cờ (`judge:conditional`) | **0.90** | **ĐẠT** (True Positive) |
| **5** | **Không cắm cờ** | *"Chốt Supabase, tiện thì mình cũng chuyển luôn dữ liệu cũ sang tuần này."* | Việc phụ kết hợp, không phải điều kiện | Không điều kiện (TN) | **0.20** | Cho qua an toàn (Không cắm) | **0.05** | **ĐẠT** (True Negative) |
| **6** | **Không cắm cờ** | *"Quyết định release thứ Hai; sau release Trang sẽ bật tính năng chat dần theo tỷ lệ."* | Việc triển khai sau khi quyết định có hiệu lực | Không điều kiện (TN) | **0.17** | Cho qua an toàn (Không cắm) | **0.05** | **ĐẠT** (True Negative) |
| **7** | **Không cắm cờ** | *"Thống nhất dùng Playwright, ai rảnh thì viết thêm test cho giỏ hàng."* | Đề xuất tự nguyện, không ràng buộc | Không điều kiện (TN) | **0.20** | Cho qua an toàn (Không cắm) | **0.10** | **ĐẠT** (True Negative) |
| **8** | **Không cắm cờ** | *"Chốt gói Standard, sau này cần thì nâng cấp."* | Kế hoạch tương lai, không phải điều kiện | Không điều kiện (TN) | **0.24** | Cho qua an toàn (Không cắm) | **0.05** | **ĐẠT** (True Negative) |

3. **Phân tích Định lượng & Cảnh báo Thận trọng về Cỡ mẫu:**
   - **Độ nhạy & Tỷ lệ cắm cờ nhầm:**
     * **Recall:** 4/4 ca có điều kiện thật (cận dưới khoảng tin cậy 95% chính xác là $0.05^{1/4} \approx 47.3\%$).
     * **FPR:** 0/4 ca không điều kiện (cận trên khoảng tin cậy 95% chính xác là $1 - 0.05^{1/4} \approx 52.7\%$).
     * *(Lưu ý phương pháp luận: Quy tắc Rule of Three $3/n$ chỉ là xấp xỉ tốt khi $n \ge 30$; với $n=4$, công thức nhị thức chính xác $1 - 0.05^{1/n}$ cho cận trên tỷ lệ lỗi là ~53%. Đồng thời, Recall và FPR là hai tỷ lệ có mẫu số khác nhau nên không được gộp chung mẫu).*
   - **Biên phân tách điểm số:**
     * Trên Jev System One: Điểm thấp nhất của nhóm có điều kiện là $p = 0.71$, điểm cao nhất của nhóm không điều kiện là $p = 0.24$ ($\Delta = 0.47$).
     * Trên Gemini Judge: Điểm nhóm có điều kiện $\ge 0.90$, nhóm không điều kiện $\le 0.10$.
   - **Cảnh báo về giới hạn cỡ mẫu nhỏ ($n = 4 + 4 = 8$):** Cỡ mẫu 8 câu chỉ là bước thăm dò ban đầu. Biên phân tách $\Delta = 0.47$ là một tín hiệu gợi ý ban đầu nhưng khoảng tin cậy còn rất rộng (tỷ lệ lỗi thực tế vẫn có thể tới ~53%). Ngưỡng $p = 0.40$ do đó hoàn toàn chỉ là một **giả thuyết làm việc trong mẫu (in-sample hypothesis)**. Kiến trúc sản phẩm do đó vẫn giữ Jev ở chế độ cảnh báo (`--judge-mode advisory`), không tự động hạ cấp.

4. **Mở rộng Thẩm định Độc lập Quy mô lớn ($N = 60$ câu do NVIDIA Nemotron 120B sinh):**
   Để giải quyết triệt để cảnh báo cỡ mẫu nhỏ ($n=4$) và loại bỏ hoàn toàn nguy cơ rò rỉ prompt (evaluation leakage), chúng tôi đã sử dụng mô hình bên thứ ba (**`nvidia/nemotron-3-super-120b-a12b`**) để sinh độc lập **60 câu hội thoại doanh nghiệp tiếng Việt hoàn toàn mới** (30 câu có điều kiện: ngân sách, phê duyệt, kỹ thuật, thời gian + 30 câu không điều kiện gồm quyết định dứt khoát và hard-negatives có từ "nếu" sau khi đã chốt).
   - **Tập dữ liệu đóng băng:** Lưu tại [`data/independent_tests/conditional_sentences_60.json`](../data/independent_tests/conditional_sentences_60.json) với mã băm SHA-256 cố định: `01a9f0e541957b7470f19d1b931654ba44dcb2a3f9f7ad4852c5c68beef49c7d`.
   - **Điều kiện thực nghiệm & Khắc phục lỗi hạ tầng:**
     * Mô hình đối chứng: **`gemini-3.1-flash-lite`** (mô hình nhỏ nhất trong dòng Gemini).
     * Ngưỡng quyết định chính (Headline Threshold): Chọn cố định **`0.40`** (ngưỡng đã khai báo trước từ tập thăm dò, không tinh chỉnh sau khi thấy dữ liệu).
     * Lần chạy ban đầu ghi nhận 3 lời gọi của Gemini gặp lỗi quá tải hạ tầng `HTTP 503: Model experiencing high demand` (tại $c20, c24, u02$). Sau khi chạy lại một lần duy nhất với cơ chế exponential backoff, cả 3 câu đều nhận được kết quả HTTP 200 hoàn chỉnh (Gemini bắt đúng $c20, c24$ và cắm cờ nhầm $u02$).
   - **Bảng Kết quả Đo lường Đối đầu (Headline Threshold = 0.40, Mẫu đầy đủ 30/30 mỗi nhóm):**
     *Trích xuất từ [`outputs/independent_sentences_60_results.json`](../outputs/independent_sentences_60_results.json):*

     | Tiêu chí Thống kê ($N=60$) | Jev System One (noul) | Gemini (`gemini-3.1-flash-lite`) | Nhận xét Khoa học & Đối soát Thống kê |
     |---|:---:|:---:|---|
     | **Recall (Bắt câu có điều kiện)** | **96.7%** (29/30) | **100.0%** (30/30) | Cả hai bên đều bắt hầu hết các điều kiện tiên quyết |
     | *Khoảng tin cậy 95% Clopper-Pearson* | [82.8%, 99.9%] | [88.4%, 100.0%] | *Khoảng tin cậy trùng lặp gần như hoàn toàn* |
     | **False Positive Rate (Hạ oan)** | **10.0%** (3/30) | **40.0%** (12/30) | **Jev có 3/30 lỗi, Gemini có 12/30 lỗi dương tính giả** |
     | *Khoảng tin cậy 95% Clopper-Pearson* | [2.1%, 26.5%] | [22.7%, 59.4%] | *Khoảng tin cậy chỉ chồng lấn nhẹ ở vùng biên [22.7% - 26.5%]* |
     | **Độ đặc hiệu (Specificity)** | **90.0%** (27/30) | **60.0%** (18/30) | Jev để yên 27/30 quyết định dứt khoát |
     | **Độ chính xác tổng thể (Accuracy)** | **93.3%** (56/60) | **80.0%** (48/60) | Jev đúng 56/60 ca, Gemini đúng 48/60 ca |
     | **ROC-AUC (Toàn dải ngưỡng)** | **0.9950** | **0.9806** | Cả hai đều có khả năng xếp hạng xác suất tốt |

   - **Kiểm định Ghép cặp McNemar Chính xác (Exact Paired McNemar Test):**
     * *Trên Tỷ lệ Hạ oan (FPR trên 30 câu không điều kiện — Kết luận chính):* Cả hai cùng cho qua đúng: 17; Jev đúng - Gemini sai: 10; Gemini đúng - Jev sai: 1; Cả hai cùng sai: 2. Discordant pairs = 11 ($b=10, c=1$). Giá trị kiểm định nhị thức chính xác: **$p = 0.0117 < 0.05$**. Khẳng định: **`gemini-3.1-flash-lite` cắm cờ nhầm nhiều hơn Jev trên các câu không điều kiện một cách có ý nghĩa thống kê**.
     * *Trên Độ chính xác Tổng thể (Accuracy trên 60 câu):* Cả hai cùng đúng: 46; Jev đúng - Gemini sai: 10; Gemini đúng - Jev sai: 2; Cả hai cùng sai: 2. Discordant pairs = 12 ($b=10, c=2$). Giá trị kiểm định nhị thức chính xác: **$p = 0.0386 < 0.05$**.
   - **Bảng Quét Ngưỡng Độ nhạy (Threshold Sweep $0.30 	o 0.80$):**

     | Ngưỡng ($th$) | Jev Recall | Jev FPR (Số ca FP) | Jev Accuracy | Gemini Recall | Gemini FPR (Số ca FP) | Gemini Accuracy |
     |:---:|:---:|:---:|:---:|:---:|:---:|:---:|
     | **0.30** | 100.0% | 26.7% (8/30) | 86.7% | 100.0% | 40.0% (12/30) | 80.0% |
     | **0.40 (Headline)** | **96.7%** | **10.0% (3/30)** | **93.3%** | **100.0%** | **40.0% (12/30)** | **80.0%** |
     | **0.50** | 96.7% | 10.0% (3/30) | 93.3% | 100.0% | 40.0% (12/30) | 80.0% |
     | **0.60** | 96.7% | 6.7% (2/30) | 95.0% | 100.0% | 40.0% (12/30) | 80.0% |
     | **0.70** | 90.0% | 0.0% (0/30) | 95.0% | 100.0% | 40.0% (12/30) | 80.0% |
     | **0.80** | 80.0% | 0.0% (0/30) | 90.0% | 100.0% | 40.0% (12/30) | 80.0% |

     *(Ghi chú kỹ thuật: Ở Gemini, khi mô hình trả về `answer: False`, trường `p` thể hiện độ tin cậy của câu trả lời phủ định; xác suất gán cờ điều kiện được tính chuẩn xác bằng $1 - p$ nếu $p > 0.5$. Toàn bộ 12 ca dương tính giả của Gemini đều được mô hình gán $p \ge 0.85$, do đó FPR của Gemini bất biến trên dải ngưỡng $0.30 - 0.80$).*

   - **Rà soát Đối soát Các Ca Biên Gây Tranh Chấp (Disputed Boundary Cases):**
     * Nhóm nghiên cứu ghi nhận 0 câu trùng lặp nguyên văn và 0 cặp câu gần giống (Jaccard > 0.65).
     * Hai câu gây tranh chấp nhãn:
       1. Ca $c26$ (*"Nếu buổi họp với nhà đầu tư kết thúc trước 11h, chúng ta sẽ có thời gian chỉnh sửa slide"*): Nemotron gán nhãn có điều kiện, nhưng thực chất là việc sắp xếp thời gian sinh hoạt chuẩn bị. Jev chấm $p=0.39$. Nếu loại trừ ca này, Recall của Jev là 29/29 (100.0%). Tuy nhiên, để đảm bảo tính khách quan khoa học, **chúng tôi giữ nguyên mẫu đầy đủ 30/30 (Recall 96.7%) làm số liệu chính thức**.
       2. Ca $u27$ (*"Ban giám đốc đã đồng ý mở chi nhánh mới ở Đà Nẵng, nếu thuê không được địa điểm thích hợp, chúng ta sẽ xem xét lại khu vực"*): Nemotron gán nhãn không điều kiện (coi đây là phương án dự phòng), nhưng mệnh đề phụ hoàn toàn có thể hiểu là điều kiện ràng buộc việc mở chi nhánh. Cả Jev ($p=0.66$) và Gemini ($p=0.95$) đều cắm cờ tại ca này.
     * Lưu ý phương pháp luận: Jev là mô hình hộp đen trả về xác suất noul, không cung cấp chuỗi suy luận nội bộ; các lý giải ở đây thuần túy là quan sát đối soát của nhóm nghiên cứu.

   - **Bài học Rút ra (Lessons Learned) — Nguy cơ Cực lớn của Cỡ Mẫu Nhỏ ($n$):**
     * Ở thử nghiệm ban đầu với $n=4$, Gemini đạt $0/4$ lỗi dương tính giả (0% FPR), tạo ra cảm giác an toàn giả tạo.
     * Khi mở rộng lên $N=30$, tỷ lệ dương tính giả của `gemini-3.1-flash-lite` lộ rõ ở mức $12/30$ (40.0%). Quan sát cụ thể cho thấy ở các câu hard-negative có từ "nếu" sau khi đã chốt (ví dụ: *"Đã chốt chọn NCC An Phát, nếu có lỗi thì gọi họ bảo hành"*), Gemini luôn gán xác suất điều kiện rất cao ($p \ge 0.90$).
     * Điều này chứng minh tại sao việc thẩm định trên cỡ mẫu nhỏ ($n \le 10$) rất nguy hiểm và có thể che giấu hoàn toàn các điểm mù hệ thống.

---

### 2.5. Thực nghiệm End-to-End trên 6 Cuộc Họp Tổng Hợp Độc Lập
Để kiểm tra tính toàn vẹn của pipeline khi không có bất kỳ tinh chỉnh nào trước đó, chúng tôi đã cho chạy một lần duy nhất (one-shot raw pass) trên **6 cuộc họp tổng hợp** (`indep_m01` – `indep_m06`) do `nvidia/nemotron-3-super-120b-a12b` sinh, đã đóng băng tại [`data/independent_tests/meetings/MANIFEST.json`](../data/independent_tests/meetings/MANIFEST.json). Danh bạ nhân sự (`people.yaml`) và bảng quyền (`decision_rights.yaml`) do nhóm thiết lập và đóng băng trước khi chạy (lưu ý: tính hợp lệ về phân quyền có phần phản ánh cách cấu hình ngữ cảnh ban đầu này).

#### Bảng Đối Chiếu: Kết Quả Thô Tự Động vs Đối Soát Sau (Bởi Người Dùng, Dựa Trên Đề Xuất Của Agent)
*Trích xuất từ [`outputs/independent_meetings_e2e_results.json`](../outputs/independent_meetings_e2e_results.json):*

| Cuộc họp tổng hợp | Tình huống Nghiệp vụ | Kết quả Thô Tự động (`gemini+none`) | Đối soát sau (Bởi người dùng, dựa trên đề xuất của agent) | Bản chất Kỹ thuật & Đối soát Nghiệp vụ |
|---|---|:---:|:---:|---|
| **`indep_m01`** | Chọn DB: Đổi ý từ MongoDB $\to$ MySQL $\to$ PostgreSQL | **ĐẠT (0 lỗi)** | **ĐẠT (Hợp lý)** | Pipeline nhận diện chính xác PostgreSQL là phương án chốt, đưa MongoDB vào superseded. Cả 2 cấu hình đều pass. |
| **`indep_m02`** | Ngân sách: Chốt gói Kim cương có điều kiện BOD duyệt | **1 Bỏ sót** (Miss) | **Đúng theo định nghĩa hệ thống** *(Gold Nemotron không theo định nghĩa này)* | Lời thoại ghi rõ *"Tạm chốt... NHƯNG phải đợi BGD duyệt, nếu không duyệt thì hủy"*. Theo 4 điều kiện của hệ thống (vi phạm điều kiện 1: chốt không điều kiện), việc hạ về `leaning` là đúng định nghĩa an toàn. Gold `decided` của Nemotron là nhãn lạc quan không biết định nghĩa này. |
| **`indep_m03`** | Phân công: Giao Thắng fix bug payment vs Linh chỉ góp ý UI | **3 Bỏ sót** | **Đạt về quyết định & phân công** *(Gold bổ sung viết sau khi thấy kết quả, có nguy cơ neo)* | Nemotron đưa task fix bug và deadline vào Topics thay vì Tasks. Khi đối soát bằng gold bổ sung viết sau ([expected_adjudicated.json](file:///d:/Tri%20tue%20phong%20hop/meeting-intel/data/independent_tests/meetings/indep_m03/expected_adjudicated.json)), pipeline bóc tách đúng: Thắng nhận task fix bug payment gateway (deadline 2026-10-18), Linh KHÔNG bị gán nhầm việc code. Topics: 0 lỗi. *(Lưu ý: Gold bổ sung viết sau khi đã thấy kết quả nên có nguy cơ neo theo đầu ra).* |
| **`indep_m04`** | Thẩm quyền: Designer đề xuất bỏ onboarding, PM giữ lại | **1 Lỗi Nghiêm trọng\*** | **Đúng theo transcript** *(Báo động giả của bộ chấm)* | Transcript cho thấy Huy chỉ nói *"màn onboarding có thể bị bỏ..."* (đề xuất, không tự ý chốt). Viết (PM có quyền) khẳng định: *"Tôi quyết định giữ lại màn hình onboarding"*. Pipeline chốt: *"Giữ lại màn onboarding"*, đúng theo transcript. Nhưng bộ chấm dùng `_hit()` tìm cụm `"giữ onboarding"` (thiếu chữ "lại màn") nên phạt nhầm thành Lỗi Nghiêm trọng. |
| **`indep_m05`** | Phạm vi MVP: Cân nhắc thanh toán QR, hoãn trả góp | **2 Bỏ sót** | **Đúng theo định nghĩa hệ thống** *(Gold Nemotron là nhãn lạc quan sai)* | Việt (PM) nói: *"Vậy chúng ta có thể cân nhắc phát hành MVP..."* (đây là đề xuất, không phải kết luận). Dũng nói: *"Đồng ý, ngày 25/10 là khả thi nếu..."* (đồng ý có điều kiện). Không ai chốt dứt khoát cả. Với 4 điều kiện khắt khe của hệ thống, `leaning` là kết quả đúng; gold `decided` của Nemotron là nhãn lạc quan sai. Pipeline không bịa một quyết định khi chưa chốt. |
| **`indep_m06`** | Khẩn cấp: Rollback v1.4 tràn RAM, giao log root-cause | **2 Bỏ sót** | **Đạt về quyết định & phân công** *(Gold bổ sung viết sau khi thấy kết quả, có nguy cơ neo)* | Nemotron đưa 2 task giám sát metrics và trích xuất log vào Topics. Khi đối soát bằng gold bổ sung viết sau ([expected_adjudicated.json](file:///d:/Tri%20tue%20phong%20hop/meeting-intel/data/independent_tests/meetings/indep_m06/expected_adjudicated.json)), pipeline chốt đúng Rollback v1.3 (`decided`), phân công đúng Quang giám sát metrics và Thành trích xuất log. *(Lưu ý: Gold bổ sung viết sau khi đã thấy kết quả nên có nguy cơ neo theo đầu ra).* |

> **Tổng kết Đo lường Thô & Bài học Khoa học:**
> - **Số liệu chính thức độc lập:** **1/6 cuộc họp đạt (16.7%) theo kết quả thô tự động**, phản ánh khoảng cách thực tế giữa tập dữ liệu phát triển nội bộ và dữ liệu độc lập ngoài mẫu. Bảng đối soát thủ công bên trên chỉ đóng vai trò phân tích phụ trợ nhằm bóc tách nguyên nhân kỹ thuật, không dùng để thay thế con số đo lường thô 1/6.
> - **Chi phí của sự thận trọng & Gánh nặng duyệt cho PM:** Ở `indep_m02` và `indep_m05`, việc hạ quyết định về `leaning` là đúng định nghĩa an toàn, nhưng đồng nghĩa với việc PM vẫn phải vào Review Queue để xem xét lại. Sự thận trọng này tránh được việc chốt nhầm, nhưng tạo ra chi phí vận hành cho con người. Hướng cải tiến trong tương lai là bổ sung trạng thái `decided_conditional` (Chốt có điều kiện) để tách biệt quyết định bị treo với quyết định đang thảo luận mở.
> - **Thừa nhận thiên kiến neo (Anchoring Risk):** Hai file gold bổ sung của `indep_m03` và `indep_m06` được tạo sau khi đã quan sát lỗi schema của evaluator; dù bám sát transcript thực tế, quá trình này có nguy cơ neo theo đầu ra của pipeline (anchoring bias).
> - **Hạn chế về độ dài transcript:** 6 cuộc họp tổng hợp do Nemotron sinh ra tương đối ngắn (khoảng 15-18 phát biểu ngắn gọn), chủ yếu kiểm tra từng tình huống nghiệp vụ riêng lẻ, chưa phản ánh đầy đủ tính chất của các cuộc họp dài nhiều bên tranh luận phức tạp.



---

### 2.4. Thực nghiệm Đánh giá Reranker Toàn diện (Vị trí B trong Proposal)
Ở Proposal Mục 3 & 4, chúng tôi đã đề xuất vị trí thứ hai cho Jev: **Reranker lọc các đoạn chính sách (policy snippets) liên quan trước khi đưa vào context cho LLM**.

Để trả lời khách quan câu hỏi: *"Jev có ưu việt hơn từ khóa/BM25/LLM trong việc lọc chính sách không và có nên đưa vào pipeline không?"*, chúng tôi đã thiết lập bộ thực nghiệm chuẩn hóa gồm 4 phương pháp đối chứng, kiểm thử trên bộ nhãn ground truth, bài đo độ bền với 200 đoạn nhiễu và đo tác động pass rate end-to-end trên toàn bộ 20 cuộc họp.

#### A. Thiết lập Bộ dữ liệu Kiểm chứng (Ground Truth Relevance Benchmark)
- **Tập dữ liệu:** 8 cuộc họp viết tay (`m01`–`m08`) đối chiếu với 12 đoạn chính sách công ty (`data/company/policies/`).
- **Quy mô nhãn:** 8 cuộc họp × 12 đoạn chính sách = **96 nhãn nhị phân chuẩn (Ground Truth Relevance: 0 hoặc 1)** được thiết lập thủ công dựa trên việc đoạn chính sách có thực sự quy định các chủ đề trong chương trình họp hay không.
- **Tiêu chí gửi vào Jev System One (`call_jev_rerank`):**
  > *"Đoạn chính sách này có trực tiếp quy định hoặc liên quan đến các chủ đề trong mục đích/chương trình cuộc họp không? True nếu đoạn chính sách chứa quy tắc, quy trình hoặc phân quyền áp dụng cho ít nhất một mục trong chương trình họp. False nếu chỉ trùng từ khóa nhưng không liên quan thực chất."*

#### B. Kết quả Đối chứng 4 Phương pháp Reranker (Top-3 Selection)
Trích xuất trực tiếp từ bài đo thực nghiệm [`experiments/experiment_rerankers.py`](../experiments/experiment_rerankers.py) lưu tại `outputs/reranker_experiment_results.json`:

| Phương pháp Reranker | Recall@3 | Precision@3 | Độ trễ TB / truy vấn | Độ nhạy Thứ tự (Order Invariance) | Nhận xét Cơ chế |
|---|---|---|---|---|---|
| **Lọc Từ khóa (Keyword)** | 48.8% | 54.2% | **1.10 ms** | Đổi top-3 **3/3 lần** | Dễ hòa điểm giữa các đoạn có số từ trùng nhau; thứ tự xuất hiện quyết định top-3. |
| **BM25 Okapi (`rank_bm25`)** | 33.1% | 37.5% | **0.46 ms** | Đổi top-3 **0/3 lần** *(Luôn cố định)* | Do corpus chỉ 12 đoạn ngắn và truy vấn ngắn, BM25 bị phạt điểm độ dài và thiếu từ đồng nghĩa ("backend" không khớp "công nghệ, hạ tầng"). |
| **Gemini Reranker** | **70.0%** | **79.2%** | 1.340,30 ms | Đổi top-3 **2/3 lần** | Hiểu ngữ nghĩa tốt nhất nhưng bị ảnh hưởng bởi *position bias* khi đọc danh sách dài. |
| **Jev System One Reranker** | 69.0% | **79.2%** | 653,57 ms | Đổi top-3 **0/3 lần** *(Ổn định)* | Chấm xác suất độc lập cho từng cặp (query, doc) qua câu hỏi noul, cho xác suất float ổn định, ngang ngửa Gemini về Precision. |

*Lưu ý về Điều kiện Thí nghiệm:*
- Jev và Gemini nhận prompt có tiêu chí ngữ nghĩa gần tương đồng với định nghĩa nhãn ground truth, trong khi Keyword và BM25 thuần túy dựa trên so khớp chuỗi ký tự mà không có ngữ cảnh này.
- Mô hình Cross-encoder chuyên biệt (như BGE-Reranker hay MiniLM) chưa được thử nghiệm trong khuôn khổ MVP này do hạn chế môi trường local không có GPU.

#### C. Thực nghiệm Độ bền khi Mở rộng Quy mô & Bài đo BM25 Recall@30 khi Có Nhiễu
Chúng tôi thiết lập bài kiểm tra sức chịu tải ([`experiments/test_bm25_recall30_noise.py`](../experiments/test_bm25_recall30_noise.py)) bằng cách sinh ngẫu nhiên **200 đoạn chính sách hành chính / nhân sự / văn phòng** chứa các từ khóa mồi ("báo cáo", "tiến độ", "kỹ thuật", "hạ tầng", "chốt", "quyết định"):

| Số đoạn chính sách nhiễu | Tổng quy mô corpus | Keyword Precision@3 | BM25 Precision@3 | **BM25 Recall@30 (Vòng gửi xe)** | Đánh giá & Rủi ro Kiến trúc |
|---|---|---|---|---|---|
| **0 đoạn** *(Nguyên bản)* | 12 đoạn | 66.7% | 66.7% | **100.0%** | Không rơi tài liệu nào; BM25 đưa đủ vào bước 2. |
| **20 đoạn** | 32 đoạn | **0.0%** | 33.3% | **95.8%** | Lọc từ khóa thô sụp đổ; BM25 vẫn giữ được 95.8% tài liệu đúng. |
| **50 đoạn** | 62 đoạn | **0.0%** | 33.3% | **63.1%** | BM25 bắt đầu làm rơi 36.9% tài liệu đúng ra ngoài top-30! |
| **100 đoạn** | 112 đoạn | **0.0%** | **0.0%** | **42.7%** | Hơn một nửa tài liệu đúng bị BM25 loại bỏ trước khi tới Reranker. |
| **200 đoạn** | 212 đoạn | **0.0%** | **0.0%** | **32.1%** | **BM25 làm rơi mất 67.9% tài liệu đúng**; kiến trúc 2 bước thuần BM25 thất bại! |

*Giải trình Thống nhất Số liệu Precision@3 của BM25:*
- Ở Bảng 2.4.B, con số **Precision@3 = 37.5%** là giá trị trung bình trên toàn bộ **8 cuộc họp** (`m01`–`m08`) đối chiếu với 12 đoạn chính sách (tổng cộng 96 nhãn ground truth).
- Ở Bảng 2.4.C (khi có 0 đoạn nhiễu), con số **Precision@3 = 66.7%** là kết quả đo riêng biệt trên **truy vấn đơn lẻ của `m01`** (chọn nền tảng backend), trong đó top-3 chọn trúng 2 tài liệu liên quan (`tech_stack` và `security_data`, tức 2/3 = 66.7%).

*Kiểm nghiệm Trực tiếp Jev Reranker Quét Toàn bộ 212 Đoạn (12 đoạn gốc + 200 đoạn nhiễu):*
Để kiểm tra khả năng của Reranker ở quy mô lớn, chúng tôi đã đo lường trực tiếp Jev System One trên toàn bộ 212 đoạn chính sách (ghi nhận tại [`outputs/jev_noise_212_results.json`](../outputs/jev_noise_212_results.json) và [`outputs/jev_noise_4_meetings_results.json`](../outputs/jev_noise_4_meetings_results.json)):
1. **Trên 1 truy vấn đơn lẻ của `m01`:**
   - **Precision@3:** **100.0% (3/3)** — Cả 3 tài liệu đứng đầu đều là tài liệu chính sách liên quan chuẩn xác (`tech_stack`, `security_data`, `data_classification`), không bị lẫn đoạn nhiễu nào.
   - **Recall@10:** **100.0% (5/5)** — Toàn bộ 5 tài liệu liên quan đều nằm trong top-10.
2. **Mở rộng kiểm nghiệm trên 4 cuộc họp (`m01`, `m02`, `m05`, `m08`):**
   - **Precision@3 trung bình:** **75.0%** (trong đó `m01` đạt 100%, `m02`, `m05`, `m08` đạt 66.7%).
   - **Recall@10 trung bình:** **93.8%** (trong đó `m01`, `m02`, `m05` đạt 100%, `m08` đạt 75%).
3. **Nhận xét so sánh & Điểm nghẽn kiến trúc:**
   - Trên 4 truy vấn này, Jev giữ được P@3 75.0% và R@10 93.8% khi thêm 200 đoạn nhiễu. Hiện tại chưa có bài đo đối chứng Gemini hay Dense Retrieval trên cùng 4 truy vấn có nhiễu này để khẳng định Jev vượt trội hơn các mô hình ngôn ngữ lớn khác.
   - Tuy nhiên, trong bài đo mở rộng với BM25 (đo trên `m01`), khi thêm 200 đoạn nhiễu thì BM25 Recall@30 giảm mạnh xuống **32.1%** (làm rơi 67.9% tài liệu đúng). Điều này chỉ ra rằng trong kiến trúc 2 bước (BM25 $\to$ Reranker), điểm nghẽn nằm ở bước tìm ứng viên (candidate generation): nếu bộ lọc thô ban đầu làm rơi tài liệu thì reranker ở bước sau không thể phục hồi.

#### D. Đo lường Pass Rate End-to-End trên Toàn bộ 20 Cuộc họp
Chúng tôi đo lường tác động của Reranker đến chất lượng chốt quyết định cuối cùng ([`experiments/test_rerank_e2e_passrate.py`](../experiments/test_rerank_e2e_passrate.py)):
- **Trên Nhãn Tham chiếu (Oracle):** Cả cấu hình Lọc Từ khóa (`0.51s`) lẫn Jev Reranker (`107.43s`) đều đạt **Pass Rate 100% (20/20)**, 0 lỗi nghiêm trọng.
- **Trên Pipeline Gemini Thật (`--backend gemini`):** Cả hai cấu hình đạt **Pass Rate 90.0% (18/20)**, 0 lỗi chốt nhầm nghiêm trọng, 0 ca hạ oan quyết định đúng. 2 ca chưa đạt là `m01` (LLM bỏ sót 1 việc phụ nhỏ) và `m07` (LLM bỏ sót câu hỏi mở về biểu đồ).
- **Lý do số đo không thay đổi:** Trong kiến trúc Meeting Intel, các đoạn chính sách được đưa vào ngữ cảnh nhằm hỗ trợ AI hiểu tình huống, nhưng việc xác định quyền hạn ra quyết định được tính toán trực tiếp bằng code đối chiếu với bảng quy chế phân quyền (`decision_rights.yaml`). Do đó, sự khác biệt trong việc xếp hạng chính sách chưa làm thay đổi quyết định cuối cùng trên 20 cuộc họp hiện tại.

#### E. Kết luận Kỹ thuật & Quyết định Kiến trúc Được Điều Chỉnh
1. **Giới hạn của Bộ lọc Truyền thống:** Thí nghiệm với 200 đoạn nhiễu cho thấy lọc từ khóa và BM25 thuần rất dễ bị đánh lừa bởi các văn bản hành chính dài có chứa từ khóa mồi.
2. **Cảnh báo về Thiết kế Hai Bước:** Không thể giả định một cách đơn giản rằng *"BM25 lọc 30 ứng viên rồi đưa cho Reranker là xong"*. Khi có nhiễu từ mồi, **BM25 làm rơi mất tới 67.9% tài liệu đúng** (Recall@30 chỉ còn 32.1%). Nếu bước 1 đã loại mất tài liệu đúng thì Reranker ở bước 2 không có cơ hội phục hồi. Muốn áp dụng kiến trúc 2 bước hiệu quả, bước 1 bắt buộc phải kết hợp **Dense Retrieval (Vector Embeddings)** hoặc mở rộng kích thước cửa sổ ứng viên.
3. **Quyết định cho MVP Hiện tại:** Ở quy mô 12 đoạn chính sách (~3.500 từ), việc nạp thẳng toàn bộ các đoạn chính sách vào context (hoặc lọc từ khóa trong RAM) là giải pháp tối ưu nhất về độ trễ (1 ms so với 653 ms) và chi phí vận hành. Chúng tôi lưu trữ module Jev Reranker làm giải pháp dự phòng cho kịch bản kho tri thức mở rộng.

---

## 3. Trả lời 3 Câu hỏi Bắt buộc

### Câu hỏi 1: Phần quan trọng nhất bạn chọn để hiện thực hóa trong MVP là gì? Vì sao nếu phần này hoạt động, bạn tin rằng hướng giải quyết của mình là khả thi?
* **Phần quan trọng nhất:** **Sự kết hợp giữa Bộ quy tắc logic kiểm tra dòng thời gian và cơ chế bắt buộc trích dẫn nguyên văn từ biên bản.**
* **Lý do tin rằng khả thi:**
  1. Trong biên bản họp, sai sót nguy hiểm nhất là **nhận diện sai quyết định** (coi một đề xuất cũ đã bị bác bỏ là quyết định đang thi hành) và **giao nhầm việc** (tự tiện gán việc cho một người chỉ được nhắc tên thoáng qua).
  2. Bằng cách phân định rõ ràng nhiệm vụ: AI chỉ đóng vai trò thư ký đọc hiểu và trích xuất câu chữ; còn code logic kiểm soát chặt chẽ mốc thời gian, quyền hạn chức danh và loại bỏ hoàn toàn các trích dẫn bịa đặt.
  3. Kết quả 0 lỗi nghiêm trọng chứng minh: trên tập dữ liệu chuẩn 20 cuộc họp, hệ thống **chưa quan sát thấy lỗi chốt nhầm nào**. Tuy nhiên, theo quy tắc số ba (Rule of Three), với 0 lỗi ghi nhận trên cỡ mẫu $N=20$, cận trên khoảng tin cậy 95% của tỷ lệ lỗi thực tế vẫn vào khoảng **~15%** ($3/20 = 15\%$). Do đó, cần tiếp tục mở rộng quy mô kiểm thử trước khi khẳng định loại trừ hoàn toàn rủi ro này.

### Câu hỏi 2: So với kế hoạch ở Mission 1, bạn đã thay đổi quyết định hoặc thiết kế nào? Điều gì trong quá trình làm khiến bạn thay đổi?
* **Thay đổi 1: Không sử dụng Jev làm reranker trong pipeline chính**:
  - Nhận thấy việc gọi API bên ngoài để lọc 12 đoạn chính sách là không cần thiết so với lọc từ khóa trong RAM.
* **Thay đổi 2: Vá Lỗ hổng 7 — Xử lý bất đối xứng khi loại bỏ nhãn (Asymmetric Dropping)**:
  - Nếu nhãn bị loại là `reverse`, `oppose` hay `defer`, việc loại bỏ nhãn sẽ làm mất bằng chứng phủ định, khiến quyết định cũ vô tình **vẫn bị chốt**.
  - *Cách sửa:* Nhãn khẳng định trích dẫn sai thì loại bỏ. Nhãn phủ định nếu `utterance_id` có thật mà trích dẫn sai ➔ **vẫn giữ lại nhãn**, đánh dấu `quote_unverified=True`, kích hoạt cờ `unverified_negative_evidence` để hạ quyết định về `leaning`.
* **Thay đổi 3: Vá Lỗ hổng 8 — Kiểm tra từ do dự (Hedge Check) cho người nhận việc**:
  - Bổ sung regex `HEDGE` (`chắc`, `có lẽ`, `nhỉ`, `để xem`, `?`) và kiểm tra phản hồi trong 2 phát biểu kế tiếp (`assignment_ok`), kết hợp câu hỏi giao việc thứ 6.
* **Thay đổi 4: Tách bạch Cờ lệnh Bộ chấm và Nhận diện Dải Không chắc chắn**:
  - Trong thử nghiệm ban đầu ở chế độ cắt cứng 0.5 (`downgrade`), ca `g12` ($p=0.51$) bị hạ oan dù người tham gia đã đồng ý làm theo.
  - Chúng tôi giải quyết mâu thuẫn này bằng cách: (1) Bổ sung cờ lệnh `--judge-mode advisory|downgrade` (mặc định `advisory` trong pipeline); (2) Coi vùng xác suất $[0.40, 0.80)$ là **dải không chắc chắn (Uncertainty Band)** để chỉ cắm cờ cảnh báo đưa vào Review Queue cho con người phân xử, không tự ý hạ cấp.

### Câu hỏi 3: Loại thông tin nào hệ thống hiện dễ ghi nhận sai nhất? Bạn đang làm gì để tránh tạo ra một quyết định, công việc hoặc dữ liệu không thực sự tồn tại trong cuộc họp?
* **Loại thông tin dễ sai nhất:** **Người nhận việc (Assignee)**, **Các quyết định ngầm**, và **Nhóm quyết định (`category`) do LLM gán nhãn**.
* **Giải pháp phòng ngừa & Bằng chứng kiểm thử đột biến (Mutation Tests):**
  Chúng tôi duy trì bộ kiểm thử đột biến tự động trong `tests/test_mutations.py`:
  1. **Test đột biến Assignee (`test_mutation_hole_8_adversarial_assignee`):**
     - Cố tình ép `assignee="Đạt"` trong `g10` (Hà hỏi: *"chắc Đạt làm được nhỉ"*, Đạt: *"để em xem đã"*), và ép `assignee="Nam"` trong `m07`.
     - *Kết quả:* Bộ lọc `assignment_ok` phát hiện từ do dự và câu hỏi ➔ Tự động hạ `assignee = None`, gắn cờ `assignee_only_mentioned`. Chặn đứng việc gán nhầm trách nhiệm.
  2. **Test đột biến Trích dẫn phủ định (`test_mutation_hole_7_corrupted_negative_quote`):**
     - Trong `m01`, cố tình sửa `quote` của nhãn `reverse` (bỏ Firebase) thành một chuỗi bịa đặt.
     - *Kết quả:* Hệ thống giữ lại nhãn với `quote_unverified=True` ➔ Chủ đề bị hạ về `leaning` kèm cờ `unverified_negative_evidence`. Quyết định cũ không bị chốt lọt sổ.
  3. **Phòng ngừa sai lệch `category`:** Bổ sung ranh giới phân loại rõ ràng trong prompt của LLM (Mục 4 - Ca 5).

---

## 4. Bộ 5 Tình huống Kiểm thử Tiêu biểu (Đối chiếu Trực tiếp Transcript & Output Thật)

Tất cả trích dẫn thời gian và phát biểu dưới đây được trích xuất trực tiếp từ transcript gốc và đã được kiểm chứng khớp nguyên văn qua script tự động:

| # | Tình huống kiểm thử & Dữ liệu nguồn | Kỳ vọng tham chiếu | Kết quả thực tế (`outputs/eval_gemini_none.json`) | Đánh giá | Điều học được |
|---|---|---|---|---|---|
| **1** | **Xử lý tốt: Đổi A sang B (`m01`)**<br>*Transcript:*<br>• [00:00:20] Minh: *"Ban đầu mình đề xuất dùng Firebase."*<br>• [00:01:10] Quân: *"Mình hơi lo vendor lock-in."*<br>• [00:05:40] Minh: *"Ok, vậy là mình đổi ý. Chốt Supabase cho backend Aurora, bỏ Firebase."* | Chốt Supabase; Firebase bị thay thế (`rejected_options: ["Firebase"]`). | `status: "decided"`<br>`final_option: "Supabase"`<br>`rejected_options: ["Firebase"]` | **ĐẠT** | Theo dõi thứ tự thời gian giúp loại bỏ đề xuất cũ. Gemini bóc tách sót 1 việc nhỏ phụ (Minh nhắn anh Phúc xin ngân sách), nhưng quyết định cốt lõi đạt chuẩn. |
| **2** | **Xử lý tốt: Phân loại đủ loại việc (`g10`)**<br>*Transcript:*<br>• [00:00:48] Hà: *"Quân làm phần đăng nhập, xong trước ngày 18/11 nhé."*<br>• [00:01:30] Quân: *"Ok, mình nhận."*<br>• [00:02:11] Nam: *"Mình sẽ viết tài liệu cho phần giao diện."*<br>• [00:02:36] Hà: *"Còn phần kiểm thử tự động thì chắc Đạt làm được nhỉ."*<br>• [00:03:00] Đạt: *"Để em xem đã."* | Quân có hạn 18/11; Nam không hạn; Đạt không được gán việc. | • Việc đăng nhập: `assignee: "Quân"`, `deadline: "2026-11-18"`<br>• Tài liệu UI: `assignee: "Nam"`, `deadline: null`<br>• Kiểm thử: `assignee: null`, cờ `assignee_only_mentioned` | **ĐẠT** | Bộ lọc regex `HEDGE` và kiểm tra phản hồi người được gọi tên chặn đứng việc biến người chỉ bị nhắc tên thành người chịu trách nhiệm. |
| **3** | **Tình huống khó: Chốt có điều kiện chưa xảy ra (`m05`)**<br>*Transcript:*<br>• [00:04:00] Huy: *"Ok, chốt Stripe, với điều kiện Phúc xác nhận phí giao dịch tổng cộng dưới 2%."*<br>• [00:04:30] Phúc: *"Mình cần hỏi lại bên Stripe, chưa có số chính thức."* | Không được để `Đã chốt`; phải là `Nghiêng về` hoặc `Chưa chốt`. | `status: "leaning"`<br>`leaning_option: "Stripe"`<br>Cờ: `conditional`<br>Quote: *"với điều kiện Phúc xác nhận phí giao dịch tổng cộng dưới 2%"* | **ĐẠT** | Nhận diện cờ điều kiện giúp doanh nghiệp không triển khai non khi điều kiện tiên quyết chưa hoàn tất. |
| **4** | **Tình huống khó: Người chốt không có quyền, người có quyền xác nhận sau (`g02`)**<br>*Transcript:*<br>• [00:03:58] Trang: *"Vậy chốt ảnh chụp thật nhé."* (Trang là QA Lead, không có quyền chốt design)<br>• [00:04:18] Lan: *"Ừ, mình đồng ý ảnh chụp thật."* (Lan là Design Lead có thẩm quyền xác nhận sau) | Hợp lệ hóa quyết định sau khi có thẩm quyền xác nhận. | `status: "decided"`<br>`final_option: "ảnh chụp thật"`<br>`rejected_options: ["minh họa phẳng"]` | **ĐẠT** | Bảng phân quyền và vai trò nhân sự (`people.yaml` & `decision_rights.yaml`) giúp code tự động hợp lệ hóa quyết định khi có người có thẩm quyền xác nhận. |
| **5** | **Thất bại thực tế do LLM gán sai nhóm chủ đề (`m02`)**<br>*Transcript:*<br>• [00:02:00] Hà: *"Vậy demo cho khách mình đề xuất thứ Năm tuần sau, 15/10."*<br>• [00:03:20] Hà: *"Ok, chốt demo ngày 15/10."* | Đáp án tham chiếu: `decided` (Hà là PM có quyền chốt nhóm `scope`). | `status: "leaning"`<br>`leaning_option: "Thứ Năm 15/10"`<br>Cờ: `needs_authority_confirmation`<br>Explanation: *"Người chốt (Hà) không có quyền xác nhận cho nhóm 'release'"* | **CHƯA ĐẠT** *(Lỗi Phân loại Nhóm Chủ đề)* | **Bài học lớn:** Gemini tự ý phân loại chủ đề ngày demo vào nhóm `"release"`. Theo bảng phân quyền công ty, nhóm `release` chỉ có Head of Product (Huy) được chốt. Việc xếp nhầm nhóm chủ đề khiến code áp dụng nhầm quy chế phân quyền. Giải pháp: Nêu rõ ranh giới phân loại trong prompt và hỗ trợ sửa trực tiếp nhóm chủ đề trên giao diện web để hệ thống tự tính toán lại. |

---

## 5. Hạn chế & Rủi ro Hiện tại

1. **Dữ liệu kiểm thử do đội ngũ tự xây dựng:** 20 transcript hiện tại (gồm 8 ca viết tay `m01–m08` và 12 ca sinh theo cấu trúc `g01–g12`) nhằm kiểm tra độ phủ của luật và các trường hợp biên. Bộ dữ liệu này chưa bao quát được toàn bộ sự phức tạp của tiếng Việt đời thường (nói chen ngang, khẩu ngữ, tiếng Việt pha tiếng Anh công nghệ, âm thanh ồn hoặc lỗi nhận diện giọng nói ASR).
2. **Khả năng bao quát của LLM ở các câu hỏi mở:** Trong lần chạy thật, Gemini còn bỏ sót một số việc phụ phát sinh trong trao đổi nhanh (như việc Minh nhắn riêng anh Phúc ở `m01`, hay câu hỏi mở về format biểu đồ ở `m07`). Cần tinh chỉnh prompt bóc tách và bổ sung few-shot examples.
3. **Sự phụ thuộc vào việc phân loại nhóm chủ đề của AI:** Như ca `m02` đã chứng minh, nếu AI phân loại sai nhóm quyết định (`scope` thành `release`), code logic sẽ áp dụng nhầm quy định phân quyền, dẫn đến việc hạ cấp nhầm quyết định hợp lệ của PM.

---

## 6. Nguồn gốc Dữ liệu & Hướng dẫn Tái hiện

### 6.1. Nguồn gốc Dữ liệu Kiểm thử (Data Provenance)
Bộ dữ liệu gồm 20 cuộc họp chuẩn nằm trong thư mục `data/meetings/`:
- **8 cuộc họp viết tay (`m01` đến `m08`):** Do tác giả tự biên soạn dựa trên các kịch bản thực tế trong quản trị dự án:
  - `m01`: Đổi kiến trúc cơ sở dữ liệu từ Firebase sang Supabase (A đổi sang B).
  - `m02`: Ngày demo cho khách; PM (Hà) đề xuất và chốt ngày 15/10 cho nhóm scope. *(Ghi chú thực nghiệm: Khi chạy với LLM bóc tách, LLM gán nhầm sang nhóm release dẫn đến thất bại thẩm quyền).*
  - `m03`: Đề xuất thiết kế nhưng chưa chốt dứt khoát (đồng thuận ngầm).
  - `m04`: Quyết định vượt thẩm quyền bị từ chối; hoãn sang họp sau.
  - `m05`: Huy chốt Stripe có điều kiện phụ thuộc phí bên thứ ba (Phúc xác nhận phí Stripe dưới 2%).
  - `m06`: Huy chốt ngày release thứ Hai 19/10; tính năng thanh toán tắt bằng feature flag để test thêm.
  - `m07`: Thảo luận định dạng báo cáo cuối tháng (PDF hay Excel); tham chiếu mơ hồ; giao việc Nam không hạn.
  - `m08`: Hai chủ đề đan xen: Minh chốt AWS cho hosting; Hà hoãn công cụ monitoring Datadog sang tuần sau.
- **12 cuộc họp sinh cấu trúc (`g01` đến `g12`):** Sinh tự động từ kịch bản kiểm thử nhằm bao phủ mọi tình huống phân quyền theo chức danh (`decision_rights.yaml`), các cuộc tranh luận nhiều bên và các mốc thời hạn tương đối.
- **Đáp án tham chiếu (`expected.json`):** Được thiết lập thủ công làm ground truth để đo lường độ chính xác.

### 6.2. Mã nguồn & Hướng dẫn Tái hiện Thực tế
```bash
# 1. Chạy 12 automated unit & mutation tests (100% Pass trong 0.4s)
pytest -v tests/

# 2. Chạy đánh giá cấu hình vận hành chính thức (LLM Gemini + Luật thuần)
python main.py eval --backend gemini --judge none

# 3. Chạy cấu hình thử nghiệm phòng vệ với Jev System One (Chế độ cảnh báo)
python main.py eval --backend gemini --judge jev --judge-mode advisory
python main.py compare outputs/eval_gemini_none.json outputs/eval_gemini_jev.json

# 4. Khởi chạy Giao diện Web Tra cứu phong cách Monkeytype
python main.py ui --port 8080
# Mở trình duyệt tại: http://127.0.0.1:8080
```

---

## 7. Đã Chuẩn Bị Hợp Đồng Dữ Liệu, Hoãn Có Chủ Đích Phần Lưu Trữ Kho Tri Thức

> **Soi chiếu nguyên văn Đề bài:**  
> *"Doanh nghiệp cần một sản phẩm sử dụng AI để biến nội dung cuộc họp thành dữ liệu có cấu trúc có thể tiếp tục sử dụng cho công việc, quy trình và kho tri thức (gồm: quyết định, việc cần làm, vướng mắc, yêu cầu, phản hồi, vấn đề chưa chốt và tri thức mới)."*

Đề bài yêu cầu dữ liệu **"có thể tiếp tục sử dụng cho kho tri thức"**, không đòi hỏi phải dựng toàn bộ hạ tầng lưu trữ cồng kềnh ngay trong MVP.

### 7.1. Đánh giá Công nghệ: Tránh "Dao Mổ Trâu" Cho Dữ liệu Cuộc Họp
* **Mô hình đúng hướng: Knowledge Graph theo dòng thời gian (Temporal Knowledge Graph)**:
  - Khái niệm lưu sự kiện kèm khoảng thời gian hiệu lực (`valid_from`, `valid_to: null`) và đánh dấu bản cũ bị thay thế (`rejected_options` / `supersedes_decision_id`) thay vì xóa bỏ là cách tiếp cận chuẩn mực hiện nay (như mô hình của [Zep / Graphiti](https://arxiv.org/pdf/2501.13956.pdf)). Hệ thống Meeting Intel **đã chuẩn bị sẵn các trường dữ liệu tương thích này**, và hoãn có chủ đích phần xử lý suy luận xuyên cuộc họp sang giai đoạn sau khi có cơ chế đối chiếu người dùng.
* **Quy mô công cụ phù hợp thực tế:**
  - Một dự án công nghệ thông thường chỉ có vài chục đến vài trăm quyết định, và các mối quan hệ chỉ xoay quanh việc thay thế quyết định cũ và thuộc về dự án nào.
  - Việc đưa GraphRAG của Microsoft hoặc Neo4j vào giai đoạn này là quá mức cần thiết (overkill). Theo các bài phân tích kỹ thuật ([beri.net](https://www.beri.net/article/graphrag-vs-vector-rag-indexing-query-cost-lightrag-lazygraphrag-2026), [HackerNoon](https://hackernoon.com/when-graphrag-is-overkill-a-break-even-test-for-plain-rag-graphs-and-hybrid-search)), chi phí lập chỉ mục vector chỉ bằng khoảng 0.1% so với GraphRAG, và GraphRAG kiểu gom cụm tóm tắt cộng đồng không phù hợp với dữ liệu quyết định thay đổi liên tục. Hầu hết câu hỏi của doanh nghiệp là tra cứu điểm (*"Quyết định hiện hành của chủ đề X là gì?"*), vốn được giải quyết tối ưu bằng metadata và tìm kiếm từ khóa/vector.
* **Rủi ro lớn nhất trong thực tế:** Khó khăn lớn nhất không nằm ở việc lưu trữ, mà là việc nhận diện hai phát biểu ở hai cuộc họp cách nhau nhiều tháng có cùng một chủ đề hay không. Việc nối nhầm thực thể bằng AI sẽ tạo ra cảnh báo mâu thuẫn giả—đúng loại sai sót nguy hiểm mà chúng tôi muốn tránh.

### 7.2. Kế hoạch 3 Bước Hiện thực hóa Kho Tri thức
1. **Làm ngay trong MVP: Hợp đồng dữ liệu chuẩn hóa (Data Contract)**:
   - Hệ thống đã bổ sung hàm xuất `decisions_jsonl()` trong `src/export.py`, sinh ra file `outputs/<id>_decisions.jsonl` chuẩn hóa:
     ```json
     {
       "decision_id": "m01_T1",
       "topic_title": "Chọn nền tảng backend cho Aurora",
       "topic_ref": null,
       "category": "technical",
       "status": "decided",
       "final_option": "Supabase",
       "rejected_options": ["Firebase"],
       "supersedes_decision_id": null,
       "valid_from": "2026-10-05",
       "valid_to": null,
       "evidence_utterance_ids": ["U002", "U006", "U010"],
       "approved_by": null,
       "approved_at": null,
       "flags": [],
       "meeting_id": "m01"
     }
     ```
   - Hợp đồng này cho phép bất kỳ hệ thống SQL, Vector DB hay Graph DB nào sau này đều có thể nạp trực tiếp mà không cần sửa đổi pipeline lõi.
2. **Sau MVP: Bảng SQL kết hợp Full-Text Search**:
   - Lưu các bản ghi trên vào một bảng Postgres/SQLite có các cột `supersedes_decision_id`, `valid_from` và tìm kiếm từ khóa.
   - Khi có cuộc họp mới, hệ thống truy xuất các ứng viên cùng chủ đề từ các cuộc họp trước rồi đưa vào giao diện để **người dùng xác nhận liên kết `supersedes_decision_id`**, tuân thủ nguyên tắc *"AI tìm ứng viên, con người phân xử"*.
3. **Chỉ triển khai Đồ thị Tri thức khi có điều kiện kích hoạt cụ thể**:
   - Chỉ kích hoạt mở rộng Neo4j hoặc Graph RAG khi: (1) Độ trễ tìm kiếm trên SQL vượt ngưỡng chấp nhận được, hoặc (2) Bài đo kiểm thử thực tế cho thấy recall của tìm kiếm từ khóa/vector rơi xuống dưới 80% trên các câu hỏi truy vấn nhiều bước (multi-hop queries).
   - Việc ghi ngược vào Notion/Confluence sẽ được thực hiện cuối cùng theo cơ chế một chiều, chỉ sau khi con người đã duyệt.
