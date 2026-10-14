import sys, os, time, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.evaluate import evaluate_all
from src.pipeline import list_meetings

meetings = list_meetings()
print("======================================================================")
print("THỰC NGHIỆM ĐỐI CHỨNG BỘ CHẤM: JEV VS GEMINI VS NONE (TRÊN 20 CUỘC HỌP)")
print("======================================================================")

modes = [
    ("gemini", "none", "downgrade", "Gemini + Không bộ chấm (Baseline)"),
    ("gemini", "jev", "downgrade", "Gemini + Jev Judge (Chế độ tự hạ cấp)"),
    ("gemini", "jev", "advisory", "Gemini + Jev Judge (Chế độ cảnh báo)"),
    ("gemini", "gemini", "downgrade", "Gemini + Gemini Judge (Chế độ tự hạ cấp)"),
    ("gemini", "gemini", "advisory", "Gemini + Gemini Judge (Chế độ cảnh báo)"),
]

results = []

for backend, judge, judge_mode, label in modes:
    t0 = time.time()
    rep = evaluate_all(meetings, backend=backend, judge=judge, oracle=False, judge_mode=judge_mode)
    dur = time.time() - t0
    s = rep["summary"]
    
    # Đếm số ca hạ oan và số cờ cảnh báo
    downgrades = []
    advisories = []
    for c in rep["cases"]:
        mid = c["meeting_id"]
        for p in c.get("problems", []):
            if "Bỏ sót quyết định" in p:
                downgrades.append((mid, p))
    
    results.append({
        "label": label,
        "backend": backend,
        "judge": judge,
        "judge_mode": judge_mode,
        "pass_rate": s["pass_rate"],
        "critical_errors": s["critical_errors"],
        "conservative_misses": s["conservative_misses"],
        "duration_s": dur,
        "downgrades": downgrades
    })
    print(f"--- {label} ---")
    print(f"  Pass Rate: {s['pass_rate']*100:.1f}%")
    print(f"  Lỗi chốt nhầm (Critical): {s['critical_errors']}")
    print(f"  Hạ oan / Bỏ sót (Misses): {s['conservative_misses']} ca -> {downgrades}")
    print(f"  Thời gian: {dur:.2f}s\n")

out_file = ROOT / "outputs" / "judge_comparison_results.json"
out_file.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Đã lưu kết quả tại: {out_file}")
