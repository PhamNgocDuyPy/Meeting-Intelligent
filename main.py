"""CLI.  Ví dụ:
  python main.py list
  python main.py run m01 --oracle                      # không cần API, dùng nhãn viết tay (kiểm thử luật)
  python main.py run m01 --backend gemini              # dùng Gemini thật
  python main.py run m01 --backend gemini --judge jev  # thêm bộ chấm Jev
  python main.py eval --oracle                         # chấm toàn bộ bằng nhãn viết tay
  python main.py eval --backend gemini --judge none
  python main.py compare outputs/eval_gemini_none.json outputs/eval_gemini_jev.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.evaluate import evaluate_all, save_report
from src.export import decisions_jsonl, tasks_csv, to_markdown
from src.pipeline import list_meetings, run_meeting

ROOT = Path(__file__).parent
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    r = sub.add_parser("run")
    r.add_argument("meeting")
    r.add_argument("--backend", default="gemini")
    r.add_argument("--judge", default="none", choices=["none", "gemini", "jev"])
    r.add_argument("--judge-mode", default="downgrade", choices=["advisory", "downgrade"],
                   help="downgrade: tự động hạ cấp decided -> leaning; advisory: chỉ cắm cờ cảnh báo")
    r.add_argument("--oracle", action="store_true")
    r.add_argument("--save", action="store_true", help="ghi outputs/<id>.md|.json|_tasks.csv")
    e = sub.add_parser("eval")
    e.add_argument("--backend", default="gemini")
    e.add_argument("--judge", default="none", choices=["none", "gemini", "jev"])
    e.add_argument("--judge-mode", default="downgrade", choices=["advisory", "downgrade"],
                   help="downgrade: tự động hạ cấp decided -> leaning; advisory: chỉ cắm cờ cảnh báo")
    e.add_argument("--oracle", action="store_true")
    e.add_argument("--only", nargs="*")
    c = sub.add_parser("compare")
    c.add_argument("a")
    c.add_argument("b")
    u = sub.add_parser("ui")
    u.add_argument("--port", type=int, default=None, help="Cổng chạy server (mặc định đọc PORT từ môi trường, hoặc 8080)")
    u.add_argument("--host", default="127.0.0.1", help="Địa chỉ host (mặc định 127.0.0.1 hoặc HOST từ môi trường)")
    a = ap.parse_args()

    if a.cmd == "ui":
        import os
        from src.server import run_server
        port = a.port if a.port is not None else int(os.environ.get("PORT", 8080))
        host = os.environ.get("HOST", a.host)
        run_server(port=port, host=host)
        return 0
    elif a.cmd == "list":
        print("\n".join(list_meetings()))
    elif a.cmd == "run":
        res = run_meeting(a.meeting, backend=a.backend, judge=a.judge, judge_mode=a.judge_mode, oracle=a.oracle)
        md = to_markdown(res)
        print(md)
        if a.save:
            out = ROOT / "outputs"
            out.mkdir(exist_ok=True)
            (out / f"{a.meeting}.md").write_text(md, encoding="utf-8")
            (out / f"{a.meeting}_tasks.csv").write_text(tasks_csv(res), encoding="utf-8")
            (out / f"{a.meeting}_decisions.jsonl").write_text(decisions_jsonl(res), encoding="utf-8")
    elif a.cmd == "eval":
        ids = a.only or list_meetings()
        rep = evaluate_all(ids, a.backend, a.judge, a.oracle, judge_mode=a.judge_mode)
        jp, mp = save_report(rep, ROOT / "outputs")
        print(mp.read_text(encoding="utf-8"))
        print(f"Đã ghi {jp} và {mp}")
    elif a.cmd == "compare":
        A, B = (json.loads(Path(p).read_text(encoding="utf-8")) for p in (a.a, a.b))
        keys = ["pass_rate", "critical_errors", "conservative_misses", "topic_status_acc", "assignee_acc", "deadline_acc",
                "fabricated_assignee", "fabricated_deadline", "forbidden_hits"]
        print(f"| Chỉ số | {A['backend']}+{A['judge']} | {B['backend']}+{B['judge']} |\n|---|---|---|")
        for k in keys:
            print(f"| {k} | {A['summary'][k]} | {B['summary'][k]} |")
        diff = [(x["meeting_id"], x["pass"], y["pass"]) for x, y in zip(A["cases"], B["cases"]) if x["pass"] != y["pass"]]
        print("\nCa khác kết quả:", diff or "không")
    return 0


if __name__ == "__main__":
    sys.exit(main())
