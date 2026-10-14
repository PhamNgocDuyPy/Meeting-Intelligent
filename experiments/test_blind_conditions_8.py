import sys, os, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.llm import call_jev, generate_json, _load_dotenv
from src.schema import JudgeVerdict

_load_dotenv()

TEST_CASES = [
    # Must flag (phải cắm cờ - điều kiện tiên quyết thật)
    {
        "id": "C1",
        "cand": "Stripe",
        "text": "[00:05:00] Huy: Chốt Stripe, nhưng phải đợi pháp chế ký xong hợp đồng đã.",
        "must_flag": True,
        "note": "Phụ thuộc ký hợp đồng pháp chế"
    },
    {
        "id": "C2",
        "cand": "gói Pro",
        "text": "[00:06:15] Phúc: Ok thống nhất dùng gói Pro, miễn là Finance duyệt ngân sách trước thứ Sáu.",
        "must_flag": True,
        "note": "Phụ thuộc Finance duyệt ngân sách"
    },
    {
        "id": "C3",
        "cand": "Supabase",
        "text": "[00:08:30] Minh: Quyết định giữ Supabase, trừ khi bên bảo mật không cho lưu dữ liệu ở nước ngoài.",
        "must_flag": True,
        "note": "Điều kiện phủ quyết từ bảo mật"
    },
    {
        "id": "C4",
        "cand": "thứ Hai",
        "text": "[00:10:00] Huy: Chốt release thứ Hai, còn nếu QA tìm ra lỗi mức cao thì dời lại.",
        "must_flag": True,
        "note": "Điều kiện phụ thuộc kết quả QA"
    },
    # Must NOT flag (không được cắm cờ - triển khai sau hoặc khẩu ngữ)
    {
        "id": "C5",
        "cand": "Supabase",
        "text": "[00:04:20] Minh: Chốt Supabase, tiện thì mình cũng chuyển luôn dữ liệu cũ sang tuần này.",
        "must_flag": False,
        "note": "Việc tiện thể làm kèm sau khi chốt"
    },
    {
        "id": "C6",
        "cand": "thứ Hai",
        "text": "[00:09:40] Huy: Quyết định release thứ Hai; sau release Trang sẽ bật tính năng chat dần theo tỷ lệ.",
        "must_flag": False,
        "note": "Kế hoạch bật tính năng sau khi release"
    },
    {
        "id": "C7",
        "cand": "Playwright",
        "text": "[00:07:10] Nam: Thống nhất dùng Playwright, ai rảnh thì viết thêm test cho giỏ hàng.",
        "must_flag": False,
        "note": "Gợi ý làm thêm tự nguyện"
    },
    {
        "id": "C8",
        "cand": "gói Standard",
        "text": "[00:11:00] Hà: Chốt gói Standard, sau này cần thì nâng cấp.",
        "must_flag": False,
        "note": "Dự định tương lai xa"
    },
]

print("======================================================================")
print("BỘ THỬ ĐIỀU KIỆN 8 CÂU ĐỘC LẬP (BLIND EVALUATION)")
print("======================================================================")

results = []

for c in TEST_CASES:
    cand = c["cand"]
    instructions = (
        f"Việc chốt phương án '{cand}' có bị ràng buộc bởi điều kiện tiên quyết (prerequisite) nào "
        f"chưa được đáp ứng trước khi quyết định có hiệu lực không? "
        f"(Chỉ tính điều kiện để phê duyệt quyết định; không tính kế hoạch triển khai sau khi quyết định đã chốt, "
        f"và không tính các câu nói phụ họa hoặc nguyện vọng cá nhân)."
    )
    
    # 1. Gọi Jev
    jev_p = 0.5
    try:
        resp = call_jev(c["text"], {"conditional": {"type": "noul", "instructions": instructions}}, use_cache=False)
        answers = resp.get("answers", resp)
        q = answers.get("conditional", {})
        jev_p = q.get("noul", q.get("probability", 0.5))
    except Exception as e:
        print(f"Jev err {c['id']}: {e}")
        
    # 2. Gọi Gemini
    gem_p, gem_ans = 0.5, False
    try:
        user_prompt = f"Phát biểu: {c['text']}\nPhương án ứng viên: '{cand}'\n\nCâu hỏi: Việc chốt phương án '{cand}' có bị ràng buộc bởi điều kiện tiên quyết nào chưa được đáp ứng trước khi quyết định có hiệu lực không? (Không tính kế hoạch triển khai sau khi đã chốt)."
        g_res = generate_json("gemini", "Bạn là bộ chấm thẩm định quyết định. Trả về JSON: {'conditional': {'answer': bool, 'p': float, 'why': str}}", user_prompt, dict, use_cache=False)
        cond_info = g_res.get("conditional", {})
        gem_ans = cond_info.get("answer", False)
        gem_p = cond_info.get("p", 1.0 if gem_ans else 0.0)
    except Exception as e:
        print(f"Gemini err {c['id']}: {e}")

    results.append({
        "id": c["id"],
        "cand": c["cand"],
        "text": c["text"],
        "must_flag": c["must_flag"],
        "note": c["note"],
        "jev_p": round(jev_p, 3),
        "jev_flagged": jev_p >= 0.5,
        "gem_p": round(gem_p, 3),
        "gem_flagged": gem_ans,
    })

print(f"{'ID':<4} | {'Kỳ vọng':<14} | {'Jev p':<8} | {'Jev Flag?':<10} | {'Gemini p':<8} | {'Gem Flag?':<10} | {'Mô tả'}")
print("-" * 88)
for r in results:
    exp = "PHẢI CẮM CỜ" if r["must_flag"] else "KHÔNG CẮM"
    jf = "YES" if r["jev_flagged"] else "no"
    gf = "YES" if r["gem_flagged"] else "no"
    print(f"{r['id']:<4} | {exp:<14} | {r['jev_p']:<8.3f} | {jf:<10} | {r['gem_p']:<8.3f} | {gf:<10} | {r['note']}")
print("-" * 88)
# Jev metrics
jev_tp = sum(1 for r in results if r["must_flag"] and r["jev_flagged"])
jev_fp = sum(1 for r in results if not r["must_flag"] and r["jev_flagged"])
jev_rec = jev_tp / 4.0
jev_fpr = jev_fp / 4.0

# Gemini metrics
gem_tp = sum(1 for r in results if r["must_flag"] and r["gem_flagged"])
gem_fp = sum(1 for r in results if not r["must_flag"] and r["gem_flagged"])
gem_rec = gem_tp / 4.0
gem_fpr = gem_fp / 4.0

print(f"Jev System One: Recall = {jev_rec*100:.1f}% ({jev_tp}/4), False Positive Rate = {jev_fpr*100:.1f}% ({jev_fp}/4)")
print(f"Gemini LLM:     Recall = {gem_rec*100:.1f}% ({gem_tp}/4), False Positive Rate = {gem_fpr*100:.1f}% ({gem_fp}/4)")

out_path = ROOT / "outputs" / "blind_conditions_8_results.json"
out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nĐã lưu kết quả tại: {out_path}")

