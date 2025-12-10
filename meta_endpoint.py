from __future__ import annotations

import json
import os
import re
import time
import hashlib
import shutil
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter(prefix="/api/meta", tags=["meta"])

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = Path(os.getenv("WORKSPACE", str(ROOT)))
STATE_DIR = WORKSPACE / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)

META_FILE = WORKSPACE / "meta.ndjson"
META_FILE.touch(exist_ok=True)

LOG_FILE = WORKSPACE / "server.log"
MEM_DB = Path(os.getenv("MEM_DB", str(ROOT / "mem.db")))

SENSITIVE_PAT = re.compile(
    r"(api[_-]?key|token|secret|password|pwd|bearer|authorization|x-.*-token)",
    re.I,
)

def _safe_env() -> Dict[str, str]:
    out: Dict[str, str] = {}
    for k, v in os.environ.items():
        if SENSITIVE_PAT.search(k):
            continue
        if len(v) > 400:
            v = v[:400] + "…"
        out[k] = v
    return dict(sorted(out.items()))

def _tail(path: Path, max_lines: int = 200) -> List[str]:
    if not path.exists():
        return []
    max_lines = max(1, min(max_lines, 5000))
    with path.open("rb") as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        block = 4096
        data = b""
        while size > 0 and data.count(b"\n") <= max_lines:
            step = min(block, size)
            size -= step
            f.seek(size)
            data = f.read(step) + data
        lines = data.splitlines()[-max_lines:]
        return [line.decode("utf-8", "replace") for line in lines]

def _ndjson_count(path: Path) -> int:
    if not path.exists():
        return 0
    n = 0
    with path.open("rb") as f:
        for _ in f:
            n += 1
    return n

def _sqlite_count(db: Path, table: str) -> Optional[int]:
    if not db.exists():
        return None
    try:
        conn = sqlite3.connect(str(db))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) as c FROM {table}")
        r = cur.fetchone()
        conn.close()
        return int(r["c"]) if r and "c" in r.keys() else None
    except Exception:
        return None

def _disk_usage(path: Path) -> Dict[str, Any]:
    try:
        total, used, free = shutil.disk_usage(str(path))
        return {"total": total, "used": used, "free": free}
    except Exception:
        return {"total": None, "used": None, "free": None}

@router.get("/info", summary="Podstawowe info o instancji")
def meta_info() -> Dict[str, Any]:
    return {
        "ok": True,
        "workspace": str(WORKSPACE),
        "root": str(ROOT),
        "meta_file": str(META_FILE),
        "log_file": str(LOG_FILE),
        "mem_db": str(MEM_DB),
        "pid": os.getpid(),
        "time": time.time(),
    }

@router.get("/env", summary="Bezpieczny snapshot ENV (bez sekretów)")
def meta_env() -> Dict[str, Any]:
    return {"ok": True, "env": _safe_env()}

@router.get("/stats", summary="Statystyki: meta.ndjson, mem.db, dysk")
def meta_stats() -> Dict[str, Any]:
    mem_counts = {}
    for table in ("memories", "facts", "episodes"):
        c = _sqlite_count(MEM_DB, table)
        if c is not None:
            mem_counts[table] = c
    return {
        "ok": True,
        "meta_file": {
            "path": str(META_FILE),
            "lines": _ndjson_count(META_FILE),
            "size": META_FILE.stat().st_size if META_FILE.exists() else 0,
        },
        "mem_db": {"path": str(MEM_DB), "tables": mem_counts},
        "disk": _disk_usage(WORKSPACE),
        "loadavg": os.getloadavg() if hasattr(os, "getloadavg") else None,
        "pid": os.getpid(),
        "time": time.time(),
    }

@router.get("/routers", summary="Lista zarejestrowanych tras")
def meta_routers(request: Request) -> Dict[str, Any]:
    routes = []
    seen = set()
    for r in request.app.routes:
        path = getattr(r, "path", None)
        methods = sorted([m for m in getattr(r, "methods", set()) if m not in {"HEAD", "OPTIONS"}])
        name = getattr(r, "name", "")
        if not path:
            continue
        key = (path, tuple(methods))
        if key in seen:
            continue
        routes.append(
            {"path": path, "methods": methods, "name": name, "tags": list(getattr(r, "tags", []) or [])}
        )
        seen.add(key)
    routes.sort(key=lambda x: (x["path"], ",".join(x["methods"])))
    return {"ok": True, "count": len(routes), "routes": routes}

@router.get("/logs/tail", summary="Tail logów/mety")
def meta_logs_tail(
    which: str = Query("meta", regex="^(meta|server)$"),
    lines: int = Query(200, ge=1, le=5000),
) -> Dict[str, Any]:
    path = META_FILE if which == "meta" else LOG_FILE
    return {"ok": True, "file": str(path), "lines": lines, "tail": _tail(path, lines)}

@router.post("/logs/rotate", summary="Rotacja meta/log")
def meta_logs_rotate(which: str = Query("meta", regex="^(meta|server)$")) -> Dict[str, Any]:
    src = META_FILE if which == "meta" else LOG_FILE
    if not src.exists():
        return {"ok": True, "rotated": False, "reason": "not_found", "file": str(src)}
    ts = time.strftime("%Y%m%d-%H%M%S", time.localtime())
    dst = src.with_name(f"{src.stem}.{ts}{src.suffix}")
    src.replace(dst)
    src.touch()
    return {"ok": True, "rotated": True, "old_path": str(dst), "new_path": str(src)}

@router.post("/compact", summary="Kompakcja + deduplikacja meta.ndjson")
def meta_compact() -> Dict[str, Any]:
    if not META_FILE.exists():
        META_FILE.touch()
        return {"ok": True, "compacted": True, "dedupe": 0, "kept": 0}
    tmp = META_FILE.with_suffix(".tmp")
    seen: set[str] = set()
    kept = 0
    dedupe = 0
    with META_FILE.open("r", encoding="utf-8") as src, tmp.open("w", encoding="utf-8") as dst:
        for line in src:
            s = line.strip()
            if not s:
                continue
            h = hashlib.sha256(s.encode("utf-8")).hexdigest()
            if h in seen:
                dedupe += 1
                continue
            seen.add(h)
            dst.write(s + "\n")
            kept += 1
    tmp.replace(META_FILE)
    return {"ok": True, "compacted": True, "dedupe": dedupe, "kept": kept}

@router.post("/append", summary="Dopisanie rekordu do meta.ndjson")
def meta_append(
    event: str = Query(..., min_length=1, max_length=80),
    payload: Optional[str] = Query(None, description="Dowolny JSON jako string"),
) -> Dict[str, Any]:
    try:
        obj = {"ts": time.time(), "event": event}
        if payload:
            try:
                obj["data"] = json.loads(payload)
            except Exception:
                obj["data_raw"] = payload
        with META_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        return {"ok": True, "written": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dump", summary="Zrzut początkowych i końcowych N linii meta.ndjson")
def meta_dump(head: int = Query(50, ge=1, le=2000), tail: int = Query(50, ge=1, le=2000)) -> Dict[str, Any]:
    if not META_FILE.exists():
        return {"ok": True, "head": [], "tail": []}
    head_lines: List[str] = []
    tail_lines: List[str] = _tail(META_FILE, tail)
    with META_FILE.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= head:
                break
            head_lines.append(line.rstrip("\n"))
    return {"ok": True, "head": head_lines, "tail": tail_lines}
