# KẾ HOẠCH TRIỂN KHAI TRỰC TUYẾN & QUẢN TRỊ RỦI RO (DEPLOYMENT GUIDE)

Tài liệu này lưu trữ quy trình kỹ thuật nội bộ triển khai hệ thống Meeting Intel lên hạ tầng đám mây (Render) và các biện pháp kiểm soát rủi ro trong suốt giai đoạn chấm thi Mission 2.

---

## 1. Bảng Quản Lý Rủi Ro Khi Chấm Trực Tuyến

| Rủi ro tiềm ẩn | Mức độ | Biện pháp giảm thiểu kỹ thuật đã triển khai |
|---|:---:|---|
| **Máy chủ miễn phí tự ngủ (Cold start)** | Trung bình | • Hiển thị cảnh báo "Mở lần đầu chờ ~1 phút" ngay đầu README và trên thanh thông báo web.<br>• Sử dụng dịch vụ ping định kỳ (UptimeRobot) gọi `/healthz` mỗi 5 phút để giữ máy chủ luôn thức trong giờ cao điểm chấm bài.<br>• Chuẩn bị sẵn phương án nâng gói trả phí nếu cần đảm bảo độ khả dụng tuyệt đối. |
| **Hết hạn mức (Quota) khóa Gemini** | Cao | • Toàn bộ 26 cuộc họp mẫu đọc trực tiếp từ `demo_cache/` (đã commit và quét bảo mật trước), chạy bình thường kể cả khi hết quota hoặc chưa cấu hình API key.<br>• Khi phân tích transcript mới, nếu Gemini gặp lỗi mạng/hết quota, hệ thống tự động chuyển sang mô hình dự phòng NVIDIA NIM (`NVIDIA_API_KEY`).<br>• Đặt trần `DAILY_RUN_LIMIT=100` lượt/ngày để bảo vệ tài khoản. |
| **Khóa API bị đổi hoặc thu hồi sau khi nộp** | Cao | • Sử dụng khóa Gemini độc lập dành riêng cho bản demo trực tuyến (tách biệt hoàn toàn với khóa phát triển cá nhân).<br>• Cam kết không thu hồi hoặc chỉnh sửa khóa này cho đến khi có thông báo kết quả chính thức từ ban tổ chức. |
| **Commit mới làm hỏng phiên bản đang chạy** | Cao | • Gắn tag phiên bản `v1.0` cố định cho bản nộp.<br>• Cấu hình Render triển khai từ nhánh cố định `release` (hoặc tắt tính năng Auto-Deploy sau khi kiểm tra xong bản nộp).<br>• Tuyệt đối không đẩy thêm commit vào nhánh `release` sau hạn nộp bài. |

---

## 2. Quy Trình Triển Khai Chi Tiết Lên Render

### Bước 1: Chuẩn bị mã nguồn và nhánh phát hành
```bash
# Tạo nhánh release cố định từ tag v1.0
git checkout -b release v1.0
git push -u origin release
```

### Bước 2: Tạo Web Service trên Render Dashboard
1. Truy cập [dashboard.render.com](https://dashboard.render.com/) -> Chọn **New** -> **Web Service**.
2. Kết nối với GitHub repository: `https://github.com/PhamNgocDuyPy/Meeting-Intelligent.git`.
3. Cấu hình các thông số cơ bản:
   * **Name:** `meeting-intel`
   * **Region:** Singapore (hoặc gần nhất)
   * **Branch:** `release`
   * **Runtime:** `Python 3`
   * **Build Command:** `pip install -r requirements.txt`
   * **Start Command:** `python main.py ui --host 0.0.0.0 --port $PORT`
   * **Plan Type:** `Free`

### Bước 3: Thiết lập Biến Môi Trường (Environment Variables)

Trong tab **Environment** trên Render, bạn thiết lập các biến sau:

| Biến môi trường (Key) | Giá trị mẫu (Value) | Tính chất | Ý nghĩa kỹ thuật |
|---|---|:---:|---|
| `PYTHON_VERSION` | `3.11.0` | **Bắt buộc** | Đảm bảo Render dùng đúng runtime Python tương thích |
| `ACCESS_CODE` | `MeetingIntel2026` *(tự chọn)* | **Khuyến nghị** | Mã bảo vệ, chỉ cấp cho Giám khảo qua form nộp bài để ngăn spam quota |
| `GEMINI_API_KEY` | *(Khóa Gemini của bạn)* | **Cần thiết** | Dùng khi người dùng tải lên transcript mới cần gọi LLM ngoài cache |
| `GEMINI_MODEL` | `gemini-3.1-flash-lite` | Mặc định | Mô hình LLM chính thức của pipeline |
| `DAILY_RUN_LIMIT` | `100` | Mặc định | Khóa trần số lượt gọi LLM mới mỗi ngày (chống cạn kiệt tài khoản) |
| `RATE_LIMIT_PER_MINUTE` | `30` | Mặc định | Chặn địa chỉ IP gửi request dồn dập |
| `JEV_BASE_URL` | `https://opencode.ai/inference/v1/systemone` | Tùy chọn | Endpoint Jev System One (nếu có dùng Jev) |
| `OPENCODE_API_KEY` | *(Khóa OpenCode nếu có)* | Tùy chọn | Nếu để trống, server tự động bỏ qua Jev mà không gây lỗi |
| `NVIDIA_API_KEY` | *(Khóa NVIDIA nếu có)* | Dự phòng | Tự động kích hoạt thay thế nếu Gemini gặp sự cố mạng hoặc hết quota |
| `NVIDIA_MODEL` | `nvidia/nemotron-3.5-lightning-30b-a3b` | Mặc định | Mô hình NVIDIA NIM dự phòng |

---

### Bước 4: Thiết lập Health Check
* Trong mục **Advanced Settings** -> **Health Check Path**: Điền `/healthz`.
* Render sẽ tự động thăm dò endpoint này để xác nhận dịch vụ đã khởi động xong trước khi định tuyến người dùng.

---

### Bước 5: Hướng Dẫn Trải Nghiệm & Kiểm Thử Bản Live (User & Evaluator Flow)

> [!IMPORTANT]
> **Quy trình hoạt động của `ACCESS_CODE` (Không có tường chặn login bên ngoài):**
> 1. **Mở trang web tự do:** Bất kỳ ai có đường link Render đều mở được trang chủ ngay lập tức. Không có màn hình đăng nhập bắt chặn bên ngoài.
> 2. **Xem 26 cuộc họp mẫu (Không cần mã):** Chọn bất kỳ ca nào từ `m01` đến `m08`, `g01`–`g12`, hay `indep_m01`–`indep_m06`. Hệ thống nạp tức thì từ `demo_cache/` (~50ms) **mà không đòi hỏi nhập mã hay tiêu tốn hạn mức API**.
> 3. **Phân tích transcript mới (Cần nhập mã):** Khi bấm nút **"+ nạp transcript"** để dán nội dung mới, người dùng nhập `ACCESS_CODE` vào ô khóa (có thể nhập ở góc trên thanh Header hoặc nhập trực tiếp ngay trong cửa sổ popup Nạp Transcript). Mã được trình duyệt tự động lưu cho các lần sau.

#### Các bước kiểm tra nhanh sau deploy:
1. Mở URL Render trong cửa sổ ẩn danh (Incognito), chờ ~1 phút nếu máy chủ đang khởi động lần đầu (Cold start).
2. Kiểm tra cuộc họp mẫu (ví dụ `m01`, `g10`): Chọn và xem kết quả — dữ liệu phải nạp tức thì từ `demo_cache/`.
3. Kiểm tra bảo vệ mật mã: Bấm **"+ nạp transcript"**, xóa trắng ô `ACCESS_CODE` và bấm **"phân tích ngay"** -> Hệ thống phải báo lỗi yêu cầu mã (`401 Unauthorized`) và viền đỏ ô nhập mã.
4. Điền mã `ACCESS_CODE` đúng -> bấm **"phân tích ngay"** -> Hệ thống bóc tách thành công và chuyển ngay sang giao diện duyệt.
5. Kiểm tra log của Render: Đảm bảo không có dòng nào in khóa API hoặc nội dung transcript ra màn hình console.

### Bước 6: Khóa Auto-Deploy
* Trong mục **Settings** của Render: Chuyển **Auto-Deploy** sang `No` (hoặc giữ nguyên deploy từ nhánh `release` và không bao giờ push vào nhánh này nữa).
* Cập nhật URL chính thức vào biểu mẫu nộp bài và README.
