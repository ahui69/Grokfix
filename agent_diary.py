# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
import json, time, re
from typing import List, Dict, Any, Optional, Tuple

DIARY_PATH = Path("/root/mordzix-ai/out/agent_diary.jsonl")
DIARY_PATH.parent.mkdir(parents=True, exist_ok=True)

def _append(rec: dict) -> str:
    DIARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DIARY_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return str(DIARY_PATH)

def extract_topics(text: str, topk: int = 5) -> List[str]:
    text = (text or "").lower()
    words = re.findall(r"[a-ząćęłńóśżź0-9]{3,}", text)
    stop = set("oraz albo orazże orazże jest są było była były był być mieć robić robiłem robiła co jak gdzie kiedy dlaczego oraz czy tego tegoż że aby więc oraz też teżże orazże oraz".split())
    cnt = {}
    for w in words:
        if w in stop: continue
        cnt[w] = cnt.get(w, 0) + 1
    return [w for w,_ in sorted(cnt.items(), key=lambda x:(-x[1], x[0]))[:topk]]

def write_entry(
    user_id: str,
    session_id: Optional[str],
    question: str,
    answer: str,
    critique: Optional[str],
    score: Optional[float],
    lessons: Optional[List[str]] = None,
    actions: Optional[List[str]] = None,
    topics_hint: Optional[List[str]] = None,
) -> str:
    rec = {
        "kind": "agent_diary",
        "ts": int(time.time()),
        "user_id": user_id,
        "session_id": session_id,
        "topics": topics_hint or extract_topics(question),
        "question": question,
        "answer_head": (answer or "")[:400],
        "critique": critique or "",
        "score": None if score is None else float(score),
        "lessons": lessons or [],
        "actions": actions or [],
    }
    return _append(rec)

def last_entries(user_id: str, n: int = 20) -> List[Dict[str,Any]]:
    out: List[Dict[str,Any]] = []
    if not DIARY_PATH.exists(): return out
    with DIARY_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                j = json.loads(line)
            except Exception:
                continue
            if j.get("kind") != "agent_diary": continue
            if user_id and j.get("user_id") != user_id: continue
            out.append(j)
    return out[-n:]

def summarize_user_diary(user_id: str, n: int = 200) -> Dict[str,Any]:
    rows = last_entries(user_id, n)
    topics = {}
    scores = []
    lessons: List[str] = []
    for r in rows:
        for t in r.get("topics", []):
            topics[t] = topics.get(t, 0) + 1
        if isinstance(r.get("score"), (int,float)): scores.append(float(r["score"]))
        lessons.extend(r.get("lessons", []))
    top_topics = [k for k,_ in sorted(topics.items(), key=lambda x:(-x[1], x[0]))[:8]]
    avg = sum(scores)/len(scores) if scores else None
    return {"count": len(rows), "top_topics": top_topics, "avg_score": avg, "lessons": lessons[-8:]}
