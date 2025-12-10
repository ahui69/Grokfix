# -*- coding: utf-8 -*-
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime
import os, json, threading
from .critique_engine import improve_answer, derive_correction_rule

_FEED_DIR = Path(os.getenv("FEEDBACK_DIR", "/root/mordzix-ai/data/feedback"))
_FEED_DIR.mkdir(parents=True, exist_ok=True)
_FEED_FILE = _FEED_DIR / "feedback.jsonl"
_CORR_FILE = _FEED_DIR / "corrections.jsonl"
_LOCK = threading.Lock()

def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"

def _append(path: Path, obj: Dict[str, Any]) -> None:
    try:
        with _LOCK:
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[FEEDBACK] write failed: {e}")

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

class FeedbackSubmit(BaseModel):
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    question: str = Field(..., min_length=1)
    bad_answer: str = Field(..., min_length=1)
    critique: str = Field(..., min_length=1)
    messages: Optional[List[Dict[str, Any]]] = None
    corrected_answer: Optional[str] = None

@router.post("/submit")
async def submit_feedback(body: FeedbackSubmit):
    msgs = body.messages or [{"role":"user","content": body.question},
                             {"role":"assistant","content": body.bad_answer}]
    corrected = body.corrected_answer or await improve_answer(msgs, body.bad_answer, body.critique)

    rec = {
        "ts": _now_iso(),
        "user_id": body.user_id, "session_id": body.session_id,
        "question": body.question, "bad_answer": body.bad_answer,
        "critique": body.critique, "corrected_answer": corrected
    }
    _append(_FEED_FILE, rec)

    rule = await derive_correction_rule(body.question, body.bad_answer, body.critique, corrected)
    _append(_CORR_FILE, {"ts": _now_iso(), "user_id": body.user_id, "rule": rule})

    return {"ok": True, "corrected_answer": corrected, "rule": rule}

@router.get("/stats")
def feedback_stats():
    total = corr = 0
    try:
        if _FEED_FILE.exists():
            total = sum(1 for _ in _FEED_FILE.open("r", encoding="utf-8"))
        if _CORR_FILE.exists():
            corr = sum(1 for _ in _CORR_FILE.open("r", encoding="utf-8"))
    except Exception:
        pass
    return {"ok": True, "feedback_count": total, "learned_rules": corr}
