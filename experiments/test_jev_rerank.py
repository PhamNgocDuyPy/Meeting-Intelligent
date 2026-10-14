import sys, time, json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.context import _policy_sections, _rerank_keyword, _rerank_with_jev, _yaml

print("==================================================")
print("THỰC NGHIỆM ĐÁNH GIÁ JEV LÀM RERANKER (VỊ TRÍ B TRONG PROPOSAL)")
print("==================================================")

policy_dir = ROOT / "data/company/policies"
sections = _policy_sections(policy_dir)
print(f"Tổng số đoạn chính sách ứng viên: {len(sections)}")
for i, s in enumerate(sections):
    print(f"  [{i}] {s['file']} -> {s['heading']}")

test_meetings = ["m01", "m02", "m05", "m06", "m07", "m08"]
results = []

for mid in test_meetings:
    brief = _yaml(ROOT / f"data/meetings/{mid}/brief.yaml", {})
    query = " ".join([brief.get("title", ""), brief.get("purpose", "")] + brief.get("agenda", []))
    print(f"\n--- Cuộc họp {mid}: {brief.get('title')} ---")
    print(f"Truy vấn ngữ cảnh: '{query[:100]}...'")
    
    # 1. Keyword baseline
    t0 = time.time()
    kw_res = _rerank_keyword(query, sections, top_k=3)
    kw_time = (time.time() - t0) * 1000
    kw_headings = [f"{s['file']}::{s['heading']}" for s in kw_res]
    
    # 2. Jev reranker
    t0 = time.time()
    jev_res = _rerank_with_jev(query, sections, top_k=3, threshold=0.3)
    jev_time = (time.time() - t0) * 1000
    jev_headings = [f"{s['file']}::{s['heading']} (p={s.get('jev_p', 0):.2f})" for s in jev_res]
    
    print(f"  Keyword (thời gian: {kw_time:.2f}ms): {kw_headings}")
    print(f"  Jev Rerank (thời gian: {jev_time:.2f}ms): {jev_headings}")
    
    results.append({
        "meeting": mid,
        "title": brief.get("title"),
        "keyword_time_ms": kw_time,
        "jev_time_ms": jev_time,
        "keyword_selected": kw_headings,
        "jev_selected": jev_headings,
    })

print("\n==================================================")
print("KẾT LUẬN TỔNG HỢP VỀ JEV RERANKER")
print("==================================================")
avg_kw = sum(r['keyword_time_ms'] for r in results) / len(results)
avg_jev = sum(r['jev_time_ms'] for r in results) / len(results)
print(f"Thời gian trung bình:")
print(f"  - Keyword Rerank: {avg_kw:.2f} ms")
print(f"  - Jev Rerank:     {avg_jev:.2f} ms (chậm hơn khoảng {avg_jev/max(avg_kw, 0.001):.1f}x do gọi network API)")
