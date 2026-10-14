"""Luật tất định cập nhật trạng thái chủ đề theo thời gian. LLM KHÔNG quyết định ở đây.

Một chủ đề chỉ "Đã chốt" khi đủ 4 điều kiện (xem proposal, mục 2):
  1. Có phát biểu `conclude` rõ ràng, không điều kiện (conditional=False).
  2. Thẩm quyền: kiểu `authority` -> người có quyền (theo chính sách + vai trò) là người chốt hoặc xác nhận;
                 kiểu `consensus` -> đủ số người ủng hộ (>= nửa số người dự, tối thiểu 2).
  3. Không còn phản đối chưa giải quyết (authority: phản đối SAU lúc chốt; consensus: mọi phản đối còn đứng).
     Không có `defer` sau lúc chốt.
  4. Không có phát biểu muộn hơn đảo ngược (`reverse`) hoặc chốt phương án khác (khi đó `conclude` muộn nhất mới xét).
Thiếu điều kiện nào -> hạ về "Nghiêng về" hoặc "Chưa chốt" + gắn cờ, KHÔNG suy đoán.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .context import ContextPack
from .schema import STATUS_VI, Label, TimelineEvent, TopicDef, TopicState, Utterance

POSITIVE = {"propose", "support", "conclude"}


@dataclass
class _Opt:
    oid: str
    label: str
    stance: dict = field(default_factory=dict)  # người nói -> (stance, idx) gần nhất
    oppose_idx: dict = field(default_factory=dict)
    last_reverse_idx: int = -1
    ever_positive: bool = False
    first_pos_label: Optional[Label] = None

    def supporters(self) -> set[str]:
        return {s for s, (st, _) in self.stance.items() if st in POSITIVE}

    def opposers(self) -> set[str]:
        return {s for s, (st, _) in self.stance.items() if st == "oppose"}


def evaluate_topic(topic: TopicDef, labels: list[Label], utts: dict[str, Utterance], ctx: ContextPack) -> TopicState:
    cat = topic.category
    opts: dict[str, _Opt] = {o.option_id: _Opt(o.option_id, o.label) for o in topic.options}
    ordered = sorted(labels, key=lambda l: utts[l.utterance_id].idx)

    def opt_for(lb: Label) -> Optional[_Opt]:
        oid = lb.option_id
        if oid is None and len(opts) == 1:
            oid = next(iter(opts))
        if oid is None:
            return None
        if oid not in opts:
            opts[oid] = _Opt(oid, oid)
        return opts[oid]

    timeline: list[TimelineEvent] = []
    concludes: list[tuple[Label, int]] = []
    defer_idx = -1
    flags: list[str] = []

    for lb in ordered:
        u = utts[lb.utterance_id]
        o = opt_for(lb)
        timeline.append(TimelineEvent(utterance_id=u.id, ts_label=u.ts_label, speaker=u.speaker, stance=lb.stance,
                                      option_label=o.label if o else None, quote=lb.quote, conditional=lb.conditional))
        if lb.stance == "defer":
            defer_idx = u.idx
            continue
        if o is None:
            if lb.stance in ("conclude", "reverse", "propose", "support", "oppose"):
                flags.append("label_without_option")
            continue
        if lb.stance in POSITIVE:
            o.stance[u.speaker] = (lb.stance, u.idx)
            o.ever_positive = True
            if o.first_pos_label is None:
                o.first_pos_label = lb
            if lb.stance == "conclude":
                concludes.append((lb, u.idx))
        elif lb.stance == "oppose":
            o.stance[u.speaker] = ("oppose", u.idx)
            o.oppose_idx[u.speaker] = u.idx
        elif lb.stance == "reverse":
            o.last_reverse_idx = u.idx

    label_of = {o.oid: o.label for o in opts.values()}
    state = TopicState(topic_id=topic.topic_id, title=topic.title, category=cat,
                       options=[o.label for o in opts.values()], status="open", status_vi=STATUS_VI["open"],
                       timeline=timeline)

    cand_lb: Optional[Label] = None
    cand_idx = -1
    if concludes:
        cand_lb, cand_idx = concludes[-1]  # điều kiện 4: chỉ xét lần chốt muộn nhất
    cand_opt = opt_for(cand_lb) if cand_lb else None

    reasons: list[str] = []
    ok = False
    if cand_lb and cand_opt:
        if cand_opt.last_reverse_idx > cand_idx:
            flags.append("conclusion_reversed")
            reasons.append(f"Kết luận về “{cand_opt.label}” đã bị rút lại ở phát biểu muộn hơn; chưa có kết luận mới.")
            cand_lb = None  # không còn ứng viên hợp lệ
        else:
            speaker = utts[cand_lb.utterance_id].speaker
            fails = []
            # Lỗ hổng 7: Có bằng chứng phản đối/đảo ngược chưa kiểm chứng được trích dẫn -> không chốt
            if any(getattr(l, "quote_unverified", False) for l in ordered):
                fails.append("unverified_negative_evidence")
                reasons.append("Có bằng chứng phản đối/đảo ngược chưa kiểm chứng được trích dẫn; cần người xác nhận.")
            # (1) không điều kiện
            if cand_lb.conditional:
                fails.append("conditional")
                reasons.append("Kết luận còn phụ thuộc điều kiện: " + (cand_lb.condition_text or "chưa nêu rõ") + ".")
            # (2) thẩm quyền
            mode = ctx.mode_for(cat)
            if mode == "authority":
                auth = ctx.has_authority(speaker, cat)
                # người có thẩm quyền phải là người chốt hoặc xác nhận TẠI/SAU lúc kết luận
                sup_auth = [s for s, (st, i) in cand_opt.stance.items()
                            if st in POSITIVE and i >= cand_idx and ctx.has_authority(s, cat)]
                if auth is None:
                    flags.append("speaker_unidentified")
                if not sup_auth:
                    fails.append("needs_authority_confirmation")
                    names = ", ".join(ctx.authority_names(cat)) or "chưa rõ"
                    reasons.append(f"Người chốt ({speaker}) không có thẩm quyền xác nhận cho nhóm “{cat}”; cần: {names}.")
            else:
                need = ctx.min_consensus()
                have = len(cand_opt.supporters())
                if have < need:
                    fails.append("insufficient_consensus")
                    reasons.append(f"Chưa đủ đồng thuận: {have}/{need} người ủng hộ.")
            # (3) phản đối chưa giải quyết
            if mode == "authority":
                late_opp = [s for s in cand_opt.opposers() if cand_opt.oppose_idx.get(s, -1) > cand_idx]
            else:
                late_opp = list(cand_opt.opposers())
            if late_opp:
                fails.append("unresolved_objection")
                reasons.append("Còn phản đối chưa được giải quyết từ: " + ", ".join(sorted(late_opp)) + ".")
            early_opp = [s for s in cand_opt.opposers() if s not in late_opp]
            if mode == "authority" and early_opp:
                flags.append("dissent_recorded:" + ",".join(sorted(early_opp)))
            if defer_idx > cand_idx:
                fails.append("deferred_after_conclusion")
                reasons.append("Sau khi chốt, chủ đề được hoãn/để xem lại.")
            flags.extend(f for f in fails if f not in flags)
            ok = not fails

    if ok and cand_opt:
        state.status, state.final_option = "decided", cand_opt.label
        others = [o for o in opts.values() if o.oid != cand_opt.oid and (o.ever_positive or o.last_reverse_idx >= 0)]
        state.superseded = [o.label for o in others]
        state.explanation = f"Đã chốt “{cand_opt.label}”." + (
            " Phương án đã bị thay thế: " + ", ".join(state.superseded) + "." if state.superseded else "")
        ev = []
        if cand_opt.first_pos_label:
            ev.append(cand_opt.first_pos_label.utterance_id)
        ev.append(cand_lb.utterance_id)
        for o in others:
            if o.first_pos_label:
                ev.append(o.first_pos_label.utterance_id)
        state.evidence_ids = sorted(set(ev), key=lambda i: utts[i].idx)
    else:
        # Nghiêng về: ứng viên chốt nhưng chưa đủ điều kiện, hoặc một phương án dẫn rõ ràng
        lean: Optional[_Opt] = cand_opt if (cand_lb and cand_opt) else None
        if lean is None:
            active = [o for o in opts.values() if o.last_reverse_idx < 0 and o.supporters()]
            if active:
                active.sort(key=lambda o: (len(o.supporters()) - len(o.opposers()), len(o.supporters())), reverse=True)
                top = active[0]
                tied = len(active) > 1 and (len(active[1].supporters()) - len(active[1].opposers())) == (len(top.supporters()) - len(top.opposers()))
                if not tied and len(top.supporters()) >= 2 and len(top.supporters()) > len(top.opposers()):
                    lean = top
                    reasons.append(f"“{top.label}” được nhiều người ủng hộ ({len(top.supporters())}) nhưng chưa có phát biểu chốt hợp lệ.")
                else:
                    reasons.append("Chưa có phương án nào được chốt hoặc dẫn rõ ràng.")
        if defer_idx > -1 and "deferred_after_conclusion" not in flags:
            flags.append("deferred")
            reasons.append("Chủ đề được hoãn sang lần sau.")
        if lean is not None:
            state.status, state.leaning_option = "leaning", lean.label
            state.needs_confirmation = True
        else:
            state.status = "open"
            if not reasons:
                reasons.append("Chưa có kết luận.")
        state.evidence_ids = sorted({lb.utterance_id for lb in ordered if lb.stance in ("conclude", "propose", "defer")},
                                    key=lambda i: utts[i].idx)
        state.explanation = " ".join(reasons)

    state.status_vi = STATUS_VI[state.status]
    state.flags = list(dict.fromkeys(flags))
    return state


def evaluate_all(topics: list[TopicDef], labels: list[Label], utts: dict[str, Utterance], ctx: ContextPack) -> list[TopicState]:
    by_topic: dict[str, list[Label]] = {}
    for lb in labels:
        by_topic.setdefault(lb.topic_id, []).append(lb)
    known = {t.topic_id for t in topics}
    all_topics = list(topics) + [TopicDef(topic_id=tid, title=tid) for tid in by_topic if tid not in known]
    return [evaluate_topic(t, by_topic.get(t.topic_id, []), utts, ctx) for t in all_topics if by_topic.get(t.topic_id)]
