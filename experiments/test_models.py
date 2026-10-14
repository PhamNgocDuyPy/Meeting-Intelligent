import os
import requests
from pathlib import Path

env = Path(".env").read_text(encoding="utf-8")
key = [l.split("=", 1)[1].strip() for l in env.splitlines() if l.startswith("GEMINI_API_KEY=")][0]

models_to_try = [
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-3.1-pro-preview",
    "gemma-4-26b-a4b-it",
    "gemma-4-31b-it",
    "gemini-flash-latest",
]

for m in models_to_try:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
    try:
        r = requests.post(url, headers={"x-goog-api-key": key, "Content-Type": "application/json"}, json={"contents": [{"role":"user", "parts":[{"text":"hi"}]}]}, timeout=15)
        print(f"Model: {m} -> Status: {r.status_code}")
        if r.status_code == 200:
            print("  SUCCESS:", r.text[:100])
        else:
            print("  FAIL:", r.text[:120])
    except Exception as e:
        print(f"Model: {m} -> Exception: {e}")
