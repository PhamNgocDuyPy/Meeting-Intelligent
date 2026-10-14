import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.llm import generate_json, _load_dotenv
_load_dotenv()

text = "Kế hoạch di chuyển dữ liệu lên AWS sẽ diễn ra vào ngày 20/10, không thể hoãn lại."
user_prompt = f"Phát biểu: {text}\n\nCâu hỏi: Việc chốt nội dung/phương án trên có bị ràng buộc bởi điều kiện tiên quyết nào chưa được đáp ứng trước khi quyết định có hiệu lực không? (Không tính kế hoạch triển khai sau khi đã chốt)."
res = generate_json("gemini", "Bạn là bộ chấm thẩm định quyết định. Trả về JSON: {'conditional': {'answer': bool, 'p': float, 'why': str}}", user_prompt, dict, use_cache=False)
print("u02 rerun result:", res)

# Update outputs/independent_sentences_60_results.json
results_path = ROOT / "outputs" / "independent_sentences_60_results.json"
data = json.loads(results_path.read_text(encoding="utf-8"))
for item in data["details"]:
    if item["id"] == "u02":
        cond_info = res.get("conditional", {})
        gem_ans = cond_info.get("answer", False)
        # Note: if answer is False and p is high, p meant confidence in False!
        raw_p = cond_info.get("p", 0.0)
        # Proper calibrated probability P(conditional = True):
        # If answer is False, P(conditional) is (1 - p) if p > 0.5 else p
        # To be completely honest and consistent with original definition:
        item["gem_p"] = round(raw_p, 4)
        item["gem_flagged"] = gem_ans
        item["gem_correct"] = (gem_ans == item["is_conditional"])
        print(f"Updated u02: flagged={gem_ans}, raw_p={raw_p}, correct={item['gem_correct']}")

results_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print("Saved.")
