# Dữ liệu tổng hợp và luồng ngữ cảnh

## 1. Dữ liệu: đã có gì, cần thêm gì

| Loại | Đã có (trong repo) | Cần thêm | Mục đích |
|---|---|---|---|
| Transcript | 20: `m01–m08` viết tay, `g01–g12` sinh bằng `scripts/gen_synthetic.py` | +12 bản "nhiễu" (nhờ Gemini viết lại g01–g12 thành lời nói đời thường: ngập ngừng, ngắt lời, viết tắt, lẫn tiếng Anh, lỗi ASR giả), giữ nguyên đáp án; +3 cuộc họp dài (200–600 phát biểu) với A ở phút 4, B ở phút 150 | Đạt ~35 ca. Bản nhiễu đo độ bền ngôn ngữ; cuộc họp dài tái hiện đúng câu chuyện mở đầu proposal |
| Đáp án tham chiếu | `expected.json` mỗi ca (so khớp theo từ khóa nên vẫn dùng được cho bản viết lại) | Nhờ 1 người khác (PM/bạn) rà ít nhất 8 ca khó | Proposal yêu cầu PM gán nhãn; hiện cùng một người viết transcript và đáp án nên có thiên lệch |
| Nhãn mẫu | `labels_oracle.json` (nhãn viết tay, dùng để test luật không cần API) | Không | Tách lỗi của luật khỏi lỗi của LLM |
| Audio | Không | Không cần cho MVP | Proposal ghi "audio để giai đoạn sau". Nếu muốn minh họa giới hạn: 2–3 clip TTS tiếng Việt → ASR → xem nhãn người nói bị mất thế nào (ưu tiên thấp) |
| Tài liệu công ty | 4 policy, `decision_rights.yaml`, `people.yaml` | +3 tài liệu "bẫy" (xem dưới) | Kiểm tra ngữ cảnh không bị dùng làm bằng chứng |
| Tài liệu dự án | 2 dự án (Aurora, Helios): charter, members, glossary, open_items | Như trên | |

**Tài liệu bẫy cần thêm** (mục tiêu: không quyết định hay việc nào được tạo chỉ từ bối cảnh):
1. Policy cũ đã bị thay thế, mâu thuẫn với policy hiện hành về người chốt release.
2. Charter ghi sẵn một lựa chọn mặc định ("dự kiến dùng Firebase") mà cuộc họp không hề nhắc tới → kết quả không được có quyết định Firebase.
3. `open_items.yaml` có một việc có tên người nhận, nhưng transcript không nhắc → không được xuất hiện thành việc đã giao.

**Cách chia tập:** `m01–m08` là tập chỉnh (được sửa prompt theo đó). `g01–g12` và các bản nhiễu là tập kiểm: chạy, lưu kết quả TRƯỚC khi sửa gì, rồi mới sửa và lưu bản sau. Lưu ý trung thực: `g01–g12` sinh từ khuôn câu nên kiểm tra độ phủ của luật, không đo được độ đa dạng ngôn ngữ; phần đó do bản nhiễu và `m01–m08` gánh.

**Bảng phủ tình huống**

| Tình huống | Ca |
|---|---|
| A đổi thành B | m01, m06, g01, g12 |
| Thẩm quyền (người chốt không có quyền / khách / xác nhận sau) | m04, m06, g02, g05 |
| Đồng thuận (đủ / thiếu) | m03, g03, g04 |
| Chốt có điều kiện | m05, g06 |
| Rút lại, chưa có kết luận mới | g07 |
| Hoãn | m04, m08, g08 |
| Phản đối chưa giải quyết | g09 |
| Việc: giao, tự nhận, chỉ nhắc tên, hạn tương đối | m02, m07, g10, g11 |
| Hai chủ đề đan xen | m08, g12 |
| Tham chiếu mơ hồ ("như đợt trước") | m07 |

## 2. Luồng đưa policy, dự án, mục đích họp vào kho dữ liệu

Ba tầng, mỗi tầng một nguồn sự thật, nạp theo khóa xác định (không dùng vector search cho phần này):

```
Tầng 0 · Công ty (ít đổi, có version)
  policies/*.md  ──(người duyệt rút ra, KHÔNG để LLM đọc lúc chạy)──►  decision_rights.yaml
  people.yaml (tên, bí danh, chức danh, vai trò toàn công ty)
Tầng 1 · Dự án
  charter.md · members.yaml (vai trò theo dự án: pm, tech_lead…) · glossary.yaml · open_items.yaml
Tầng 2 · Cuộc họp
  brief.yaml (mục đích, chương trình, ngày, danh sách người dự) · transcript.txt
                         │
                         ▼
        ContextPack = vai trò người dự (gộp tầng 0+1) + bảng thẩm quyền
                      + glossary + việc mở còn tồn + top-k đoạn policy liên quan
```

**Ngữ cảnh dùng vào việc gì**
1. Giải nghĩa tên gọi/thuật ngữ cho bước gán nhãn (chỉ đưa vào prompt, có ghi rõ "không phải bằng chứng").
2. Tính thẩm quyền bằng CODE: `rules.py` lấy vai trò người nói từ `people`/`members`, đối chiếu `decision_rights`. LLM không tự suy thẩm quyền từ văn bản policy.
3. Nhắc việc/chủ đề còn mở từ họp trước để gom đúng chủ đề.

**Ngữ cảnh KHÔNG được làm gì:** làm trích dẫn, tạo quyết định, tạo việc, điền người nhận/hạn. `evidence.py` chỉ chấp nhận trích dẫn nằm trong transcript.

**Vòng ghi ngược (sau khi PM duyệt) — chưa làm, thiết kế sẵn**
- Chủ đề "Đã chốt" → `projects/<p>/decision_log.jsonl` (mỗi dòng: meeting_id, topic, final_option, superseded, utterance_ids, approved_by, thời điểm).
- "Nghiêng về", "Chưa chốt", vướng mắc, câu hỏi mở → ghi vào `open_items.yaml` để họp sau nạp lại.
- Quyết định ở cuộc họp sau thay thế quyết định cũ: thêm trường `supersedes` trỏ về dòng log trước (ngoài phạm vi MVP, chỉ cần schema).

**Hiện trạng code:** `src/context.py` nạp đủ ba tầng; chọn đoạn policy bằng trùng từ khóa (thô, đây là chỗ nên thử reranker, xem `PLAN_AND_JEV.md`); mọi mục còn mở của dự án đều được đưa vào (chưa lọc). Chưa có vòng ghi ngược và chưa có tài liệu bẫy.
