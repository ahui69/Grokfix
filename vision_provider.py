#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vision Provider - uniwersalny wrapper dla różnych Vision API
Próbuje kolejno: OpenAI → Replicate → DeepInfra
"""

import httpx
import os
import asyncio
from typing import Optional, Dict

async def analyze_image_universal(base64_data: str, mime_type: str, filename: str) -> Optional[str]:
    """
    Próbuje przeanalizować obrazek kolejno różnymi providerami
    Zwraca: opis obrazka lub None
    """
    
    # 1. TRY OPENAI GPT-4 VISION (najlepsze, ale płatne)
    try:
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key and not openai_key.endswith('...'):
            print("🔍 Próbuję OpenAI GPT-4 Vision...")
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {openai_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o",
                        "messages": [{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Opisz dokładnie po polsku co widzisz na tym obrazku w 2-3 zdaniach."},
                                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_data}"}}
                            ]
                        }],
                        "max_tokens": 300
                    }
                )
                
                if resp.status_code == 200:
                    result = resp.json()
                    analysis = result['choices'][0]['message']['content']
                    print(f"✅ OpenAI Vision OK")
                    return analysis
    except Exception as e:
        print(f"❌ OpenAI Vision: {e}")
    
    # 2. TRY REPLICATE (llama-3.2-vision)
    try:
        replicate_key = os.getenv('REPLICATE_API_KEY')
        if replicate_key:
            print("🔍 Próbuję Replicate Llama Vision...")
            async with httpx.AsyncClient(timeout=90) as client:
                resp = await client.post(
                    "https://api.replicate.com/v1/models/meta/llama-3.2-11b-vision-instruct/predictions",
                    headers={
                        "Authorization": f"Bearer {replicate_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "input": {
                            "image": f"data:{mime_type};base64,{base64_data}",
                            "prompt": "Describe in Polish what you see in this image in 2-3 sentences."
                        }
                    }
                )
                
                if resp.status_code == 201:
                    result = resp.json()
                    pred_id = result.get('id')
                    
                    # Poll result
                    for _ in range(30):
                        await asyncio.sleep(2)
                        check_resp = await client.get(
                            f"https://api.replicate.com/v1/predictions/{pred_id}",
                            headers={"Authorization": f"Bearer {replicate_key}"}
                        )
                        data = check_resp.json()
                        
                        if data.get('status') == 'succeeded':
                            output = data.get('output', [])
                            analysis = ''.join(output) if isinstance(output, list) else str(output)
                            print(f"✅ Replicate Vision OK")
                            return analysis
                        elif data.get('status') in ['failed', 'canceled']:
                            break
    except Exception as e:
        print(f"❌ Replicate Vision: {e}")
    
    # 3. TRY DEEPINFRA (backup)
    try:
        deepinfra_key = os.getenv('VISION_API_KEY') or os.getenv('LLM_API_KEY')
        if deepinfra_key:
            print("🔍 Próbuję DeepInfra Vision...")
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    "https://api.deepinfra.com/v1/openai/chat/completions",
                    headers={
                        "Authorization": f"Bearer {deepinfra_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "meta-llama/Llama-3.2-11B-Vision-Instruct",
                        "messages": [{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Opisz po polsku co widzisz."},
                                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_data}"}}
                            ]
                        }]
                    }
                )
                
                if resp.status_code == 200:
                    result = resp.json()
                    analysis = result['choices'][0]['message']['content']
                    print(f"✅ DeepInfra Vision OK")
                    return analysis
    except Exception as e:
        print(f"❌ DeepInfra Vision: {e}")
    
    print("❌ Wszystkie Vision API failed")
    return None
