#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import asyncio
from typing import Any, Dict, List, Optional
from .llm import chat_completion
from .meta_memory import log_session_retrospect

async def _session_dump(session_id: str) -> str:
    """
    Zbiera z DB (jeśli jest) albo zwraca placeholder. Nie wywala błędu.
    """
    try:
        from .sessions import get_session_messages  # jeśli masz helper
        msgs = get_session_messages(session_id)  # type: ignore
        chunks = []
        for m in msgs[-200:]:
            role = m.get("role","user")
            content = m.get("content","")
            chunks.append(f"{role.upper()}: {content}")
        return "\n".join(chunks)
    except Exception:
        return "(no session fetch available)"

async def _retrospect(session_id: str, user_id: str):
    dump = await _session_dump(session_id)
    sys = (
        "Analyze the conversation dump. Return three sections:\n"
        "1) Short summary (3-5 bullets)\n"
        "2) Main topics (comma separated keywords)\n"
        "3) Hard points (where assistant struggled)\n"
        "4) Lessons (what to do better next time)\n"
    )
    prompt = [
        {"role":"system","content": sys},
        {"role":"user","content": dump}
    ]
    try:
        txt = await chat_completion(prompt, temperature=0.2, max_tokens=600)
    except Exception:
        txt = "Summary: n/a\nTopics: n/a\nHard points: n/a\nLessons: n/a"

    # prosta ekstrakcja
    def _lines_after(h: str) -> str:
        i = txt.lower().find(h)
        return txt[i+len(h):] if i>=0 else ""

    summary = _lines_after("summary")
    topics = [x.strip(" ,.-") for x in _lines_after("topics").split(",") if x.strip()]
    hard = [x.strip(" *-") for x in _lines_after("hard") .split("\n") if x.strip()]
    lessons = [x.strip(" *-") for x in _lines_after("lesson") .split("\n") if x.strip()]

    log_session_retrospect(
        user_id=user_id,
        session_id=session_id,
        summary=summary.strip()[:2000],
        main_topics=topics[:12],
        hard_points=hard[:8],
        lessons=lessons[:8],
    )

def schedule_session_retrospect(session_id: str, user_id: str):
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_retrospect(session_id, user_id))
    except RuntimeError:
        # nie ma pętli – uruchom leniwie
        asyncio.run(_retrospect(session_id, user_id))
