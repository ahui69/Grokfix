# -*- coding: utf-8 -*-
from __future__ import annotations
from fastapi import APIRouter, Request
from typing import Dict, Any, Optional, List
from pathlib import Path
import json, hashlib, re, time

from .agent_diary import summarize_user_diary
from .quality_adaptation import get_adaptive_prefs
try:
    from .user_persona_inference import infer_persona, propose_personalization
except Exception:
    def infer_persona(uid: str) -> Dict[str,Any]:
        return {"user_id": uid, "style":"neutral", "llm_persona":None, "domains":[], "prefer_web":False, "recommendations":[], "updated_at":int(time.time())}
    def propose_personalization(uid: str) -> Dict[str,Any]:
        return {"tips":[]}

META_PATH = Path("/root/mordzix-ai/out/memory_meta.jsonl")

router = APIRouter(prefix="/api/profile", tags=["profile"])

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()[:16]

def _get_user_id(req: Request) -> str:
    auth = req.headers.get("Authorization","")
    tok = auth.replace("Bearer ","").strip()
    return _hash_token(tok) if tok else "default"

def _top_topics_from_meta(user_id: str, n: int = 200) -> List[str]:
    tx = {}
    if META_PATH.exists():
        with META_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                try: j = json.loads(line)
                except: continue
                if j.get("user_id") != user_id: continue
                if j.get("kind") in ("interaction","agent_diary"):
                    q = (j.get("question","") or "") + " " + " ".join(j.get("topics",[]))
                    for w in re.findall(r"[a-ząćęłńóśżź0-9]{3,}", q.lower()):
                        tx[w] = tx.get(w,0)+1
    return [k for k,_ in sorted(tx.items(), key=lambda x:(-x[1], x[0]))[:10]]

@router.get("/whoami")
async def whoami(request: Request):
    uid = _get_user_id(request)
    persona = infer_persona(uid)
    diary = summarize_user_diary(uid)
    adaptive = get_adaptive_prefs(uid)
    suggest = propose_personalization(uid)
    topics_meta = _top_topics_from_meta(uid)
    learned = (diary.get("lessons") or [])[:6]

    return {
        "ok": True,
        "user_id": uid,
        "style": persona.get("style","neutral"),
        "llm_persona": persona.get("llm_persona"),
        "domains": persona.get("domains", []),
        "prefer_web": bool(persona.get("prefer_web", False) or adaptive.get("force_web", False)),
        "top_topics": diary.get("top_topics") or topics_meta,
        "learned_by_agent": learned,
        "agent_suggestions": (suggest or {}).get("tips", []),
        "adaptive_now": adaptive,
        "quality_avg_score": diary.get("avg_score"),
    }
