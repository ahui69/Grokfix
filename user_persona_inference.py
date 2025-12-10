#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import os, json, re, time
from typing import Any, Dict, List, Optional
from pathlib import Path
from collections import Counter

from .meta_memory import iter_user, summarize_user
from .llm import chat_completion, set_user_persona, PERSONAS

PERSONA_STORE = Path(os.getenv("USER_PERSONAS_PATH", "/root/mordzix-ai/out/user_personas.json"))
PERSONA_STORE.parent.mkdir(parents=True, exist_ok=True)

def _load() -> Dict[str, Any]:
    if PERSONA_STORE.exists():
        try:
            return json.loads(PERSONA_STORE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def _save(data: Dict[str, Any]) -> None:
    PERSONA_STORE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def _heuristic_style(samples: List[str]) -> str:
    txt = " ".join(samples[:20]).lower()
    if re.search(r"\b(kurwa|chuj|pierdol|jeban|spierdal)\b", txt): return "edgy"
    if re.search(r"(proszę|uprzejmi|dziękuj|czy mógłbyś)", txt): return "polite"
    if re.search(r"(hej|elo|siema|xd|:D)", txt): return "casual"
    return "neutral"

def _map_style_to_llm_persona(style: str) -> Optional[str]:
    if style == "edgy" and "kurwabot" in PERSONAS: return "kurwabot"
    if style == "polite" and "mentor" in PERSONAS: return "mentor"
    if style == "casual" and "flirt" in PERSONAS: return "flirt"
    return None

def _collect_text_snippets(user_id: str, limit: int = 50) -> List[str]:
    """Zbieraj krótkie fragmenty z meta (np. z retrospektów)."""
    out: List[str] = []
    for rec in iter_user(user_id, last_n=2000):
        if rec.get("kind") == "user_feedback":
            out.append(rec.get("question","")[:200])
            out.append(rec.get("critique","")[:200])
        elif rec.get("kind") == "session_retrospect":
            out.extend(rec.get("main_topics") or [])
            out.append(rec.get("summary","")[:200])
    return out[:limit]

def infer_persona(user_id: str) -> Dict[str, Any]:
    """Wnioskujemy styl, domeny i preferencje web na bazie meta + heurystyk (LLM opcjonalnie)."""
    su = summarize_user(user_id, last_n=2000)
    snippets = _collect_text_snippets(user_id)
    style = _heuristic_style(snippets)
    llm_persona = _map_style_to_llm_persona(style)

    # domeny
    intents = [i for i,_ in su.get("top_intents", [])]
    topics = [t for t in (su.get("source_usage") or {}).keys()]
    domains = intents[:5]

    # preferencje web
    web_share = (su.get("source_usage", {}).get("web", 0) / max(1, su["stats"]["events"]))
    prefer_web = web_share > 0.4

    persona = {
        "user_id": user_id,
        "style": style,
        "llm_persona": llm_persona,
        "domains": domains,
        "prefer_web": prefer_web,
        "recommendations": su.get("recommendations", []),
        "updated_at": int(time.time()),
    }
    db = _load()
    db[user_id] = persona
    _save(db)
    return persona

def update_user_persona(user_id: str, last_user_text: Optional[str] = None) -> Dict[str, Any]:
    p = infer_persona(user_id)
    try:
        if p.get("llm_persona"):
            set_user_persona(user_id, p["llm_persona"])
    except Exception:
        pass
    return p

def get_persona(user_id: str) -> Optional[Dict[str, Any]]:
    return _load().get(user_id)

def propose_personalization(user_id: str) -> Dict[str, Any]:
    p = get_persona(user_id) or infer_persona(user_id)
    tips = list(p.get("recommendations") or [])
    if p.get("prefer_web"):
        tips.append("Aktywować tryb web-first dla Twoich pytań?")
    if p.get("llm_persona"):
        tips.append(f"Ustawić styl: {p['llm_persona']}?")
    return {"user_id": user_id, "tips": tips, "persona": p}

# ====== DATASETY: FT i RLHF ======

def export_ft_dataset(path: str = "/root/mordzix-ai/out/ft_supervised.jsonl", last_n: int = 5000) -> str:
    """
    Supervised FT: bierzemy rekordy z auto-eval, gdzie istnieje improved_answer,
    i tworzymy przykładowy format JSONL (messages -> assistant).
    """
    from .meta_memory import META_PATH
    out = Path(path); out.parent.mkdir(parents=True, exist_ok=True)
    cnt = 0
    with META_PATH.open("r", encoding="utf-8") as fin, out.open("w", encoding="utf-8") as fout:
        for line in fin:
            try:
                j = json.loads(line)
            except Exception:
                continue
            if j.get("kind") != "interaction":
                continue
            extra = j.get("extra") or {}
            improved = extra.get("improved_answer") or None
            # fallback: nie zawsze trzymamy treść pytania – więc dataset przykładowy
            if improved:
                rec = {
                    "messages": [
                        {"role":"user","content":"<user_question_redacted_or_last_user_text>"},
                    ],
                    "completion": improved
                }
                fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                cnt += 1
    return f"{out} ({cnt} examples)"

def export_rlhf_pairs(path: str = "/root/mordzix-ai/out/rlhf_pairs.jsonl", last_n: int = 5000) -> str:
    """
    RLHF/RLAIF preference pairs: z user_feedback – bad_answer vs better_answer.
    """
    from .meta_memory import META_PATH
    out = Path(path); out.parent.mkdir(parents=True, exist_ok=True)
    cnt = 0
    with META_PATH.open("r", encoding="utf-8") as fin, out.open("w", encoding="utf-8") as fout:
        for line in fin:
            try:
                j = json.loads(line)
            except Exception:
                continue
            if j.get("kind") != "user_feedback":
                continue
            pair = {
                "prompt": j.get("question",""),
                "chosen": j.get("better_answer",""),
                "rejected": j.get("bad_answer",""),
                "critique": j.get("critique","")
            }
            fout.write(json.dumps(pair, ensure_ascii=False) + "\n")
            cnt += 1
    return f"{out} ({cnt} pairs)"
# ===== HOTFIX: Safe exporters (create meta file if missing, no crash) =====
from pathlib import Path as _Path
import json as _json, time as _time

def export_ft_dataset(path: str = "/root/mordzix-ai/out/ft_supervised.jsonl", last_n: int = 5000) -> str:
    from .meta_memory import META_PATH  # reuse canonical path
    out = _Path(path); out.parent.mkdir(parents=True, exist_ok=True)
    # ensure meta exists
    if not META_PATH.exists():
        META_PATH.parent.mkdir(parents=True, exist_ok=True)
        META_PATH.touch()
        out.write_text("", encoding="utf-8")
        return f"{out} (0 examples) – initialized empty meta at {META_PATH}"
    cnt = 0
    with META_PATH.open("r", encoding="utf-8") as fin, out.open("w", encoding="utf-8") as fout:
        for line in fin:
            try:
                j = _json.loads(line)
            except Exception:
                continue
            if j.get("kind") != "interaction":
                continue
            improved = (j.get("extra") or {}).get("improved_answer")
            if not improved:
                continue
            rec = {
                "messages": [{"role":"user","content": j.get("question","<redacted>")}],
                "completion": improved
            }
            fout.write(_json.dumps(rec, ensure_ascii=False) + "\n")
            cnt += 1
    return f"{out} ({cnt} examples)"

def export_rlhf_pairs(path: str = "/root/mordzix-ai/out/rlhf_pairs.jsonl", last_n: int = 5000) -> str:
    from .meta_memory import META_PATH
    out = _Path(path); out.parent.mkdir(parents=True, exist_ok=True)
    # ensure meta exists
    if not META_PATH.exists():
        META_PATH.parent.mkdir(parents=True, exist_ok=True)
        META_PATH.touch()
        out.write_text("", encoding="utf-8")
        return f"{out} (0 pairs) – initialized empty meta at {META_PATH}"
    cnt = 0
    with META_PATH.open("r", encoding="utf-8") as fin, out.open("w", encoding="utf-8") as fout:
        for line in fin:
            try:
                j = _json.loads(line)
            except Exception:
                continue
            if j.get("kind") != "user_feedback":
                continue
            pair = {
                "prompt":   j.get("question",""),
                "chosen":   j.get("better_answer",""),
                "rejected": j.get("bad_answer",""),
                "critique": j.get("critique","")
            }
            # odfiltruj puste rekordy
            if not (pair["prompt"] and (pair["chosen"] or pair["rejected"])):
                continue
            fout.write(_json.dumps(pair, ensure_ascii=False) + "\n")
            cnt += 1
    return f"{out} ({cnt} pairs)"
