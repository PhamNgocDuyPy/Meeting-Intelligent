import sys, os, time, json, random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.context import _policy_sections, _rerank_keyword, _yaml, norm_plain
from rank_bm25 import BM25Okapi

# Sinh 200 đoạn chính sách hành chính / nhân sự / văn phòng làm nhiễu
TOPICS = [
    ("công tác phí", "Quy định thanh toán tiền ăn ở và đi lại khi đi công tác xa."),
    ("trang phục", "Quy tắc trang phục công sở vào các ngày làm việc trong tuần."),
    ("nghỉ phép năm", "Thủ tục xin nghỉ phép năm và số ngày phép tồn tối đa."),
    ("bảo hiểm xã hội", "Chính sách đóng bảo hiểm và chế độ thai sản, ốm đau."),
    ("văn phòng phẩm", "Quy trình đăng ký mua bút, giấy in, kẹp tài liệu hàng tháng."),
    ("gửi xe", "Chính sách hỗ trợ vé gửi xe máy và ô tô tại tầng hầm tòa nhà."),
    ("tiếp khách", "Hạn mức chi tiêu tiếp khách đối tác cho các cấp quản lý."),
    ("quẹt thẻ chấm công", "Thời gian quẹt thẻ vào ca và quy định phạt đi muộn."),
    ("làm việc từ xa", "Điều kiện đăng ký làm việc remote tối đa 2 ngày mỗi tháng."),
    ("thiết bị máy tính", "Quy định cấp phát laptop và bảo hành linh kiện định kỳ."),
    ("vệ sinh phòng họp", "Quy định dọn dẹp bảng trắng và tắt máy chiếu sau khi họp."),
    ("đào tạo nội bộ", "Chính sách hỗ trợ kinh phí thi chứng chỉ và khóa học online."),
    ("thưởng lễ tết", "Tiêu chuẩn xét thưởng các dịp Quốc khánh, Tết Dương lịch."),
    ("khám sức khỏe", "Lịch khám sức khỏe định kỳ hàng năm cho toàn thể nhân viên."),
    ("quà sinh nhật", "Chính sách tặng quà và tổ chức sinh nhật cho thành viên team."),
    ("mượn chìa khóa", "Quy trình mượn chìa khóa kho và phòng máy chủ ngoài giờ."),
    ("pha cà phê", "Hướng dẫn sử dụng máy pha cà phê và giữ vệ sinh khu pantry."),
    ("sử dụng wifi", "Quy định không dùng wifi công ty để tải phim hay chơi game."),
    ("quản lý tài sản", "Thủ tục bàn giao màn hình và tai nghe khi chuyển dự án."),
    ("khen thưởng sáng kiến", "Tiêu chí chấm điểm và trao giải cho sáng kiến cải tiến quy trình.")
]

def generate_distractors(n: int = 200) -> list[dict]:
    distractors = []
    # Từ khóa mồi gây nhiễu để bẫy thuật toán từ khóa
    bait_words = ["báo cáo", "tiến độ", "kỹ thuật", "hạ tầng", "chốt", "quyết định", "hạn hoàn thành", "người nhận", "dự án", "phân việc"]
    
    for i in range(n):
        topic, desc = TOPICS[i % len(TOPICS)]
        bait = random.sample(bait_words, 2)
        text = (
            f"Chính sách số {i+1} về {topic}: {desc} "
            f"Lưu ý: Mọi việc cần có {bait[0]} cụ thể và tuân thủ {bait[1]} của công ty. "
            f"Người phụ trách bộ phận hành chính sẽ theo dõi và ghi nhận vào hệ thống nội bộ."
        )
        distractors.append({
            "file": f"admin_policy_{i+1:03d}.md",
            "heading": f"Quy định về {topic} (Mục {i+1})",
            "text": text,
            "is_distractor": True
        })
    return distractors

def run_noise_experiment():
    policy_dir = ROOT / "data/company/policies"
    orig_sections = _policy_sections(policy_dir)
    for s in orig_sections:
        s["is_distractor"] = False
        
    distractors = generate_distractors(200)
    
    # Cuộc họp m01 làm mốc: liên quan [0, 2, 6, 8, 9]
    brief = _yaml(ROOT / "data/meetings/m01/brief.yaml", {})
    query = " ".join([brief.get("title", ""), brief.get("purpose", "")] + brief.get("agenda", []))
    rel_ids = {0, 2, 6, 8, 9}
    
    scales = [0, 20, 50, 100, 200]
    print("======================================================================")
    print("THỰC NGHIỆM ĐỘ BỀN VỚI NHIỄU (NOISE SCALING EXPERIMENT)")
    print("Đo lường mức độ suy giảm của Lọc từ khóa vs BM25 khi thêm đoạn nhiễu")
    print("======================================================================")
    print(f"Truy vấn m01: '{query}'")
    print(f"{'Số đoạn nhiễu':<15} | {'Tổng đoạn':<10} | {'Keyword Precision@3':<22} | {'BM25 Precision@3':<20}")
    print("-" * 75)
    
    def tokenize(text: str) -> list[str]:
        norm = norm_plain(text)
        return [t for t in norm.split() if len(t) >= 2]
    
    for n in scales:
        corpus = list(orig_sections) + distractors[:n]
        
        # 1. Keyword
        kw_res = _rerank_keyword(query, corpus, top_k=3)
        kw_hits = sum(1 for s in kw_res if not s.get("is_distractor", False) and orig_sections.index(s) in rel_ids)
        kw_prec = kw_hits / 3.0
        
        # 2. BM25
        c_tokens = [tokenize(f"{s['heading']} {s['text']}") for s in corpus]
        bm = BM25Okapi(c_tokens)
        scores = bm.get_scores(tokenize(query))
        top_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:3]
        bm_hits = sum(1 for idx in top_idx if idx < len(orig_sections) and idx in rel_ids)
        bm_prec = bm_hits / 3.0
        
        print(f"{n:<15} | {len(corpus):<10} | {kw_prec*100:>20.1f}% | {bm_prec*100:>18.1f}%")

if __name__ == "__main__":
    run_noise_experiment()
