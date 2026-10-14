# KẾ HOẠCH TRIỂN KHAI TRỰC TUYẾN & QUẢN TRỊ RỦI RO (DEPLOYMENT GUIDE)

Tài liệu này lưu trữ quy trình kỹ thuật nội bộ triển khai hệ thống Meeting Intel lên hạ tầng đám mây (Render) và các biện pháp kiểm soát rủi ro trong suốt giai đoạn chấm thi Mission 2.

---

## 1. Bảng Quản Lý Rủi Ro Khi Chấm Trực Tuyến

| Rủi ro tiềm ẩn | Mức độ | Biện pháp giảm thiểu kỹ thuật đã triển khai |
|---|:---:|---|
| **Máy chủ miễn phí tự ngủ (Cold start)** | Trung bình | • Hiển thị cảnh báo "Mở lần đầu chờ ~1 phút" ngay đầu README và trên thanh thông báo web.<br>• Sử dụng dịch vụ ping định kỳ (UptimeRobot) gọi `/healthz` mỗi 5 phút để giữ máy chủ luôn thức trong giờ cao điểm chấm bài.<br>• Chuẩn bị sẵn phương án nâng gói trả phí nếu cần đảm bảo độ khả dụng tuyệt đối. |
| **Hết hạn mức (Quota) khóa Gemini** | Cao | • Toàn bộ 26 cuộc họp mẫu đọc trực tiếp từ `demo_cache/` (đã commit và quét bảo mật trước), chạy bình thường kể cả khi hết quota hoặc chưa cấu hình API key.<br>• Chỉ transcript mới do giám khảo tải lên mới tiêu tốn quota; hệ thống đặt trần `DAILY_RUN_LIMIT=100` lượt/ngày và hiển thị thông báo hướng dẫn chạy local khi chạm trần. |
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
Trong tab **Environment**, thiết lập các biến sau:
* `PYTHON_VERSION`: `3.11.0` (hoặc `3.10.x` trở lên)
* `ACCESS_CODE`: *(Mã truy cập bí mật dành riêng cho Giám khảo, ví dụ: `MeetingIntel2026`)*
* `GEMINI_API_KEY`: *(Khóa Gemini API dành riêng cho bản demo trực tuyến)*
* `GEMINI_MODEL`: `gemini-3.1-flash-lite`
* `DAILY_RUN_LIMIT`: `100`
* `RATE_LIMIT_PER_MINUTE`: `30`

### Bước 4: Thiết lập Health Check
* Trong phần **Advanced Settings** -> **Health Check Path**: Điền `/healthz`.
* Render sẽ tự động thăm dò endpoint này để xác nhận dịch vụ đã sẵn sàng nhận kết nối.

### Bước 5: Kiểm thử sau khi triển khai (Smoke Test)
1. Mở URL Render trong cửa sổ ẩn danh (Incognito), chờ ~1 phút nếu máy chủ đang thức dậy.
2. Kiểm tra cuộc họp mẫu (ví dụ `m01`, `g10`): Chọn và xem kết quả — dữ liệu phải nạp tức thì từ `demo_cache/` mà không cần tiêu tốn quota Gemini.
3. Kiểm tra bảo vệ mật mã: Thử phân tích transcript mới mà không nhập mã truy cập -> máy chủ phải từ chối (401 Unauthorized).
4. Nhập mã `ACCESS_CODE` hợp lệ -> nạp transcript mới và xác nhận kết quả trả về chính xác.
5. Kiểm tra log của Render: Đảm bảo không có dòng nào in khóa API hoặc nội dung transcript ra màn hình console.

### Bước 6: Khóa Auto-Deploy
* Trong mục **Settings** của Render: Chuyển **Auto-Deploy** sang `No` (hoặc giữ nguyên deploy từ nhánh `release` và không bao giờ push vào nhánh này nữa).
* Cập nhật URL chính thức vào biểu mẫu nộp bài và README.
