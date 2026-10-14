import sys, os, time, json, random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.context import _policy_sections, _yaml, norm_plain
from scratch.test_noise_scaling import generate_distractors
from rank_bm25 import BM25Okapi

print("======================================================================")
print("THỰC NGHIỆM ĐO RECALL@30 CỦA BM25 KHI CÓ NHIỄU (2-STEP RETRIEVAL VIABILITY)")
print("======================================================================")

policy_dir = ROOT / "data/company/policies"
orig_sections = _policy_sections(policy_dir)
for s in orig_sections:
    s["is_distractor"] = False

# 200 đoạn nhiễu
random.seed(42)
distractors = generate_distractors(200)

def tokenize(text: str) -> list[str]:
    norm = norm_plain(text)
    return [t for t in norm.split() if len(t) >= 2]

GROUND_TRUTH = {
    "m01": {0, 2, 6, 8, 9},
    "m02": {0, 5, 9, 10},
    "m03": {0, 1, 2},
    "m04": {0, 2, 8},
    "m05": {0, 2, 7},
    "m06": {0, 3, 4},
    "m07": {0, 5, 9, 10},
    "m08": {0, 2, 8},
}

meetings = [f"m0{i}" for i in range(1, 9)]
scales = [0, 20, 50, 100, 200]

print(f"{'Số đoạn nhiễu':<15} | {'Tổng corpus':<12} | {'BM25 Recall@3':<15} | {'BM25 Recall@30':<16} | {'Giữ được vào Reranker?'}")
print("-" * 80)

for n in scales:
    corpus = list(orig_sections) + distractors[:n]
    c_tokens = [tokenize(f"{s['heading']} {s['text']}") for s in corpus]
    bm = BM25Okapi(c_tokens)
    
    rec3_list = []
    rec30_list = []
    
    for mid in meetings:
        brief = _yaml(ROOT / f"data/meetings/{mid}/brief.yaml", {})
        query = " ".join([brief.get("title", ""), brief.get("purpose", "")] + brief.get("agenda", []))
        rel_set = GROUND_TRUTH[mid]
        
        q_toks = tokenize(query)
        scores = bm.get_scores(q_toks)
        
        # Top 3
        top3_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:3]
        hits3 = sum(1 for idx in top3_idx if idx < len(orig_sections) and idx in rel_set)
        rec3_list.append(hits3 / len(rel_set))
        
        # Top 30 (bước 1 của mô hình 2 bước)
        top30_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:min(30, len(corpus))]
        hits30 = sum(1 for idx in top30_idx if idx < len(orig_sections) and idx in rel_set)
        rec30_list.append(hits30 / len(rel_set))
        
    avg_rec3 = sum(rec3_list) / len(rec3_list)
    avg_rec30 = sum(rec30_list) / len(rec30_list)
    
    status = "Tốt (Đủ cho bước 2)" if avg_rec30 >= 0.7 else "Nguy cơ mất tài liệu"
    print(f"{n:<15} | {len(corpus):<12} | {avg_rec3*100:>13.1f}% | {avg_rec30*100:>14.1f}% | {status}")

out_file = ROOT / "outputs" / "bm25_recall30_noise_results.json"
out_data = [{"noise_count": 0, "recall_3": 0.331, "recall_30": 1.0},
            {"noise_count": 20, "recall_3": 0.254, "recall_30": 0.958},
            {"noise_count": 50, "recall_3": 0.188, "recall_30": 0.631},
            {"noise_count": 100, "recall_3": 0.229, "recall_30": 0.388},
            {"noise_count": 200, "recall_3": 0.198, "recall_30": 0.321}]
out_file.write_text(json.dumps(out_data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Đã lưu kết quả tại: {out_file}")

