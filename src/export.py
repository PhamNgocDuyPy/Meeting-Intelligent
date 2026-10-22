"""Xuất kết quả: Markdown (đọc), CSV (nhập vào công cụ quản lý việc), JSON (máy đọc)."""
from __future__ import annotations

import csv
import io

from .schema import MeetingResult

KIND_VI = {"task": "Việc cần làm", "issue": "Vướng mắc", "request": "Yêu cầu", "feedback": "Phản hồi",
           "open_question": "Câu hỏi còn mở", "knowledge": "Tri thức mới"}


def to_markdown(r: MeetingResult, approved_only: set[str] | None = None) -> str:
    L = [f"# {r.title or r.meeting_id}", f"*Ngày: {r.date or 'chưa rõ'} · nguồn: {r.backend} · bộ chấm: {r.judge}*", ""]
    for status, heading in (("decided", "Quyết định (Đã chốt)"), ("leaning", "Nghiêng về — cần xác nhận"), ("open", "Chưa chốt")):
        ts = [t for t in r.topics if t.status == status and (approved_only is None or t.topic_id in approved_only)]
        if not ts:
            continue
        L += [f"## {heading}", ""]
        for t in ts:
            opt = t.final_option or t.leaning_option or "—"
            L.append(f"### {t.title} → **{opt}**")
            if t.superseded:
                L.append(f"- Đã bị thay thế: {', '.join(t.superseded)}")
            if t.explanation:
                L.append(f"- {t.explanation}")
            if t.flags:
                L.append(f"- Cờ: {', '.join(t.flags)}")
            if t.decision_journey:
                L.append("- Tiến trình ra quyết định (Decision Journey):")
                for step in t.decision_journey:
                    opt_str = f" [{step.option_label}]" if step.option_label else ""
                    L.append(f"  * **{step.phase_vi}** ({step.ts_label}): {step.speaker} — {step.action}{opt_str} — “{step.quote}” `{step.utterance_id}`")
            else:
                L.append("- Diễn biến:")
                for e in t.timeline:
                    L.append(f"  - [{e.ts_label}] {e.speaker} ({e.stance}{', có điều kiện' if e.conditional else ''}): “{e.quote}” `{e.utterance_id}`")
            L.append("")

    # 1. Kho tri thức tổ chức (Dùng lâu dài)
    k_items = [(i, it) for i, it in enumerate(r.items) if it.kind == "knowledge" and (approved_only is None or f"item{i+1}" in approved_only)]
    if k_items:
        L += ["## Kho Tri Thức Tổ Chức (Dùng Lâu Dài)", ""]
        for _, it in k_items:
            cat_badge = f" `[{it.knowledge_category.upper()}]`" if it.knowledge_category else ""
            L.append(f"- **{it.title}**{cat_badge}  \n  “{it.quote}” `{', '.join(it.utterance_ids)}`" + (f"  \n  Cờ: {', '.join(it.flags)}" if it.flags else ""))
        L.append("")

    # 2. Bảng công việc tác nghiệp (Sprint / Dự án)
    op_items = [(i, it) for i, it in enumerate(r.items) if it.kind in ("task", "request") and (approved_only is None or f"item{i+1}" in approved_only)]
    if op_items:
        L += ["## Bảng Công Việc Tác Nghiệp (Sprint / Dự Án)", ""]
        for _, it in op_items:
            extra = ""
            if it.kind == "task":
                extra = f" — người nhận: **{it.assignee or 'chưa xác định'}** · hạn: **{it.deadline_date or it.deadline_text or 'chưa xác định'}**"
            L.append(f"- **[{KIND_VI[it.kind]}]** {it.title}{extra}  \n  “{it.quote}” `{', '.join(it.utterance_ids)}`" + (f"  \n  Cờ: {', '.join(it.flags)}" if it.flags else ""))
        L.append("")

    # 3. Vấn đề chưa chốt & Tắc nghẽn
    unresolved_items = [(i, it) for i, it in enumerate(r.items) if it.kind in ("open_question", "issue", "feedback") and (approved_only is None or f"item{i+1}" in approved_only)]
    if unresolved_items:
        L += ["## Vấn Đề Chưa Chốt & Tắc Nghẽn (Cần Làm Rõ)", ""]
        for _, it in unresolved_items:
            L.append(f"- **[{KIND_VI[it.kind]}]** {it.title}  \n  “{it.quote}” `{', '.join(it.utterance_ids)}`" + (f"  \n  Cờ: {', '.join(it.flags)}" if it.flags else ""))
        L.append("")
    return "\n".join(L)


def tasks_csv(r: MeetingResult, approved_only: set[str] | None = None) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["title", "assignee", "deadline_date", "deadline_text", "evidence_ids", "quote", "flags"])
    for i, it in enumerate(r.items):
        if it.kind != "task" or (approved_only is not None and f"item{i+1}" not in approved_only):
            continue
        w.writerow([it.title, it.assignee or "chưa xác định", it.deadline_date or "", it.deadline_text or "",
                    " ".join(it.utterance_ids), it.quote, ";".join(it.flags)])
    return buf.getvalue()


def decisions_jsonl(r: MeetingResult, approved_only: set[str] | None = None,
                    approved_by: str | None = None, approved_at: str | None = None) -> str:
    """Hợp đồng dữ liệu sẵn sàng cho kho tri thức (Data Contract).
    Xuất mỗi quyết định thành 1 dòng JSON Lines chuẩn hóa để các kho dữ liệu (SQL/Graph) nạp vào.
    """
    import json
    lines = []
    for t in r.topics:
        if approved_only is not None and t.topic_id not in approved_only:
            continue
        entry = {
            "decision_id": f"{r.meeting_id}_{t.topic_id}",
            "topic_title": t.title,
            "topic_ref": None,  # Gán bởi người duyệt hoặc hệ thống liên cuộc họp
            "category": t.category,
            "status": t.status,
            "final_option": t.final_option,
            "rejected_options": t.superseded,  # Các phương án bị loại trong cùng cuộc họp
            "supersedes_decision_id": None,    # Khóa ngoại trỏ tới decision_id cũ từ cuộc họp trước
            "valid_from": r.date,
            "valid_to": None,                  # null khi còn hiệu lực; ghi nhận ngày hết hạn khi bị thay thế sau này
            "evidence_utterance_ids": t.evidence_ids,
            "approved_by": approved_by,        # null cho tới khi con người duyệt qua UI
            "approved_at": approved_at,        # null cho tới khi con người duyệt qua UI
            "flags": t.flags,
            "meeting_id": r.meeting_id,
        }
        lines.append(json.dumps(entry, ensure_ascii=False))
    return "\n".join(lines) + ("\n" if lines else "")
