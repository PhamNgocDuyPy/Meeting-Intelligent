import sys, os, time, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.pipeline import run_meeting_dir, MEETINGS
from src.context import load_context
from src.evaluate import score_meeting

meetings = sorted([p.name for p in MEETINGS.iterdir() if (p / "transcript.txt").exists()])
print(f"Kiểm tra End-to-End Pass rate trên 20 cuộc họp:")
print(f"So sánh giữa use_jev_rerank=False (Keyword) và use_jev_rerank=True (Jev Rerank)\n")

for mode_name, use_jev in [("Keyword Rerank (Mặc định)", False), ("Jev Rerank", True)]:
    passes = 0
    total = len(meetings)
    crit_errs = 0
    misses = 0
    t0 = time.time()
    for mid in meetings:
        mdir = MEETINGS / mid
        gold = json.loads((mdir / "expected.json").read_text(encoding="utf-8"))
        ctx = load_context(ROOT, mdir, use_jev_rerank=use_jev)
        # Chạy với backend gemini, judge none (cấu hình chuẩn)
        res = run_meeting_dir(mdir, backend="gemini", judge="none", ctx=ctx)
        score = score_meeting(res, gold)
        
        # pass nếu không có critical error và không có conservative miss
        is_pass = (score["critical_errors"] == 0 and score["conservative_misses"] == 0 and 
                   score["fabricated_assignee"] == 0 and score["fabricated_deadline"] == 0)
        if is_pass: passes += 1
        crit_errs += score["critical_errors"]
        misses += score["conservative_misses"]
    
    elapsed = time.time() - t0
    print(f"Chế độ: {mode_name}", flush=True)
    print(f"  Pass Rate        : {passes}/{total} ({passes/total*100:.1f}%)", flush=True)
    print(f"  Lỗi nghiêm trọng : {crit_errs}", flush=True)
    print(f"  Bỏ sót quyết định: {misses}", flush=True)
    print(f"  Thời gian chạy   : {elapsed:.2f}s\n", flush=True)
