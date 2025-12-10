#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MORDZIX - Media Endpoints (TTS + Image Generation)

Endpoints:
- POST /api/tts/speak - Text to speech
- GET /api/tts/voices - Available voices
- POST /api/images/generate - Generate image
- GET /api/images/{filename} - Serve generated image
- GET /api/images/list - List generated images
"""

import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel, Field

from .helpers import log_info, log_error
from .config import BASE_DIR

router = APIRouter()

# Auth configuration
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "__CHANGE_ME_AUTH_TOKEN__")


def _simple_auth(req: Request):
    """Simple token auth matching other endpoints."""
    auth_header = req.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")
    
    token = auth_header[7:]
    if token != AUTH_TOKEN:
        raise HTTPException(401, "Invalid token")
    
    return True


# ============================================================================
# MODELS
# ============================================================================

class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    voice: str = Field(default="adam")


class ImageRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    negative_prompt: str = Field(default="")
    width: int = Field(default=1024, ge=512, le=1536)
    height: int = Field(default=1024, ge=512, le=1536)
    style: Optional[str] = Field(default=None)


# ============================================================================
# TTS ENDPOINTS
# ============================================================================

@router.post("/tts/speak")
async def api_tts_speak(body: TTSRequest, req: Request, _=Depends(_simple_auth)):
    """
    Convert text to speech.
    Returns MP3 audio.
    """
    from .tts_engine import text_to_speech, is_tts_available
    
    if not is_tts_available():
        raise HTTPException(503, "TTS not configured (missing ELEVENLABS_API_KEY)")
    
    result = await text_to_speech(body.text, body.voice)
    
    if not result.get("ok"):
        raise HTTPException(500, f"TTS failed: {result.get('error')}")
    
    return Response(
        content=result["audio"],
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": "inline; filename=speech.mp3",
            "X-Cached": str(result.get("cached", False))
        }
    )


@router.get("/tts/voices")
async def api_tts_voices(_=Depends(_simple_auth)):
    """Get available TTS voices."""
    from .tts_engine import get_available_voices, is_tts_available
    
    return {
        "ok": True,
        "available": is_tts_available(),
        "voices": await get_available_voices()
    }


# ============================================================================
# IMAGE GENERATION ENDPOINTS
# ============================================================================

@router.post("/images/generate")
async def api_generate_image(body: ImageRequest, req: Request, _=Depends(_simple_auth)):
    """
    Generate image from prompt.
    Returns image URL.
    """
    from .image_generator import generate_image, is_image_gen_available
    
    if not is_image_gen_available():
        raise HTTPException(503, "Image generation not configured")
    
    log_info(f"[IMG_GEN] Generating: {body.prompt[:50]}...")
    
    result = await generate_image(
        prompt=body.prompt,
        negative_prompt=body.negative_prompt,
        width=body.width,
        height=body.height,
        style=body.style
    )
    
    if not result.get("ok"):
        raise HTTPException(500, f"Image generation failed: {result.get('error')}")
    
    return {
        "ok": True,
        "url": result.get("url"),
        "seed": result.get("seed"),
        "cached": result.get("cached", False)
    }


@router.get("/images/{filename}")
async def api_serve_image(filename: str, _=Depends(_simple_auth)):
    """Serve generated image."""
    from .image_generator import IMAGES_DIR
    
    # Sanitize filename
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(400, "Invalid filename")
    
    filepath = IMAGES_DIR / filename
    
    if not filepath.exists():
        raise HTTPException(404, "Image not found")
    
    return FileResponse(
        filepath,
        media_type="image/png",
        filename=filename
    )


@router.get("/images/list")
async def api_list_images(limit: int = 20, _=Depends(_simple_auth)):
    """List recently generated images."""
    from .image_generator import get_generated_images
    
    images = get_generated_images(limit=limit)
    
    return {
        "ok": True,
        "count": len(images),
        "images": images
    }


# ============================================================================
# MEDIA STATUS
# ============================================================================

@router.get("/media/status")
async def api_media_status(_=Depends(_simple_auth)):
    """Get status of all media services."""
    from .tts_engine import is_tts_available
    from .image_generator import is_image_gen_available
    
    return {
        "ok": True,
        "tts": {
            "available": is_tts_available(),
            "provider": "elevenlabs" if is_tts_available() else None
        },
        "image_generation": {
            "available": is_image_gen_available(),
            "provider": "stability" if os.getenv("STABILITY_API_KEY") else (
                "replicate" if os.getenv("REPLICATE_API_KEY") else None
            )
        }
    }
