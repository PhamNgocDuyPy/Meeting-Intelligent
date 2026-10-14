import os
import sys
import time
import json
import re
import hashlib
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


def call_nemotron(prompt: str, system_prompt: str = "", max_tokens: int = 6144, temperature: float = 0.3, retries: int = 3) -> str:
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

    for attempt in range(retries):
        try:
            start_t = time.time()
            resp = requests.post(endpoint, headers=headers, json=payload, timeout=120)
            elapsed = time.time() - start_t
            if resp.status_code != 200:
                print(f"[Attempt {attempt+1}] HTTP Error {resp.status_code}: {resp.text}")
                time.sleep(2 * (attempt + 1))
                continue

            data = resp.json()
            choice = data["choices"][0]
            msg = choice.get("message", {})
            content = msg.get("content")
            finish_reason = choice.get("finish_reason")

            # Check for the Reasoning Starvation Bug
            if content is None:
                print(f"[Attempt {attempt+1}] BUG DETECTED: content is None! finish_reason={finish_reason}. Retrying with higher max_tokens...")
                payload["max_tokens"] += 2048
                time.sleep(2)
                continue

            print(f"API call successful in {elapsed:.2f}s (finish_reason={finish_reason})")
            return content

        except Exception as e:
            print(f"[Attempt {attempt+1}] Request exception: {e}")
            time.sleep(2 * (attempt + 1))

    raise RuntimeError("Failed to get valid response from NVIDIA API after all retries.")


def extract_json(raw_text: str):
    clean = raw_text.strip()
    match = re.search(r"```(?:json)?\s*(\[[\s\S]*\]|\{[\s\S]*\})\s*```", clean)
    if match:
        clean = match.group(1)
    else:
        # Try finding outermost bracket
        start_arr = clean.find('[')
        end_arr = clean.rfind(']')
        start_obj = clean.find('{')
        end_obj = clean.rfind('}')
        if start_arr != -1 and end_arr > start_arr:
            clean = clean[start_arr:end_arr+1]
        elif start_obj != -1 and end_obj > start_obj:
            clean = clean[start_obj:end_obj+1]
    return json.loads(clean)


def generate_60_conditional_sentences():
    print("\n=======================================================")
    print("GENERATING 60 DIVERSE VIETNAMESE CONDITIONAL TEST CASES")
    print("Model: nvidia/nemotron-3-super-120b-a12b (Independent 3rd-party)")
    print("=======================================================")

    prompt = """Bạn là chuyên gia ngôn ngữ học và thẩm định hội thoại kinh doanh tiếng Việt độc lập.
Nhiệm vụ của bạn là tạo ra một bộ dữ liệu kiểm thử gồm CHÍNH XÁC 60 câu phát biểu ngắn trong các cuộc họp doanh nghiệp tại Việt Nam.

Yêu cầu phân chia cân bằng:
1. 30 câu CÓ ĐIỀU KIỆN (is_conditional = true):
   - Quyết định hoặc kế hoạch chưa chốt dứt khoát, phụ thuộc vào điều kiện tiên quyết chưa diễn ra.
   - Phải phân bổ đa dạng qua các khía cạnh:
     * Phụ thuộc ngân sách/giá cả (ví dụ: chờ báo giá, phụ thuộc đàm phán giảm giá, nếu kế toán cân đối...)
     * Phụ thuộc phê duyệt cấp trên/khách hàng (ví dụ: chờ chị Linh gật đầu, nếu BOD duyệt, trình ban giám đốc...)
     * Phụ thuộc kỹ thuật/PoC/kiểm thử (ví dụ: nếu test tải dưới 500ms, xem bên thứ 3 mở API, thử nghiệm tuần này...)
     * Điều kiện ngầm/dè dặt tự nhiên (ví dụ: "để xem tình hình bên xưởng", "nếu đối tác phản hồi trước thứ Sáu", "tùy vào lượng đơn đợt sale...")
   - KHÔNG dùng cấu trúc rập khuôn máy móc. Hãy dùng ngôn ngữ nói đời thường của dân công sở Việt Nam.

2. 30 câu KHÔNG CÓ ĐIỀU KIỆN / ĐÃ CHỐT DỨT KHOÁT (is_conditional = false):
   - Quyết định đã thông qua, giao việc rõ ràng, hoặc khẳng định chắc chắn.
   - Bao gồm các trường hợp bẫy (hard negatives):
     * Câu có từ "nếu" nhưng chỉ là giả định cách xử lý tình huống phát sinh sau khi ĐÃ CHỐT (ví dụ: "Đã chốt chọn NCC An Phát, nếu có lỗi thì gọi họ bảo hành").
     * Câu khẳng định dứt khoát: "Chốt phương án migrate lên AWS vào ngày 20 tới, không bàn lùi nữa."
     * Phân công nhiệm vụ trực tiếp: "Tuấn phụ trách viết tài liệu kỹ thuật và gửi trước 17h mai."

Yêu cầu định dạng đầu ra:
Trả về DUY NHẤT một mảng JSON (không có lời mở đầu hay kết thúc):
[
  {
    "id": "c01" .. "c30" (cho nhóm true) hoặc "u01" .. "u30" (cho nhóm false),
    "text": "câu phát biểu tiếng Việt tự nhiên",
    "is_conditional": true/false,
    "category": "budget / approval / technical / timing / definitive / task_assignment / hard_negative",
    "rationale": "giải thích ngắn gọn vì sao có hoặc không có điều kiện"
  }
]
"""
    system_prompt = "You are an expert NLP annotator for business Vietnamese. Provide exhaustive, diverse, realistic examples in strict JSON format. Keep reasoning concise."

    raw = call_nemotron(prompt, system_prompt=system_prompt, max_tokens=8192, temperature=0.4)
    data = extract_json(raw)
    
    print(f"\nSuccessfully generated {len(data)} items!")
    cond_count = sum(1 for x in data if x.get("is_conditional") is True)
    uncond_count = sum(1 for x in data if x.get("is_conditional") is False)
    print(f"Summary: {cond_count} Conditional, {uncond_count} Unconditional")

    output_path = "data/independent_tests/conditional_sentences_60.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # Calculate SHA-256
    with open(output_path, "rb") as f:
        sha256 = hashlib.sha256(f.read()).hexdigest()
    
    print(f"Saved to: {output_path}")
    print(f"SHA-256 Hash: {sha256}")
    return output_path, sha256


if __name__ == "__main__":
    generate_60_conditional_sentences()
