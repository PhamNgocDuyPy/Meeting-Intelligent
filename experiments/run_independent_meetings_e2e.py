import sys
import os
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from src.pipeline import run_meeting_dir
from src.evaluate import score_meeting
from src.llm import _load_dotenv

_load_dotenv()

BASE_DIR = ROOT / "data" / "independent_tests" / "meetings"
MEETING_IDS = ["indep_m01", "indep_m02", "indep_m03", "indep_m04", "indep_m05", "indep_m06"]


def run_e2e_benchmark():
    print("======================================================================")
    print("CHẠY THỰC NGHIỆM ĐỘC LẬP 6 CUỘC HỌP TỔNG HỢP (RAW FIRST-PASS E2E)")
    print("Dữ liệu độc lập: do nvidia/nemotron-3-super-120b-a12b sinh")
    print("======================================================================\n")

    results_baseline = {}
    results_jev_advisory = {}

    for mid in MEETING_IDS:
        mdir = BASE_DIR / mid
        gold_file = mdir / "expected.json"
        if not gold_file.exists():
            print(f"Skipping {mid}: missing expected.json")
            continue
        gold = json.loads(gold_file.read_text(encoding="utf-8"))

        print(f"\n>>> Running {mid} (gemini + none)...")
        t0 = time.time()
        try:
            res_base = run_meeting_dir(mdir, backend="gemini", judge="none")
            score_base = score_meeting(res_base, gold)
            results_baseline[mid] = {
                "score": score_base,
                "topics_found": len(res_base.topics),
                "items_found": len(res_base.items),
                "review_queue_len": len(res_base.review_queue),
                "elapsed": round(time.time() - t0, 2)
            }
            pass_base = (score_base["critical_errors"] == 0 and score_base["conservative_misses"] == 0)
            print(f"  [gemini+none] Done in {results_baseline[mid]['elapsed']}s | Critical={score_base['critical_errors']}, Miss={score_base['conservative_misses']}, Problems={len(score_base['problems'])}")
            for p in score_base['problems']:
                print(f"    - Problem: {p}")
        except Exception as e:
            print(f"  [gemini+none] FAILED with error: {e}")
            results_baseline[mid] = {"error": str(e)}

        print(f">>> Running {mid} (gemini + jev advisory)...")
        t0 = time.time()
        try:
            res_jev = run_meeting_dir(mdir, backend="gemini", judge="jev", judge_mode="advisory")
            score_jev = score_meeting(res_jev, gold)
            results_jev_advisory[mid] = {
                "score": score_jev,
                "topics_found": len(res_jev.topics),
                "items_found": len(res_jev.items),
                "review_queue_len": len(res_jev.review_queue),
                "elapsed": round(time.time() - t0, 2)
            }
            pass_jev = (score_jev["critical_errors"] == 0 and score_jev["conservative_misses"] == 0)
            print(f"  [gemini+jev_advisory] Done in {results_jev_advisory[mid]['elapsed']}s | Critical={score_jev['critical_errors']}, Miss={score_jev['conservative_misses']}, Problems={len(score_jev['problems'])}")
            for p in score_jev['problems']:
                print(f"    - Problem: {p}")
        except Exception as e:
            print(f"  [gemini+jev_advisory] FAILED with error: {e}")
            results_jev_advisory[mid] = {"error": str(e)}

    # Summary
    output_data = {
        "metadata": {
            "model_extractor": "gemini-3.1-flash-lite",
            "model_generator": "nvidia/nemotron-3-super-120b-a12b",
            "judge": "jev-1.13-free",
            "date": "2026-10-14",
            "meetings_count": len(MEETING_IDS)
        },
        "baseline_gemini_none": results_baseline,
        "gemini_jev_advisory": results_jev_advisory
    }

    out_path = ROOT / "outputs" / "independent_meetings_e2e_results.json"
    out_path.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n======================================================================")
    print(f"Báo cáo E2E đã lưu tại: {out_path}")
    print("======================================================================")


if __name__ == "__main__":
    run_e2e_benchmark()
