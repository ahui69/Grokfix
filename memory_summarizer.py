#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MORDZIX - Memory Summarization System

Kompresuje stare rozmowy do streszczeń, oszczędzając tokeny.
"""

import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

from .config import DB_PATH
from .helpers import log_info, log_warning, log_error
from .llm import call_llm


# Config
SUMMARIZE_AFTER_MESSAGES = 50  # Summarize sessions with 50+ messages
SUMMARY_MAX_TOKENS = 500  # Max tokens for summary
KEEP_RECENT_MESSAGES = 10  # Keep last N messages unsummarized


async def summarize_text(text: str, max_length: int = 500) -> str:
    """
    Summarize text using LLM.
    """
    try:
        prompt = f"""Streść poniższy tekst w maksymalnie {max_length} znakach.
Zachowaj najważniejsze fakty, decyzje i kontekst.
Pisz zwięźle, bez zbędnych słów.

TEKST:
{text[:8000]}

STRESZCZENIE:"""
        
        result = await asyncio.to_thread(
            call_llm,
            messages=[
                {"role": "system", "content": "Jesteś ekspertem od streszczeń. Pisz zwięźle."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=SUMMARY_MAX_TOKENS
        )
        
        if isinstance(result, dict):
            return result.get("content", result.get("answer", ""))[:max_length]
        return str(result)[:max_length]
        
    except Exception as e:
        log_error(f"[SUMMARIZER] LLM error: {e}")
        # Fallback: just truncate
        return text[:max_length] + "..."


async def summarize_conversation(messages: List[Dict[str, Any]]) -> str:
    """
    Summarize a list of conversation messages.
    """
    # Build conversation text
    conv_text = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")[:1000]  # Limit per message
        conv_text.append(f"{role.upper()}: {content}")
    
    full_text = "\n\n".join(conv_text)
    return await summarize_text(full_text)


def get_sessions_to_summarize() -> List[Dict[str, Any]]:
    """
    Get sessions that need summarization (50+ messages, no summary yet).
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Find sessions with many messages and no summary
        cursor.execute("""
            SELECT s.id, s.title, s.created_at, s.updated_at,
                   COUNT(m.id) as message_count,
                   s.summary
            FROM sessions s
            LEFT JOIN messages m ON s.id = m.session_id
            GROUP BY s.id
            HAVING message_count >= ?
            AND (s.summary IS NULL OR s.summary = '')
            ORDER BY message_count DESC
            LIMIT 10
        """, (SUMMARIZE_AFTER_MESSAGES,))
        
        sessions = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return sessions
        
    except Exception as e:
        log_error(f"[SUMMARIZER] DB error: {e}")
        return []


def get_session_messages_for_summary(session_id: str) -> List[Dict[str, Any]]:
    """
    Get messages from session for summarization (excluding recent ones).
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get all messages except the last KEEP_RECENT_MESSAGES
        cursor.execute("""
            SELECT role, content, created_at
            FROM messages
            WHERE session_id = ?
            ORDER BY created_at ASC
            LIMIT -1 OFFSET 0
        """, (session_id,))
        
        all_messages = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # Return all except last N
        if len(all_messages) > KEEP_RECENT_MESSAGES:
            return all_messages[:-KEEP_RECENT_MESSAGES]
        return []
        
    except Exception as e:
        log_error(f"[SUMMARIZER] DB error: {e}")
        return []


def save_session_summary(session_id: str, summary: str):
    """
    Save summary to session.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Add summary column if not exists
        try:
            cursor.execute("ALTER TABLE sessions ADD COLUMN summary TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        cursor.execute("""
            UPDATE sessions SET summary = ? WHERE id = ?
        """, (summary, session_id))
        
        conn.commit()
        conn.close()
        log_info(f"[SUMMARIZER] Saved summary for session {session_id[:8]}...")
        
    except Exception as e:
        log_error(f"[SUMMARIZER] Save error: {e}")


async def summarize_session(session_id: str) -> Optional[str]:
    """
    Summarize a single session.
    """
    messages = get_session_messages_for_summary(session_id)
    if not messages:
        return None
    
    log_info(f"[SUMMARIZER] Summarizing {len(messages)} messages from session {session_id[:8]}...")
    
    summary = await summarize_conversation(messages)
    if summary:
        save_session_summary(session_id, summary)
    
    return summary


async def run_summarization_batch():
    """
    Run batch summarization for all eligible sessions.
    """
    sessions = get_sessions_to_summarize()
    if not sessions:
        log_info("[SUMMARIZER] No sessions need summarization")
        return {"processed": 0}
    
    log_info(f"[SUMMARIZER] Found {len(sessions)} sessions to summarize")
    
    processed = 0
    for session in sessions:
        try:
            summary = await summarize_session(session["id"])
            if summary:
                processed += 1
        except Exception as e:
            log_error(f"[SUMMARIZER] Error processing session {session['id']}: {e}")
    
    log_info(f"[SUMMARIZER] Processed {processed} sessions")
    return {"processed": processed}


def get_session_with_summary(session_id: str) -> Dict[str, Any]:
    """
    Get session context including summary if available.
    Returns optimized context for LLM.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get session with summary
        cursor.execute("""
            SELECT id, title, summary, created_at, updated_at
            FROM sessions WHERE id = ?
        """, (session_id,))
        
        session = cursor.fetchone()
        if not session:
            conn.close()
            return {}
        
        session_dict = dict(session)
        
        # Get recent messages only
        cursor.execute("""
            SELECT role, content, created_at
            FROM messages
            WHERE session_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (session_id, KEEP_RECENT_MESSAGES))
        
        recent_messages = [dict(row) for row in cursor.fetchall()]
        recent_messages.reverse()  # Chronological order
        
        conn.close()
        
        return {
            "session": session_dict,
            "summary": session_dict.get("summary"),
            "recent_messages": recent_messages,
            "has_summary": bool(session_dict.get("summary"))
        }
        
    except Exception as e:
        log_error(f"[SUMMARIZER] Get session error: {e}")
        return {}


def build_optimized_context(session_id: str) -> List[Dict[str, str]]:
    """
    Build optimized context for LLM using summary + recent messages.
    Saves tokens while preserving context.
    """
    data = get_session_with_summary(session_id)
    if not data:
        return []
    
    context = []
    
    # Add summary as system context if available
    if data.get("summary"):
        context.append({
            "role": "system",
            "content": f"[KONTEKST WCZEŚNIEJSZEJ ROZMOWY]\n{data['summary']}"
        })
    
    # Add recent messages
    for msg in data.get("recent_messages", []):
        context.append({
            "role": msg["role"],
            "content": msg["content"]
        })
    
    return context


# Background task for periodic summarization
async def summarization_background_task():
    """
    Background task that runs summarization every hour.
    """
    while True:
        try:
            await run_summarization_batch()
        except Exception as e:
            log_error(f"[SUMMARIZER] Background task error: {e}")
        
        await asyncio.sleep(3600)  # Run every hour
