import sys
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from src.llm import generate_json, _load_dotenv

_load_dotenv()

results_path = ROOT / "outputs" / "independent_sentences_60_results.json"
data = json.loads(results_path.read_text(encoding="utf-8"))
details = data["details"]

# Find c20 and c24
target_ids = {"c20", "c24"}
print(f"Rerunning Gemini for target cases: {target_ids} with backoff...\n")

for item in details:
    if item["id"] in target_ids:
        text = item["text"]
        print(f"=== Case {item['id']} ===")
        print(f"Text: \"{text}\"")

        user_prompt = (
            f"Phát biểu: {text}\n\n"
            f"Câu hỏi: Việc chốt nội dung/phương án trên có bị ràng buộc bởi điều kiện tiên quyết nào "
            f"chưa được đáp ứng trước khi quyết định có hiệu lực không? (Không tính kế hoạch triển khai sau khi đã chốt)."
        )

        success = False
        for attempt in range(5):
            try:
                g_res = generate_json(
                    "gemini",
                    "Bạn là bộ chấm thẩm định quyết định. Trả về JSON: {'conditional': {'answer': bool, 'p': float, 'why': str}}",
                    user_prompt,
                    dict,
                    use_cache=False
                )
                cond_info = g_res.get("conditional", {})
                gem_ans = cond_info.get("answer", False)
                gem_p = cond_info.get("p", 1.0 if gem_ans else 0.0)

                item["gem_p"] = round(gem_p, 4)
                item["gem_flagged"] = gem_ans
                item["gem_correct"] = (gem_ans == item["is_conditional"])
                print(f"  Attempt {attempt+1}: Success! gem_p={gem_p:.4f}, gem_flagged={gem_ans}, correct={item['gem_correct']}")
                success = True
                break
            except Exception as e:
                print(f"  Attempt {attempt+1} failed: {e}. Retrying in {3 * (attempt + 1)}s...")
                time.sleep(3 * (attempt + 1))

        if not success:
            print(f"  FAILED to get response for {item['id']} after 5 attempts!")

# Save updated details
# Recalculate metrics
n_pos = sum(1 for r in details if r["is_conditional"])
n_neg = sum(1 for r in details if not r["is_conditional"])

jev_tp = sum(1 for r in details if r["is_conditional"] and r["jev_flagged"])
jev_fp = sum(1 for r in details if not r["is_conditional"] and r["jev_flagged"])
jev_tn = sum(1 for r in details if not r["is_conditional"] and not r["jev_flagged"])
jev_fn = sum(1 for r in details if r["is_conditional"] and not r["jev_flagged"])

gem_tp = sum(1 for r in details if r["is_conditional"] and r["gem_flagged"])
gem_fp = sum(1 for r in details if not r["is_conditional"] and r["gem_flagged"])
gem_tn = sum(1 for r in details if not r["is_conditional"] and not r["gem_flagged"])
gem_fn = sum(1 for r in details if r["is_conditional"] and not r["gem_flagged"])

metrics = {
    "dataset_size": len(details),
    "n_conditional": n_pos,
    "n_unconditional": n_neg,
    "jev": {
        "tp": jev_tp, "fp": jev_fp, "tn": jev_tn, "fn": jev_fn,
        "recall": jev_tp / n_pos if n_pos else 0,
        "fpr": jev_fp / n_neg if n_neg else 0,
        "specificity": jev_tn / n_neg if n_neg else 0,
        "precision": jev_tp / (jev_tp + jev_fp) if (jev_tp + jev_fp) else 0,
        "accuracy": (jev_tp + jev_tn) / len(details)
    },
    "gemini": {
        "tp": gem_tp, "fp": gem_fp, "tn": gem_tn, "fn": gem_fn,
        "recall": gem_tp / n_pos if n_pos else 0,
        "fpr": gem_fp / n_neg if n_neg else 0,
        "specificity": gem_tn / n_neg if n_neg else 0,
        "precision": gem_tp / (gem_tp + gem_fp) if (gem_tp + gem_fp) else 0,
        "accuracy": (gem_tp + gem_tn) / len(details)
    }
}

data["metrics"] = metrics
results_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print("\nUpdated outputs/independent_sentences_60_results.json successfully!")
