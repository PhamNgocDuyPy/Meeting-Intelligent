"""Chấm kết quả so với đáp án tham chiếu (expected.json). Đo lỗi nghiêm trọng trước, độ phủ sau.

Lỗi nghiêm trọng (critical) = hệ thống ghi "Đã chốt" mà đáp án nói không phải / chốt sai phương án
(ví dụ chốt phương án đã bị thay thế). Bỏ sót một quyết định thật chỉ là "bảo thủ" (conservative_miss).
"""
from __future__ import annotations

import json
from pathlib import Path

from .pipeline import MEETINGS, run_meeting
from .schema import MeetingResult
from .textnorm import norm_plain


def _hit(text: str, kws: list[str]) -> bool:
    t = norm_plain(text)
    return any(norm_plain(k) in t for k in kws)


def _as_list(x):
    return x if isinstance(x, list) else [x]


def score_meeting(r: MeetingResult, gold: dict) -> dict:
    res = {"meeting_id": r.meeting_id, "difficulty": gold.get("difficulty", ""), "topics": [], "tasks": [], "items": [],
           "critical_errors": 0, "conservative_misses": 0, "fabricated_assignee": 0, "fabricated_deadline": 0,
           "forbidden_hits": 0, "extra_tasks": 0, "problems": []}

    # ---- chủ đề ----
    for g in gold.get("topics", []):
        allowed = _as_list(g["status"])
        t = next((t for t in r.topics if _hit(t.title + " " + " ".join(t.options), g["keywords"])), None)
        row = {"keywords": g["keywords"], "expected": allowed, "ok": False}
        if t is None:
            row["actual"] = "không tìm thấy chủ đề"
            res["problems"].append(f"Thiếu chủ đề {g['keywords']}")
            if "decided" in allowed:
                res["conservative_misses"] += 1
        else:
            row["actual"] = t.status
            row["final_option"] = t.final_option
            row["superseded"] = t.superseded
            ok = t.status in allowed
            if t.status == "decided":
                fo_ok = _hit(t.final_option or "", g.get("final_option_keywords", [""]) or [""]) if g.get("final_option_keywords") else True
                wrong_sup = g.get("not_final_keywords") and _hit(t.final_option or "", g["not_final_keywords"])
                if "decided" not in allowed or not fo_ok or wrong_sup:
                    res["critical_errors"] += 1
                    res["problems"].append(f"LỖI NGHIÊM TRỌNG: chốt “{t.final_option}” cho {g['keywords']}")
                    ok = False
            elif "decided" in allowed and allowed == ["decided"]:
                res["conservative_misses"] += 1
                res["problems"].append(f"Bỏ sót quyết định {g['keywords']} (hệ thống: {t.status})")
            if ok and g.get("superseded_keywords"):
                row["superseded_ok"] = any(_hit(s, g["superseded_keywords"]) for s in t.superseded)
            row["ok"] = ok
        res["topics"].append(row)

    # ---- việc ----
    tasks = [(i, it) for i, it in enumerate(r.items) if it.kind == "task"]
    matched: set[int] = set()
    for g in gold.get("tasks", []):
        found = next(((i, it) for i, it in tasks if i not in matched and _hit(it.title + " " + (it.detail or "") + " " + it.quote, g["keywords"])), None)
        row = {"keywords": g["keywords"], "expected_assignee": g.get("assignee"), "expected_deadline": g.get("deadline"), "found": bool(found)}
        if found:
            i, it = found
            matched.add(i)
            row["actual_assignee"], row["actual_deadline"] = it.assignee, it.deadline_date
            row["assignee_ok"] = norm_plain(it.assignee or "") == norm_plain(g.get("assignee") or "")
            row["deadline_ok"] = (it.deadline_date or None) == (g.get("deadline") or None)
            if g.get("assignee") is None and it.assignee:
                res["fabricated_assignee"] += 1
                res["problems"].append(f"Tự gán người nhận “{it.assignee}” cho việc {g['keywords']}")
            if g.get("deadline") is None and it.deadline_date:
                res["fabricated_deadline"] += 1
                res["problems"].append(f"Tự điền hạn {it.deadline_date} cho việc {g['keywords']}")
        else:
            res["problems"].append(f"Thiếu việc {g['keywords']}")
        res["tasks"].append(row)
    optional = [o["keywords"] for o in gold.get("optional_tasks", [])]
    for i, it in tasks:
        if i in matched:
            continue
        blob = it.title + " " + (it.detail or "") + " " + it.quote
        if any(_hit(blob, k) for k in optional):
            continue
        res["extra_tasks"] += 1
    for f in gold.get("forbidden_tasks", []):
        if any(_hit(it.title + " " + it.quote, f["keywords"]) for _, it in tasks):
            res["forbidden_hits"] += 1
            res["problems"].append(f"Tạo việc không có thật {f['keywords']}")

    # ---- mục khác ----
    for g in gold.get("items", []):
        found = any(it.kind == g["kind"] and _hit(it.title + " " + (it.detail or "") + " " + it.quote, g["keywords"]) for it in r.items)
        res["items"].append({"kind": g["kind"], "keywords": g["keywords"], "found": found})
        if not found:
            res["problems"].append(f"Thiếu mục {g['kind']} {g['keywords']}")

    # ---- bằng chứng ----
    v = r.validation
    res["labels_total"], res["labels_dropped"] = v.labels_total, len(v.labels_dropped)
    res["items_total"], res["items_dropped"] = v.items_total, len(v.items_dropped)

    topic_ok = all(t["ok"] for t in res["topics"])
    task_ok = all(t["found"] and t.get("assignee_ok", False) and t.get("deadline_ok", False) for t in res["tasks"])
    items_ok = all(i["found"] for i in res["items"])
    res["pass"] = bool(topic_ok and task_ok and items_ok and res["critical_errors"] == 0 and res["forbidden_hits"] == 0
                       and res["fabricated_assignee"] == 0 and res["fabricated_deadline"] == 0)
    return res


def evaluate_all(meeting_ids: list[str], backend: str, judge: str, oracle: bool, judge_mode: str = "downgrade") -> dict:
    rows = []
    for mid in meeting_ids:
        gold_path = MEETINGS / mid / "expected.json"
        if not gold_path.exists():
            continue
        gold = json.loads(gold_path.read_text(encoding="utf-8"))
        try:
            r = run_meeting(mid, backend=backend, judge=judge, judge_mode=judge_mode, oracle=oracle)
            rows.append(score_meeting(r, gold))
        except Exception as e:
            rows.append({"meeting_id": mid, "difficulty": gold.get("difficulty", ""), "error": f"{type(e).__name__}: {e}",
                         "pass": False, "critical_errors": 0, "problems": [f"Lỗi chạy: {e}"]})
    n = len(rows) or 1
    gt = sum(len(x.get("topics", [])) for x in rows)
    gk = sum(len(x.get("tasks", [])) for x in rows)
    lt = sum(x.get("labels_total", 0) for x in rows)
    summary = {
        "meetings": len(rows),
        "pass_rate": sum(1 for x in rows if x["pass"]) / n,
        "critical_errors": sum(x.get("critical_errors", 0) for x in rows),
        "conservative_misses": sum(x.get("conservative_misses", 0) for x in rows),
        "topic_status_acc": (sum(1 for x in rows for t in x.get("topics", []) if t["ok"]) / gt) if gt else None,
        "task_recall": (sum(1 for x in rows for t in x.get("tasks", []) if t["found"]) / gk) if gk else None,
        "assignee_acc": (sum(1 for x in rows for t in x.get("tasks", []) if t.get("assignee_ok")) / gk) if gk else None,
        "deadline_acc": (sum(1 for x in rows for t in x.get("tasks", []) if t.get("deadline_ok")) / gk) if gk else None,
        "fabricated_assignee": sum(x.get("fabricated_assignee", 0) for x in rows),
        "fabricated_deadline": sum(x.get("fabricated_deadline", 0) for x in rows),
        "forbidden_hits": sum(x.get("forbidden_hits", 0) for x in rows),
        "label_quote_valid_rate": (1 - sum(x.get("labels_dropped", 0) for x in rows) / lt) if lt else None,
    }
    return {"backend": "oracle" if oracle else backend, "judge": judge, "judge_mode": judge_mode, "summary": summary, "cases": rows}


def describe_gold(g: dict) -> str:
    parts = []
    for t in g.get("topics", []):
        s = "/".join(_as_list(t["status"]))
        extra = f" → {', '.join(t['final_option_keywords'])}" if t.get("final_option_keywords") else ""
        parts.append(f"chủ đề {t['keywords'][0]}: {s}{extra}")
    for t in g.get("tasks", []):
        parts.append(f"việc {t['keywords'][0]}: {t.get('assignee') or 'chưa xác định'}, hạn {t.get('deadline') or 'chưa xác định'}")
    return "; ".join(parts)


def to_results_markdown(rep: dict) -> str:
    s = rep["summary"]
    fmt = lambda v: "n/a" if v is None else f"{v:.0%}"
    L = [f"# Kết quả kiểm thử — backend `{rep['backend']}`, bộ chấm `{rep['judge']}`", "",
         f"- Số cuộc họp: {s['meetings']} · đạt toàn bộ: {fmt(s['pass_rate'])}",
         f"- **Lỗi nghiêm trọng (chốt nhầm): {s['critical_errors']}** · bỏ sót quyết định (bảo thủ): {s['conservative_misses']}",
         f"- Đúng trạng thái chủ đề: {fmt(s['topic_status_acc'])} · việc tìm thấy: {fmt(s['task_recall'])} · đúng người nhận: {fmt(s['assignee_acc'])} · đúng hạn: {fmt(s['deadline_acc'])}",
         f"- Tự gán người nhận: {s['fabricated_assignee']} · tự điền hạn: {s['fabricated_deadline']} · tạo việc không có thật: {s['forbidden_hits']}",
         f"- Tỷ lệ nhãn có trích dẫn khớp transcript: {fmt(s['label_quote_valid_rate'])}", "",
         "| Ca | Độ khó | Kết quả thực tế | Đạt? |", "|---|---|---|---|"]
    for c in rep["cases"]:
        res = "; ".join(c.get("problems", [])) or "Khớp đáp án tham chiếu"
        L.append(f"| {c['meeting_id']} | {c.get('difficulty','')} | {res} | {'Đạt' if c['pass'] else 'Chưa đạt'} |")
    return "\n".join(L) + "\n"


def save_report(rep: dict, outdir: Path) -> tuple[Path, Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    tag = f"{rep['backend']}_{rep['judge']}"
    jp, mp = outdir / f"eval_{tag}.json", outdir / f"eval_{tag}.md"
    jp.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    mp.write_text(to_results_markdown(rep), encoding="utf-8")
    return jp, mp
