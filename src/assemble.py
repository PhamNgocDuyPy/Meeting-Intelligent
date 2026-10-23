"""Kiểm tra và hợp nhất đầu ra của bộ gán nhãn: bỏ mọi thứ không có căn cứ trong transcript."""
from __future__ import annotations

import re

from .context import ContextPack
from .dates import resolve_deadline
from .evidence import quote_in_text, validate_item_source, validate_label
from .schema import ItemOut, Label, LabelerOutput, TopicDef, Utterance, ValidationReport
from .textnorm import contains_word, normalize

NEGATIVE = {"reverse", "oppose", "defer"}
HEDGE = re.compile(r"\b(chắc|có lẽ|hình như|nhỉ|không biết|để (mình |em |anh |chị )?xem|thử xem|chưa chắc)\b", re.IGNORECASE)
OPINION_INQUIRY = re.compile(r"\b(nghĩ sao|thấy sao|ý kiến gì|thấy thế nào|nghĩ thế nào|có biết|có nhớ|chia sẻ|nhắc đến|từng làm|quan điểm|có rảnh|rảnh không)\b", re.IGNORECASE)
COLLECTIVE_ASSIGNEE = re.compile(r"^(team|nhóm|team mình|nhóm mình|cả team|cả nhóm|chúng ta|chúng tôi|chúng mình|mọi người|anh em|các bạn|ai đó|bên mình|toàn đội)$", re.IGNORECASE)
COLLECTIVE_DELEGATION = re.compile(r"\b(team|nhóm|cả team|cả nhóm|chúng ta|chúng mình|mọi người|anh em)\s+(mình\s+)?(xử lý|làm|lo|chạy|triển khai|phụ trách|follow|gánh|bàn|giải quyết)\b", re.IGNORECASE)
PERSONAL_COMMITMENT = re.compile(r"(?<!team\s)(?<!nhóm\s)(?<!cả\s)(?<!bên\s)\b(tôi|mình|em|anh|chị)\s+(sẽ|nhận|làm|lo|phụ trách|đảm nhiệm|triển khai|xử lý)\b|\bđể\s+(tôi|mình|em|anh|chị)\b", re.IGNORECASE)


def _categorize_knowledge(title: str, text: str) -> str:
    combined = f"{title} {text}".lower()
    if re.search(r"\b(kiến trúc|microservice|cluster|database|postgres|redis|grpc|api|schema|ha|failover)\b", combined):
        return "architecture"
    elif re.search(r"\b(quy định|chính sách|quy trình|tuân thủ|bảo mật|quy ước)\b", combined):
        return "policy"
    elif re.search(r"\b(bài học|kinh nghiệm|lưu ý|sự cố|postmortem|rút kinh nghiệm)\b", combined):
        return "lesson_learned"
    return "general"


def validate_labels(out: LabelerOutput, by_id: dict[str, Utterance]) -> tuple[list[Label], ValidationReport]:
    rep = ValidationReport(labels_total=len(out.labels), items_total=len(out.items))
    good: list[Label] = []
    for lb in out.labels:
        ok, why = validate_label(lb, by_id)
        if ok:
            good.append(lb)
            continue
        rep.labels_dropped.append({
            "utterance_id": lb.utterance_id,
            "stance": lb.stance,
            "quote": lb.quote,
            "reason": why,
            "negative": lb.stance in NEGATIVE,
        })
        # Lỗ hổng 7: nhãn mang bằng chứng phủ định (reverse, oppose, defer)
        # nếu utterance_id có thật nhưng quote bị lệch/không khớp chuỗi con,
        # GIỮ LẠI nhãn và đánh dấu quote_unverified=True để hạ cấp an toàn (không để chủ đề bị chốt nhầm).
        if lb.stance in NEGATIVE and why == "quote_not_in_utterance":
            u = by_id.get(lb.utterance_id)
            if u:
                good.append(lb.model_copy(update={"quote": u.text, "quote_unverified": True}))
    rep.labels_valid = len(good)
    return good, rep


def _same_person(a: str, b: str, ctx: ContextPack) -> bool:
    pa, pb = ctx.person(a), ctx.person(b)
    if pa and pb:
        return pa.get("id") == pb.get("id")
    return normalize(a) == normalize(b)


def assignment_ok(it, utts_list: list[Utterance], by_id: dict[str, Utterance], ctx: ContextPack) -> bool:
    """Lỗ hổng 8 - Lớp 1: Kiểm tra cấu trúc câu giao việc để chặn 'chỉ bị nhắc tên'.
    Nếu câu có từ do dự (HEDGE) hoặc là câu hỏi, hoặc chính người đó trả lời do dự ở 2 câu tiếp theo -> không phải giao việc.
    """
    cited = [by_id[u] for u in it.utterance_ids if u in by_id]
    if not cited:
        return False
    # 1) câu nêu tên người nhận bởi người khác mà có từ do dự, hỏi ý kiến hoặc là câu hỏi -> chỉ nhắc tên
    for u in cited:
        if contains_word(u.text, it.assignee) and not _same_person(u.speaker, it.assignee, ctx):
            norm_text = normalize(u.text)
            if HEDGE.search(norm_text) or OPINION_INQUIRY.search(norm_text) or u.text.rstrip().endswith("?"):
                return False
    # 2) trong 2 phát biểu kế tiếp, chính người đó trả lời do dự hoặc từ chối -> chưa nhận
    last = max(u.idx for u in cited)
    next_utts = [u for u in utts_list if last < u.idx <= last + 2]
    for u in next_utts:
        if _same_person(u.speaker, it.assignee, ctx):
            norm_u = normalize(u.text)
            if HEDGE.search(norm_u) or OPINION_INQUIRY.search(norm_u) or re.search(r"\b(không làm được|bận|chưa nhận|khó lắm|chưa rõ)\b", norm_u):
                return False
    return True


def build_items(out: LabelerOutput, by_id: dict[str, Utterance], ctx: ContextPack,
                meeting_date: str | None, rep: ValidationReport) -> list[ItemOut]:
    items: list[ItemOut] = []
    seen: set[tuple[str, str]] = set()
    utts_list = sorted(by_id.values(), key=lambda u: u.idx)
    for it in out.items:
        ok, why = validate_item_source(it, by_id)
        if not ok:
            rep.items_dropped.append({"title": it.title, "kind": it.kind, "reason": why})
            continue
        key = (it.kind, normalize(it.title))
        if key in seen:
            continue
        seen.add(key)
        flags: list[str] = []
        cited = [by_id[u] for u in it.utterance_ids]
        cited_text = " ".join(u.text for u in cited)
        assignee, basis = it.assignee, it.assignee_basis
        deadline_text, deadline_date = it.deadline_text, None

        if it.kind == "task":
            # --- Chặn đại từ tập thể ("team mình", "cả nhóm") làm assignee ---
            if assignee and COLLECTIVE_ASSIGNEE.match(assignee.strip()):
                rep.downgrades.append({"item": it.title, "field": "assignee", "value": assignee, "reason": "collective_not_individual"})
                assignee, basis = None, "none"

            # --- người nhận: phải được giao hoặc tự nhận rõ ràng; chỉ bị nhắc tên là chưa đủ ---
            if assignee and basis in ("assigned", "self_accepted"):
                if basis == "self_accepted":
                    is_speaker = any(_same_person(u.speaker, assignee, ctx) for u in cited)
                    is_collective = any(COLLECTIVE_DELEGATION.search(normalize(u.text)) for u in cited)
                    has_personal = any(PERSONAL_COMMITMENT.search(normalize(u.text)) for u in cited)
                    if is_speaker and is_collective and not has_personal:
                        # Câu kiểu "cái này team mình xử lý nhé" -> không phải tự nhận cá nhân
                        verified = False
                        rep.downgrades.append({"item": it.title, "field": "assignee", "value": assignee, "reason": "collective_delegation_not_self_accepted"})
                    else:
                        verified = is_speaker
                else:
                    verified = contains_word(cited_text, assignee) or any(_same_person(u.speaker, assignee, ctx) for u in cited)
                
                # Lỗ hổng 8: Chặn câu hỏi do dự và nhắc tên vu vơ
                if verified and basis == "assigned":
                    if not assignment_ok(it, utts_list, by_id, ctx):
                        verified = False
                        rep.downgrades.append({"item": it.title, "field": "assignee", "value": assignee, "reason": "hedged_or_interrogative"})
                        flags.append("assignee_only_mentioned")
                        assignee, basis = None, "none"

                if not verified and basis != "none":
                    rep.downgrades.append({"item": it.title, "field": "assignee", "value": assignee, "reason": "name_not_in_cited_text"})
                    flags.append("assignee_unverified")
                    assignee, basis = None, "none"
            else:
                if assignee:
                    flags.append("assignee_only_mentioned")
                    rep.downgrades.append({"item": it.title, "field": "assignee", "value": assignee, "reason": basis})
                assignee, basis = None, "none"
            if assignee is None:
                flags.append("assignee_unknown")
            # --- hạn: chỉ ghi khi nêu cụ thể trong nguồn ---
            if deadline_text:
                if quote_in_text(deadline_text, cited_text):
                    deadline_date = resolve_deadline(deadline_text, meeting_date)
                    if deadline_date is None:
                        flags.append("deadline_not_precise")
                else:
                    rep.downgrades.append({"item": it.title, "field": "deadline", "value": deadline_text, "reason": "text_not_in_source"})
                    flags.append("deadline_not_in_source")
                    deadline_text = None
            else:
                flags.append("deadline_unknown")
        else:
            assignee, basis, deadline_text = None, "none", None

        k_cat = _categorize_knowledge(it.title, cited_text) if it.kind == "knowledge" else None
        prio = {"task": 1 if assignee else 2, "issue": 2, "request": 2}.get(it.kind, 3)
        items.append(ItemOut(kind=it.kind, title=it.title, detail=it.detail, utterance_ids=it.utterance_ids, quote=it.quote,
                             assignee=assignee, assignee_basis=basis, deadline_text=deadline_text,
                             deadline_date=deadline_date, flags=flags, priority=prio, knowledge_category=k_cat))
    rep.items_valid = len(items)
    return items


def build_review_queue(topics, items) -> list[dict]:
    q: list[dict] = []
    for t in topics:
        if t.status == "decided":
            pr = 1
        elif t.status == "leaning":
            pr = 1
        else:
            pr = 2
        q.append({"type": "topic", "id": t.topic_id, "title": t.title, "priority": pr, "status": t.status_vi,
                  "flags": t.flags})
    for i, it in enumerate(items):
        q.append({"type": it.kind, "id": f"item{i+1}", "title": it.title, "priority": it.priority,
                  "status": "cần duyệt", "flags": it.flags})
    q.sort(key=lambda x: x["priority"])
    return q
