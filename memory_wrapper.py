# -*- coding: utf-8 -*-
"""
core.memory_wrapper — lekki wrapper pamięci:
- czyta fakty z lokalnej SQLite (MEM_DB)
- wstrzykuje je do system prompt
- odpala LLM (non-stream) i zwraca {'answer': ...}

Bez zależności od nieistniejącego `cognitive_engine_full`.
"""

import os, sqlite3, time, typing as t

MEM_DB = os.environ.get("MEM_DB", "/root/mordzix-ai/mem.db")
MEM_TOPK = int(os.environ.get("MEM_TOPK", "5"))
MEM_TIMEOUT_S = float(os.environ.get("MEM_QUERY_TIMEOUT", "0.150"))

_SQL_MEMORY = """
WITH rows(content) AS (
    SELECT text    FROM facts         WHERE IFNULL(deleted,0)=0
    UNION ALL
    SELECT content FROM memory_nodes  WHERE IFNULL(deleted,0)=0
)
SELECT content
  FROM rows
 WHERE content LIKE ? OR content LIKE ?
 ORDER BY 1 DESC
 LIMIT ?;
"""

def _like_term(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return "%"
    return f"%{s[:200]}%"

def _extract_query(msgs: t.List[dict]) -> str:
    for m in reversed(msgs or []):
        if (m or {}).get("role") == "user":
            return (m.get("content") or "").strip()
    return " ".join((m.get("content") or "") for m in msgs or []).strip()

def _search_memory(q: str, topk: int = MEM_TOPK) -> t.List[str]:
    try:
        con = sqlite3.connect(MEM_DB, timeout=MEM_TIMEOUT_S)
        con.row_factory = lambda cur,row: row[0]
        cur = con.cursor()
        like1 = _like_term(q)
        rows = cur.execute(_SQL_MEMORY, (like1, "%", int(topk))).fetchall()
        con.close()
        return [r for r in rows if r]
    except Exception:
        return []

async def process_message(user_id: t.Optional[str] = None,
                          messages: t.Optional[t.List[dict]] = None,
                          req: t.Any = None) -> dict:
    """
    API zgodne z adapterem w assistant_endpoint:
    zwraca dict z kluczem 'answer'
    """
    try:
        from .llm import chat_completion  # lazy import
    except Exception:
        # bez LLM -> daj bezpieczną odpowiedź
        return {"answer": "System pamięci jest dostępny, ale generowanie odpowiedzi zostało chwilowo wyłączone."}

    msgs = messages or []
    q = _extract_query(msgs)
    facts = _search_memory(q, MEM_TOPK)

    rules = [
        "• Odpowiadaj krótko i trzymaj się FAKTÓW, jeśli są na liście.",
        "• Gdy brak dopasowania — powiedz wprost, że nie masz danych w pamięci.",
        "• Nie wymyślaj szczegółów ani dat.",
    ]
    facts_block = "\n".join(f"- {f}" for f in facts) if facts else "(brak dopasowanych faktów)"
    system_block = (
        "FAKTY Z PAMIĘCI (lokalna baza):\n"
        f"{facts_block}\n\n"
        "ZASADY:\n" + "\n".join(rules)
    )

    # zbuduj wiadomości do LLM
    llm_msgs = [{"role": "system", "content": system_block}]
    for m in msgs:
        role = (m or {}).get("role","user")
        content = (m or {}).get("content","")
        llm_msgs.append({"role": role, "content": content})

    try:
        txt = await chat_completion(llm_msgs, temperature=0.5)
        return {
            "answer": txt or "",
            "metadata": {
                "memory_used": bool(facts),
                "facts_count": len(facts),
                "user_id": user_id or "default",
            },
            "sources": []
        }
    except Exception as e:
        return {"answer": f"Nie udało się wygenerować odpowiedzi ({type(e).__name__})."}
