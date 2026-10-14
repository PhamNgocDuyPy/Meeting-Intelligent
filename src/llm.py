"""Gọi LLM (Gemini) và bộ chấm (Jev qua OpenCode API) -> JSON đã kiểm schema. Có cache đĩa để chạy lại miễn phí.

Biến môi trường (xem .env.example):
  GEMINI_API_KEY, GEMINI_MODEL
  JEV_BASE_URL, JEV_API_KEY, JEV_MODEL
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Type, TypeVar

import requests
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)
CACHE_DIR = Path(__file__).resolve().parent.parent / "outputs" / "cache"


class LLMError(RuntimeError):
    pass


def _load_dotenv():
    env = Path(__file__).resolve().parent.parent / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            return json.loads(m.group(0))
        raise


def _post_with_retry(url: str, headers: dict, payload: dict, tries: int = 5, timeout: int = 120) -> dict:
    last = None
    for i in range(tries):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=timeout)
            if r.status_code in (429, 500, 502, 503, 504):
                last = f"HTTP {r.status_code}: {r.text[:200]}"
                time.sleep(min(2 ** i * 2, 30))
                continue
            if r.status_code >= 400:
                raise LLMError(f"HTTP {r.status_code}: {r.text[:400]}")
            return r.json()
        except requests.RequestException as e:
            last = str(e)
            time.sleep(min(2 ** i * 2, 30))
    raise LLMError(f"Hết số lần thử: {last}")


def call_gemini_text(system: str, user: str, temperature: float = 0.0) -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise LLMError("Thiếu GEMINI_API_KEY (đặt trong .env hoặc biến môi trường).")
    model = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"temperature": temperature, "responseMimeType": "application/json"},
    }
    data = _post_with_retry(url, {"x-goog-api-key": key, "Content-Type": "application/json"}, payload)
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise LLMError(f"Phản hồi Gemini không hợp lệ: {str(data)[:300]}")


def _jev_config() -> tuple[str, str, str]:
    """Trả về (base_url, api_key, model) cho Jev/OpenCode."""
    base = os.environ.get("JEV_BASE_URL")
    key = os.environ.get("OPENCODE_API_KEY") or os.environ.get("JEV_API_KEY")
    model = os.environ.get("JEV_MODEL", "jev-1.13-free")
    if not (base and key):
        raise LLMError("Thiếu JEV_BASE_URL / OPENCODE_API_KEY (đặt trong .env hoặc biến môi trường).")
    return base.rstrip("/"), key, model


def call_jev(state: str, questions: dict, use_cache: bool = True) -> dict:
    """Gọi Jev qua OpenCode /systemone endpoint.

    Args:
        state: văn bản ngữ cảnh (transcript, đoạn policy, v.v.)
        questions: dict câu hỏi, mỗi key là question_id, value là dict với
                   type ("noul"|"choice"|"score"), instructions, và criteria (tuỳ type).
    Returns:
        dict kết quả gốc từ Jev (chứa key cho mỗi question_id).
    """
    base, key, model = _jev_config()

    # Cache theo nội dung câu hỏi
    cache_key = hashlib.sha256(json.dumps({"model": model, "state": state, "questions": questions},
                                          ensure_ascii=False).encode()).hexdigest()[:24]
    cache_file = CACHE_DIR / f"jev_{cache_key}.json"
    if use_cache and cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))

    payload = {"model": model, "state": state, "questions": questions}
    data = _post_with_retry(base, {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, payload)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def call_jev_rerank(query: str, candidates: list[dict], criteria: str,
                    threshold: float = 0.5) -> list[dict]:
    """Dùng Jev làm reranker: chấm từng ứng viên bằng câu hỏi noul, sắp xếp theo xác suất.

    Mỗi candidate là dict có ít nhất {"id": ..., "text": ...}.
    Trả về danh sách đã sắp theo p giảm dần, chỉ giữ những ứng viên có p >= threshold.
    Mỗi phần tử được thêm trường "jev_p".
    """
    if not candidates:
        return []

    # Gom candidates thành từng batch (tối đa 10 ứng viên/request) để gọi Jev song song, tiết kiệm thời gian
    batch_size = 10
    results = []
    for i in range(0, len(candidates), batch_size):
        batch = candidates[i:i + batch_size]
        state_parts = [f"Truy vấn: {query}\n\nDanh sách các đoạn ứng viên:"]
        questions = {}
        for idx, cand in enumerate(batch):
            qid = f"c_{idx}"
            state_parts.append(f"--- Đoạn [{cand['id']}] ---\n{cand['text']}\n")
            questions[qid] = {
                "type": "noul",
                "instructions": f"Đoạn [{cand['id']}] có liên quan đến truy vấn theo tiêu chí: {criteria}",
            }
        state = "\n".join(state_parts)
        try:
            resp = call_jev(state, questions)
            answers = resp.get("answers", resp)
            for idx, cand in enumerate(batch):
                qid = f"c_{idx}"
                q = answers.get(qid, {})
                p = q.get("noul", q.get("probability", 0.0))
                results.append({**cand, "jev_p": p})
        except LLMError:
            for cand in batch:
                results.append({**cand, "jev_p": 0.0})

    # Sắp xếp giảm dần theo p, lọc theo threshold
    results.sort(key=lambda x: -x["jev_p"])
    return [r for r in results if r["jev_p"] >= threshold]


# Giữ call_jev_text wrapper cho backward compatibility nếu cần gọi Jev như text backend
def call_jev_text(system: str, user: str, temperature: float = 0.0) -> str:
    """Fallback: dùng Jev cho câu hỏi noul đơn giản, trả 'true'/'false' như text.
    Chỉ dùng cho generate_json khi backend='jev' (không khuyến khích, nên dùng call_jev trực tiếp)."""
    state = f"{system}\n\n{user}"
    questions = {"answer": {"type": "noul", "instructions": "Based on the context, answer the question."}}
    resp = call_jev(state, questions)
    answers = resp.get("answers", resp)
    q = answers.get("answer", {})
    p = q.get("noul", q.get("probability", 0.5))
    return json.dumps({"answer": p >= 0.5, "p": p})


_BACKENDS = {"gemini": call_gemini_text, "jev": call_jev_text}


def generate_json(backend: str, system: str, user: str, model_cls: Type[T], repairs: int = 2, use_cache: bool = True) -> T:
    if backend not in _BACKENDS:
        raise LLMError(f"Backend không hỗ trợ: {backend}")
    model_id = os.environ.get("GEMINI_MODEL" if backend == "gemini" else "JEV_MODEL", "")
    key = hashlib.sha256(json.dumps([backend, model_id, system, user], ensure_ascii=False).encode()).hexdigest()[:24]
    cache_file = CACHE_DIR / f"{backend}_{key}.json"
    if use_cache and cache_file.exists():
        raw_data = json.loads(cache_file.read_text(encoding="utf-8"))
        return raw_data if model_cls is dict else model_cls.model_validate(raw_data)

    prompt, last_err = user, None
    for _ in range(repairs + 1):
        text = _BACKENDS[backend](system, prompt)
        try:
            obj = _extract_json(text)
            parsed = obj if model_cls is dict else model_cls.model_validate(obj)
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
            return parsed
        except (json.JSONDecodeError, ValidationError, AttributeError) as e:
            last_err = e
            prompt = user + f"\n\n[LẦN TRƯỚC TRẢ VỀ JSON KHÔNG HỢP LỆ: {str(e)[:300]}. Hãy trả lại JSON đúng schema, không thêm chữ nào khác.]"
    raise LLMError(f"Không có JSON hợp lệ sau {repairs + 1} lần: {last_err}")
