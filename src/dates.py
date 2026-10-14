"""Suy hạn hoàn thành từ cụm từ trong transcript. Bảo thủ: mơ hồ thì trả None (giữ nguyên văn bản)."""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional

from .textnorm import norm_plain

_WD = {"hai": 0, "2": 0, "ba": 1, "3": 1, "tu": 2, "4": 2, "nam": 3, "5": 3, "sau": 4, "6": 4, "bay": 5, "7": 5}


def resolve_deadline(text: Optional[str], meeting_date: Optional[str]) -> Optional[str]:
    if not text or not meeting_date:
        return None
    try:
        base = date.fromisoformat(meeting_date)
    except ValueError:
        return None
    t = norm_plain(text)

    # 1) dd/mm(/yyyy) hoặc "ngày dd tháng mm"
    m = re.search(r"(?<!\d)(\d{1,2})\s*/\s*(\d{1,2})(?:\s*/\s*(\d{4}))?(?!\d)", text)
    m2 = re.search(r"ngay (\d{1,2}) thang (\d{1,2})", t)
    if m or m2:
        d, mo = (int(m.group(1)), int(m.group(2))) if m else (int(m2.group(1)), int(m2.group(2)))
        y = int(m.group(3)) if (m and m.group(3)) else base.year
        try:
            res = date(y, mo, d)
        except ValueError:
            return None
        if res < base and not (m and m.group(3)):
            res = date(y + 1, mo, d)
        return res.isoformat()

    # 2) hôm nay / ngày mai / ngày kia
    if re.search(r"\bhom nay\b", t):
        return base.isoformat()
    if re.search(r"\b(ngay mai|mai)\b", t):
        return (base + timedelta(days=1)).isoformat()
    if re.search(r"\bngay kia\b", t):
        return (base + timedelta(days=2)).isoformat()

    # 3) thứ trong tuần
    wd = None
    mw = re.search(r"\bthu (hai|ba|tu|nam|sau|bay|[2-7])\b", t)
    if mw:
        wd = _WD[mw.group(1)]
    elif re.search(r"\bchu nhat\b", t):
        wd = 6
    if wd is not None:
        if re.search(r"\btuan sau\b", t):  # thứ X của tuần kế tiếp (tuần bắt đầu thứ Hai)
            start_next = base - timedelta(days=base.weekday()) + timedelta(days=7)
            return (start_next + timedelta(days=wd)).isoformat()
        delta = (wd - base.weekday()) % 7
        delta = delta or 7  # lần xuất hiện kế tiếp, không tính hôm nay
        return (base + timedelta(days=delta)).isoformat()

    return None  # "tuần sau", "cuối tháng", "sau khi có staging"... không đủ cụ thể
