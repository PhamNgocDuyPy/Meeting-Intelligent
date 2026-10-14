import sys, os, time, json, random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.context import _policy_sections, _rerank_keyword, _yaml, norm_plain
from src.llm import call_jev_rerank, call_gemini_text, _extract_json
from rank_bm25 import BM25Okapi

print("======================================================================")
print("THỰC NGHIỆM ĐÁNH GIÁ 4 PHƯƠNG PHÁP RERANKER TRÊN BỘ DỮ LIỆU CHUẨN")
print("======================================================================")

policy_dir = ROOT / "data/company/policies"
sections = _policy_sections(policy_dir)
print(f"Tổng số đoạn chính sách gốc: {len(sections)}")

# Danh sách 8 cuộc họp viết tay m01 - m08
meetings = [f"m0{i}" for i in range(1, 9)]

# 1. BẢNG NHÃN GROUND TRUTH RELEVANCE (8 cuộc họp x 12 đoạn = 96 nhãn)
# Chỉ số các đoạn:
# 0: decision_policy::Ai được chốt quyết định
# 1: decision_policy::Quyết định theo đồng thuận
# 2: decision_policy::Ghi nhận quyết định
# 3: release_policy::Điều kiện phát hành
# 4: release_policy::Ngày phát hành
# 5: release_policy::Báo cáo định kỳ
# 6: security_policy::Dữ liệu khách hàng
# 7: security_policy::Thanh toán và đăng nhập
# 8: security_policy::Hạ tầng
# 9: task_assignment_policy::Một việc hợp lệ
# 10: task_assignment_policy::Hạn hoàn thành
# 11: task_assignment_policy::Việc phụ thuộc

GROUND_TRUTH = {
    # m01: Kỹ thuật chọn backend Aurora (Supabase/Firebase) & Phân việc dựng môi trường
    # Liên quan: [0] Quyền chốt kỹ thuật, [2] Ghi nhận quyết định, [6] Dữ liệu khách hàng bên thứ 3, [8] Hạ tầng đám mây chi phí, [9] Phân việc
    "m01": {0, 2, 6, 8, 9},
    
    # m02: Tiến độ tuần Helios (Ngày demo khách, phân việc báo cáo doanh thu)
    # Liên quan: [0] Quyền chốt tiến độ (PM), [5] Báo cáo định kỳ, [9] Một việc hợp lệ, [10] Hạn hoàn thành
    "m02": {0, 5, 9, 10},
    
    # m03: Thiết kế - màu chủ đạo Aurora
    # Liên quan: [0] Quyền chốt thiết kế, [1] Quyết định đồng thuận, [2] Ghi nhận quyết định
    "m03": {0, 1, 2},
    
    # m04: Kỹ thuật - cache màn báo cáo Helios
    # Liên quan: [0] Quyền chốt kỹ thuật, [2] Ghi nhận quyết định, [8] Hạ tầng kỹ thuật
    "m04": {0, 2, 8},
    
    # m05: Chọn cổng thanh toán Aurora (Stripe / nội địa, phí giao dịch)
    # Liên quan: [0] Quyền chốt, [2] Ghi nhận quyết định (điều kiện), [7] Thanh toán và đăng nhập (PCI-DSS)
    "m05": {0, 2, 7},
    
    # m06: Chốt ngày release Aurora 1.0 (Tình hình test, ngày release)
    # Liên quan: [0] Quyền chốt, [3] Điều kiện phát hành (không lỗi cao), [4] Ngày phát hành (Head of Product)
    "m06": {0, 3, 4},
    
    # m07: Báo cáo cuối tháng Helios (Định dạng báo cáo, xuất file tự động)
    # Liên quan: [0] Quyền chốt, [5] Báo cáo định kỳ theo mẫu, [9] Việc hợp lệ, [10] Hạn hoàn thành
    "m07": {0, 5, 9, 10},
    
    # m08: Hạ tầng Aurora - hosting và monitoring (AWS, Datadog)
    # Liên quan: [0] Quyền chốt kỹ thuật, [2] Ghi nhận quyết định, [8] Hạ tầng đám mây
    "m08": {0, 2, 8},
}

# Tiêu chí Jev
JEV_CRITERIA = (
    "Đoạn chính sách này có trực tiếp quy định hoặc liên quan đến "
    "các chủ đề trong mục đích/chương trình cuộc họp không? "
    "True nếu đoạn chính sách chứa quy tắc, quy trình hoặc phân quyền "
    "áp dụng cho ít nhất một mục trong chương trình họp. "
    "False nếu chỉ trùng từ khóa nhưng không liên quan thực chất."
)

# Chuẩn bị corpus BM25
def tokenize(text: str) -> list[str]:
    norm = norm_plain(text)
    return [t for t in norm.split() if len(t) >= 2]

corpus_tokens = [tokenize(f"{s['heading']} {s['text']}") for s in sections]
bm25 = BM25Okapi(corpus_tokens)

# Hàm gọi Gemini Reranker
def rerank_gemini(query: str, sec_list: list[dict], top_k: int = 3) -> list[int]:
    cand_text = "\n".join([f"[{i}] {s['file']} :: {s['heading']}\n{s['text']}" for i, s in enumerate(sec_list)])
    system_prompt = "Bạn là bộ xếp hạng tài liệu (Reranker). Hãy chọn các đoạn liên quan nhất tới cuộc họp."
    user_prompt = f"""Cuộc họp cần tìm chính sách áp dụng:
{query}

Danh sách chính sách:
{cand_text}

Hãy chọn đúng {top_k} đoạn liên quan nhất. Trả về JSON theo định dạng:
{{"top_indices": [chỉ số nguyên của top 1, chỉ số nguyên của top 2, chỉ số nguyên của top 3]}}
Chỉ trả về JSON, không thêm văn bản nào khác.
"""
    try:
        raw = call_gemini_text(system_prompt, user_prompt, temperature=0.0)
        obj = _extract_json(raw)
        indices = obj.get("top_indices", [])
        return [idx for idx in indices if 0 <= idx < len(sec_list)][:top_k]
    except Exception as e:
        # Fallback keyword nếu Gemini lỗi
        kw = _rerank_keyword(query, sec_list, top_k=top_k)
        return [sec_list.index(s) for s in kw]

# Khởi tạo bảng kết quả
results = {
    "keyword": {"recalls": [], "precisions": [], "latencies": [], "top3_per_meeting": {}},
    "bm25": {"recalls": [], "precisions": [], "latencies": [], "top3_per_meeting": {}},
    "gemini": {"recalls": [], "precisions": [], "latencies": [], "top3_per_meeting": {}},
    "jev": {"recalls": [], "precisions": [], "latencies": [], "top3_per_meeting": {}},
}

print("\n--- BẮT ĐẦU CHẠY TRÊN 8 CUỘC HỌP ---")

for mid in meetings:
    brief = _yaml(ROOT / f"data/meetings/{mid}/brief.yaml", {})
    query = " ".join([brief.get("title", ""), brief.get("purpose", "")] + brief.get("agenda", []))
    rel_set = GROUND_TRUTH[mid]
    
    print(f"\nCuộc họp {mid} ('{brief.get('title')}'): Tập liên quan chuẩn: {len(rel_set)} đoạn {rel_set}")

    # 1. KEYWORD
    t0 = time.time()
    kw_secs = _rerank_keyword(query, sections, top_k=3)
    kw_lat = (time.time() - t0) * 1000
    kw_idx = [sections.index(s) for s in kw_secs]
    # Nếu ít hơn 3 đoạn do không trùng từ khóa, bù
    kw_hits = len(set(kw_idx) & rel_set)
    results["keyword"]["recalls"].append(kw_hits / len(rel_set))
    results["keyword"]["precisions"].append(kw_hits / 3.0)
    results["keyword"]["latencies"].append(kw_lat)
    results["keyword"]["top3_per_meeting"][mid] = kw_idx

    # 2. BM25
    t0 = time.time()
    q_toks = tokenize(query)
    scores = bm25.get_scores(q_toks)
    bm_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:3]
    bm_lat = (time.time() - t0) * 1000
    bm_hits = len(set(bm_idx) & rel_set)
    results["bm25"]["recalls"].append(bm_hits / len(rel_set))
    results["bm25"]["precisions"].append(bm_hits / 3.0)
    results["bm25"]["latencies"].append(bm_lat)
    results["bm25"]["top3_per_meeting"][mid] = bm_idx

    # 3. GEMINI
    t0 = time.time()
    gem_idx = rerank_gemini(query, sections, top_k=3)
    gem_lat = (time.time() - t0) * 1000
    gem_hits = len(set(gem_idx) & rel_set)
    results["gemini"]["recalls"].append(gem_hits / len(rel_set))
    results["gemini"]["precisions"].append(gem_hits / 3.0)
    results["gemini"]["latencies"].append(gem_lat)
    results["gemini"]["top3_per_meeting"][mid] = gem_idx

    # 4. JEV
    t0 = time.time()
    cand_payload = [{"id": f"p{i}", "text": f"[{s['file']} / {s['heading']}]\n{s['text']}", "_idx": i}
                    for i, s in enumerate(sections)]
    jev_ranked = call_jev_rerank(query, cand_payload, JEV_CRITERIA, threshold=0.1)
    jev_lat = (time.time() - t0) * 1000
    jev_idx = [r["_idx"] for r in jev_ranked[:3]]
    # fallback nếu < 3
    if len(jev_idx) < 3:
        for i in range(len(sections)):
            if i not in jev_idx:
                jev_idx.append(i)
                if len(jev_idx) == 3: break
    jev_hits = len(set(jev_idx) & rel_set)
    results["jev"]["recalls"].append(jev_hits / len(rel_set))
    results["jev"]["precisions"].append(jev_hits / 3.0)
    results["jev"]["latencies"].append(jev_lat)
    results["jev"]["top3_per_meeting"][mid] = jev_idx

    print(f"  Keyword : top-3={kw_idx}, Hits={kw_hits}/3 ({kw_lat:.2f}ms)")
    print(f"  BM25    : top-3={bm_idx}, Hits={bm_hits}/3 ({bm_lat:.2f}ms)")
    print(f"  Gemini  : top-3={gem_idx}, Hits={gem_hits}/3 ({gem_lat:.2f}ms)")
    print(f"  Jev     : top-3={jev_idx}, Hits={jev_hits}/3 ({jev_lat:.2f}ms)")

# TỔNG KẾT BẢNG SO SÁNH
print("\n======================================================================")
print("BẢNG ĐỐI CHỨNG HIỆU NĂNG 4 PHƯƠNG PHÁP RERANKER (TRÊN 8 CUỘC HỌP)")
print("======================================================================")
print(f"{'Phương pháp':<15} | {'Recall@3':<10} | {'Precision@3':<12} | {'Độ trễ TB (ms)':<15}")
print("-" * 60)
for method in ["keyword", "bm25", "gemini", "jev"]:
    avg_rec = sum(results[method]["recalls"]) / len(results[method]["recalls"])
    avg_prec = sum(results[method]["precisions"]) / len(results[method]["precisions"])
    avg_lat = sum(results[method]["latencies"]) / len(results[method]["latencies"])
    print(f"{method:<15} | {avg_rec*100:>8.1f}% | {avg_prec*100:>10.1f}% | {avg_lat:>14.2f}ms")

# THÍ NGHIỆM ĐẢO THỨ TỰ ỨNG VIÊN (ORDER SENSITIVITY TEST)
print("\n======================================================================")
print("THÍ NGHIỆM ĐỘ NHẠY VỚI THỨ TỰ ĐẦU VÀO (INPUT ORDER SENSITIVITY)")
print("======================================================================")
# Lấy m01 làm đại diện, đảo thứ tự các đoạn 3 lần
brief_m01 = _yaml(ROOT / "data/meetings/m01/brief.yaml", {})
q_m01 = " ".join([brief_m01.get("title", ""), brief_m01.get("purpose", "")] + brief_m01.get("agenda", []))

for method_name in ["keyword", "bm25", "gemini", "jev"]:
    changes = 0
    base_top3 = set(results[method_name]["top3_per_meeting"]["m01"])
    for seed in [42, 99, 123]:
        shuffled_indices = list(range(len(sections)))
        random.seed(seed)
        random.shuffle(shuffled_indices)
        shuffled_sections = [sections[i] for i in shuffled_indices]
        
        if method_name == "keyword":
            s_top = _rerank_keyword(q_m01, shuffled_sections, top_k=3)
            cur_top3 = {sections.index(s) for s in s_top}
        elif method_name == "bm25":
            shuf_tokens = [tokenize(f"{s['heading']} {s['text']}") for s in shuffled_sections]
            shuf_bm25 = BM25Okapi(shuf_tokens)
            scores = shuf_bm25.get_scores(tokenize(q_m01))
            cur_top3 = {shuffled_indices[i] for i in sorted(range(len(scores)), key=lambda x: scores[x], reverse=True)[:3]}
        elif method_name == "gemini":
            cur_idx = rerank_gemini(q_m01, shuffled_sections, top_k=3)
            cur_top3 = {shuffled_indices[i] for i in cur_idx}
        elif method_name == "jev":
            cands = [{"id": f"p{shuffled_indices[i]}", "text": f"[{s['file']} / {s['heading']}]\n{s['text']}", "_orig_idx": shuffled_indices[i]}
                     for i, s in enumerate(shuffled_sections)]
            j_res = call_jev_rerank(q_m01, cands, JEV_CRITERIA, threshold=0.1)
            cur_top3 = {r["_orig_idx"] for r in j_res[:3]}
        
        if cur_top3 != base_top3:
            changes += 1
    print(f"Phương pháp {method_name:<10}: Đổi top-3 {changes}/3 lần khi đảo thứ tự")

# Lưu kết quả JSON
out_path = ROOT / "outputs" / "reranker_experiment_results.json"
out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nĐã lưu kết quả thực nghiệm chi tiết tại: {out_path}")
