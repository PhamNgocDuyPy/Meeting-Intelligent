"""Chuẩn hóa văn bản tiếng Việt để so khớp trích dẫn / tên."""
from __future__ import annotations

import re
import unicodedata

_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_QUOTES = {"‘": "'", "’": "'", "“": '"', "”": '"', "…": "..."}


def nfc(s: str | None) -> str:
    return unicodedata.normalize("NFC", s or "")


def normalize(s: str | None) -> str:
    """Giữ dấu tiếng Việt, bỏ dấu câu, hạ chữ thường, gộp khoảng trắng."""
    s = nfc(s).lower()
    for a, b in _QUOTES.items():
        s = s.replace(a, b)
    s = _PUNCT.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def strip_accents(s: str | None) -> str:
    s = nfc(s).lower().replace("đ", "d")
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def norm_plain(s: str | None) -> str:
    """Bỏ cả dấu thanh: dùng để khớp từ khóa lỏng (gold, glossary, thứ trong tuần)."""
    return normalize(strip_accents(s))


def contains_word(haystack: str, needle: str) -> bool:
    """needle xuất hiện như một từ/cụm từ nguyên vẹn trong haystack (đã normalize)."""
    h, n = normalize(haystack), normalize(needle)
    if not n:
        return False
    return re.search(rf"(?<!\w){re.escape(n)}(?!\w)", h) is not None
