"""Bộ chấm câu hỏi hẹp có/không (Jev hoặc Gemini đối chứng). KHÔNG tự cập nhật trạng thái chủ đề.

Chỉ được dùng để HẠ cấp "Đã chốt" -> "Nghiêng về" khi bộ chấm không đồng ý với luật (an toàn hơn).
Không bao giờ dùng để NÂNG cấp một chủ đề lên "Đã chốt".
"""
from __future__ import annotations

from .context import ContextPack
from .llm import call_jev, generate_json
from .parser import render_for_prompt
from .schema import JudgeAnswer, JudgeVerdict, TopicState, Utterance

# Prompt cho Gemini fallback (khi backend != "jev")
SYSTEM = """Bạn là bộ chấm thận trọng cho biên bản họp. Bạn nhận một chủ đề, phương án ứng viên và các phát biểu liên quan.
Với mỗi câu hỏi, hãy đánh giá và trả về duy nhất xác suất 'p' (số thực từ 0.0 đến 1.0) rằng câu trả lời đúng là CÓ, kèm lý do ngắn gọn.
Trả về JSON đúng cấu trúc sau (hệ thống sẽ tự tính kết luận CÓ khi p >= 0.5):
{
  "explicit_conclusion": {"p": float, "why": "ngắn"},
  "objection_remaining": {"p": float, "why": "ngắn"},
  "reversed_later": {"p": float, "why": "ngắn"},
  "conditional": {"p": float, "why": "ngắn"},
  "authority_ok": {"p": float, "why": "ngắn"}
}
Định nghĩa câu hỏi (p = xác suất câu trả lời đúng là CÓ):
- explicit_conclusion: xác suất có phát biểu KẾT LUẬN rõ ràng chọn đúng phương án ứng viên (đề xuất/gợi ý/nghiêng về KHÔNG tính)?
- objection_remaining: sau khi kết luận, xác suất còn ai phản đối mà chưa được giải quyết?
- reversed_later: sau khi kết luận, xác suất có phát biểu đảo ngược hoặc đổi sang phương án khác?
- conditional: xác suất việc chốt bị ràng buộc bởi điều kiện tiên quyết chưa được đáp ứng trước khi quyết định có hiệu lực? (Không tính kế hoạch triển khai sau khi đã chốt).
- authority_ok: xác suất người kết luận có thẩm quyền chốt loại quyết định này theo danh sách người có thẩm quyền được cung cấp?
Nếu không đủ căn cứ, chọn p gần 0.5."""


def _build_state(state: TopicState, utts: list[Utterance], ctx: ContextPack) -> tuple[str, str, list[Utterance]]:
    """Xây dựng state text và thông tin phụ cho cả Jev lẫn Gemini."""
    cand = state.final_option or state.leaning_option
    cited = {e.utterance_id for e in state.timeline}
    sub = [u for u in utts if u.id in cited or any(abs(u.idx - int(c[1:])) <= 1 for c in cited)]
    auth = ", ".join(ctx.authority_names(state.category)) or "không ai trong cuộc họp"
    state_text = (f"Chủ đề: {state.title} (nhóm: {state.category}, kiểu quyết định: {ctx.mode_for(state.category)})\n"
                  f"Phương án ứng viên: {cand}\nNgười có thẩm quyền trong cuộc họp: {auth}\n\n"
                  f"Các phát biểu liên quan:\n{render_for_prompt(sub)}")
    return state_text, auth, sub


def _judge_jev(state: TopicState, utts: list[Utterance], ctx: ContextPack) -> JudgeVerdict:
    """Gọi Jev trực tiếp: 5 câu noul trong 1 lần gọi API."""
    state_text, auth, _ = _build_state(state, utts, ctx)
    cand = state.final_option or state.leaning_option

    questions = {
        "explicit_conclusion": {
            "type": "noul",
            "instructions": f"Trong các phát biểu được cho, có phát biểu KẾT LUẬN rõ ràng chọn đúng phương án '{cand}' không? (đề xuất/nghiêng về/gợi ý KHÔNG tính)"
        },
        "objection_remaining": {
            "type": "noul",
            "instructions": f"Sau khi kết luận phương án '{cand}', còn ai phản đối mà chưa được giải quyết không?"
        },
        "reversed_later": {
            "type": "noul",
            "instructions": f"Sau khi kết luận phương án '{cand}', có phát biểu đảo ngược hoặc đổi sang phương án khác không?"
        },
        "conditional": {
            "type": "noul",
            "instructions": (
                f"Việc chốt phương án '{cand}' có bị ràng buộc bởi điều kiện tiên quyết (prerequisite) nào "
                f"chưa được đáp ứng trước khi quyết định có hiệu lực không? "
                f"(Chỉ tính điều kiện để phê duyệt quyết định; không tính kế hoạch triển khai sau khi quyết định đã chốt, "
                f"và không tính các câu nói phụ họa hoặc nguyện vọng cá nhân)."
            )
        },
        "authority_ok": {
            "type": "noul",
            "instructions": f"Người kết luận có thẩm quyền chốt loại quyết định này không? Người có thẩm quyền: {auth}"
        },
    }

    resp = call_jev(state_text, questions)
    answers = resp.get("answers", resp)

    def _parse(qid: str, threshold: float = 0.5) -> JudgeAnswer:
        q = answers.get(qid, {})
        p = q.get("noul", q.get("probability", 0.5))
        return JudgeAnswer(answer=p >= threshold, p=p, why=f"jev_p={p:.3f}")

    return JudgeVerdict(
        explicit_conclusion=_parse("explicit_conclusion", threshold=0.5),
        objection_remaining=_parse("objection_remaining", threshold=0.5),
        reversed_later=_parse("reversed_later", threshold=0.5),
        conditional=_parse("conditional", threshold=0.5),
        authority_ok=_parse("authority_ok", threshold=0.5),
    )


def judge_task_assignee(backend: str, item_title: str, assignee: str, cited_text: str) -> tuple[float, str]:
    """Lỗ hổng 8 - Lớp 2: Kiểm tra người nhận việc bằng câu hỏi thứ 6 qua Jev hoặc fallback.
    Chỉ được hạ, không bao giờ nâng: nếu nhãn đã là none thì không hỏi.
      p < 0.4: bỏ người nhận ('drop')
      0.4 <= p <= 0.6: giữ tên nhưng gắn cờ assignee_needs_confirm ('confirm')
      p > 0.6: giữ ('keep')
    """
    if not assignee or backend == "none":
        return 1.0, "keep"

    question_text = f"Trong các phát biểu sau, {assignee} có được giao rõ ràng việc '{item_title}', hoặc chính {assignee} đã nhận làm việc đó chưa?"
    state_text = f"Đoạn trao đổi liên quan đến việc '{item_title}':\n{cited_text}"

    p = 0.5
    if backend == "jev":
        try:
            resp = call_jev(state_text, {"assigned": {"type": "noul", "instructions": question_text + " Trả lời có/không."}})
            answers = resp.get("answers", resp)
            q = answers.get("assigned", {})
            p = q.get("noul", q.get("probability", 0.5))
        except Exception:
            return 0.5, "confirm"
    else:
        try:
            res = generate_json(
                backend,
                "Bạn là bộ chấm kiểm tra việc giao nhiệm vụ trong cuộc họp. "
                "Trả về duy nhất JSON: {\"p\": float, \"why\": \"lý do ngắn\"}, "
                "trong đó 'p' là xác suất (từ 0.0 đến 1.0) rằng câu trả lời đúng là CÓ "
                "(tức người đó đã được giao rõ ràng hoặc tự nhận việc). Không trả về trường answer.",
                f"{state_text}\n{question_text}",
                dict
            )
            p = float(res.get("p", 0.5))
        except Exception:
            return 0.5, "confirm"

    if p < 0.4:
        return p, "drop"
    elif 0.4 <= p <= 0.6:
        return p, "confirm"
    else:
        return p, "keep"


def _judge_gemini(backend: str, state: TopicState, utts: list[Utterance], ctx: ContextPack) -> JudgeVerdict:
    """Fallback: dùng Gemini (hoặc bất kỳ backend text nào) trả JSON."""
    state_text, _, sub = _build_state(state, utts, ctx)
    user = state_text + "\n\nTrả về JSON với trường 'p' (xác suất CÓ từ 0.0 đến 1.0) và 'why' cho từng mục."
    raw = generate_json(backend, SYSTEM, user, dict)

    def _parse(field: str) -> JudgeAnswer:
        item = raw.get(field, {})
        p = float(item.get("p", 0.5))
        ans = p >= 0.5
        why = str(item.get("why", ""))
        return JudgeAnswer(answer=ans, p=p, why=why)

    return JudgeVerdict(
        explicit_conclusion=_parse("explicit_conclusion"),
        objection_remaining=_parse("objection_remaining"),
        reversed_later=_parse("reversed_later"),
        conditional=_parse("conditional"),
        authority_ok=_parse("authority_ok"),
    )


def judge_topic(backend: str, state: TopicState, utts: list[Utterance], ctx: ContextPack) -> JudgeVerdict:
    """Dispatcher: dùng Jev native nếu backend='jev', ngược lại dùng Gemini."""
    if backend == "jev":
        return _judge_jev(state, utts, ctx)
    return _judge_gemini(backend, state, utts, ctx)


def apply_judge(state: TopicState, verdict: JudgeVerdict, mode: str = "downgrade") -> dict | None:
    """Ghi verdict vào state; nếu mode='downgrade' thì hạ cấp, nếu mode='advisory' thì cắm cờ cảnh báo."""
    state.judge = verdict.model_dump()
    if state.status != "decided":
        return None
    reasons = []
    if not verdict.explicit_conclusion.answer:
        reasons.append("judge:not_explicit")
    if verdict.objection_remaining.answer:
        reasons.append("judge:objection_remaining")
    if verdict.reversed_later.answer:
        reasons.append("judge:reversed_later")
    if verdict.conditional.answer:
        reasons.append("judge:conditional")
    if not reasons:
        return None

    state.flags.extend(r for r in reasons if r not in state.flags)
    if mode == "advisory":
        state.needs_confirmation = True
        state.explanation += " [Lưới cảnh báo bộ chấm: " + ", ".join(reasons) + " -> giữ decided nhưng đẩy vào Review Queue để con người xác nhận]"
        return {"topic": state.title, "reasons": reasons, "mode": "advisory"}
    else:
        state.leaning_option, state.final_option = state.final_option, None
        state.status, state.status_vi, state.needs_confirmation = "leaning", "Nghiêng về", True
        state.explanation += " [Bộ chấm không đồng ý: " + ", ".join(reasons) + " -> hạ về Nghiêng về]"
        return {"topic": state.title, "reasons": reasons, "mode": "downgrade"}
