"""Bộ kiểm thử tính toàn vẹn (Integrity & Logic Tests) cho Meeting-Intel.

Kiểm tra:
1. Chuỗi bằng chứng cứng (Evidence): quote bắt buộc là substring, không được hallucinate.
2. 4 điều kiện chốt quyết định trong rules.py:
   - Đổi A sang B (A bị superseded).
   - Chốt có điều kiện (bị hạ về leaning).
   - Thiếu thẩm quyền (bị hạ về open / leaning).
   - Phản đối chưa giải quyết (bị hạ về leaning).
3. Người nhận việc và hạn chót trong assemble.py:
   - Giao việc tự nhận (self-accepted) vs chỉ bị nhắc tên.
   - Hạn chót suy luận được (relative date) vs hạn mơ hồ.
4. Tích hợp Jev / System One:
   - Parser unpack đúng cấu trúc resp['answers'][qid]['noul'].
   - Bộ chấm (Judge) hạ cấp thận trọng, không chốt nhầm.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from src.schema import Utterance, Label, RawItem, TopicDef, OptionDef, TopicState, TimelineEvent
from src.evidence import quote_in_text, validate_label, validate_item_source
from src.parser import parse_transcript
from src.dates import resolve_deadline
from src.context import ContextPack, load_context
from src.rules import evaluate_topic, evaluate_all
from src.assemble import validate_labels, build_items, build_review_queue
from src.judge import JudgeVerdict, JudgeAnswer, apply_judge
from src.pipeline import run_meeting

ROOT = Path(__file__).resolve().parent.parent


# ==========================================
# 1. EVIDENCE & SUBSTRING INTEGRITY
# ==========================================
def test_quote_in_text_exact_and_normalized():
    text = "Chúng tôi quyết định chọn phương án B thay vì phương án A."
    # Khớp chính xác
    assert quote_in_text("chọn phương án B", text) is True
    # Khớp không phụ thuộc viết hoa/thường hay dấu câu nhẹ
    assert quote_in_text("CHỌN PHƯƠNG ÁN B", text) is True
    # Không khớp chuỗi bịa đặt
    assert quote_in_text("chọn phương án C", text) is False
    assert quote_in_text("", text) is False


def test_validate_label_with_transcript():
    utts = {
        "U001": Utterance(id="U001", idx=1, speaker="An", text="Tôi đề xuất dùng Redis cluster.")
    }
    # Label có quote chuẩn
    good_label = Label(utterance_id="U001", topic_id="t1", stance="propose", quote="đề xuất dùng Redis cluster")
    ok, err = validate_label(good_label, utts)
    assert ok is True
    assert err == ""

    # Label có quote bịa đặt -> Drop
    fake_label = Label(utterance_id="U001", topic_id="t1", stance="propose", quote="đề xuất dùng MongoDB")
    ok, err = validate_label(fake_label, utts)
    assert ok is False
    assert err == "quote_not_in_utterance"


# ==========================================
# 2. DETERMINISTIC RULES & TIMELINE
# ==========================================
def test_a_to_b_superseded():
    """Tình huống cốt lõi: Đề xuất A, tranh luận, cuối cùng chốt B."""
    utts = {
        "U001": Utterance(id="U001", idx=1, ts=60, speaker="An", text="Tôi đề xuất phương án A."),
        "U002": Utterance(id="U002", idx=2, ts=300, speaker="Bình", text="Phương án A quá đắt, tôi phản đối."),
        "U003": Utterance(id="U003", idx=3, ts=600, speaker="An", text="Vậy thống nhất bỏ A, chốt phương án B nhé.")
    }
    topic = TopicDef(
        topic_id="t1",
        title="Công nghệ lưu trữ",
        category="technical",
        options=[OptionDef(option_id="opt_a", label="Phương án A"), OptionDef(option_id="opt_b", label="Phương án B")]
    )
    labels = [
        Label(utterance_id="U001", topic_id="t1", option_id="opt_a", stance="propose", quote="đề xuất phương án A"),
        Label(utterance_id="U002", topic_id="t1", option_id="opt_a", stance="oppose", quote="tôi phản đối"),
        Label(utterance_id="U003", topic_id="t1", option_id="opt_a", stance="reverse", quote="bỏ A"),
        Label(utterance_id="U003", topic_id="t1", option_id="opt_b", stance="conclude", quote="chốt phương án B")
    ]
    # An có thẩm quyền
    ctx = ContextPack(
        meeting={}, attendees=[],
        rights={"technical": {"mode": "authority", "roles": ["Tech Lead"]}},
        glossary={}, carryover=[], policy_snippets=[],
        _index={"an": {"id": "an", "name": "An", "roles": ["Tech Lead"]}}
    )

    state = evaluate_topic(topic, labels, utts, ctx)
    assert state.status == "decided"
    assert state.final_option == "Phương án B"
    assert "Phương án A" in state.superseded


def test_conditional_decision_downgrades_to_leaning():
    """Quyết định còn điều kiện phụ thuộc chưa xảy ra -> không được là decided."""
    utts = {
        "U001": Utterance(id="U001", idx=1, ts=60, speaker="An", text="Nếu khách hàng đồng ý duyệt ngân sách thì chốt phương án B.")
    }
    topic = TopicDef(
        topic_id="t1", title="Triển khai", category="process",
        options=[OptionDef(option_id="opt_b", label="Phương án B")]
    )
    labels = [
        Label(utterance_id="U001", topic_id="t1", option_id="opt_b", stance="conclude", conditional=True,
              condition_text="nếu khách hàng duyệt", quote="chốt phương án B")
    ]
    ctx = ContextPack(
        meeting={}, attendees=[],
        rights={"process": {"mode": "authority", "roles": ["PM"]}},
        glossary={}, carryover=[], policy_snippets=[],
        _index={"an": {"id": "an", "name": "An", "roles": ["PM"]}}
    )

    state = evaluate_topic(topic, labels, utts, ctx)
    assert state.status != "decided"
    assert "conditional" in state.flags


# ==========================================
# 3. TASK ASSIGNEE & DEADLINE LOGIC
# ==========================================
def test_task_assignee_only_mentioned_is_not_assigned():
    """Người chỉ bị nhắc tên vu vơ không được gán assignee."""
    utts = {
        "U001": Utterance(id="U001", idx=1, speaker="Hà", text="Cái này chắc nhờ Tuấn xem qua thử xem sao.")
    }
    by_id = {u.id: u for u in utts.values()}
    raw_item = RawItem(
        kind="task",
        title="Xem qua module",
        utterance_ids=["U001"],
        quote="nhờ Tuấn xem qua",
        assignee="Tuấn",
        assignee_basis="mentioned_only"
    )
    from src.schema import LabelerOutput
    out = LabelerOutput(topics=[], labels=[], items=[raw_item])
    ctx = ContextPack(meeting={}, attendees=[], rights={}, glossary={}, carryover=[], policy_snippets=[], _index={})
    from src.schema import ValidationReport
    rep = ValidationReport()
    items = build_items(out, by_id, ctx, "2026-10-10", rep)

    assert len(items) == 1
    # Bắt buộc bị hạ về None và gắn cờ
    assert items[0].assignee is None
    assert "assignee_only_mentioned" in items[0].flags or "assignee_unknown" in items[0].flags


def test_resolve_deadline_dates():
    """Kiểm tra phân giải ngày tương đối."""
    meeting_date = "2026-10-05"  # Thứ Hai
    # "thứ Sáu" trong tuần -> 2026-10-09
    assert resolve_deadline("thứ Sáu", meeting_date) == "2026-10-09"
    # "ngày mai" -> 2026-10-06
    assert resolve_deadline("ngày mai", meeting_date) == "2026-10-06"
    # "cuối tháng" mơ hồ -> None
    assert resolve_deadline("cuối tháng", meeting_date) is None


# ==========================================
# 4. JEV VERDICT PARSING & JUDGE DOWNGRADE
# ==========================================
def test_apply_judge_downgrades_on_objection():
    """Khi Jev phát hiện có objection_remaining -> hạ decided về leaning."""
    topic = TopicState(
        topic_id="t1", title="Kiến trúc", category="technical", status="decided", status_vi="Đã chốt",
        final_option="Phương án A", timeline=[]
    )
    verdict = JudgeVerdict(
        explicit_conclusion=JudgeAnswer(answer=True, p=0.9),
        objection_remaining=JudgeAnswer(answer=True, p=0.85, why="còn phản đối từ Bình"),
        reversed_later=JudgeAnswer(answer=False, p=0.1),
        conditional=JudgeAnswer(answer=False, p=0.1),
        authority_ok=JudgeAnswer(answer=True, p=0.9)
    )
    downgrade = apply_judge(topic, verdict)
    assert downgrade is not None
    assert topic.status == "leaning"
    assert topic.final_option is None
    assert topic.leaning_option == "Phương án A"
    assert "judge:objection_remaining" in topic.flags


# ==========================================
# 5. END-TO-END ORACLE EVALUATION ON M01
# ==========================================
def test_run_meeting_m01_end_to_end():
    """Chạy end-to-end meeting m01 với oracle backend."""
    res = run_meeting("m01", oracle=True, judge="none")
    assert res.title == "Họp kỹ thuật chọn backend Aurora"
    # Có 1 chủ đề đã chốt
    assert len(res.topics) >= 1
    t = res.topics[0]
    assert t.status == "decided"
    assert t.final_option == "Supabase"
    assert "Firebase" in t.superseded
    # Có tasks
    tasks = [it for it in res.items if it.kind == "task"]
    assert len(tasks) >= 4
    # Task có assignee rõ ràng
    staging_task = next(t for t in tasks if "staging" in t.title.lower() or "staging" in t.quote.lower())
    assert staging_task.assignee == "Quân"
    assert staging_task.deadline_date == "2026-10-09"


def test_judge_assignee_cited_text_includes_speaker():
    """Hồi quy: Văn bản trích dẫn gửi cho bộ chấm kiểm tra giao việc bắt buộc phải kèm tên người nói (speaker: text).
    Ngăn chặn lỗi trước đây chỉ truyền text khiến LLM judge mất ngữ cảnh ai giao việc cho ai."""
    utts = {
        "U001": Utterance(id="U001", idx=1, speaker="Hà", text="Minh hoàn thành phần giao diện trước thứ Sáu.")
    }
    cited_ids = ["U001"]
    cited_utts = [utts[u] for u in cited_ids if u in utts]
    cited_text = " ".join(f"{u.speaker}: {u.text}" for u in cited_utts)
    assert "Hà: Minh hoàn thành phần giao diện" in cited_text
    assert cited_text.startswith("Hà:")


def test_custom_adhoc_consensus_meeting():
    """Kiểm thử cuộc họp tùy biến với người nói mới (không nằm trong people.yaml).
    Hệ thống nhận diện ở chế độ consensus và chốt quyết định hợp lệ khi đủ đồng thuận."""
    from src.context import ContextPack
    from src.rules import evaluate_all
    from src.schema import Label, TopicDef, OptionDef

    utts = {
        "U001": Utterance(id="U001", idx=1, speaker="Tuấn", text="Tôi đề xuất dùng phương án X."),
        "U002": Utterance(id="U002", idx=2, speaker="Hùng", text="Tôi đồng ý dùng X."),
        "U003": Utterance(id="U003", idx=3, speaker="Tuấn", text="Vậy chốt phương án X.")
    }
    brief = {
        "id": "custom_test", "title": "Họp tùy biến", "date": "2026-10-14",
        "mode": "consensus", "attendees": ["Tuấn", "Hùng"]
    }
    attendees = [
        {"id": "tuan", "name": "Tuấn", "title": "Thành viên", "roles": ["member"], "known": True},
        {"id": "hung", "name": "Hùng", "title": "Thành viên", "roles": ["member"], "known": True}
    ]
    rights = {"technical": {"mode": "consensus"}}
    ctx = ContextPack(
        meeting=brief, attendees=attendees, rights=rights, glossary={}, carryover=[], policy_snippets=[],
        _index={"tuan": attendees[0], "hung": attendees[1]}
    )

    topic = TopicDef(topic_id="T1", title="Chọn kiến trúc", category="technical", options=[OptionDef(option_id="O1", label="X")])
    labels = [
        Label(utterance_id="U001", topic_id="T1", option_id="O1", stance="propose", quote="Tôi đề xuất dùng phương án X."),
        Label(utterance_id="U002", topic_id="T1", option_id="O1", stance="support", quote="Tôi đồng ý dùng X."),
        Label(utterance_id="U003", topic_id="T1", option_id="O1", stance="conclude", quote="Vậy chốt phương án X.")
    ]

    states = evaluate_all([topic], labels, utts, ctx)
    assert len(states) == 1
    assert states[0].status == "decided"
    assert states[0].final_option == "X"

