# Meeting Intel

Hệ thống trích xuất dữ liệu có cấu trúc từ biên bản cuộc họp (Meeting Intelligence), theo dõi diễn biến quyết định theo dòng thời gian (Decision Evolution: A → B) với cơ chế đối soát chứng cứ nguyên văn (Exact Substring Verification).

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: 21/21 Passed](https://img.shields.io/badge/tests-21%2F21%20passed-brightgreen.svg)]()
[![Benchmark: 90% Pass (Dev Set)](https://img.shields.io/badge/benchmark-90%25%20(0%20critical%20errors)-success.svg)]()

---

## Demo

* **Địa chỉ truy cập:** [https://meeting-intelligent-bfca.onrender.com/](https://meeting-intelligent-bfca.onrender.com/)
* **Lưu ý khởi động:** Do sử dụng gói máy chủ miễn phí trên Render, hệ thống sẽ tự động chuyển sang chế độ ngủ (spin-down) khi không có lượt truy cập. **Lần đầu mở trang có thể mất khoảng 50–60 giây để máy chủ khởi động lại.**

---

## 1. Bài Toán và Nguyên Tắc Thiết Kế

Trong các cuộc họp điều hành và kỹ thuật:
* **Diễn biến thảo luận biến động liên tục:** Đầu phiên đề xuất Phương án A, thảo luận một hồi đổi ý sang Phương án B, hoặc quyết định đã chốt nhưng đi kèm điều kiện ràng buộc chưa được xác nhận.
* **Thách thức cốt lõi:** Xác định chính xác kết luận nào thực sự có hiệu lực thi hành, thay vì tóm tắt văn bản chung chung hoặc dùng RAG semantic search (vốn dễ coi cả đề xuất ban đầu A và kết luận đảo chiều B đều là các quyết định song song).

### Nguyên tắc cốt lõi:
1. **Độ chính xác cao hơn độ phủ:** Thà hạ cấp quyết định còn nghi vấn về trạng thái `Nghiêng về` (`leaning`) để con người rà soát, còn hơn chốt nhầm quyết định chưa ngã ngũ (`decided`) gây sai lệch trong vận hành thực tế.
2. **Tách biệt khâu đọc hiểu và khâu ra quyết định:** AI chỉ đảm nhận vai trò thư ký trích xuất câu chữ và dẫn chứng nguyên văn; toàn bộ logic phân định hiệu lực quyết định được giao cho code logic kiểm tra (xét thứ tự thời gian, quyền hạn chức danh và điều kiện đi kèm). Cách làm này triệt tiêu hoàn toàn nguy cơ AI tự ý suy diễn hoặc bịa đặt.
3. **Bắt buộc trích dẫn nguyên văn:** Mọi trích dẫn làm căn cứ bắt buộc phải là chuỗi ký tự trùng khớp từng chữ trong biên bản gốc, loại bỏ triệt để tình trạng AI tự bịa căn cứ.

---

## 2. Kiến Trúc Hệ Thống

```
[ Biên bản cuộc họp thô ]
       │
       ▼
[ Tầng 1: Kiểm tra trích dẫn nguyên văn ]
  • Đối soát 100% trích dẫn phải trùng khớp tuyệt đối từng chữ trong biên bản gốc.
  • Nguyên tắc ưu tiên an toàn: Nếu phát hiện câu phản đối hoặc đổi ý, kể cả khi trích dẫn có sai lệch nhỏ về định dạng, hệ thống vẫn giữ lại để hạ cấp an toàn về trạng thái chờ duyệt.
       │
       ▼
[ Tầng 2: Bộ quy tắc logic theo dòng thời gian ]
  • Kiểm tra tuần tự 4 điều kiện: Không kèm điều kiện treo, Đúng người có thẩm quyền, Không còn phản đối sau đó, Không bị đổi ý muộn hơn.
  • Theo dõi diễn biến theo thời gian: Đề xuất A ➔ Phản đối / Đổi ý ➔ Kết luận B (Lưu vết phương án cũ bị thay thế).
       │
       ▼
[ Tầng 3: Chốt chặn kiểm toán độc lập (Mô hình Jev) ]
  • Đánh giá đa chiều qua các câu hỏi hẹp: Quyết định, Phản đối, Đổi ý, Ràng buộc điều kiện, Thẩm quyền, Giao việc.
  • Nhận diện phát biểu do dự: Phát hiện các từ ngập ngừng, thăm dò để ngăn chặn việc tự động gán việc khi người tham gia chỉ được nhắc tên gián tiếp.
  • Chế độ cảnh báo an toàn: Đưa các trường hợp nghi vấn vào Hàng chờ duyệt thay vì tự ý hạ cấp, hạn chế tối đa báo động giả.
       │
       ▼
[ Tầng 4: Giao diện duyệt cho con người & Xuất dữ liệu ]
  • Trực quan hóa Hành trình Quyết định (Decision Journey): Minh họa lộ trình 4 giai đoạn (Đề xuất ➔ Phản biện ➔ Thay đổi ➔ Quyết định chính thức) theo mốc thời gian.
  • Đánh dấu phát biểu hai chiều: Bấm vào kết luận/bằng chứng sẽ tự động cuộn đến và làm sáng câu thoại gốc trong biên bản.
  • Phân định 3 miền dữ liệu riêng biệt: Kho tri thức dài hạn (ADR, quy chế, bài học), Bảng việc tác nghiệp (Người nhận, Hạn chót) và Vấn đề chưa chốt (Blockers/Open Questions).
  • Điều chỉnh bảng phân quyền linh hoạt: Chỉnh sửa trực tiếp quyền hạn theo chức danh ngay trên giao diện theo từng phiên họp.
  • Thao tác phê duyệt 3 trạng thái: Xác nhận (Approve), Chỉnh sửa (Edit), Bác bỏ (Reject).
  • Xuất dữ liệu đa định dạng: Biên bản Markdown (.md), Danh sách việc CSV (.csv), và file chuẩn (.jsonl) cho kho tri thức.
```

---

## 3. Hướng Dẫn Cài Đặt và Khởi Chạy

### Yêu cầu hệ thống
* Python 3.10 trở lên.
* Hệ điều hành: Windows, macOS hoặc Linux.

### Bước 1: Clone repository và cài đặt dependencies
```bash
git clone https://github.com/PhamNgocDuyPy/Meeting-Intelligent.git
cd Meeting-Intelligent
pip install -r requirements.txt
```

### Bước 2: Cấu hình môi trường (Tùy chọn)
Sao chép `.env.example` thành `.env` nếu cần phân tích transcript mới bằng Gemini API:
```bash
cp .env.example .env
```
*Ghi chú: Toàn bộ 27 cuộc họp mẫu đã có sẵn dữ liệu phản hồi trong `demo_cache/`. Bạn có thể chạy kiểm thử và trải nghiệm giao diện đầy đủ mà không bắt buộc phải có API key.*

### Bước 3: Khởi chạy Review UI
```bash
python main.py ui --port 8080 --host 127.0.0.1
```
Mở trình duyệt tại: `http://127.0.0.1:8080`

### Bước 4: Chạy Đánh giá và So sánh Benchmark (CLI)
```bash
# Đánh giá cấu hình chuẩn (Gemini + Bộ quy tắc logic theo thời gian)
python main.py eval --backend gemini --judge none

# Đánh giá cấu hình cảnh báo an toàn (Gemini + Jev Advisory)
python main.py eval --backend gemini --judge jev --judge-mode advisory

# Đánh giá với nhãn chuẩn đối soát cục bộ (Không tốn chi phí mạng/API)
python main.py eval --oracle

# So sánh kết quả chi tiết giữa 2 lần chạy
python main.py compare outputs/eval_gemini_none.json outputs/eval_gemini_jev.json
```

### Bước 5: Chạy Kiểm thử Tự động (Pytest)
```bash
pytest -v
```
Kết quả: **21/21 tests (16 Regression Tests từ Mission 2 + 5 Tests mới phát triển cho Mission 3 theo yêu cầu) vượt qua thành công (100% Passed).**

---

## 4. Bộ Kiểm Thử & Kết Quả Thực Nghiệm

### 4.1. Vị trí bộ kiểm thử trong repository

Toàn bộ dữ liệu và mã nguồn kiểm thử được tổ chức minh bạch và có thể tái lập 100%:
* **Dữ liệu kịch bản họp & Nhãn chuẩn đối soát (Ground Truth):**
  * `data/meetings/`: 21 kịch bản họp chuẩn (`m01`–`m09`, `g01`–`g12`). Mỗi thư mục bao gồm `transcript.txt` (lời thoại), `brief.yaml` (bối cảnh cuộc họp), và `expected.json` (kết quả chuẩn đối soát). Đặc biệt `m09` là kịch bản họp kỹ thuật dài (1h25) kiểm thử trọn vẹn diễn biến 3 phương án kiến trúc (A ➔ B ➔ C).
  * `data/independent_tests/meetings/`: 6 kịch bản họp kiểm thử độc lập (`indep_m01`–`indep_m06`).
  * `data/independent_tests/conditional_sentences_60.json`: Bộ 60 phát biểu kiểm thử biên điều kiện.
* **Mã nguồn kiểm thử tự động (21/21 Tests):**
  * **Nhóm 1: Bộ kiểm thử hồi quy kế thừa từ Mission 2 (Regression Testing Suite — 16 tests quan trọng đã có):**
    Thực hiện đúng yêu cầu cốt lõi của Ban tổ chức *"Chạy lại các test quan trọng của Mission 2 để kiểm tra regression"*, bảo đảm phiên bản Mission 3 kế thừa trọn vẹn toàn bộ logic nền tảng, không làm gãy bất kỳ hành vi cốt lõi nào:
    * `tests/test_integrity.py` (12 tests): Kiểm tra chuỗi bằng chứng substring bắt buộc (chống bịa đặt), 4 điều kiện chốt quyết định, ma trận phân quyền thẩm quyền (người ngoài vs PM/Tech Lead), tự nhận việc vs giao việc, và phân giải thời hạn (deadline resolution).
    * `tests/test_mutations.py` (4 tests): Kiểm thử đột biến (mutation testing) đánh giá khả năng phòng thủ trước ảo giác (trích dẫn giả mạo, phát biểu bị bóp méo, gài bẫy người nhận việc).
  * **Nhóm 2: Bộ kiểm thử mới phát triển cho Mission 3 (`tests/test_mission3.py` — 5 test cases chuyên biệt):**
    Đáp ứng toàn diện các yêu cầu cải tiến, Edge cases và Change Request C2 của Ban tổ chức:
    * **01 Test bắt buộc cho Change Request C2 (`test_change_request_c2_vague_action_no_owner_no_deadline`)**:
      Thử nghiệm trực tiếp yêu cầu *"Cuộc họp có câu 'cái này team mình xử lý nhé' nhưng không nói rõ người phụ trách hoặc deadline. Hệ thống không được tự bịa owner/deadline"*. Kiểm chứng qua 3 tình huống bẫy: (1) LLM gán đại từ tập thể ("team mình") $\rightarrow$ Bị loại bỏ thành `assignee = None`, gắn cờ `assignee_unknown`; (2) LLM gán nhầm người phát biểu (Huy) thành người tự nhận việc $\rightarrow$ Bị hạ cấp thành `assignee = None`; (3) Deadline bị bịa đặt ("sớm nhất", mốc thời gian không có trong transcript) $\rightarrow$ Bị xóa bỏ thành `deadline = None`, gắn cờ `deadline_unknown`. Đạt 100% tiêu chí đề bài.
    * **01 Test cho Edge Case phát hiện thêm (`test_edge_case_tentative_conclusion_and_opinion_inquiry`)**:
      Bắt gọn 2 tình huống khó thường gặp: (1) Sếp kết luận thử nghiệm/tạm thời (`TENTATIVE_PHRASE`: *"Trước mắt tạm thời thử nghiệm phương án B xem sao"*) $\rightarrow$ Hạ cấp về `leaning`, gắn cờ `tentative_conclusion` thay vì chốt vội; (2) Câu hỏi thăm dò quan điểm đồng nghiệp (`OPINION_INQUIRY`: *"Duy ơi bạn thấy thế nào về phương án này?"*) $\rightarrow$ Chặn gán nhầm task cho người được hỏi ý kiến.
    * **01 Test cho Lỗi Regression tiềm ẩn (`test_regression_mission2_invariants`)**:
      Kiểm chứng các bất biến cốt lõi của Mission 2 (phát biểu giao việc dứt khoát, deadline ISO cụ thể, thẩm quyền PM chốt scope) không bao giờ bị suy thoái hoặc bị xóa nhầm bởi các bộ lọc mới của Mission 3 và Change Request C2.
    * **01 Test phân tách Tác nghiệp vs Tri thức dài hạn (`test_operational_task_vs_longterm_knowledge_separation`)**:
      Kiểm chứng cơ chế bóc tách độc lập giữa Action Items ngắn hạn cho Sprint (xuất sang Jira) và Knowledge Base / ADR dài hạn (xuất sang Notion/Wiki).
    * **01 Test theo dõi diễn biến kịch bản họp dài 1h25 (`test_long_transcript_multiround_journey_evolution`)**:
      Tranh luận qua 3 phương án kiến trúc $A \rightarrow B \rightarrow C$ (Monolith $\rightarrow$ Microservices $\rightarrow$ Modular Monolith), chốt C, hủy A & B, tái hiện trọn vẹn 9 bước Decision Journey.
* **Tài liệu phân tích chuyên sâu:**
  * [docs/TEST_CASES.md](docs/TEST_CASES.md): Mô tả chi tiết các ca kiểm thử tiêu biểu đối chiếu từng câu thoại gốc và bài học rút ra.
  * [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md): Báo cáo đối soát thực nghiệm, số liệu phân tích chuyên sâu và đối chứng bộ đánh giá.

---

### 4.2. 5 Tình huống kiểm thử bắt buộc

*(Định dạng: Kỳ vọng → Kết quả thực tế → Đánh giá → Bài học rút ra)*

#### Tình huống 1: Sản phẩm xử lý tốt — Đổi ý kiến theo dòng thời gian (Decision Evolution: A → B)
* **Kịch bản:** `m01` (Kiến trúc Backend Aurora) & `tests/test_integrity.py::test_a_to_b_superseded`
* **Diễn biến:** Đầu buổi họp Minh đề xuất dùng Firebase. Sau khi Quân phân tích nhược điểm vendor lock-in và chi phí đọc dữ liệu, Minh phát biểu đổi ý: *"Ok, vậy là mình đổi ý. Chốt Supabase cho backend Aurora, bỏ Firebase"*. Hà đồng ý.
* **Kỳ vọng:** Phương án ban đầu (Firebase) phải được đánh dấu bị thay thế (`superseded`); hệ thống chỉ ghi nhận Supabase là quyết định hiện hành duy nhất; trích dẫn căn cứ phải là exact substring từ transcript gốc.
* **Kết quả thực tế:** Chủ đề đạt trạng thái "Đã chốt" với phương án Supabase; Firebase xuất hiện trong danh sách `rejected_options`; trích dẫn nguyên văn `"chốt Supabase cho backend Aurora, bỏ Firebase"` khớp 100%.
* **Đánh giá:** **ĐẠT.**
* **Bài học rút ra:** Bộ quy tắc logic theo dòng thời gian kết hợp đối soát trích dẫn nguyên văn giúp xác định chính xác mốc kết luận muộn nhất và lưu vết phương án cũ bị thay thế, loại bỏ triệt để lỗi ghi nhận đồng thời cả hai phương án của các giải pháp tóm tắt AI thông thường.

#### Tình huống 2: Sản phẩm xử lý tốt — Ngăn chặn gán nhầm Task khi người tham gia chỉ được nhắc tên hoặc phản hồi do dự
* **Kịch bản:** `g10` (Phân công công việc sprint) & `tests/test_integrity.py::test_task_assignee_only_mentioned_is_not_assigned`
* **Diễn biến:** Hà giao việc đăng nhập cho Quân có hạn 18/11 (Quân nhận lời); Nam tự nhận viết tài liệu; Hà hỏi *"Còn phần kiểm thử tự động thì chắc Đạt làm được nhỉ"*, Đạt đáp do dự *"Để em xem đã"*.
* **Kỳ vọng:** Công việc đăng nhập gán cho Quân; tài liệu gán cho Nam; riêng phần kiểm thử tự động tuyệt đối không được tự tiện gán Đạt làm người nhận (`assignee: null`), phân loại cơ sở giao việc là `mentioned_only`.
* **Kết quả thực tế:** Công việc kiểm thử tự động được ghi nhận, nhưng trường người nhận việc để trống (`assignee: null`); hệ thống gắn cờ cảnh báo `assignee_only_mentioned` và chuyển vào Review Queue.
* **Đánh giá:** **ĐẠT.**
* **Bài học rút ra:** Cơ chế nhận diện từ do dự kết hợp rà soát ngữ cảnh phát biểu kế tiếp ngăn chặn việc gán trách nhiệm công việc cho người chỉ được nhắc tên gián tiếp.

#### Tình huống 3: Tình huống phức tạp — Quyết định có điều kiện ràng buộc chưa thỏa mãn (Conditional Decision)
* **Kịch bản:** `m05` (Chọn cổng thanh toán Aurora) & `indep_m02`
* **Diễn biến:** Huy phát biểu: *"Ok, chốt Stripe, với điều kiện Phúc xác nhận phí giao dịch tổng cộng dưới 2%"*. Phúc đáp: *"Mình cần hỏi lại bên Stripe, chưa có số chính thức"*.
* **Kỳ vọng:** Không được tự tiện ghi nhận "Đã chốt" vì điều kiện tiên quyết về mức phí chưa được đáp ứng; hệ thống phải hạ cấp từ "Đã chốt" về "Nghiêng về" (`leaning`), trích dẫn đúng điều kiện và đưa vào Review Queue.
* **Kết quả thực tế:** `status: "leaning"`, `leaning_option: "Stripe"`, cờ cảnh báo `conditional`, trích dẫn nguyên văn *"với điều kiện Phúc xác nhận phí giao dịch tổng cộng dưới 2%"*.
* **Đánh giá:** **ĐẠT.**
* **Bài học rút ra:** Áp dụng nguyên tắc thận trọng (ưu tiên độ chính xác): hạ cấp về trạng thái "Nghiêng về" (`leaning`) kèm cờ cảnh báo `conditional` để con người xác nhận, ngăn ngừa rủi ro triển khai sớm khi điều kiện tiên quyết chưa được đáp ứng.

#### Tình huống 4: Tình huống phức tạp — Kiểm soát thẩm quyền ra quyết định theo quy chế và Hợp lệ hóa muộn hơn
* **Kịch bản:** `g02` (Phong cách hình ảnh giao diện) & `tests/test_integrity.py::test_stranger_leaning_vs_pm_decided`
* **Diễn biến:** Trang (QA Lead) chốt *"Vậy chốt ảnh chụp thật nhé"*. Theo bảng phân quyền công ty `decision_rights.yaml`, nhóm design chỉ có Design Lead (Lan) hoặc Head of Product (Huy) mới có quyền chốt. Đến phát biểu kế tiếp, Lan lên tiếng: *"Ừ, mình đồng ý ảnh chụp thật"*.
* **Kỳ vọng:** Phát biểu của Trang ban đầu chưa đủ thẩm quyền (nếu chỉ có Trang thì hạ về "Nghiêng về"), nhưng quyết định được hợp lệ hóa thành "Đã chốt" ngay sau khi người có thẩm quyền (Lan) lên tiếng xác nhận.
* **Kết quả thực tế:** Trạng thái ghi nhận `status: "decided"`, `final_option: "ảnh chụp thật"`. (Ở bài test độc lập: nếu người không có thẩm quyền chốt mà không có PM xác nhận thì giữ nguyên trạng thái "Nghiêng về").
* **Đánh giá:** **ĐẠT.**
* **Bài học rút ra:** Tách riêng bảng phân quyền (`decision_rights.yaml`) khỏi biên bản giúp hệ thống kiểm soát chặt chẽ vai trò ra quyết định theo từng lĩnh vực, đồng thời linh hoạt công nhận quyết định khi người có thẩm quyền chuẩn thuận sau đó.

#### Tình huống 5: Tình huống chưa tối ưu — Bỏ sót công việc phụ trao đổi nhanh ở cuối buổi họp
* **Kịch bản:** `m01` (Việc xin ngân sách của Minh)
* **Diễn biến:** Ở phần cuối buổi họp `m01`, Hà nhắc việc chưa duyệt ngân sách gói Pro của Supabase, Minh nói: *"Mình sẽ nhắn anh Phúc sau, chưa biết khi nào có trả lời"*.
* **Kỳ vọng:** Hệ thống trích xuất đầy đủ cả 2 công việc (Việc dựng Supabase của Quân và Việc xin ngân sách của Minh).
* **Kết quả thực tế:** Hệ thống bóc tách trúng việc của Quân; nhưng bỏ sót việc xin ngân sách của Minh (`tasks: 1/2`, `tasks_ok: False`, khiến ca `m01` không đạt benchmark tuyệt đối).
* **Đánh giá:** **CHƯA ĐẠT** (bỏ sót đầu việc trao đổi ngắn ở cuối buổi họp).
* **Bài học rút ra:** Khi phát biểu diễn ra ở cuối phiên dưới dạng câu ngắn, thiếu chủ ngữ và không có hạn chót cụ thể, AI dễ nhận định nhầm là trao đổi xã giao. Hướng khắc phục: bổ sung ví dụ minh họa trong prompt hoặc thiết lập bước quét rà soát chuyên biệt cho các phát biểu ở cuối biên bản.

---

### 4.3. Kết Quả Thực Nghiệm Trên Tập Phát Triển (In-Sample Dev Set)

Bảng so sánh đối chứng trên 20 cuộc họp chuẩn (`m01`–`m08`, `g01`–`g12`):

| Chỉ số đánh giá | Gemini chuẩn (`gemini+none`) *(Cấu hình chính)* | Gemini + Jev Advisory (`judge-mode advisory`) | Gemini + Jev Downgrade (`judge-mode downgrade`) | Oracle tham chiếu (`oracle+none`) |
|---|---|---|---|---|
| **Tỷ lệ đạt (Pass rate)** | **90.0%** (18/20 ca) | **90.0%** (18/20 ca) | 85.0% (17/20 ca) | **100%** (20/20 ca) |
| **Lỗi chốt nhầm (Critical Errors)** | **0** *(tập phát triển, in-sample)* | **0** | **0** | **0** |
| **Hạ cấp sai lệch (False Positive Downgrades)** | **0 ca** (0%) | **0 ca** (0%) | 1 ca (`g12`, 12.5%) | **0** |
| **Khối lượng cần duyệt bổ sung (Review Overhead)** | 0 ca | 1 ca (`g12`, 12.5%) | 0 ca | 0 |
| **Độ thu hồi việc (Task recall)** | 95% | 95% | 95% | 100% |
| **Đúng người nhận việc (Assignee accuracy)** | 95% | 95% | 95% | 100% |
| **Đúng hạn chót (Deadline accuracy)** | 95% | 95% | 95% | 100% |
| **Tự tạo thực thể giả (Hallucinated Entity)** | **0** | **0** | **0** | **0** |
| **Độ chính xác trích dẫn (Exact Substring Accuracy)** | **100%** | **100%** | **100%** | **100%** |

*Ghi chú:* Hai ca chưa đạt (`m01`, `m07`) xuất phát từ việc LLM bỏ sót việc phụ trao đổi ngắn hoặc câu hỏi mở bên lề ở cuối giờ. Trạng thái quyết định đạt 100% độ chính xác trên toàn bộ tập dữ liệu dev, hoàn toàn không có lỗi chốt nhầm.

---

### 4.4. Đánh Giá Khả Năng Khái Quát Hóa (Out-of-Sample Generalization)

Nhằm kiểm tra tính tổng quát hóa độc lập ngoài tập phát triển nội bộ:
* **Tập thử nghiệm độc lập:** Gồm 60 câu phát biểu kiểm thử điều kiện (`conditional_sentences_60.json`) và 6 cuộc họp do AI ngoài (Nemotron) sinh độc lập tại `data/independent_tests/meetings/` (`indep_m01`–`indep_m06`), đạt **1/6 (16.7%) theo bộ đối soát chuỗi tự động**.
* **Độ tin cậy và đối soát chuyên sâu:** Con số "0 critical error" được ghi nhận trên tập dev; trên tập độc lập có 1 cảnh báo, qua phân tích đối soát chuyên sâu, đây là báo động giả (false alarm) của bộ so khớp tự động (hàm `_hit()` phạt nhầm do lệch từ nối hình thức tại `indep_m04`, trong khi pipeline đã xác định chính xác nội dung theo transcript và đúng thẩm quyền của PM Viết).
* **Báo cáo chi tiết:** Phân tích đối soát từng ca và dữ liệu thực nghiệm được trình bày chi tiết tại [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md).

---

### 4.5. Cơ Chế Bộ Nhớ Đệm Demo Cache (`demo_cache/`)

Để bảo đảm quá trình đánh giá và nghiệm thu diễn ra mượt mà, không phụ thuộc vào tình trạng mạng hay giới hạn hạn mức API:
1. **Dữ liệu cache chuẩn bị sẵn:** Toàn bộ phản hồi của Gemini và Jev cho cả 27 cuộc họp mẫu (`m01`–`m09`, `g01`–`g12`, `indep_m01`–`indep_m06`) đã được lưu trữ trong thư mục `demo_cache/` (dung lượng ~0.35 MB) và quản lý trực tiếp trong Git repository.
2. **Kiểm tra an toàn dữ liệu:** Thư mục `demo_cache/` đã được quét tự động bằng regex chuyên dụng, **bảo đảm 100% không chứa API key, mật mã hay token riêng tư**.
3. **Cơ chế nạp ưu tiên:** Trong [src/llm.py](src/llm.py), cả hai hàm `generate_json` và `call_jev` luôn kiểm tra thư mục `demo_cache/` đầu tiên trước khi gọi ra API bên ngoài.
4. **Lợi ích khi đánh giá & kiểm thử thực tế:**
   * Người đánh giá có thể xem và phân tích lại bất kỳ cuộc họp mẫu nào trong 27 cuộc họp với tốc độ phản hồi tức thì (~50ms).
   * Hệ thống hoạt động 100% ổn định kể cả khi API key hết hạn mức (quota = 0) hoặc chưa cấu hình biến môi trường trên Render.
   * Chỉ khi người dùng tải lên transcript mới chưa từng có trong cache, hệ thống mới gọi API bên ngoài (có trần 100 lượt/ngày bảo vệ).

---

## 5. Bảo Mật và Bản Quyền

* **Bảo mật dữ liệu:** Hệ thống không lưu trữ API key, mã truy cập hay nội dung phát biểu nhạy cảm vào log. Bản demo trực tuyến có cơ chế xác thực bằng `ACCESS_CODE`, giới hạn tần suất yêu cầu (rate limiting) theo IP và trần số lượt chạy mỗi ngày.
* **Bản quyền:** Mã nguồn được phát hành theo giấy phép tự do [MIT License](LICENSE).
