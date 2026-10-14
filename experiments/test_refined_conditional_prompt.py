import sys, os, time, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.llm import call_jev

cases = [
    # Nhóm 1: Điều kiện thật (True condition - bắt buộc phải cắm cờ hoặc hạ cấp)
    {
        "id": "m05_true_cond",
        "name": "m05: Điều kiện bên thứ ba",
        "text": "Huy: Ok, chốt Stripe, với điều kiện Phúc xác nhận phí giao dịch tổng cộng dưới 2%.\nPhúc: Mình cần hỏi lại bên Stripe, chưa có số chính thức.",
        "cand": "Stripe",
        "is_real_condition": True
    },
    {
        "id": "g06_true_cond",
        "name": "g06: Điều kiện kết quả kiểm thử",
        "text": "Minh: Chốt bản v1.2 phát hành ngày 20/11, chỉ khi QA test xong toàn bộ luồng thanh toán.\nLan: Bên QA vẫn đang chạy test, chưa xong.",
        "cand": "ngày 20/11",
        "is_real_condition": True
    },
    {
        "id": "implicit_1_true_cond",
        "name": "Điều kiện ngầm 1: Tùy thuộc kết quả",
        "text": "Huy: Chốt ngày 19/10, tùy thuộc vào kết quả test chiều nay.",
        "cand": "ngày 19/10",
        "is_real_condition": True
    },
    {
        "id": "implicit_2_true_cond",
        "name": "Điều kiện ngầm 2: Để xem phản hồi",
        "text": "Nam: Thống nhất chọn giải pháp A, để xem phản hồi từ đối tác rồi mới tiến hành.",
        "cand": "giải pháp A",
        "is_real_condition": True
    },

    # Nhóm 2: Điều kiện của hành động làm sau hoặc câu cửa miệng (False condition - KHÔNG được coi là điều kiện chốt)
    {
        "id": "m06_post_action",
        "name": "m06: Bật tính năng sau khi release (Feature flag)",
        "text": "Huy: Ok, chốt ngày release thứ Hai 19/10 nhé.\nTrang: Phần tính năng thanh toán mình sẽ bật sau khi test xong, tạm thời tắt bằng feature flag.",
        "cand": "thứ Hai 19/10",
        "is_real_condition": False
    },
    {
        "id": "hedge_action_preference",
        "name": "Câu cửa miệng: Nếu được thì làm luôn",
        "text": "Minh: Chốt phương án Supabase cho backend, nếu được thì triển khai luôn trong tuần này nhé.",
        "cand": "Supabase",
        "is_real_condition": False
    },
    {
        "id": "g12_reluctance",
        "name": "g12: Miễn cưỡng đồng ý (Vẫn lo nhưng làm theo)",
        "text": "Hà: Vậy thống nhất làm theo phương án của Quân nhé.\nMinh: Ok, mình vẫn lo nhưng sẽ làm theo.",
        "cand": "phương án của Quân",
        "is_real_condition": False
    }
]

print("======================================================================")
print("TEST HỒI QUY CÂU HỎI ĐIỀU KIỆN JEV (CŨ VS MỚI CÓ LOẠI TRỪ HÀNH ĐỘNG SAU)")
print("======================================================================")

q_old_template = "Kết luận phương án '{cand}' có phụ thuộc vào điều kiện chưa xảy ra không?"
q_new_template = (
    "Việc chốt phương án '{cand}' có bị ràng buộc bởi điều kiện tiên quyết nào "
    "chưa được đáp ứng trước khi quyết định có hiệu lực không? "
    "(KHÔNG tính các điều kiện áp dụng cho hành động triển khai hoặc việc làm sau khi quyết định đã chốt; "
    "KHÔNG tính các câu bày tỏ sở thích như 'nếu được thì')."
)

results = []

for c in cases:
    cand = c["cand"]
    state_text = f"Phát biểu trong cuộc họp:\n{c['text']}"
    
    # 1. Câu hỏi cũ
    q_old = q_old_template.format(cand=cand)
    r_old = call_jev(state_text, {"cond": {"type": "noul", "instructions": q_old}}, use_cache=False)
    p_old = r_old.get("answers", {}).get("cond", {}).get("noul", 0.5)
    
    # 2. Câu hỏi mới
    q_new = q_new_template.format(cand=cand)
    r_new = call_jev(state_text, {"cond": {"type": "noul", "instructions": q_new}}, use_cache=False)
    p_new = r_new.get("answers", {}).get("cond", {}).get("noul", 0.5)
    
    results.append({
        "name": c["name"],
        "is_real_condition": c["is_real_condition"],
        "p_old": p_old,
        "p_new": p_new,
        "old_flagged": p_old >= 0.5,
        "new_flagged": p_new >= 0.5
    })
    
    print(f"--- {c['name']} (Kỳ vọng cắm cờ điều kiện: {c['is_real_condition']}) ---")
    print(f"  Câu hỏi cũ: p={p_old:.3f} -> {'CẮM CỜ' if p_old >= 0.5 else 'BỎ QUA'}")
    print(f"  Câu hỏi mới: p={p_new:.3f} -> {'CẮM CỜ' if p_new >= 0.5 else 'BỎ QUA'}")

print("\n" + "="*70)
print(f"{'Tình huống kiểm thử':<35} | {'Loại':<10} | {'p cũ':<8} | {'p mới':<8} | {'Cải thiện'}")
print("-" * 70)
for r in results:
    exp = "Thật" if r["is_real_condition"] else "Giả"
    old_ok = (r["old_flagged"] == r["is_real_condition"])
    new_ok = (r["new_flagged"] == r["is_real_condition"])
    diff = "Giữ đúng" if (old_ok and new_ok) else ("SỬA ĐƯỢC" if (not old_ok and new_ok) else "Chưa đổi")
    print(f"{r['name']:<35} | {exp:<10} | {r['p_old']:<8.2f} | {r['p_new']:<8.2f} | {diff}")

out_path = ROOT / "outputs" / "conditional_regression_results.json"
out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nĐã lưu kết quả tại: {out_path}")
