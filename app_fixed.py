#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MORDZIX AI - Fixed Core Application
Wersja 5.0.1 - Naprawiona architektura
"""

import os
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, List, Any
from collections import Counter

# FastAPI imports
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# ═══════════════════════════════════════════════════════════════════
# KONFIGURACJA ŚRODOWISKA
# ═══════════════════════════════════════════════════════════════════
BASE_DIR = Path(__file__).parent.absolute()
os.environ.setdefault("AUTH_TOKEN", "__CHANGE_ME_AUTH_TOKEN__")
os.environ.setdefault("WORKSPACE", str(BASE_DIR))
os.environ.setdefault("MEM_DB", str(BASE_DIR / "mem.db"))

# Czy logować podczas importu
_SUPPRESS_IMPORT_LOGS = os.environ.get("MORDZIX_SUPPRESS_STARTUP_LOGS") == "1"

# ═══════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def _get_cors_origins() -> List[str]:
    """Pobierz listę dozwolonych CORS origins"""
    raw = os.getenv("CORS_ORIGINS", "").strip()
    if not raw:
        return ["http://localhost:5173", "http://localhost:8080"]
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return parts or ["http://localhost:5173"]


def _req_id_from(request: Request) -> str:
    """Pobierz Request ID z nagłówków lub wygeneruj nowy"""
    rid = request.headers.get("X-Request-ID")
    if not rid and hasattr(request, "state"):
        rid = request.state.__dict__.get("request_id")
    return rid or "n/a"


def _json_error(status: int, code: str, detail, request_id: str):
    """Zwróć standardowy JSON error response"""
    payload = {
        "error": code,
        "code": status,
        "detail": detail,
        "request_id": request_id
    }
    return JSONResponse(status_code=status, content=payload)


# ═══════════════════════════════════════════════════════════════════
# MIDDLEWARE CLASSES
# ═══════════════════════════════════════════════════════════════════

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Dodaje Request ID i mierzy czas odpowiedzi"""
    
    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        start = time.time()
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Response-Time"] = f"{(time.time()-start)*1000:.1f}ms"
        return response


# Rate limiting - proste ograniczenie w pamięci
_RATE_BUCKETS = {}
RL_DISABLE = os.getenv("RL_DISABLE", "0") == "1"
RL_RPM_LIMIT = int(os.getenv("RL_RPM_LIMIT", "100"))


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Proste rate limiting per IP"""
    
    async def dispatch(self, request: Request, call_next):
        if RL_DISABLE:
            return await call_next(request)
        
        try:
            ip = request.client.host if request.client else "unknown"
        except Exception:
            ip = "unknown"
            
        key = f"{ip}:{request.url.path}"
        now = time.time()
        window = int(now // 60)  # per-minute window
        count, win = _RATE_BUCKETS.get(key, (0, window))
        
        if win != window:
            count, win = 0, window
        count += 1
        _RATE_BUCKETS[key] = (count, win)
        
        if count > RL_RPM_LIMIT:
            error_content = '{"error":"rate_limit","detail":"Too Many Requests"}'
            return Response(
                status_code=429,
                content=error_content,
                media_type="application/json"
            )
        
        return await call_next(request)


# ═══════════════════════════════════════════════════════════════════
# FASTAPI APPLICATION
# ═══════════════════════════════════════════════════════════════════

app = FastAPI(
    title="Mordzix AI",
    version="5.0.1",
    description="Zaawansowany system AI z pamięcią, uczeniem i pełną automatyzacją",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ═══════════════════════════════════════════════════════════════════
# EXCEPTION HANDLERS
# ═══════════════════════════════════════════════════════════════════

@app.exception_handler(StarletteHTTPException)
async def http_exc_handler(request: Request, exc: StarletteHTTPException):
    return _json_error(exc.status_code, "http_error", exc.detail, _req_id_from(request))


@app.exception_handler(RequestValidationError)
async def validation_exc_handler(request: Request, exc: RequestValidationError):
    return _json_error(422, "validation_error", exc.errors(), _req_id_from(request))


@app.exception_handler(Exception)
async def unhandled_exc_handler(request: Request, exc: Exception):
    # Nie wyciekaj internals; zwróć ogólny komunikat + typ dla debugowania
    return _json_error(500, "internal_error", {"type": type(exc).__name__}, _req_id_from(request))


# ═══════════════════════════════════════════════════════════════════
# MIDDLEWARE SETUP
# ═══════════════════════════════════════════════════════════════════

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID i timing
app.add_middleware(RequestIDMiddleware)

# Rate limiting
app.add_middleware(RateLimitMiddleware)

# Prometheus middleware (jeśli dostępne)
try:
    from core.metrics import PROMETHEUS_AVAILABLE, record_error, record_request
    
    if PROMETHEUS_AVAILABLE:
        @app.middleware("http")
        async def prometheus_middleware(request: Request, call_next):
            start_time = time.time()
            endpoint = request.url.path
            method = request.method
            status_code = 500
            
            try:
                response = await call_next(request)
                status_code = response.status_code
                return response
            except Exception as exc:
                status_code = getattr(exc, "status_code", 500)
                error_label = exc.__class__.__name__
                record_error(error_label, endpoint)
                raise
            finally:
                duration = time.time() - start_time
                record_request(method, endpoint, status_code, duration)
                
except ImportError:
    if not _SUPPRESS_IMPORT_LOGS:
        print("[WARN] Prometheus metrics nie są dostępne")


# ═══════════════════════════════════════════════════════════════════
# INCLUDE ROUTERS - Wszystkie endpointy
# ═══════════════════════════════════════════════════════════════════

if not _SUPPRESS_IMPORT_LOGS:
    print("\n" + "="*70)
    print("MORDZIX AI - INICJALIZACJA ENDPOINTÓW")
    print("="*70 + "\n")

# Lista endpointów do załadowania
ENDPOINTS_TO_LOAD = [
    # Core endpoints (z folderu core/)
    ("core.frontend_autorouter", "🚀 AutoRouter Frontend", "/api/autoroute/*"),
    ("core.assistant_endpoint", "Assistant endpoint", "/api/chat/*"),
    ("core.psyche_endpoint", "Psyche endpoint", "/api/psyche/*"),
    ("core.travel_endpoint", "Travel endpoint", "/api/travel/*"),
    ("core.suggestions_endpoint", "Suggestions endpoint", "/api/suggestions/*"),
    ("core.cognitive_endpoint", "Cognitive endpoint", "/api/cognitive/*"),
    ("core.memory_endpoint", "Memory endpoint", "/api/memory/*"),
    
    # Root endpoints
    ("programista_endpoint", "Programista endpoint", "/api/code/*"),
    ("files_endpoint", "Files endpoint", "/api/files/*"),
    ("admin_endpoint", "Admin endpoint", "/api/admin/*"),
    ("captcha_endpoint", "Captcha endpoint", "/api/captcha/*"),
    ("prometheus_endpoint", "Prometheus endpoint", "/api/prometheus/*"),
    ("tts_endpoint", "TTS endpoint", "/api/tts/*"),
    ("stt_endpoint", "STT endpoint", "/api/stt/*"),
    ("writing_endpoint", "Writing endpoint", "/api/writing/*"),
    ("batch_endpoint", "Batch endpoint", "/api/batch/*"),
    ("research_endpoint", "Research endpoint", "/api/research/*"),
    ("nlp_endpoint", "NLP endpoint", "/api/nlp/*"),
    ("internal_endpoint", "Internal endpoint", "/api/internal/*"),
]

# Załaduj endpointy
loaded_count = 0
for module_name, display_name, path in ENDPOINTS_TO_LOAD:
    try:
        if module_name.startswith("core."):
            # Import z folderu core
            module = __import__(module_name, fromlist=[module_name.split('.')[-1]])
        else:
            # Import z root directory
            sys.path.insert(0, str(BASE_DIR.parent))
            module = __import__(module_name)
            
        if hasattr(module, 'router'):
            app.include_router(module.router)
            loaded_count += 1
            if not _SUPPRESS_IMPORT_LOGS:
                print(f"✓ {display_name:<20} {path}")
        else:
            if not _SUPPRESS_IMPORT_LOGS:
                print(f"✗ {display_name:<20} - brak atrybutu 'router'")
                
    except Exception as e:
        if not _SUPPRESS_IMPORT_LOGS:
            print(f"✗ {display_name:<20} - {e}")

if not _SUPPRESS_IMPORT_LOGS:
    print(f"\n📊 Załadowano {loaded_count}/{len(ENDPOINTS_TO_LOAD)} endpointów")
    print("="*70 + "\n")


# ═══════════════════════════════════════════════════════════════════
# BASIC ROUTES
# ═══════════════════════════════════════════════════════════════════

@app.get("/api")
@app.get("/status")
async def api_status():
    """Status API"""
    return {
        "ok": True,
        "app": "Mordzix AI",
        "version": "5.0.1",
        "status": "healthy",
        "timestamp": time.time(),
        "features": {
            "auto_stm_to_ltm": True,
            "auto_learning": True,
            "context_injection": True,
            "psyche_system": True,
            "travel_search": True,
            "code_executor": True,
            "tts_stt": True,
            "file_analysis": True
        }
    }


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy", "timestamp": time.time()}


@app.get("/api/endpoints/list")
async def list_endpoints():
    """Lista wszystkich endpointów API"""
    endpoints = []
    seen = set()
    
    for route in app.routes:
        if isinstance(route, APIRoute) and route.path.startswith("/api"):
            methods = sorted([m for m in route.methods if m not in {"HEAD", "OPTIONS"}])
            identifier = (route.path, tuple(methods))
            
            if identifier not in seen:
                endpoints.append({
                    "path": route.path,
                    "methods": methods,
                    "name": route.name,
                    "tags": list(route.tags) if route.tags else [],
                    "summary": route.summary or ""
                })
                seen.add(identifier)
    
    endpoints.sort(key=lambda e: (e["path"], ",".join(e["methods"])))
    return {"ok": True, "count": len(endpoints), "endpoints": endpoints}


# ═══════════════════════════════════════════════════════════════════
# FRONTEND ROUTES
# ═══════════════════════════════════════════════════════════════════

FRONTEND_DIST = BASE_DIR / "frontend" / "dist" / "mordzix-ai"

# Serwowanie statycznych plików z Angular dist/ (tylko jeśli istnieją)
assets_dir = FRONTEND_DIST / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")


@app.get("/", response_class=HTMLResponse)
@app.get("/app", response_class=HTMLResponse)
@app.get("/chat", response_class=HTMLResponse)
async def serve_frontend():
    """Główny interfejs czatu - Angular SPA"""
    # Próbujemy załadować Angular dist
    angular_index = FRONTEND_DIST / "index.html"
    if angular_index.exists():
        return HTMLResponse(content=angular_index.read_text(encoding="utf-8"))
    
    # Fallback: stary index.html (dla dev bez builda)
    fallback_index = BASE_DIR / "index.html"
    if fallback_index.exists():
        return HTMLResponse(content=fallback_index.read_text(encoding="utf-8"))
    
    # Brak frontendu
    return HTMLResponse(
        content="""
        <h1>🚧 Frontend Not Built</h1>
        <p>Run: <code>cd frontend && npm install && npm run build:prod</code></p>
        <p>Or use API directly: <a href="/docs">/docs</a></p>
        """,
        status_code=404
    )


# Catch-all dla Angular routing
@app.get("/{full_path:path}", response_class=HTMLResponse, include_in_schema=False)
async def angular_catch_all(full_path: str):
    """Przekieruj wszystkie nieznane ścieżki do Angular SPA"""
    # Ignoruj ścieżki API
    if full_path.startswith("api/") or full_path.startswith("health"):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    
    # Zwróć Angular index.html
    angular_index = FRONTEND_DIST / "index.html"
    if angular_index.exists():
        return HTMLResponse(content=angular_index.read_text(encoding="utf-8"))
    
    raise HTTPException(status_code=404, detail="Frontend not found")


# PWA Assets
@app.get("/sw.js", include_in_schema=False)
@app.get("/ngsw-worker.js", include_in_schema=False)
async def serve_service_worker():
    """Service worker"""
    candidates = [
        FRONTEND_DIST / "ngsw-worker.js",
        FRONTEND_DIST / "sw.js",
        BASE_DIR / "dist" / "ngsw-worker.js",
        BASE_DIR / "sw.js",
    ]
    for path in candidates:
        if path.exists():
            return FileResponse(path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="service worker not found")


@app.get("/favicon.ico", include_in_schema=False)
async def serve_favicon():
    """Favicon"""
    paths = [
        FRONTEND_DIST / "favicon.ico",
        BASE_DIR / "favicon.ico",
        BASE_DIR / "icons" / "favicon.ico"
    ]
    for path in paths:
        if path.exists():
            return FileResponse(path, media_type="image/x-icon")
    raise HTTPException(status_code=404, detail="favicon not found")


# ═══════════════════════════════════════════════════════════════════
# STARTUP & SHUTDOWN
# ═══════════════════════════════════════════════════════════════════

@app.on_event("startup")
async def startup_event():
    """Inicjalizacja przy starcie"""
    if not _SUPPRESS_IMPORT_LOGS:
        print("\n" + "="*70)
        print("MORDZIX AI - STARTED")
        print("="*70)
        print(f"\n[INFO] Endpoints: http://localhost:8080/docs")
        print(f"[INFO] Frontend:  http://localhost:8080/")
        print(f"[INFO] API:       {len(app.routes)} routes loaded")
        print("="*70 + "\n")
    
    # Inicjalizacja bazy danych i pamięci
    try:
        # Sprawdź czy moduły pamięci istnieją
        try:
            from core.memory import _init_db, load_ltm_to_memory
            _init_db()
            load_ltm_to_memory()
            if not _SUPPRESS_IMPORT_LOGS:
                print("[OK] Pamięć LTM załadowana")
        except ImportError:
            if not _SUPPRESS_IMPORT_LOGS:
                print("[WARN] Moduł core.memory nie znaleziony")
    except Exception as e:
        if not _SUPPRESS_IMPORT_LOGS:
            print(f"[WARN] Błąd inicjalizacji pamięci: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup przy wyłączeniu"""
    if not _SUPPRESS_IMPORT_LOGS:
        print("\n[INFO] Shutting down Mordzix AI...")


# ═══════════════════════════════════════════════════════════════════
# MAIN - Uruchomienie serwera
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    try:
        import uvicorn
    except ImportError:
        raise RuntimeError("Uvicorn nie jest zainstalowany. Uruchom 'pip install uvicorn'")
    
    import argparse
    
    parser = argparse.ArgumentParser(description='Mordzix AI Server')
    parser.add_argument('-p', '--port', type=int, default=8080, help='Port (default: 8080)')
    parser.add_argument('-H', '--host', default="0.0.0.0", help='Host (default: 0.0.0.0)')
    parser.add_argument('--reload', action='store_true', help='Auto-reload on code changes')
    args = parser.parse_args()
    
    print(f"\n[INFO] Starting server on http://{args.host}:{args.port}")
    print(f"[INFO] API Docs: http://localhost:{args.port}/docs")
    print(f"[INFO] Frontend: http://localhost:{args.port}/\n")
    
    uvicorn.run(
        "core.app_fixed:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )