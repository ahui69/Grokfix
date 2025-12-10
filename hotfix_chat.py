#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/hotfix_chat.py

Tryb awaryjny czatu:
- JEŚLI cokolwiek w kodzie zawoła hotfix_fallback, to i tak lecimy do LLM
- Zero tekstu "Nie mam wystarczającej informacji w lokalnej pamięci."
- Bez kombinowania z pamięcią: proste, szybkie, pewne
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException

logger = logging.getLogger("mordzix.hotfix_chat")

router = APIRouter(prefix="/api/hotfix", tags=["Hotfix Chat"])


# ===================== LOW LEVEL LLM CALL =====================

def _get_llm_config() -> Dict[str, str]:
    base_url = os.getenv("LLM_BASE_URL", "").strip()
    api_key = os.getenv("LLM_API_KEY", "").strip()
    model = os.getenv("LLM_MODEL", "").strip()

    if not base_url:
        raise RuntimeError("LLM_BASE_URL nie ustawione")
    if not api_key:
        raise RuntimeError("LLM_API_KEY nie ustawione")
    if not model:
        raise RuntimeError("LLM_MODEL nie ustawione")

    return {
        "base_url": base_url,
        "api_key": api_key,
        "model": model,
    }


def _call_llm_sync(prompt: str) -> str:
    """
    Sync call do endpointu OpenAI-kompatybilnego (DeepInfra / OpenAI / cokolwiek).
    Zrobione na urllib, bez dodatkowych bibliotek.
    """
    import urllib.request

    cfg = _get_llm_config()

    url = cfg["base_url"].rstrip("/")
    # jeśli ktoś podał /chat/completions w env, to zostawiamy jak jest
    if not url.endswith("/chat/completions"):
        url = url + "/chat/completions"

    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": "Jesteś asystentem Mordzix AI. Odpowiadasz zwięźle po polsku."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 512,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    with urllib.request.urlopen(req, timeout=90) as resp:
        body = resp.read()
        try:
            j = json.loads(body.decode("utf-8"))
        except Exception:
            logger.error("Nie udało się zdekodować odpowiedzi LLM: %r", body[:200])
            raise

    try:
        return j["choices"][0]["message"]["content"]
    except Exception:
        logger.error("Niepoprawna struktura odpowiedzi LLM: %r", j)
        raise RuntimeError("LLM zwrócił nieoczekiwaną strukturę")


async def _call_llm(prompt: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _call_llm_sync, prompt)


def _extract_user_text(payload: Dict[str, Any]) -> str:
    """
    Bierzemy ostatnią wiadomość usera z payloadu takiego jak /api/chat/assistant.
    """
    msgs: List[Dict[str, Any]] = payload.get("messages") or []
    for msg in reversed(msgs):
        if isinstance(msg, dict) and msg.get("role") == "user":
            content = msg.get("content")
            if isinstance(content, str):
                return content

    # fallback: nie ma messages, może jest "prompt"
    prompt = payload.get("prompt")
    if isinstance(prompt, str) and prompt.strip():
        return prompt.strip()

    raise ValueError("Brak tekstu użytkownika w payloadzie")


# ===================== GŁÓWNY FALLBACK =====================

async def hotfix_fallback(
    payload: Dict[str, Any],
    reason: Optional[str] = None,
    error: Optional[BaseException] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    To wywołują inne moduły, kiedy coś im nie pasuje.
    Teraz:
        -> wyciągamy tekst usera
        -> wołamy normalnie LLM
        -> zwracamy pełną odpowiedź

    ZERO "Nie mam wystarczającej informacji w lokalnej pamięci."
    """

    t0 = time.time()
    try:
        user_text = _extract_user_text(payload)
    except Exception as e:
        logger.error("hotfix_fallback: nie mogę wyciągnąć tekstu usera: %r", e)
        return {
            "ok": True,
            "answer": "Coś poszło nie tak w trybie awaryjnym – brak tekstu użytkownika.",
            "sources": [],
            "metadata": {
                "source": "hotfix_llm_error",
                "raw_finish_reason": "error",
                "processing_time": round(time.time() - t0, 4),
                "error": str(e),
            },
        }

    try:
        answer = await _call_llm(user_text)
        dt = round(time.time() - t0, 4)

        return {
            "ok": True,
            "answer": answer,
            "sources": [],
            "metadata": {
                "source": "hotfix_llm",   # już NIE "hotfix_fallback" z tym gównem
                "raw_finish_reason": "stop",
                "processing_time": dt,
                "fallback_reason": reason or "used_by_assistant",
            },
        }
    except Exception as e:
        logger.exception("hotfix_fallback: LLM też się wyjebał: %r", e)
        dt = round(time.time() - t0, 4)
        return {
            "ok": True,
            "answer": "Nawet tryb awaryjny się wysypał. Spróbuj za chwilę.",
            "sources": [],
            "metadata": {
                "source": "hotfix_llm_error",
                "raw_finish_reason": "error",
                "processing_time": dt,
                "error": str(e),
            },
        }


# ===================== PROSTY ENDPOINT (opcjonalny) =====================

@router.post("/chat")
async def hotfix_chat_endpoint(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Opcjonalny endpoint /api/hotfix/chat – jak coś innego go użyje, też działa.
    """
    try:
        return await hotfix_fallback(payload, reason="direct_hotfix_endpoint")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Błąd w /api/hotfix/chat: %r", e)
        raise HTTPException(status_code=500, detail="Błąd trybu awaryjnego")
