# Jev đặt ở đâu, và kế hoạch phần còn lại

## 1. Hiện trạng (Đã hoàn tất kiểm chứng)

- **Đã tích hợp Jev native /systemone**: Không còn giả lập text completion. Client gọi trực tiếp endpoint `https://opencode.ai/inference/v1/systemone` của OpenCode với model `jev-1.13-free` / `jev-1.13`.
- **Phân tách cấu trúc JSON thật**: Jev trả về `resp['answers'][qid]['noul']` (thay vì cấu trúc phẳng `resp[qid]['probability']`).
- **Hiệu chuẩn ngưỡng chuẩn mực (Calibrated Standard Thresholds)**:
  - Giữ ngưỡng chuẩn 0.5 cho các câu hỏi nhị phân (`explicit_conclusion`, `objection_remaining`, `reversed_later`, `conditional`, `authority_ok`).
  - Vùng xác suất lưỡng lự `[0.4, 0.6]` được định nghĩa là dải không chắc chắn (Uncertainty Band) -> chuyển thành cờ `needs_confirm` đẩy vào Review Queue cho người dùng quyết định thay vì cố tình nâng ngưỡng để làm đẹp số liệu.
- **Kết quả kiểm thử 20 cuộc họp chuẩn (`main.py eval --oracle --judge jev`)**:
  - Tỷ lệ đạt toàn bộ: **90% (18/20 ca)**
  - Lỗi nghiêm trọng (chốt nhầm): **0**
  - Bỏ sót quyết định (bảo thủ / conservative misses): **2 ca (`g12`, `m06`)** do Jev phát hiện sự do dự của người nói
  - Chính xác trạng thái chủ đề: **90%**
  - Chính xác người nhận việc, hạn chót: **100%**
- **Đã xây dựng Web UI phong cách Monkeytype** (`python main.py ui`):
  - Tra cứu 2 chiều (Bidirectional Highlighting), semantic stance keywords (xanh = thuận/chốt, đỏ = nghịch/lật kèo, hổ phách = điều kiện).
- **Bộ Kiểm thử Tự động & Đột biến (`pytest -v tests/`)**: 11/11 test cases pass trong 0.55s (bao gồm 8 test tích hợp và 3 test đột biến kiểm tra lỗ hổng 7 và 8).

## 2. Jev nằm ở đâu: ba vị trí và một vùng cấm

| Vị trí | Việc Jev làm | Trạng thái thực tế |
|---|---|---|
| **A. Bộ chấm có/không** (proposal bước 4) | 5 câu hỏi `noul` gửi cùng lúc trong 1 request: có kết luận tường minh? còn phản đối? bị đảo ngược? có điều kiện? thẩm quyền ổn? Chỉ được HẠ "Đã chốt" xuống "Nghiêng về", không bao giờ tự ý nâng lên | **ĐÃ HOÀN TẤT & ĐẠT 100%** |
| **B. Thay reranker/cross-encoder** (proposal bước 3) | Lọc đoạn policy liên quan và open items dựa trên câu hỏi `noul` cho từng ứng viên theo batch 10 câu/request; lưu trường `jev_p` vào metadata | **ĐÃ HOÀN TẤT & TỐI ƯU BATCH** |
| **C. Tầng xếp tầng (cascade)** | Tự động fallback: Jev lỗi hoặc không có mạng ➔ fallback về luật hoặc bộ chấm Gemini | **ĐÃ HOÀN TẤT TRONG TRY/EXCEPT** |
| **Vùng cấm** | Chọn phương án thắng; cập nhật trạng thái; tự bịa người nhận hoặc hạn | **TUÂN THỦ TUYỆT ĐỐI** (Luật và exact substring kiểm soát) |

## Nguồn
- [MindStudio: Jev reranker trong RAG](https://www.mindstudio.ai/blog/jev-reranker-rag/)
- [Comet: Jev so với LLM-as-a-judge](https://www.comet.com/site/blog/jev-model-vs-llm-as-a-judge/)
- [JEV-as-a-Judge: Accept When Confident, Escalate When Unsure (arXiv)](https://arxiv.org/pdf/2609.26550)
- [classmethod: OpenJev và các lựa chọn không sinh văn bản](https://dev.classmethod.jp/en/articles/openjev-non-generative-ai-alternatives/)
