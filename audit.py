
import os, json, time
from pathlib import Path
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

LOG_DIR = Path(os.getenv("WORKSPACE", ".")) / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_FILE = LOG_DIR / "audit.jsonl"
MAX_BYTES = 5 * 1024 * 1024  # 5MB

def _rotate_if_needed():
    try:
        if AUDIT_FILE.exists() and AUDIT_FILE.stat().st_size > MAX_BYTES:
            ts = time.strftime("%Y%m%d-%H%M%S", time.localtime())
            AUDIT_FILE.rename(LOG_DIR / f"audit-{ts}.jsonl")
    except Exception:
        pass

class AdminAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        # audit tylko /api/admin/*
        path = request.url.path or ""
        if not path.startswith("/api/admin"):
            return await call_next(request)

        start = time.time()
        req_id = request.headers.get("X-Request-ID","n/a")
        ip = request.client.host if request.client else "n/a"
        ua = request.headers.get("User-Agent","n/a")
        auth = request.headers.get("Authorization","")[:16] + "…" if request.headers.get("Authorization") else ""

        response: Response = await call_next(request)
        rec = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "request_id": req_id,
            "ip": ip,
            "method": request.method,
            "path": path,
            "status": response.status_code,
            "ua": ua,
            "auth_present": bool(auth),
            "duration_ms": round((time.time()-start)*1000, 2)
        }
        try:
            _rotate_if_needed()
            with AUDIT_FILE.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            pass
        return response
