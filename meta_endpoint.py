# -*- coding: utf-8 -*-
"""
META endpoint (full fat) – zarządzanie dziennikami i feedbackiem:
- /api/meta/status         – stan plików *.jsonl
- /api/meta/append         – dopisz rekord do memory_meta.jsonl
- /api/meta/sample         – ostatnie N linii (tail)
- /api/meta/stats          – statystyki, top tematy, ostatnie wpisy
- /api/meta/compact        – deduplikacja + kompaktowanie
- /api/meta/rotate         – rotacja po progu rozmiaru
- /api/meta/clear          – backup + wyczyszczenie pliku
- /api/meta/download       – pobierz plik
- /api/meta/diary/append   – dopisz wpis do agent_diary.jsonl
- /api/meta/whoami         – szybki /whoami profil użytkownika (styl, tematy, sugestie)
Nie wymaga żadnych zewnętrznych importów poza FastAPI/Pydantic (standard w projekcie).
"""

from __future__ import annotations
from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Iterable, Tuple
from pathlib import Path
import json, time, os, io, gzip, hashlib, re, threading

router = APIRouter(prefix="/api/meta", tags=["meta"])

# ────────────────────────────────────────────────────────────────────────────────
# ŚCIEŻKI
# repo root = katalog wyżej niż core/
REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR   = Path(os.getenv("OUT_DIR", str(REPO_ROOT / "out")))
OUT_DIR.mkdir(parents=True, exist_ok=True)

META_PATH  = Path(os.getenv("META_PATH",  str(OUT_DIR / "memory_meta.jsonl")))
DIARY_PATH = Path(os.getenv("AGENT_DIARY_PATH", str(OUT_DIR / "agent_diary.jsonl")))
for p in (META_PATH, DIARY_PATH):
    if not p.exists():
        p.touch()

# Prosty globalny lock do zapisu (unikamy dodatkowych zależności)
_WRITE_LOCK = threading.Lock()

# ────────────────────────────────────────────────────────────────────────────────
# MODELE
class MetaRecord(BaseModel):
    kind: str = Field(..., description="np. user_feedback, auto_eval, system_note")
    ts: int = Field(default_factory=lambda: int(time.time()))
    user_id: str = Field(..., min_length=1)
    question: Optional[str] = None
    bad_answer: Optional[str] = None
    better_answer: Optional[str] = None
    critique: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)

class DiaryRecord(BaseModel):
    ts: int = Field(default_factory=lambda: int(time.time()))
    session_id: Optional[str] = None
    stage: str = Field(..., description="np. generate, critique, improve, auto-adapt")
    note: str
    eval_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    meta: Dict[str, Any] = Field(default_factory=dict)

# ────────────────────────────────────────────────────────────────────────────────
# UTILS
def _append_jsonl(path: Path, data: Dict[str, Any]) -> None:
    line = json.dumps(data, ensure_ascii=False) + "\n"
    with _WRITE_LOCK:
        with path.open("a", encoding="utf-8") as f:
            f.write(line)

def _tail_lines(path: Path, limit: int) -> Iterable[str]:
    """Szybki tail: czytamy od końca blokami."""
    if limit <= 0 or not path.exists():
        return []
    chunk = 64 * 1024
    size = path.stat().st_size
    buf = b""
    with path.open("rb") as f:
        pos = size
        while pos > 0 and len(buf.splitlines()) <= limit:
            read = min(chunk, pos)
            pos -= read
            f.seek(pos)
            buf = f.read(read) + buf
    lines = buf.splitlines()[-limit:]
    for b in lines:
        try:
            yield b.decode("utf-8", errors="ignore")
        except Exception:
            continue

def _fingerprint(obj: Dict[str, Any]) -> str:
    keys = ["kind", "user_id", "question", "bad_answer", "better_answer", "critique"]
    base = "||".join(str(obj.get(k, "")).strip() for k in keys)
    return hashlib.sha1(base.encode("utf-8")).hexdigest()

_PL_STOP = set("""
i w z na do że a o po u od za dla jak czy oraz albo być mieć ten ta to te tym tymi tych
""".split())

def _extract_tokens(text: str, limit: int = 8) -> List[str]:
    toks = re.findall(r"[a-zA-ZąćęłńóśżźĄĆĘŁŃÓŚŻŹ0-9]+", (text or "").lower())
    toks = [t for t in toks if t not in _PL_STOP and len(t) > 2]
    return toks[:limit]

# ────────────────────────────────────────────────────────────────────────────────
# ENDPOINTY
@router.get("/status", summary="Status plików meta/diary")
def meta_status() -> Dict[str, Any]:
    def stat(path: Path) -> Dict[str, Any]:
        try:
            st = path.stat()
            return {
                "exists": True,
                "path": str(path),
                "size": st.st_size,
                "mtime": st.st_mtime,
            }
        except FileNotFoundError:
            return {"exists": False, "path": str(path)}
    return {
        "ok": True,
        "meta": stat(META_PATH),
        "diary": stat(DIARY_PATH),
    }

@router.post("/append", summary="Dopisz rekord do memory_meta.jsonl")
def meta_append(rec: MetaRecord) -> Dict[str, Any]:
    obj = rec.dict()
    obj["_fp"] = _fingerprint(obj)
    _append_jsonl(META_PATH, obj)
    return {"ok": True, "written": True, "path": str(META_PATH)}

@router.get("/sample", summary="Ostatnie N linii (tail)")
def meta_sample(limit: int = Query(50, ge=1, le=5000)) -> StreamingResponse:
    lines = list(_tail_lines(META_PATH, limit))
    payload = "\n".join(lines) + ("\n" if lines else "")
    return StreamingResponse(io.StringIO(payload), media_type="application/x-ndjson")

@router.get("/download", summary="Pobierz surowy plik memory_meta.jsonl")
def meta_download() -> FileResponse:
    if not META_PATH.exists():
        raise HTTPException(404, "file not found")
    return FileResponse(str(META_PATH), filename="memory_meta.jsonl", media_type="application/octet-stream")

@router.post("/compact", summary="Deduplikacja i kompaktowanie")
def meta_compact(dedupe: bool = True) -> Dict[str, Any]:
    if not META_PATH.exists():
        return {"ok": True, "compacted": False, "reason": "no_file"}
    seen = set()
    kept = 0
    tmp = META_PATH.with_suffix(".jsonl.tmp")
    with _WRITE_LOCK:
        with META_PATH.open("r", encoding="utf-8") as src, tmp.open("w", encoding="utf-8") as dst:
            for line in src:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                fp = obj.get("_fp") or _fingerprint(obj)
                if dedupe and fp in seen:
                    continue
                seen.add(fp)
                dst.write(json.dumps({**obj, "_fp": fp}, ensure_ascii=False) + "\n")
                kept += 1
        tmp.replace(META_PATH)
    return {"ok": True, "compacted": True, "kept": kept}

@router.post("/rotate", summary="Rotuj gdy przekroczony rozmiar")
def meta_rotate(max_bytes: Optional[int] = Query(None, ge=1024), default_threshold: int = 1024*1024*25) -> Dict[str, Any]:
    threshold = max_bytes or default_threshold
    if not META_PATH.exists():
        return {"ok": True, "rotated": False, "reason": "no_file"}
    st = META_PATH.stat()
    if st.st_size < threshold:
        return {"ok": True, "rotated": False, "size": st.st_size, "threshold": threshold}
    dst = META_PATH.with_name(f"{META_PATH.stem}.{int(time.time())}.ndjson")
    with _WRITE_LOCK:
        META_PATH.replace(dst)
        META_PATH.touch()
    return {"ok": True, "rotated": True, "old_path": str(dst), "new_path": str(META_PATH), "old_size": st.st_size, "threshold": threshold}

@router.delete("/clear", summary="Backup + wyczyszczenie pliku")
def meta_clear(backup: bool = True) -> Dict[str, Any]:
    if not META_PATH.exists():
        return {"ok": True, "cleared": False, "reason": "no_file"}
    info: Dict[str, Any] = {"ok": True}
    with _WRITE_LOCK:
        if backup and META_PATH.stat().st_size > 0:
            bpath = META_PATH.with_suffix(f".{int(time.time())}.bak.gz")
            with META_PATH.open("rb") as src, gzip.open(bpath, "wb") as dst:
                dst.write(src.read())
            info["backup"] = str(bpath)
        META_PATH.write_text("", encoding="utf-8")
    info["cleared"] = True
    return info

@router.get("/stats", summary="Statystyki + top tematy")
def meta_stats(limit_tail: int = Query(5000, ge=10, le=200000)) -> Dict[str, Any]:
    cnt = 0
    by_kind: Dict[str, int] = {}
    by_user: Dict[str, int] = {}
    topics: Dict[str, int] = {}
    last_entries: List[Dict[str, Any]] = []

    for line in _tail_lines(META_PATH, limit_tail):
        try:
            obj = json.loads(line)
        except Exception:
            continue
        cnt += 1
        k = str(obj.get("kind") or "unknown")
        u = str(obj.get("user_id") or "unknown")
        by_kind[k] = by_kind.get(k, 0) + 1
        by_user[u] = by_user.get(u, 0) + 1
        q = obj.get("question") or ""
        for t in _extract_tokens(q, limit=12):
            topics[t] = topics.get(t, 0) + 1
        last_entries.append({
            "ts": obj.get("ts"),
            "user_id": u,
            "kind": k,
            "q": (q[:160] + "…") if len(q) > 160 else q
        })
    last_entries = last_entries[-50:]
    top = lambda d, n=20: sorted(d.items(), key=lambda x: (-x[1], x[0]))[:n]
    return {
        "ok": True,
        "lines": cnt,
        "by_kind": top(by_kind),
        "by_user": top(by_user),
        "topics": top(topics),
        "last": last_entries,
        "path": str(META_PATH),
    }

# ────────────────────────────────────────────────────────────────────────────────
# AGENT DIARY
@router.post("/diary/append", summary="Dopisz wpis do dziennika agenta")
def diary_append(rec: DiaryRecord) -> Dict[str, Any]:
    _append_jsonl(DIARY_PATH, rec.dict())
    return {"ok": True, "written": True, "path": str(DIARY_PATH)}

# ────────────────────────────────────────────────────────────────────────────────
# WHOAMI / PROFILE (lekka wersja na podstawie meta + diary)
@router.get("/whoami", summary="Szybki profil użytkownika na podstawie meta/diary")
def whoami(user_id: str = Query(..., min_length=1), lookback: int = Query(10000, ge=10, le=200000)) -> Dict[str, Any]:
    topics: Dict[str, int] = {}
    learned: int = 0
    recs: List[str] = []
    style = "neutral"

    # analizujemy meta
    for line in _tail_lines(META_PATH, lookback):
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get("user_id") != user_id:
            continue
        q = obj.get("question") or ""
        for t in _extract_tokens(q, limit=12):
            topics[t] = topics.get(t, 0) + 1
        if obj.get("better_answer") or obj.get("critique"):
            learned += 1

    # heurystyka stylu: jeśli w pytaniach dużo CAPS lub !, to "direct"
    caps = sum(1 for t, n in topics.items() if t.isupper())
    style = "direct" if caps > 0 else "neutral"

    # proste sugestie
    if learned > 0 and sum(topics.values()) > 5:
        recs.append("Kontynuuj feedback (critique + better_answer) – poprawia trafność.")
    if sum(topics.values()) > 10:
        recs.append("Warto dodać przykłady/kontrprzykłady, żeby agent lepiej się dopasował.")
    if not recs:
        recs.append("Dostarczaj krótkie, konkretne pytania – agent szybciej trafia w intencję.")

    top_topics = sorted(topics.items(), key=lambda x: -x[1])[:15]
    return {
        "ok": True,
        "user_id": user_id,
        "style": style,
        "top_topics": top_topics,
        "learned_events": learned,
        "suggestions": recs
    }
