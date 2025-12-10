# -*- coding: utf-8 -*-
from __future__ import annotations
from fastapi import APIRouter, Query
from typing import Dict, Any, List, Optional
from pathlib import Path
import os, json, re, collections

_META_DIR = Path(os.getenv("META_DIR", "/root/mordzix-ai/data/meta"))
_META_FILE = _META_DIR / "memory_meta.jsonl"
_EVAL_FILE = _META_DIR / "eval_log.jsonl"

router = APIRouter(prefix="/api/meta", tags=["meta-user"])

def _iter_jsonl(path: Path):
    if not path.exists(): return
    with path.open("r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln: continue
            try:
                yield json.loads(ln)
            except Exception:
                continue

def _top_words(texts: List[str], k: int = 10) -> List[str]:
    cnt = collections.Counter()
    for t in texts:
        for w in re.findall(r"[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ0-9]{4,}", (t or "").lower()):
            if w in {"https","http","jest","taki","tego","tą","toby","aby","albo","czy","oraz","która","który","które"}:
                continue
            cnt[w] += 1
    return [w for w,_ in cnt.most_common(k)]

@router.get("/user_summary")
def user_summary(user_id: str = Query(..., description="Hashowany id (z assistant_endpoint)")):
    questions, intents, web_yes, web_no = [], collections.Counter(), 0, 0
    errors = timeouts = 0
    for rec in _iter_jsonl(_META_FILE) or []:
        if rec.get("user_id") != user_id: 
            continue
        q = rec.get("question","")
        if q: questions.append(q)
        intent = (rec.get("intent") or "chat").lower()
        intents[intent] += 1
        if rec.get("web_used") is True: web_yes += 1
        elif rec.get("web_used") is False: web_no += 1
        if rec.get("error"): errors += 1
        if rec.get("timeout"): timeouts += 1

    eval_actions = collections.Counter()
    hallu_high = 0
    for rec in _iter_jsonl(_EVAL_FILE) or []:
        if rec.get("kind") in {"joined_eval"} and rec.get("user_id") == user_id:
            v = rec.get("verdict") or {}
            act = (v.get("action") or "ok").lower()
            eval_actions[act] += 1
            if (v.get("hallucination_risk") or "").lower() == "high":
                hallu_high += 1

    topics = _top_words(questions, 12)
    suggestions = []
    if eval_actions.get("research",0) >= max(2, eval_actions.get("ok",0)):
        suggestions.append("Aktywować tryb web-first (często potrzebny research).")
    if hallu_high >= 2:
        if topics:
            suggestions.append(f"Być bardziej precyzyjnym w: {', '.join(topics[:5])}.")
        else:
            suggestions.append("Zaostrzyć walidację faktów (wysokie ryzyko halucynacji).")
    if errors + timeouts > 0:
        suggestions.append("Zwiększyć timeout streamu lub dodać fallback model.")

    return {
        "ok": True,
        "user_id": user_id,
        "stats": {
            "intents": intents,
            "web_used": {"yes": web_yes, "no": web_no},
            "eval_actions": eval_actions,
            "hallucination_high": hallu_high,
            "errors": errors, "timeouts": timeouts
        },
        "top_topics": topics,
        "personalization": suggestions
    }
