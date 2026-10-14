# Meeting Intel

Hệ thống trích xuất dữ liệu có cấu trúc từ biên bản cuộc họp (Meeting Intelligence), theo dõi diễn biến quyết định theo dòng thời gian (Decision Evolution: A → B) với cơ chế đối soát chứng cứ nguyên văn (Exact Substring Verification).

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: 16/16 Passed](https://img.shields.io/badge/tests-16%2F16%20passed-brightgreen.svg)]()
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
1. **Precision over Recall (Độ chính xác cao hơn độ phủ):** Thà hạ cấp quyết định còn nghi vấn về trạng thái `Nghiêng về` (`leaning`) để con người rà soát (Human Review), còn hơn chốt nhầm quyết định chưa ngã ngũ (`decided`) gây sai lệch trong vận hành.
2. **Tách biệt Extraction và Adjudication:** LLM chỉ đảm nhận vai trò trích xuất cấu trúc và dẫn chiếu chứng cứ thô; Deterministic Timeline Engine (Động cơ quy tắc tất định) chịu trách nhiệm xác định trạng thái quyết định cuối cùng dựa trên các điều kiện kiểm soát nghiêm ngặt.
3. **Xác thực chứng cứ nguyên văn (Exact Substring Verification):** Mọi trích dẫn làm căn cứ bắt buộc phải là chuỗi con trùng khớp tuyệt đối (exact substring) trong transcript gốc, loại bỏ triệt để ảo giác (hallucination).

---

## 2. Kiến Trúc Hệ Thống

```
[ Raw Meeting Transcript ]
       │
       ▼
[ Layer 1: Exact Substring Verification ]
  • Xác thực 100% trích dẫn là chuỗi con trùng khớp tuyệt đối (exact substring) từ transcript gốc.
  • Evidence Asymmetry: Bảo lưu tín hiệu phản đối hoặc đảo chiều quan điểm ngay cả khi trích dẫn có sai lệch định dạng nhỏ, nhằm ưu tiên hạ cấp an toàn.
       │
       ▼
[ Layer 2: Deterministic Timeline Engine ]
  • Kiểm soát 4 điều kiện tất định: Không kèm điều kiện ràng buộc, Đúng thẩm quyền (Decision Rights), Không có phản đối sau cùng, Không bị đảo ngược muộn hơn.
  • Theo dõi diễn biến theo mốc thời gian: Đề xuất A ➔ Phản đối / Đổi ý ➔ Kết luận B (Superseded Tracking).
       │
       ▼
[ Layer 3: Advisory Safety Net ]
  • Đánh giá đa chiều qua các câu hỏi hẹp: Quyết định, Phản đối, Đổi ý, Ràng buộc điều kiện, Thẩm quyền, Giao việc.
  • Hedge Language Detection: Nhận diện ngôn ngữ thăm dò, do dự để ngăn chặn việc tự động gán task khi người tham gia chỉ được nhắc tên gián tiếp.
  • Advisory Mode: Hoạt động ở chế độ cảnh báo, tự động đưa các trường hợp nghi vấn vào Hàng chờ duyệt (Review Queue) thay vì tự ý hạ cấp, hạn chế tối đa báo động giả (false alarms).
       │
       ▼
[ Layer 4: Human-in-the-Loop Review UI & Export ]
  • Bidirectional Highlighting: Liên kết hai chiều trực quan giữa kết luận và phát biểu gốc trong transcript.
  • Dynamic Decision Rights: Điều chỉnh linh hoạt ma trận thẩm quyền trực tiếp trên giao diện theo từng phiên làm việc.
  • Thao tác phê duyệt 3 trạng thái: Xác nhận (Approve), Chỉnh sửa (Edit), Bác bỏ (Reject).
  • Export Pipeline: Biên bản Markdown (.md), Danh sách công việc CSV (.csv), và JSONL kho tri thức.
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
*Ghi chú: Toàn bộ 26 cuộc họp mẫu đã có sẵn dữ liệu phản hồi trong `demo_cache/`. Bạn có thể chạy kiểm thử và trải nghiệm giao diện đầy đủ mà không bắt buộc phải có API key.*

### Bước 3: Khởi chạy Review UI
```bash
python main.py ui --port 8080 --host 127.0.0.1
```
Mở trình duyệt tại: `http://127.0.0.1:8080`

### Bước 4: Chạy Đánh giá và So sánh Benchmark (CLI)
```bash
# Đánh giá cấu hình chuẩn (Gemini + Deterministic Timeline Engine)
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
Kết quả: **16/16 tests (Integrity & Mutation Tests) vượt qua thành công.**

---

## 4. Bộ Kiểm Thử Mission 2 & Kết Quả Thực Nghiệm

### 4.1. Vị trí bộ kiểm thử trong repository

Toàn bộ dữ liệu và mã nguồn kiểm thử được tổ chức minh bạch và có thể tái lập 100%:
* **Dữ liệu kịch bản họp & Nhãn chuẩn đối soát (Ground Truth):**
  * `data/meetings/`: 20 kịch bản họp chuẩn (`m01`–`m08`, `g01`–`g12`). Mỗi thư mục bao gồm `transcript.txt` (lời thoại), `brief.yaml` (bối cảnh cuộc họp), và `expected.json` (kết quả chuẩn đối soát).
  * `data/independent_tests/meetings/`: 6 kịch bản họp kiểm thử độc lập (`indep_m01`–`indep_m06`).
  * `data/independent_tests/conditional_sentences_60.json`: Bộ 60 phát biểu kiểm thử biên điều kiện.
* **Mã nguồn kiểm thử tự động (Unit & Mutation Tests):**
  * `tests/test_integrity.py`: 12 test cases tự động kiểm tra chuỗi bằng chứng substring, 4 điều kiện chốt, thẩm quyền (người ngoài vs PM), gán việc và phân giải hạn chót.
  * `tests/test_mutations.py`: 4 test cases kiểm thử đột biến (mutation testing) đánh giá khả năng phòng thủ trước ảo giác (trích dẫn giả mạo, gài bẫy người nhận việc).
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
* **Bài học rút ra:** Deterministic Timeline Engine kết hợp Exact Substring Verification xác định chính xác mốc kết luận muộn nhất và lưu vết phương án bị thay thế (superseded), loại bỏ triệt để lỗi ghi nhận đồng thời cả hai phương án của các giải pháp tóm tắt LLM hoặc RAG thông thường.

#### Tình huống 2: Sản phẩm xử lý tốt — Ngăn chặn gán nhầm Task khi người tham gia chỉ được nhắc tên hoặc phản hồi do dự
* **Kịch bản:** `g10` (Phân công công việc sprint) & `tests/test_integrity.py::test_task_assignee_only_mentioned_is_not_assigned`
* **Diễn biến:** Hà giao việc đăng nhập cho Quân có hạn 18/11 (Quân nhận lời); Nam tự nhận viết tài liệu; Hà hỏi *"Còn phần kiểm thử tự động thì chắc Đạt làm được nhỉ"*, Đạt đáp do dự *"Để em xem đã"*.
* **Kỳ vọng:** Công việc đăng nhập gán cho Quân; tài liệu gán cho Nam; riêng phần kiểm thử tự động tuyệt đối không được tự tiện gán Đạt làm người nhận (`assignee: null`), phân loại cơ sở giao việc là `mentioned_only`.
* **Kết quả thực tế:** Công việc kiểm thử tự động được ghi nhận, nhưng trường người nhận việc để trống (`assignee: null`); hệ thống gắn cờ cảnh báo `assignee_only_mentioned` và chuyển vào Review Queue.
* **Đánh giá:** **ĐẠT.**
* **Bài học rút ra:** Cơ chế Hedge Language Detection kết hợp rà soát ngữ cảnh phát biểu kế tiếp ngăn chặn việc gán trách nhiệm công việc cho người chỉ được nhắc tên gián tiếp (mentioned only).

#### Tình huống 3: Tình huống phức tạp — Quyết định có điều kiện ràng buộc chưa thỏa mãn (Conditional Decision)
* **Kịch bản:** `m05` (Chọn cổng thanh toán Aurora) & `indep_m02`
* **Diễn biến:** Huy phát biểu: *"Ok, chốt Stripe, với điều kiện Phúc xác nhận phí giao dịch tổng cộng dưới 2%"*. Phúc đáp: *"Mình cần hỏi lại bên Stripe, chưa có số chính thức"*.
* **Kỳ vọng:** Không được tự tiện ghi nhận "Đã chốt" vì điều kiện tiên quyết về mức phí chưa được đáp ứng; hệ thống phải hạ cấp từ "Đã chốt" về "Nghiêng về" (`leaning`), trích dẫn đúng điều kiện và đưa vào Review Queue.
* **Kết quả thực tế:** `status: "leaning"`, `leaning_option: "Stripe"`, cờ cảnh báo `conditional`, trích dẫn nguyên văn *"với điều kiện Phúc xác nhận phí giao dịch tổng cộng dưới 2%"*.
* **Đánh giá:** **ĐẠT.**
* **Bài học rút ra:** Áp dụng nguyên tắc thận trọng (Precision over Recall): hạ cấp về trạng thái "Nghiêng về" (`leaning`) kèm cờ cảnh báo `conditional` để con người xác nhận, ngăn ngừa rủi ro triển khai sớm khi điều kiện tiên quyết chưa được đáp ứng.

#### Tình huống 4: Tình huống phức tạp — Kiểm soát thẩm quyền ra quyết định (Decision Rights) và Hợp lệ hóa muộn hơn
* **Kịch bản:** `g02` (Phong cách hình ảnh giao diện) & `tests/test_integrity.py::test_stranger_leaning_vs_pm_decided`
* **Diễn biến:** Trang (QA Lead) chốt *"Vậy chốt ảnh chụp thật nhé"*. Theo ma trận phân quyền `decision_rights.yaml`, nhóm design chỉ có Design Lead (Lan) hoặc Head of Product (Huy) mới có quyền chốt. Đến phát biểu kế tiếp, Lan lên tiếng: *"Ừ, mình đồng ý ảnh chụp thật"*.
* **Kỳ vọng:** Phát biểu của Trang ban đầu chưa đủ thẩm quyền (nếu chỉ có Trang thì hạ về "Nghiêng về"), nhưng quyết định được hợp lệ hóa thành "Đã chốt" ngay sau khi người có thẩm quyền (Lan) lên tiếng xác nhận.
* **Kết quả thực tế:** Trạng thái ghi nhận `status: "decided"`, `final_option: "ảnh chụp thật"`. (Ở bài test độc lập: nếu người không có thẩm quyền chốt mà không có PM xác nhận thì giữ nguyên trạng thái "Nghiêng về").
* **Đánh giá:** **ĐẠT.**
* **Bài học rút ra:** Tách riêng ma trận thẩm quyền (`decision_rights.yaml`) khỏi transcript giúp hệ thống kiểm soát chặt chẽ vai trò ra quyết định theo từng lĩnh vực, đồng thời linh hoạt công nhận quyết định khi người có thẩm quyền chuẩn thuận sau đó.

#### Tình huống 5: Tình huống chưa tối ưu — Bỏ sót công việc phụ trao đổi nhanh ở cuối buổi họp
* **Kịch bản:** `m01` (Việc xin ngân sách của Minh)
* **Diễn biến:** Ở phần cuối buổi họp `m01`, Hà nhắc việc chưa duyệt ngân sách gói Pro của Supabase, Minh nói: *"Mình sẽ nhắn anh Phúc sau, chưa biết khi nào có trả lời"*.
* **Kỳ vọng:** Hệ thống trích xuất đầy đủ cả 2 công việc (Việc dựng Supabase của Quân và Việc xin ngân sách của Minh).
* **Kết quả thực tế:** Hệ thống bóc tách trúng việc của Quân; nhưng bỏ sót việc xin ngân sách của Minh (`tasks: 1/2`, `tasks_ok: False`, khiến ca `m01` không đạt benchmark tuyệt đối).
* **Đánh giá:** **CHƯA ĐẠT** (bỏ sót đầu việc trao đổi ngắn ở cuối buổi họp).
* **Bài học rút ra:** Khi phát biểu diễn ra ở cuối phiên dưới dạng câu ngắn, thiếu chủ ngữ và không có hạn chót cụ thể, LLM dễ nhận định nhầm là giao tiếp thông thường (chitchat). Hướng khắc phục: tinh chỉnh few-shot prompt hoặc bổ sung bước quét chuyên biệt (Tail-sweep Scan) cho các phát biểu cuối transcript.

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
1. **Dữ liệu cache chuẩn bị sẵn:** Toàn bộ 707 mục phản hồi của Gemini và Jev cho cả 26 cuộc họp mẫu (`m01`–`m08`, `g01`–`g12`, `indep_m01`–`indep_m06`) đã được lưu trữ trong thư mục `demo_cache/` (dung lượng 0.31 MB) và quản lý trực tiếp trong Git repository.
2. **Kiểm tra an toàn dữ liệu:** Thư mục `demo_cache/` đã được quét tự động bằng regex chuyên dụng, **bảo đảm 100% không chứa API key, mật mã hay token riêng tư**.
3. **Cơ chế nạp ưu tiên:** Trong [src/llm.py](src/llm.py), cả hai hàm `generate_json` và `call_jev` luôn kiểm tra thư mục `demo_cache/` đầu tiên trước khi gọi ra API bên ngoài.
4. **Lợi ích khi đánh giá & kiểm thử thực tế:**
   * Người đánh giá có thể xem và phân tích lại bất kỳ cuộc họp mẫu nào trong 26 cuộc họp với tốc độ phản hồi tức thì (~50ms).
   * Hệ thống hoạt động 100% ổn định kể cả khi API key hết hạn mức (quota = 0) hoặc chưa cấu hình biến môi trường trên Render.
   * Chỉ khi người dùng tải lên transcript mới chưa từng có trong cache, hệ thống mới gọi API bên ngoài (có trần 100 lượt/ngày bảo vệ).

---

## 5. Trả Lời 3 Câu Hỏi Bắt Buộc

### Câu hỏi 1: Phần quan trọng nhất bạn chọn để hiện thực hóa trong MVP là gì? Vì sao nếu phần này hoạt động, bạn tin rằng hướng giải quyết của mình là khả thi?

* **Phần quan trọng nhất:** Tách rời hoàn toàn khâu trích xuất của LLM khỏi khâu xác định hiệu lực quyết định, sử dụng bộ kiểm chứng trích dẫn nguyên văn 100% kết hợp với động cơ quy tắc cứng theo dòng thời gian (*Exact Substring Verification + Deterministic Timeline Engine*).
* **Vì sao tin là khả thi:** 
  Trong thực tế họp hành, rủi ro nghiêm trọng nhất là ghi nhận sai quyết định (người tham gia ban đầu đề xuất Phương án A, sau đó đổi ý chốt Phương án B) hoặc gán nhầm trách nhiệm công việc cho người chỉ được nhắc tên gián tiếp. Nếu để LLM tự do tóm tắt hoặc dùng tìm kiếm tương đồng (RAG), mô hình rất dễ gặp ảo giác, coi cả ý kiến đề xuất ban đầu và kết luận mới đều là quyết định có hiệu lực.
  Bằng cách bắt buộc mọi trích dẫn chứng cứ phải khớp nguyên văn từng chữ trong biên bản gốc, sau đó để Deterministic Timeline Engine kiểm tra tuần tự 4 điều kiện: (1) Không ràng buộc điều kiện, (2) Đúng người có thẩm quyền, (3) Không có ý kiến phản đối sau cùng, (4) Không bị rút lại hoặc thay thế ở phát biểu muộn hơn, hệ thống triệt tiêu nguy cơ chốt nhầm. Thực nghiệm chứng minh hệ thống đạt 0 wrong decided trên 20 cuộc họp tập phát triển (in-sample).

### Câu hỏi 2: So với kế hoạch ở Mission 1, bạn đã thay đổi quyết định hoặc thiết kế nào? Điều gì trong quá trình làm khiến bạn thay đổi?

* **Loại bỏ mô hình Reranker bên ngoài:** Ban đầu dự kiến dùng một mô hình LLM riêng để xếp hạng lại tài liệu quy định công ty trước khi đưa vào ngữ cảnh. Tuy nhiên qua thực nghiệm, các tài liệu dự án thường ngắn gọn; việc nạp trực tiếp toàn bộ tài liệu vào bộ nhớ vừa nhanh hơn, vừa loại bỏ phụ thuộc mạng và tiết kiệm chi phí gọi API.
* **Cơ chế Evidence Asymmetry khi xử lý ý kiến phản đối:** Ban đầu nếu nhãn trích dẫn bị lệch định dạng dù chỉ một ký tự, hệ thống sẽ loại bỏ nhãn đó. Tuy nhiên, nếu loại bỏ một nhãn phản đối hoặc đảo chiều ý kiến, hệ thống có thể vô tình xác nhận một quyết định vốn đã bị bác bỏ trong thực tế. Vì vậy, hệ thống áp dụng cơ chế bất đối xứng: câu phản đối dù trích dẫn chưa chuẩn tuyệt đối vẫn được bảo lưu để hạ cấp quyết định về "Nghiêng về", tuân thủ nguyên tắc thà rà soát thêm còn hơn chốt thiếu căn cứ.
* **Chuyển bộ đánh giá an toàn sang chế độ cảnh báo (Advisory Mode):** Ban đầu dự kiến để bộ đánh giá phụ tự động hạ cấp quyết định (Downgrade Mode). Thực nghiệm cho thấy bộ đánh giá phụ có thể phân tích sai các câu đồng thuận ngắn và hạ cấp sai lệch quyết định đã đồng thuận (như ca `g12`). Chuyển sang Advisory Mode giúp hệ thống vừa bảo đảm an toàn dữ liệu, vừa tránh gây phiền hà cho người vận hành.

### Câu hỏi 3: Loại thông tin nào hệ thống hiện dễ ghi nhận sai nhất? Bạn đang làm gì để tránh tạo ra một quyết định, công việc hoặc dữ liệu không thực sự tồn tại trong cuộc họp?

* **Thông tin dễ sai nhất:** Xác định người nhận việc khi người tham gia chỉ được nhắc tên gián tiếp ("chắc Nam làm được việc này"), các phát biểu ngập ngừng do dự ("để em xem lại đã", "chắc là được"), và các đầu việc trao đổi quá vắn tắt ở những giây cuối buổi họp.
* **Giải pháp kiểm soát và phòng ngừa:**
  1. **Hedge Language Detection:** Nhận diện các câu nói ngập ngừng, thăm dò; nếu phát hiện, hệ thống không tự động gán tên người đó mà chuyển về trạng thái cần xác nhận (`assignee: null`, cờ `assignee_only_mentioned`).
  2. **Kiểm soát ma trận thẩm quyền nghiêm ngặt (Decision Rights Matrix):** Chỉ những người có vai trò phù hợp trong ma trận quyền hạn mới có thể chốt các chủ đề tương ứng (ví dụ: chỉ Tech Lead mới có quyền chốt kiến trúc kỹ thuật; thành viên thông thường kết luận sẽ tự động đưa về "Nghiêng về").
  3. **Hàng chờ duyệt (Review Queue) cho con người:** Toàn bộ các trường hợp có cờ cảnh báo nghi vấn đều được đưa vào hàng chờ duyệt trên giao diện để người chủ trì rà soát và phê duyệt với một thao tác, ngăn chặn triệt để dữ liệu sai lệch lọt vào cơ sở tri thức doanh nghiệp.

---

## 6. Bảo Mật và Bản Quyền

* **Bảo mật dữ liệu:** Hệ thống không lưu trữ API key, mã truy cập hay nội dung phát biểu nhạy cảm vào log. Bản demo trực tuyến có cơ chế xác thực bằng `ACCESS_CODE`, giới hạn tần suất yêu cầu (rate limiting) theo IP và trần số lượt chạy mỗi ngày.
* **Bản quyền:** Mã nguồn được phát hành theo giấy phép tự do [MIT License](LICENSE).
