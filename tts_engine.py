#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MORDZIX - Text-to-Speech Engine

ElevenLabs integration for voice output.
"""

import os
import asyncio
import httpx
import hashlib
import time
from pathlib import Path
from typing import Optional, Dict, Any

from .helpers import log_info, log_warning, log_error
from .config import BASE_DIR

# Config
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"
ELEVENLABS_TIMEOUT = 60

# Voice IDs (ElevenLabs)
VOICES = {
    "adam": "pNInz6obpgDQGcFmaJgB",      # Deep male
    "rachel": "21m00Tcm4TlvDq8ikWAM",    # Female
    "domi": "AZnzlk1XvdvUeBnXmlld",      # Female
    "bella": "EXAVITQu4vr4xnSDxMaL",     # Female
    "antoni": "ErXwobaYiN019PkySvjV",    # Male
    "elli": "MF3mGyEYCl7XYWbV9V6O",      # Female
    "josh": "TxGEqnHWrfWFTfGW9XjX",      # Male
    "arnold": "VR6AewLTigWG4xSOukaG",    # Male
    "sam": "yoZ06aMxZJJ28mfd3POQ",       # Male
}

DEFAULT_VOICE = "adam"

# Cache for generated audio
TTS_CACHE_DIR = Path(BASE_DIR) / "data" / "tts_cache"
TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_TTL = 86400 * 7  # 7 days


def _cache_key(text: str, voice: str) -> str:
    """Generate cache key for text+voice combo."""
    return hashlib.md5(f"{voice}:{text}".encode()).hexdigest()


def _get_cached_audio(text: str, voice: str) -> Optional[bytes]:
    """Get cached audio if exists and not expired."""
    key = _cache_key(text, voice)
    cache_file = TTS_CACHE_DIR / f"{key}.mp3"
    
    if cache_file.exists():
        # Check age
        age = time.time() - cache_file.stat().st_mtime
        if age < CACHE_TTL:
            return cache_file.read_bytes()
        else:
            cache_file.unlink()  # Delete expired
    
    return None


def _save_to_cache(text: str, voice: str, audio: bytes):
    """Save audio to cache."""
    key = _cache_key(text, voice)
    cache_file = TTS_CACHE_DIR / f"{key}.mp3"
    cache_file.write_bytes(audio)
    
    # Cleanup old cache files (keep max 100)
    cache_files = sorted(TTS_CACHE_DIR.glob("*.mp3"), key=lambda f: f.stat().st_mtime)
    if len(cache_files) > 100:
        for f in cache_files[:-100]:
            f.unlink()


async def text_to_speech(
    text: str,
    voice: str = DEFAULT_VOICE,
    model: str = "eleven_multilingual_v2",
    stability: float = 0.5,
    similarity_boost: float = 0.75,
) -> Dict[str, Any]:
    """
    Convert text to speech using ElevenLabs.
    
    Args:
        text: Text to convert (max 5000 chars)
        voice: Voice name or ID
        model: ElevenLabs model
        stability: Voice stability (0-1)
        similarity_boost: Voice similarity (0-1)
    
    Returns:
        {
            "ok": bool,
            "audio": bytes,  # MP3 audio data
            "content_type": "audio/mpeg",
            "cached": bool,
            "error": str (if failed)
        }
    """
    if not ELEVENLABS_API_KEY:
        return {"ok": False, "error": "no_api_key", "audio": None}
    
    # Limit text length
    text = text[:5000]
    
    # Resolve voice ID
    voice_id = VOICES.get(voice.lower(), voice)
    
    # Check cache
    cached_audio = _get_cached_audio(text, voice_id)
    if cached_audio:
        log_info(f"[TTS] Cache HIT for {len(text)} chars")
        return {
            "ok": True,
            "audio": cached_audio,
            "content_type": "audio/mpeg",
            "cached": True
        }
    
    # Call ElevenLabs API
    url = f"{ELEVENLABS_BASE_URL}/text-to-speech/{voice_id}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    
    payload = {
        "text": text,
        "model_id": model,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=ELEVENLABS_TIMEOUT) as client:
            response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code != 200:
                error_text = response.text[:200]
                log_error(f"[TTS] API error {response.status_code}: {error_text}")
                return {"ok": False, "error": f"api_error_{response.status_code}", "audio": None}
            
            audio_data = response.content
            
            # Save to cache
            _save_to_cache(text, voice_id, audio_data)
            
            log_info(f"[TTS] Generated {len(audio_data)} bytes for {len(text)} chars")
            
            return {
                "ok": True,
                "audio": audio_data,
                "content_type": "audio/mpeg",
                "cached": False
            }
            
    except httpx.TimeoutException:
        log_error("[TTS] Timeout")
        return {"ok": False, "error": "timeout", "audio": None}
    except Exception as e:
        log_error(f"[TTS] Error: {e}")
        return {"ok": False, "error": str(e), "audio": None}


async def get_available_voices() -> Dict[str, str]:
    """Get list of available voices."""
    return VOICES.copy()


def is_tts_available() -> bool:
    """Check if TTS is configured."""
    return bool(ELEVENLABS_API_KEY)


# Sync wrapper
def text_to_speech_sync(text: str, voice: str = DEFAULT_VOICE) -> Dict[str, Any]:
    """Synchronous wrapper for text_to_speech."""
    return asyncio.run(text_to_speech(text, voice))
