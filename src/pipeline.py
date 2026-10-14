"""Luồng chính: transcript + bối cảnh -> nhãn -> kiểm bằng chứng -> luật -> (bộ chấm) -> hàng chờ duyệt."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .assemble import build_items, build_review_queue, validate_labels
from .context import ContextPack, load_context
from .judge import apply_judge, judge_task_assignee, judge_topic
from .labeler import label_transcript
from .parser import parse_transcript
from .rules import evaluate_all
from .schema import LabelerOutput, MeetingResult

ROOT = Path(__file__).resolve().parent.parent
MEETINGS = ROOT / "data" / "meetings"
INDEP_MEETINGS = ROOT / "data" / "independent_tests" / "meetings"


def list_meetings() -> list[str]:
    meetings = [p.name for p in MEETINGS.iterdir() if (p / "transcript.txt").exists()]
    if INDEP_MEETINGS.exists():
        meetings.extend(p.name for p in INDEP_MEETINGS.iterdir() if (p / "transcript.txt").exists())
    return sorted(meetings)


def run_meeting_dir(meeting_dir: Path, backend: str = "gemini", judge: str = "none",
                    judge_mode: str = "downgrade",
                    labeler_out: Optional[LabelerOutput] = None, ctx: Optional[ContextPack] = None,
                    transcript_text: Optional[str] = None,
                    custom_roles: Optional[dict[str, str]] = None) -> MeetingResult:
    meeting_dir = Path(meeting_dir)
    raw = transcript_text if transcript_text is not None else (meeting_dir / "transcript.txt").read_text(encoding="utf-8")
    utts = parse_transcript(raw)
    by_id = {u.id: u for u in utts}
    ctx = ctx or load_context(ROOT, meeting_dir, custom_roles=custom_roles)

    out = labeler_out if labeler_out is not None else label_transcript(backend, ctx, utts)
    labels, rep = validate_labels(out, by_id)
    topics = evaluate_all(out.topics, labels, by_id, ctx)
    # Lỗ hổng 7: Nếu có nhãn phủ định bị mất hẳn (utterance_id không tồn tại), hạ decided về leaning để an toàn
    if any(d.get("negative") and d.get("reason") == "utterance_id_not_found" for d in rep.labels_dropped):
        for t in topics:
            if t.status == "decided":
                t.status, t.status_vi = "leaning", "Nghiêng về"
                t.needs_confirmation = True
                if "negative_label_lost" not in t.flags:
                    t.flags.append("negative_label_lost")
                t.explanation += " [Có nhãn phản đối/đảo ngược bị thất lạc ID phát biểu -> hạ về Nghiêng về]"

    if judge != "none":
        for t in topics:
            if t.status in ("decided", "leaning") and any(e.stance == "conclude" for e in t.timeline):
                try:
                    verdict = judge_topic(judge, t, utts, ctx)
                    if verdict is not None:
                        dg = apply_judge(t, verdict, mode=judge_mode)
                        if dg and dg.get("mode") == "downgrade":
                            rep.downgrades.append({"item": t.title, "field": "status", "value": "decided", "reason": ",".join(dg["reasons"])})
                        elif dg and dg.get("mode") == "advisory":
                            rep.downgrades.append({"item": t.title, "field": "status_flag", "value": "advisory_flag", "reason": ",".join(dg["reasons"])})
                except Exception as e:  # bộ chấm lỗi không được làm hỏng kết quả luật
                    t.flags.append(f"judge_error:{type(e).__name__}")

    meeting_date = ctx.meeting.get("date")
    items = build_items(out, by_id, ctx, meeting_date, rep)

    if judge != "none":
        for it in items:
            if it.kind == "task" and it.assignee:
                cited_utts = [by_id[u] for u in it.utterance_ids if u in by_id]
                cited_text = " ".join(f"{u.speaker}: {u.text}" for u in cited_utts)
                try:
                    p_task, act = judge_task_assignee(judge, it.title, it.assignee, cited_text)
                    if act == "drop":
                        rep.downgrades.append({"item": it.title, "field": "assignee", "value": it.assignee, "reason": f"judge_rejected:p={p_task:.2f}"})
                        it.assignee = None
                        it.flags.append("judge_assignee_dropped")
                    elif act == "confirm":
                        it.flags.append("assignee_needs_confirm")
                except Exception as e:
                    it.flags.append(f"judge_task_error:{type(e).__name__}")

    return MeetingResult(meeting_id=ctx.meeting.get("id", meeting_dir.name), title=ctx.meeting.get("title", ""),
                         date=meeting_date, backend=backend, judge=judge, topics=topics, items=items,
                         validation=rep, review_queue=build_review_queue(topics, items), transcript=utts)


def run_meeting(meeting_id: str, backend: str = "gemini", judge: str = "none",
                judge_mode: str = "downgrade", oracle: bool = False,
                custom_roles: Optional[dict[str, str]] = None) -> MeetingResult:
    d = MEETINGS / meeting_id
    if not d.exists() and (INDEP_MEETINGS / meeting_id).exists():
        d = INDEP_MEETINGS / meeting_id
    lo = None
    if oracle:
        oracle_file = d / "labels_oracle.json"
        if oracle_file.exists():
            lo = LabelerOutput.model_validate(json.loads(oracle_file.read_text(encoding="utf-8")))
            backend = "oracle"
    return run_meeting_dir(d, backend=backend, judge=judge, judge_mode=judge_mode, labeler_out=lo, custom_roles=custom_roles)
