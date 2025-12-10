# -*- coding: utf-8 -*-
from __future__ import annotations
import os, json, asyncio, threading
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional
from .llm import chat_completion

_META_DIR = Path(os.getenv("META_DIR", "/root/mordzix-ai/data/meta"))
_META_FILE = _META_DIR / "memory_meta.jsonl"
_SESS_FILE = _META_DIR / "session_summaries.jsonl"
_LOCK = threading.Lock()

def _now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"

def _iter_meta():
    if not _META_FILE.exists(): return
    with _META_FILE.open("r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln: continue
            try: yield json.loads(ln)
            except Exception: continue

def _append(path: Path, obj: Dict[str, Any]) -> None:
    try:
        with _LOCK:
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[RETRO] write failed: {e}")

async def summarize_session(session_id: str, user_id: Optional[str]) -> Dict[str, Any]:
    entries = [r for r in (_iter_meta() or []) if r.get("session_id")==session_id]
    if not entries:
        return {"ok": False, "error": "no entries"}
    # posortuj wg ts jeśli się da
    try:
        entries.sort(key=lambda r: r.get("ts",""))
    except Exception:
        pass
    convo = []
    for e in entries[-40:]:
        q = e.get("question","")
        a_len = e.get("answer_len")
        convo.append(f"Q: {q}\nA_len: {a_len}")

    sys = (
        "Summarize the session as JSON. Keys: "
        "summary (string), key_topics (string[]), lessons (string[]), "
        "memory_facts (string[]). No prose."
    )
    msgs = [{"role":"system","content":sys},
            {"role":"user","content":"\n\n".join(convo)}]
    out = await chat_completion(msgs, temperature=0.2, max_tokens=500)
    try:
        data = json.loads(out.strip())
    except Exception:
        data = {"summary": out[:800], "key_topics": [], "lessons": [], "memory_facts": []}

    rec = {"ts": _now(), "session_id": session_id, "user_id": user_id, "result": data}
    _append(_SESS_FILE, rec)
    return {"ok": True, "result": data}

def schedule_session_retrospect(session_id: Optional[str], user_id: Optional[str]) -> None:
    if not session_id:
        return
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(summarize_session(session_id, user_id))
    except RuntimeError:
        asyncio.run(summarize_session(session_id, user_id))
