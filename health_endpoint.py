import os
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

# Root projektu (np. /root/mordzix-ai)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

SESSIONS_DB_PATH = DATA_DIR / "sessions.db"
MEM_DB_PATH = DATA_DIR / "mem.db"
FEEDBACK_DB_PATH = DATA_DIR / "feedback.db"
LEGACY_MEM_DB_PATH = PROJECT_ROOT / "mem.db"


def _check_sqlite_db(name: str, path: Path) -> Dict[str, Any]:
    """Sprawdza pojedynczą bazę sqlite: istnienie, rozmiar, SELECT 1."""
    info: Dict[str, Any] = {
        "name": name,
        "path": str(path),
        "exists": path.exists(),
        "status": "missing",
        "size_bytes": None,
        "details": "",
    }

    if not path.exists():
        info["details"] = "Plik bazy nie istnieje"
        return info

    try:
        info["size_bytes"] = path.stat().st_size
    except Exception as e:  # noqa: BLE001
        info["details"] = f"Nie udało się odczytać rozmiaru: {e!r}"

    try:
        conn = sqlite3.connect(
            f"file:{path}?mode=ro",
            uri=True,
            timeout=2.0,
            isolation_level=None,
        )
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1;")
            _ = cur.fetchone()
        finally:
            conn.close()

        info["status"] = "ok"
        if not info["details"]:
            info["details"] = "Połączenie OK, SELECT 1 działa"
    except Exception as e:  # noqa: BLE001
        info["status"] = "error"
        info["details"] = f"Błąd połączenia / zapytania: {e!r}"

    return info


def _check_redis() -> Dict[str, Any]:
    """Opcjonalny check Redis na podstawie REDIS_URL / REDIS_URL_MAIN."""
    redis_url = os.getenv("REDIS_URL") or os.getenv("REDIS_URL_MAIN")
    info: Dict[str, Any] = {
        "enabled": bool(redis_url),
        "status": "disabled",
        "url": redis_url,
        "details": "",
    }

    if not redis_url:
        info["details"] = "Redis nie skonfigurowany (brak REDIS_URL / REDIS_URL_MAIN)"
        return info

    try:
        import redis  # type: ignore[import-not-found]

        client = redis.Redis.from_url(redis_url, socket_connect_timeout=2)
        pong = client.ping()
        if pong:
            info["status"] = "ok"
            info["details"] = "Redis odpowiedział na PING"
        else:
            info["status"] = "error"
            info["details"] = "Redis nie odpowiedział na PING"
    except Exception as e:  # noqa: BLE001
        info["status"] = "error"
        info["details"] = f"Błąd połączenia z Redis: {e!r}"

    return info


def _check_memory_system() -> Dict[str, Any]:
    """
    Lekki check systemu pamięci:
    - czy moduły się importują (core.memory, core.hierarchical_memory)
    - bez ciężkiego odpalania silnika.
    """
    result: Dict[str, Any] = {
        "status": "unknown",
        "components": {},
    }

    # Unified Memory
    mem_info: Dict[str, Any] = {
        "imported": False,
        "status": "missing",
        "details": "",
    }
    try:
        from core import memory as core_memory  # type: ignore[import-not-found]

        _ = core_memory
        mem_info["imported"] = True
        mem_info["status"] = "ok"
        mem_info["details"] = "Moduł core.memory zaimportowany"
    except Exception as e:  # noqa: BLE001
        mem_info["status"] = "error"
        mem_info["details"] = f"Błąd importu core.memory: {e!r}"

    result["components"]["unified_memory"] = mem_info

    # Hierarchical Memory
    hier_info: Dict[str, Any] = {
        "imported": False,
        "status": "missing",
        "details": "",
    }
    try:
        from core import hierarchical_memory  # type: ignore[import-not-found]

        _ = hierarchical_memory
        hier_info["imported"] = True
        hier_info["status"] = "ok"
        hier_info["details"] = "Moduł core.hierarchical_memory zaimportowany"
    except Exception as e:  # noqa: BLE001
        hier_info["status"] = "error"
        hier_info["details"] = f"Błąd importu core.hierarchical_memory: {e!r}"

    result["components"]["hierarchical_memory"] = hier_info

    statuses = {c["status"] for c in result["components"].values()}
    if "error" in statuses:
        result["status"] = "error"
    elif "ok" in statuses and len(statuses) == 1:
        result["status"] = "ok"
    elif "ok" in statuses and len(statuses) > 1:
        result["status"] = "degraded"
    else:
        result["status"] = "unknown"

    return result


def _aggregate_status(*statuses: str) -> str:
    norm = [s.lower() for s in statuses if isinstance(s, str)]
    if not norm:
        return "unknown"
    if "error" in norm:
        return "error"
    if "degraded" in norm:
        return "degraded"
    if "ok" in norm:
        return "ok"
    return "unknown"


@router.get("/api/health", response_class=JSONResponse)
def health_check() -> JSONResponse:
    """
    Health-check Mordzix AI:
    - SQLite: sessions.db, mem.db, feedback.db (+ legacy mem.db jeśli istnieje)
    - Redis (jeśli skonfigurowany)
    - System pamięci (import modułów)
    """
    db_checks: Dict[str, Any] = {
        "sessions_db": _check_sqlite_db("sessions", SESSIONS_DB_PATH),
        "mem_db": _check_sqlite_db("mem", MEM_DB_PATH),
        "feedback_db": _check_sqlite_db("feedback", FEEDBACK_DB_PATH),
    }

    if LEGACY_MEM_DB_PATH.exists():
        db_checks["legacy_mem_db"] = _check_sqlite_db("legacy_mem", LEGACY_MEM_DB_PATH)

    redis_check = _check_redis()
    memory_check = _check_memory_system()

    db_status = _aggregate_status(*(d["status"] for d in db_checks.values()))
    global_status = _aggregate_status(
        db_status,
        redis_check.get("status", "unknown"),
        memory_check.get("status", "unknown"),
    )

    env_info = {
        "app_env": os.getenv("APP_ENV", "production"),
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        "hostname": os.getenv("HOSTNAME", ""),
        "python_env": os.getenv("VIRTUAL_ENV", ""),
    }

    payload: Dict[str, Any] = {
        "status": global_status,
        "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        "version": "1.0.0",
        "services": {
            "databases": db_checks,
            "redis": redis_check,
            "memory": memory_check,
            "environment": env_info,
        },
    }

    if global_status != "ok":
        logger.warning("Health check status: %s", global_status)

    return JSONResponse(content=payload)
