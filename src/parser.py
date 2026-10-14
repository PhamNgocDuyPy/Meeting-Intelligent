"""Tách transcript thành các phát biểu có ID. Giữ nguyên văn bản gốc.

Định dạng chấp nhận:
    [00:04:12] Minh: nội dung        (HH:MM:SS)
    [04:12] Minh: nội dung           (MM:SS)
    Minh: nội dung                   (không có mốc giờ)
Dòng bắt đầu bằng '#' là chú thích, bị bỏ qua. Dòng không khớp được nối vào phát biểu trước.
"""
from __future__ import annotations

import re
from pathlib import Path

from .schema import Utterance
from .textnorm import nfc

_TS_LINE = re.compile(r"^\s*\[(\d{1,2}):(\d{2})(?::(\d{2}))?\]\s*([^:\[\]]{1,40}?)\s*:\s*(.*\S)\s*$")
_PLAIN_LINE = re.compile(r"^\s*([^:\[\]]{1,30}?)\s*:\s*(.*\S)\s*$")


def parse_transcript(raw: str | Path) -> list[Utterance]:
    if isinstance(raw, Path):
        raw = raw.read_text(encoding="utf-8")
    utts: list[Utterance] = []
    for line in nfc(raw).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = _TS_LINE.match(line)
        ts = None
        if m:
            a, b, c, speaker, text = m.groups()
            ts = int(a) * 3600 + int(b) * 60 + int(c) if c is not None else int(a) * 60 + int(b)
        else:
            m2 = _PLAIN_LINE.match(line)
            if m2 and len(m2.group(1).split()) <= 4:
                speaker, text = m2.groups()
            else:
                if utts:  # dòng nối tiếp
                    utts[-1].text += " " + line.strip()
                continue
        idx = len(utts) + 1
        utts.append(Utterance(id=f"U{idx:03d}", idx=idx, ts=ts, speaker=speaker.strip(), text=text.strip()))
    return utts


def render_for_prompt(utts: list[Utterance]) -> str:
    return "\n".join(f"{u.id} [{u.ts_label}] {u.speaker}: {u.text}" for u in utts)
