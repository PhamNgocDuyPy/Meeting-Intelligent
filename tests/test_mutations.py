"""Bộ kiểm thử đột biến (Mutation Tests) chứng minh hiệu quả vá lỗ hổng 7 và 8.

1. Test đột biến cho Lỗ hổng 7 (Negative Label Quote Corruption):
   Lấy labels_oracle của m01, cố tình sửa quote của nhãn 'reverse' (bỏ Firebase) thành một chuỗi
   hoàn toàn không có trong transcript ("tôi quyết định quay xe dẹp Firebase ngay").
   Kỳ vọng: Hệ thống KHÔNG được chốt phương án cũ, mà giữ nhãn phủ định ở dạng quote_unverified=True
   và hạ chủ đề về 'leaning' kèm cờ 'unverified_negative_evidence'.

2. Test đột biến cho Lỗ hổng 8 (Adversarial Assignee Hallucination):
   Lấy g10 và m07, cố tình ép assignee="Đạt", assignee_basis="assigned" cho việc kiểm thử tự động (g10),
   và assignee="Nam", assignee_basis="assigned" cho việc xuất file (m07) (giả lập LLM bị ảo giác gán nhầm người nhận).
   Kỳ vọng: Lớp 1 (assignment_ok) phát hiện từ do dự ("chắc", "nhỉ", "để em xem", "để xem")
   và buộc hạ assignee về None kèm cờ 'assignee_only_mentioned'.
"""
import os
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from src.schema import LabelerOutput
from src.parser import parse_transcript
from src.context import load_context
from src.assemble import validate_labels, build_items
from src.rules import evaluate_all
from src.pipeline import run_meeting_dir


def test_mutation_hole_7_corrupted_negative_quote_downgrades_topic():
    """Đột biến 7: Nhãn reverse bị sai quote không được phép làm quyết định cũ bị chốt lọt sổ."""
    m_dir = ROOT / "data/meetings/m01"
    raw_oracle = json.loads((m_dir / "labels_oracle.json").read_text(encoding="utf-8"))
    out = LabelerOutput.model_validate(raw_oracle)

    # Cố tình làm hỏng quote của nhãn reverse
    found_reverse = False
    for lb in out.labels:
        if lb.stance == "reverse":
            lb.quote = "đoạn này bịa đặt hoàn toàn không có trong transcript"
            found_reverse = True
            break
    assert found_reverse is True, "Phải tìm thấy nhãn reverse trong m01 để đột biến"

    utts = parse_transcript(m_dir / "transcript.txt")
    by_id = {u.id: u for u in utts}
    ctx = load_context(ROOT, m_dir)

    labels, rep = validate_labels(out, by_id)
    # Xác nhận nhãn phủ định được giữ lại với cờ quote_unverified
    unverified = [l for l in labels if getattr(l, "quote_unverified", False)]
    assert len(unverified) >= 1, "Nhãn reverse bị sai quote phải được giữ lại và đánh dấu quote_unverified=True"

    topics = evaluate_all(out.topics, labels, by_id, ctx)
    t = topics[0]
    # Chủ đề KHÔNG được là 'decided'
    assert t.status != "decided", f"Chủ đề không được 'decided' khi có bằng chứng phủ định chưa kiểm chứng; thực tế: {t.status}"
    assert "unverified_negative_evidence" in t.flags


def test_mutation_hole_8_adversarial_assignee_g10_dat():
    """Đột biến 8a: Ép g10 Đạt thành 'assigned' -> assignment_ok phải chặn đứng về None."""
    m_dir = ROOT / "data/meetings/g10"
    raw_oracle = json.loads((m_dir / "labels_oracle.json").read_text(encoding="utf-8"))
    out = LabelerOutput.model_validate(raw_oracle)

    # Cố tình gán Đạt là assigned cho việc kiểm thử tự động
    target_item = next(it for it in out.items if "kiểm thử" in it.title.lower())
    target_item.assignee = "Đạt"
    target_item.assignee_basis = "assigned"

    utts = parse_transcript(m_dir / "transcript.txt")
    by_id = {u.id: u for u in utts}
    ctx = load_context(ROOT, m_dir)
    from src.schema import ValidationReport
    rep = ValidationReport()

    items = build_items(out, by_id, ctx, "2026-11-18", rep)
    checked_item = next(it for it in items if "kiểm thử" in it.title.lower())

    # Bắt buộc bị chặn về None
    assert checked_item.assignee is None, f"Assignee phải bị chặn về None; thực tế: {checked_item.assignee}"
    assert "assignee_only_mentioned" in checked_item.flags


def test_mutation_hole_8_adversarial_assignee_m07_nam():
    """Đột biến 8b: Ép m07 Nam thành 'assigned' -> assignment_ok phải chặn đứng về None."""
    m_dir = ROOT / "data/meetings/m07"
    raw_oracle = json.loads((m_dir / "labels_oracle.json").read_text(encoding="utf-8"))
    out = LabelerOutput.model_validate(raw_oracle)

    # Cố tình gán Nam là assigned cho việc xuất file báo cáo
    target_item = next(it for it in out.items if "xuất file" in it.title.lower())
    target_item.assignee = "Nam"
    target_item.assignee_basis = "assigned"

    utts = parse_transcript(m_dir / "transcript.txt")
    by_id = {u.id: u for u in utts}
    ctx = load_context(ROOT, m_dir)
    from src.schema import ValidationReport
    rep = ValidationReport()

    items = build_items(out, by_id, ctx, "2026-10-31", rep)
    checked_item = next(it for it in items if "xuất file" in it.title.lower())

    # Bắt buộc bị chặn về None
    assert checked_item.assignee is None, f"Assignee phải bị chặn về None; thực tế: {checked_item.assignee}"
    assert "assignee_only_mentioned" in checked_item.flags


@pytest.mark.skipif(
    not (os.environ.get("JEV_BASE_URL") and (os.environ.get("OPENCODE_API_KEY") or os.environ.get("JEV_API_KEY"))),
    reason="Yêu cầu API key Jev trong .env để gọi live Jev System One"
)
def test_reverse_mutation_jev_catches_missed_conditional():
    """Đột biến ngược (Phản biện Ý 1): Khi LLM bỏ sót cờ conditional trong m05 và g06.
    - Luật thuần (không Jev) sẽ chốt nhầm 'decided' (lỗi nghiêm trọng).
    - Jev System One đo được p >= 0.5 và hạ cấp về 'leaning' (cứu thành công).
    """
    from src.judge import judge_topic, apply_judge

    for mid in ["m05", "g06"]:
        m_dir = ROOT / f"data/meetings/{mid}"
        raw_oracle = json.loads((m_dir / "labels_oracle.json").read_text(encoding="utf-8"))
        out = LabelerOutput.model_validate(raw_oracle)

        # Cố tình xóa cờ conditional
        for lb in out.labels:
            lb.conditional = False
            lb.condition_text = None

        utts = parse_transcript(m_dir / "transcript.txt")
        by_id = {u.id: u for u in utts}
        ctx = load_context(ROOT, m_dir)
        labels, _ = validate_labels(out, by_id)

        # 1. Luật thuần không có Jev: chốt nhầm decided
        topics_none = evaluate_all(out.topics, labels, by_id, ctx)
        assert topics_none[0].status == "decided", f"Luật thuần phải chốt nhầm khi mất cờ conditional ở {mid}"

        # 2. Có Jev: câu hỏi conditional bắt được và hạ về leaning
        topics_jev = evaluate_all(out.topics, labels, by_id, ctx)
        t_jev = topics_jev[0]
        verdict = judge_topic("jev", t_jev, utts, ctx)
        apply_judge(t_jev, verdict)

        assert t_jev.status == "leaning", f"Jev phải cứu được và hạ về leaning ở {mid}; thực tế: {t_jev.status}"
        assert verdict.conditional.p >= 0.5, f"Xác suất conditional của Jev phải >= 0.5; thực tế: {verdict.conditional.p}"
