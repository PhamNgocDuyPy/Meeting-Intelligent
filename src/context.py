"""Kho ngữ cảnh 3 tầng: công ty -> dự án -> cuộc họp. Xem docs/CONTEXT_FLOW.md.

NGUYÊN TẮC: ngữ cảnh chỉ dùng để (1) giải nghĩa tên/vai trò/thuật ngữ, (2) xác định ai có thẩm quyền,
(3) nhắc lại việc còn mở. Ngữ cảnh KHÔNG BAO GIỜ là bằng chứng cho một quyết định hay đầu việc.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from .textnorm import norm_plain, normalize


def _yaml(path: Path, default):
    if not path.exists():
        return default
    return yaml.safe_load(path.read_text(encoding="utf-8")) or default


def _policy_sections(policy_dir: Path) -> list[dict]:
    out = []
    for f in sorted(policy_dir.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        parts = re.split(r"(?m)^## ", text)
        for p in parts[1:]:
            head, _, body = p.partition("\n")
            out.append({"file": f.name, "heading": head.strip(), "text": body.strip()})
    return out


@dataclass
class ContextPack:
    meeting: dict
    attendees: list[dict]
    rights: dict
    glossary: dict
    carryover: list[dict]
    policy_snippets: list[dict]
    charter_summary: str = ""
    _index: dict = field(default_factory=dict, repr=False)

    # ----- nhận diện người nói -----
    def person(self, speaker: str) -> Optional[dict]:
        return self._index.get(norm_plain(speaker))

    def roles_of(self, speaker: str) -> list[str]:
        p = self.person(speaker)
        return list(p.get("roles", [])) if p else []

    # ----- thẩm quyền -----
    def mode_for(self, category: str) -> str:
        return self.rights.get(category, self.rights.get("other", {})).get("mode", "consensus")

    def allowed_roles(self, category: str) -> list[str]:
        return list(self.rights.get(category, {}).get("roles", []))

    def has_authority(self, speaker: str, category: str) -> Optional[bool]:
        """True/False nếu nhận diện được người nói; None nếu không có trong danh bạ (khách, nhãn lạ)."""
        p = self.person(speaker)
        if p is None:
            return None
        return bool(set(p.get("roles", [])) & set(self.allowed_roles(category)))

    def authority_names(self, category: str) -> list[str]:
        roles = set(self.allowed_roles(category))
        return [a["name"] for a in self.attendees if set(a.get("roles", [])) & roles]

    def min_consensus(self) -> int:
        n = len([a for a in self.attendees if a.get("known", True)]) or len(self.attendees)
        return max(2, math.ceil(n / 2))

    # ----- đưa vào prompt -----
    def to_prompt(self) -> str:
        m = self.meeting
        lines = [
            "### BỐI CẢNH (chỉ để hiểu tên gọi/vai trò; KHÔNG phải bằng chứng, không được trích dẫn từ đây)",
            f"- Cuộc họp: {m.get('title', '')} | Ngày: {m.get('date', '?')} | Dự án: {m.get('project', '?')}",
            f"- Mục đích: {m.get('purpose', '(không có)')}",
        ]
        if m.get("agenda"):
            lines.append("- Chương trình: " + "; ".join(m["agenda"]))
        lines.append("- Người dự và vai trò:")
        for a in self.attendees:
            lines.append(f"  * {a['name']} — {a.get('title', 'không rõ')} (vai trò: {', '.join(a.get('roles', [])) or 'không có'})")
        lines.append("- Ai được quyền chốt loại quyết định nào (theo chính sách):")
        for cat, r in self.rights.items():
            who = ", ".join(self.authority_names(cat)) or "không ai trong cuộc họp này"
            lines.append(f"  * {cat}: kiểu {r.get('mode')} — {who if r.get('mode') == 'authority' else 'cả nhóm đồng thuận'}")
        if self.glossary:
            lines.append("- Thuật ngữ: " + "; ".join(f"{k} = {v}" for k, v in self.glossary.items()))
        if self.carryover:
            lines.append("- Việc/chủ đề còn mở từ các cuộc họp trước (có thể được nhắc lại):")
            for c in self.carryover:
                lines.append(f"  * {c.get('title')} ({c.get('note', '')})")
        if self.policy_snippets:
            lines.append("- Trích chính sách liên quan:")
            for s in self.policy_snippets:
                lines.append(f"  * [{s['file']} / {s['heading']}] {s['text'][:400]}")
        return "\n".join(lines)


def load_context(root: Path, meeting_dir: Path, use_jev_rerank: bool = False,
                 custom_roles: Optional[dict[str, str]] = None) -> ContextPack:
    root = Path(root)
    brief = _yaml(meeting_dir / "brief.yaml", {})
    people = {p["id"]: p for p in _yaml(root / "data/company/people.yaml", {}).get("people", [])}
    rights = _yaml(root / "data/company/decision_rights.yaml", {}).get("categories", {})

    project = brief.get("project", "")
    pdir = root / "data/projects" / project
    members = _yaml(pdir / "members.yaml", {}).get("members", {})
    glossary = _yaml(pdir / "glossary.yaml", {}).get("terms", {})
    carry_all = _yaml(pdir / "open_items.yaml", {}).get("items", [])
    charter = (pdir / "charter.md").read_text(encoding="utf-8") if (pdir / "charter.md").exists() else ""

    attendees, index = [], {}
    custom_mode = brief.get("mode")
    leader_name = brief.get("leader")

    if custom_roles is not None:
        # Chế độ gán vai trò trực tiếp trong bộ nhớ cho lần chạy này (không ghi file)
        # Giữ nguyên bảng thẩm quyền chuẩn của công ty (decision_rights.yaml)
        all_speakers = list(dict.fromkeys(list(brief.get("attendees", [])) + list(custom_roles.keys())))
        for name in all_speakers:
            s_name = str(name).strip()
            role = custom_roles.get(s_name, custom_roles.get(norm_plain(s_name), "member"))
            roles = [role] if role else ["member"]
            entry = {
                "id": norm_plain(s_name),
                "name": s_name,
                "title": f"Vai trò: {role}",
                "roles": roles,
                "known": (role != "member")
            }
            index[norm_plain(s_name)] = entry
            attendees.append(entry)
    elif custom_mode == "consensus":
        # Chế độ họp đồng thuận: Mọi người tham gia đều được công nhận và có quyền biểu quyết
        rights = {cat: {"mode": "consensus"} for cat in ["scope", "technical", "design", "budget", "release", "process", "other"]}
        for ref in brief.get("attendees", []):
            name = str(ref)
            entry = {"id": norm_plain(name), "name": name, "title": "Thành viên", "roles": ["member"], "known": True}
            index[norm_plain(name)] = entry
            attendees.append(entry)
    elif leader_name:
        # Chế độ chỉ định người chủ trì / chốt quyền
        rights = {cat: {"mode": "authority", "roles": ["leader"]} for cat in ["scope", "technical", "design", "budget", "release", "process", "other"]}
        for ref in brief.get("attendees", []):
            name = str(ref)
            is_lead = norm_plain(name) == norm_plain(leader_name)
            roles = ["leader"] if is_lead else ["member"]
            entry = {"id": norm_plain(name), "name": name, "title": "Chủ trì" if is_lead else "Thành viên", "roles": roles, "known": True}
            index[norm_plain(name)] = entry
            attendees.append(entry)
    else:
        # Chế độ mặc định theo ma trận công ty đã cấu hình
        for ref in brief.get("attendees", []):
            p = people.get(ref)
            if p:
                roles = list(p.get("roles", []))
                if members.get(ref):
                    roles.append(members[ref])
                entry = {"id": ref, "name": p["name"], "title": p.get("title", ""), "roles": roles, "known": True}
                for key in [p["name"], *p.get("aliases", [])]:
                    index[norm_plain(key)] = entry
            else:  # khách / nhãn không có trong danh bạ
                entry = {"id": None, "name": str(ref), "title": "không có trong danh bạ", "roles": [], "known": False}
            attendees.append(entry)
        # người nói không nằm trong danh sách dự họp nhưng có trong danh bạ vẫn nhận diện được
        for p in people.values():
            index.setdefault(norm_plain(p["name"]), {"id": p["id"], "name": p["name"], "title": p.get("title", ""),
                                                     "roles": list(p.get("roles", [])) + ([members[p["id"]]] if members.get(p["id"]) else []),
                                                     "known": True})

    # --- Chọn đoạn policy liên quan ---
    query_text = " ".join([brief.get("title", ""), brief.get("purpose", "")] + brief.get("agenda", []))
    all_sections = _policy_sections(root / "data/company/policies")

    if use_jev_rerank and all_sections:
        snippets = _rerank_with_jev(query_text, all_sections)
    else:
        snippets = _rerank_keyword(query_text, all_sections)

    # --- Lọc open items bằng Jev nếu bật ---
    if use_jev_rerank and carry_all:
        carry_filtered = _rerank_open_items_with_jev(query_text, carry_all)
    else:
        carry_filtered = carry_all  # chưa lọc, đưa hết vào (hiện trạng cũ)

    return ContextPack(meeting=brief, attendees=attendees, rights=rights, glossary=glossary,
                       carryover=carry_filtered, policy_snippets=snippets, charter_summary=charter[:600], _index=index)


def _rerank_keyword(query_text: str, sections: list[dict], top_k: int = 3) -> list[dict]:
    """Chọn đoạn policy bằng trùng từ khóa (cách cũ, fallback)."""
    query = norm_plain(query_text)
    qtok = {t for t in query.split() if len(t) >= 4}
    scored = []
    for s in sections:
        stok = set(norm_plain(s["heading"] + " " + s["text"]).split())
        score = len(qtok & stok)
        if score:
            scored.append((score, s))
    scored.sort(key=lambda x: -x[0])
    return [s for _, s in scored[:top_k]]


def _rerank_with_jev(query_text: str, sections: list[dict], top_k: int = 3,
                     threshold: float = 0.4) -> list[dict]:
    """Dùng Jev làm reranker cho policy snippets (Vị trí B theo thiết kế giải pháp).

    Mỗi section được chấm: "Đoạn chính sách này có trực tiếp liên quan đến
    mục đích/chương trình cuộc họp không?"
    """
    try:
        from .llm import call_jev_rerank
    except ImportError:
        return _rerank_keyword(query_text, sections, top_k)

    criteria = (
        "Đoạn chính sách này có trực tiếp quy định hoặc liên quan đến "
        "các chủ đề trong mục đích/chương trình cuộc họp không? "
        "True nếu đoạn chính sách chứa quy tắc, quy trình hoặc phân quyền "
        "áp dụng cho ít nhất một mục trong chương trình họp. "
        "False nếu chỉ trùng từ khóa nhưng không liên quan thực chất."
    )
    candidates = [{"id": f"p{i}", "text": f"[{s['file']} / {s['heading']}]\n{s['text']}", "_section": s}
                  for i, s in enumerate(sections)]

    try:
        ranked = call_jev_rerank(query_text, candidates, criteria, threshold=threshold)
        if ranked:
            out = []
            for r in ranked[:top_k]:
                sec = dict(r["_section"])
                sec["jev_p"] = r.get("jev_p")
                out.append(sec)
            return out
    except Exception:
        pass  # Jev lỗi -> fallback

    return _rerank_keyword(query_text, sections, top_k)


def _rerank_open_items_with_jev(query_text: str, items: list[dict],
                                 threshold: float = 0.35) -> list[dict]:
    """Dùng Jev lọc open items liên quan đến cuộc họp hiện tại."""
    try:
        from .llm import call_jev_rerank
    except ImportError:
        return items

    criteria = (
        "Mục việc/chủ đề mở này có khả năng được thảo luận hoặc liên quan "
        "đến chương trình cuộc họp hiện tại không? "
        "True nếu có liên hệ trực tiếp. False nếu không liên quan."
    )
    candidates = [{"id": f"oi{i}", "text": f"{it.get('title', '')} — {it.get('note', '')}", "_item": it}
                  for i, it in enumerate(items)]

    try:
        ranked = call_jev_rerank(query_text, candidates, criteria, threshold=threshold)
        if ranked:
            out = []
            for r in ranked:
                it = dict(r["_item"])
                it["jev_p"] = r.get("jev_p")
                out.append(it)
            return out
    except Exception:
        pass

    return items
