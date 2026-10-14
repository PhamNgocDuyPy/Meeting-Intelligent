"""Bước LLM: gom chủ đề + gán nhãn từng phát biểu + trích mục (việc, vướng mắc...). LLM KHÔNG quyết định trạng thái."""
from __future__ import annotations

from .context import ContextPack
from .llm import generate_json
from .parser import render_for_prompt
from .schema import LabelerOutput, Utterance

SYSTEM = """Bạn là trợ lý đọc biên bản cuộc họp tiếng Việt. Nhiệm vụ: ĐỌC transcript và GÁN NHÃN từng phát biểu theo chủ đề.
BẠN KHÔNG ĐƯỢC tự kết luận cái gì "đã chốt". Chỉ mô tả từng phát biểu đang làm gì; việc quyết định trạng thái do hệ thống khác làm.

Trả về DUY NHẤT một JSON object, theo schema:
{
 "topics": [{"topic_id": "T1", "title": "...", "category": "scope|technical|design|budget|release|process|other",
             "options": [{"option_id": "A", "label": "tên ngắn, đặc trưng của phương án"}]}],
 "labels": [{"utterance_id": "U005", "topic_id": "T1", "option_id": "A hoặc null",
             "stance": "propose|support|oppose|conclude|reverse|defer|question|info",
             "conditional": false, "condition_text": null, "quote": "trích NGUYÊN VĂN từ phát biểu đó"}],
 "items": [{"kind": "task|issue|request|feedback|open_question|knowledge", "title": "...", "detail": "...",
            "utterance_ids": ["U012","U013"], "quote": "trích NGUYÊN VĂN",
            "assignee": "tên hoặc null", "assignee_basis": "assigned|self_accepted|mentioned_only|none",
            "deadline_text": "cụm từ hạn NGUYÊN VĂN hoặc null"}]
}

ĐỊNH NGHĨA category:
- scope: phạm vi công việc, tính năng sprint, ngày demo nội bộ/demo cho khách. (PM có quyền chốt).
- release: CHỈ dành cho ngày phát hành sản phẩm chính thức ra công chúng/khách hàng (go/no-go production). (Cần cấp quản lý sản phẩm).
- technical: kiến trúc, thư viện, database, hạ tầng hosting. (Cần Tech Lead).
- design: thiết kế giao diện, bố cục UI/UX. (Cần Designer).
- budget: ngân sách gói dịch vụ, chi phí bản quyền. (Cần Finance/CEO).
- process: quy trình phát triển, đặt tên nhánh git, họp định kỳ.

ĐỊNH NGHĨA stance:
- propose: đưa ra một phương án/đề xuất. support: ủng hộ/đồng ý với phương án (kể cả "ok", "mình cũng thấy vậy").
- reverse: rút lại/bỏ một phương án đã nêu trước đó ("bỏ Firebase", "đổi ý", "hủy cái đó"). option_id là phương án BỊ rút. Nếu cùng câu chốt phương án mới, tạo thêm một nhãn conclude cho phương án mới.
- conclude: phát biểu KẾT LUẬN rõ ràng ("chốt X", "quyết định X", "vậy làm X"). Gợi ý/nghiêng về/"có lẽ" KHÔNG phải conclude.
- defer: hoãn chủ đề/để lần sau. question: hỏi làm rõ. info: thông tin liên quan không đổi hướng quyết định.
- conditional=true CHỈ khi chính kết luận phụ thuộc điều kiện chưa xảy ra ("chốt B nếu bên X đồng ý"); ghi condition_text.
- Một phát biểu có thể có nhiều nhãn. Phát biểu mơ hồ/không rõ tham chiếu ("như đợt trước đi", "cứ thế đi") KHÔNG gán conclude trừ khi tham chiếu được nêu rõ NGAY trong cuộc họp.
- option_id ổn định xuyên suốt chủ đề; label là tên đặc trưng (ví dụ "Supabase", "Release thứ Hai 19/10"), không dùng "phương án A" chung chung nếu có tên cụ thể.

ĐỊNH NGHĨA items:
- task: việc cần làm. assignee_basis=assigned nếu ai đó GIAO rõ cho người đó; self_accepted nếu người đó tự nhận ("mình nhận", "em làm"); mentioned_only nếu chỉ bị nhắc tên/phỏng đoán ("chắc Nam làm được") -> khi đó để assignee null.
  deadline_text chỉ điền khi hạn được nói cụ thể; chép nguyên văn cụm từ; không suy diễn. Không có thì null.
- issue: vướng mắc/rủi ro đang cản trở. request: yêu cầu (từ khách, PM...). feedback: góp ý/phản hồi. open_question: câu hỏi chưa được trả lời. knowledge: thông tin/quy tắc mới đáng lưu.
- Chỉ tạo mục khi có căn cứ trong transcript; KHÔNG tạo việc từ chính sách hay bối cảnh.

QUY TẮC CHUNG:
- quote phải là chuỗi con nguyên văn của (các) phát biểu được nêu; không sửa chữ, không dịch.
- Bối cảnh (người dự, vai trò, chính sách) chỉ để hiểu tên gọi; không phải bằng chứng.
- Bỏ qua phát biểu xã giao không mang nội dung. Không bịa tên người, ngày, con số."""

EXAMPLE = """VÍ DỤ NGẮN (chủ đề khác, chỉ để minh họa định dạng):
U004 Lan: Mình đề xuất dùng Sendgrid gửi email.   -> {"utterance_id":"U004","topic_id":"T1","option_id":"SG","stance":"propose","quote":"đề xuất dùng Sendgrid"}
U009 Hùng: Thôi bỏ Sendgrid, chốt Amazon SES.     -> hai nhãn: reverse SG (quote "bỏ Sendgrid") và conclude SES (quote "chốt Amazon SES")
U010 Dũng: Chắc Mai gửi báo cáo được nhỉ.          -> task, assignee null, assignee_basis "mentioned_only"
"""


def build_user_prompt(ctx: ContextPack, utts: list[Utterance]) -> str:
    return f"{ctx.to_prompt()}\n\n{EXAMPLE}\n### TRANSCRIPT (mỗi dòng: ID [giờ] Người nói: nội dung)\n{render_for_prompt(utts)}\n\nTrả về JSON."


def label_transcript(backend: str, ctx: ContextPack, utts: list[Utterance]) -> LabelerOutput:
    return generate_json(backend, SYSTEM, build_user_prompt(ctx, utts), LabelerOutput)
