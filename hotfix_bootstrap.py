from __future__ import annotations

from typing import List, Dict, Any, Optional

import sqlite3
from fastapi import APIRouter
from pydantic import BaseModel

from . import hotfix_chat

DB = "/root/mordzix-ai/mem.db"


def _search_mem_like(q: str, limit: int = 5) -> list[str]:
    """
    Prosty LIKE po lokalnej bazie, na wszelki wypadek.
    Nieużywane w normalnym trybie, ale zostawiam jako narzędzie pomocnicze.
    """
    rows: list[str] = []
    try:
        con = sqlite3.connect(DB)
        cur = con.cursor()

        # facts
        try:
            cur.execute(
                "SELECT text FROM facts "
                "WHERE IFNULL(deleted,0)=0 AND text LIKE ? "
                "ORDER BY created DESC LIMIT ?",
                (f"%{q}%", limit),
            )
            rows += [r[0] for r in cur.fetchall()]
        except Exception:
            pass

        # episodic_memory
        try:
            cur.execute(
                "SELECT content FROM episodic_memory "
                "WHERE content LIKE ? "
                "ORDER BY timestamp DESC LIMIT ?",
                (f"%{q}%", limit),
            )
            rows += [r[0] for r in cur.fetchall()]
        except Exception:
            pass

        # semantic_memory
        try:
            cur.execute(
                "SELECT content FROM semantic_memory "
                "WHERE content LIKE ? "
                "ORDER BY timestamp DESC LIMIT ?",
                (f"%{q}%", limit),
            )
            rows += [r[0] for r in cur.fetchall()]
        except Exception:
            pass

        con.close()
    except Exception:
        pass

    return rows


class HotfixMessage(BaseModel):
    role: str
    content: str


class HotfixChatRequest(BaseModel):
    messages: List[HotfixMessage]
    stream: bool = False
    user_id: Optional[str] = None


async def _run_hotfix_chat(payload: HotfixChatRequest) -> Dict[str, Any]:
    """
    Wspólny executor – pełny pipeline z hotfix_chat:
    - advanced_cognitive_engine (jak działa)
    - LLM
    - web (jak trzeba)
    """
    messages: List[Dict[str, str]] = [
        {"role": m.role, "content": m.content} for m in payload.messages
    ]

    result = await hotfix_chat.chat_with_hotfix(
        messages=messages,
        user_id=payload.user_id,
        use_advanced=True,
        allow_web=True,
    )

    if not isinstance(result, dict):
        # awaryjnie opakuj w sensowny JSON
        return {
            "ok": True,
            "answer": str(result),
            "sources": [],
            "metadata": {
                "source": "hotfix_chat_direct",
                "note": "Result was not dict, wrapped in hotfix_bootstrap.",
            },
        }

    meta = result.get("metadata") or {}
    meta.setdefault("source", "hotfix_chat")
    result["metadata"] = meta
    return result


def register(app) -> None:
    """
    Rejestruje hotfixy BEZ zabijania głównego endpointu.

    Zasada:
    - jeśli /api/chat/assistant już istnieje -> NIE rejestrujemy naszego hotfixa
    - jeśli nie istnieje -> dostajesz pełny chat na bazie hotfix_chat.chat_with_hotfix
    - to samo dla /api/chat/assistant/stream (pseudo-stream, ale pełna logika)
    """
    router = APIRouter()

    # Sprawdź, co już siedzi w app
    try:
        existing_paths = {getattr(r, "path", None) for r in getattr(app, "routes", [])}
    except Exception:
        existing_paths = set()

    chat_exists = "/api/chat/assistant" in existing_paths
    stream_exists = "/api/chat/assistant/stream" in existing_paths

    # Jeśli NIE ma głównego /api/chat/assistant -> rejestrujemy pełny hotfix chat
    if not chat_exists:
        @router.post("/api/chat/assistant")
        async def chat_assistant_hotfix(payload: HotfixChatRequest):
            result = await _run_hotfix_chat(payload)
            return result

    # Jeśli NIE ma streama -> rejestrujemy prosty pseudo-stream (1 chunk, ale pełna logika)
    if not stream_exists:
        @router.post("/api/chat/assistant/stream")
        async def chat_assistant_stream_hotfix(payload: HotfixChatRequest):
            result = await _run_hotfix_chat(payload)
            meta = result.get("metadata") or {}
            meta["stream_simulated"] = True
            meta.setdefault("source", "hotfix_chat")
            result["metadata"] = meta
            return result

    # Jeśli dodaliśmy jakieś trasy – podpinamy router
    if router.routes:
        app.include_router(router)
