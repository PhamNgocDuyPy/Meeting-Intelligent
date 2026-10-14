import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.evaluate import evaluate_all
from src.pipeline import list_meetings

meetings = list_meetings()
configs = [
    ("None (Baseline)", "none", "downgrade"),
    ("Jev (Advisory)", "jev", "advisory"),
    ("Jev (Downgrade)", "jev", "downgrade"),
    ("Gemini (Advisory)", "gemini", "advisory"),
    ("Gemini (Downgrade)", "gemini", "downgrade"),
]

for label, j, jm in configs:
    rep = evaluate_all(meetings, backend="gemini", judge=j, oracle=False, judge_mode=jm)
    s = rep["summary"]
    failed = [(c["meeting_id"], c["problems"]) for c in rep["cases"] if not c["pass"]]
    passed = sum(1 for c in rep["cases"] if c["pass"])
    print(f"=== {label}: Pass {s['pass_rate']*100:.1f}% ({passed}/{s['meetings']}) ===")
    print(f"  Critical errors: {s['critical_errors']}, Conservative misses: {s['conservative_misses']}")
    for fid, probs in failed:
        print(f"  FAIL [{fid}]: {probs}")
    print()
