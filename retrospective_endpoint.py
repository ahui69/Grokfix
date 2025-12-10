# -*- coding: utf-8 -*-
from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from .retrospective import summarize_session

router = APIRouter(prefix="/api/meta", tags=["meta-retro"])

class RetroReq(BaseModel):
    session_id: str
    user_id: Optional[str] = None

@router.post("/session/retrospect")
async def session_retrospect(body: RetroReq):
    return await summarize_session(body.session_id, body.user_id)
