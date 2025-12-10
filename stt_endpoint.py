"""
MORDZIX AI - Speech-to-Text Endpoint (PHASE 6 - Full Security)

Features:
- File size limit (25MB max)
- Rate limiting
- OpenAI Whisper / HuggingFace fallback
"""

from fastapi import APIRouter, UploadFile, File, Request, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import os, time, uuid, httpx, asyncio, json, mimetypes, shutil, re

from .response_adapter import adapt
from .memory_store import set_pref_lang
from .lang_detect import detect_lang
from .security import security_manager, get_client_ip
from .helpers import log_warning, log_info

router = APIRouter(prefix="/api/stt", tags=["stt"])

# Configuration
WORKSPACE = Path(os.getenv("WORKSPACE", "."))
INBOX = WORKSPACE / "out" / "stt"
INBOX.mkdir(parents=True, exist_ok=True)

HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_STT_MODEL = os.getenv("OPENAI_STT_MODEL", "whisper-1")
HUGGINGFACE_STT_MODEL = os.getenv("HUGGINGFACE_STT_MODEL", "openai/whisper-large-v3")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "__CHANGE_ME_AUTH_TOKEN__")

# Limits
MAX_AUDIO_SIZE = 25 * 1024 * 1024  # 25MB max (OpenAI Whisper limit)
RATE_LIMIT_STT = 30  # 30 transcriptions per hour


def _tenant(req: Request) -> str:
    """Extract tenant ID from request"""
    t = (req.headers.get("X-Tenant-ID") or "default").strip() or "default"
    safe = "".join(ch for ch in t if ch.isalnum() or ch in "-_").lower()
    return safe or "default"


def _auth_with_rate_limit(req: Request):
    """Auth dependency with rate limiting"""
    client_ip = get_client_ip(req)
    endpoint = req.url.path
    
    # Check rate limit
    if not security_manager.check_rate_limit(client_ip, endpoint, RATE_LIMIT_STT):
        log_warning(f"[STT] Rate limit exceeded for {client_ip}")
        raise HTTPException(
            status_code=429, 
            detail="Rate limit exceeded. Please try again later."
        )
    
    # Check auth
    auth_header = req.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip() if auth_header.startswith("Bearer ") else ""
    
    if token != AUTH_TOKEN:
        security_manager.record_failed_attempt(client_ip)
        raise HTTPException(status_code=401, detail="Unauthorized")


def _guess_lang(text: str) -> str:
    """Simple language detection heuristic"""
    t = text.strip()
    if not t:
        return 'und'
    # Polish diacritics
    if re.search(r'[ąćęłńóśźż]', t.lower()):
        return 'pl'
    # Common English words
    if re.search(r'\b(the|and|you|are|is|this|that)\b', t.lower()):
        return 'en'
    return 'pl' if sum(c in 'ąćęłńóśźż' for c in t.lower()) > 0 else 'en'


async def _openai_asr(bytes_data: bytes) -> str:
    """Transcribe audio using OpenAI Whisper API"""
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=400, detail="openai_asr_not_configured")
    
    import aiohttp
    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as session:
        data = aiohttp.FormData()
        data.add_field('file', bytes_data, filename='audio.webm', content_type='audio/webm')
        data.add_field('model', OPENAI_STT_MODEL)
        
        async with session.post(url, headers=headers, data=data) as r:
            if r.status != 200:
                error_text = await r.text()
                log_warning(f"[STT] OpenAI API error: {r.status} - {error_text}")
                raise HTTPException(status_code=502, detail="openai_asr_failed")
            js = await r.json()
            return js.get("text", "")


async def _hf_asr(bytes_data: bytes) -> str:
    """Transcribe audio using HuggingFace Inference API"""
    if not HUGGINGFACE_API_KEY:
        raise HTTPException(status_code=400, detail="hf_asr_not_configured")
    
    url = f"https://api-inference.huggingface.co/models/{HUGGINGFACE_STT_MODEL}"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
    
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(url, headers=headers, content=bytes_data)
        
        # Retry once if model is loading
        if r.status_code == 503:
            await asyncio.sleep(2.0)
            r = await client.post(url, headers=headers, content=bytes_data)
        
        r.raise_for_status()
        
        try:
            js = r.json()
            if isinstance(js, dict) and "text" in js:
                return js["text"]
        except Exception:
            pass
        
        return ""


@router.post("/transcribe")
async def transcribe(req: Request, file: UploadFile = File(...)):
    """
    Transcribe audio file to text.
    
    Supports: webm, mp3, mp4, m4a, wav, ogg
    Max size: 25MB
    
    Returns:
        {text: "transcribed text", language: "pl/en", items: [...]}
    """
    # Auth and rate limit
    _auth_with_rate_limit(req)
    
    tenant = _tenant(req)
    
    # Check file size by reading in chunks
    content = b""
    total_size = 0
    
    while True:
        chunk = await file.read(1024 * 1024)  # 1MB chunks
        if not chunk:
            break
        total_size += len(chunk)
        
        if total_size > MAX_AUDIO_SIZE:
            raise HTTPException(
                status_code=413, 
                detail=f"Audio file too large. Maximum size is {MAX_AUDIO_SIZE // (1024*1024)}MB"
            )
        
        content += chunk
    
    if total_size == 0:
        raise HTTPException(status_code=400, detail="Empty audio file")
    
    # Save file
    ts = time.strftime("%Y%m%d-%H%M%S")
    ext = os.path.splitext(file.filename or "")[1].lower() or ".wav"
    outdir = INBOX / tenant
    outdir.mkdir(parents=True, exist_ok=True)
    fp = outdir / f"{ts}-{uuid.uuid4().hex}{ext}"
    
    with fp.open("wb") as f:
        f.write(content)
    
    log_info(f"[STT] Processing audio file: {fp.name} ({total_size} bytes)")
    
    # Transcribe
    try:
        if OPENAI_API_KEY:
            text = await _openai_asr(content)
        elif HUGGINGFACE_API_KEY:
            text = await _hf_asr(content)
        else:
            raise HTTPException(
                status_code=503, 
                detail="No STT provider configured. Set OPENAI_API_KEY or HUGGINGFACE_API_KEY."
            )
    except HTTPException:
        raise
    except Exception as e:
        log_warning(f"[STT] Transcription error: {e}")
        raise HTTPException(status_code=502, detail=f"Transcription failed: {str(e)}")
    
    if not text:
        raise HTTPException(status_code=502, detail="stt_empty_result")
    
    # Detect language
    lang = detect_lang(text)
    set_pref_lang(tenant, lang)
    
    log_info(f"[STT] Transcribed: {len(text)} chars, lang={lang}")
    
    return adapt({
        "text": text, 
        "sources": [], 
        "language": lang, 
        "items": [{
            "name": fp.name, 
            "url": f"/api/stt/file/{tenant}/{fp.name}", 
            "mime": "audio/*", 
            "size": fp.stat().st_size
        }]
    })


@router.get("/file/{tenant}/{name}")
async def stt_file(req: Request, tenant: str, name: str):
    """
    Download a previously uploaded audio file.
    """
    # Basic auth check (no rate limit for file downloads)
    auth_header = req.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip() if auth_header.startswith("Bearer ") else ""
    
    if token != AUTH_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Sanitize path to prevent directory traversal
    safe_tenant = "".join(ch for ch in tenant if ch.isalnum() or ch in "-_").lower()
    safe_name = "".join(ch for ch in name if ch.isalnum() or ch in "-_.")
    
    fp = INBOX / safe_tenant / safe_name
    
    if not fp.exists():
        raise HTTPException(status_code=404, detail="not_found")
    
    # Verify file is within INBOX directory (prevent path traversal)
    try:
        fp.resolve().relative_to(INBOX.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    
    mt, _ = mimetypes.guess_type(str(fp))
    return FileResponse(fp, media_type=mt or "application/octet-stream", filename=safe_name)
