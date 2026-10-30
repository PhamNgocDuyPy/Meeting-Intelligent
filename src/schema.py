"""Schema dùng chung. LLM chỉ được điền LabelerOutput; trạng thái cuối do rules.py tính."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field

Stance = Literal["propose", "support", "oppose", "conclude", "reverse", "defer", "question", "info"]
Category = Literal["scope", "technical", "design", "budget", "release", "process", "other"]
ItemKind = Literal["task", "issue", "request", "feedback", "open_question", "knowledge"]
AssigneeBasis = Literal["assigned", "self_accepted", "mentioned_only", "none"]
Status = Literal["decided", "leaning", "open"]

STATUS_VI = {"decided": "Đã chốt", "leaning": "Nghiêng về", "open": "Chưa chốt"}


class _Lenient(BaseModel):
    model_config = ConfigDict(extra="ignore")


# ---------- Transcript ----------
class Utterance(BaseModel):
    id: str
    idx: int
    ts: Optional[int] = None  # giây
    speaker: str
    text: str

    @computed_field
    @property
    def ts_label(self) -> str:
        if self.ts is None:
            return "--:--:--"
        h, r = divmod(self.ts, 3600)
        m, s = divmod(r, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"


# ---------- Đầu ra của bộ gán nhãn (LLM) ----------
class OptionDef(_Lenient):
    option_id: str
    label: str


class TopicDef(_Lenient):
    topic_id: str
    title: str
    category: Category = "other"
    options: list[OptionDef] = Field(default_factory=list)


class Label(_Lenient):
    utterance_id: str
    topic_id: str
    option_id: Optional[str] = None
    stance: Stance
    conditional: bool = False
    condition_text: Optional[str] = None
    quote: str
    quote_unverified: bool = False


class RawItem(_Lenient):
    kind: ItemKind
    title: str
    detail: Optional[str] = None
    utterance_ids: list[str]
    quote: str
    assignee: Optional[str] = None
    assignee_basis: AssigneeBasis = "none"
    deadline_text: Optional[str] = None


class LabelerOutput(_Lenient):
    topics: list[TopicDef] = Field(default_factory=list)
    labels: list[Label] = Field(default_factory=list)
    items: list[RawItem] = Field(default_factory=list)


# ---------- Đầu ra của bộ chấm (Jev / LLM đối chứng) ----------
class JudgeAnswer(_Lenient):
    answer: bool = False
    p: float = 0.5
    why: str = ""


class JudgeVerdict(_Lenient):
    explicit_conclusion: JudgeAnswer
    objection_remaining: JudgeAnswer
    reversed_later: JudgeAnswer
    conditional: JudgeAnswer
    authority_ok: JudgeAnswer


# ---------- Kết quả cuối ----------
class TimelineEvent(BaseModel):
    utterance_id: str
    ts_label: str
    speaker: str
    stance: str
    option_label: Optional[str] = None
    quote: str
    conditional: bool = False


class DecisionJourneyStep(BaseModel):
    phase: Literal["proposal", "discussion", "modification", "resolution"]
    phase_vi: str  # "Đề xuất ban đầu", "Thảo luận / Phản biện", "Thay đổi / Bác bỏ", "Quyết định chính thức"
    speaker: str
    action: str
    quote: str
    option_label: Optional[str] = None
    ts_label: str = "--:--:--"
    utterance_id: str = ""


class TopicState(BaseModel):
    topic_id: str
    title: str
    category: str = "other"
    options: list[str] = Field(default_factory=list)
    status: Status
    status_vi: str
    final_option: Optional[str] = None
    leaning_option: Optional[str] = None
    superseded: list[str] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    explanation: str = ""
    needs_confirmation: bool = False
    timeline: list[TimelineEvent] = Field(default_factory=list)
    decision_journey: list[DecisionJourneyStep] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    judge: Optional[dict] = None


class ItemOut(BaseModel):
    kind: ItemKind
    title: str
    detail: Optional[str] = None
    utterance_ids: list[str]
    quote: str
    assignee: Optional[str] = None  # None = "chưa xác định"
    assignee_basis: AssigneeBasis = "none"
    deadline_text: Optional[str] = None
    deadline_date: Optional[str] = None  # ISO, chỉ khi suy ra được chắc chắn
    flags: list[str] = Field(default_factory=list)
    priority: int = 3
    knowledge_category: Optional[str] = None  # "architecture", "policy", "lesson_learned", "convention"


class ValidationReport(BaseModel):
    labels_total: int = 0
    labels_valid: int = 0
    labels_dropped: list[dict] = Field(default_factory=list)
    items_total: int = 0
    items_valid: int = 0
    items_dropped: list[dict] = Field(default_factory=list)
    downgrades: list[dict] = Field(default_factory=list)


class MeetingResult(BaseModel):
    meeting_id: str
    title: str = ""
    date: Optional[str] = None
    backend: str = ""
    judge: str = "none"
    topics: list[TopicState] = Field(default_factory=list)
    items: list[ItemOut] = Field(default_factory=list)
    validation: ValidationReport = Field(default_factory=ValidationReport)
    review_queue: list[dict] = Field(default_factory=list)
    transcript: list[Utterance] = Field(default_factory=list)
