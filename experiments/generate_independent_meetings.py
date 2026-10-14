import os
import sys
import time
import json
import re
import hashlib
from pathlib import Path
import requests
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

load_dotenv()

api_key = os.getenv("NVIDIA_API_KEY")
if not api_key:
    print("ERROR: NVIDIA_API_KEY is not set in .env")
    sys.exit(1)

endpoint = "https://integrate.api.nvidia.com/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}
model = "nvidia/nemotron-3-super-120b-a12b"

BASE_DIR = Path("data/independent_tests/meetings")
BASE_DIR.mkdir(parents=True, exist_ok=True)


def call_nemotron(prompt: str, system_prompt: str = "", max_tokens: int = 6144, temperature: float = 0.3) -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    resp = requests.post(endpoint, headers=headers, json=payload, timeout=120)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP Error {resp.status_code}: {resp.text}")

    data = resp.json()
    choice = data["choices"][0]
    msg = choice.get("message", {})
    content = msg.get("content")
    if content is None:
        raise RuntimeError("Model returned None content (reasoning token starvation).")
    return content


def extract_json(raw_text: str):
    clean = raw_text.strip()
    match = re.search(r"```(?:json)?\s*(\{[\s\S]*\}|\[[\s\S]*\])\s*```", clean)
    if match:
        clean = match.group(1)
    else:
        start_obj = clean.find('{')
        end_obj = clean.rfind('}')
        if start_obj != -1 and end_obj > start_obj:
            clean = clean[start_obj:end_obj+1]
    return json.loads(clean)


# Define 6 realistic, diverse meeting scenarios
SCENARIOS = [
    {
        "folder": "indep_m01",
        "title": "Họp lựa chọn Database: Tranh luận MySQL vs MongoDB, cuối cùng đảo sang PostgreSQL",
        "spec": "Cuộc họp kỹ thuật 5 người (Trưởng nhóm: Hoàng, Dev: Sơn, Tuấn, QA: Mai, DevOps: Bình). Ban đầu Sơn đề xuất MongoDB, sau Tuấn phản biện ACID và đề xuất MySQL, cuối cùng Hoàng chốt PostgreSQL. Giao Tuấn dựng DB staging trước thứ Sáu, Mai viết test plan."
    },
    {
        "folder": "indep_m02",
        "title": "Họp ngân sách marketing: Quyết định có điều kiện ràng buộc phê duyệt BOD",
        "spec": "Cuộc họp marketing (Chủ trì: Hương, Media: Long, Content: Trang). Bàn về gói tài trợ sự kiện 200 triệu. Hương kết luận: 'Tạm chốt tham gia gói Kim cương, NHƯNG phải đợi Ban Giám đốc phê duyệt hạn mức trước thứ Ba tuần sau, nếu không duyệt thì hủy'. Quyết định có điều kiện (conditional)."
    },
    {
        "folder": "indep_m03",
        "title": "Họp phân công nhiệm vụ: Người nhận việc rõ ràng vs người chỉ đưa ra góp ý",
        "spec": "Cuộc họp phân công sprint (Scrum Master: Dũng, Dev: Thắng, Linh). Dũng giao Thắng fix bug payment gateway trước 15h mai. Linh chỉ góp ý về UI nhưng không nhận việc code. Kiểm tra xem hệ thống có gán nhầm việc cho Linh hay không."
    },
    {
        "folder": "indep_m04",
        "title": "Họp thẩm quyền: Người phát biểu không có quyền chốt",
        "spec": "Cuộc họp dự án Mobile (PM: Viết, Tester: An, Designer: Huy). Designer Huy tự ý nói 'chốt bỏ màn hình onboarding', nhưng PM Viết là người có thẩm quyền duy nhất về product scope và Viết bác bỏ, giữ lại màn onboarding."
    },
    {
        "folder": "indep_m05",
        "title": "Họp phạm vi MVP vs Phase 2: Chốt cắt bớt tính năng",
        "spec": "Cuộc họp release (Chủ trì: Việt, Tech Lead: Dũng, BA: Nga). Chốt release MVP vào ngày 25/10 chỉ có tính năng thanh toán QR, hoãn tính năng trả góp sang Phase 2. Giao Dũng cập nhật roadmap, Nga báo cho khách hàng."
    },
    {
        "folder": "indep_m06",
        "title": "Họp xử lý sự cố (Incident Post-mortem): Rollback phiên bản và giao điều tra",
        "spec": "Cuộc họp khẩn cấp (CTO: Bách, SRE: Quang, Backend: Thành). Hệ thống bị tràn bộ nhớ sau release v1.4. Bách chốt dứt khoát rollback về v1.3 ngay lập tức. Giao Quang theo dõi metrics sau rollback, Thành trích xuất log để điều tra root cause trước 10h sáng mai."
    }
]


def generate_single_meeting(sc):
    folder = sc["folder"]
    target_dir = BASE_DIR / folder
    target_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n---> Generating {folder}: {sc['title']}")
    prompt = f"""Bạn là chuyên gia mô phỏng dữ liệu hội thoại doanh nghiệp thực tế tại Việt Nam.
Tạo một cuộc họp hoàn chỉnh cho kịch bản sau:
{sc['spec']}

Yêu cầu xuất ra định dạng JSON duy nhất gồm 2 phần:
1. "transcript": Chuỗi văn bản gồm 15-22 câu thoại. Mỗi câu thoại có định dạng chuẩn:
   [hh:mm:ss] Tên: Lời phát biểu...
   (Ngôn ngữ tự nhiên, chân thực, văn phong công sở Việt Nam).

2. "expected": Object ground truth theo đúng cấu trúc chuẩn sau:
{{
  "difficulty": "mô tả ngắn về độ khó và bẫy nghiệp vụ",
  "topics": [
    {{
      "keywords": ["từ khóa 1", "từ khóa 2"],
      "status": "decided / leaning / open / proposed",
      "final_option_keywords": ["tên phương án được chốt"],
      "not_final_keywords": ["phương án bị loại hoặc đề xuất ban đầu"],
      "superseded_keywords": ["phương án ban đầu bị đảo ngược nếu có"],
      "is_conditional": true/false
    }}
  ],
  "tasks": [
    {{
      "keywords": ["từ khóa nhiệm vụ"],
      "assignee": "Tên người nhận",
      "deadline": "YYYY-MM-DD hoặc null"
    }}
  ],
  "items": [
    {{
      "kind": "issue / request",
      "keywords": ["từ khóa vướng mắc hoặc yêu cầu"]
    }}
  ]
}}

Chỉ xuất JSON, không giải thích gì thêm ngoài JSON.
"""
    system_prompt = "You are a professional business transcript generator. Keep reasoning concise and output strict valid JSON."
    raw = call_nemotron(prompt, system_prompt=system_prompt, max_tokens=6144, temperature=0.3)
    data = extract_json(raw)

    transcript_text = data.get("transcript", "")
    expected_data = data.get("expected", {})

    # Save transcript.txt
    (target_dir / "transcript.txt").write_text(transcript_text, encoding="utf-8")
    # Save expected.json
    (target_dir / "expected.json").write_text(json.dumps(expected_data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Saved {folder}/transcript.txt ({len(transcript_text.splitlines())} lines)")
    print(f"Saved {folder}/expected.json")


def main():
    print("=== GENERATING 6 INDEPENDENT MEETINGS USING NEMOTRON 120B ===")
    for sc in SCENARIOS:
        try:
            generate_single_meeting(sc)
            time.sleep(2)
        except Exception as e:
            print(f"Error generating {sc['folder']}: {e}")

    # Calculate SHA-256 for all generated files
    hashes = {}
    for p in sorted(BASE_DIR.glob("**/*")):
        if p.is_file():
            hashes[str(p.relative_to(BASE_DIR))] = hashlib.sha256(p.read_bytes()).hexdigest()

    manifest_path = BASE_DIR / "MANIFEST.json"
    manifest_path.write_text(json.dumps(hashes, indent=2), encoding="utf-8")
    print(f"\nGenerated Manifest at {manifest_path}")


if __name__ == "__main__":
    main()
