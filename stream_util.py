# -*- coding: utf-8 -*-
"""
stream_util.py — rozbudowany helper do streamowania z awaryjnym fallbackiem.

ZACHOWANE NAZWY (kompatybilność):
- stream_first_or_fallback_iter(...)
- _stream_first_or_fallback(...), alias: stream_first_or_fallback

Co dochodzi:
- Konfig z ENV (timeouty, cisza, keepalive token, limity, koszty)
- Keepalive (domyślnie NUL), częściowe flush’e, twardy limit czasu
- Mini circuit-breaker (okno, próg, czas otwarcia)
- Backoff przy fallbacku (mały jitter)
- Limit równoległości per event-loop (STREAM_MAX_CONCURRENCY)
- Hooki: on_start, on_token, on_complete, on_error
- Metryki + estymacja kosztu (LLM_COST_PROMPT_PER_1K / LLM_COST_COMP_PER_1K)
- SSE adapter: sse_stream_adapter(...) (opcjonalne)
"""

from __future__ import annotations
from typing import AsyncIterator, List, Optional, Dict, Any, Callable
from dataclasses import dataclass
import asyncio, os, time, contextlib, math, json, random

# --- logging awaryjny (bez twardych zależności) ---
try:
    from .helpers import log_info, log_warning
except Exception:
    def log_info(msg: str): print("[INFO]", msg)
    def log_warning(msg: str): print("[WARN]", msg)

# ==============================
#       Circuit breaker
# ==============================
_CB_STATE: Dict[str, Dict[str, Any]] = {}  # {key: {fails:int, last:float, opened_until:float}}

def _cb_is_open(key: str) -> bool:
    st = _CB_STATE.get(key)
    return bool(st and st.get("opened_until", 0.0) > time.time())

def _cb_fail(key: str, window: float, threshold: int, open_sec: float):
    now = time.time()
    st = _CB_STATE.setdefault(key, {"fails": 0, "last": now, "opened_until": 0.0})
    if now - st["last"] > window:
        st["fails"] = 0
    st["last"] = now
    st["fails"] += 1
    if st["fails"] >= threshold:
        st["opened_until"] = now + open_sec
        log_warning(f"[STREAM_UTIL][CB] OPEN key={key} for {open_sec:.1f}s (fails={st['fails']})")

def _cb_success(key: str):
    if key in _CB_STATE:
        _CB_STATE[key]["fails"] = 0
        _CB_STATE[key]["opened_until"] = 0.0

# ==============================
#            Config
# ==============================
@dataclass
class StreamConfig:
    first_token_timeout: float = 1.8       # s – czekanie na pierwszy token
    per_token_timeout: float = 1.2         # s – czekanie na kolejne tokeny
    max_silence: float = 8.0               # s – bez tokenów => kończymy
    sse_keepalive_interval: float = 10.0   # s – jak długo bez chunków => keepalive
    hard_time_limit: float = 120.0         # s – twardy limit na cały stream
    cb_key: str = "llm_stream"             # klucz CB (możesz podać np. nazwę modelu)
    cb_open_sec: float = 10.0
    cb_window: float = 30.0
    cb_threshold: int = 3
    # koszt
    cost_prompt_per_1k: Optional[float] = None
    cost_comp_per_1k: Optional[float] = None
    # keepalive token (domyślnie NUL, łatwy do odfiltrowania)
    keepalive_token: str = "\u0000"
    # częściowe flush’e (dla SSE adaptera)
    partial_flush_chars: int = 0           # 0 = wyłączone, >0 = buforuj do progu
    # wykrywanie „error tokenów”
    error_prefixes: tuple[str, ...] = ("[ERROR]", "ERROR:", "[ERR]")
    # nazwa trybu: "auto" | "force_stream" | "force_fallback"
    collect_mode: str = "auto"

    # hooki (opcjonalne)
    on_start: Optional[Callable[[Dict[str, Any]], None]] = None
    on_token: Optional[Callable[[str], None]] = None
    on_complete: Optional[Callable[[str, Dict[str, Any]], None]] = None
    on_error: Optional[Callable[[Exception], None]] = None

    @classmethod
    def from_env(cls) -> "StreamConfig":
        def _envfloat(name: str, default: Optional[float]) -> Optional[float]:
            v = os.getenv(name, "")
            try:
                return float(v) if v else default
            except Exception:
                return default
        def _envint(name: str, default: int) -> int:
            try:
                return int(os.getenv(name, "") or default)
            except Exception:
                return default

        keepalive = os.getenv("STREAM_KEEPALIVE_TOKEN", "\u0000")
        mode = os.getenv("STREAM_COLLECT_MODE", "auto")

        return cls(
            first_token_timeout=_envfloat("STREAM_FIRST_TOKEN_TIMEOUT", 1.8) or 1.8,
            per_token_timeout=_envfloat("STREAM_PER_TOKEN_TIMEOUT", 1.2) or 1.2,
            max_silence=_envfloat("STREAM_MAX_SILENCE", 8.0) or 8.0,
            sse_keepalive_interval=_envfloat("STREAM_KEEPALIVE_SEC", 10.0) or 10.0,
            hard_time_limit=_envfloat("STREAM_HARD_LIMIT_SEC", 120.0) or 120.0,
            cb_open_sec=_envfloat("STREAM_CB_OPEN_SEC", 10.0) or 10.0,
            cb_window=_envfloat("STREAM_CB_WINDOW_SEC", 30.0) or 30.0,
            cb_threshold=_envint("STREAM_CB_THRESHOLD", 3),
            cost_prompt_per_1k=_envfloat("LLM_COST_PROMPT_PER_1K", None),
            cost_comp_per_1k=_envfloat("LLM_COST_COMP_PER_1K", None),
            keepalive_token=keepalive if keepalive else "\u0000",
            partial_flush_chars=_envint("STREAM_PARTIAL_FLUSH_CHARS", 0),
            collect_mode=mode if mode in ("auto", "force_stream", "force_fallback") else "auto",
        )

# ==============================
#        Concurrency guard
# ==============================
_LOOP_SEMS: Dict[int, asyncio.Semaphore] = {}

def _get_sem() -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    lid = id(loop)
    sem = _LOOP_SEMS.get(lid)
    if sem is None:
        max_c = 8
        try:
            max_c = int(os.getenv("STREAM_MAX_CONCURRENCY", "8"))
        except Exception:
            pass
        sem = asyncio.Semaphore(max_c)
        _LOOP_SEMS[lid] = sem
    return sem

# ==============================
#       Metryki i koszt
# ==============================
_RECENT_METRICS: List[Dict[str, Any]] = []
_RECENT_MAX = 100

def _approx_tokens(s: str) -> int:
    if not s:
        return 0
    return max(1, int(math.ceil(len(s) / 4)))  # ~4 znaki / token

def estimate_cost(prompt_text: str, completion_text: str, cfg: StreamConfig) -> float:
    pt = _approx_tokens(prompt_text)
    ct = _approx_tokens(completion_text)
    cost = 0.0
    if cfg.cost_prompt_per_1k:
        cost += (pt / 1000.0) * cfg.cost_prompt_per_1k
    if cfg.cost_comp_per_1k:
        cost += (ct / 1000.0) * cfg.cost_comp_per_1k
    return round(cost, 6)

def summarize_metrics(prompt: str, completion: str, cfg: Optional[StreamConfig] = None) -> Dict[str, Any]:
    cfg = cfg or StreamConfig.from_env()
    data = {
        "prompt_tokens_approx": _approx_tokens(prompt),
        "completion_tokens_approx": _approx_tokens(completion),
        "estimated_cost": estimate_cost(prompt, completion, cfg),
        "cost_prompt_per_1k": cfg.cost_prompt_per_1k,
        "cost_comp_per_1k": cfg.cost_comp_per_1k,
    }
    return data

def _push_metrics(meta: Dict[str, Any]):
    _RECENT_METRICS.append(meta)
    if len(_RECENT_METRICS) > _RECENT_MAX:
        del _RECENT_METRICS[: len(_RECENT_METRICS) - _RECENT_MAX]

def get_recent_metrics(n: int = 10) -> List[Dict[str, Any]]:
    return _RECENT_METRICS[-n:]

# ==============================
#         Public API
# ==============================

async def stream_first_or_fallback_iter(
    llm_messages: List[dict],
    model_override: Optional[str] = None,
    cfg: Optional[StreamConfig] = None,
    keepalives: bool = True,
) -> AsyncIterator[str]:
    """
    Async iterator tokenów:
    - próbuje streamować (chyba że cfg.collect_mode == 'force_fallback')
    - jeśli nie ma 1. tokena w czasie first_token_timeout -> fallback
    - keepalive emituje jako cfg.keepalive_token (domyślnie NUL)
    """
    cfg = cfg or StreamConfig.from_env()
    t0 = time.time()
    meta = {
        "mode": "stream",
        "started_at": t0,
        "first_token_ms": None,
        "end_ms": None,
        "fallback_used": False,
        "model_override": model_override,
    }
    if cfg.on_start:
        with contextlib.suppress(Exception): cfg.on_start({"messages_len": len(llm_messages)})

    # force fallback?
    if cfg.collect_mode == "force_fallback" or _cb_is_open(cfg.cb_key):
        if _cb_is_open(cfg.cb_key):
            log_warning(f"[STREAM_UTIL] CB OPEN (key={cfg.cb_key}) – od razu fallback")
        meta["mode"] = "fallback"
        async for tok in _fallback_collect(llm_messages, model_override, cfg):
            if cfg.on_token and tok and tok != cfg.keepalive_token:
                with contextlib.suppress(Exception): cfg.on_token(tok)
            yield tok
        meta["fallback_used"] = True
        meta["end_ms"] = int((time.time() - t0) * 1000)
        _push_metrics(meta)
        return

    # force stream?
    force_stream = cfg.collect_mode == "force_stream"

    # worker streamujący
    try:
        from .llm import call_llm_stream_with_fallback
    except Exception as e:
        log_warning(f"[STREAM_UTIL] Brak call_llm_stream_with_fallback: {e}")
        call_llm_stream_with_fallback = None

    if call_llm_stream_with_fallback is None and not force_stream:
        # fallback bez streamu
        meta["mode"] = "fallback"
        async for tok in _fallback_collect(llm_messages, model_override, cfg):
            if cfg.on_token and tok and tok != cfg.keepalive_token:
                with contextlib.suppress(Exception): cfg.on_token(tok)
            yield tok
        meta["fallback_used"] = True
        meta["end_ms"] = int((time.time() - t0) * 1000)
        _push_metrics(meta)
        return

    queue: "asyncio.Queue[str]" = asyncio.Queue()
    done = asyncio.Event()
    err_holder: Dict[str, Any] = {"e": None}

    async def _worker():
        sem = _get_sem()
        async with sem:
            try:
                async for tok in call_llm_stream_with_fallback(
                    llm_messages, temperature=0.7, model_override=model_override
                ):
                    await queue.put(tok or "")
            except Exception as e:
                err_holder["e"] = e
            finally:
                done.set()

    task = asyncio.create_task(_worker())

    # first token gate (jeśli nie force_stream)
    first_seen = False
    if not force_stream:
        try:
            tok = await asyncio.wait_for(queue.get(), timeout=cfg.first_token_timeout)
            first_seen = True
            meta["first_token_ms"] = int((time.time() - t0) * 1000)
            _cb_success(cfg.cb_key)
            if tok:
                if cfg.on_token and tok != cfg.keepalive_token:
                    with contextlib.suppress(Exception): cfg.on_token(tok)
                yield tok
        except asyncio.TimeoutError:
            # fallback
            with contextlib.suppress(Exception):
                task.cancel()
                await task
            _cb_fail(cfg.cb_key, cfg.cb_window, cfg.cb_threshold, cfg.cb_open_sec)
            meta["mode"] = "fallback"
            async for tok in _fallback_collect(llm_messages, model_override, cfg):
                if cfg.on_token and tok and tok != cfg.keepalive_token:
                    with contextlib.suppress(Exception): cfg.on_token(tok)
                yield tok
            meta["fallback_used"] = True
            meta["end_ms"] = int((time.time() - t0) * 1000)
            _push_metrics(meta)
            return
    else:
        # force stream – nie czekamy na pierwszy token, jedziemy pętlą niżej
        pass

    # kontynuacja streamu
    last_emit = time.time()
    silence_start = time.time()
    start_time = t0

    while True:
        now = time.time()
        # limity
        if now - start_time > cfg.hard_time_limit:
            log_warning("[STREAM_UTIL] HARD LIMIT czasu – kończę stream")
            with contextlib.suppress(Exception):
                task.cancel()
                await task
            break

        # keepalive
        if keepalives and (now - last_emit) >= cfg.sse_keepalive_interval:
            yield cfg.keepalive_token
            last_emit = now

        # jeśli worker padł i kolejka pusta → koniec
        if done.is_set() and queue.empty():
            break

        try:
            tok = await asyncio.wait_for(queue.get(), timeout=cfg.per_token_timeout)
            last_emit = time.time()
            silence_start = last_emit
            if tok:
                # wykrywanie prefiksów błędów w strumieniu
                for pref in cfg.error_prefixes:
                    if tok.startswith(pref):
                        log_warning(f"[STREAM_UTIL] Error-like token: {tok[:60]}")
                        break
                if cfg.on_token and tok != cfg.keepalive_token:
                    with contextlib.suppress(Exception): cfg.on_token(tok)
                yield tok
        except asyncio.TimeoutError:
            # cisza – sprawdź czy nie za długo
            if time.time() - silence_start > cfg.max_silence:
                log_warning("[STREAM_UTIL] Zbyt długa cisza – przerywam stream")
                with contextlib.suppress(Exception):
                    task.cancel()
                    await task
                break
            # w innym wypadku – pętla dalej
            continue

    with contextlib.suppress(Exception):
        await task

    # błąd z workera?
    if err_holder["e"] and cfg.on_error:
        with contextlib.suppress(Exception): cfg.on_error(err_holder["e"])

    meta["end_ms"] = int((time.time() - t0) * 1000)
    _push_metrics(meta)


async def _fallback_collect(
    llm_messages: List[dict], model_override: Optional[str], cfg: StreamConfig
) -> AsyncIterator[str]:
    """
    Fallback „non-stream” (preferowany) albo „zebranie streamu” do 1 chmury tekstu.
    Z małym backoffem (jitter) przy pierwszym podejściu, żeby uniknąć thundering-herd.
    """
    # drobny jitter
    await asyncio.sleep(random.uniform(0.02, 0.12))

    # call_llm (non-stream)
    call_llm = None
    try:
        from .llm import call_llm as _call_llm
        call_llm = _call_llm
    except Exception:
        pass

    if call_llm is not None:
        try:
            sem = _get_sem()
            async with sem:
                text = await call_llm(llm_messages, temperature=0.7, model_override=model_override)
            yield text or ""
            return
        except Exception as e:
            log_warning(f"[STREAM_UTIL] call_llm nieudany, spróbuję zebrać stream: {e}")

    # ostateczność: zbierz strumień do jednego stringa
    try:
        from .llm import call_llm_stream_with_fallback
        acc: List[str] = []
        sem = _get_sem()
        async with sem:
            async for tok in call_llm_stream_with_fallback(
                llm_messages, temperature=0.7, model_override=model_override
            ):
                if tok:
                    acc.append(tok)
        yield "".join(acc)
    except Exception as e:
        log_warning(f"[STREAM_UTIL] Nie udało się nawet zebrać streamu: {e}")
        yield ""

# ===== Pełny tekst (jak wcześniej) =====
async def _stream_first_or_fallback(
    llm_messages: List[dict],
    model_override: Optional[str] = None,
    cfg: Optional[StreamConfig] = None,
) -> str:
    """Zwraca cały tekst (sklejone tokeny z iteratora), pomija keepalive'y."""
    cfg = cfg or StreamConfig.from_env()
    acc: List[str] = []
    async for tok in stream_first_or_fallback_iter(llm_messages, model_override=model_override, cfg=cfg):
        if tok == cfg.keepalive_token:
            continue
        acc.append(tok)
    return "".join(acc)

# alias zgodny z wcześniejszym importem
stream_first_or_fallback = _stream_first_or_fallback

# ==============================
#      SSE adapter (opcjonalne)
# ==============================
async def sse_stream_adapter(
    llm_messages: List[dict],
    model_override: Optional[str] = None,
    cfg: Optional[StreamConfig] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> AsyncIterator[str]:
    """
    Zwraca gotowe linie SSE:
      data: {"type":"start"}
      data: {"type":"chunk","content":"..."}
      data: {"type":"ping"}
      data: {"type":"complete","answer":"...","metadata":{...}}
      data: {"type":"error","message":"..."}
    """
    cfg = cfg or StreamConfig.from_env()
    meta = metadata.copy() if metadata else {}
    answer_acc: List[str] = []

    # start
    yield "data: " + json.dumps({"type": "start"}) + "\n\n"

    try:
        buffer: List[str] = []
        last_flush = time.time()

        async for tok in stream_first_or_fallback_iter(llm_messages, model_override=model_override, cfg=cfg):
            if tok == cfg.keepalive_token:
                yield "data: " + json.dumps({"type": "ping"}) + "\n\n"
                continue

            # częściowy flush?
            if cfg.partial_flush_chars and tok:
                buffer.append(tok)
                if (len("".join(buffer)) >= cfg.partial_flush_chars) or (time.time() - last_flush) > 0.5:
                    chunk = "".join(buffer)
                    buffer.clear()
                    last_flush = time.time()
                    answer_acc.append(chunk)
                    yield "data: " + json.dumps({"type": "chunk", "content": chunk}) + "\n\n"
            else:
                answer_acc.append(tok)
                yield "data: " + json.dumps({"type": "chunk", "content": tok}) + "\n\n"

        # zrzut ewentualnego bufora
        if buffer:
            chunk = "".join(buffer)
            answer_acc.append(chunk)
            yield "data: " + json.dumps({"type": "chunk", "content": chunk}) + "\n\n"

        full_answer = "".join(answer_acc)
        meta_out = {
            **meta,
            "metrics": summarize_metrics(_safe_first_user(llm_messages), full_answer, cfg),
            "stream_adapter": True,
        }
        if cfg.on_complete:
            with contextlib.suppress(Exception): cfg.on_complete(full_answer, meta_out)

        yield "data: " + json.dumps({"type": "complete", "answer": full_answer, "metadata": meta_out}) + "\n\n"

    except Exception as e:
        if cfg.on_error:
            with contextlib.suppress(Exception): cfg.on_error(e)
        yield "data: " + json.dumps({"type": "error", "message": str(e)}) + "\n\n"

def _safe_first_user(messages: List[dict]) -> str:
    # do estymacji kosztu promptu
    for m in reversed(messages):
        if (m.get("role") == "user") and m.get("content"):
            return str(m["content"])
    # w ostateczności cały prompt jako tekst
    try:
        return json.dumps(messages, ensure_ascii=False)
    except Exception:
        return ""
