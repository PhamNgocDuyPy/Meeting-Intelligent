import sys, os, time, json, random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.context import _policy_sections, _yaml
from experiments.test_noise_scaling import generate_distractors
from src.llm import call_jev_rerank, _load_dotenv

_load_dotenv()

policy_dir = ROOT / "data/company/policies"
orig_sections = _policy_sections(policy_dir)
for s in orig_sections:
    s["is_distractor"] = False

random.seed(42)
distractors = generate_distractors(200)
full_corpus = list(orig_sections) + distractors  # 212 segments
for idx, s in enumerate(full_corpus):
    s["id"] = f"sec_{idx}"

orig_headings = [s["heading"] for s in orig_sections]

GROUND_TRUTH = {
    "m01": {0, 2, 6, 8, 9},
    "m02": {0, 5, 9, 10},
    "m05": {0, 2, 7},
    "m08": {0, 2, 8, 9},
}

criteria = (
    "Đoạn chính sách này có trực tiếp quy định hoặc liên quan đến các chủ đề trong mục đích/chương trình cuộc họp không? "
    "True nếu đoạn chính sách chứa quy tắc, quy trình hoặc phân quyền áp dụng cho ít nhất một mục trong chương trình họp. "
    "False nếu chỉ trùng từ khóa nhưng không liên quan thực chất."
)

meetings = ["m01", "m02", "m05", "m08"]
results = []

for mid in meetings:
    brief = _yaml(ROOT / f"data/meetings/{mid}/brief.yaml", {})
    query = " ".join([brief.get("title", ""), brief.get("purpose", "")] + brief.get("agenda", []))
    rel_ids = GROUND_TRUTH[mid]
    
    ranked = call_jev_rerank(query, full_corpus, criteria=criteria, threshold=0.0)
    top3 = ranked[:3]
    top3_hits = sum(1 for s in top3 if not s.get("is_distractor", False) and s["heading"] in orig_headings and orig_headings.index(s["heading"]) in rel_ids)
    p3 = top3_hits / 3.0
    
    top10 = ranked[:10]
    top10_hits = sum(1 for s in top10 if not s.get("is_distractor", False) and s["heading"] in orig_headings and orig_headings.index(s["heading"]) in rel_ids)
    r10 = top10_hits / float(len(rel_ids))
    
    distractors_in_top10 = sum(1 for s in top10 if s.get("is_distractor", False))
    
    results.append({
        "meeting_id": mid,
        "query": query,
        "p@3": p3,
        "r@10": r10,
        "rel_count": len(rel_ids),
        "distractors_in_top10": distractors_in_top10
    })
    print(f"[{mid}] P@3: {p3*100:.1f}%, R@10: {r10*100:.1f}%, Distractors in top 10: {distractors_in_top10}")

avg_p3 = sum(r["p@3"] for r in results) / len(results)
avg_r10 = sum(r["r@10"] for r in results) / len(results)

out_data = {
    "corpus_size": len(full_corpus),
    "distractor_count": 200,
    "meetings_count": len(meetings),
    "avg_p@3": avg_p3,
    "avg_r@10": avg_r10,
    "details": results
}

out_file = ROOT / "outputs" / "jev_noise_4_meetings_results.json"
out_file.write_text(json.dumps(out_data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"=== TRUNG BÌNH 4 CUỘC HỌP: P@3={avg_p3*100:.1f}%, R@10={avg_r10*100:.1f}% ===")
