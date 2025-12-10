
from fastapi import APIRouter, UploadFile, File, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from typing import List, Dict, Any
from pathlib import Path
import subprocess
import os, shutil, uuid, time, mimetypes

from .response_adapter import adapt

_MAX_SIZE = int(os.getenv('MAX_FILE_SIZE','52428800'))
# Rozszerzona lista dozwolonych typów MIME
_ALLOWED = set([
    'image/', 'video/', 'audio/',  # wszystkie obrazy, wideo, audio
    'application/pdf', 'application/zip', 'application/x-zip-compressed',
    'application/x-rar-compressed', 'application/x-7z-compressed',
    'application/msword', 'application/vnd.openxmlformats-officedocument',
    'application/vnd.ms-excel', 'application/vnd.ms-powerpoint',
    'application/json', 'application/xml', 'application/javascript',
    'text/plain', 'text/html', 'text/css', 'text/csv', 'text/markdown',
    'application/octet-stream'  # fallback dla nieznanych typów
])

try:
    from PIL import Image
    PIL_OK = True
except Exception:
    PIL_OK = False

router = APIRouter(prefix="/api/files", tags=["files"])

WORKSPACE = Path(os.getenv("WORKSPACE", "."))
UPLOADS = WORKSPACE / "uploads"
THUMBS = UPLOADS / "_thumbs"
UPLOADS.mkdir(parents=True, exist_ok=True)
THUMBS.mkdir(parents=True, exist_ok=True)
FFMPEG_THUMBS = os.getenv('FFMPEG_THUMBS','0') in ('1','true','yes','on')
FFMPEG_BIN = os.getenv('FFMPEG_BIN','ffmpeg')

def _tenant(req: Request) -> str:
    t = (req.headers.get("X-Tenant-ID") or "default").strip() or "default"
    safe = "".join(ch for ch in t if ch.isalnum() or ch in "-_").lower()
    return safe or "default"

def _today() -> str:
    return time.strftime("%Y%m%d")

def _save_file(fp: Path, file: UploadFile):
    # chunked copy with limit
    total=0
    with fp.open('wb') as f:
        while True:
            chunk = file.file.read(1024*1024)
            if not chunk: break
            total += len(chunk)
            if total > _MAX_SIZE:
                f.close(); fp.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail='file_too_large')
            f.write(chunk)

    with fp.open("wb") as f:
        shutil.copyfileobj(file.file, f)

def _thumb_for_image(src: Path, dst: Path, max_side: int = 512):
    if not PIL_OK:
        return False
    try:
        with Image.open(src) as im:
            im.thumbnail((max_side, max_side))
            dst.parent.mkdir(parents=True, exist_ok=True)
            # use JPEG for wide compatibility
            im.convert("RGB").save(dst, format="JPEG", quality=85, optimize=True)
        return True
    except Exception:
        return False

def _thumb_for_video(src: Path, dst: Path) -> bool:
    if not FFMPEG_THUMBS:
        return False
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        # grab frame at 1s, high quality jpeg
        cmd = [FFMPEG_BIN, "-y", "-ss", "00:00:01.000", "-i", str(src), "-frames:v", "1", "-q:v", "3", str(dst)]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return dst.exists() and dst.stat().st_size > 0
    except Exception:
        return False


def _meta_for(path: Path) -> Dict[str, Any]:
    mime, _ = mimetypes.guess_type(str(path))
    mime = mime or "application/octet-stream"
    size = path.stat().st_size if path.exists() else 0
    name = path.name
    return {"name": name, "size": size, "mime": mime}

@router.post("/upload")
async def upload(req: Request, files: List[UploadFile] = File(...)):
    tenant = _tenant(req)
    day = _today()
    out_items = []
    base_dir = UPLOADS / tenant / day
    base_dir.mkdir(parents=True, exist_ok=True)

    for uf in files:
        ext = os.path.splitext(uf.filename or "")[1].lower()
        fid = f"{uuid.uuid4().hex}{ext}"
        fp = base_dir / fid
        # mime check pre-save based on filename
        guessed = (mimetypes.guess_type(uf.filename or '')[0] or '').lower()
        if not any(guessed.startswith(p) for p in _ALLOWED):
            raise HTTPException(status_code=415, detail='unsupported_media_type')
        _save_file(fp, uf)
        meta = _meta_for(fp)
        meta["id"] = f"{tenant}/{day}/{fid}"
        meta["url"] = f"/api/files/{meta['id']}"
        meta["thumb_url"] = None

        # thumbnails for images
        if (meta["mime"].startswith("image/")) and PIL_OK:
            thumb_rel = f"{tenant}/{day}/{uuid.uuid4().hex}.jpg"
            tp = THUMBS / thumb_rel
            if _thumb_for_image(fp, tp):
                meta["thumb_url"] = f"/api/files/thumb/{thumb_rel}"

        # video thumbnail via ffmpeg if enabled
        if meta["mime"].startswith("video/"):
            snap_rel = f"{tenant}/{day}/{uuid.uuid4().hex}.jpg"
            stp = THUMBS / snap_rel
            if _thumb_for_video(fp, stp):
                meta["thumb_url"] = f"/api/files/thumb/{snap_rel}"
        # small flags for ui
        meta["kind"] = "image" if meta["mime"].startswith("image/") else "video" if meta["mime"].startswith("video/") else "audio" if meta["mime"].startswith("audio/") else "file"

        out_items.append(meta)

    # zwracamy listę jako {text,sources}+attachments w polu "items"
    return adapt({"text": f"Wgrano {len(out_items)} plik(ów).", "sources": [], "items": out_items})

@router.get("/{tenant}/{day}/{name}")
async def download(tenant: str, day: str, name: str):
    fp = UPLOADS / tenant / day / name
    if not fp.exists():
        raise HTTPException(status_code=404, detail="file_not_found")
    return FileResponse(fp, filename=name)

@router.get("/thumb/{tenant}/{day}/{name}")
async def thumb(tenant: str, day: str, name: str):
    tp = THUMBS / tenant / day / name
    if not tp.exists():
        raise HTTPException(status_code=404, detail="thumb_not_found")
    return FileResponse(tp, filename=name, media_type="image/jpeg")
