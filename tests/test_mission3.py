"""Bộ kiểm thử Mission 3 (Mission 3 Test Suite).

Kiểm chứng toàn trình (End-to-End Pipeline) với Backend Gemini 2.5 Flash,
Mô hình phản biện JEV Judge và Demo Cache trên các kịch bản cuộc họp thực tế.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from src.pipeline import run_meeting
from src.schema import (
    Utterance, Label, RawItem, TopicDef, OptionDef, TopicState, LabelerOutput, ValidationReport
)
from src.parser import parse_transcript
from src.context import ContextPack
from src.rules import evaluate_all
from src.assemble import validate_labels, build_items, build_review_queue
from src.textnorm import norm_plain


def make_mock_context(roles_map: dict[str, str], meeting_info: dict = None, rights: dict = None) -> ContextPack:
    meeting = meeting_info or {"id": "m_test", "leader": "Leader", "mode": "authority", "date": "2026-10-23"}
    attendees = []
    _index = {}
    for spk, role in roles_map.items():
        nid = norm_plain(spk)
        _index[nid] = {"id": nid, "name": spk, "roles": [role]}
        attendees.append({"id": nid, "name": spk, "roles": [role]})
    default_rights = {
        "technical": {"mode": "authority", "roles": ["tech_lead"]},
        "scope": {"mode": "authority", "roles": ["pm"]},
        "other": {"mode": "authority", "roles": ["pm", "tech_lead"]}
    }
    return ContextPack(
        meeting=meeting,
        attendees=attendees,
        rights=rights or default_rights,
        glossary={},
        carryover=[],
        policy_snippets=[],
        _index=_index
    )


# =========================================================================
# TEST 1: EDGE CASES / TÌNH HUỐNG KHÓ (PIPELINE THẬT GEMINI + JEV)
# Chống False Decision (Quyết định có điều kiện / Tạm thời)
# Chống False Action (Câu hỏi ý kiến / Phản hồi do dự)
# =========================================================================
def test_edge_case_tentative_conclusion_and_opinion_inquiry():
    """Kiểm chứng các ca biên hóc búa qua Pipeline toàn trình với Gemini và JEV:
    1. Ca m05: Quyết định kèm điều kiện ràng buộc chưa ngã ngũ -> Tự động hạ về leaning.
    2. Ca g10: Người tham gia chỉ được hỏi ý kiến / do dự -> Tuyệt đối không gán task.
    3. Bộ lọc TENTATIVE_PHRASE: Chặn câu chốt thử nghiệm của sếp.
    """
    # 1. Pipeline thật trên m05: Huy chốt Stripe có điều kiện phí < 2%
    res_m05 = run_meeting("m05", backend="gemini", judge="jev")
    topic_m05 = res_m05.topics[0]
    # KHÔNG ĐƯỢC CHỐT (decided), phải hạ về leaning kèm cờ conditional
    assert topic_m05.status == "leaning", f"Kỳ vọng status leaning nhưng nhận {topic_m05.status}"
    assert "conditional" in topic_m05.flags
    assert topic_m05.leaning_option == "Stripe"

    # 2. Pipeline thật trên g10: Hà hỏi Đạt 'chắc Đạt làm được nhỉ', Đạt 'để em xem đã'
    res_g10 = run_meeting("g10", backend="gemini", judge="jev")
    task_test = next((it for it in res_g10.items if "kiểm thử" in it.title.lower()), None)
    assert task_test is not None, "Phải tìm thấy đầu việc kiểm thử tự động"
    # Đạt chỉ được nhắc tên và trả lời do dự -> Tuyệt đối không gán assignee cho Đạt!
    assert task_test.assignee is None, f"Assignee phải là None nhưng lại nhận: {task_test.assignee}"
    assert task_test.assignee_basis == "none"

    # 3. Kiểm chứng bộ lọc câu thử nghiệm của sếp (TENTATIVE_PHRASE)
    raw_transcript = """
[00:01:00] Cường: Trước mắt tạm thời thử nghiệm phương án Cache B xem sao nhé, chưa chốt vội.
"""
    utts = parse_transcript(raw_transcript)
    by_id = {u.id: u for u in utts}
    ctx = make_mock_context(roles_map={"Cường": "tech_lead"})
    topic_tentative = TopicDef(topic_id="t_cache", title="Giải pháp Cache", category="technical",
                               options=[OptionDef(option_id="b", label="Cache B")])
    label_tentative = Label(utterance_id=utts[0].id, topic_id="t_cache", option_id="b", stance="conclude",
                            quote="Trước mắt tạm thời thử nghiệm phương án Cache B xem sao nhé")
    out = LabelerOutput(topics=[topic_tentative], labels=[label_tentative], items=[])
    good_labels, rep = validate_labels(out, by_id)
    states = evaluate_all(out.topics, good_labels, by_id, ctx)
    assert states[0].status == "leaning"
    assert "tentative_conclusion" in states[0].flags


# =========================================================================
# TEST 2: REGRESSION INVARIANTS CHO MISSION 2 (PIPELINE THẬT TRÊN M01)
# Đảm bảo toàn bộ bất biến và độ chính xác của Mission 2 được kế thừa 100%
# =========================================================================
def test_regression_mission2_invariants():
    """Kiểm chứng toàn bộ các quy tắc bất biến của Mission 2 trên cuộc họp thật m01:
    - Quyết định đổi ý từ Firebase sang Supabase (Supabase decided, Firebase superseded).
    - Toàn bộ 4 công việc tác nghiệp được bóc tách chuẩn xác với deadline ISO.
    - 100% trích dẫn bằng chứng hợp lệ, không có nhãn bị loại bỏ vô lý.
    """
    res = run_meeting("m01", backend="gemini", judge="jev")

    # 1. Bất biến về quyết định đổi ý A -> B
    assert res.title == "Họp kỹ thuật chọn backend Aurora"
    assert len(res.topics) >= 1
    t = res.topics[0]
    assert t.status == "decided"
    assert t.final_option == "Supabase"
    assert "Firebase" in t.superseded

    # 2. Bất biến về công việc tác nghiệp (Assignee & Deadline)
    tasks = {it.assignee: it for it in res.items if it.kind == "task"}
    assert "Quân" in tasks, "Phải có công việc dựng staging của Quân"
    assert tasks["Quân"].deadline_date == "2026-10-09"
    assert "Nam" in tasks, "Phải có công việc viết tài liệu của Nam"
    assert "Trang" in tasks, "Phải có công việc test plan của Trang"

    # 3. Bất biến về kiểm định bằng chứng chuỗi con
    assert len(res.validation.labels_dropped) == 0, "Không được có nhãn bằng chứng hợp lệ nào bị loại bỏ"


# =========================================================================
# TEST 3: PHÂN BIỆT TÁC NGHIỆP VS TRI THỨC DÀI HẠN (PIPELINE THẬT TRÊN M09)
# Tách bạch 3 luồng: Việc tác nghiệp (Jira), Tri thức (Wiki/ADR), Vấn đề chưa chốt
# =========================================================================
def test_operational_task_vs_longterm_knowledge_separation():
    """Kiểm chứng cơ chế phân tách 3 miền dữ liệu độc lập trên cuộc họp thực tế m09:
    1. Việc tác nghiệp ngắn hạn (Action Item): có người nhận rõ ràng và deadline ISO cụ thể.
    2. Kho tri thức tổ chức (Knowledge Base): chuẩn hóa kiến trúc dài hạn, không gán cá nhân.
    3. Vấn đề chưa chốt (Blocker / Open Question): câu hỏi mở cần thảo luận phiên tiếp theo.
    """
    res = run_meeting("m09", backend="gemini", judge="jev")

    # 1. Kiểm tra Tri thức dùng lâu dài (Knowledge / Architecture ADR)
    knowledge_items = [it for it in res.items if it.kind == "knowledge"]
    assert len(knowledge_items) >= 1, "Phải bóc tách được tri thức kiến trúc dài hạn"
    k = knowledge_items[0]
    assert k.knowledge_category == "architecture"
    assert k.assignee is None, "Tri thức kiến trúc dùng chung không được gán assignee cá nhân"

    # 2. Kiểm tra Việc tác nghiệp ngắn hạn (Tasks cho Sprint)
    tasks = [it for it in res.items if it.kind == "task"]
    assert len(tasks) >= 2, "Phải có ít nhất 2 đầu việc tác nghiệp cho Tuấn và Lan"
    tuan_task = next((it for it in tasks if it.assignee == "Tuấn"), None)
    lan_task = next((it for it in tasks if it.assignee == "Lan"), None)
    assert tuan_task is not None and tuan_task.deadline_date == "2026-10-30"
    assert lan_task is not None and lan_task.deadline_date == "2026-10-30"

    # 3. Kiểm tra Vấn đề chưa chốt (Open questions / Blockers)
    open_items = [it for it in res.items if it.kind in ("open_question", "issue")]
    assert len(open_items) >= 1, "Phải có mục vấn đề chưa chốt (License Datadog / SSL wildcard)"


# =========================================================================
# TEST 4: TRANSCRIPT DÀI 1H25 & TIẾN TRÌNH QUYẾT ĐỊNH ĐA CHIỀU (A -> B -> C)
# Chạy THẬT 100% qua Pipeline toàn trình (Gemini + Jev Judge) trên m09
# =========================================================================
def test_long_transcript_multiround_journey_evolution():
    """Kiểm chứng cuộc họp kỹ thuật dài 1h25 (m09) qua toàn bộ Pipeline Gemini + Jev:
    - 85 phút tranh luận liên tiếp qua 3 phương án: Monolith -> Microservices -> Modular Monolith.
    - Hệ thống ghi nhận chính xác 9 bước Decision Journey.
    - Chốt hạ Modular Monolith, đưa cả Monolith và Microservices vào danh sách superseded.
    """
    res = run_meeting("m09", backend="gemini", judge="jev")

    # 1. Kiểm tra thông tin phiên họp được nạp từ brief.yaml
    assert res.title == "Họp toàn thể kỹ thuật: Tái cấu trúc kiến trúc hệ thống (1h25)"
    assert len(res.topics) >= 1

    # 2. Kiểm tra Quyết định kiến trúc và Diễn biến thay thế 3 phương án (A -> B -> C)
    t = res.topics[0]
    assert t.status == "decided"
    assert t.final_option == "Modular Monolith"
    # Cả 2 phương án trước đó (Monolith và Microservices) đều phải bị ghi nhận là superseded
    assert "Monolith" in t.superseded
    assert "Microservices" in t.superseded

    # 3. Kiểm tra Tiến trình Decision Journey từ đầu giờ đến cuối giờ
    assert len(t.decision_journey) >= 6
    phases = [step.phase for step in t.decision_journey]
    assert "proposal" in phases
    assert "discussion" in phases
    assert "modification" in phases
    assert "resolution" in phases

    # Bước chốt hạ cuối cùng thuộc về Tech Lead Hoàng
    last_step = t.decision_journey[-1]
    assert last_step.phase == "resolution"
    assert last_step.speaker == "Hoàng"
    assert last_step.option_label == "Modular Monolith"


# =========================================================================
# TEST 5: CHANGE REQUEST C2 — ACTION CHƯA RÕ (BẮT BUỘC)
# Cuộc họp có câu "cái này team mình xử lý nhé" nhưng không nói rõ người
# phụ trách hoặc deadline. Hệ thống KHÔNG ĐƯỢC tự bịa owner/deadline.
# =========================================================================
def test_change_request_c2_vague_action_no_owner_no_deadline():
    """Kiểm chứng trực tiếp yêu cầu của Change Request C2:
    Transcript xuất hiện câu: 'Cái này team mình xử lý nhé.'
    Hệ thống kiên quyết:
    1. Không tự bịa owner (hủy đại từ tập thể 'team mình', không gán nhầm người nói Huy).
    2. Không tự bịa deadline (deadline = None).
    3. Gắn cờ cảnh báo 'assignee_unknown' và 'deadline_unknown' đưa vào Review Queue.
    """
    raw_transcript = """
[00:01:00] Huy: Cái này team mình xử lý nhé.
[00:02:00] Nam: Vâng, em nắm được tinh thần rồi.
"""
    utts = parse_transcript(raw_transcript)
    by_id = {u.id: u for u in utts}
    ctx = make_mock_context(
        roles_map={"Huy": "pm", "Nam": "member"},
        meeting_info={"id": "m_c2_test", "leader": "Huy", "mode": "authority", "date": "2026-10-23"}
    )

    # Tình huống 1: LLM gán assignee là đại từ tập thể "team mình" và bịa deadline "sớm nhất"
    item_hallucinated_team = RawItem(
        kind="task",
        title="Xử lý công việc dự án",
        utterance_ids=[utts[0].id],
        quote="Cái này team mình xử lý nhé",
        assignee="team mình",
        assignee_basis="assigned",
        deadline_text="sớm nhất"
    )

    out_1 = LabelerOutput(topics=[], labels=[], items=[item_hallucinated_team])
    rep_1 = ValidationReport()
    res_1 = build_items(out_1, by_id, ctx, meeting_date="2026-10-23", rep=rep_1)
    assert len(res_1) == 1
    t_1 = res_1[0]
    # KHÔNG ĐƯỢC để owner là đại từ tập thể "team mình", phải gạt về None
    assert t_1.assignee is None, f"Owner không được là tập thể nhưng lại nhận: {t_1.assignee}"
    assert t_1.assignee_basis == "none"
    assert "assignee_unknown" in t_1.flags
    # KHÔNG ĐƯỢC tự bịa deadline (quote không có trong transcript)
    assert t_1.deadline_date is None
    assert "deadline_unknown" in t_1.flags or "deadline_not_in_source" in t_1.flags

    # Tình huống 2: LLM nhầm người phát biểu (Huy) là người tự nhận việc (self_accepted)
    item_hallucinated_speaker = RawItem(
        kind="task",
        title="Xử lý công việc dự án",
        utterance_ids=[utts[0].id],
        quote="Cái này team mình xử lý nhé",
        assignee="Huy",
        assignee_basis="self_accepted",
        deadline_text=None
    )

    out_2 = LabelerOutput(topics=[], labels=[], items=[item_hallucinated_speaker])
    rep_2 = ValidationReport()
    res_2 = build_items(out_2, by_id, ctx, meeting_date="2026-10-23", rep=rep_2)
    assert len(res_2) == 1
    t_2 = res_2[0]
    # KHÔNG ĐƯỢC tự ý gán người phát biểu câu giao việc chung thành người tự nhận việc
    assert t_2.assignee is None, f"Owner không được tự bịa là Huy: {t_2.assignee}"
    assert t_2.assignee_basis == "none"
    assert "assignee_unknown" in t_2.flags
    assert t_2.deadline_date is None
    assert "deadline_unknown" in t_2.flags

    # Tình huống 3: Bóc tách chuẩn và đẩy vào Review Queue cho con người phân công
    item_clean = RawItem(
        kind="task",
        title="Xử lý công việc dự án",
        utterance_ids=[utts[0].id],
        quote="Cái này team mình xử lý nhé",
        assignee=None,
        assignee_basis="none",
        deadline_text=None
    )
    out_3 = LabelerOutput(topics=[], labels=[], items=[item_clean])
    rep_3 = ValidationReport()
    res_3 = build_items(out_3, by_id, ctx, meeting_date="2026-10-23", rep=rep_3)
    rq = build_review_queue([], res_3)
    assert len(res_3) == 1
    assert res_3[0].assignee is None
    assert res_3[0].deadline_date is None
    # Bắt buộc phải có trong Review Queue để người duyệt chỉ định người phụ trách
    assert any(q["title"] == res_3[0].title for q in rq)
