"""Bộ kiểm thử Mission 3 (Mission 3 Test Suite).

Bao gồm tối thiểu 3 bài test theo đúng yêu cầu đề bài Mission 3:
1. Test 1 (Edge Case / Tình huống khó):
   - Diễn biến cuộc họp tranh luận phức tạp: Đổi ý từ A sang B (A bị superseded).
   - Câu kết luận mang tính tạm thời / thử nghiệm của sếp ("Trước mắt tạm thời test thử phương án B xem sao") -> Bị hạ về leaning, có cờ tentative_conclusion, không chốt nhầm (Tránh False Decision).
   - Câu hỏi thăm dò ý kiến đồng nghiệp ("Duy ơi bạn thấy thế nào về phương án này?") -> Không biến thành task của Duy (Tránh False Action).
   - Vấn đề chưa chốt ("Vấn đề SSL certificate chưa thống nhất, để tuần sau bàn tiếp") -> Phân loại đúng thành vướng mắc/câu hỏi mở.

2. Test 2 (Regression Test):
   - Đảm bảo toàn bộ các bất biến của Mission 2 vẫn giữ nguyên:
     * Quy tắc 4 điều kiện chốt quyết định.
     * Kiểm tra thẩm quyền ma trận (PM chốt Scope, Tech Lead chốt Tech).
     * Bằng chứng trích dẫn substring bắt buộc (Anti-hallucination).

3. Test 3 (Phân loại Tác nghiệp vs Tri thức lâu dài - Domain Separation):
   - Phân biệt rõ ràng giữa:
     * Task tác nghiệp ngắn hạn (Action Item cho Sprint, có người nhận và deadline).
     * Tri thức tổ chức dùng lâu dài (Knowledge / ADR / Chính sách kiến trúc).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from src.schema import (
    Utterance, Label, RawItem, TopicDef, OptionDef, TopicState, LabelerOutput, ValidationReport
)
from src.parser import parse_transcript
from src.context import ContextPack
from src.rules import evaluate_topic, evaluate_all
from src.assemble import validate_labels, build_items, build_review_queue
from src.textnorm import norm_plain


def make_mock_context(roles_map: dict[str, str], meeting_info: dict = None, rights: dict = None) -> ContextPack:
    meeting = meeting_info or {"id": "m_test", "leader": "Leader", "mode": "authority", "date": "2026-10-21"}
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
# TEST 1: EDGE CASE / TÌNH HUỐNG KHÓ
# Chống False Decision (phát biểu thử nghiệm) + Chống False Action (câu hỏi ý kiến)
# =========================================================================
def test_edge_case_tentative_conclusion_and_opinion_inquiry():
    raw_transcript = """
[00:01:00] An: Tôi đề xuất chúng ta chọn giải pháp Cache A dùng memcached.
[00:02:00] Bình: Tôi phản đối Cache A vì memcached không hỗ trợ cluster tốt, nên chuyển sang Cache B dùng Redis cluster.
[00:03:00] An: Duy ơi bạn thấy thế nào về phương án Cache B này?
[00:03:30] Duy: Tôi thấy Redis cluster khá ổn định nhưng chưa chắc đã đủ tài nguyên.
[00:04:00] Cường: Trước mắt tạm thời thử nghiệm phương án Cache B xem sao nhé, chưa chốt vội.
[00:05:00] Bình: Còn việc cấu hình SSL certificate thì vẫn chưa rõ ai làm, để buổi sau bàn tiếp nhé.
"""
    utts = parse_transcript(raw_transcript)
    by_id = {u.id: u for u in utts}

    # Cường là Tech Lead (có quyền technical)
    ctx = make_mock_context(
        roles_map={"Cường": "tech_lead", "An": "member", "Bình": "member", "Duy": "member"},
        meeting_info={"id": "m_edge_test", "leader": "Cường", "mode": "authority", "date": "2026-10-21"}
    )

    topic_cache = TopicDef(
        topic_id="t_cache",
        title="Lựa chọn giải pháp bộ nhớ đệm Cache",
        category="technical",
        options=[OptionDef(option_id="opt_a", label="Cache A"), OptionDef(option_id="opt_b", label="Cache B")]
    )

    labels = [
        Label(utterance_id=utts[0].id, topic_id="t_cache", option_id="opt_a", stance="propose", quote="đề xuất chúng ta chọn giải pháp Cache A"),
        Label(utterance_id=utts[1].id, topic_id="t_cache", option_id="opt_a", stance="oppose", quote="phản đối Cache A"),
        Label(utterance_id=utts[1].id, topic_id="t_cache", option_id="opt_b", stance="propose", quote="chuyển sang Cache B"),
        # Sếp kết luận nhưng có từ thử nghiệm "Trước mắt tạm thời thử nghiệm"
        Label(utterance_id=utts[4].id, topic_id="t_cache", option_id="opt_b", stance="conclude", quote="Trước mắt tạm thời thử nghiệm phương án Cache B xem sao nhé")
    ]

    items = [
        RawItem(
            kind="task",
            title="Đánh giá phương án Cache B",
            utterance_ids=[utts[2].id],
            quote="Duy ơi bạn thấy thế nào về phương án Cache B này",
            assignee="Duy",
            assignee_basis="assigned"
        ),
        RawItem(
            kind="open_question",
            title="Cấu hình chứng chỉ SSL certificate",
            utterance_ids=[utts[5].id],
            quote="việc cấu hình SSL certificate thì vẫn chưa rõ ai làm, để buổi sau bàn tiếp nhé"
        )
    ]

    labeler_out = LabelerOutput(topics=[topic_cache], labels=labels, items=items)

    # 1. Kiểm chứng Luật đánh giá Quyết định (rules.py)
    good_labels, rep = validate_labels(labeler_out, by_id)
    topic_states = evaluate_all(labeler_out.topics, good_labels, by_id, ctx)
    assert len(topic_states) == 1
    t = topic_states[0]

    # KHÔNG ĐƯỢC CHỐT (decided) vì câu nói của sếp là thử nghiệm / tạm thời
    assert t.status == "leaning", f"Kỳ vọng status là leaning nhưng nhận {t.status}"
    assert "tentative_conclusion" in t.flags
    assert t.needs_confirmation is True
    # Kiểm tra phương án A đã bị superseded / thay thế bởi B
    assert "Cache A" in t.superseded

    # Kiểm tra Decision Journey được ghi nhận chi tiết từng bước
    assert len(t.decision_journey) >= 3
    phases = [s.phase for s in t.decision_journey]
    assert "proposal" in phases
    assert "discussion" in phases
    assert "resolution" in phases

    # 2. Kiểm chứng Chống Giao Việc Nhầm (assemble.py)
    items_out = build_items(labeler_out, by_id, ctx, meeting_date="2026-10-21", rep=rep)
    task_items = [it for it in items_out if it.kind == "task"]
    assert len(task_items) == 1
    # Duy CHỈ BỊ NHẮC TÊN trong câu hỏi ý kiến, KHÔNG PHẢI GIAO VIỆC -> Assignee phải bị huỷ bỏ!
    assert task_items[0].assignee is None, f"Assignee phải bị huỷ nhưng lại là: {task_items[0].assignee}"
    assert "assignee_only_mentioned" in task_items[0].flags

    # 3. Kiểm chứng Vấn đề chưa chốt
    open_items = [it for it in items_out if it.kind == "open_question"]
    assert len(open_items) == 1
    assert "SSL certificate" in open_items[0].title


# =========================================================================
# TEST 2: REGRESSION TEST CHO CÁC BẤT BIẾN MISSION 2
# Đảm bảo các logic cũ không bị phá vỡ sau khi nâng cấp
# =========================================================================
def test_regression_mission2_invariants():
    raw_transcript = """
[00:01:00] Alice: Tôi đề xuất phạm vi Release 1.0 chỉ gồm tính năng đăng nhập và giỏ hàng.
[00:02:00] Bob: Tôi đồng ý hoàn toàn với đề xuất của Alice.
[00:03:00] Charlie: Với tư cách PM, tôi chốt chính thức phạm vi Release 1.0 như Alice nêu.
"""
    utts = parse_transcript(raw_transcript)
    by_id = {u.id: u for u in utts}

    # Charlie là PM, có quyền chốt scope
    ctx = make_mock_context(
        roles_map={"Charlie": "pm", "Alice": "member", "Bob": "member"},
        meeting_info={"id": "m_reg_test", "leader": "Charlie", "mode": "authority", "date": "2026-10-21"}
    )

    topic_scope = TopicDef(
        topic_id="t_scope",
        title="Phạm vi Release 1.0",
        category="scope",
        options=[OptionDef(option_id="opt_scope", label="Đăng nhập và giỏ hàng")]
    )

    labels = [
        Label(utterance_id=utts[0].id, topic_id="t_scope", option_id="opt_scope", stance="propose", quote="đề xuất phạm vi Release 1.0 chỉ gồm tính năng đăng nhập và giỏ hàng"),
        Label(utterance_id=utts[1].id, topic_id="t_scope", option_id="opt_scope", stance="support", quote="đồng ý hoàn toàn với đề xuất của Alice"),
        Label(utterance_id=utts[2].id, topic_id="t_scope", option_id="opt_scope", stance="conclude", quote="tôi chốt chính thức phạm vi Release 1.0 như Alice nêu")
    ]

    out = LabelerOutput(topics=[topic_scope], labels=labels, items=[])
    good_labels, rep = validate_labels(out, by_id)
    states = evaluate_all(out.topics, good_labels, by_id, ctx)

    assert len(states) == 1
    s = states[0]
    # Khi đủ thẩm quyền, câu chốt dứt khoát không do dự, không phản đối -> BẮT BUỘC ĐÃ CHỐT
    assert s.status == "decided"
    assert s.final_option == "Đăng nhập và giỏ hàng"
    assert s.needs_confirmation is False
    assert len(s.evidence_ids) >= 2


# =========================================================================
# TEST 3: PHÂN BIỆT TÁC NGHIỆP HIỆN TẠI VS TRI THỨC DÙNG LÂU DÀI
# Phân tách Action Items (Jira) vs Knowledge Base (Wiki/ADR)
# =========================================================================
def test_operational_task_vs_longterm_knowledge_separation():
    raw_transcript = """
[00:01:00] Trưởng nhóm: Về mặt kiến trúc lâu dài, toàn bộ hệ thống thống nhất chuẩn hóa giao thức gRPC và cơ sở dữ liệu PostgreSQL cho mọi microservices.
[00:02:00] Hoàng: Em tự nhận sẽ viết script migration dữ liệu sang PostgreSQL trước ngày 2026-10-28.
"""
    utts = parse_transcript(raw_transcript)
    by_id = {u.id: u for u in utts}

    ctx = make_mock_context(
        roles_map={"Trưởng nhóm": "tech_lead", "Hoàng": "member"},
        meeting_info={"id": "m_domain_sep", "leader": "Trưởng nhóm", "mode": "authority", "date": "2026-10-21"}
    )

    items = [
        # Tri thức dài hạn: Quyết định kiến trúc hệ thống
        RawItem(
            kind="knowledge",
            title="Chuẩn hóa kiến trúc microservices qua gRPC và PostgreSQL",
            utterance_ids=[utts[0].id],
            quote="toàn bộ hệ thống thống nhất chuẩn hóa giao thức gRPC và cơ sở dữ liệu PostgreSQL cho mọi microservices"
        ),
        # Việc tác nghiệp ngắn hạn: Task có người tự nhận và deadline
        RawItem(
            kind="task",
            title="Viết script migration dữ liệu sang PostgreSQL",
            utterance_ids=[utts[1].id],
            quote="Em tự nhận sẽ viết script migration dữ liệu sang PostgreSQL",
            assignee="Hoàng",
            assignee_basis="self_accepted",
            deadline_text="2026-10-28"
        )
    ]

    out = LabelerOutput(topics=[], labels=[], items=items)
    rep = ValidationReport()
    built_items = build_items(out, by_id, ctx, meeting_date="2026-10-21", rep=rep)

    assert len(built_items) == 2

    # Phân loại 1: Tri thức dùng lâu dài
    k_item = next(it for it in built_items if it.kind == "knowledge")
    assert k_item.knowledge_category == "architecture"
    assert k_item.assignee is None  # Tri thức không gán assignee cá nhân

    # Phân loại 2: Việc tác nghiệp ngắn hạn
    t_item = next(it for it in built_items if it.kind == "task")
    assert t_item.assignee == "Hoàng"
    assert t_item.assignee_basis == "self_accepted"
    assert t_item.deadline_date == "2026-10-28"
    assert t_item.priority == 1


# =========================================================================
# TEST 4: TRANSCRIPT DÀI & LỘ TRÌNH DIỄN BIẾN ĐA CHIỀU (A -> B -> C)
# Kiểm chứng việc theo dõi diễn biến qua nhiều vòng tranh luận phức tạp
# =========================================================================
def test_long_transcript_multiround_journey_evolution():
    raw_transcript = """
[00:01:00] Tuấn: Đầu tiên, tôi đề xuất kiến trúc Monolith nguyên khối để team làm nhanh.
[00:02:00] Dũng: Tôi thấy Monolith ban đầu dễ nhưng khó scale khi user tăng cao.
[00:03:00] Lan: Đúng vậy, tôi đề xuất chuyển sang Microservices hoàn toàn để độc lập deploy.
[00:04:00] Tuấn: Nhưng Microservices thì chi phí hạ tầng và vận hành Kubernetes rất đắt đỏ.
[00:05:00] Bảo: Tài chính bên em cũng cảnh báo chi phí cloud cho Microservices sẽ vượt ngân sách quý này.
[00:06:00] Lan: Nhưng nếu giữ Monolith thì tech debt sau này ai chịu trách nhiệm?
[00:07:00] Sơn: Tôi đề xuất phương án thỏa hiệp: Modular Monolith, vừa rẻ vừa module hóa tốt.
[00:08:00] Dũng: Ý kiến của Sơn rất hay, Modular Monolith giải quyết được cả bài toán chi phí lẫn cấu trúc code.
[00:09:00] Tuấn: Tôi đồng ý bỏ đề xuất Monolith cũ để ủng hộ Modular Monolith.
[00:10:00] Lan: Tôi cũng rút lại đề xuất Microservices vì vấn đề ngân sách, đồng ý Modular Monolith.
[00:11:00] Hoàng: Với vai trò Tech Lead, tôi chốt chính thức phương án Modular Monolith cho dự án.
"""
    utts = parse_transcript(raw_transcript)
    by_id = {u.id: u for u in utts}

    ctx = make_mock_context(
        roles_map={"Hoàng": "tech_lead", "Tuấn": "member", "Dũng": "member", "Lan": "member", "Bảo": "finance", "Sơn": "member"},
        meeting_info={"id": "m_long_evolution", "leader": "Hoàng", "mode": "authority", "date": "2026-10-22"}
    )

    topic_arch = TopicDef(
        topic_id="t_arch",
        title="Kiến trúc hệ thống phần mềm",
        category="technical",
        options=[
            OptionDef(option_id="opt_mono", label="Monolith"),
            OptionDef(option_id="opt_micro", label="Microservices"),
            OptionDef(option_id="opt_modular", label="Modular Monolith")
        ]
    )

    labels = [
        Label(utterance_id=utts[0].id, topic_id="t_arch", option_id="opt_mono", stance="propose", quote="đề xuất kiến trúc Monolith nguyên khối"),
        Label(utterance_id=utts[1].id, topic_id="t_arch", option_id="opt_mono", stance="oppose", quote="khó scale khi user tăng cao"),
        Label(utterance_id=utts[2].id, topic_id="t_arch", option_id="opt_micro", stance="propose", quote="đề xuất chuyển sang Microservices hoàn toàn"),
        Label(utterance_id=utts[3].id, topic_id="t_arch", option_id="opt_micro", stance="oppose", quote="chi phí hạ tầng và vận hành Kubernetes rất đắt đỏ"),
        Label(utterance_id=utts[4].id, topic_id="t_arch", option_id="opt_micro", stance="oppose", quote="chi phí cloud cho Microservices sẽ vượt ngân sách"),
        Label(utterance_id=utts[6].id, topic_id="t_arch", option_id="opt_modular", stance="propose", quote="đề xuất phương án thỏa hiệp: Modular Monolith"),
        Label(utterance_id=utts[7].id, topic_id="t_arch", option_id="opt_modular", stance="support", quote="Modular Monolith giải quyết được cả bài toán chi phí"),
        Label(utterance_id=utts[8].id, topic_id="t_arch", option_id="opt_mono", stance="reverse", quote="đồng ý bỏ đề xuất Monolith cũ"),
        Label(utterance_id=utts[9].id, topic_id="t_arch", option_id="opt_micro", stance="reverse", quote="rút lại đề xuất Microservices"),
        Label(utterance_id=utts[10].id, topic_id="t_arch", option_id="opt_modular", stance="conclude", quote="tôi chốt chính thức phương án Modular Monolith")
    ]

    out = LabelerOutput(topics=[topic_arch], labels=labels, items=[])
    good_labels, rep = validate_labels(out, by_id)
    states = evaluate_all(out.topics, good_labels, by_id, ctx)

    assert len(states) == 1
    s = states[0]

    # Kiểm tra phương án chốt cuối cùng
    assert s.status == "decided"
    assert s.final_option == "Modular Monolith"

    # Cả 2 phương án trước đó (Monolith và Microservices) đều phải bị ghi nhận là superseded
    assert "Monolith" in s.superseded
    assert "Microservices" in s.superseded

    # Kiểm tra Tiến trình Decision Journey phải theo dõi đủ các bước từ khởi đầu đến kết luận
    assert len(s.decision_journey) >= 6
    phases = [step.phase for step in s.decision_journey]
    assert "proposal" in phases
    assert "discussion" in phases
    assert "modification" in phases
    assert "resolution" in phases

    # Kiểm tra bước chốt cuối cùng là của Tech Lead Hoàng
    last_step = s.decision_journey[-1]
    assert last_step.phase == "resolution"
    assert last_step.speaker == "Hoàng"
    assert last_step.option_label == "Modular Monolith"

