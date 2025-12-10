#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================
MORDZIX AI PRO - Unified Application
Version: 6.0.0 (December 2025)
============================================

- Tryby tematyczne, web search, pliki, pamięć LTM/STM
- Auto-learning + self-critique + autoadaptacja jakości
- Profil użytkownika (/api/profile/whoami)
"""

from __future__ import annotations

import os
import time
import uuid
import logging
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI
from core.meta_endpoint import router as meta_router, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse, Response
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

# ────────────────────────────────────────────────────────────────────
# KONFIG
# ────────────────────────────────────────────────────────────────────
APP_NAME = "Mordzix AI PRO"
APP_VERSION = "6.0.0"

BASE_DIR = Path(__file__).parent.absolute()
APP_ROOT = BASE_DIR.parent  # repo root (…/mordzix-ai)
os.environ.setdefault("AUTH_TOKEN", "__CHANGE_ME_AUTH_TOKEN__")
os.environ.setdefault("WORKSPACE", str(BASE_DIR))
os.environ.setdefault("MEM_DB", str(BASE_DIR / "mem.db"))

# Opcjonalne metryki
try:
    from core.metrics import MetricsMiddleware, metrics_endpoint  # type: ignore
    PROMETHEUS_AVAILABLE = True
except Exception:
    PROMETHEUS_AVAILABLE = False
    MetricsMiddleware = None  # type: ignore

    def metrics_endpoint():
        return {"ok": False, "detail": "metrics disabled"}

# Rate limit z configu
try:
    from .config import RATE_LIMIT_ENABLED, RATE_LIMIT_PER_MINUTE  # type: ignore
except Exception:
    RATE_LIMIT_ENABLED = False
    RATE_LIMIT_PER_MINUTE = 120

_SUPPRESS_IMPORT_LOGS = os.environ.get("MORDZIX_SUPPRESS_STARTUP_LOGS") == "1"

# ────────────────────────────────────────────────────────────────────
# UTILS
# ────────────────────────────────────────────────────────────────────
def _get_cors_origins() -> List[str]:
    raw = os.getenv("CORS_ORIGINS", "").strip()
    if not raw:
        return ["http://localhost:5173", "http://localhost:8080"]
    return [p.strip() for p in raw.split(",") if p.strip()]

def _req_id_from(request: Request) -> str:
    rid = request.headers.get("X-Request-ID")
    if rid:
        return rid
    try:
        if hasattr(request, "state") and getattr(request.state, "request_id", None):
            return str(request.state.request_id)
    except Exception:
        pass
    return "n/a"

def _json_error(status: int, code: str, detail, request_id: str):
    payload = {"error": code, "code": status, "detail": detail, "request_id": request_id}
    return JSONResponse(status_code=status, content=payload)

# ────────────────────────────────────────────────────────────────────
# APLIKACJA
# ────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Zaawansowany asystent AI (tryby: Tech, Sport, Moda/Vinted, HVAC/Budowlany, Pisma urzędowe). Web search, pamięć, obrazy, załączniki.",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ────────────────────────────────────────────────────────────────────
# MIDDLEWARE
# ────────────────────────────────────────────────────────────────────
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        start = time.time()
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Response-Time"] = f"{(time.time()-start)*1000:.1f}ms"
        return response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """CSP + bezpieczne nagłówki (XSS/Clickjacking)."""
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' cdnjs.cloudflare.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' data: cdnjs.cloudflare.com; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response

# naiwny per-process rate limiter
_RATE_BUCKETS: Dict[str, tuple[int, int]] = {}
class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not RATE_LIMIT_ENABLED:
            return await call_next(request)
        try:
            ip = request.client.host if request.client else "unknown"
        except Exception:
            ip = "unknown"
        key = f"{ip}:{request.url.path}"
        now = time.time()
        window = int(now // 60)  # per-minute
        count, win = _RATE_BUCKETS.get(key, (0, window))
        if win != window:
            count, win = 0, window
        count += 1
        _RATE_BUCKETS[key] = (count, win)
        if count > RATE_LIMIT_PER_MINUTE:
            return JSONResponse(status_code=429, content={"error": "rate_limit", "detail": "Too Many Requests"})
        return await call_next(request)

# rejestracja middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(CORSMiddleware, allow_origins=_get_cors_origins(), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
if PROMETHEUS_AVAILABLE and MetricsMiddleware:
    app.add_middleware(MetricsMiddleware)

# ────────────────────────────────────────────────────────────────────
# EXCEPTION HANDLERS
# ────────────────────────────────────────────────────────────────────
@app.exception_handler(StarletteHTTPException)
async def http_exc_handler(request: Request, exc: StarletteHTTPException):
    return _json_error(exc.status_code, "http_error", exc.detail, _req_id_from(request))

@app.exception_handler(RequestValidationError)
async def validation_exc_handler(request: Request, exc: RequestValidationError):
    return _json_error(422, "validation_error", exc.errors(), _req_id_from(request))

@app.exception_handler(Exception)
async def unhandled_exc_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception: {type(exc).__name__}: {exc}", exc_info=True)
    return _json_error(500, "internal_error", "An internal error occurred", _req_id_from(request))

# ────────────────────────────────────────────────────────────────────
# AUTOMATION SUMMARY
# ────────────────────────────────────────────────────────────────────
MANUAL_TOOL_ENDPOINTS: List[Dict[str, str]] = [
    {"name": "code_write",        "endpoint": "POST /api/code/write",        "reason": "Zapis plików w repo."},
    {"name": "code_deps_install", "endpoint": "POST /api/code/deps/install", "reason": "Instalacja zależności."},
    {"name": "code_docker_build", "endpoint": "POST /api/code/docker/build", "reason": "Budowanie obrazu Docker."},
    {"name": "code_docker_run",   "endpoint": "POST /api/code/docker/run",   "reason": "Uruchomienie kontenera."},
    {"name": "code_git",          "endpoint": "POST /api/code/git",          "reason": "Operacje na historii Git."},
    {"name": "code_init",         "endpoint": "POST /api/code/init",         "reason": "Tworzenie struktury projektu."},
]

_AUTOMATION_SUMMARY_CACHE: Dict[str, Any] = {}
_AUTOMATION_SUMMARY_TS: float = 0.0

def _load_fast_path_handlers() -> Dict[str, Any]:
    try:
        from core.intent_dispatcher import FAST_PATH_HANDLERS  # type: ignore
        handlers = [h.__name__ for h in FAST_PATH_HANDLERS]
        return {"available": True, "handlers": handlers, "count": len(handlers)}
    except Exception as exc:
        if not _SUPPRESS_IMPORT_LOGS:
            print(f"[WARN] Fast path handlers unavailable: {exc}")
        return {"available": True, "handlers": [], "count": 0, "error": str(exc)}

def _load_tool_registry() -> Dict[str, Any]:
    try:
        from core.tools_registry import get_all_tools  # type: ignore
        tools = get_all_tools()
        tool_names = [t.get("name", "") for t in tools if t.get("name")]
        categories_counter = Counter(name.split("_", 1)[0] if "_" in name else name for name in tool_names)
        categories = [{"name": key, "count": categories_counter[key]} for key in sorted(categories_counter, key=lambda k: (-categories_counter[k], k))]
        return {"available": True, "count": len(tools), "tools": tools, "names": tool_names, "categories": categories}
    except Exception as exc:
        if not _SUPPRESS_IMPORT_LOGS:
            print(f"[WARN] Tool registry unavailable: {exc}")
        return {"available": True, "count": 0, "tools": [], "names": [], "categories": [], "error": str(exc)}

def _build_automation_summary() -> Dict[str, Any]:
    fast_path = _load_fast_path_handlers()
    tools = _load_tool_registry()
    manual_count = len(MANUAL_TOOL_ENDPOINTS)
    totals_automations = fast_path.get("count", 0) + tools.get("count", 0)
    totals_automatic = max(totals_automations - manual_count, 0)
    return {
        "generated_at": time.time(),
        "fast_path": fast_path,
        "tools": {
            "available": tools.get("available", True),
            "count": tools.get("count", 0),
            "categories": tools.get("categories", []),
            "sample": tools.get("names", [])[:15],
        },
        "manual": {"count": manual_count, "endpoints": MANUAL_TOOL_ENDPOINTS},
        "totals": {"automations": totals_automations, "automatic": totals_automatic},
    }

def get_automation_summary(refresh: bool = False) -> Dict[str, Any]:
    global _AUTOMATION_SUMMARY_CACHE, _AUTOMATION_SUMMARY_TS
    if refresh or not _AUTOMATION_SUMMARY_CACHE:
        _AUTOMATION_SUMMARY_CACHE = _build_automation_summary()
        _AUTOMATION_SUMMARY_TS = _AUTOMATION_SUMMARY_CACHE.get("generated_at", time.time())
    else:
        _AUTOMATION_SUMMARY_CACHE["generated_at"] = _AUTOMATION_SUMMARY_TS
    return _AUTOMATION_SUMMARY_CACHE

# ────────────────────────────────────────────────────────────────────
# ROUTERS
# ────────────────────────────────────────────────────────────────────
if not _SUPPRESS_IMPORT_LOGS:
    print("\n" + "=" * 70)
    print("MORDZIX AI - INICJALIZACJA ENDPOINTÓW")
    print("=" * 70 + "\n")

def _try_include(label: str, import_path: str, attr: str = "router", **kwargs):
    try:
        mod = __import__(import_path, fromlist=[attr])
        app.include_router(getattr(mod, attr), **kwargs)
        if not _SUPPRESS_IMPORT_LOGS:
            print(f"[OK] {label}")
    except Exception as e:
        if not _SUPPRESS_IMPORT_LOGS:
            print(f"[FAIL] {label}: {e}")

# Core chat + sesje
_try_include("Assistant endpoint      /api/chat/assistant", "core.assistant_endpoint")
_try_include("Sessions endpoint       /api/sessions/*", "core.sessions_endpoint")

# „Psyche”, programista, pliki, travel…
_try_include("Psyche endpoint         /api/psyche/*", "core.psyche_endpoint")
_try_include("Programista endpoint    /api/code/*", "core.programista_endpoint")
_try_include("Files endpoint          /api/files/*", "core.files_endpoint")
_try_include("Travel endpoint         /api/travel/*", "core.travel_endpoint")
_try_include("Admin endpoint          /api/admin/*", "core.admin_endpoint")
_try_include("Prometheus endpoint     /api/prometheus/*", "core.prometheus_endpoint", prefix="/api/prometheus", tags=["monitoring"])
_try_include("STT endpoint            /api/stt/*", "core.stt_endpoint")
_try_include("Writing endpoint        /api/writing/*", "core.writing_endpoint")
_try_include("Suggestions endpoint    /api/suggestions/*", "core.suggestions_endpoint")
_try_include("Batch endpoint          /api/batch/*", "core.batch_endpoint")
_try_include("Research endpoint       /api/research/*", "core.research_endpoint")
_try_include("Cognitive endpoint      /api/cognitive/*", "core.cognitive_endpoint")
_try_include("Memory endpoint         /api/memory/*", "core.memory_endpoint")
_try_include("AI Fashion endpoint     /api/fashion/*", "core.fashion_endpoint")
_try_include("AI Auction endpoint     /api/auction/*", "core.auction_endpoint")
_try_include("ML Predictions endpoint /api/ml/*", "core.ml_endpoint")
_try_include("Fact Validation endpoint /api/facts/*", "core.fact_validation_endpoint")
_try_include("Vision endpoint         /api/vision/*", "core.vision_endpoint")
_try_include("Voice endpoint          /api/voice/*", "core.voice_endpoint")
_try_include("Self-Reflection endpoint /api/reflection/*", "core.reflection_endpoint")
_try_include("AI Hacker endpoint      /api/hacker/*", "core.hacker_endpoint")
_try_include("Image endpoint          /api/image/*", "core.image_endpoint")
_try_include("NLP endpoint            /api/nlp/*", "core.nlp_endpoint")
_try_include("AutoRouter endpoint     /api/autoroute/*", "core.frontend_autorouter")
_try_include("Lang endpoint           /api/lang/*", "core.lang_endpoint")
_try_include("Internal endpoint       /api/internal/*", "core.internal_endpoint")
_try_include("Media endpoint          /api/tts/*,/api/images/*", "core.media_endpoint", prefix="/api", tags=["media"])
_try_include("Hybrid Search endpoint  /api/search/*", "core.hybrid_search_endpoint")
_try_include("Legal Office endpoint   /api/legal/*", "core.legal_office_endpoint")
_try_include("AI Negocjator endpoint  /api/negocjator/*", "core.negocjator_endpoint")

# NOWE: profil użytkownika (whoami)
_try_include("Profile endpoint        /api/profile/*", "core.profile_endpoint")

# Opcjonalny hotfix chat
_try_include("Hotfix Chat endpoint    /api/hotfix/chat/*", "core.hotfix_chat")

if not _SUPPRESS_IMPORT_LOGS:
    print("\n" + "=" * 70)
    print("WSZYSTKIE ENDPOINTY ZAŁADOWANE")
    print("=" * 70 + "\n")

# ────────────────────────────────────────────────────────────────────
# PODSTAWOWE ROUTES / STATUS
# ────────────────────────────────────────────────────────────────────
@app.get("/api")
@app.get("/status")
async def api_status():
    """Status API + podsumowanie automatyzacji."""
    return {
        "ok": True,
        "app": APP_NAME,
        "version": APP_VERSION,
        "features": {
            "auto_stm_to_ltm": True,
            "auto_learning": True,
            "context_injection": True,
            "psyche_system": True,
            "travel_search": True,
            "code_executor": True,
            "tts_stt": True,
            "file_analysis": True,
            "self_critique": True,
            "quality_adaptation": True,
            "user_profile": True
        },
        "endpoints": {
            "chat": "/api/chat/assistant",
            "chat_stream": "/api/chat/assistant/stream",
            "psyche": "/api/psyche/status",
            "travel": "/api/travel/search",
            "code": "/api/code/exec",
            "files": "/api/files/upload",
            "admin": "/api/admin/stats",
            "tts": "/api/tts/speak",
            "stt": "/api/stt/transcribe",
            "profile": "/api/profile/whoami"
        },
        "automation": get_automation_summary()
    }

@app.get("/health")
async def health():
    """Rozszerzony health-check (DB+memory)."""
    checks = {"api": "ok", "database": "unknown", "memory": "unknown"}
    # DB
    try:
        from core.sessions import get_db  # type: ignore
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM sessions")
            cur.fetchone()
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)[:80]}"
    # Memory
    try:
        from core.config import MEMORY_ENABLED  # type: ignore
        if MEMORY_ENABLED:
            from core.memory import get_memory_system  # type: ignore
            mem_sys = get_memory_system()
            checks["memory"] = "ok" if mem_sys else "disabled"
        else:
            checks["memory"] = "disabled"
    except Exception as e:
        checks["memory"] = f"error: {str(e)[:80]}"

    all_ok = checks["database"] == "ok" and checks["api"] == "ok"
    status = "healthy" if all_ok else "degraded"
    return {"status": status, "timestamp": time.time(), "checks": checks}

@app.get("/api/endpoints/list")
async def list_endpoints():
    """Lista wszystkich endpointów API."""
    endpoints = []
    seen = set()
    for route in app.routes:
        if isinstance(route, APIRoute) and route.path.startswith("/api"):
            methods = sorted([m for m in route.methods if m not in {"HEAD", "OPTIONS"}])
            ident = (route.path, tuple(methods))
            if ident in seen:
                continue
            endpoints.append({
                "path": route.path,
                "methods": methods,
                "name": route.name,
                "tags": list(route.tags) if route.tags else [],
                "summary": route.summary or ""
            })
            seen.add(ident)
    endpoints.sort(key=lambda e: (e["path"], ",".join(e["methods"])))
    return {"ok": True, "count": len(endpoints), "endpoints": endpoints}

@app.get("/api/automation/status")
async def automation_status():
    return {"ok": True, **get_automation_summary()}

# ────────────────────────────────────────────────────────────────────
# FRONTEND / STATIC
# ────────────────────────────────────────────────────────────────────
FRONTEND_DIR = APP_ROOT / "frontend"

if (FRONTEND_DIR / "css").exists():
    app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="frontend_css")
    print("[OK] Frontend CSS mounted at /css/")

if (FRONTEND_DIR / "js").exists():
    app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="frontend_js")
    print("[OK] Frontend JS mounted at /js/")

print("[INIT] Registering serve_frontend for routes: /, /app, /chat")

@app.get("/", response_class=HTMLResponse)
@app.get("/app", response_class=HTMLResponse)
@app.get("/chat", response_class=HTMLResponse)
async def serve_frontend():
    new_frontend = FRONTEND_DIR / "index.html"
    if new_frontend.exists():
        return HTMLResponse(content=new_frontend.read_text(encoding="utf-8"))
    return HTMLResponse(
        content="""
        <!DOCTYPE html>
        <html>
        <head><title>Mordzix AI</title></head>
        <body style="background:#0d0d0d;color:#fff;font-family:sans-serif;text-align:center;padding:50px;">
            <h1>Frontend not found</h1>
            <p>Please ensure frontend/index.html exists.</p>
            <p>API docs: <a href="/docs" style="color:#10a37f;">/docs</a></p>
        </body>
        </html>
        """,
        status_code=404
    )

@app.get("/legal", response_class=HTMLResponse)
@app.get("/pisma", response_class=HTMLResponse)
async def serve_legal_frontend():
    p = FRONTEND_DIR / "legal.html"
    return HTMLResponse(content=p.read_text(encoding="utf-8")) if p.exists() else HTMLResponse(content="Legal module not found", status_code=404)

@app.get("/admin", response_class=HTMLResponse)
@app.get("/panel", response_class=HTMLResponse)
async def serve_admin_panel():
    p = FRONTEND_DIR / "admin.html"
    return HTMLResponse(content=p.read_text(encoding="utf-8")) if p.exists() else HTMLResponse(content="Admin panel not found", status_code=404)

@app.get("/license", response_class=HTMLResponse)
@app.get("/licencja", response_class=HTMLResponse)
async def serve_license_page():
    p = FRONTEND_DIR / "license.html"
    return HTMLResponse(content=p.read_text(encoding="utf-8")) if p.exists() else HTMLResponse(content="License page not found", status_code=404)

@app.get("/negocjator", response_class=HTMLResponse)
@app.get("/debt", response_class=HTMLResponse)
async def serve_negocjator_page():
    p = FRONTEND_DIR / "negocjator.html"
    return HTMLResponse(content=p.read_text(encoding="utf-8")) if p.exists() else HTMLResponse(content="Negocjator page not found", status_code=404)

# PWA assets
@app.get("/sw.js", include_in_schema=False)
@app.get("/ngsw-worker.js", include_in_schema=False)
async def serve_service_worker():
    candidates = [APP_ROOT / "sw.js", FRONTEND_DIR / "sw.js", BASE_DIR / "sw.js"]
    for path in candidates:
        if path.exists():
            return FileResponse(path, media_type="application/javascript")
    return HTMLResponse(status_code=404, content="service worker not found")

@app.get("/manifest.webmanifest", include_in_schema=False)
async def serve_manifest():
    candidates = [APP_ROOT / "manifest.webmanifest", FRONTEND_DIR / "manifest.webmanifest", BASE_DIR / "manifest.webmanifest"]
    for path in candidates:
        if path.exists():
            return FileResponse(path, media_type="application/manifest+json")
    return HTMLResponse(status_code=404, content="manifest not found")

@app.get("/favicon.ico", include_in_schema=False)
async def serve_favicon():
    paths = [FRONTEND_DIR / "favicon.ico", APP_ROOT / "favicon.ico", BASE_DIR / "icons" / "favicon.ico"]
    for path in paths:
        if path.exists():
            return FileResponse(path, media_type="image/x-icon")
    return HTMLResponse(status_code=404)

# Static /icons
if (BASE_DIR / "icons").exists():
    app.mount("/icons", StaticFiles(directory=str(BASE_DIR / "icons")), name="icons")

# Alternatywny webui
webui_dir = BASE_DIR.parent / "webui"
if webui_dir.exists():
    app.mount("/webui", StaticFiles(directory=str(webui_dir)), name="webui")
    print("[OK] WebUI Frontend mounted at /webui/")
    @app.get("/webui/", include_in_schema=False)
    async def webui_index():
        return FileResponse(str(webui_dir / "index.html"))
else:
    print(f"[FAIL] WebUI directory not found at {webui_dir}")

# ────────────────────────────────────────────────────────────────────
# STARTUP / SHUTDOWN
# ────────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    print("\n" + "="*70)
    print("MORDZIX AI - STARTED")
    print("="*70)
    print(f"\n[INFO] {APP_NAME} v{APP_VERSION}")
    print("  [OK] Auto STM->LTM transfer")
    print("  [OK] Auto-learning (web + scraping)")
    print("  [OK] Context injection (LTM w prompt)")
    print("  [OK] Psyche system")
    print("  [OK] Travel / Code / Files / TTS/STT")
    print("  [OK] Self-critique & Quality adaptation")
    print("  [OK] Profile (/api/profile/whoami)")
    print("\n[INFO] Endpoints: POST /api/chat/assistant | POST /api/chat/assistant/stream | GET /api/profile/whoami\n")

    summary = get_automation_summary(refresh=True)
    print("[INFO] Automatyzacja:")
    print(f"  [OK] Fast path handlers : {summary.get('fast_path',{}).get('count',0)}")
    print(f"  [OK] Router tools       : {summary.get('tools',{}).get('count',0)}")
    print(f"  [OK] Manual approvals   : {summary.get('manual',{}).get('count',0)}")
    print(f"  [OK] Auto executables   : {summary.get('totals',{}).get('automatic',0)}")

    # init pamięci
    try:
        from core.memory import _init_db, load_ltm_to_memory  # type: ignore
        _init_db()
        load_ltm_to_memory()
        print("[OK] Pamięć LTM załadowana")
    except Exception as e:
        print(f"[WARN] Błąd inicjalizacji pamięci: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    print("\n[INFO] Shutting down Mordzix AI...")

# ────────────────────────────────────────────────────────────────────
# METRICS (fallback safe)
# ────────────────────────────────────────────────────────────────────
@app.get('/metrics', include_in_schema=False)
def _metrics():
    return metrics_endpoint()

# ────────────────────────────────────────────────────────────────────
# AUTO ROUTERS + HOTFIX BOOTSTRAP (idempotent)
# ────────────────────────────────────────────────────────────────────
try:
    from .auto_router_loader import attach_all_routers  # type: ignore
    attach_all_routers(app)
except Exception as e:
    print(f"[AUTO_ROUTERS] [FAIL] Nie udalo sie podpiac wszystkich routerow: {e}")

try:
    from core.hotfix_bootstrap import register as _hotfix_register  # type: ignore
    @app.on_event("startup")
    async def _hotfix_mount():
        try:
            _hotfix_register(app)
        except Exception as e:
            print("[HOTFIX] register failed:", e)
except Exception as e:
    print("[HOTFIX] import failed:", e)

# ────────────────────────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        import uvicorn  # type: ignore
    except Exception:
        raise RuntimeError("Uvicorn nie jest zainstalowany. Uruchom: pip install uvicorn")
    import argparse
    parser = argparse.ArgumentParser(description='Mordzix AI Server')
    parser.add_argument('-p', '--port', type=int, default=8080, help='Port (default: 8080)')
    parser.add_argument('-H', '--host', default="0.0.0.0", help='Host (default: 0.0.0.0)')
    parser.add_argument('--reload', action='store_true', help='Auto-reload on code changes')
    args = parser.parse_args()
    print(f"\n[INFO] Starting server on http://{args.host}:{args.port}")
    print(f"[INFO] API Docs: http://localhost:{args.port}/docs")
    print(f"[INFO] Frontend: http://localhost:{args.port}/\n")
    uvicorn.run("core.app:app", host=args.host, port=args.port, reload=args.reload, log_level="info")

app.include_router(meta_router)
