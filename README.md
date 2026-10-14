# Meeting Intel

Hệ thống trích xuất dữ liệu có cấu trúc từ biên bản cuộc họp, theo dõi diễn biến quyết định theo dòng thời gian (A sang B) và kiểm chứng 100% chuỗi con nguyên văn (Exact Substring Verification).

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: 16/16 Passed](https://img.shields.io/badge/tests-16%2F16%20passed-brightgreen.svg)]()
[![Benchmark: 90% Pass (Dev Set)](https://img.shields.io/badge/benchmark-90%25%20(0%20critical%20errors)-success.svg)]()

---

## Bản Chạy Thử (Demo Trực Tuyến)

* **Địa chỉ truy cập:** [https://meeting-intel.onrender.com](https://meeting-intel.onrender.com) *(Thay bằng URL Render thật sau khi tạo Web Service)*
* **Video demo (≤5 phút):** <link> *(Điền link video tại đây hoặc đính kèm qua form nộp bài)*
* **Lưu ý khởi động:** Do sử dụng gói máy chủ miễn phí trên Render, hệ thống sẽ tự động ngủ khi không có lượt truy cập. **Lần đầu mở trang có thể mất khoảng 1 phút để máy chủ khởi động lại.**
* **Mã truy cập (ACCESS_CODE):** Để bảo vệ hạn mức API và ngăn chặn lạm dụng, hệ thống yêu cầu mã truy cập khi phân tích transcript mới. Mã này được cung cấp riêng cho Ban Giám khảo qua form nộp bài (không ghi công khai trong README; nhập vào ô "Mã truy cập" ở góc trên thanh điều khiển web).
* **Cơ chế dự phòng ngoại tuyến:** Toàn bộ 26 cuộc họp mẫu đã có sẵn trong thư mục `demo_cache/`, cho phép kiểm tra và xem kết quả phân tích tức thì (~50ms) ngay cả khi không có kết nối API ngoài hoặc hết hạn mức quota.
* **Kế hoạch triển khai & Quản trị rủi ro:** Chi tiết về quy trình deploy và các biện pháp giảm thiểu sự cố khi chấm bài xem tại [docs/DEPLOY.md](docs/DEPLOY.md).

---

## 1. Bài Toán và Nguyên Tắc Thiết Kế

Trong các cuộc họp điều hành và kỹ thuật:
* Ý kiến thảo luận biến động liên tục: Đầu cuộc họp đề xuất phương án A, thảo luận một hồi đổi ý sang phương án B, hoặc chốt nhưng kèm điều kiện ràng buộc chưa xong.
* Thách thức cốt lõi: Xác định chính xác kết luận hiện hành nào thực sự có hiệu lực thi hành, thay vì tóm tắt văn bản chung chung hoặc dùng RAG tìm kiếm tương đồng (dễ coi cả ý kiến cũ A và kết luận mới B cùng là quyết định có hiệu lực).

### Nguyên tắc cốt lõi:
1. **Ưu tiên đúng hơn đủ:** Thà hạ một quyết định còn nghi vấn về trạng thái "Nghiêng về" để con người duyệt lại, còn hơn tự ý chốt nhầm một nội dung chưa ngã ngũ.
2. **Tách biệt trích xuất và phân xử:** LLM chỉ làm nhiệm vụ bóc tách câu chữ và trích dẫn thô; động cơ luật tất định chịu trách nhiệm cập nhật trạng thái quyết định dựa trên 4 điều kiện kiểm soát nghiêm ngặt.
3. **Kiểm chứng bằng chứng cứng:** Mọi trích dẫn làm căn cứ bắt buộc phải là chuỗi con chính xác 100% trong bản ghi lời thoại gốc.

---

## 2. Kiến Trúc Hệ Thống

```
[ Transcript thô ]
       │
       ▼
[ Tầng 1: Kiểm chứng chuỗi con (Exact Substring Verification) ]
  • Kiểm tra 100% trích dẫn xuất phát nguyên văn từ transcript gốc.
  • Bất đối xứng bằng chứng: Dấu hiệu phản đối/rút lại dù trích dẫn chưa chuẩn vẫn giữ lại để hạ cấp an toàn.
       │
       ▼
[ Tầng 2: Động cơ luật dòng thời gian (Deterministic Timeline Engine) ]
  • Áp dụng 4 điều kiện: Không điều kiện, Đúng thẩm quyền, Không phản đối, Không bị đảo ngược muộn hơn.
  • Theo dõi trình tự phát biểu: Đề xuất A ➔ Phản đối A ➔ Kết luận B.
       │
       ▼
[ Tầng 3: Lưới phòng thủ cảnh báo (Advisory Safety Net) ]
  • Bộ chấm phân tích các câu hỏi hẹp (chốt, phản đối, đảo ngược, điều kiện, thẩm quyền, giao việc).
  • Kiểm tra từ do dự (Hedge Check) ngăn chặn việc tự tiện gán việc cho người chỉ được nhắc tên.
  • Hoạt động ở chế độ cảnh báo (Advisory Mode) để đẩy vào hàng chờ duyệt, không tự động hạ oan quyết định đúng.
       │
       ▼
[ Tầng 4: Giao diện người duyệt và xuất dữ liệu (Human-in-the-Loop UI) ]
  • Tra cứu liên kết 2 chiều giữa trích dẫn quyết định và lời thoại gốc.
  • Tùy chọn vai trò người nói ngay trên giao diện theo ma trận quyền hạn (chỉ dùng cho lần chạy đó, không ghi đè file).
  • Đầy đủ 3 thao tác duyệt: Xác nhận, Chỉnh sửa, Từ chối.
  • Xuất dữ liệu: Markdown biên bản, CSV công việc, JSONL kho tri thức.
```

---

## 3. Hướng Dẫn Cài Đặt và Chạy Cục Bộ (Local)

### Yêu cầu hệ thống
* Python 3.10 trở lên.
* Hệ điều hành: Windows, macOS hoặc Linux.

### Bước 1: Sao chép kho mã nguồn và cài đặt thư viện
```bash
git clone https://github.com/PhamNgocDuyPy/Meeting-Intelligent.git
cd Meeting-Intelligent
pip install -r requirements.txt
```

### Bước 2: Cấu hình môi trường (Tùy chọn)
Sao chép `.env.example` thành `.env` nếu muốn phân tích các transcript tự do mới bằng Gemini API:
```bash
cp .env.example .env
```
*Lưu ý: 26 cuộc họp mẫu chuẩn đã có sẵn trong `demo_cache/`, bạn có thể chạy kiểm thử và xem giao diện đầy đủ mà không cần điền API key.*

### Bước 3: Khởi chạy Giao diện Web (Review UI)
```bash
python main.py ui --port 8080 --host 127.0.0.1
```
Mở trình duyệt tại: `http://127.0.0.1:8080`

### Bước 4: Chạy Đánh giá và So sánh Benchmark (CLI)
```bash
# Đánh giá cấu hình chuẩn (Gemini + Luật tất định)
python main.py eval --backend gemini --judge none

# Đánh giá cấu hình cảnh báo (Gemini + Jev Advisory)
python main.py eval --backend gemini --judge jev --judge-mode advisory

# Đánh giá với nhãn tham chiếu cục bộ (Không tốn mạng/API)
python main.py eval --oracle

# So sánh kết quả giữa 2 lần chạy
python main.py compare outputs/eval_gemini_none.json outputs/eval_gemini_jev.json
```

### Bước 5: Chạy Kiểm thử Tự động (Pytest)
```bash
pytest -v
```
Kết quả: **16/16 kiểm thử toàn vẹn và đột biến phòng thủ vượt qua thành công.**

---

## 4. Bộ Kiểm Thử Mission 2 & Kết Quả Thực Nghiệm

### 4.1. Vị trí bộ kiểm thử trong repository

Toàn bộ dữ liệu và mã nguồn kiểm thử được tổ chức minh bạch và có thể tái lập 100% trong repo:
* **Dữ liệu kịch bản họp & Nhãn chuẩn:**
  * `data/meetings/`: 20 kịch bản họp chuẩn (`m01`–`m08`, `g01`–`g12`). Mỗi thư mục bao gồm `transcript.txt` (lời thoại), `brief.yaml` (bối cảnh cuộc họp), và `expected.json` (kết quả chuẩn mặt đất).
  * `data/independent_tests/meetings/`: 6 kịch bản họp kiểm thử độc lập (`indep_m01`–`indep_m06`).
  * `data/independent_tests/conditional_sentences_60.json`: Bộ 60 câu phát biểu kiểm thử biên điều kiện.
* **Mã nguồn kiểm thử tự động (Unit & Mutation Tests):**
  * `tests/test_integrity.py`: 12 kiểm thử tự động kiểm tra chuỗi bằng chứng substring, 4 điều kiện chốt, thẩm quyền (người lạ vs PM), gán việc và phân giải hạn chót.
  * `tests/test_mutations.py`: 4 kiểm thử đột biến kiểm tra khả năng phòng thủ trước ảo giác (trích dẫn giả mạo, gài bẫy người nhận việc).
  * *Lệnh thực thi toàn bộ kiểm thử:* `pytest -v`.
* **Tài liệu phân tích chuyên sâu:**
  * [docs/TEST_CASES.md](docs/TEST_CASES.md): Bản mô tả chi tiết các ca kiểm thử tiêu biểu đối chiếu từng câu thoại gốc và bài học rút ra.
  * [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md): Báo cáo đối soát thực nghiệm, số liệu phân tích chuyên sâu và đối chứng bộ chấm.

---

### 4.2. 5 Tình huống kiểm thử bắt buộc

*(Định dạng: Kỳ vọng → Kết quả thực tế → Đạt/Chưa đạt → Điều học được)*

#### Tình huống 1: Sản phẩm làm tốt — Ý kiến ban đầu thay đổi trong cuộc họp (A sang B lật kèo)
* **Kịch bản:** `m01` (Kiến trúc Backend Aurora) & `tests/test_integrity.py::test_a_to_b_superseded`
* **Diễn biến:** Đầu buổi họp Minh đề xuất dùng Firebase. Sau khi Quân phân tích nhược điểm vendor lock-in và chi phí đọc dữ liệu, Minh phát biểu đổi ý: *"Ok, vậy là mình đổi ý. Chốt Supabase cho backend Aurora, bỏ Firebase"*. Hà đồng ý.
* **Kỳ vọng:** Phương án ban đầu (Firebase) phải được đánh dấu bị thay thế (`superseded`); hệ thống chỉ ghi nhận Supabase là quyết định hiện hành duy nhất; trích dẫn căn cứ phải là chuỗi con nguyên văn 100% từ transcript gốc.
* **Kết quả thực tế:** Chủ đề đạt trạng thái "Đã chốt" với phương án Supabase; Firebase xuất hiện trong danh sách `rejected_options`; trích dẫn nguyên văn `"chốt Supabase cho backend Aurora, bỏ Firebase"` khớp 100%.
* **Đánh giá:** **ĐẠT.**
* **Điều học được:** Động cơ luật dòng thời gian kết hợp kiểm chứng chuỗi con bắt đúng mốc kết luận muộn nhất và lưu vết phương án bị thay thế, không bị đánh lừa bởi phát biểu đề xuất đầu giờ (xóa bỏ triệt để lỗi "chốt cả 2 phương án" của các hệ thống tóm tắt LLM hoặc RAG thông thường).

#### Tình huống 2: Sản phẩm làm tốt — Chặn gán nhầm người nhận việc khi chỉ bị nhắc tên hoặc nói ngập ngừng
* **Kịch bản:** `g10` (Phân công công việc sprint) & `tests/test_integrity.py::test_task_assignee_only_mentioned_is_not_assigned`
* **Diễn biến:** Hà giao việc đăng nhập cho Quân có hạn 18/11 (Quân nhận lời); Nam tự nhận viết tài liệu; Hà hỏi *"Còn phần kiểm thử tự động thì chắc Đạt làm được nhỉ"*, Đạt đáp do dự *"Để em xem đã"*.
* **Kỳ vọng:** Công việc đăng nhập gán cho Quân; tài liệu gán cho Nam; riêng phần kiểm thử tự động tuyệt đối không được tự tiện gán Đạt làm người nhận (`assignee: null`), phân loại cơ sở giao việc là `mentioned_only`.
* **Kết quả thực tế:** Công việc kiểm thử tự động được ghi nhận, nhưng trường người nhận việc để trống (`assignee: null`); hệ thống gắn cờ cảnh báo `assignee_only_mentioned` và đẩy vào Review Queue.
* **Đánh giá:** **ĐẠT.**
* **Điều học được:** Bộ lọc từ do dự (Hedge Check) kết hợp kiểm tra 2 phát biểu kế tiếp chặn đứng việc biến người chỉ bị nhắc tên vu vơ thành người chịu trách nhiệm công việc.

#### Tình huống 3: Tình huống khó / Dữ liệu không rõ ràng — Quyết định kèm điều kiện ràng buộc chưa xảy ra
* **Kịch bản:** `m05` (Chọn cổng thanh toán Aurora) & `indep_m02`
* **Diễn biến:** Huy phát biểu: *"Ok, chốt Stripe, với điều kiện Phúc xác nhận phí giao dịch tổng cộng dưới 2%"*. Phúc đáp: *"Mình cần hỏi lại bên Stripe, chưa có số chính thức"*.
* **Kỳ vọng:** Không được tự tiện ghi nhận "Đã chốt" vì điều kiện tiên quyết về mức phí chưa đáp ứng; hệ thống phải hạ cấp từ "Đã chốt" về "Nghiêng về" (`leaning`), trích dẫn đúng điều kiện và đưa vào Review Queue.
* **Kết quả thực tế:** `status: "leaning"`, `leaning_option: "Stripe"`, cờ cảnh báo `conditional`, trích dẫn nguyên văn *"với điều kiện Phúc xác nhận phí giao dịch tổng cộng dưới 2%"*.
* **Đánh giá:** **ĐẠT.**
* **Điều học được:** Áp dụng nguyên tắc thận trọng: thà hạ về "Nghiêng về" để hỏi lại con người còn hơn tự ý chốt một quyết định chưa đủ điều kiện pháp lý, ngăn chặn rủi ro triển khai non trong doanh nghiệp.

#### Tình huống 4: Tình huống khó / Dữ liệu không rõ ràng — Kiểm tra thẩm quyền ra quyết định & Hợp lệ hóa muộn hơn
* **Kịch bản:** `g02` (Phong cách hình ảnh giao diện) & `tests/test_integrity.py::test_stranger_leaning_vs_pm_decided`
* **Diễn biến:** Trang (QA Lead) chốt *"Vậy chốt ảnh chụp thật nhé"*. Theo ma trận phân quyền `decision_rights.yaml`, nhóm design chỉ có Design Lead (Lan) hoặc Head of Product (Huy) mới có quyền chốt. Đến phát biểu kế tiếp, Lan lên tiếng: *"Ừ, mình đồng ý ảnh chụp thật"*.
* **Kỳ vọng:** Phát biểu của Trang ban đầu chưa đủ thẩm quyền (nếu chỉ có Trang thì phải hạ về "Nghiêng về"), nhưng quyết định được hợp lệ hóa thành "Đã chốt" ngay sau khi người có thẩm quyền (Lan) lên tiếng xác nhận.
* **Kết quả thực tế:** Trạng thái ghi nhận `status: "decided"`, `final_option: "ảnh chụp thật"`. (Ở bài test độc lập: nếu người lạ chốt mà không có PM xác nhận thì giữ nguyên trạng thái "Nghiêng về").
* **Đánh giá:** **ĐẠT.**
* **Điều học được:** Tách riêng ma trận thẩm quyền (`decision_rights.yaml`) khỏi lời thoại giúp động cơ luật kiểm soát chặt chẽ ai có quyền chốt loại quyết định nào, đồng thời linh hoạt công nhận quyết định khi người có thẩm quyền chuẩn thuận sau đó.

#### Tình huống 5: Tình huống sản phẩm chưa xử lý tốt / Thất bại thực tế — Bỏ sót đầu việc phụ trao đổi nhanh cuối giờ
* **Kịch bản:** `m01` (Việc xin ngân sách của Minh)
* **Diễn biến:** Ở phần cuối buổi họp `m01`, Hà nhắc việc chưa duyệt ngân sách gói Pro của Supabase, Minh nói: *"Mình sẽ nhắn anh Phúc sau, chưa biết khi nào có trả lời"*.
* **Kỳ vọng:** Hệ thống trích xuất đầy đủ cả 2 công việc (Việc dựng Supabase của Quân và Việc xin ngân sách của Minh).
* **Kết quả thực tế:** Hệ thống bóc tách trúng việc của Quân; nhưng bỏ sót việc xin ngân sách của Minh (`tasks: 1/2`, `tasks_ok: False`, khiến ca `m01` không đạt benchmark tuyệt đối).
* **Đánh giá:** **CHƯA ĐẠT** (thất bại ở khâu thu hồi việc phụ ở cuối buổi họp).
* **Điều học được:** Khi phát biểu xuất hiện ở cuối buổi họp dưới dạng câu nói ngắn, thiếu chủ ngữ và không có hạn chót cụ thể, mô hình LLM dễ nhầm lẫn thành câu xã giao (chitchat) và bỏ qua. Cần cải thiện few-shot prompt hoặc bổ sung câu hỏi rà soát riêng cho 5% phát biểu cuối transcript trước khi đóng biên bản.

---

### 4.3. Kết Quả Thực Nghiệm Trên Tập Phát Triển (In-Sample Dev Set)

Bảng so sánh đối chứng trên 20 cuộc họp chuẩn (`m01–m08`, `g01–g12`):

| Chỉ số đánh giá | Gemini thuần (`gemini+none`) *(Cấu hình chính)* | Gemini + Jev Cảnh báo (`judge-mode advisory`) | Gemini + Jev Tự hạ (`judge-mode downgrade`) | Oracle tham chiếu (`oracle+none`) |
|---|---|---|---|---|
| **Tỷ lệ đạt (Pass rate)** | **90.0%** (18/20 ca) | **90.0%** (18/20 ca) | 85.0% (17/20 ca) | **100%** (20/20 ca) |
| **Lỗi chốt nhầm (Critical Errors)** | **0** *(tập phát triển, in-sample)* | **0** | **0** | **0** |
| **Hạ oan quyết định đúng** | **0 ca** (0%) | **0 ca** (0%) | 1 ca (`g12`, 12.5%) | **0** |
| **Gánh nặng duyệt thêm** | 0 ca | 1 ca (`g12`, 12.5%) | 0 ca | 0 |
| **Độ thu hồi việc (Task recall)** | 95% | 95% | 95% | 100% |
| **Đúng người nhận việc (Assignee)** | 95% | 95% | 95% | 100% |
| **Đúng hạn chót (Deadline)** | 95% | 95% | 95% | 100% |
| **Tự tạo người nhận / hạn chót** | **0** | **0** | **0** | **0** |
| **Độ chính xác trích dẫn nguyên văn**| **100%** | **100%** | **100%** | **100%** |

*Ghi chú:* Hai ca chưa đạt (`m01`, `m07`) xuất phát từ việc LLM bỏ sót việc phụ trao đổi ngắn hoặc câu hỏi mở bên lề ở cuối giờ. Trạng thái quyết định đạt 100% độ chính xác trên toàn bộ tập dữ liệu dev, hoàn toàn không có lỗi chốt nhầm.

---

### 4.4. Kết Quả Ngoài Tập Tinh Chỉnh (Out-of-Sample Generalization)

Nhằm kiểm tra tính tổng quát hóa độc lập ngoài tập phát triển nội bộ:
* **Tập thử nghiệm độc lập:** Gồm 60 câu phát biểu kiểm thử điều kiện (`conditional_sentences_60.json`) và 6 cuộc họp do AI ngoài (Nemotron) sinh độc lập tại `data/independent_tests/meetings/` (`indep_m01`–`indep_m06`), đạt **1/6 (16.7%) kết quả thô tự động**.
* **Độ tin cậy và đối soát:** Con số "0 critical error" là trên tập dev; trên tập độc lập có 1 cảnh báo, sau đối soát là báo động giả của bộ chấm (bộ chấm chuỗi cứng `_hit()` phạt nhầm do lệch từ nối ngữ cảnh tại `indep_m04`, trong khi pipeline đã chốt đúng theo transcript và đúng thẩm quyền của PM Viết).
* **Báo cáo chi tiết:** Phân tích đối soát từng ca và dữ liệu thực nghiệm được trình bày chi tiết tại [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md).

---

### 4.5. Cơ Chế Xử Lý Bộ Nhớ Đệm Demo Cache (`demo_cache/`)

Để bảo đảm quá trình chấm thi trực tuyến diễn ra mượt mà và không phụ thuộc vào tình trạng mạng hay hạn mức API:
1. **Dữ liệu cache chuẩn bị sẵn:** Toàn bộ 707 mục phản hồi của Gemini và Jev cho cả 26 cuộc họp mẫu (`m01`–`m08`, `g01`–`g12`, `indep_m01`–`indep_m06`) đã được sao chép vào thư mục `demo_cache/` (dung lượng chỉ 0.31 MB) và commit trực tiếp vào git repository.
2. **Kiểm tra an toàn bí mật:** Thư mục `demo_cache/` đã được quét tự động bằng regex chuyên dụng, **bảo đảm 100% không chứa API key, mật mã hay token riêng tư**.
3. **Cơ chế đọc ưu tiên:** Trong [src/llm.py](src/llm.py), cả hai hàm `generate_json` và `call_jev` luôn kiểm tra thư mục `demo_cache/` đầu tiên trước khi gọi ra API bên ngoài.
4. **Lợi ích khi chấm bài:**
   * Ban Giám khảo có thể bấm xem và phân tích lại bất kỳ cuộc họp mẫu nào trong 26 cuộc họp với tốc độ phản hồi tức thì (~50ms).
   * Hệ thống hoạt động 100% ổn định kể cả khi khóa API bị hết hạn mức (quota = 0) hoặc chưa cấu hình biến môi trường trên Render.
   * Chỉ khi người dùng tải lên transcript mới chưa từng có trong cache, hệ thống mới tiêu tốn hạn mức API bên ngoài (có trần 100 lượt/ngày bảo vệ).

---

## 5. Trả Lời 3 Câu Hỏi Bắt Buộc

### Câu hỏi 1: Phần quan trọng nhất bạn chọn để hiện thực hóa trong MVP là gì? Vì sao nếu phần này hoạt động, bạn tin rằng hướng giải quyết của mình là khả thi?

* **Phần quan trọng nhất:** Tách rời hoàn toàn khâu đọc hiểu của LLM khỏi khâu ra quyết định, sử dụng bộ kiểm chứng trích dẫn nguyên văn 100% kết hợp với động cơ luật cứng theo dòng thời gian (*Exact Substring Verification + Deterministic Timeline Engine*).
* **Vì sao tin là khả thi:** 
  Trong thực tế họp hành, rủi ro tai hại nhất là ghi nhận sai quyết định (người tham gia ban đầu bàn phương án A, sau đó đổi ý chốt phương án B) hoặc gán nhầm đầu việc cho người chỉ bị nhắc tên vu vơ. Nếu để LLM tự do tóm tắt hoặc dùng tìm kiếm ngữ nghĩa (RAG), mô hình rất dễ bị ảo giác, coi cả ý kiến ban đầu và kết luận mới đều là quyết định có hiệu lực.
  Bằng cách buộc mọi trích dẫn làm bằng chứng phải khớp nguyên văn từng chữ trong biên bản gốc, sau đó cho động cơ luật kiểm tra tuần tự 4 điều kiện: (1) Không ràng buộc điều kiện, (2) Đúng người có thẩm quyền, (3) Không còn ai phản đối sau đó, (4) Không bị rút lại hoặc đổi ý ở phát biểu muộn hơn, hệ thống triệt tiêu hoàn toàn khả năng chốt nhầm. Thực nghiệm chứng minh hệ thống đạt 0 wrong decided trên 20 cuộc họp (tập phát triển, in-sample).

### Câu hỏi 2: So với kế hoạch ở Mission 1, bạn đã thay đổi quyết định hoặc thiết kế nào? Điều gì trong quá trình làm khiến bạn thay đổi?

* **Bỏ mô hình xếp hạng tài liệu ngoài (Reranker):** Ban đầu dự kiến dùng một mô hình LLM bên ngoài để xếp hạng lại tài liệu quy định công ty trước khi đưa vào ngữ cảnh. Nhưng qua thực nghiệm, các tài liệu dự án thường ngắn gọn; việc nạp trực tiếp toàn bộ tài liệu vào bộ nhớ vừa nhanh hơn, vừa loại bỏ phụ thuộc mạng và tiết kiệm chi phí gọi API.
* **Xử lý bất đối xứng khi kiểm tra câu phản đối:** Ban đầu nếu nhãn trích dẫn bị lệch dù chỉ một ký tự, hệ thống sẽ hủy nhãn đó. Tuy nhiên, nếu hủy một nhãn phản đối hoặc đảo chiều ý kiến, hệ thống có thể vô tình chốt một quyết định vốn đã bị bác bỏ trong thực tế. Vì vậy, hệ thống đổi sang cơ chế bất đối xứng: câu phản đối dù trích dẫn chưa chuẩn vẫn được giữ lại để hạ cấp quyết định về "Nghiêng về", bảo đảm thà hỏi lại con người còn hơn chốt ẩu.
* **Chuyển bộ chấm phụ sang chế độ cảnh báo (Advisory Mode):** Ban đầu định để bộ chấm AI tự động hạ cấp quyết định ("Downgrade Mode"). Thực nghiệm cho thấy bộ chấm phụ có lúc hiểu sai các câu đồng thuận ngắn và hạ oan quyết định đúng (như ca `g12`). Chuyển sang chế độ cảnh báo giúp hệ thống vừa giữ được độ an toàn, vừa không gây phiền hà cho người dùng.

### Câu hỏi 3: Loại thông tin nào hệ thống hiện dễ ghi nhận sai nhất? Bạn đang làm gì để tránh tạo ra một quyết định, công việc hoặc dữ liệu không thực sự tồn tại trong cuộc họp?

* **Thông tin dễ sai nhất:** Xác định người nhận việc khi người tham gia chỉ được người khác nhắc tên ("chắc Nam làm được việc này"), các phát biểu ngập ngừng do dự ("để em xem lại đã", "chắc là được"), và các đầu việc trao đổi quá vắn tắt ở những giây cuối buổi họp.
* **Cách kiểm soát và phòng ngừa:**
  1. **Bộ lọc từ ngữ do dự (Hedge Check):** Nhận diện các câu nói ngập ngừng, thăm dò; nếu phát hiện, hệ thống không tự động gán tên người đó mà chuyển về trạng thái cần xác nhận.
  2. **Đối soát quyền hạn nghiêm ngặt:** Chỉ những người có vai trò phù hợp trong ma trận quyền hạn mới có thể chốt các chủ đề tương ứng (ví dụ: chỉ Tech Lead mới có quyền chốt kiến trúc kỹ thuật; thành viên thông thường kết luận sẽ tự động đưa về "Nghiêng về").
  3. **Hàng chờ duyệt (Review Queue) cho con người:** Toàn bộ các trường hợp bị cắm cờ nghi ngờ đều được gom vào một danh sách riêng trên giao diện để người chủ trì xem lại và bấm duyệt nhanh chỉ với một thao tác, ngăn chặn triệt để mọi dữ liệu rác lọt vào cơ sở tri thức doanh nghiệp.

---

## 6. Bảo Mật và Bản Quyền

* **Bảo mật dữ liệu:** Hệ thống không lưu trữ API key, mã truy cập hay nội dung phát biểu nhạy cảm vào log. Bản demo trực tuyến có cơ chế phân quyền bằng mã `ACCESS_CODE`, giới hạn tần suất yêu cầu theo IP và trần số lượt chạy mỗi ngày.
* **Bản quyền:** Mã nguồn được phát hành theo giấy phép tự do [MIT License](LICENSE).
