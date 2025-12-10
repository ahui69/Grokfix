#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM core module – DeepInfra chat completions + cache + fallback.

Ten moduł jest JEDYNYM miejscem, które gada z LLM.
Wszystkie inne warstwy (advanced_cognitive_engine, autonauka, psyche, research)
mają z niego korzystać.

Kluczowe założenie:
- KOMPATYBILNOŚĆ WSTECZ:
    call_llm("prompt")
    call_llm(prompt="prompt")
    call_llm(messages=[{"role": "...", "content": "..."}])

Wszystkie te formy działają.
"""

from __future__ import annotations

import time
import json
import hashlib
from typing import Any, Dict, List, Optional, Generator, Union

import httpx

from .config import (
    LLM_BASE_URL,
    LLM_API_KEY,
    LLM_MODEL,
    LLM_FALLBACK_MODEL,
    LLM_TIMEOUT,
    LLM_RETRIES,
    LLM_BACKOFF_S,
)
from .helpers import log_error, log_warning, log_info

# Redis cache (jeśli jest)
try:
    from .redis_middleware import get_redis
    REDIS_AVAILABLE = True
    log_info("[LLM] Redis cache available", "LLM")
except Exception as e:
    REDIS_AVAILABLE = False
    log_warning(f"[LLM] Redis cache not available: {e}", "LLM")


# ══════════════════════════════════════════════════════════════
#  UTILS
# ══════════════════════════════════════════════════════════════

def _normalize_messages(
    messages: Optional[Any],
    prompt: Optional[str],
    system_prompt: Optional[str] = None,
) -> List[Dict[str, str]]:
    """
    Normalizacja wejścia do standardu OpenAI:
    [{"role": "...", "content": "..."}]
    """
    # Jeśli ktoś wywołał: call_llm("cośtam")
    if isinstance(messages, str) and prompt is None:
        prompt = messages
        messages = None

    if messages is not None:
        # zakładamy, że to już jest lista dictów
        return list(messages)

    if prompt is None:
        raise ValueError("call_llm: musisz podać messages LUB prompt")

    msg_list: List[Dict[str, str]] = []
    if system_prompt:
        msg_list.append({"role": "system", "content": system_prompt})
    msg_list.append({"role": "user", "content": prompt})
    return msg_list


def _generate_cache_key(
    messages: List[Dict[str, str]],
    model: str,
    **opts: Any,
) -> str:
    """Deterministyczny klucz cache na podstawie wejścia."""
    cache_data = {
        "model": model,
        "messages": messages,
        "temperature": opts.get("temperature"),
        "max_tokens": opts.get("max_tokens"),
    }
    cache_string = json.dumps(cache_data, sort_keys=True, ensure_ascii=False)
    return "llm:" + hashlib.sha256(cache_string.encode("utf-8")).hexdigest()


def _http_call(
    *,
    model: str,
    messages: List[Dict[str, str]],
    timeout_s: float,
    stream: bool = False,
    extra_payload: Optional[Dict[str, Any]] = None,
) -> httpx.Response:
    """Surowe wywołanie HTTP do DeepInfra."""
    if not LLM_API_KEY:
        raise RuntimeError("LLM_API_KEY is not set in environment")

    url = f"{LLM_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
    }
    if extra_payload:
        payload.update(extra_payload)

    with httpx.Client(timeout=timeout_s) as client:
        return client.post(url, headers=headers, json=payload)


# ══════════════════════════════════════════════════════════════
#  GŁÓWNY CALL + RAW + STREAM
# ══════════════════════════════════════════════════════════════

def _llm_request(
    messages: List[Dict[str, str]],
    model: str,
    *,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    timeout_s: Optional[float] = None,
    retries: Optional[int] = None,
    backoff_s: Optional[float] = None,
    stream: bool = False,
    extra_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Niskopoziomowe wywołanie LLM (z retry).
    Zwraca pełny JSON z DeepInfra.
    """
    if temperature is not None:
        if extra_payload is None:
            extra_payload = {}
        extra_payload["temperature"] = float(temperature)

    if max_tokens is not None:
        if extra_payload is None:
            extra_payload = {}
        try:
            extra_payload["max_tokens"] = int(max_tokens)
        except Exception:
            pass

    if retries is None:
        retries = LLM_RETRIES
    if backoff_s is None:
        backoff_s = LLM_BACKOFF_S
    if timeout_s is None:
        timeout_s = LLM_TIMEOUT

    last_exc: Optional[Exception] = None

    for attempt in range(1, retries + 1):
        try:
            r = _http_call(
                model=model,
                messages=messages,
                timeout_s=float(timeout_s),
                stream=stream,
                extra_payload=extra_payload,
            )
            r.raise_for_status()
            data = r.json()
            if attempt > 1:
                log_info(f"[LLM] Request succeeded on attempt {attempt}", "LLM")
            return data
        except Exception as e:
            last_exc = e
            if attempt < retries:
                sleep_time = backoff_s * attempt
                log_warning(
                    f"[LLM] Request failed (attempt {attempt}/{retries}), retry in {sleep_time}s: {e}",
                    "LLM",
                )
                time.sleep(sleep_time)
            else:
                log_error(e, "LLM_REQUEST")
                break

    if last_exc:
        raise last_exc
    raise RuntimeError("Unknown LLM error")


def call_llm(
    messages: Optional[Any] = None,
    *,
    prompt: Optional[str] = None,
    system_prompt: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    timeout_s: Optional[float] = None,
    skip_cache: bool = False,
    cache_ttl: int = 3600,
    model: Optional[str] = None,
    use_fallback: bool = True,
    **extra_opts: Any,
) -> str:
    """
    Wysokopoziomowe wywołanie LLM z cache + fallback.

    OBSŁUGUJE:
        call_llm("tekst")
        call_llm(prompt="tekst")
        call_llm(messages=[...])

    Zwraca: sam tekst odpowiedzi.
    """
    model_name = model or LLM_MODEL
    msgs = _normalize_messages(messages, prompt, system_prompt)

    # Cache
    cache_key = None
    if REDIS_AVAILABLE and not skip_cache:
        try:
            redis = get_redis()
            cache_key = _generate_cache_key(msgs, model_name,
                                            temperature=temperature,
                                            max_tokens=max_tokens)
            cached = redis.get(cache_key)
            if cached:
                log_info("[LLM] Cache HIT", "LLM")
                return cached.decode("utf-8")
            log_info("[LLM] Cache MISS", "LLM")
        except Exception as e:
            log_warning(f"[LLM] Redis error (ignored): {e}", "LLM")

    # Główne żądanie
    try:
        data = _llm_request(
            msgs,
            model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_s=timeout_s,
        )
    except Exception as e:
        log_error(e, "LLM_MAIN_MODEL_FAILED")
        if not use_fallback or not LLM_FALLBACK_MODEL:
            raise

        # Fallback model
        try:
            log_warning(
                f"[LLM] Main model failed, trying fallback: {LLM_FALLBACK_MODEL}",
                "LLM",
            )
            data = _llm_request(
                msgs,
                LLM_FALLBACK_MODEL,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout_s=timeout_s,
            )
        except Exception as e2:
            log_error(e2, "LLM_FALLBACK_FAILED")
            raise

    content = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )

    # Zapis do cache
    if REDIS_AVAILABLE and not skip_cache and cache_key is not None:
        try:
            redis = get_redis()
            redis.setex(cache_key, cache_ttl, content)
            log_info("[LLM] Cache STORE", "LLM")
        except Exception as e:
            log_warning(f"[LLM] Redis setex error (ignored): {e}", "LLM")

    return content


def call_llm_raw(
    messages: Optional[Any] = None,
    *,
    prompt: Optional[str] = None,
    system_prompt: Optional[str] = None,
    **opts: Any,
) -> Dict[str, Any]:
    """
    To samo co call_llm, ale zwraca pełny JSON z DeepInfra.
    """
    msgs = _normalize_messages(messages, prompt, system_prompt)
    model_name = opts.pop("model", LLM_MODEL)
    data = _llm_request(msgs, model_name, **opts)
    return data


def call_llm_stream(
    messages: Optional[Any] = None,
    *,
    prompt: Optional[str] = None,
    system_prompt: Optional[str] = None,
    **opts: Any,
) -> Generator[str, None, None]:
    """
    Pseudo-streaming:
    - na razie robimy zwykłe wywołanie i yieldujemy całość jako jeden chunk,
      żeby nie wysypywać starego kodu, który oczekuje generatora.
    """
    text = call_llm(messages, prompt=prompt, system_prompt=system_prompt, **opts)
    yield text


def stream_llm(
    messages: Optional[Any] = None,
    *,
    prompt: Optional[str] = None,
    system_prompt: Optional[str] = None,
    **opts: Any,
) -> Generator[str, None, None]:
    """
    Alias na call_llm_stream – trzymamy dla zgodności.
    """
    yield from call_llm_stream(messages, prompt=prompt, system_prompt=system_prompt, **opts)


# ══════════════════════════════════════════════════════════════
#  WYŻSZE POZIOMY: CHAT + HEALTH
# ══════════════════════════════════════════════════════════════

def chat_with_context(
    *,
    user_content: str,
    system_prompt: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
    **opts: Any,
) -> str:
    """
    Prosty helper: history + system + user_content => call_llm(messages=...)
    """
    msgs: List[Dict[str, str]] = []
    if system_prompt:
        msgs.append({"role": "system", "content": system_prompt})
    if history:
        msgs.extend(history)
    msgs.append({"role": "user", "content": user_content})
    return call_llm(messages=msgs, **opts)


def llm_health() -> Dict[str, Any]:
    """
    Lekkie sprawdzenie, czy LLM odpowiada.
    Nie strzelamy nic ciężkiego – prosty echo-test.
    """
    try:
        reply = call_llm(prompt="ping", max_tokens=4, skip_cache=True, use_fallback=True)
        ok = bool(reply)
        return {
            "ok": ok,
            "reply": reply,
            "base_url": LLM_BASE_URL,
            "model": LLM_MODEL,
            "fallback_model": LLM_FALLBACK_MODEL,
        }
    except Exception as e:
        log_error(e, "LLM_HEALTH")
        return {
            "ok": False,
            "error": str(e),
            "base_url": LLM_BASE_URL,
            "model": LLM_MODEL,
            "fallback_model": LLM_FALLBACK_MODEL,
        }


def get_llm_client() -> Dict[str, Any]:
    """
    Zostawiamy jako prosty deskryptor – nie robimy tu żadnych magii.
    Stare moduły oczekują, że coś takiego istnieje.
    """
    return {
        "base_url": LLM_BASE_URL,
        "api_key_set": bool(LLM_API_KEY),
        "default_model": LLM_MODEL,
        "fallback_model": LLM_FALLBACK_MODEL,
        "timeout": LLM_TIMEOUT,
    }


__all__ = [
    "call_llm",
    "call_llm_raw",
    "call_llm_stream",
    "stream_llm",
    "chat_with_context",
    "llm_health",
    "get_llm_client",
]
