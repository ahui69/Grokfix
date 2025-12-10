#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import os, json, time, statistics
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from collections import Counter, defaultdict

from .meta_memory import META_PATH, summarize_user

OUT_PATH = Path(os.getenv("AGENT_SELF_MODEL_PATH", "/root/mordzix-ai/out/agent_self_model.json"))
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

def _read_all(last_n: int = 40000) -> List[Dict[str, Any]]:
    if not META_PATH.exists():
        return []
    rows: List[Dict[str, Any]] = []
    with META_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows[-last_n:]

def _agg_stats(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    intents = defaultdict(lambda: {"cnt":0,"scores":[],"hall":0,"timeout":0,"err":0,"web":0,"dur":[],"len":[]})
    topics = Counter()
    hard = Counter()

    for r in rows:
        k = r.get("kind")
        if k == "interaction":
            intent = r.get("intent","chat")
            intents[intent]["cnt"] += 1
            sc = r.get("eval_score")
            if isinstance(sc,(int,float)): intents[intent]["scores"].append(float(sc))
            if (r.get("eval_flags") or {}).get("hallucination"): intents[intent]["hall"] += 1
            if r.get("timed_out"): intents[intent]["timeout"] += 1
            if r.get("error"): intents[intent]["err"] += 1
            if r.get("web_used"): intents[intent]["web"] += 1
            if isinstance(r.get("duration_ms"), (int, float)): intents[intent]["dur"].append(int(r["duration_ms"]))
            intents[intent]["len"].append(int(r.get("answer_len",0)))
        elif k == "session_retrospect":
            for t in (r.get("main_topics") or []):
                topics[t.lower()] += 1
            for h in (r.get("hard_points") or []):
                hard[h.strip().lower()] += 1

    by_intent = {}
    for name, v in intents.items():
        cnt = max(1, v["cnt"])
        avg = statistics.fmean(v["scores"]) if v["scores"] else None
        by_intent[name] = {
            "count": v["cnt"],
            "avg_score": None if avg is None else round(avg,3),
            "hallucination_rate": round(v["hall"]/cnt,3),
            "timeout_rate": round(v["timeout"]/cnt,3),
            "error_rate": round(v["err"]/cnt,3),
            "web_share": round(v["web"]/cnt,3),
            "p50_latency_ms": int(statistics.median(v["dur"])) if v["dur"] else None,
            "p90_latency_ms": int(statistics.quantiles(v["dur"], n=10)[-1]) if len(v["dur"])>=10 else None,
            "answer_len_p50": int(statistics.median(v["len"])) if v["len"] else None,
        }

    top_topics = [t for t,_ in topics.most_common(30)]
    hard_snippets = [h for h,_ in hard.most_common(30)]

    return {"by_intent": by_intent, "top_topics": top_topics, "hard_points": hard_snippets}

def _recommend_global(stats: Dict[str, Any]) -> Dict[str, Any]:
    web_first = set()
    temp_adj: Dict[str,float] = {}
    max_tokens = {}

    for intent, v in stats["by_intent"].items():
        hall = v["hallucination_rate"] or 0.0
        score = v["avg_score"] if v["avg_score"] is not None else 0.8
        if hall >= 0.12 or score < 0.7:
            web_first.add(intent)
        # temperatura: niższa przy halucynacjach
        base = 0.7
        if hall >= 0.15: t = 0.35
        elif hall >= 0.10: t = 0.45
        elif score < 0.7: t = 0.5
        else: t = base
        temp_adj[intent] = round(t,2)

        # max_tokens heurystycznie po długości
        l50 = v.get("answer_len_p50") or 400
        max_tokens[intent] = int(min(2000, max(400, l50*2)))

    return {
        "web_first_intents": sorted(web_first),
        "suggested_temperature": temp_adj,
        "suggested_max_tokens": max_tokens,
    }

def rebuild_global(last_n: int = 40000) -> Dict[str, Any]:
    rows = _read_all(last_n)
    stats = _agg_stats(rows)
    recs = _recommend_global(stats)
    model = {
        "generated_at": int(time.time()),
        "window": last_n,
        "stats": stats,
        "recommendations": recs,
    }
    OUT_PATH.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    return model

def load_profile() -> Dict[str, Any]:
    if OUT_PATH.exists():
        try:
            return json.loads(OUT_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return rebuild_global()

def personal_rules_for_user(user_id: str, last_n: int = 2000) -> Dict[str, Any]:
    """Łączy globalny model z per-user podsumowaniem i zwraca reguły runtime."""
    profile = load_profile()
    su = summarize_user(user_id, last_n=last_n)
    recs = profile.get("recommendations", {})

    # web-first jeśli user często potrzebuje bieżących danych lub ma wysoki hallu-rate
    web_first = set(recs.get("web_first_intents", []))
    if (su.get("source_usage", {}).get("web", 0) / max(1, su["stats"]["events"])) > 0.4:
        web_first.add("chat")

    # temperatura: bierz z intentu 'chat' jako domyślną
    temp = recs.get("suggested_temperature", {}).get("chat", 0.7)

    # tokeny – domyśl po intencie chat
    max_tok = recs.get("suggested_max_tokens", {}).get("chat", 1200)

    return {
        "user_id": user_id,
        "web_first": sorted(web_first),
        "temperature": temp,
        "max_tokens": max_tok,
        "notes": su.get("recommendations", []),
    }

def advise_params_for_request(user_id: str, intent: str = "chat", text: str = "") -> Dict[str, Any]:
    """Szybka porada parametrów wywołania LLM pod aktualne zapytanie."""
    profile = load_profile()
    recs = profile.get("recommendations", {})
    temp = recs.get("suggested_temperature", {}).get(intent, 0.7)
    max_tok = recs.get("suggested_max_tokens", {}).get(intent, 1200)
    web_first = intent in set(recs.get("web_first_intents", []))
    return {"temperature": temp, "max_tokens": max_tok, "force_web": web_first}
