# -*- coding: utf-8 -*-
"""
Zaawansowana warstwa LLM dla Mordzixa.

Cel:
- ZERO odpalania event loopa przy imporcie,
- spójny wrapper na core.llm:
    * call_llm
    * chat_with_context
- wsparcie dla:
    * web search context
    * memory / unified + hierarchical
    * psyche / nastrój
    * poprzednich wiadomości

Publiczne API:
    - is_initialized()
    - ensure_initialized()
    - call_advanced_llm(...)
    - adaptive_llm_call(...)  – alias wsteczny
    - aask(...)               – alias
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import asyncio

from core.helpers import log_info, log_error
from core.llm import (
    call_llm,
    chat_with_context,
)

_initialized: bool = False


async def _auto_init() -> None:
    """Lekka inicjalizacja – można wołać z innych modułów."""
    global _initialized
    if _initialized:
        return
    _initialized = True
    log_info("[ADV_LLM] Advanced LLM initialized", "ADV_LLM")


def is_initialized() -> bool:
    return _initialized


async def ensure_initialized() -> None:
    """Publiczny entrypoint do inicjalizacji."""
    await _auto_init()


async def _run_sync_in_executor(func, *args, **kwargs):
    """
    Pomocnik: odpala synchroniczną funkcję (call_llm / chat_with_context)
    w executorze, tak żeby można było ją normalnie używać z 'await'.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))


async def call_advanced_llm(*, prompt: str, **kwargs: Any) -> Dict[str, Any]:
    """
    Główna funkcja – wywołanie LLM z warstwy advanced.

    Wspiera dwa główne tryby:

    1) 'messages' w kwargs:
        - spodziewamy się listy [{role, content}, ...]
        - wtedy idzie przez core.llm.call_llm(messages=...)

    2) tryb "prompt + context":
        - prompt = aktualne pytanie usera
        - kwargs może zawierać:

            personality: str
            web_policy: str
            memory_policy: str
            psyche_hint: str

            web_snippets: List[str]
            memory_snippets: List[str]
            psyche_state: str

            extra_system_msgs: List[str]
            previous_messages: List[Dict[str, str]]

            oraz standardowe opcje:
            temperature: float
            max_tokens: int
            timeout_s: float
            skip_cache: bool
            cache_ttl: int
    """
    await ensure_initialized()

    # 1) Tryb z pełnymi messages (np. jakieś legacy, multi-agent itp.)
    if "messages" in kwargs and kwargs["messages"] is not None:
        messages = kwargs.pop("messages")
        try:
            result_str: str = await _run_sync_in_executor(
                call_llm,
                messages,
                **kwargs,
            )
            return {
                "ok": True,
                "result": result_str,
                "mode": "messages",
            }
        except Exception as e:
            log_error(f"[ADV_LLM] call_llm(messages=...) failed: {e}")
            return {
                "ok": False,
                "error": "llm_call_failed",
                "details": str(e),
                "mode": "messages",
            }

    # 2) Tryb prompt + context
    personality: Optional[str] = kwargs.pop("personality", None)
    web_policy: Optional[str] = kwargs.pop("web_policy", None)
    memory_policy: Optional[str] = kwargs.pop("memory_policy", None)
    psyche_hint: Optional[str] = kwargs.pop("psyche_hint", None)

    web_snippets: Optional[List[str]] = kwargs.pop("web_snippets", None)
    memory_snippets: Optional[List[str]] = kwargs.pop("memory_snippets", None)
    psyche_state: Optional[str] = kwargs.pop("psyche_state", None)

    extra_system_msgs: Optional[List[str]] = kwargs.pop(
        "extra_system_msgs", None
    )
    previous_messages: Optional[List[Dict[str, str]]] = kwargs.pop(
        "previous_messages", None
    )

    try:
        result_str: str = await _run_sync_in_executor(
            chat_with_context,
            user_content=prompt,
            personality=personality,
            web_policy=web_policy,
            memory_policy=memory_policy,
            psyche_hint=psyche_hint,
            web_snippets=web_snippets,
            memory_snippets=memory_snippets,
            psyche_state=psyche_state,
            extra_system_msgs=extra_system_msgs,
            previous_messages=previous_messages,
            **kwargs,
        )
        return {
            "ok": True,
            "result": result_str,
            "mode": "prompt+context",
        }
    except Exception as e:
        log_error(f"[ADV_LLM] call_advanced_llm(prompt+context) failed: {e}")
        return {
            "ok": False,
            "error": "llm_call_failed",
            "details": str(e),
            "mode": "prompt+context",
        }


async def adaptive_llm_call(*, prompt: str, **kwargs: Any) -> Dict[str, Any]:
    """
    Alias zgodny wstecznie – stare moduły importują adaptive_llm_call
    z core.advanced_llm.
    """
    return await call_advanced_llm(prompt=prompt, **kwargs)


async def aask(prompt: str, **kwargs: Any) -> Dict[str, Any]:
    """Wygodny alias: await aask("co tam")"""
    return await call_advanced_llm(prompt=prompt, **kwargs)


__all__ = [
    "is_initialized",
    "ensure_initialized",
    "call_advanced_llm",
    "adaptive_llm_call",
    "aask",
]
