import os
import sys
import time
import json
import requests
from dotenv import load_dotenv

# Ensure UTF-8 output on Windows console
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

print(f"=== NVIDIA API BENCHMARK & BUG CHECK ===")
print(f"Model: {model}")
print(f"Endpoint: {endpoint}\n")

# Test 1: Simple ping
print("--- TEST 1: Ping / Latency Check ---")
start = time.time()
try:
    payload_1 = {
        "model": model,
        "messages": [
            {"role": "user", "content": "Trả lời ngắn gọn bằng JSON: {\"status\": \"ok\", \"message\": \"ping\"}"}
        ],
        "temperature": 0.1,
        "max_tokens": 2048
    }
    resp = requests.post(endpoint, headers=headers, json=payload_1, timeout=60)
    elapsed = time.time() - start
    print(f"Status Code: {resp.status_code}")
    print(f"Total Time: {elapsed:.2f}s")
    if resp.status_code == 200:
        data = resp.json()
        choice = data["choices"][0]
        msg = choice.get("message", {})
        usage = data.get("usage", {})
        print(f"Finish Reason: {choice.get('finish_reason')}")
        print(f"Reasoning Tokens: {usage.get('completion_tokens_details', {}).get('reasoning_tokens')}")
        print(f"Output Tokens: {usage.get('completion_tokens', 0) - usage.get('completion_tokens_details', {}).get('reasoning_tokens', 0)}")
        print(f"Total Tokens: {usage.get('total_tokens')}")
        print(f"Content: {msg.get('content')}\n")
    else:
        print(f"Error: {resp.text}\n")
except Exception as e:
    print(f"Test 1 Failed: {e}\n")

# Test 2: Test Bug Case (Low max_tokens leading to content=None)
print("--- TEST 2: Investigating Bug (Low max_tokens truncation) ---")
try:
    payload_2 = {
        "model": model,
        "messages": [
            {"role": "user", "content": "Hãy phân tích chi tiết quy trình họp và xuất ra JSON gồm 3 quyết định giả định."}
        ],
        "temperature": 0.2,
        "max_tokens": 150  # Very low to trigger reasoning token overflow
    }
    start = time.time()
    resp = requests.post(endpoint, headers=headers, json=payload_2, timeout=60)
    elapsed = time.time() - start
    print(f"Status Code: {resp.status_code}")
    print(f"Total Time: {elapsed:.2f}s")
    if resp.status_code == 200:
        data = resp.json()
        choice = data["choices"][0]
        msg = choice.get("message", {})
        finish = choice.get("finish_reason")
        print(f"Finish Reason: {finish}")
        print(f"Content is None: {msg.get('content') is None}")
        print(f"Content: {msg.get('content')}")
        print(f"Has reasoning: {bool(msg.get('reasoning_content'))}")
        print("-> BUG CONFIRMED: When max_tokens is small, reasoning fills max_tokens, finish_reason='length', and content is None!\n")
except Exception as e:
    print(f"Test 2 Failed: {e}\n")

# Test 3: Realistic Generation (Vietnamese Test Cases with max_tokens=4096)
print("--- TEST 3: Generating Test Cases (max_tokens=4096) ---")
prompt_test_gen = """Bạn là chuyên gia thẩm định dữ liệu hội thoại tiếng Việt.
Hãy tạo 4 câu phát biểu trong cuộc họp tiếng Việt thực tế:
- 2 câu có điều kiện/chưa chốt (ví dụ: phụ thuộc ngân sách, chờ sếp duyệt, tùy tình hình...)
- 2 câu đã chốt dứt khoát / không điều kiện.

Yêu cầu xuất ĐÚNG định dạng JSON sau (không markdown codeblock ngoài JSON):
[
  {
    "id": "test_01",
    "text": "câu phát biểu...",
    "is_conditional": true,
    "condition_type": "budget/approval/schedule/other",
    "explanation": "lý do"
  }
]
"""
try:
    payload_3 = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant. Keep internal reasoning concise and output valid JSON."},
            {"role": "user", "content": prompt_test_gen}
        ],
        "temperature": 0.2,
        "max_tokens": 4096
    }
    start = time.time()
    resp = requests.post(endpoint, headers=headers, json=payload_3, timeout=120)
    elapsed = time.time() - start
    print(f"Status Code: {resp.status_code}")
    print(f"Total Time: {elapsed:.2f}s")
    if resp.status_code == 200:
        data = resp.json()
        choice = data["choices"][0]
        msg = choice.get("message", {})
        content = msg.get("content", "")
        usage = data.get("usage", {})
        print(f"Finish Reason: {choice.get('finish_reason')}")
        print(f"Reasoning Tokens: {usage.get('completion_tokens_details', {}).get('reasoning_tokens')}")
        print(f"Total Completion Tokens: {usage.get('completion_tokens')}")
        print(f"Generation Speed: {usage.get('completion_tokens', 0) / max(elapsed, 0.01):.1f} tokens/s")
        print("Raw Content Preview:")
        print(content[:500] if content else "NONE")
        
        # Test JSON parsing
        try:
            # Strip markdown if any
            clean_json = content.strip()
            if clean_json.startswith("```json"):
                clean_json = clean_json[7:]
            if clean_json.startswith("```"):
                clean_json = clean_json[3:]
            if clean_json.endswith("```"):
                clean_json = clean_json[:-3]
            clean_json = clean_json.strip()
            parsed = json.loads(clean_json)
            print(f"\nJSON parsed successfully! Total items: {len(parsed)}")
            for item in parsed:
                print(f"  - [{item.get('id')}] (cond={item.get('is_conditional')}): {item.get('text')}")
        except Exception as je:
            print(f"\nJSON parsing error: {je}")
except Exception as e:
    print(f"Test 3 Failed: {e}")
