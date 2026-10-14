import os
import requests
from pathlib import Path

env = Path(".env").read_text(encoding="utf-8")
key = None
for line in env.splitlines():
    if line.startswith("GEMINI_API_KEY="):
        key = line.split("=", 1)[1].strip()

# Let's test with gemini-2.5-flash-lite or gemini-flash-latest or gemini-2.5-pro or gemini-3.8-flash
for model in ["gemini-2.5-flash-lite", "gemini-flash-latest", "gemini-2.5-pro", "gemini-3.8-flash"]:
    print(f"Testing model: {model} with 45s timeout...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": "Hi, reply 1 word: OK"}]}],
    }
    try:
        r = requests.post(url, headers={"x-goog-api-key": key, "Content-Type": "application/json"}, json=payload, timeout=45)
        print(f"Result for {model}: HTTP {r.status_code}")
        if r.status_code == 200:
            print("Response:", r.json()['candidates'][0]['content']['parts'][0]['text'])
            break
        else:
            print("Error text:", r.text[:200])
    except Exception as e:
        print(f"Exception for {model}: {e}")
