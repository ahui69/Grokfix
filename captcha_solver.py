#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2Captcha Solver - automatyczne rozwiązywanie captcha
"""

import httpx
import os
import asyncio
from typing import Optional, Dict

async def solve_recaptcha(site_key: str, page_url: str) -> Optional[str]:
    """
    Rozwiązuje reCAPTCHA v2
    
    Args:
        site_key: klucz sitekey z captcha
        page_url: URL strony z captcha
    
    Returns:
        token captcha lub None
    """
    
    api_key = os.getenv('TWOCAPTCHA_API_KEY')
    if not api_key:
        print("❌ Brak TWOCAPTCHA_API_KEY")
        return None
    
    try:
        print(f"🔐 2Captcha: rozwiązuję reCAPTCHA...")
        
        async with httpx.AsyncClient(timeout=120) as client:
            # Submit captcha
            submit_resp = await client.post(
                "https://2captcha.com/in.php",
                data={
                    "key": api_key,
                    "method": "userrecaptcha",
                    "googlekey": site_key,
                    "pageurl": page_url,
                    "json": 1
                }
            )
            
            if submit_resp.status_code != 200:
                print(f"❌ Submit failed: {submit_resp.status_code}")
                return None
            
            result = submit_resp.json()
            if result.get('status') != 1:
                print(f"❌ Submit error: {result}")
                return None
            
            captcha_id = result.get('request')
            print(f"📝 Captcha ID: {captcha_id}")
            
            # Poll for result (max 2 min)
            for i in range(40):
                await asyncio.sleep(3)
                
                get_resp = await client.get(
                    f"https://2captcha.com/res.php?key={api_key}&action=get&id={captcha_id}&json=1"
                )
                
                if get_resp.status_code != 200:
                    continue
                
                data = get_resp.json()
                
                if data.get('status') == 1:
                    token = data.get('request')
                    print(f"✅ 2Captcha OK: {token[:50]}...")
                    return token
                elif data.get('request') == 'CAPCHA_NOT_READY':
                    print(f"⏳ Czekam... ({i+1}/40)")
                    continue
                else:
                    print(f"❌ Error: {data}")
                    return None
            
            print("❌ Timeout")
            return None
                
    except Exception as e:
        print(f"❌ 2Captcha error: {e}")
        return None


async def solve_hcaptcha(site_key: str, page_url: str) -> Optional[str]:
    """Rozwiązuje hCaptcha"""
    api_key = os.getenv('TWOCAPTCHA_API_KEY')
    if not api_key:
        return None
    
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            submit_resp = await client.post(
                "https://2captcha.com/in.php",
                data={
                    "key": api_key,
                    "method": "hcaptcha",
                    "sitekey": site_key,
                    "pageurl": page_url,
                    "json": 1
                }
            )
            
            if submit_resp.status_code != 200:
                return None
            
            result = submit_resp.json()
            if result.get('status') != 1:
                return None
            
            captcha_id = result.get('request')
            
            for i in range(40):
                await asyncio.sleep(3)
                get_resp = await client.get(
                    f"https://2captcha.com/res.php?key={api_key}&action=get&id={captcha_id}&json=1"
                )
                
                if get_resp.status_code == 200:
                    data = get_resp.json()
                    if data.get('status') == 1:
                        return data.get('request')
            
            return None
    except:
        return None
