#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .auto_eval import auto_eval_and_log, handle_user_feedback

router = APIRouter(prefix="/api/eval", tags=["evaluation"])

class EvalBody(BaseModel):
    user_id: str
    session_id: Optional[str] = None
    messages: List[Dict[str,str]]
    answer: str
    intent: str = "chat"
    web_used: bool = False
    duration_ms: int = 0

@router.post("/check")
async def eval_check(body: EvalBody):
    try:
        res = await auto_eval_and_log(
            body.user_id, body.session_id, body.messages, body.answer,
            intent=body.intent, web_used=body.web_used, duration_ms=body.duration_ms
        )
        return {"ok": True, **res}
    except Exception as e:
        raise HTTPException(500, f"eval failed: {e}")

class FeedbackBody(BaseModel):
    user_id: str
    session_id: Optional[str] = None
    question: str
    bad_answer: str
    critique: str
    better_answer: str

@router.post("/feedback")
async def submit_feedback(body: FeedbackBody):
    await handle_user_feedback(
        user_id=body.user_id,
        session_id=body.session_id,
        question=body.question,
        bad_answer=body.bad_answer,
        critique=body.critique,
        better_answer=body.better_answer,
    )
    return {"ok": True}
