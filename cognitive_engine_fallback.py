# -*- coding: utf-8 -*-
"""
Prosty fallback cognitive_engine – uderza w DeepInfra (OpenAI-compatible).
Używa ENV:
  LLM_BASE_URL (np. https://api.deepinfra.com/v1/openai)
  LLM_API_KEY
  LLM_MODEL
  LLM_TIMEOUT / LLM_HTTP_TIMEOUT_S (opcjonalnie)
  MORDZIX_SYSTEM_PROMPT (opcjonalnie)
Zwraca ten sam kształt co oryginalny engine.process_message(...).
"""
import os, httpx, asyncio, time
from typing import List, Dict, Any

def _env_f(name: str, default: float) -> float:
    try: return float(str(os.getenv(name, default)).strip())
    except: return float(default)

def _env_i(name: str, default: int) -> int:
    try: return int(str(os.getenv(name, default)).strip())
    except: return int(default)

class _FallbackEngine:
    async def process_message(self, user_id: str, messages: List[Dict[str, Any]], req) -> Dict[str, Any]:
        base = (os.getenv("LLM_BASE_URL", "https://api.deepinfra.com/v1/openai") or "").rstrip("/")
        api_key = os.getenv("LLM_API_KEY", "")
        model = os.getenv("LLM_MODEL", "meta-llama/Llama-3.3-70B-Instruct")
        timeout_s = _env_i("LLM_HTTP_TIMEOUT_S", _env_i("LLM_TIMEOUT", 120))
        temperature = _env_f("LLM_TEMPERATURE", 0.3)
        max_tokens = _env_i("LLM_MAX_TOKENS", 800)

        # system prompt (jeśli jest)
        system_prompt = ""
        try:
            from .config import MORDZIX_SYSTEM_PROMPT
            system_prompt = MORDZIX_SYSTEM_PROMPT or ""
        except Exception:
            pass

        # sprowadź listę wiadomości do OpenAI format
        chat_msgs = []
        if system_prompt.strip():
            chat_msgs.append({"role": "system", "content": system_prompt})
        for m in messages:
            role = (m.get("role") or "").lower() or "user"
            content = m.get("content") or ""
            chat_msgs.append({"role": role, "content": content})

        url = f"{base}/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": chat_msgs,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }

        t0 = time.time()
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()

        try:
            answer = (data["choices"][0]["message"]["content"] or "").strip()
        except Exception:
            answer = (data.get("choices") or [{}])[0].get("text","").strip()

        meta = {
            "source": "cognitive_engine_fallback",
            "model": model,
            "temperature": temperature,
            "total_processing_time": time.time() - t0
        }
        return {"answer": answer, "sources": [], "metadata": meta}

cognitive_engine = _FallbackEngine()
