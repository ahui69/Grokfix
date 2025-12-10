# -*- coding: utf-8 -*-
"""
Cognitive Engine – wersja rozbudowana (append-features, bez TODO).

Funkcje:
- DeepInfra (OpenAI-compatible) chat/completions (stream i non-stream)
- Obsługa function_call / tool_calls (mapa -> lokalne API 127.0.0.1:8080)
- Confidence score, self-critique, meta-refleksje
- A/B warianty (ENV: AB_VARIANTS, AB_DELTA_TEMP)
- Feedback JSONL + asynchroniczny eksport (ELK/S3)
- Memory DB: SQLite (+opcjonalnie Redis) – fakty i persona per sesja
- Chain-of-thought: wymuszenie myślenia wieloetapowego (tylko finalny output)
- LLM-as-Judge: autoocena odpowiedzi drugim przebiegiem
- Dynamiczna persona per sesja
- Embedding cache (per-prompt)
- Prompt compression dla długich wątków

Zależności: standardowe + httpx; Redis (opcjonalnie).
"""

from __future__ import annotations
import os, time, json, re, math, asyncio, uuid, hashlib, random, sqlite3, statistics
from typing import List, Dict, Any, AsyncIterator, Optional, Tuple
import httpx

# ───────────────────────────────────────────────────────────────────────────────
# ENV helpers

def _env_str(k: str, default: str = "") -> str:
    v = os.getenv(k)
    return default if v is None else str(v)

def _env_int(k: str, default: int) -> int:
    try: return int(str(os.getenv(k, default)).strip())
    except Exception: return default

def _env_float(k: str, default: float) -> float:
    try: return float(str(os.getenv(k, default)).strip())
    except Exception: return default

def _env_bool(k: str, default: bool) -> bool:
    v = str(os.getenv(k, "1" if default else "0")).strip().lower()
    return v in ("1","true","yes","y","on")

# ───────────────────────────────────────────────────────────────────────────────
# Konfiguracja

LLM_BASE_URL   = _env_str("LLM_BASE_URL", "https://api.deepinfra.com/v1/openai").rstrip("/")
LLM_API_KEY    = _env_str("LLM_API_KEY") or _env_str("OPENAI_API_KEY")
LLM_MODEL      = _env_str("LLM_MODEL", "meta-llama/Llama-3.3-70B-Instruct")
LLM_FALLBACK   = _env_str("LLM_FALLBACK_MODEL", "")
LLM_TIMEOUT    = _env_int("LLM_HTTP_TIMEOUT_S", _env_int("LLM_TIMEOUT", 120))
LLM_RETRIES    = _env_int("LLM_RETRIES", 3)
LLM_BACKOFF_S  = _env_float("LLM_BACKOFF_S", 2.0)
LLM_MAX_TOKENS = _env_int("LLM_MAX_TOKENS", 1024)
LLM_TEMPERATURE= _env_float("LLM_TEMPERATURE", 0.2)
LLM_TOP_P      = _env_float("LLM_TOP_P", 1.0)
LLM_MAX_CONC   = _env_int("LLM_MAX_CONC", 6)

# self-critique / AB / meta
SELF_CRITIQUE_ENABLED = _env_bool("SELF_CRITIQUE_ENABLED", True)
SELF_CRITIQUE_STYLE   = _env_str("SELF_CRITIQUE_STYLE", "strict")
AB_VARIANTS           = _env_int("AB_VARIANTS", 0)         # 0/2/3
AB_DELTA_TEMP         = _env_float("AB_DELTA_TEMP", 0.25)
META_ASK_ENABLED      = _env_bool("META_ASK_ENABLED", True)

# chain-of-thought (wewnętrzne)
REASONING_ENFORCE     = _env_bool("REASONING_ENFORCE", True)
REASONING_STRICT      = _env_bool("REASONING_STRICT", True)

# personality
PERSONA_MODE          = _env_str("PERSONA_MODE", "").lower()   # default global
PERSONA_CUSTOM        = _env_str("PERSONA_CUSTOM", "")

# feedback
FEEDBACK_PATH         = _env_str("FEEDBACK_PATH", "/root/mordzix-ai/data/feedback.jsonl")
FEEDBACK_SUMMARY      = _env_str("FEEDBACK_SUMMARY", "/root/mordzix-ai/data/feedback_summary.json")
FEEDBACK_EXPORT_ELK   = _env_str("FEEDBACK_EXPORT_ELK", "")
FEEDBACK_EXPORT_S3    = _env_str("FEEDBACK_EXPORT_S3", "")

# auth do lokalnych tooli
LOCAL_AUTH_TOKEN      = _env_str("AUTH_TOKEN")

# replay cache
REPLAY_CACHE_TTL_S    = _env_int("REPLAY_CACHE_TTL_S", 20)

# embeddings
EMBED_URL             = _env_str("LLM_EMBED_URL", LLM_BASE_URL + "/embeddings")
EMBED_MODEL           = _env_str("LLM_EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-mpnet-base-v2")

# Memory DB
FACTS_DB_PATH         = _env_str("MEM_FACTS_DB", "/root/mordzix-ai/data/engine_facts.db")
REDIS_ENABLED         = _env_bool("REDIS_ENABLED", False)
REDIS_URL             = _env_str("REDIS_URL", "")

# prompt compression
PROMPT_COMPRESS       = _env_bool("PROMPT_COMPRESS", True)
PROMPT_MAX_CHARS      = _env_int("PROMPT_MAX_CHARS", 12000)     # jeśli przekroczone → kompresja
PROMPT_TAIL_KEEP      = _env_int("PROMPT_TAIL_KEEP", 12)        # ile ostatnich wiadomości zostawić po kompresji

# guard/system prompt
try:
    from .config import MORDZIX_SYSTEM_PROMPT
except Exception:
    MORDZIX_SYSTEM_PROMPT = ""

# ───────────────────────────────────────────────────────────────────────────────
# Oszczędne logi (bez zależności z helpers)

def _log_info(msg: str):  print(msg)
def _log_warn(msg: str):  print(msg)

# ───────────────────────────────────────────────────────────────────────────────
# Persona registry

_PERSONAS: Dict[str, str] = {
    "mentor": (
        "Jesteś spokojnym, technicznym mentorem. Wyjaśniaj rzeczy klarownie, krok po kroku. "
        "Bez zbędnej emfazy, konkretnie i rzeczowo."
    ),
    "kurwabot": (
        "Masz ostry, bezpośredni styl. Przeklinasz, ale trzymasz się meritum. Priorytetem jest szybkie dojście do rozwiązania."
    ),
    "flirt": (
        "Luźny styl, subtelny humor i kokietowanie bez przekraczania granic."
    ),
}

def _hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def _now_ms() -> int:
    return int(time.time() * 1000)

# ───────────────────────────────────────────────────────────────────────────────
# Memory DB (SQLite + opcjonalnie Redis)

class MemoryDB:
    def __init__(self, path: str, redis_url: str = "", redis_enabled: bool = False) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS session_facts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                fact TEXT,
                ts INTEGER
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS session_meta(
                session_id TEXT PRIMARY KEY,
                persona TEXT DEFAULT '',
                updated INTEGER
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS embeddings(
                hash TEXT PRIMARY KEY,
                text_hash TEXT,
                model TEXT,
                vec TEXT,
                created INTEGER
            )
        """)
        self.conn.commit()
        self.r = None
        if redis_enabled and redis_url:
            try:
                import redis  # opcjonalne
                self.r = redis.from_url(redis_url, decode_responses=True)
            except Exception as e:
                _log_warn(f"[MEM] Redis disabled: {e}")

    # — Fakty —
    def add_fact(self, session_id: str, fact: str) -> None:
        if not (session_id and fact.strip()):
            return
        self.conn.execute("INSERT INTO session_facts(session_id,fact,ts) VALUES(?,?,?)",
                          (session_id, fact.strip(), _now_ms()))
        self.conn.commit()
        if self.r:
            try:
                self.r.lpush(f"facts:{session_id}", fact.strip())
                self.r.ltrim(f"facts:{session_id}", 0, 200)  # max 200
            except Exception: pass

    def get_facts(self, session_id: str, topk: int = 10) -> List[str]:
        out: List[str] = []
        if self.r:
            try:
                out = self.r.lrange(f"facts:{session_id}", 0, topk-1) or []
            except Exception:
                out = []
        if len(out) < topk:
            rows = self.conn.execute(
                "SELECT fact FROM session_facts WHERE session_id=? ORDER BY id DESC LIMIT ?",
                (session_id, topk)
            ).fetchall()
            out.extend([r[0] for r in rows][:max(0, topk - len(out))])
        return out[:topk]

    # — Persona —
    def set_persona(self, session_id: str, persona: str) -> None:
        if not session_id: return
        self.conn.execute(
            "INSERT INTO session_meta(session_id, persona, updated) VALUES(?,?,?) "
            "ON CONFLICT(session_id) DO UPDATE SET persona=excluded.persona, updated=excluded.updated",
            (session_id, persona, _now_ms())
        )
        self.conn.commit()
        if self.r:
            try: self.r.hset(f"meta:{session_id}", "persona", persona)
            except Exception: pass

    def get_persona(self, session_id: str) -> str:
        if self.r:
            try:
                v = self.r.hget(f"meta:{session_id}", "persona")
                if v: return v
            except Exception: pass
        row = self.conn.execute(
            "SELECT persona FROM session_meta WHERE session_id=?",
            (session_id,)
        ).fetchone()
        return (row[0] or "") if row else ""

    # — Embedding cache —
    def get_cached_embedding(self, text_hash: str, model: str) -> Optional[List[float]]:
        row = self.conn.execute(
            "SELECT vec FROM embeddings WHERE text_hash=? AND model=?",
            (text_hash, model)
        ).fetchone()
        if not row: return None
        try:
            return json.loads(row[0])
        except Exception:
            return None

    def put_cached_embedding(self, text_hash: str, model: str, vec: List[float]) -> None:
        try:
            self.conn.execute(
                "INSERT OR REPLACE INTO embeddings(hash,text_hash,model,vec,created) VALUES(?,?,?,?,?)",
                (_hash(text_hash+model), text_hash, model, json.dumps(vec), _now_ms())
            )
            self.conn.commit()
        except Exception:
            pass

MEM = MemoryDB(FACTS_DB_PATH, REDIS_URL, REDIS_ENABLED)

# ───────────────────────────────────────────────────────────────────────────────
# Pomocnicze: confidence, AB, persona

def _confidence_from(answer_len: int, temperature: float, tool_calls: int) -> float:
    base = 0.55 + min(0.25, answer_len / 5000.0)
    base -= min(0.35, temperature * 0.35)
    base += min(0.15, tool_calls * 0.05)
    return max(0.0, min(1.0, base))

def _ab_variants(base_temp: float, n: int) -> List[float]:
    if n <= 1: return [base_temp]
    return [max(0.0, min(1.5, base_temp + (i - (n-1)/2) * AB_DELTA_TEMP)) for i in range(n)]

def _choose_best_variant(candidates: List[Dict[str, Any]]) -> int:
    if not candidates: return 0
    scores = []
    for i, c in enumerate(candidates):
        txt = c.get("answer","") or ""
        l = len(txt)
        conf = c.get("metadata",{}).get("confidence_score", 0.5)
        penalty = 0.0
        if l < 40: penalty += 0.3
        if l > 4000: penalty += 0.2
        score = conf + min(0.3, l/2000.0) - penalty
        scores.append((score,i))
    scores.sort(reverse=True)
    return scores[0][1]

def _persona_text(global_mode: str, session_mode: str, custom: str) -> str:
    mode = (session_mode or global_mode or "").lower().strip()
    if mode == "custom" and custom.strip():
        return custom.strip()
    return _PERSONAS.get(mode, "")

# ───────────────────────────────────────────────────────────────────────────────
# Tool registry → lokalne API 127.0.0.1

_TOOL_MAP: Dict[str, str] = {
    "search_web": "/api/search/hybrid",
    "travel_plan": "/api/travel/trip-plan",
    "auction_analyze": "/api/auction/analyze",
    "programista_exec": "/api/code/exec",
    "nlp_analyze": "/api/nlp/analyze",
}

async def _call_local_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    endpoint = _TOOL_MAP.get(name)
    if not endpoint:
        return {"error": f"unknown_tool:{name}"}
    headers = {"Content-Type":"application/json"}
    if LOCAL_AUTH_TOKEN: headers["Authorization"] = f"Bearer {LOCAL_AUTH_TOKEN}"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"http://127.0.0.1:8080{endpoint}", headers=headers, json=args)
            if r.status_code != 200:
                return {"error": f"http_{r.status_code}", "detail": r.text[:1000]}
            return r.json()
    except Exception as e:
        return {"error": str(e)}

# ───────────────────────────────────────────────────────────────────────────────
# Feedback + eksport

class _FeedbackStore:
    def __init__(self, path: str, summary_path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.path = path
        self.summary_path = summary_path
        self._lock = asyncio.Lock()
        self._export_q: asyncio.Queue = asyncio.Queue()
        self._task: Optional[asyncio.Task] = None
        self._elk = FEEDBACK_EXPORT_ELK
        self._s3  = FEEDBACK_EXPORT_S3

    async def ensure(self):
        if (self._elk or self._s3) and self._task is None:
            self._task = asyncio.create_task(self._worker())

    async def _worker(self):
        async with httpx.AsyncClient(timeout=15) as client:
            while True:
                item = await self._export_q.get()
                try:
                    if self._elk:
                        try: await client.post(self._elk, json=item)
                        except Exception: pass
                    if self._s3:
                        try:
                            payload = (json.dumps(item, ensure_ascii=False) + "\n").encode("utf-8")
                            await client.put(self._s3, content=payload, headers={"Content-Type":"application/x-ndjson"})
                        except Exception: pass
                finally:
                    self._export_q.task_done()

    async def add(self, rec: Dict[str, Any]) -> None:
        await self.ensure()
        line = json.dumps(rec, ensure_ascii=False)
        async with self._lock:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        try: await self._update_summary(rec)
        except Exception: pass
        try:
            if self._elk or self._s3:
                await self._export_q.put(rec)
        except Exception: pass

    async def _update_summary(self, rec: Dict[str, Any]) -> None:
        try:
            try:
                with open(self.summary_path, "r", encoding="utf-8") as f:
                    state = json.load(f)
            except Exception:
                state = {}
            k = json.dumps({
                "model": rec.get("model"),
                "temperature": rec.get("temperature"),
                "top_p": rec.get("top_p"),
                "tools": tuple(sorted(rec.get("tools_used", [])))
            }, sort_keys=True)
            obj = state.get(k) or {"n":0,"score":0.0}
            w   = float(rec.get("user_weight", 1.0))
            sc  = float(rec.get("score", 0.0))  # -1..+1
            obj["score"] = (obj["score"]*obj["n"] + sc*w) / max(1.0, obj["n"]+w)
            obj["n"] += w
            state[k] = obj
            with open(self.summary_path, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

_FEEDBACK = _FeedbackStore(FEEDBACK_PATH, FEEDBACK_SUMMARY)

def _user_weight(user_id: str) -> float:
    try:
        if not os.path.exists(FEEDBACK_PATH): return 1.0
        cnt = 0
        with open(FEEDBACK_PATH, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    j = json.loads(line)
                    if j.get("user_id") == user_id: cnt += 1
                except Exception: pass
        return min(3.0, 1.0 + math.log10(1 + cnt))
    except Exception:
        return 1.0

async def record_feedback(user_id: str, model: str, temperature: float, top_p: float,
                          tools_used: List[str], score: int, latency_ms: int,
                          answer_len: int, session_id: Optional[str] = None,
                          judge_score: Optional[float] = None, judge_reason: str = "") -> None:
    rec = {
        "ts": _now_ms(),
        "user_id": user_id,
        "session_id": session_id,
        "model": model,
        "temperature": temperature,
        "top_p": top_p,
        "tools_used": tools_used,
        "score": score,
        "latency_ms": latency_ms,
        "answer_len": answer_len,
        "judge_score": judge_score,
        "judge_reason": judge_reason[:400]
    }
    rec["user_weight"] = _user_weight(user_id)
    await _FEEDBACK.add(rec)

# ───────────────────────────────────────────────────────────────────────────────
# Pomocnicze dla LLM

def _get_session_id_from_req(req) -> str:
    try:
        sid = req.headers.get("X-Session-Id") or ""
        if not sid:
            try: sid = req.query_params.get("session_id") or ""
            except Exception: sid = ""
        return sid or "default"
    except Exception:
        return "default"

def _messages_len_chars(messages: List[Dict[str,Any]]) -> int:
    s = 0
    for m in messages:
        c = m.get("content")
        if c: s += len(str(c))
    return s

def _compress_messages(messages: List[Dict[str,Any]], tail_keep: int) -> List[Dict[str,Any]]:
    if len(messages) <= tail_keep: return messages
    head = messages[:-tail_keep]
    tail = messages[-tail_keep:]
    # naiwny skrót głowy: wyciągamy pierwsze zdania
    head_text = []
    for m in head:
        txt = (m.get("content") or "").strip()
        if not txt: continue
        sentence = txt.split(".")[0]
        head_text.append(f"{m.get('role','user')}: {sentence.strip()[:180]}.")
    summary = "Skrót wcześniejszej rozmowy:\n- " + "\n- ".join(head_text[:20])
    return [{"role":"system","content":summary}] + tail

def _extract_facts_heuristic(answer: str) -> List[str]:
    lines = [l.strip("•*- ").strip() for l in answer.splitlines() if l.strip()]
    picks = []
    for l in lines:
        if len(l) < 25: continue
        if any(ch.isdigit() for ch in l) or (" jest " in l.lower()) or (":" in l and len(l) < 200):
            picks.append(l[:300])
        if len(picks) >= 6: break
    if not picks and len(answer) > 80:
        s = re.split(r"[.!?]\s+", answer)
        picks = [x.strip()[:300] for x in s if len(x) > 40][:5]
    return picks[:6]

def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a)!=len(b): return 0.0
    sa = sum(x*x for x in a); sb = sum(x*x for x in b)
    if sa<=0 or sb<=0: return 0.0
    dot = sum(x*y for x,y in zip(a,b))
    return max(0.0, min(1.0, dot / math.sqrt(sa*sb)))

# ───────────────────────────────────────────────────────────────────────────────
# Klasa silnika

class CognitiveEngine:

    def __init__(self) -> None:
        self.base_url   = LLM_BASE_URL
        self.api_key    = LLM_API_KEY
        self.model      = LLM_MODEL
        self.fallback   = LLM_FALLBACK
        self.timeout    = LLM_TIMEOUT
        self.temperature= LLM_TEMPERATURE
        self.top_p      = LLM_TOP_P
        self.max_tokens = LLM_MAX_TOKENS
        self.sem        = asyncio.Semaphore(LLM_MAX_CONC)
        self._replay_cache: Dict[str, float] = {}

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _headers(self) -> Dict[str,str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type":"application/json"}

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=self.timeout, base_url=self.base_url)

    def _system_prompt(self, session_persona: str) -> str:
        persona = _persona_text(PERSONA_MODE, session_persona, PERSONA_CUSTOM)
        guard = (
            "Jeśli dołączone są Aktualne Dane z Internetu – opieraj się wyłącznie na nich. "
            "Jeśli brakuje informacji, powiedz to wprost. Nie wymyślaj dat, wyników ani cen."
        )
        core = "\n\n".join([x for x in [MORDZIX_SYSTEM_PROMPT.strip(), guard, ("PERSONALITY:\n"+persona if persona else "")] if x])
        return core

    def _messages_with_system(self, messages: List[Dict[str,Any]], session_persona: str) -> List[Dict[str,str]]:
        out: List[Dict[str,str]] = []
        sp = self._system_prompt(session_persona)
        if sp:
            out.append({"role":"system","content": sp})
        out.extend({"role": m.get("role"), "content": str(m.get("content"))} for m in messages if m.get("role") and m.get("content") is not None)
        return out

    # ── API: non-stream ────────────────────────────────────────────────────────

    async def process_message(self, user_id: str, messages: List[Dict[str, Any]], req) -> Dict[str, Any]:
        t0 = time.time()
        meta: Dict[str, Any] = {
            "source": "cognitive_engine_full",
            "model": self.model,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
        }
        if not self.api_key:
            return {"answer":"[LLM] Brak LLM_API_KEY/OPENAI_API_KEY", "sources": [], "metadata":{**meta, "error":"no_api_key"}}

        session_id = _get_session_id_from_req(req)

        # persona switch (runtime) – frazy typu: #persona mentor / tryb mentor / styl flirt / kurwabot
        try:
            last_user_txt = ""
            for m in reversed(messages):
                if (m.get("role") or "") == "user":
                    last_user_txt = m.get("content") or ""
                    break
            m = re.search(r"(?:#persona|tryb|styl)\s*:\s*(mentor|kurwabot|flirt|custom)", last_user_txt, re.I)
            if m:
                mode = m.group(1).lower()
                MEM.set_persona(session_id, mode)
        except Exception: pass
        session_persona = MEM.get_persona(session_id)

        # prompt compression
        msgs_in = messages
        if PROMPT_COMPRESS and _messages_len_chars(messages) > PROMPT_MAX_CHARS:
            msgs_in = _compress_messages(messages, PROMPT_TAIL_KEEP)
            meta["compressed"] = True
        else:
            meta["compressed"] = False

        # chain-of-thought (wymuszenie myślenia, ale finalny output)
        cot_prefix = ""
        cot_marker = "###ANSWER:"
        if REASONING_ENFORCE:
            cot_prefix = (
                "Myśl krok po kroku wewnętrznie. Na koniec zwróć wyłącznie linię:\n"
                f"{cot_marker} <ostateczna zwięzła odpowiedź>\n"
            )
            # wstrzykujemy do ostatniej wiadomości usera
            for i in range(len(msgs_in)-1, -1, -1):
                if msgs_in[i].get("role") == "user":
                    msgs_in = msgs_in.copy()
                    msgs_in[i] = {"role":"user","content": cot_prefix + "\n" + str(msgs_in[i].get("content") or "")}
                    break

        # AB warianty
        temps = _ab_variants(self.temperature, AB_VARIANTS) if AB_VARIANTS >= 2 else [self.temperature]
        candidates: List[Dict[str, Any]] = []

        async with self.sem:
            for idx, temp in enumerate(temps):
                try:
                    cand = await self._one_completion_with_tools(
                        messages=msgs_in, temperature=temp, top_p=self.top_p, session_persona=session_persona,
                        cot_marker=cot_marker if REASONING_ENFORCE else None
                    )
                    cand["metadata"]["variant_index"] = idx
                    candidates.append(cand)
                except Exception as e:
                    candidates.append({"answer": f"[variant_error] {e}", "sources": [],
                                       "metadata": {**meta, "variant_index": idx, "error": str(e)}})

        pick = _choose_best_variant(candidates) if len(candidates) > 1 else 0
        best = candidates[pick]
        meta.update(best.get("metadata", {}))

        # LLM-as-Judge
        if SELF_CRITIQUE_ENABLED:
            try:
                jscore, jreason = await self._judge_answer(best.get("answer",""))
                meta["judge_score"]  = jscore
                meta["judge_reason"] = jreason
            except Exception as e:
                meta["judge_error"] = str(e)

        # zapisz fakty per sesja (heur.)
        try:
            for f in _extract_facts_heuristic(best.get("answer","")):
                MEM.add_fact(session_id, f)
            meta["facts_saved"] = True
        except Exception:
            meta["facts_saved"] = False

        # dołącz kilka ostatnich faktów do metadanych (diagnostyka)
        try:
            meta["facts_preview"] = MEM.get_facts(session_id, topk=5)
        except Exception:
            meta["facts_preview"] = []

        meta["latency_ms"] = int((time.time()-t0)*1000)
        best["metadata"] = meta
        return best

    # ── API: stream ────────────────────────────────────────────────────────────

    async def stream_message(self, user_id: str, messages: List[Dict[str, Any]]) -> AsyncIterator[Dict[str, Any]]:
        t0 = time.time()
        if not self.api_key:
            yield {"type":"error","message":"no_api_key"}; return

        # jedna runda narzędzi bez streamu
        pre = await self._one_completion_with_tools(messages, self.temperature, self.top_p, session_persona="", cot_marker=None)
        answer_acc = pre.get("answer","")
        tool_meta  = pre.get("metadata",{})
        yield {"type":"start"}

        follow_msgs = messages + ([{"role":"assistant","content":answer_acc}] if answer_acc else [])
        try:
            async for part in self._stream_chat(follow_msgs, self.temperature, self.top_p, session_persona=""):
                if part["type"] == "chunk":
                    yield part; answer_acc += part.get("content","")
                elif part["type"] == "error":
                    yield part; return
        except Exception as e:
            yield {"type":"error","message":str(e)}; return

        conf = _confidence_from(len(answer_acc), self.temperature, int(tool_meta.get("tool_calls_count", 0)))
        meta = {**tool_meta, "confidence_score": round(conf,3), "latency_ms": int((time.time()-t0)*1000), "streaming": True}
        yield {"type":"complete","answer":answer_acc,"metadata":meta}

    # ── wnętrze: jedna kompletacja + tools ─────────────────────────────────────

    async def _one_completion_with_tools(self, messages: List[Dict[str, Any]],
                                         temperature: float, top_p: float,
                                         session_persona: str, cot_marker: Optional[str]) -> Dict[str, Any]:
        t0 = time.time()
        sys_msgs = self._messages_with_system(messages, session_persona)
        payload = {
            "model": self.model,
            "messages": sys_msgs,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": self.max_tokens,
            "stream": False
        }
        # retry
        for attempt in range(1, LLM_RETRIES+1):
            try:
                async with self._client() as client:
                    r = await client.post("/chat/completions", headers=self._headers(), json=payload)
                    r.raise_for_status()
                    data = r.json(); break
            except Exception:
                if attempt >= LLM_RETRIES: raise
                await asyncio.sleep(LLM_BACKOFF_S * attempt)

        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message", {}) or {}
        raw_answer = msg.get("content","") or ""
        tool_calls = msg.get("tool_calls") or []
        function_call = msg.get("function_call") or None

        # odetnij chain-of-thought (zachowaj tylko final)
        answer = raw_answer
        if cot_marker:
            m = re.search(rf"{re.escape(cot_marker)}\s*(.*)$", raw_answer, re.S)
            if m: answer = m.group(1).strip()

        used_tools: List[str] = []

        # function_call
        if function_call and isinstance(function_call, dict):
            name = function_call.get("name") or "call_tool"
            try: args = json.loads(function_call.get("arguments") or "{}")
            except Exception: args = {}
            res = await _call_local_tool(name, args); used_tools.append(name)
            sys_msgs += [
                {"role":"assistant","content":raw_answer, "tool_calls":[{"id":"fc1","type":"function","function":{"name":name,"arguments":json.dumps(args)}}]},
                {"role":"tool","content":json.dumps(res, ensure_ascii=False), "tool_call_id":"fc1"},
            ]
            async with self._client() as client:
                r2 = await client.post("/chat/completions", headers=self._headers(), json={
                    "model": self.model, "messages": sys_msgs,
                    "temperature": temperature, "top_p": top_p,
                    "max_tokens": self.max_tokens, "stream": False
                })
                r2.raise_for_status()
                data2 = r2.json()
            choice2 = (data2.get("choices") or [{}])[0]
            answer = (choice2.get("message") or {}).get("content","") or answer

        # tool_calls[]
        elif tool_calls and isinstance(tool_calls, list):
            for i, tc in enumerate(tool_calls):
                fn = ((tc or {}).get("function") or {})
                name = fn.get("name") or f"tool_{i}"
                try: args = json.loads(fn.get("arguments") or "{}")
                except Exception: args = {}
                res = await _call_local_tool(name, args); used_tools.append(name)
                sys_msgs += [
                    {"role":"assistant","content": raw_answer if i==0 else "", "tool_calls":[{"id":f"tc{i}","type":"function","function":{"name":name,"arguments":json.dumps(args)}}]},
                    {"role":"tool","content":json.dumps(res, ensure_ascii=False), "tool_call_id":f"tc{i}"},
                ]
            async with self._client() as client:
                r3 = await client.post("/chat/completions", headers=self._headers(), json={
                    "model": self.model, "messages": sys_msgs,
                    "temperature": temperature, "top_p": top_p,
                    "max_tokens": self.max_tokens, "stream": False
                })
                r3.raise_for_status()
                data3 = r3.json()
            choice3 = (data3.get("choices") or [{}])[0]
            answer = (choice3.get("message") or {}).get("content","") or answer

        conf = _confidence_from(len(answer), temperature, len(used_tools))
        meta = {
            "model": self.model,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": self.max_tokens,
            "tool_calls_count": len(used_tools) or len(tool_calls) or (1 if function_call else 0),
            "tools_used": used_tools,
            "raw_finish_reason": choice.get("finish_reason"),
            "processing_time": time.time()-t0,
            "confidence_score": round(conf,3),
        }
        return {"answer": answer or "(pusta odpowiedź modelu)", "sources": [], "metadata": meta}

    # ── streaming po /chat/completions ─────────────────────────────────────────

    async def _stream_chat(self, messages: List[Dict[str, Any]], temperature: float, top_p: float, session_persona: str) -> AsyncIterator[Dict[str, Any]]:
        sys_msgs = self._messages_with_system(messages, session_persona)
        payload = {"model": self.model, "messages": sys_msgs, "temperature": temperature, "top_p": top_p,
                   "max_tokens": self.max_tokens, "stream": True}
        try:
            async with self._client() as client:
                async with client.stream("POST", "/chat/completions", headers=self._headers(), json=payload) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line: continue
                        if line.startswith("data: "):
                            chunk = line[len("data: "):].strip()
                            if chunk == "[DONE]": break
                            try: j = json.loads(chunk)
                            except Exception: continue
                            delta = (((j.get("choices") or [{}])[0]).get("delta") or {})
                            if "content" in delta and delta["content"]:
                                yield {"type":"chunk","content": delta["content"]}
                            # function_call/tool_calls w streamie – tylko ignoruj w SSE (narzędzia obsługujemy w rundzie pre)
        except httpx.HTTPStatusError as e:
            yield {"type":"error","message": f"http_{e.response.status_code}: {e.response.text[:400]}"}
        except Exception as e:
            yield {"type":"error","message": str(e)}

    # ── LLM-as-Judge (krótka ocena) ────────────────────────────────────────────

    async def _judge_answer(self, answer: str) -> Tuple[Optional[float], str]:
        if not answer.strip():
            return None, ""
        prompt = (
            "Oceń odpowiedź w skali 0..1 (float) pod kątem: trafność (accuracy), jasność (clarity), "
            "zwięzłość (brevity). Zwróć JSON {\"score\":float,\"reason\":\"...\"}. Krótko."
        )
        msgs = [{"role":"system","content":"You are a strict judge."},
                {"role":"user","content": prompt+"\n\nODPOWIEDŹ:\n"+answer[:4000]}]
        async with httpx.AsyncClient(timeout=30, base_url=self.base_url) as client:
            r = await client.post("/chat/completions", headers=self._headers(), json={
                "model": self.model, "messages": msgs, "temperature": 0.0, "top_p": 1.0, "max_tokens": 180, "stream": False
            })
            r.raise_for_status()
            data = r.json()
        txt = (((data.get("choices") or [{}])[0]).get("message") or {}).get("content","{}")
        try:
            j = json.loads(re.search(r"\{.*\}", txt, re.S).group(0))
            return float(j.get("score", None)), str(j.get("reason",""))[:400]
        except Exception:
            return None, txt[:200]

# ───────────────────────────────────────────────────────────────────────────────
# Embedding cache (per-prompt)

async def get_embedding(text: str) -> Optional[List[float]]:
    if not text.strip(): return None
    th = _hash(text)
    cached = MEM.get_cached_embedding(th, EMBED_MODEL)
    if cached: return cached
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(EMBED_URL, headers={"Authorization": f"Bearer {LLM_API_KEY}", "Content-Type":"application/json"},
                                  json={"model": EMBED_MODEL, "input": text})
            r.raise_for_status()
            data = r.json()
        vec = ((data.get("data") or [{}])[0]).get("embedding")
        if isinstance(vec, list) and vec:
            MEM.put_cached_embedding(th, EMBED_MODEL, vec)
            return vec
    except Exception:
        return None
    return None

# ───────────────────────────────────────────────────────────────────────────────
# Instancja eksportowana

cognitive_engine = CognitiveEngine()
