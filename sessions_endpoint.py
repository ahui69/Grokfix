"""
MORDZIX AI - Sessions API Endpoint (PHASE 6 - Full Security)

REST API for session management with:
- User ownership validation
- Rate limiting
- Proper error handling
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, List
import os

from .sessions import (
    create_session,
    list_sessions,
    get_session,
    update_session,
    delete_session,
    verify_session_ownership
)
from .security import security_manager, get_client_ip
from .helpers import log_warning

# Auth configuration
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "__CHANGE_ME_AUTH_TOKEN__")

# Rate limits
RATE_LIMIT_SESSIONS_LIST = 60      # 60 requests per hour
RATE_LIMIT_SESSIONS_CREATE = 30    # 30 creates per hour
RATE_LIMIT_SESSIONS_DELETE = 30    # 30 deletes per hour


def _get_user_id(req: Request) -> str:
    """Extract user ID from request (from token or IP)"""
    # In production, this would decode JWT and extract user_id
    # For now, use simple token as user identifier
    auth_header = req.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip() if auth_header.startswith("Bearer ") else ""
    
    # Hash token to create pseudo user_id (same token = same user)
    if token:
        import hashlib
        return hashlib.sha256(token.encode()).hexdigest()[:16]
    
    return "default"


def _auth_with_rate_limit(req: Request, limit: int = 100):
    """Auth dependency with rate limiting"""
    client_ip = get_client_ip(req)
    endpoint = req.url.path
    
    # Check rate limit
    if not security_manager.check_rate_limit(client_ip, endpoint, limit):
        log_warning(f"[SESSIONS] Rate limit exceeded for {client_ip} on {endpoint}")
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
    
    return _get_user_id(req)


router = APIRouter(prefix="/api/sessions", tags=["sessions"])


# =====================================================================
# MODELS
# =====================================================================

class CreateSessionRequest(BaseModel):
    title: Optional[str] = "Nowa rozmowa"


class UpdateSessionRequest(BaseModel):
    title: str


class SessionResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: Optional[int] = 0
    user_id: Optional[str] = None


class SessionDetailResponse(SessionResponse):
    messages: List[dict] = []


class SessionsListResponse(BaseModel):
    sessions: List[SessionResponse]
    total: int


# =====================================================================
# ENDPOINTS
# =====================================================================

@router.get("", response_model=List[SessionResponse])
async def api_list_sessions(
    req: Request,
    limit: int = 50,
    offset: int = 0
):
    """
    List all chat sessions for the authenticated user.
    Only returns sessions owned by the current user.
    
    Query params:
    - limit: Max sessions to return (default 50, max 100)
    - offset: Pagination offset (default 0)
    """
    user_id = _auth_with_rate_limit(req, RATE_LIMIT_SESSIONS_LIST)
    
    # Clamp limit
    limit = min(max(1, limit), 100)
    offset = max(0, offset)
    
    sessions = list_sessions(user_id=user_id, limit=limit, offset=offset)
    return sessions


@router.post("", response_model=SessionResponse)
async def api_create_session(
    req: Request,
    body: CreateSessionRequest = CreateSessionRequest()
):
    """
    Create a new chat session for the authenticated user.
    
    Body (optional):
    - title: Session title (default "Nowa rozmowa")
    """
    user_id = _auth_with_rate_limit(req, RATE_LIMIT_SESSIONS_CREATE)
    
    session = create_session(
        title=body.title or "Nowa rozmowa",
        user_id=user_id
    )
    return session


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def api_get_session(
    req: Request,
    session_id: str
):
    """
    Get a single session with its message history.
    Only returns the session if owned by the current user.
    """
    user_id = _auth_with_rate_limit(req, RATE_LIMIT_SESSIONS_LIST)
    
    # Get session with ownership check
    session = get_session(session_id, user_id=user_id)
    if not session:
        raise HTTPException(
            status_code=404, 
            detail="Session not found or access denied"
        )
    return session


@router.put("/{session_id}", response_model=SessionDetailResponse)
async def api_update_session(
    req: Request,
    session_id: str,
    body: UpdateSessionRequest
):
    """
    Update session title.
    Only works if the session is owned by the current user.
    """
    user_id = _auth_with_rate_limit(req, RATE_LIMIT_SESSIONS_LIST)
    
    # Update with ownership check
    session = update_session(session_id, body.title, user_id=user_id)
    if not session:
        raise HTTPException(
            status_code=404, 
            detail="Session not found or access denied"
        )
    return session


@router.delete("/{session_id}")
async def api_delete_session(
    req: Request,
    session_id: str
):
    """
    Delete a session and all its messages.
    Only works if the session is owned by the current user.
    """
    user_id = _auth_with_rate_limit(req, RATE_LIMIT_SESSIONS_DELETE)
    
    # Delete with ownership check
    deleted = delete_session(session_id, user_id=user_id)
    if not deleted:
        raise HTTPException(
            status_code=404, 
            detail="Session not found or access denied"
        )
    return {"ok": True, "deleted": session_id}
