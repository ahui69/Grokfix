# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
import json, time
from typing import Dict, Any, Optional, List

META_PATH = Path("/root/mordzix-ai/out/memory_meta.jsonl")
PREFS_PATH = Path("/root/mordzix-ai/out/adaptive_prefs.json")

def _append_meta(j: dict):
    META_PATH.parent.mkdir(parents=True, exist_ok=True)
    with META_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(j, ensure_ascii=False) + "\n")

def _load_prefs() -> Dict[str,Any]:
    if PREFS_PATH.exists():
        try: return json.loads(PREFS_PATH.read_text(encoding="utf-8"))
        except: return {}
    return {}

def _save_prefs(obj: Dict[str,Any]):
    PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PREFS_PATH.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def _recent_scores(user_id: str, last_n: int = 20) -> List[float]:
    out = []
    if not META_PATH.exists(): return out
    with META_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            try: j = json.loads(line)
            except: continue
            if j.get("kind")!="eval": continue
            if j.get("user_id")!=user_id: continue
            sc = j.get("score")
            if isinstance(sc,(int,float)): out.append(float(sc))
    return out[-last_n:]

def register_eval_signal(user_id: str, score: float) -> Dict[str,Any]:
    now = int(time.time())
    _append_meta({"kind":"eval","ts":now,"user_id":user_id,"score":float(score)})
    prefs = _load_prefs()
    row = prefs.get(user_id, {"force_web": False, "temperature": 0.7, "persona": None, "ts": now})
    # Prosta polityka:
    scores = _recent_scores(user_id, 10)
    avg = sum(scores)/len(scores) if scores else score
    if avg < 0.55:
        row["force_web"] = True
        row["temperature"] = 0.3
        row["persona"] = "mentor"
    elif avg < 0.70:
        row["force_web"] = True
        row["temperature"] = 0.5
        row["persona"] = row.get("persona") or "mentor"
    else:
        row["force_web"] = False
        row["temperature"] = 0.7
        # persona zostaw jak była (użytkownik może mieć preferencje)
    row["ts"] = now
    prefs[user_id] = row
    _save_prefs(prefs)
    return {"avg_score": avg, **row}

def get_adaptive_prefs(user_id: str) -> Dict[str,Any]:
    prefs = _load_prefs().get(user_id) or {}
    # domyślne wartości:
    return {
        "force_web": bool(prefs.get("force_web", False)),
        "temperature": float(prefs.get("temperature", 0.7)),
        "persona": prefs.get("persona")
    }
