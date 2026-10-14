import sys
import os
import time
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from src.llm import call_jev, generate_json, _load_dotenv

_load_dotenv()


def exact_binomial_ci(k: int, n: int, confidence: float = 0.95):
    """Calculate exact Clopper-Pearson binomial confidence interval."""
    from scipy.stats import beta
    alpha = 1.0 - confidence
    if k == 0:
        low = 0.0
    else:
        low = beta.ppf(alpha / 2, k, n - k + 1)
    if k == n:
        high = 1.0
    else:
        high = beta.ppf(1.0 - alpha / 2, k + 1, n - k)
    return low, high


def run_evaluation(data_file: str = "data/independent_tests/conditional_sentences_60.json"):
    path = ROOT / data_file
    if not path.exists():
        print(f"Error: {path} not found.")
        return

    with open(path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    print(f"Loaded {len(cases)} test cases from {path}")
    results = []

    for i, c in enumerate(cases, 1):
        cid = c.get("id", f"case_{i:02d}")
        text = c.get("text", "")
        is_cond = c.get("is_conditional", False)
        category = c.get("category", "")
        rationale = c.get("rationale", "")

        # Extract plausible candidate or topic
        cand = "phương án này"
        instructions = (
            f"Việc chốt phương án/nội dung được nhắc tới có bị ràng buộc bởi điều kiện tiên quyết (prerequisite) nào "
            f"chưa được đáp ứng trước khi quyết định có hiệu lực không? "
            f"(Chỉ tính điều kiện để phê duyệt quyết định; không tính kế hoạch triển khai sau khi quyết định đã chốt, "
            f"và không tính các câu nói phụ họa hoặc nguyện vọng cá nhân)."
        )

        # 1. Jev Call
        jev_p = 0.5
        try:
            resp = call_jev(text, {"conditional": {"type": "noul", "instructions": instructions}}, use_cache=True)
            answers = resp.get("answers", resp)
            q = answers.get("conditional", {})
            jev_p = q.get("noul", q.get("probability", 0.5))
        except Exception as e:
            print(f"[{i}/{len(cases)}] Jev error on {cid}: {e}")

        # 2. Gemini Call
        gem_p = 0.5
        gem_ans = False
        try:
            user_prompt = (
                f"Phát biểu: {text}\n\n"
                f"Câu hỏi: Việc chốt nội dung/phương án trên có bị ràng buộc bởi điều kiện tiên quyết nào "
                f"chưa được đáp ứng trước khi quyết định có hiệu lực không? (Không tính kế hoạch triển khai sau khi đã chốt)."
            )
            g_res = generate_json(
                "gemini",
                "Bạn là bộ chấm thẩm định quyết định. Trả về JSON: {'conditional': {'answer': bool, 'p': float, 'why': str}}",
                user_prompt,
                dict,
                use_cache=True
            )
            cond_info = g_res.get("conditional", {})
            gem_ans = cond_info.get("answer", False)
            gem_p = cond_info.get("p", 1.0 if gem_ans else 0.0)
        except Exception as e:
            print(f"[{i}/{len(cases)}] Gemini error on {cid}: {e}")

        jev_flagged = jev_p >= 0.5
        results.append({
            "id": cid,
            "text": text,
            "is_conditional": is_cond,
            "category": category,
            "rationale": rationale,
            "jev_p": round(jev_p, 4),
            "jev_flagged": jev_flagged,
            "gem_p": round(gem_p, 4),
            "gem_flagged": gem_ans,
            "jev_correct": (jev_flagged == is_cond),
            "gem_correct": (gem_ans == is_cond)
        })

        if i % 10 == 0 or i == len(cases):
            print(f"Processed {i}/{len(cases)} cases...")

    # Statistics
    n_pos = sum(1 for r in results if r["is_conditional"])
    n_neg = sum(1 for r in results if not r["is_conditional"])

    jev_tp = sum(1 for r in results if r["is_conditional"] and r["jev_flagged"])
    jev_fp = sum(1 for r in results if not r["is_conditional"] and r["jev_flagged"])
    jev_tn = sum(1 for r in results if not r["is_conditional"] and not r["jev_flagged"])
    jev_fn = sum(1 for r in results if r["is_conditional"] and not r["jev_flagged"])

    gem_tp = sum(1 for r in results if r["is_conditional"] and r["gem_flagged"])
    gem_fp = sum(1 for r in results if not r["is_conditional"] and r["gem_flagged"])
    gem_tn = sum(1 for r in results if not r["is_conditional"] and not r["gem_flagged"])
    gem_fn = sum(1 for r in results if r["is_conditional"] and not r["gem_flagged"])

    metrics = {
        "dataset_size": len(results),
        "n_conditional": n_pos,
        "n_unconditional": n_neg,
        "jev": {
            "tp": jev_tp, "fp": jev_fp, "tn": jev_tn, "fn": jev_fn,
            "recall": jev_tp / n_pos if n_pos else 0,
            "fpr": jev_fp / n_neg if n_neg else 0,
            "specificity": jev_tn / n_neg if n_neg else 0,
            "precision": jev_tp / (jev_tp + jev_fp) if (jev_tp + jev_fp) else 0,
            "accuracy": (jev_tp + jev_tn) / len(results)
        },
        "gemini": {
            "tp": gem_tp, "fp": gem_fp, "tn": gem_tn, "fn": gem_fn,
            "recall": gem_tp / n_pos if n_pos else 0,
            "fpr": gem_fp / n_neg if n_neg else 0,
            "specificity": gem_tn / n_neg if n_neg else 0,
            "precision": gem_tp / (gem_tp + gem_fp) if (gem_tp + gem_fp) else 0,
            "accuracy": (gem_tp + gem_tn) / len(results)
        }
    }

    out_file = ROOT / "outputs" / "independent_sentences_60_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"metrics": metrics, "details": results}, f, ensure_ascii=False, indent=2)

    print("\n================ EVALUATION SUMMARY ================")
    print(f"Total Sentences: {len(results)} (Pos: {n_pos}, Neg: {n_neg})")
    print(f"JEV System One: Recall = {metrics['jev']['recall']*100:.1f}% ({jev_tp}/{n_pos}), FPR = {metrics['jev']['fpr']*100:.1f}% ({jev_fp}/{n_neg}), Acc = {metrics['jev']['accuracy']*100:.1f}%")
    print(f"GEMINI LLM:     Recall = {metrics['gemini']['recall']*100:.1f}% ({gem_tp}/{n_pos}), FPR = {metrics['gemini']['fpr']*100:.1f}% ({gem_fp}/{n_neg}), Acc = {metrics['gemini']['accuracy']*100:.1f}%")
    print(f"Full results saved to: {out_file}")


if __name__ == "__main__":
    run_evaluation()
