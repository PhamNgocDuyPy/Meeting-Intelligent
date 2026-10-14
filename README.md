# Meeting Intel

Hệ thống trích xuất dữ liệu có cấu trúc từ biên bản cuộc họp, theo dõi diễn biến quyết định theo dòng thời gian (A sang B) và kiểm chứng 100% chuỗi con nguyên văn (Exact Substring Verification).

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: 16/16 Passed](https://img.shields.io/badge/tests-16%2F16%20passed-brightgreen.svg)]()
[![Benchmark: 90% Pass (0 Critical Errors)](https://img.shields.io/badge/benchmark-90%25%20(0%20critical%20errors)-success.svg)]()

---

## Demo Trực Tuyến

* **Địa chỉ truy cập:** [https://meeting-intel.onrender.com](https://meeting-intel.onrender.com) *(hoặc URL do người triển khai cấu hình)*
* **Lưu ý khởi động:** Do sử dụng gói máy chủ miễn phí trên Render, hệ thống sẽ tự động ngủ khi không có lượt truy cập. **Lần đầu mở trang có thể mất khoảng 1 phút để máy chủ khởi động lại.**
* **Mã truy cập (ACCESS_CODE):** Nhập mã truy cập được cung cấp riêng cho người chấm vào ô nhập mã trên thanh điều khiển của giao diện để mở khóa tính năng phân tích.
* **Cơ chế dự phòng:** Toàn bộ 26 cuộc họp mẫu chuẩn đã được lưu sẵn trong thư mục `demo_cache/`, hệ thống có thể chạy tức thì và chuẩn xác ngay cả khi hết hạn mức API bên ngoài.

---

## Bảng Quản Lý Rủi Ro Khi Chấm Trực Tuyến

| Rủi ro tiềm ẩn | Biện pháp giảm thiểu kỹ thuật đã triển khai |
|---|---|
| **Máy chủ miễn phí tự ngủ (Cold start)** | Hiển thị cảnh báo "Mở lần đầu chờ ~1 phút" ngay đầu README và trên thanh thông báo trang web. Có thể kết hợp ping định kỳ (UptimeRobot) hoặc nâng gói dịch vụ khi cần duy trì liên tục. |
| **Hết hạn mức (Quota) khóa Gemini** | 26 cuộc họp mẫu đọc trực tiếp từ `demo_cache/` (đã commit và quét bảo mật trước), chạy bình thường kể cả khi hết quota hoặc chưa cấu hình API key. Chỉ transcript mới do người dùng tải lên mới tiêu tốn quota, kèm trần giới hạn số lượt chạy mỗi ngày và thông báo hướng dẫn chạy local khi chạm trần. |
| **Khóa API bị đổi hoặc thu hồi sau khi nộp** | Cung cấp khóa API riêng biệt dành riêng cho bản demo chấm thi, không thu hồi cho đến khi có kết quả đánh giá chính thức. |
| **Commit mới làm hỏng phiên bản đang chạy** | Gắn tag phiên bản `v1.0` cố định cho bản nộp. Thiết lập Render triển khai từ tag hoặc nhánh release cố định và khóa auto-deploy sau khi nộp bài. |

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

## 4. Kết Quả Thực Nghiệm

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

*Ghi chú:* Hai ca chưa đạt điểm tuyệt đối (`m01`, `m07`) do mô hình bỏ sót các việc phụ trao đổi ngắn ở cuối buổi họp. Trạng thái quyết định đạt độ chính xác 100% trên toàn bộ tập dữ liệu, hoàn toàn không có lỗi chốt nhầm.

---

## 5. Trả Lời 3 Câu Hỏi Bắt Buộc

### Câu hỏi 1: Phần quan trọng nhất bạn chọn để hiện thực hóa trong MVP là gì? Vì sao nếu phần này hoạt động, bạn tin rằng hướng giải quyết của mình là khả thi?

* **Phần quan trọng nhất:** Tách rời hoàn toàn khâu đọc hiểu của LLM khỏi khâu ra quyết định, sử dụng bộ kiểm chứng trích dẫn nguyên văn 100% kết hợp với động cơ luật cứng theo dòng thời gian (*Exact Substring Verification + Deterministic Timeline Engine*).
* **Vì sao tin là khả thi:** 
  Trong thực tế họp hành, rủi ro tai hại nhất là ghi nhận sai quyết định (người tham gia ban đầu bàn phương án A, sau đó đổi ý chốt phương án B) hoặc gán nhầm đầu việc cho người chỉ bị nhắc tên vu vơ. Nếu để LLM tự do tóm tắt hoặc dùng tìm kiếm ngữ nghĩa (RAG), mô hình rất dễ bị ảo giác, coi cả ý kiến ban đầu và kết luận mới đều là quyết định có hiệu lực.
  Bằng cách buộc mọi trích dẫn làm bằng chứng phải khớp nguyên văn từng chữ trong biên bản gốc, sau đó cho động cơ luật kiểm tra tuần tự 4 điều kiện: (1) Không ràng buộc điều kiện, (2) Đúng người có thẩm quyền, (3) Không còn ai phản đối sau đó, (4) Không bị rút lại hoặc đổi ý ở phát biểu muộn hơn, hệ thống triệt tiêu hoàn toàn khả năng chốt nhầm. Thực nghiệm chứng minh hệ thống đạt 0 lỗi chốt nhầm trên toàn bộ 20 cuộc họp chuẩn.

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
