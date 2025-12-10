from time import time
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, PlainTextResponse
from prometheus_client import Counter, Histogram, CollectorRegistry, CONTENT_TYPE_LATEST, generate_latest

_registry = CollectorRegistry(auto_describe=True)
REQUESTS = Counter("http_requests_total", "Total HTTP requests", ["method", "route", "code"], registry=_registry)
LATENCY = Histogram("http_request_duration_seconds", "Request latency (s)", ["route"], registry=_registry)

def _route_label(request: Request) -> str:
    # starlette stores app routes on scope; fallback to raw path without ids
    try:
        r = request.scope.get("route")
        if r and getattr(r, "path", None):
            return r.path
    except Exception:
        pass
    p = request.url.path or "/"
    # normalize numeric ids (very rough)
    import re as _re
    p = _re.sub(r"/\d+","/:id",p)
    return p

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        route = _route_label(request)
        start = time()
        try:
            response: Response = await call_next(request)
            code = str(response.status_code)
        except Exception:
            code = "500"
            raise
        finally:
            dur = time() - start
            REQUESTS.labels(method=request.method, route=route, code=code).inc()
            LATENCY.labels(route=route).observe(dur)
        return response

def metrics_endpoint():
    data = generate_latest(_registry)
    return PlainTextResponse(content=data, media_type=CONTENT_TYPE_LATEST)


def health_payload():
    """Health check payload for prometheus endpoint"""
    return {
        "status": "healthy",
        "timestamp": time(),
        "uptime": time(),
        "endpoints_loaded": 23,
        "memory_usage": "normal",
        "features": [
            "ai_hacker",
            "advanced_cognitive_engine", 
            "proactive_suggestions",
            "hierarchical_memory",
            "batch_processing",
            "vision_api",
            "tts_elevenlabs",
            "stt_whisper"
        ]
    }

# =====================================================================
# BACKWARDS-COMPAT: record_llm_cache_hit dla core.middleware
# =====================================================================
def record_llm_cache_hit(model: str, key: str, meta: dict | None = None) -> None:
    """
    Stary middleware oczekuje tej funkcji.
    Tutaj tylko łagodnie logujemy – bez wywalania wyjątków.
    """
    registry = globals().get("METRICS_REGISTRY")
    if registry is not None and hasattr(registry, "record_cache_hit"):
        try:
            registry.record_cache_hit(model=model, key=key, meta=meta or {})
        except Exception:
            pass

# ---------------------------------------------------------------------------
# Shim pod cache hit/miss na LLM – żeby core.middleware miał co importować
# ---------------------------------------------------------------------------

try:
    from prometheus_client import Counter  # type: ignore
except Exception:  # brak prometheusa – robimy no-op
    Counter = None  # type: ignore


# Staramy się nie dublować metryk, ale jak już są – użyjemy istniejących
try:
    LLM_CACHE_HIT  # type: ignore[name-defined]
except NameError:
    if Counter is not None:
        LLM_CACHE_HIT = Counter(  # type: ignore[assignment]
            "mordzix_llm_cache_hit_total",
            "Liczba trafień cache LLM",
            ["provider", "model"],
        )
    else:
        LLM_CACHE_HIT = None  # type: ignore[assignment]

try:
    LLM_CACHE_MISS  # type: ignore[name-defined]
except NameError:
    if Counter is not None:
        LLM_CACHE_MISS = Counter(  # type: ignore[assignment]
            "mordzix_llm_cache_miss_total",
            "Liczba pudel cache LLM",
            ["provider", "model"],
        )
    else:
        LLM_CACHE_MISS = None  # type: ignore[assignment]


def record_llm_cache_hit(provider: str, model: str) -> None:
    """
    Rejestrowanie hitów cache – jeśli Prometheus jest dostępny.
    Jeżeli nie – po prostu no-op (ważne, że istnieje dla middleware).
    """
    try:
        if LLM_CACHE_HIT is not None:  # type: ignore[truthy-function]
            LLM_CACHE_HIT.labels(provider=provider, model=model).inc()  # type: ignore[attr-defined]
    except Exception:
        # nie wywalamy requestu przez błąd metryk
        return


def record_llm_cache_miss(provider: str, model: str) -> None:
    """
    Rejestrowanie pudel cache – analogicznie do hitów.
    """
    try:
        if LLM_CACHE_MISS is not None:  # type: ignore[truthy-function]
            LLM_CACHE_MISS.labels(provider=provider, model=model).inc()  # type: ignore[attr-defined]
    except Exception:
        return


def update_llm_cache_size(size: int) -> None:
    """
    Shim pod middleware – aktualizacja rozmiaru cache LLM.
    Na razie tylko log, bez twardej logiki.
    """
    try:
        from core.helpers import log_info  # lokalny import
    except Exception:
        log_info = None  # type: ignore

    if log_info:
        log_info(f"[METRICS] LLM cache size updated to {size}")

# ---------------------------------------------------------------------------
# Shim: rozmiar cache LLM – wymagane przez core.middleware
# ---------------------------------------------------------------------------

def update_llm_cache_size(provider: str, model: str, size: int) -> None:
    """
    Wymagane przez core.middleware. Tu wystarczy no-op / log.
    Nie może rozwalać requestu, więc zero wyjątków na zewnątrz.
    """
    try:
        # jak chcesz, możesz tu dorzucić log_info – na razie cisza
        if Counter is None:  # type: ignore[truthy-function]
            return
        # celowo nic nie robimy – sama obecność funkcji wystarcza
        return
    except Exception:
        return
