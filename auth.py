#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Authentication module - Token-based authentication for API
"""

import hmac
from typing import Dict, Any
from fastapi import Request, HTTPException

from .config import AUTH_TOKEN


def check_auth(request: Request) -> bool:
    """
    Check if request has valid authentication token
    
    Args:
        request: FastAPI Request object
        
    Returns:
        bool: True if authenticated, False otherwise
    """
    if not AUTH_TOKEN:
        return True  # No auth required if no token set
        
    auth_header = request.headers.get("authorization", "") or request.headers.get("Authorization", "")
    
    if not auth_header:
        return False
        
    if not auth_header.lower().startswith("bearer "):
        return False
        
    token = auth_header.split(" ", 1)[1].strip() if " " in auth_header else ""
    
    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(token, AUTH_TOKEN)


def auth_dependency(request: Request):
    """
    FastAPI dependency for authentication
    Raises HTTPException(401) if not authenticated
    
    Usage:
        @app.get("/protected", dependencies=[Depends(auth_dependency)])
        async def protected_route():
            return {"message": "You are authenticated"}
    """
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


def extract_token(request: Request) -> str:
    """
    Extract bearer token from request
    
    Args:
        request: FastAPI Request object
        
    Returns:
        str: Token value or empty string
    """
    auth_header = request.headers.get("authorization", "") or request.headers.get("Authorization", "")
    
    if not auth_header or not auth_header.lower().startswith("bearer "):
        return ""
        
    return auth_header.split(" ", 1)[1].strip() if " " in auth_header else ""


def get_ip_address(request: Request) -> str:
    """
    Get client IP address from request (handles proxies)
    
    Args:
        request: FastAPI Request object
        
    Returns:
        str: IP address
    """
    # Check for forwarded IP (when behind proxy/load balancer)
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # X-Forwarded-For can contain multiple IPs, take the first one
        return forwarded.split(",")[0].strip()
    
    # Check for real IP header
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    
    # Fallback to direct client IP
    if request.client:
        return request.client.host
    
    return "0.0.0.0"


# Legacy WSGI-style auth check (for compatibility)
def wsgi_auth_ok(env: Dict[str, Any]) -> bool:
    """
    Check authentication for WSGI environment (legacy)
    
    Args:
        env: WSGI environment dict
        
    Returns:
        bool: True if authenticated
    """
    if not AUTH_TOKEN:
        return True
        
    auth_header = env.get("HTTP_AUTHORIZATION", "")
    if not auth_header.lower().startswith("bearer "):
        return False
        
    token = auth_header.split(" ", 1)[1].strip() if " " in auth_header else ""
    return hmac.compare_digest(token, AUTH_TOKEN)


def wsgi_get_ip(env: Dict[str, Any]) -> str:
    """
    Get IP address from WSGI environment (legacy)
    
    Args:
        env: WSGI environment dict
        
    Returns:
        str: IP address
    """
    return env.get("HTTP_X_FORWARDED_FOR") or env.get("REMOTE_ADDR") or "0.0.0.0"


def verify_token(token: str) -> bool:
    """
    Verify authentication token (legacy compatibility)
    
    Args:
        token: Bearer token to verify
        
    Returns:
        bool: True if valid
    """
    if not AUTH_TOKEN:
        return True
    return hmac.compare_digest(token, AUTH_TOKEN)


async def get_current_user(request: Request) -> Dict[str, Any]:
    """
    Get current user from request (dependency for endpoints)
    
    Args:
        request: FastAPI Request
        
    Returns:
        dict: User info {'user_id': str, 'ip': str, 'authenticated': bool}
    """
    authenticated = check_auth(request)
    return {
        "user_id": "default",
        "ip": get_ip_address(request),
        "authenticated": authenticated
    }
