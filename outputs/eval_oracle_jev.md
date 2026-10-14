# Kết quả kiểm thử — backend `oracle`, bộ chấm `jev`

- Số cuộc họp: 20 · đạt toàn bộ: 90%
- **Lỗi nghiêm trọng (chốt nhầm): 0** · bỏ sót quyết định (bảo thủ): 2
- Đúng trạng thái chủ đề: 90% · việc tìm thấy: 100% · đúng người nhận: 100% · đúng hạn: 100%
- Tự gán người nhận: 0 · tự điền hạn: 0 · tạo việc không có thật: 0
- Tỷ lệ nhãn có trích dẫn khớp transcript: 100%

| Ca | Độ khó | Kết quả thực tế | Đạt? |
|---|---|---|---|
| g01 | A đổi thành B, người có thẩm quyền chốt | Khớp đáp án tham chiếu | Đạt |
| g02 | người chốt không có thẩm quyền nhưng người có thẩm quyền xác nhận sau | Khớp đáp án tham chiếu | Đạt |
| g03 | quy trình: đồng thuận đủ số người (kiểu consensus) | Khớp đáp án tham chiếu | Đạt |
| g04 | chỉ 2/6 người ủng hộ -> chưa đủ đồng thuận | Khớp đáp án tham chiếu | Đạt |
| g05 | người nói là khách, không nhận diện được thẩm quyền | Khớp đáp án tham chiếu | Đạt |
| g06 | chốt có điều kiện chưa xảy ra | Khớp đáp án tham chiếu | Đạt |
| g07 | kết luận bị rút lại, chưa có kết luận mới | Khớp đáp án tham chiếu | Đạt |
| g08 | hai phương án, hoãn sang họp sau | Khớp đáp án tham chiếu | Đạt |
| g09 | phản đối sau khi chốt, chưa ai giải quyết | Khớp đáp án tham chiếu | Đạt |
| g10 | đủ loại việc: giao+hạn, tự nhận, chỉ nhắc tên, giao không hạn | Khớp đáp án tham chiếu | Đạt |
| g11 | hạn tương đối: ngày mai/thứ Sáu suy được; cuối tháng/tuần sau thì không | Khớp đáp án tham chiếu | Đạt |
| g12 | hai chủ đề đan xen: một chốt (phản đối đã được giải quyết), một chưa chốt | Bỏ sót quyết định ['GitHub Actions', 'Jenkins'] (hệ thống: leaning) | Chưa đạt |
| m01 | core: ý kiến đổi giữa họp (A->B) | Khớp đáp án tham chiếu | Đạt |
| m02 | dễ: việc có người nhận và hạn rõ | Khớp đáp án tham chiếu | Đạt |
| m03 | khó: đồng thuận ngầm, chưa ai chốt | Khớp đáp án tham chiếu | Đạt |
| m04 | khó: người nói không có thẩm quyền + hoãn | Khớp đáp án tham chiếu | Đạt |
| m05 | khó: chốt có điều kiện chưa xảy ra | Khớp đáp án tham chiếu | Đạt |
| m06 | khó: đổi ý + người chốt trước không có thẩm quyền | Bỏ sót quyết định ['release', 'ngày release'] (hệ thống: leaning) | Chưa đạt |
| m07 | mơ hồ: tham chiếu không rõ, việc chỉ bị nhắc tên, hạn mơ hồ | Khớp đáp án tham chiếu | Đạt |
| m08 | khó: hai chủ đề đan xen, một chốt một hoãn | Khớp đáp án tham chiếu | Đạt |
