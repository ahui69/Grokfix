from pathlib import Path
import json, time
from .meta_memory import META_PATH

def auto_eval_and_log(messages, answer: str, sources=None, score: float|None=None) -> dict:
    score = float(score) if score is not None else 0.0
    rec = {
        "kind": "auto_eval",
        "ts": int(time.time()),
        "score": score,
        "answer_len": len(answer or ""),
        "messages": messages or [],
        "sources": sources or [],
    }
    META_PATH.parent.mkdir(parents=True, exist_ok=True)
    with META_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


# --- shim: handle_user_feedback (autododany) ---
from pathlib import Path as _Path
import json as _json, time as _time
_FEEDBACK_PATH = _Path("/root/mordzix-ai/meta_feedback.ndjson")

def handle_user_feedback(payload: dict) -> dict:
    rec = {"ts": _time.time(), "event": "feedback", "payload": payload}
    _FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _FEEDBACK_PATH.open("a", encoding="utf-8") as f:
        f.write(_json.dumps(rec, ensure_ascii=False) + "\n")
    return {"ok": True}
