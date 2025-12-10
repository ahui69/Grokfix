#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cache_invalidation.py - Smart Cache Invalidation with TTL
FULL LOGIC - ZERO PLACEHOLDERS!
"""
import re
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from .helpers import log_info, log_warning

# ═══════════════════════════════════════════════════════════════════
# TTL RULES PER CATEGORY
# ═══════════════════════════════════════════════════════════════════

CACHE_TTL_RULES = {
    "news": 3600,           # 1h (świeże wiadomości)
    "weather": 1800,        # 30min
    "stock": 300,           # 5min (real-time prices)
    "crypto": 300,          # 5min
    "sports": 1800,         # 30min
    "science": 604800,      # 7 days (stable knowledge)
    "history": 2592000,     # 30 days
    "programming": 86400,   # 1 day (docs update)
    "math": 2592000,        # 30 days (stable)
    "geography": 2592000,   # 30 days
    "default": 86400        # 1 day default
}

# Category detection patterns
CATEGORY_PATTERNS = {
    "news": [
        r'\b(news|breaking|today|latest|yesterday|wiadomości|aktualności)\b',
        r'\b(headline|report|announcement|press release)\b',
        r'\b(reuters|cnn|bbc|associated press)\b'
    ],
    "weather": [
        r'\b(weather|temperature|forecast|pogoda|temperatura|prognoza)\b',
        r'\b(rain|snow|sunny|cloudy|storm|deszcz|śnieg|słońce)\b',
        r'\b(celsius|fahrenheit|humidity|wilgotność)\b'
    ],
    "stock": [
        r'\b(stock|share|nasdaq|nyse|sp500|dow jones)\b',
        r'\b(market cap|trading|ticker|giełda|akcje)\b',
        r'\b(bull|bear|dividend|dywidenda)\b'
    ],
    "crypto": [
        r'\b(bitcoin|ethereum|crypto|blockchain|btc|eth)\b',
        r'\b(cryptocurrency|kryptowaluta|mining|wallet)\b'
    ],
    "sports": [
        r'\b(football|soccer|basketball|nba|nfl|uefa)\b',
        r'\b(match|game|championship|tournament|turniej)\b',
        r'\b(score|goal|league|liga|drużyna|mecz)\b'
    ],
    "science": [
        r'\b(research|study|experiment|badanie|eksperyment)\b',
        r'\b(scientific|researcher|scientist|naukowiec)\b',
        r'\b(journal|publication|paper|artykuł naukowy)\b'
    ],
    "history": [
        r'\b(history|historical|ancient|modern|historia)\b',
        r'\b(century|decade|year \d{3,4}|wiek|rok)\b',
        r'\b(war|empire|civilization|wojna|imperium)\b'
    ],
    "programming": [
        r'\b(python|javascript|java|c\+\+|rust|go|php)\b',
        r'\b(programming|code|developer|programowanie)\b',
        r'\b(framework|library|api|database|baza danych)\b',
        r'\b(git|github|stackoverflow|npm|pip)\b'
    ],
    "math": [
        r'\b(mathematics|equation|formula|matematyka|równanie)\b',
        r'\b(calculus|algebra|geometry|geometria)\b',
        r'\b(theorem|proof|liczba|wzór)\b'
    ],
    "geography": [
        r'\b(country|city|continent|capital|geografia)\b',
        r'\b(population|area|border|populacja|granica)\b',
        r'\b(mountain|river|ocean|góra|rzeka)\b'
    ]
}


def detect_category(content: str) -> str:
    """
    Detect content category via NLP keyword matching
    
    Args:
        content: Fact content to categorize
        
    Returns:
        str: Category name (news, weather, stock, etc.)
    """
    content_lower = content.lower()
    
    # Check each category
    category_scores = {}
    for category, patterns in CATEGORY_PATTERNS.items():
        score = 0
        for pattern in patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                score += 1
        if score > 0:
            category_scores[category] = score
    
    # Return category with highest score
    if category_scores:
        return max(category_scores, key=category_scores.get)
    else:
        return "default"


def get_cache_ttl(fact_content: str, category: Optional[str] = None) -> int:
    """
    Get TTL for fact based on content category
    
    Args:
        fact_content: Fact content
        category: Optional manual category override
        
    Returns:
        int: TTL in seconds
    """
    if category and category in CACHE_TTL_RULES:
        ttl = CACHE_TTL_RULES[category]
    else:
        detected_category = detect_category(fact_content)
        ttl = CACHE_TTL_RULES.get(detected_category, CACHE_TTL_RULES["default"])
    
    log_info(f"[CACHE_TTL] Category: {category or detected_category}, TTL: {ttl}s ({ttl/3600:.1f}h)")
    
    return ttl


def calculate_expires_at(created_at: float, fact_content: str, category: Optional[str] = None) -> float:
    """
    Calculate expiration timestamp for fact
    
    Args:
        created_at: Creation timestamp
        fact_content: Fact content
        category: Optional manual category
        
    Returns:
        float: Expiration timestamp
    """
    ttl = get_cache_ttl(fact_content, category)
    expires_at = created_at + ttl
    
    return expires_at


def is_expired(expires_at: float, current_time: Optional[float] = None) -> bool:
    """
    Check if fact is expired
    
    Args:
        expires_at: Expiration timestamp
        current_time: Optional current time (default: now)
        
    Returns:
        bool: True if expired
    """
    now = current_time or time.time()
    return now > expires_at


def get_fact_age_str(created_at: float) -> str:
    """
    Get human-readable fact age
    
    Args:
        created_at: Creation timestamp
        
    Returns:
        str: Age string (e.g., "2h old (fresh!)")
    """
    age_seconds = time.time() - created_at
    
    if age_seconds < 60:
        return f"{int(age_seconds)}s old (very fresh!)"
    elif age_seconds < 3600:
        return f"{int(age_seconds/60)}min old (fresh!)"
    elif age_seconds < 86400:
        hours = int(age_seconds/3600)
        return f"{hours}h old ({'fresh!' if hours < 6 else 'ok'})"
    elif age_seconds < 604800:
        days = int(age_seconds/86400)
        return f"{days}d old ({'ok' if days < 3 else 'aging'})"
    else:
        weeks = int(age_seconds/604800)
        return f"{weeks}w old (old)"


def cleanup_expired_facts(memory_manager, dry_run: bool = False) -> Dict[str, Any]:
    """
    Background task: cleanup expired facts from L2 semantic memory
    
    Args:
        memory_manager: Memory manager instance
        dry_run: If True, only count expired facts without deleting
        
    Returns:
        dict: Cleanup stats
    """
    try:
        conn = memory_manager.db._conn()
        now = time.time()
        
        # Find expired facts (those with metadata.expires_at < now)
        cursor = conn.execute("""
            SELECT id, content, metadata, created_at
            FROM memory_nodes
            WHERE layer = 'L2' AND deleted = 0
        """)
        
        expired_ids = []
        total_checked = 0
        
        for row in cursor:
            total_checked += 1
            node_id, content, metadata_json, created_at = row
            
            # Parse metadata
            import json
            try:
                metadata = json.loads(metadata_json) if metadata_json else {}
            except:
                metadata = {}
            
            # Check if expired
            if "expires_at" in metadata:
                expires_at = metadata["expires_at"]
                if is_expired(expires_at, now):
                    expired_ids.append(node_id)
            else:
                # No expires_at? Calculate and check
                expires_at = calculate_expires_at(created_at, content)
                if is_expired(expires_at, now):
                    expired_ids.append(node_id)
        
        # Delete expired facts (unless dry run)
        if not dry_run and expired_ids:
            placeholders = ",".join("?" * len(expired_ids))
            conn.execute(
                f"UPDATE memory_nodes SET deleted = 1 WHERE id IN ({placeholders})",
                expired_ids
            )
            conn.commit()
            log_info(f"[CACHE_CLEANUP] Deleted {len(expired_ids)} expired facts")
        else:
            log_info(f"[CACHE_CLEANUP] Dry run: {len(expired_ids)} facts would be deleted")
        
        return {
            "total_checked": total_checked,
            "expired_count": len(expired_ids),
            "deleted": len(expired_ids) if not dry_run else 0,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        log_warning(f"[CACHE_CLEANUP] Error: {e}")
        return {
            "total_checked": 0,
            "expired_count": 0,
            "deleted": 0,
            "error": str(e)
        }


# ═══════════════════════════════════════════════════════════════════
# BACKGROUND TASK SCHEDULER
# ═══════════════════════════════════════════════════════════════════

import asyncio
import threading

_cleanup_task_running = False

def start_cleanup_task(memory_manager, interval: int = 3600):
    """
    Start background cleanup task (runs every hour)
    
    Args:
        memory_manager: Memory manager instance
        interval: Cleanup interval in seconds (default: 1h)
    """
    global _cleanup_task_running
    
    if _cleanup_task_running:
        log_warning("[CACHE_CLEANUP] Task already running, skipping")
        return
    
    def run_cleanup_loop():
        global _cleanup_task_running
        _cleanup_task_running = True
        
        log_info(f"[CACHE_CLEANUP] Starting background task (interval: {interval}s)")
        
        while _cleanup_task_running:
            try:
                stats = cleanup_expired_facts(memory_manager, dry_run=False)
                log_info(f"[CACHE_CLEANUP] Cleaned {stats['deleted']}/{stats['expired_count']} expired facts")
            except Exception as e:
                log_warning(f"[CACHE_CLEANUP] Task error: {e}")
            
            time.sleep(interval)
    
    # Start in background thread
    thread = threading.Thread(target=run_cleanup_loop, daemon=True)
    thread.start()
    
    log_info("[CACHE_CLEANUP] Background task started")


def stop_cleanup_task():
    """Stop background cleanup task"""
    global _cleanup_task_running
    _cleanup_task_running = False
    log_info("[CACHE_CLEANUP] Background task stopped")
