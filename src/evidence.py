"""Kiểm tra bằng chứng: mọi trích dẫn phải là chuỗi con của đoạn nguồn đã nêu."""
from __future__ import annotations

from .schema import Label, RawItem, Utterance
from .textnorm import normalize


def quote_in_text(quote: str, text: str) -> bool:
    nq, nt = normalize(quote), normalize(text)
    return bool(nq) and nq in nt


def validate_label(lb: Label, by_id: dict[str, Utterance]) -> tuple[bool, str]:
    u = by_id.get(lb.utterance_id)
    if u is None:
        return False, "utterance_id_not_found"
    if not quote_in_text(lb.quote, u.text):
        return False, "quote_not_in_utterance"
    return True, ""


def validate_item_source(it: RawItem, by_id: dict[str, Utterance]) -> tuple[bool, str]:
    if not it.utterance_ids:
        return False, "no_utterance_ids"
    texts = []
    for uid in it.utterance_ids:
        u = by_id.get(uid)
        if u is None:
            return False, "utterance_id_not_found"
        texts.append(u.text)
    joined = " ".join(texts)
    if quote_in_text(it.quote, joined) or any(quote_in_text(it.quote, t) for t in texts):
        return True, ""
    return False, "quote_not_in_cited_utterances"
