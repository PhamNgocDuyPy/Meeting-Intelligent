import sys, json
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.llm import call_jev

subtle_cases = [
    ("Chốt Stripe cho Aurora, nếu anh Phúc xin được ngân sách dưới 2%.", "Stripe", "điều kiện ngầm 'nếu anh Phúc xin được'"),
    ("Ok chốt ngày 19/10, tùy thuộc vào kết quả test của Trang chiều nay.", "ngày 19/10", "điều kiện ngầm 'tùy thuộc vào kết quả'"),
    ("Thống nhất chọn giải pháp A, để xem phản hồi từ đối tác rồi mới tiến hành.", "giải pháp A", "điều kiện ngầm 'để xem phản hồi'"),
    ("Quyết định dùng gói Enterprise, chờ bên Finance duyệt chi phí tuần tới.", "gói Enterprise", "điều kiện ngầm 'chờ bên Finance duyệt'"),
    ("Chốt phương án Supabase, nếu được thì triển khai luôn trong tuần này.", "Supabase", "câu cửa miệng 'nếu được thì' (không phải điều kiện cứng)"),
    ("Ok chốt phương án B, xem thử tuần tới sếp có ý kiến gì không đã.", "phương án B", "điều kiện ngầm 'xem thử sếp có ý kiến'")
]

print("==================================================")
print("KIỂM THỬ JEV TRÊN CÁC CÂU ĐIỀU KIỆN NGẦM / TINH VI")
print("==================================================")

for i, (text, cand, note) in enumerate(subtle_cases):
    state = f"Chủ đề: Quyết định dự án\nPhương án ứng viên: {cand}\n\nCác phát biểu liên quan:\n[00:01:00] Người nói: {text}"
    q = {
        "conditional": {
            "type": "noul",
            "instructions": f"Kết luận phương án '{cand}' có phụ thuộc vào điều kiện chưa xảy ra không?"
        }
    }
    resp = call_jev(state, q)
    answers = resp.get("answers", resp)
    p = answers.get("conditional", {}).get("noul", answers.get("conditional", {}).get("probability", 0.5))
    is_caught = p >= 0.5
    print(f"\nCa {i+1} [{note}]:")
    print(f"  Câu nói: \"{text}\"")
    print(f"  -> Jev conditional p = {p:.3f} | {'BẮT ĐƯỢC' if is_caught else 'BỎ QUA'}")
