import sys, os, time, json, random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.context import _policy_sections, _yaml, norm_plain
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

# Cuộc họp m01
brief = _yaml(ROOT / "data/meetings/m01/brief.yaml", {})
query = " ".join([brief.get("title", ""), brief.get("purpose", "")] + brief.get("agenda", []))
rel_ids = {0, 2, 6, 8, 9}  # 5 relevant policy sections for m01

print("======================================================================")
print("THỰC NGHIỆM JEV RERANKER TRÊN TOÀN BỘ 212 ĐOẠN (CẢ 200 ĐOẠN NHIỄU)")
print("======================================================================")
print(f"Query m01: '{query}'")
print(f"Tổng số đoạn trong corpus: {len(full_corpus)}")

criteria = (
    "Đoạn chính sách này có trực tiếp quy định hoặc liên quan đến các chủ đề trong mục đích/chương trình cuộc họp không? "
    "True nếu đoạn chính sách chứa quy tắc, quy trình hoặc phân quyền áp dụng cho ít nhất một mục trong chương trình họp. "
    "False nếu chỉ trùng từ khóa nhưng không liên quan thực chất."
)

for idx, s in enumerate(full_corpus):
    s["id"] = f"sec_{idx}"

# Chấm điểm toàn bộ 212 ứng viên qua Jev
t0 = time.time()
print("Đang gửi 212 ứng viên tới Jev System One theo lô 10...")
ranked_all = call_jev_rerank(query, full_corpus, criteria=criteria, threshold=0.0)
dur = time.time() - t0

print(f"Thời gian chấm 212 đoạn qua Jev: {dur:.2f}s")

orig_headings = [s["heading"] for s in orig_sections]

top3 = ranked_all[:3]
top3_hits = sum(1 for s in top3 if not s.get("is_distractor", False) and s["heading"] in orig_headings and orig_headings.index(s["heading"]) in rel_ids)
top3_prec = top3_hits / 3.0

top10 = ranked_all[:10]
top10_hits = sum(1 for s in top10 if not s.get("is_distractor", False) and s["heading"] in orig_headings and orig_headings.index(s["heading"]) in rel_ids)
top10_recall = top10_hits / len(rel_ids)

print("\nKết quả Jev quét toàn bộ 212 đoạn:")
print(f"  Precision@3: {top3_prec*100:.1f}% ({top3_hits}/3)")
print(f"  Recall@10:    {top10_recall*100:.1f}% ({top10_hits}/{len(rel_ids)})")

print("\nTop 5 đoạn được Jev chấm điểm cao nhất:")
for idx, s in enumerate(ranked_all[:5]):
    is_d = "NHIỄU" if s.get("is_distractor") else "CHÍNH SÁCH THẬT"
    is_rel = "ĐÚNG NHÃN" if (not s.get("is_distractor") and s["heading"] in orig_headings and orig_headings.index(s["heading"]) in rel_ids) else "sai nhãn"
    print(f"  #{idx+1}: p={s.get('jev_p', 0.0):.3f} [{is_d} - {is_rel}] - {s.get('heading')}")

out_data = {
    "corpus_size": len(full_corpus),
    "query": query,
    "duration_s": dur,
    "top3_precision": top3_prec,
    "top10_recall": top10_recall,
    "top5": [
        {"rank": idx+1, "p": s.get("jev_p", 0.0), "is_distractor": s.get("is_distractor", False), "heading": s.get("heading")}
        for idx, s in enumerate(ranked_all[:5])
    ]
}
out_file = ROOT / "outputs" / "jev_noise_212_results.json"
out_file.write_text(json.dumps(out_data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nĐã lưu kết quả tại: {out_file}")
