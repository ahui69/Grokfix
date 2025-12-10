# -*- coding: utf-8 -*-
from __future__ import annotations
import os, json, threading, time
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional
from .llm import chat_completion

_META_DIR = Path(os.getenv("META_DIR", "/root/mordzix-ai/data/meta"))
_META_DIR.mkdir(parents=True, exist_ok=True)
_EVAL_FILE = _META_DIR / "eval_log.jsonl"
_LOCK = threading.Lock()

def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"

def _append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    try:
        with _LOCK:
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[EVAL] write failed: {e}")

async def evaluate_answer(messages: List[Dict[str, str]],
                          sources: Optional[List[str]] = None,
                          strict: bool = True) -> Dict[str, Any]:
    sys = (
        "You are a strict evaluator. Return ONLY valid JSON with keys: "
        "truthful (bool), complete (bool), hallucination_risk ('low'|'medium'|'high'), "
        "issues (string[]), action ('ok'|'research'|'refine'). "
        "Judge adherence to the prompt, logic, and source use. No prose, JSON only."
    )
    if strict:
        sys += " If unsure, set action='research' and hallucination_risk at least 'medium'."
    msgs = [{"role":"system","content":sys}] + messages
    if sources:
        msgs.append({"role":"system","content":"### SOURCES\n" + "\n".join(sources)})

    out = await chat_completion(msgs, temperature=0.0, max_tokens=300)
    try:
        verdict = json.loads(out.strip())
    except Exception:
        verdict = {"truthful": None, "complete": None, "hallucination_risk": "unknown",
                   "issues": ["non-json-eval-output"], "action": "research", "raw": out}
    rec = {"ts": _now_iso(), "kind": "eval", "verdict": verdict, "sources": sources or []}
    _append_jsonl(_EVAL_FILE, rec)
    return verdict

async def meta_critique(verdict: Dict[str, Any]) -> Dict[str, Any]:
    sys = (
        "You are a meta-critic. Critique the evaluator's JSON verdict. "
        "Return ONLY JSON with keys: agrees (bool), issues (string[]), final_action ('ok'|'research'|'refine'). "
        "No prose."
    )
    msgs = [{"role":"system","content":sys},
            {"role":"user","content":json.dumps(verdict, ensure_ascii=False)}]
    out = await chat_completion(msgs, temperature=0.0, max_tokens=200)
    try:
        m = json.loads(out.strip())
    except Exception:
        m = {"agrees": None, "issues": ["non-json-meta-critique"], "final_action": "research", "raw": out}
    rec = {"ts": _now_iso(), "kind": "meta_critique", "meta": m}
    _append_jsonl(_EVAL_FILE, rec)
    return m

async def auto_eval_and_log(user_id: Optional[str],
                            session_id: Optional[str],
                            messages: List[Dict[str, str]],
                            answer: str,
                            sources: Optional[List[str]] = None,
                            intent: Optional[str] = None,
                            web_used: Optional[bool] = None) -> Dict[str, Any]:
    msgs = list(messages) + [{"role":"assistant","content":answer}]
    v = await evaluate_answer(msgs, sources)
    m = await meta_critique(v)
    rec = {
        "ts": _now_iso(),
        "kind": "joined_eval",
        "user_id": user_id,
        "session_id": session_id,
        "intent": intent, "web_used": web_used,
        "verdict": v, "meta_critique": m
    }
    _append_jsonl(_EVAL_FILE, rec)
    return {"verdict": v, "meta_critique": m}

async def improve_answer(messages: List[Dict[str,str]],
                         bad_answer: str,
                         critique: str,
                         knowledge_ctx: str = "") -> str:
    sys = (
        "Rewrite the assistant's answer using the critique. Fix factual errors, add missing steps, "
        "and include sources if the critique calls for them. Keep it concise and correct."
    )
    user = "### CRITIQUE\n" + critique
    if knowledge_ctx:
        user += "\n\n### KNOWLEDGE\n" + knowledge_ctx
    msgs = [{"role":"system","content":sys}] + messages + [
        {"role":"assistant","content":bad_answer},
        {"role":"user","content":user}
    ]
    out = await chat_completion(msgs, temperature=0.2, max_tokens=1000)
    return out

async def derive_correction_rule(question: str,
                                 bad_answer: str,
                                 critique: str,
                                 good_answer: str) -> Dict[str, Any]:
    sys = (
        "Extract a compact correction rule from the case. "
        "Return ONLY JSON with keys: pattern_keywords (string[]), constraints (string[]), fix_summary (string), "
        "example_good (string). No prose."
    )
    u = json.dumps({
        "question": question, "bad_answer": bad_answer,
        "critique": critique, "good_answer": good_answer
    }, ensure_ascii=False)
    msgs = [{"role":"system","content":sys}, {"role":"user","content":u}]
    out = await chat_completion(msgs, temperature=0.0, max_tokens=400)
    try:
        return json.loads(out.strip())
    except Exception:
        return {"pattern_keywords": [], "constraints": [], "fix_summary": "n/a", "example_good": good_answer}
