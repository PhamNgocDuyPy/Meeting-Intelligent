# Meeting Intel

Hệ thống trích xuất dữ liệu có cấu trúc từ biên bản cuộc họp, theo dõi diễn biến quyết định theo dòng thời gian (A sang B) và kiểm chứng 100% chuỗi con nguyên văn (Exact Substring Verification).

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: 14/14 Passed](https://img.shields.io/badge/tests-14%2F14%20passed-brightgreen.svg)]()
[![Benchmark: 90% Pass (0 Critical Errors)](https://img.shields.io/badge/benchmark-90%25%20(0%20critical%20errors)-success.svg)]()

---

## 1. Bài toán và Nguyên tắc Thiết kế

Trong các cuộc họp kỹ thuật và điều hành:
* Ý kiến thảo luận biến động liên tục: Đầu cuộc họp đề xuất phương án A, cuối cuộc họp thống nhất phương án B.
* Thách thức cốt lõi là xác định chính xác kết luận hiện hành có giá trị thực thi, thay vì tóm tắt văn bản thông thường hay sử dụng RAG đối sánh tương đồng (dễ coi cả A và B cùng là quyết định có hiệu lực).

### Nguyên tắc cốt lõi:
1. **Ưu tiên đúng hơn đủ:** Thà hạ cấp quyết định về trạng thái nghiêng về để con người duyệt còn hơn tự ý chốt nhầm một ý kiến chưa ngã ngũ.
2. **Tách biệt trích xuất và phân xử:** LLM chỉ đảm nhận bóc tách phát biểu thô; động cơ luật tất định chịu trách nhiệm cập nhật trạng thái theo 4 điều kiện nghiêm ngặt.
3. **Kiểm chứng bằng chứng cứng:** Mọi trích dẫn làm căn cứ bắt buộc phải là chuỗi con chính xác trong transcript gốc (100% Substring Verification).

---

## 2. Kiến trúc Hệ thống

```
[ Transcript thô ]
       │
       ▼
[ Layer 1: Kiểm chứng chuỗi con (Exact Substring Verification) ]
  • Kiểm tra 100% trích dẫn xuất phát nguyên văn từ transcript.
  • Bất đối xứng bằng chứng: Nhãn phủ định sai trích dẫn vẫn được giữ lại để hạ cấp an toàn.
       │
       ▼
[ Layer 2: Động cơ luật dòng thời gian (Deterministic Rules Engine) ]
  • Áp dụng 4 điều kiện: Không điều kiện, Đúng thẩm quyền, Không phản đối, Không bị đảo ngược muộn hơn.
  • Theo dõi trình tự phát biểu: Đề xuất A ➔ Phản đối A ➔ Kết luận B.
       │
       ▼
[ Layer 3: Lưới phòng thủ cảnh báo (Advisory Safety Net) ]
  • Bộ chấm phân tích câu hỏi hẹp (chốt, phản đối, đảo ngược, điều kiện, thẩm quyền, giao việc).
  • Kiểm tra từ do dự (Hedge Check) ngăn chặn việc gán sai trách nhiệm công việc.
  • Hoạt động ở chế độ cảnh báo (Advisory Mode) để đẩy vào hàng chờ duyệt, không tự động hạ cấp.
       │
       ▼
[ Layer 4: Giao diện người duyệt và xuất dữ liệu ]
  • Giao diện tra cứu 2 chiều giữa trích dẫn và transcript.
  • Đầy đủ 3 thao tác duyệt: Xác nhận, Chỉnh sửa, Từ chối.
  • Xuất dữ liệu: Markdown biên bản, CSV công việc, JSONL kho tri thức.
```

---

## 3. Cài đặt và Yêu cầu Môi trường

### Yêu cầu
* Python 3.10 trở lên.
* Hệ điều hành: Windows, macOS hoặc Linux.

### Cài đặt thư viện
```bash
git clone https://github.com/PhamNgocDuyPy/Meeting-Intelligent.git
cd Meeting-Intelligent
pip install -r requirements.txt
```

### Cấu hình môi trường (Tùy chọn)
Sao chép `.env.example` thành `.env` nếu chạy với Gemini API:
```bash
cp .env.example .env
```
*Lưu ý: Hệ thống hỗ trợ chế độ `--oracle` để chạy kiểm thử cục bộ hoàn chỉnh mà không cần API key.*

---

## 4. Hướng dẫn Sử dụng

### A. Khởi chạy Giao diện Web (Review UI)
```bash
python main.py ui --port 8080
```
Truy cập tại: `http://127.0.0.1:8080`

Các chức năng chính:
* **Tra cứu 2 chiều:** Nhấp vào bất kỳ sự kiện, trích dẫn hoặc công việc để tự động cuộn đến phát biểu gốc trong transcript.
* **Bộ lọc trạng thái:** Lọc theo chủ đề đã chốt, diễn biến đổi ý A sang B, công việc cần làm, và hàng chờ duyệt.
* **Quy trình phê duyệt Human-in-the-Loop:** Xác nhận, chỉnh sửa trực tiếp nội dung hoặc từ chối quyết định.
* **Xuất kết quả:** Xuất biên bản Markdown, danh sách việc ra CSV, hoặc chuẩn hóa JSONL.

### B. Chạy Kiểm thử và Đánh giá (Evaluation)
```bash
# Đánh giá cấu hình chính thức (Gemini + Luật tất định)
python main.py eval --backend gemini --judge none

# Đánh giá cấu hình cảnh báo (Gemini + Jev Advisory)
python main.py eval --backend gemini --judge jev --judge-mode advisory

# Đánh giá với nhãn tham chiếu cục bộ (Không cần API key)
python main.py eval --oracle

# So sánh trực tiếp kết quả giữa 2 lần chạy
python main.py compare outputs/eval_gemini_none.json outputs/eval_gemini_jev.json
```

### C. Chạy Một Cuộc họp Cụ thể qua CLI
```bash
python main.py run m01 --oracle --judge jev --judge-mode advisory --save
```
Kết quả được xuất ra thư mục `outputs/`:
* `outputs/m01.md`: Biên bản cuộc họp Markdown.
* `outputs/m01_tasks.csv`: Bảng công việc chi tiết.
* `outputs/m01_decisions.jsonl`: Hợp đồng dữ liệu quyết định cho kho tri thức.

### D. Chạy Kiểm thử Tự động (Pytest)
```bash
pytest -v
```
Kết quả: 14/14 unit & mutation tests vượt qua trong 0.5 giây.

---

## 5. Kết quả Thực nghiệm

Bảng so sánh đối chứng trên 20 cuộc họp chuẩn (`m01–m08`, `g01–g12`):

| Chỉ số đánh giá | Gemini thuần (`gemini+none`) *(Cấu hình chính)* | Gemini + Jev Cảnh báo (`judge-mode advisory`) | Gemini + Jev Tự hạ (`judge-mode downgrade`) | Oracle tham chiếu (`oracle+none`) |
|---|---|---|---|---|
| **Tỷ lệ đạt (Pass rate)** | **90.0%** (18/20 ca) | **90.0%** (18/20 ca) | 85.0% (17/20 ca) | **100%** (20/20 ca) |
| **Lỗi chốt nhầm (Critical Errors)** | **0** | **0** | **0** | **0** |
| **Hạ oan quyết định đúng** | **0 ca** (0%) | **0 ca** (0%) | 1 ca (`g12`, 12.5%) | **0** |
| **Gánh nặng duyệt thêm** | 0 ca | 1 ca (`g12`, 12.5%) | 0 ca | 0 |
| **Độ thu hồi việc (Task recall)** | 95% | 95% | 95% | 100% |
| **Đúng người nhận việc (Assignee)** | 95% | 95% | 95% | 100% |
| **Đúng hạn chót (Deadline)** | 95% | 95% | 95% | 100% |
| **Tự tạo người nhận / hạn chót** | **0** | **0** | **0** | **0** |
| **Độ chính xác trích dẫn nguyên văn**| **100%** | **100%** | **100%** | **100%** |

*Ghi chú:* Hai ca chưa đạt (`m01`, `m07`) xuất phát từ việc mô hình bỏ sót các việc phụ trao đổi ngắn cuối giờ. Tỷ lệ chính xác về trạng thái quyết định đạt 100% trên toàn bộ tập thử nghiệm.

---

## 6. Cấu trúc Thư mục

```
meeting-intel/
├── data/
│   ├── company/           # Ma trận vai trò, thẩm quyền và chính sách doanh nghiệp
│   ├── independent_tests/ # Bộ dữ liệu kiểm thử độc lập (6 cuộc họp e2e, 60 câu điều kiện)
│   └── meetings/          # 20 kịch bản họp mẫu (m01-m08, g01-g12)
├── docs/
│   ├── MISSION_2_REPORT.md# Báo cáo thực nghiệm và số liệu chi tiết
│   ├── PLAN_AND_JEV.md    # Tài liệu kỹ thuật tích hợp Jev System One
│   └── TEST_CASES.md      # Bộ 8 ca kiểm thử tiêu biểu kèm phân tích thất bại
├── experiments/           # Scripts thực nghiệm độc lập (Reranker, Judge, Noise, Mutations)
├── outputs/               # Kết quả xuất biên bản Markdown, CSV và file JSON đánh giá
├── src/
│   ├── assemble.py        # Tổng hợp dữ liệu, kiểm soát người nhận việc và hàng chờ duyệt
│   ├── context.py         # Nạp bối cảnh 3 tầng và reranker
│   ├── dates.py           # Phân giải hạn chót tương đối
│   ├── evaluate.py        # Động cơ đánh giá so với ground truth
│   ├── evidence.py        # Kiểm chứng trích dẫn chuỗi con
│   ├── export.py          # Xuất định dạng Markdown, CSV và JSONL
│   ├── judge.py           # Bộ chấm câu hỏi hẹp (Jev / Gemini)
│   ├── labeler.py         # Bóc tách và gán nhãn phát biểu qua LLM
│   ├── llm.py             # Client API tích hợp Jev và Gemini
│   ├── parser.py          # Phân tích cú pháp transcript (hỗ trợ có hoặc không có mốc giờ)
│   ├── pipeline.py        # Luồng xử lý tích hợp toàn bộ hệ thống
│   ├── rules.py           # Động cơ luật tất định áp 4 điều kiện chốt
│   ├── schema.py          # Pydantic schema dùng chung
│   └── server.py          # Máy chủ HTTP phục vụ Web UI và REST API
├── tests/
│   ├── test_integrity.py  # Bộ kiểm thử tích hợp và kiểm chứng dữ liệu
│   └── test_mutations.py  # Bộ kiểm thử đột biến phòng thủ hallucination
├── web/
│   ├── index.html         # Giao diện tra cứu và duyệt biên bản
│   ├── style.css          # Hệ thống giao diện tối ưu tương phản
│   └── app.js             # Logic tương tác tra cứu 2 chiều và phê duyệt
├── main.py                # Điểm vào CLI chính (run, eval, compare, ui)
├── pytest.ini             # Cấu hình kiểm thử
└── requirements.txt       # Danh sách thư viện phụ thuộc
```

---

## 7. Trả Lời 3 Câu Hỏi Bắt Buộc

### Câu hỏi 1: Phần quan trọng nhất bạn chọn để hiện thực hóa trong MVP là gì? Vì sao nếu phần này hoạt động, bạn tin rằng hướng giải quyết của mình là khả thi?
* **Phần quan trọng nhất:** Cặp động cơ phân xử theo dòng thời gian bằng luật tất định kết hợp kiểm chứng trích dẫn chuỗi con nguyên văn (*Deterministic Timeline Engine + Exact Substring Verification*).
* **Căn cứ khả thi:** Trong ghi nhận cuộc họp, lỗi nguy hiểm nhất là ghi nhận sai quyết định (coi đề xuất ban đầu là kết luận hiện hành) và gán nhầm việc cho người chỉ được nhắc tên. Việc tách khâu trích xuất của LLM khỏi luật chốt và kiểm chứng 100% trích dẫn chuỗi con giúp triệt tiêu nguy cơ bịa đặt thông tin nguồn. Kết quả thực nghiệm cho thấy hệ thống đạt 0 lỗi chốt nhầm trên toàn bộ 20 cuộc họp thử nghiệm.

### Câu hỏi 2: So với kế hoạch ở Mission 1, bạn đã thay đổi quyết định hoặc thiết kế nào? Điều gì trong quá trình làm khiến bạn thay đổi?
* **Reranker:** Không sử dụng mô hình ngoài làm reranker trong pipeline chính vì nạp trực tiếp tài liệu bối cảnh vào bộ nhớ đạt tốc độ cao hơn và không phụ thuộc mạng; thực nghiệm độc lập cho thấy điểm nghẽn chính nằm ở bước trích chọn ứng viên ban đầu chứ không phải ở reranker.
* **Bất đối xứng nhãn phủ định:** Khi nhãn phủ định (`reverse`, `oppose`) gặp lỗi trích dẫn, hệ thống không loại bỏ nhãn mà giữ lại kèm cờ cảnh báo để hạ cấp quyết định về trạng thái nghiêng về, ngăn chặn việc vô tình chốt phương án cũ bị lật kèo.
* **Phát hiện từ do dự:** Bổ sung regex nhận diện từ do dự kết hợp kiểm tra ngữ cảnh phát biểu kế tiếp để ngăn chặn việc gán việc khi người tham gia chỉ được gợi ý hoặc chưa nhận lời chính thức.
* **Chế độ hoạt động của bộ chấm:** Giữ bộ chấm ở chế độ cảnh báo (`advisory`), không áp dụng chế độ tự động hạ cấp (`downgrade`) do rủi ro hạ nhầm quyết định hợp lệ trong thực tế.

### Câu hỏi 3: Loại thông tin nào hệ thống hiện dễ ghi nhận sai nhất? Bạn đang làm gì để tránh tạo ra một quyết định, công việc hoặc dữ liệu không thực sự tồn tại trong cuộc họp?
* **Thông tin dễ sai nhất:** Người nhận việc trong các câu nói do dự, các công việc phụ phát sinh nhanh cuối cuộc họp, và nhóm phân loại quyết định (`category`) khi bối cảnh không rõ ràng.
* **Giải pháp kiểm soát:**
  1. Duy trì bộ kiểm thử đột biến tự động để kiểm tra khả năng phòng thủ trước hiện tượng ảo giác của mô hình ngôn ngữ.
  2. Áp dụng quy tắc lọc từ do dự và đối chiếu danh sách nhân sự có thẩm quyền trong dự án.
  3. Sử dụng hàng chờ duyệt (Review Queue) để chuyển toàn bộ các trường hợp có cờ nghi ngờ cho con người trực tiếp xác nhận trước khi lưu trữ chính thức.

---

## 8. Bảo mật và Bản quyền
* **Bảo mật:** Dự án không lưu trữ API key hoặc thông tin định danh nhạy cảm. Mọi thông tin cấu hình được quản lý qua biến môi trường.
* **Bản quyền:** Mã nguồn được phát hành theo giấy phép [MIT License](LICENSE).
