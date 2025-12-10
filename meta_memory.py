#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Meta-memory: zapisuje telemetrię konwersacji i daje podsumowania per user.
Format: JSONL (jeden rekord na linię), bezpieczne append-only.
"""

from __future__ import annotations
import os, json, time, threading
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from collections import Counter, defaultdict

META_PATH = Path(os.getenv("META_MEMORY_PATH", "/root/mordzix-ai/out/memory_meta.jsonl"))
META_PATH.parent.mkdir(parents=True, exist_ok=True)
_LOCK = threading.Lock()

def _append_jsonl(obj: Dict[str, Any]) -> None:
    try:
        with _LOCK:
            with META_PATH.open("a", encoding="utf-8") as f:
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[META] write failed: {e}")

def log_interaction_meta(
    *,
    user_id: str,
    session_id: Optional[str],
    intent: str,
    web_used: bool,
    complete: Optional[bool],
    duration_ms: Optional[int],
    timed_out: bool,
    error: Optional[str],
    answer_len: int,
    eval_score: Optional[float] = None,
    eval_flags: Optional[Dict[str, Any]] = None,
    auto_research_used: Optional[bool] = None,
    improved: Optional[bool] = None,
    tags: Optional[List[str]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    rec = {
        "ts": int(time.time()),
        "user_id": user_id,
        "session_id": session_id,
        "intent": intent,
        "web_used": bool(web_used),
        "complete": complete,
        "duration_ms": duration_ms,
        "timed_out": bool(timed_out),
        "error": (error or None),
        "answer_len": int(answer_len),
        "eval_score": eval_score,
        "eval_flags": eval_flags or {},
        "auto_research_used": auto_research_used,
        "improved": improved,
        "tags": tags or [],
        "extra": extra or {},
        "kind": "interaction",
        "version": 1,
    }
    _append_jsonl(rec)

def log_feedback(
    *,
    user_id: str,
    session_id: Optional[str],
    question: str,
    bad_answer: str,
    critique: str,
    better_answer: str,
) -> None:
    rec = {
        "ts": int(time.time()),
        "user_id": user_id,
        "session_id": session_id,
        "kind": "user_feedback",
        "question": question,
        "bad_answer": bad_answer,
        "critique": critique,
        "better_answer": better_answer,
    }
    _append_jsonl(rec)

def log_session_retrospect(
    *,
    user_id: str,
    session_id: str,
    summary: str,
    main_topics: List[str],
    hard_points: List[str],
    lessons: List[str],
) -> None:
    rec = {
        "ts": int(time.time()),
        "user_id": user_id,
        "session_id": session_id,
        "kind": "session_retrospect",
        "summary": summary,
        "main_topics": main_topics,
        "hard_points": hard_points,
        "lessons": lessons,
    }
    _append_jsonl(rec)

def iter_user(user_id: str, last_n: int = 5000):
    try:
        lines: List[str] = []
        with META_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                lines.append(line)
        for line in reversed(lines[-last_n:]):
            try:
                j = json.loads(line)
            except Exception:
                continue
            if j.get("user_id") == user_id:
                yield j
    except FileNotFoundError:
        return

def summarize_user(user_id: str, last_n: int = 1000) -> Dict[str, Any]:
    intents = Counter()
    sources = Counter()
    issues = Counter()
    scores: List[float] = []
    hallu = 0
    total = 0
    sessions = set()

    for rec in iter_user(user_id, last_n=last_n):
        total += 1
        sessions.add(rec.get("session_id"))
        if rec.get("kind") == "interaction":
            intents[rec.get("intent","chat")] += 1
            if rec.get("web_used"): sources["web"] += 1
            if rec.get("timed_out"): issues["timeout"] += 1
            if rec.get("error"): issues["error"] += 1
            ev = rec.get("eval_flags") or {}
            if ev.get("hallucination"): hallu += 1
            sc = rec.get("eval_score")
            if isinstance(sc,(int,float)): scores.append(float(sc))
        elif rec.get("kind") == "user_feedback":
            issues["user_marked_wrong"] += 1
        elif rec.get("kind") == "session_retrospect":
            issues["retrospects"] += 1

    avg_score = round(sum(scores)/len(scores),3) if scores else None
    hallu_rate = round(hallu/max(total,1),3) if total else 0.0

    personalization: List[str] = []
    if hallu_rate > 0.1:
        personalization.append("Włącz dokładniejszą walidację faktów (fact-check).")
    if (sources["web"]/max(total,1)) > 0.4:
        personalization.append("Aktywuj tryb web-first dla bieżących tematów.")
    if avg_score is not None and avg_score < 0.7:
        personalization.append("Obniż temperaturę modeli i wydłuż czas na generację.")

    return {
        "user_id": user_id,
        "stats": {
            "events": total,
            "sessions": len([s for s in sessions if s]),
            "avg_eval_score": avg_score,
            "hallucination_rate": hallu_rate,
        },
        "top_intents": intents.most_common(10),
        "source_usage": dict(sources),
        "issues": dict(issues),
        "recommendations": personalization,
    }
# === HOTFIX: append-only meta loggers (idempotent) ===
from pathlib import Path as _Path
import json as _json, time as _time

def _append_meta(rec: dict) -> str:
    p = _Path(META_PATH) if isinstance(META_PATH, str) else META_PATH  # type: ignore[name-defined]
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(_json.dumps(rec, ensure_ascii=False) + "\n")
    return str(p)

def log_interaction(user_id: str, question: str, answer: str,
                    improved_answer: str | None = None, meta: dict | None = None) -> str:
    """Jedna rozmowa: Q, A i (opcjonalnie) lepsza wersja A -> do FT."""
    return _append_meta({
        "kind": "interaction",
        "ts": int(_time.time()),
        "user_id": user_id,
        "question": question,
        "answer": answer,
        "improved_answer": improved_answer,
        "meta": meta or {}
    })

def log_user_feedback(user_id: str, question: str, bad_answer: str,
                      critique: str = "", better_answer: str = "") -> str:
    """Preferencje do RLHF/RLAIF (prompt, chosen/rejected + krytyka)."""
    return _append_meta({
        "kind": "user_feedback",
        "ts": int(_time.time()),
        "user_id": user_id,
        "question": question,
        "bad_answer": bad_answer,
        "critique": critique,
        "better_answer": better_answer,
    })
# ==== [TAIL_COMPAT] – wymagane przez meta_endpoint ====
from pathlib import Path as _Path
try:
    META_PATH  # noqa: F401
except NameError:
    META_PATH = _Path("/root/mordzix-ai/out/memory_meta.jsonl")

def tail(n: int = 200, path: _Path = META_PATH) -> str:
    try:
        with path.open("r", encoding="utf-8") as f:
            lines = f.readlines()
        return "".join(lines[-n:])
    except FileNotFoundError:
        return ""
# ==== [END TAIL_COMPAT] ====
