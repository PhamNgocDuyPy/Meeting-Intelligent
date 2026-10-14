import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

data = json.load(open("outputs/independent_meetings_e2e_results.json", encoding="utf-8"))
base = data["baseline_gemini_none"]

for mid, info in base.items():
    sc = info["score"]
    t_path = ROOT / "data/independent_tests/meetings" / mid / "transcript.txt"
    transcript = t_path.read_text(encoding="utf-8") if t_path.exists() else ""
    
    print(f"======================================================================")
    print(f"CUỘC HỌP: {mid}")
    print(f"======================================================================")
    print(f"Mô tả độ khó (Gold difficulty): {sc.get('difficulty')}")
    print(f"Kết quả thô tự động: Critical={sc.get('critical_errors')}, Conservative Misses={sc.get('conservative_misses')}")
    print(f"Danh sách vấn đề (Problems): {sc.get('problems')}")
    
    print("\n[TRANSCRIPT TOÀN VĂN]:")
    print(transcript.strip())
    
    print("\n[CHI TIẾT CHẤM CHỦ ĐỀ (TOPICS)]:")
    for t in sc.get("topics", []):
        print(f"  * Kỳ vọng: {t.get('keywords')} -> status: {t.get('expected')}")
        print(f"    Thực tế: status='{t.get('actual')}', final_option='{t.get('final_option')}', superseded={t.get('superseded')}")
        print(f"    Đạt (ok): {t.get('ok')}")
        
    print("\n[CHI TIẾT CHẤM CÔNG VIỆC (TASKS)]:")
    for tk in sc.get("tasks", []):
        print(f"  * Kỳ vọng: {tk.get('keywords')} -> Assignee: '{tk.get('expected_assignee')}', Deadline: '{tk.get('expected_deadline')}'")
        print(f"    Thực tế: Tìm thấy={tk.get('found')}, Assignee='{tk.get('actual_assignee')}' (ok={tk.get('assignee_ok')}), Deadline='{tk.get('actual_deadline')}' (ok={tk.get('deadline_ok')})")
    print("\n")
