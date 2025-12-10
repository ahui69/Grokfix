#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MORDZIX - Image Generation Engine

Stability AI (SDXL) + Replicate fallback for image generation.
"""

import os
import asyncio
import httpx
import hashlib
import base64
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

from .helpers import log_info, log_warning, log_error
from .config import BASE_DIR

# Config
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY", "")
REPLICATE_API_KEY = os.getenv("REPLICATE_API_KEY", "")
STABILITY_ENGINE = os.getenv("STABILITY_ENGINE", "stable-diffusion-xl-1024-v1-0")

STABILITY_BASE_URL = "https://api.stability.ai/v1"
REPLICATE_BASE_URL = "https://api.replicate.com/v1"

# Output directory
IMAGES_DIR = Path(BASE_DIR) / "data" / "generated_images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)


async def generate_image_stability(
    prompt: str,
    negative_prompt: str = "",
    width: int = 1024,
    height: int = 1024,
    steps: int = 30,
    cfg_scale: float = 7.0,
    style_preset: str = None,
) -> Dict[str, Any]:
    """
    Generate image using Stability AI (SDXL).
    
    Args:
        prompt: Image description
        negative_prompt: What to avoid
        width: Image width (512-1024)
        height: Image height (512-1024)
        steps: Generation steps (10-50)
        cfg_scale: Prompt adherence (1-35)
        style_preset: Style (photographic, anime, digital-art, etc.)
    
    Returns:
        {
            "ok": bool,
            "image": bytes,
            "url": str (local path),
            "seed": int,
            "error": str (if failed)
        }
    """
    if not STABILITY_API_KEY:
        return {"ok": False, "error": "no_stability_api_key", "image": None}
    
    url = f"{STABILITY_BASE_URL}/generation/{STABILITY_ENGINE}/text-to-image"
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {STABILITY_API_KEY}"
    }
    
    payload = {
        "text_prompts": [
            {"text": prompt, "weight": 1.0}
        ],
        "cfg_scale": cfg_scale,
        "width": width,
        "height": height,
        "steps": steps,
        "samples": 1,
    }
    
    if negative_prompt:
        payload["text_prompts"].append({"text": negative_prompt, "weight": -1.0})
    
    if style_preset:
        payload["style_preset"] = style_preset
    
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code != 200:
                error_text = response.text[:300]
                log_error(f"[IMG_GEN] Stability API error {response.status_code}: {error_text}")
                return {"ok": False, "error": f"api_error_{response.status_code}", "image": None}
            
            data = response.json()
            artifacts = data.get("artifacts", [])
            
            if not artifacts:
                return {"ok": False, "error": "no_artifacts", "image": None}
            
            # Get first image
            artifact = artifacts[0]
            image_b64 = artifact.get("base64")
            seed = artifact.get("seed", 0)
            
            if not image_b64:
                return {"ok": False, "error": "no_image_data", "image": None}
            
            image_bytes = base64.b64decode(image_b64)
            
            # Save to file
            filename = f"{int(time.time())}_{seed}.png"
            filepath = IMAGES_DIR / filename
            filepath.write_bytes(image_bytes)
            
            log_info(f"[IMG_GEN] Generated image: {filename} ({len(image_bytes)} bytes)")
            
            return {
                "ok": True,
                "image": image_bytes,
                "url": f"/api/images/{filename}",
                "filepath": str(filepath),
                "seed": seed,
                "cached": False
            }
            
    except httpx.TimeoutException:
        log_error("[IMG_GEN] Stability timeout")
        return {"ok": False, "error": "timeout", "image": None}
    except Exception as e:
        log_error(f"[IMG_GEN] Stability error: {e}")
        return {"ok": False, "error": str(e), "image": None}


async def generate_image_replicate(
    prompt: str,
    negative_prompt: str = "",
    width: int = 1024,
    height: int = 1024,
    model: str = "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b"
) -> Dict[str, Any]:
    """
    Generate image using Replicate (fallback).
    """
    if not REPLICATE_API_KEY:
        return {"ok": False, "error": "no_replicate_api_key", "image": None}
    
    url = f"{REPLICATE_BASE_URL}/predictions"
    
    headers = {
        "Authorization": f"Token {REPLICATE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "version": model.split(":")[-1] if ":" in model else model,
        "input": {
            "prompt": prompt,
            "negative_prompt": negative_prompt or "ugly, blurry, low quality",
            "width": width,
            "height": height,
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=180) as client:
            # Start prediction
            response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code not in [200, 201]:
                return {"ok": False, "error": f"api_error_{response.status_code}", "image": None}
            
            prediction = response.json()
            prediction_id = prediction.get("id")
            
            if not prediction_id:
                return {"ok": False, "error": "no_prediction_id", "image": None}
            
            # Poll for result
            for _ in range(60):  # Max 60 attempts (2 min)
                await asyncio.sleep(2)
                
                status_response = await client.get(
                    f"{REPLICATE_BASE_URL}/predictions/{prediction_id}",
                    headers=headers
                )
                
                if status_response.status_code != 200:
                    continue
                
                status_data = status_response.json()
                status = status_data.get("status")
                
                if status == "succeeded":
                    output = status_data.get("output")
                    if output and isinstance(output, list) and len(output) > 0:
                        image_url = output[0]
                        
                        # Download image
                        img_response = await client.get(image_url)
                        if img_response.status_code == 200:
                            image_bytes = img_response.content
                            
                            # Save to file
                            filename = f"{int(time.time())}_replicate.png"
                            filepath = IMAGES_DIR / filename
                            filepath.write_bytes(image_bytes)
                            
                            log_info(f"[IMG_GEN] Replicate generated: {filename}")
                            
                            return {
                                "ok": True,
                                "image": image_bytes,
                                "url": f"/api/images/{filename}",
                                "filepath": str(filepath),
                                "cached": False
                            }
                
                elif status == "failed":
                    error = status_data.get("error", "unknown")
                    return {"ok": False, "error": f"prediction_failed: {error}", "image": None}
            
            return {"ok": False, "error": "timeout_polling", "image": None}
            
    except Exception as e:
        log_error(f"[IMG_GEN] Replicate error: {e}")
        return {"ok": False, "error": str(e), "image": None}


async def generate_image(
    prompt: str,
    negative_prompt: str = "",
    width: int = 1024,
    height: int = 1024,
    style: str = None,
) -> Dict[str, Any]:
    """
    Generate image using best available provider.
    
    Priority:
    1. Stability AI (faster, better quality)
    2. Replicate (fallback)
    """
    # Try Stability first
    if STABILITY_API_KEY:
        result = await generate_image_stability(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            style_preset=style
        )
        if result.get("ok"):
            return result
        log_warning(f"[IMG_GEN] Stability failed, trying Replicate: {result.get('error')}")
    
    # Fallback to Replicate
    if REPLICATE_API_KEY:
        return await generate_image_replicate(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height
        )
    
    return {"ok": False, "error": "no_image_api_configured", "image": None}


def get_generated_images(limit: int = 20) -> List[Dict[str, Any]]:
    """Get list of recently generated images."""
    images = []
    
    for filepath in sorted(IMAGES_DIR.glob("*.png"), key=lambda f: f.stat().st_mtime, reverse=True)[:limit]:
        images.append({
            "filename": filepath.name,
            "url": f"/api/images/{filepath.name}",
            "created_at": filepath.stat().st_mtime,
            "size": filepath.stat().st_size
        })
    
    return images


def is_image_gen_available() -> bool:
    """Check if image generation is configured."""
    return bool(STABILITY_API_KEY or REPLICATE_API_KEY)
