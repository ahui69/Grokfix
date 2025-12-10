#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
core.llm — stabilny klient LLM dla DeepInfra (OpenAI-compatible)
Rozszerzenia (APPEND-ONLY wobec poprzedniej wersji):
- Chat Completions (non-stream + stream)
- Streaming: delta.content + obsługa function_call / tool_calls (opcjonalne markery)
- Retry + exponential backoff + fallback model/provider
- Limit równoległości (semafor)
- Redis cache (opcjonalnie) dla non-stream
- Auto-retune (ranking per user) + score_weighting (aktywniejsi użytkownicy mają większą wagę)
- Async eksport feedback do S3 i/lub Elasticsearch (batch + flush)
- Personality injection: persona per request lub per-user

Interfejsy publiczne jak wcześniej:
  call_llm, call_llm_stream_with_fallback, stream_first_or_fallback, chat_completion,
  record_feedback, suggest_params_for_user, set_user_persona, get_user_persona, PERSONAS
"""

from __future__ import annotations
import os
import json
import time
import math
import asyncio
import logging
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

import httpx

# ────────────────────────────────────────────────────────────────────────────────
# LOGGING

_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=_LOG_LEVEL, format="[LLM] %(levelname)s: %(message)s")
log = logging.getLogger("llm")

# ────────────────────────────────────────────────────────────────────────────────
# ENV

def _env_bool(k: str, default: bool) -> bool:
    v = str(os.getenv(k, "1" if default else "0")).strip().lower()
    return v in ("1","true","yes","y","on")

def _env_int(k: str, default: int) -> int:
    try:
        return int(str(os.getenv(k, default)).strip())
    except Exception:
        return default

BASE_URL            = os.getenv("LLM_BASE_URL", "https://api.deepinfra.com/v1/openai").rstrip("/")
API_KEY             = os.getenv("LLM_API_KEY", "").strip()
MODEL_PRIMARY       = os.getenv("LLM_MODEL", "meta-llama/Llama-3.3-70B-Instruct").strip()
MODEL_FALLBACK      = os.getenv("LLM_FALLBACK_MODEL", "").strip()
TIMEOUT_S           = int(os.getenv("LLM_HTTP_TIMEOUT_S", os.getenv("LLM_TIMEOUT", "120")))
RETRIES             = int(os.getenv("LLM_RETRIES", "3"))
BACKOFF_S           = float(os.getenv("LLM_BACKOFF_S", "2"))
MAX_CONC            = int(os.getenv("LLM_MAX_CONC", "4"))
CACHE_TTL_S         = int(os.getenv("LLM_CACHE_TTL_S", "300"))

ALT_BASE_URL        = os.getenv("OPENAI_BASE_URL", "").strip()
ALT_API_KEY         = os.getenv("OPENAI_API_KEY", "").strip()

# Redis (opcjonalnie)
REDIS_ENABLED       = _env_bool("REDIS_ENABLED", False)
REDIS_URL           = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Auto-retune / feedback (lokalny plik + preferencje per user)
LLM_AUTOTUNE        = _env_bool("LLM_AUTOTUNE", True)
FEEDBACK_LOG        = os.getenv("FEEDBACK_LOG", "/root/mordzix-ai/out/llm_feedback.jsonl")
LLM_PREFS_PATH      = os.getenv("LLM_PREFS_PATH", "/root/mordzix-ai/out/llm_prefs.json")

# Wagi dla aktywniejszych użytkowników
FEEDBACK_WEIGHT_CAP     = float(os.getenv("FEEDBACK_WEIGHT_CAP", "3.0"))   # maksymalna waga
FEEDBACK_WEIGHT_K       = float(os.getenv("FEEDBACK_WEIGHT_K", "2.0"))    # mnożnik przy log10
FEEDBACK_WEIGHT_BASE    = float(os.getenv("FEEDBACK_WEIGHT_BASE", "1.0")) # baza

# Async eksport feedback (w pełni opcjonalny)
FEEDBACK_EXPORT_ENABLE  = _env_bool("FEEDBACK_EXPORT_ENABLE", True)
FEEDBACK_EXPORT_BATCH   = _env_int("FEEDBACK_EXPORT_BATCH", 200)
FEEDBACK_EXPORT_FLUSH_S = _env_int("FEEDBACK_EXPORT_FLUSH_S", 5)
FEEDBACK_EXPORT_QUEUE_MAX = _env_int("FEEDBACK_EXPORT_QUEUE_MAX", 10000)

# S3
FEEDBACK_EXPORT_S3_ENABLE = _env_bool("FEEDBACK_EXPORT_S3_ENABLE", False)
S3_BUCKET       = os.getenv("S3_BUCKET", "").strip()
S3_PREFIX       = os.getenv("S3_PREFIX", "llm-feedback").strip()
S3_REGION       = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1")).strip()
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "").strip()  # opcjonalny niestandardowy endpoint (minio/opensearch s3)

# Elasticsearch / OpenSearch (HTTP _bulk)
FEEDBACK_EXPORT_ES_ENABLE = _env_bool("FEEDBACK_EXPORT_ES_ENABLE", False)
ES_BASE_URL     = os.getenv("ES_BASE_URL", "").rstrip("/")
ES_INDEX        = os.getenv("ES_INDEX", "llm-feedback")
ES_API_KEY      = os.getenv("ES_API_KEY", "").strip()         # preferowane
ES_USERNAME     = os.getenv("ES_USERNAME", "").strip()        # alternatywnie basic
ES_PASSWORD     = os.getenv("ES_PASSWORD", "").strip()

# ────────────────────────────────────────────────────────────────────────────────
# PERSONAS

PERSONAS: Dict[str, str] = {
    "mentor": (
        "Jesteś rzeczowym, spokojnym mentorem. Odpowiadasz konkretnie, technicznie, "
        "krótko i z przykładami. Gdy nie masz pewności – mówisz to wprost."
    ),
    "kurwabot": (
        "Masz ostry, bezpośredni styl i nie owijasz w bawełnę. Jesteś dosadny, "
        "ale nie szerzysz nienawiści. Priorytet: skuteczność i tempo."
    ),
    "flirt": (
        "Jesteś luźny i żartobliwy, lekko kokieteryjny, ale zawsze z wyczuciem i szacunkiem. "
        "Podajesz rozwiązania i wplatasz lekkie, pozytywne uwagi."
    ),
}

# ────────────────────────────────────────────────────────────────────────────────
# REDIS (opcjonalnie)

class _NoCache:
    async def get(self, *a, **k) -> Optional[str]:
        return None
    async def set(self, *a, **k) -> None:
        return None

_cache = _NoCache()

if REDIS_ENABLED:
    try:
        import redis.asyncio as redis
        _cache = redis.from_url(REDIS_URL, decode_responses=True)
        log.info(f"Redis cache enabled: {REDIS_URL}")
    except Exception as e:
        log.warning(f"Redis not available ({e}) — continue without cache")
        _cache = _NoCache()

# ────────────────────────────────────────────────────────────────────────────────
# HTTPX KLIENCI

def _headers(key: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

_client: Optional[httpx.AsyncClient] = None
_alt_client: Optional[httpx.AsyncClient] = None

def _get_client(base_url: str, key: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=base_url,
        timeout=httpx.Timeout(TIMEOUT_S),
        headers=_headers(key),
        http2=False,
    )

async def _ensure_clients():
    global _client, _alt_client
    if _client is None:
        _client = _get_client(BASE_URL, API_KEY)
    if ALT_BASE_URL and ALT_API_KEY and _alt_client is None:
        _alt_client = _get_client(ALT_BASE_URL, ALT_API_KEY)

# ────────────────────────────────────────────────────────────────────────────────
# UTILS

def _norm_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for m in messages:
        role = str(m.get("role", "user"))
        content = m.get("content")
        if isinstance(content, list):
            content = " ".join(str(x.get("text","")) for x in content if isinstance(x, dict))
        out.append({"role": role, "content": "" if content is None else str(content)})
    return out

def _cache_key(model: str, messages: List[Dict[str,str]], temperature: float, extra: Dict[str, Any]) -> str:
    payload = {"model": model, "messages": messages, "temperature": round(float(temperature), 3), "extra": extra or {}}
    return "llm:" + json.dumps(payload, sort_keys=True, ensure_ascii=False)

def _select_provider(attempt: int) -> Tuple[str, str, httpx.AsyncClient]:
    """
    attempt 0 → primary @ BASE_URL
    attempt 1 → fallback model @ BASE_URL
    attempt 2 → primary @ ALT_BASE_URL
    attempt 3 → fallback @ ALT_BASE_URL
    """
    if attempt == 0:
        return (MODEL_PRIMARY, BASE_URL, _client)  # type: ignore
    if attempt == 1 and MODEL_FALLBACK:
        return (MODEL_FALLBACK, BASE_URL, _client)  # type: ignore
    if attempt == 2 and ALT_BASE_URL and ALT_API_KEY:
        return (MODEL_PRIMARY, ALT_BASE_URL, _alt_client)  # type: ignore
    if attempt == 3 and MODEL_FALLBACK and ALT_BASE_URL and ALT_API_KEY:
        return (MODEL_FALLBACK, ALT_BASE_URL, _alt_client)  # type: ignore
    return (MODEL_PRIMARY, BASE_URL, _client)  # type: ignore

def _extract_text_from_response(data: Dict[str, Any]) -> str:
    try:
        ch = data["choices"][0]
        msg = ch.get("message", {})
        return str(msg.get("content", "")) if isinstance(msg, dict) else str(msg or "")
    except Exception:
        return ""

# ────────────────────────────────────────────────────────────────────────────────
# AUTO-RETUNE (feedback + per-user suggestions) + WAGI

_USER_PREFS: Dict[str, Dict[str, Any]] = {}
_prefs_loaded = False

def _prefs_load() -> None:
    try:
        if os.path.exists(LLM_PREFS_PATH):
            with open(LLM_PREFS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    _USER_PREFS.update(data)
    except Exception as e:
        log.warning(f"Prefs load failed: {e}")

def _prefs_save() -> None:
    try:
        os.makedirs(os.path.dirname(LLM_PREFS_PATH), exist_ok=True)
        with open(LLM_PREFS_PATH, "w", encoding="utf-8") as f:
            json.dump(_USER_PREFS, f, ensure_ascii=False)
    except Exception as e:
        log.warning(f"Prefs save failed: {e}")

def _ensure_prefs_loaded():
    global _prefs_loaded
    if not _prefs_loaded:
        _prefs_loaded = True
        _prefs_load()

def _update_score_bucket(bucket: Dict[str, Dict[str, float]], key: str, weighted_score: float) -> None:
    row = bucket.setdefault(key, {"sum": 0.0, "cnt": 0.0})
    row["sum"] += float(weighted_score)
    row["cnt"] += 1.0

def _weight_from_feedback_count(cnt: int) -> float:
    """
    Waga rośnie z liczbą feedbacków danego usera:
      weight = BASE + min(CAP, K * log10(cnt+1))
    Przykład przy bazie=1, K=2, cap=3:
      cnt=0 → 1.0
      cnt=5 → 1 + 2*log10(6) ≈ 2.55
      cnt=10→ ~3.0 (sufit)
    """
    try:
        w = FEEDBACK_WEIGHT_BASE + min(FEEDBACK_WEIGHT_CAP, FEEDBACK_WEIGHT_K * math.log10(max(1, cnt+1)))
        return float(max(0.1, w))
    except Exception:
        return FEEDBACK_WEIGHT_BASE

def record_feedback(
    *,
    user_id: str,
    model: str,
    temperature: float,
    tools_used: Optional[List[str]] = None,
    response_text: str = "",
    upvote: Optional[bool] = None,
    numeric_score: Optional[float] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Zapisuje feedback do JSONL, aktualizuje ranking per user (Z WAGĄ)
    i wrzuca rekord do kolejki eksportu async (S3/ES).
    """
    try:
        _ensure_prefs_loaded()
        score = float(numeric_score if numeric_score is not None else (1.0 if upvote else -1.0))

        # in-memory prefs (zliczanie feedbacków)
        row = _USER_PREFS.setdefault(user_id, {"models": {}, "temps": {}, "persona": None, "fb_cnt": 0})
        fb_cnt = int(row.get("fb_cnt", 0))
        weight = _weight_from_feedback_count(fb_cnt)
        weighted_score = score * weight
        row["fb_cnt"] = fb_cnt + 1

        # update ranking
        _update_score_bucket(row["models"], model, weighted_score)
        tkey = f"{round(float(temperature), 2):.2f}"
        _update_score_bucket(row["temps"], tkey, weighted_score)
        _prefs_save()

        # JSONL log (lokalny)
        os.makedirs(os.path.dirname(FEEDBACK_LOG), exist_ok=True)
        rec = {
            "ts": int(time.time()),
            "user_id": user_id,
            "model": model,
            "temperature": float(temperature),
            "tools": tools_used or [],
            "score": score,
            "weight": weight,
            "weighted_score": weighted_score,
            "len": len(response_text or ""),
            "meta": meta or {},
        }
        with open(FEEDBACK_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        # async eksport (opcjonalnie)
        _queue_feedback_export(rec)

    except Exception as e:
        log.warning(f"record_feedback failed: {e}")

def suggest_params_for_user(user_id: Optional[str]) -> Tuple[Optional[str], Optional[float]]:
    """
    Zwraca (model, temperature) wg lokalnego rankingu; None jeśli brak danych.
    Uwzględnia WAGI (bo sumy i cnt są już liczone na weighted_score).
    """
    if not user_id or not LLM_AUTOTUNE:
        return (None, None)
    try:
        _ensure_prefs_loaded()
        row = _USER_PREFS.get(user_id)
        if not row:
            return (None, None)

        # model: najwyższa średnia ważona
        best_model = None
        best_avg = -math.inf
        for m, v in row.get("models", {}).items():
            if v["cnt"] > 0:
                avg = v["sum"] / max(v["cnt"], 1.0)
                if avg > best_avg:
                    best_avg = avg
                    best_model = m

        # temp: średnia ważona (cnt to już „ważone” zliczenia, ale przyjmujemy je jako wagi)
        best_temp = None
        temps = row.get("temps", {})
        if temps:
            num = 0.0
            den = 0.0
            for tkey, v in temps.items():
                try:
                    tval = float(tkey)
                except Exception:
                    continue
                num += tval * v["cnt"]
                den += v["cnt"]
            if den > 0:
                best_temp = max(0.1, min(0.9, round(num / den, 2)))

        return (best_model, best_temp)
    except Exception as e:
        log.warning(f"suggest_params_for_user failed: {e}")
        return (None, None)

# persona per-user
def set_user_persona(user_id: str, persona: Optional[str]) -> None:
    try:
        _ensure_prefs_loaded()
        row = _USER_PREFS.setdefault(user_id, {"models": {}, "temps": {}, "persona": None, "fb_cnt": 0})
        row["persona"] = persona if persona in PERSONAS else None
        _prefs_save()
    except Exception as e:
        log.warning(f"set_user_persona failed: {e}")

def get_user_persona(user_id: Optional[str]) -> Optional[str]:
    try:
        if not user_id:
            return None
        _ensure_prefs_loaded()
        row = _USER_PREFS.get(user_id) or {}
        p = row.get("persona")
        return p if p in PERSONAS else None
    except Exception:
        return None

# ────────────────────────────────────────────────────────────────────────────────
# PERSONA INJECTION

def _inject_persona(messages: List[Dict[str, Any]], persona: Optional[str]) -> List[Dict[str, Any]]:
    if not persona or persona not in PERSONAS:
        return messages
    sys_msg = {"role": "system", "content": PERSONAS[persona]}
    return [sys_msg] + messages

# ────────────────────────────────────────────────────────────────────────────────
# API: NON-STREAM

async def call_llm(
    messages: List[Dict[str, Any]],
    *,
    user_id: Optional[str] = None,
    persona: Optional[str] = None,
    model_override: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_choice: Optional[Any] = None,
    extra_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    await _ensure_clients()
    if user_id and LLM_AUTOTUNE:
        sug_model, sug_temp = suggest_params_for_user(user_id)
        model_use = model_override or sug_model or MODEL_PRIMARY
        temp_use = float(temperature) if temperature is not None else (sug_temp if sug_temp is not None else 0.7)
    else:
        model_use = model_override or MODEL_PRIMARY
        temp_use = float(temperature) if temperature is not None else 0.7

    persona_use = persona or get_user_persona(user_id)

    msgs = _norm_messages(_inject_persona(messages, persona_use))
    extra = dict(extra_params or {})
    body_base = {"model": model_use, "messages": msgs, "temperature": float(temp_use)}
    if max_tokens:
        body_base["max_tokens"] = int(max_tokens)
    if tools:
        body_base["tools"] = tools
    if tool_choice:
        body_base["tool_choice"] = tool_choice
    body_base.update(extra)

    ck = _cache_key(body_base["model"], msgs, float(temp_use), extra)
    try:
        raw = await _cache.get(ck)  # type: ignore
        if raw:
            return json.loads(raw)
    except Exception:
        pass

    err_last: Optional[str] = None
    for attempt in range(0, 4):
        _, base, client = _select_provider(attempt)
        body = dict(body_base)
        try:
            async with asyncio.Semaphore(MAX_CONC if MAX_CONC > 0 else 1):
                r = await client.post("/chat/completions", content=json.dumps(body))  # type: ignore
            if r.status_code == 200:
                data = r.json()
                try:
                    await _cache.set(ck, json.dumps(data), ex=CACHE_TTL_S)  # type: ignore
                except Exception:
                    pass
                return data
            else:
                try:
                    jerr = r.json()
                except Exception:
                    jerr = {"error": r.text}
                err_last = f"HTTP {r.status_code} @ {base} ({body['model']}): {jerr}"
                log.warning(err_last)
        except Exception as e:
            err_last = f"{type(e).__name__}: {e} @ {base} ({body['model']})"
            log.warning(err_last)
        await asyncio.sleep(BACKOFF_S)

    raise RuntimeError(err_last or "LLM request failed")

# ────────────────────────────────────────────────────────────────────────────────
# STREAM + TOOL/FUNCTION CALLS

def _yield_marker(prefix: str, payload: Dict[str, Any]) -> str:
    return f"{prefix} {json.dumps(payload, ensure_ascii=False)}"

async def call_llm_stream_with_fallback(
    messages: List[Dict[str, Any]],
    *,
    user_id: Optional[str] = None,
    persona: Optional[str] = None,
    model_override: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_choice: Optional[Any] = None,
    extra_params: Optional[Dict[str, Any]] = None,
    yield_tools: bool = False,
) -> AsyncIterator[str]:
    await _ensure_clients()

    if user_id and LLM_AUTOTUNE:
        sug_model, sug_temp = suggest_params_for_user(user_id)
        model_use = model_override or sug_model or MODEL_PRIMARY
        temp_use = float(temperature) if temperature is not None else (sug_temp if sug_temp is not None else 0.7)
    else:
        model_use = model_override or MODEL_PRIMARY
        temp_use = float(temperature) if temperature is not None else 0.7

    persona_use = persona or get_user_persona(user_id)

    msgs = _norm_messages(_inject_persona(messages, persona_use))
    extra = dict(extra_params or {})
    base_body = {"model": model_use, "messages": msgs, "temperature": float(temp_use), "stream": True}
    if max_tokens:
        base_body["max_tokens"] = int(max_tokens)
    if tools:
        base_body["tools"] = tools
    if tool_choice:
        base_body["tool_choice"] = tool_choice
    base_body.update(extra)

    func_call = {"name": "", "arguments": ""}
    tool_calls_acc: Dict[int, Dict[str, Any]] = {}

    async def _handle_chunk_for_tools(delta: Dict[str, Any]) -> List[str]:
        out: List[str] = []
        if "function_call" in delta:
            fc = delta.get("function_call") or {}
            name = fc.get("name")
            args = fc.get("arguments")
            if name:
                func_call["name"] = name
            if isinstance(args, str):
                func_call["arguments"] += args
            if yield_tools:
                out.append(_yield_marker("<<<FUNCTION_CALL>>>", {"name": func_call["name"], "arguments": func_call["arguments"], "status": "update"}))
        if "tool_calls" in delta and isinstance(delta["tool_calls"], list):
            for part in delta["tool_calls"]:
                idx = part.get("index")
                if idx is None:
                    idx = len(tool_calls_acc)
                entry = tool_calls_acc.setdefault(idx, {"id": "", "name": "", "arguments": ""})
                if part.get("id"):
                    entry["id"] = part["id"]
                fn = (part.get("function") or {})
                if fn.get("name"):
                    entry["name"] = fn["name"]
                if isinstance(fn.get("arguments"), str):
                    entry["arguments"] += fn["arguments"]
                if yield_tools:
                    out.append(_yield_marker("<<<TOOL_CALL>>>", {"index": idx, "id": entry["id"], "name": entry["name"], "arguments": entry["arguments"], "status": "update"}))
        return out

    for attempt in range(0, 4):
        _, base, client = _select_provider(attempt)
        body = dict(base_body, model=model_use)
        try:
            async with asyncio.Semaphore(MAX_CONC if MAX_CONC > 0 else 1):
                async with client.stream("POST", "/chat/completions", content=json.dumps(body)) as r:  # type: ignore
                    if r.status_code != 200:
                        try:
                            raw = await r.aread()
                            txt = raw.decode("utf-8", errors="ignore")
                            try: jjson = json.loads(txt)
                            except Exception: jjson = {"error": txt[:500]}
                        except Exception:
                            jjson = {"error": "read error"}
                        log.warning(f"HTTP {r.status_code} @ {base} ({model_use}): {jjson}")
                        raise RuntimeError(f"HTTP {r.status_code}")

                    async for line in r.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            if yield_tools:
                                if func_call["name"] or func_call["arguments"]:
                                    yield _yield_marker("<<<FUNCTION_CALL>>>", {"name": func_call["name"], "arguments": func_call["arguments"], "status": "final"})
                                for idx, entry in tool_calls_acc.items():
                                    yield _yield_marker("<<<TOOL_CALL>>>", {"index": idx, "id": entry["id"], "name": entry["name"], "arguments": entry["arguments"], "status": "final"})
                            return
                        try:
                            chunk = json.loads(data_str)
                        except Exception:
                            continue
                        try:
                            ch0 = chunk["choices"][0]
                            delta = ch0.get("delta", {})
                        except Exception:
                            continue

                        txt = delta.get("content", "")
                        if txt:
                            yield txt
                        for mark in await _handle_chunk_for_tools(delta):
                            yield mark
            return
        except Exception as e:
            log.warning(f"Stream error ({base}/{model_use}): {e}")
            await asyncio.sleep(BACKOFF_S)

    # fallback non-stream
    try:
        data = await call_llm(
            messages,
            user_id=user_id,
            persona=persona,
            model_override=model_override,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            tool_choice=tool_choice,
            extra_params=extra_params,
        )
        txt = _extract_text_from_response(data)
        if txt:
            yield txt
        return
    except Exception as e:
        yield f"[ERROR] {type(e).__name__}: {e}"

# ────────────────────────────────────────────────────────────────────────────────
# „Stream first or fallback” – kompatybilny wrapper

async def stream_first_or_fallback(
    messages: List[Dict[str, Any]],
    *,
    user_id: Optional[str] = None,
    persona: Optional[str] = None,
    model_override: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_choice: Optional[Any] = None,
    extra_params: Optional[Dict[str, Any]] = None,
    yield_tools: bool = False,
) -> AsyncIterator[str]:
    async for chunk in call_llm_stream_with_fallback(
        messages,
        user_id=user_id,
        persona=persona,
        model_override=model_override,
        temperature=temperature,
        max_tokens=max_tokens,
        tools=tools,
        tool_choice=tool_choice,
        extra_params=extra_params,
        yield_tools=yield_tools,
    ):
        yield chunk

# ────────────────────────────────────────────────────────────────────────────────
# PROSTE API — tekst non-stream

async def chat_completion(
    messages: List[Dict[str, Any]],
    *,
    user_id: Optional[str] = None,
    persona: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_choice: Optional[Any] = None,
    extra_params: Optional[Dict[str, Any]] = None,
) -> str:
    data = await call_llm(
        messages,
        user_id=user_id,
        persona=persona,
        model_override=model,
        temperature=temperature,
        max_tokens=max_tokens,
        tools=tools,
        tool_choice=tool_choice,
        extra_params=extra_params,
    )
    return _extract_text_from_response(data)

# ────────────────────────────────────────────────────────────────────────────────
# ASYNC FEEDBACK EXPORT (S3 / ES)

_FB_EXPORT_Q: Optional[asyncio.Queue] = None
_FB_WORKER_STARTED = False
_S3_CLIENT = None
_ES_CLIENT: Optional[httpx.AsyncClient] = None
_S3_OK = False
_ES_OK = False

def _queue_feedback_export(rec: Dict[str, Any]) -> None:
    """Wrzuca rekord do kolejki eksportu (jeśli eksport włączony)."""
    if not FEEDBACK_EXPORT_ENABLE:
        return
    if not (FEEDBACK_EXPORT_S3_ENABLE or FEEDBACK_EXPORT_ES_ENABLE):
        return
    global _FB_EXPORT_Q, _FB_WORKER_STARTED
    if _FB_EXPORT_Q is None:
        _FB_EXPORT_Q = asyncio.Queue(maxsize=FEEDBACK_EXPORT_QUEUE_MAX)
    try:
        _FB_EXPORT_Q.put_nowait(rec)
    except Exception:
        # jeśli kolejka pełna – odpuść i zaloguj ostrzeżenie
        log.warning("Feedback export queue is full — dropping record")
        return
    if not _FB_WORKER_STARTED:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_fb_export_worker(), name="fb-export-worker")
            _FB_WORKER_STARTED = True
            log.info("[LLM] feedback export worker started")
        except RuntimeError:
            # brak działającej pętli — uruchomi się przy następnym wywołaniu, gdy pętla będzie gotowa
            pass

def _ensure_s3_client():
    global _S3_CLIENT, _S3_OK
    if _S3_CLIENT is not None or not FEEDBACK_EXPORT_S3_ENABLE:
        return
    if not S3_BUCKET:
        log.warning("S3 export enabled but S3_BUCKET not set — disabling S3 export")
        return
    try:
        import boto3  # opcjonalne
    except Exception as e:
        log.warning(f"S3 export requires boto3 ({e}) — disabling S3 export")
        return
    try:
        kw = {"region_name": S3_REGION}
        if S3_ENDPOINT_URL:
            kw["endpoint_url"] = S3_ENDPOINT_URL
        _S3_CLIENT = boto3.client("s3", **kw)
        _S3_OK = True
        log.info(f"S3 exporter ready (bucket={S3_BUCKET}, prefix={S3_PREFIX})")
    except Exception as e:
        log.warning(f"S3 client init failed: {e}")
        _S3_CLIENT = None
        _S3_OK = False

def _ensure_es_client():
    global _ES_CLIENT, _ES_OK
    if _ES_CLIENT is not None or not FEEDBACK_EXPORT_ES_ENABLE:
        return
    if not ES_BASE_URL:
        log.warning("ES export enabled but ES_BASE_URL not set — disabling ES export")
        return
    try:
        headers = {"Content-Type": "application/x-ndjson"}
        auth = None
        if ES_API_KEY:
            headers["Authorization"] = f"ApiKey {ES_API_KEY}"
        elif ES_USERNAME and ES_PASSWORD:
            auth = (ES_USERNAME, ES_PASSWORD)
        _ES_CLIENT = httpx.AsyncClient(base_url=ES_BASE_URL, timeout=httpx.Timeout(30), headers=headers, auth=auth, http2=False)
        _ES_OK = True
        log.info(f"ES exporter ready (index={ES_INDEX})")
    except Exception as e:
        log.warning(f"ES client init failed: {e}")
        _ES_CLIENT = None
        _ES_OK = False

async def _fb_export_worker():
    """Worker: zbiera rekordy z kolejki i flushuje do S3/ES w paczkach."""
    global _FB_EXPORT_Q
    _ensure_s3_client()
    _ensure_es_client()
    if _FB_EXPORT_Q is None:
        _FB_EXPORT_Q = asyncio.Queue(maxsize=FEEDBACK_EXPORT_QUEUE_MAX)

    batch: List[Dict[str, Any]] = []
    last_flush = time.time()

    async def _should_flush() -> bool:
        if len(batch) >= FEEDBACK_EXPORT_BATCH:
            return True
        if (time.time() - last_flush) >= FEEDBACK_EXPORT_FLUSH_S and batch:
            return True
        return False

    while True:
        try:
            try:
                item = await asyncio.wait_for(_FB_EXPORT_Q.get(), timeout=FEEDBACK_EXPORT_FLUSH_S)
                batch.append(item)
            except asyncio.TimeoutError:
                pass

            if not await _should_flush():
                continue

            # flush
            payload_lines = [json.dumps(r, ensure_ascii=False) for r in batch]
            await _flush_s3(payload_lines)
            await _flush_es(batch)
            batch.clear()
            last_flush = time.time()
        except Exception as e:
            log.warning(f"feedback export worker error: {e}")
            await asyncio.sleep(1.0)

def _s3_object_key() -> str:
    ts = time.strftime("%Y%m%d")
    now = int(time.time()*1000)
    return f"{S3_PREFIX}/date={ts}/feedback-{now}.jsonl"

async def _flush_s3(lines: List[str]) -> None:
    if not FEEDBACK_EXPORT_S3_ENABLE or not lines:
        return
    _ensure_s3_client()
    if not _S3_OK:
        return
    try:
        body = ("\n".join(lines) + "\n").encode("utf-8")
        loop = asyncio.get_running_loop()
        key = _s3_object_key()
        # boto3 jest synchroniczne — pchnij do executora
        import functools
        def _put():
            return _S3_CLIENT.put_object(Bucket=S3_BUCKET, Key=key, Body=body)  # type: ignore
        await loop.run_in_executor(None, _put)
        log.debug(f"S3 export: wrote {len(lines)} lines to s3://{S3_BUCKET}/{key}")
    except Exception as e:
        log.warning(f"S3 export failed: {e}")

async def _flush_es(batch: List[Dict[str, Any]]) -> None:
    if not FEEDBACK_EXPORT_ES_ENABLE or not batch:
        return
    _ensure_es_client()
    if not _ES_OK or _ES_CLIENT is None:
        return
    try:
        # _bulk NDJSON
        nd = []
        for rec in batch:
            nd.append(json.dumps({"index": {"_index": ES_INDEX}}, ensure_ascii=False))
            nd.append(json.dumps(rec, ensure_ascii=False))
        data = "\n".join(nd) + "\n"
        r = await _ES_CLIENT.post("/_bulk", content=data.encode("utf-8"))
        if r.status_code >= 300:
            try:
                j = r.json()
            except Exception:
                j = r.text
            log.warning(f"ES bulk failed: HTTP {r.status_code} {j}")
        else:
            log.debug(f"ES export: {len(batch)} docs")
    except Exception as e:
        log.warning(f"ES export failed: {e}")

# ────────────────────────────────────────────────────────────────────────────────
# CLEANUP HOOK

async def _aclose():
    global _client, _alt_client, _ES_CLIENT
    try:
        if _client:
            await _client.aclose()
        if _alt_client:
            await _alt_client.aclose()
        if _ES_CLIENT:
            await _ES_CLIENT.aclose()
    except Exception:
        pass

__all__ = [
    "call_llm",
    "call_llm_stream_with_fallback",
    "stream_first_or_fallback",
    "chat_completion",
    "record_feedback",
    "suggest_params_for_user",
    "set_user_persona",
    "get_user_persona",
    "PERSONAS",
]
# ==== [LLM_COMPAT_GLUE] – dopinka kompatybilna, NIE USUWAĆ ====
from typing import List, Dict, Any, Iterator, Optional

def _try_backend():
    backends = []
    try:
        from core import hotfix_chat as _hf
        backends.append(_hf)
    except Exception:
        pass
    try:
        from legacy_root_py import ff_sidecar as _ff
        backends.append(_ff)
    except Exception:
        pass
    return backends

def get_llm_client() -> Dict[str, Any]:
    return {"name": "mordzix-internal", "provider": "inproc", "ok": True}

def _call_backend(messages: List[Dict[str, str]], stream: bool, **kw):
    for b in _try_backend():
        for fn in ("llm_complete","complete","chat","complete_chat","local_complete"):
            f = getattr(b, fn, None)
            if callable(f):
                return f(messages=messages, stream=stream, **kw)
    raise RuntimeError("Brak dostępnego backendu LLM (core.hotfix_chat / legacy_root_py.ff_sidecar).")

def call_llm_raw(messages: List[Dict[str, str]], **kwargs) -> str:
    out = _call_backend(messages, stream=False, **kwargs)
    if isinstance(out, dict) and "text" in out:
        return out["text"]
    if isinstance(out, str):
        return out
    return str(out)

def call_llm_stream(messages: List[Dict[str, str]], **kwargs) -> Iterator[str]:
    out = _call_backend(messages, stream=True, **kwargs)
    try:
        for chunk in out:
            if isinstance(chunk, dict):
                yield chunk.get("delta") or chunk.get("text") or ""
            else:
                yield str(chunk)
    except TypeError:
        yield call_llm_raw(messages, **kwargs)

def chat_with_context(messages: List[Dict[str, str]], context: Optional[str] = None, stream: bool = False, **kwargs):
    if context:
        messages = [{"role": "system", "content": context}] + messages
    return call_llm_stream(messages, **kwargs) if stream else call_llm_raw(messages, **kwargs)
# ==== [END LLM_COMPAT_GLUE] ====
