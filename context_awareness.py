#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
context_awareness.py - Context Awareness Engine
FULL LOGIC - ZERO PLACEHOLDERS!

Features:
- Auto-detect długie rozmowy
- Smart context trimming (40% token reduction)
- Rolling summary co 50 messages
- Context compression via extractive summarization
"""
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from collections import deque

from .helpers import log_info, log_warning


# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

# Context thresholds
LONG_CONVERSATION_THRESHOLD = 50  # Messages count
CONTEXT_TRIM_THRESHOLD = 100      # Start trimming at 100 msgs
MAX_CONTEXT_MESSAGES = 150        # Hard limit
ROLLING_SUMMARY_INTERVAL = 50     # Summarize every 50 msgs
TOKEN_BUDGET = 4000               # Max tokens for context (GPT-4 has 8k-128k)
AVG_TOKENS_PER_MESSAGE = 50       # Estimate

# Compression settings
COMPRESSION_RATIO = 0.6           # Keep 60% of messages (40% reduction)
SUMMARY_MAX_LENGTH = 500          # Max summary length in chars


# ═══════════════════════════════════════════════════════════════════
# MESSAGE IMPORTANCE SCORING
# ═══════════════════════════════════════════════════════════════════

def calculate_message_importance(
    message: Dict[str, Any],
    position: int,
    total_messages: int,
    contains_question: bool = False,
    contains_code: bool = False,
    length: int = 0
) -> float:
    """
    Calculate importance score for message (0.0 - 1.0)
    
    Factors:
    - Recency (newer = more important)
    - Position (recent > middle > old)
    - Contains question (important)
    - Contains code (important)
    - Length (longer = more substantial)
    
    Args:
        message: Message dict
        position: Position in conversation (0 = oldest)
        total_messages: Total message count
        contains_question: Has question mark
        contains_code: Has code blocks
        length: Message length
        
    Returns:
        float: Importance score 0.0-1.0
    """
    score = 0.0
    
    # 1. Recency bias (40% weight)
    # Recent messages more important
    recency = position / total_messages if total_messages > 0 else 0.5
    score += recency * 0.4
    
    # 2. Content type (30% weight)
    if contains_question:
        score += 0.15  # Questions are important
    if contains_code:
        score += 0.15  # Code is important
    
    # 3. Length factor (20% weight)
    # Normalize length (assume 500 chars = max)
    length_factor = min(length / 500, 1.0)
    score += length_factor * 0.2
    
    # 4. Position in conversation (10% weight)
    # First/last messages more important than middle
    if position < 5 or position >= total_messages - 5:
        score += 0.1
    
    return min(score, 1.0)


def detect_content_features(text: str) -> Dict[str, bool]:
    """
    Detect content features in message
    
    Args:
        text: Message text
        
    Returns:
        dict: Feature flags
    """
    return {
        "contains_question": "?" in text,
        "contains_code": "```" in text or "def " in text or "class " in text or "function " in text,
        "contains_url": "http://" in text or "https://" in text,
        "contains_number": any(char.isdigit() for char in text),
        "is_long": len(text) > 300
    }


# ═══════════════════════════════════════════════════════════════════
# EXTRACTIVE SUMMARIZATION
# ═══════════════════════════════════════════════════════════════════

def extract_key_sentences(text: str, max_sentences: int = 3) -> str:
    """
    Extract most important sentences via simple ranking
    
    Args:
        text: Text to summarize
        max_sentences: Max sentences to keep
        
    Returns:
        str: Extracted summary
    """
    # Split into sentences
    import re
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    
    if len(sentences) <= max_sentences:
        return text
    
    # Score sentences by features
    scored = []
    for i, sentence in enumerate(sentences):
        score = 0.0
        
        # Length (prefer medium-length)
        length = len(sentence)
        if 50 < length < 200:
            score += 0.3
        
        # Position (first sentences often important)
        if i < 2:
            score += 0.2
        
        # Contains keywords
        keywords = ["important", "key", "main", "critical", "essential", "note", "remember"]
        if any(kw in sentence.lower() for kw in keywords):
            score += 0.3
        
        # Contains numbers (often facts)
        if any(char.isdigit() for char in sentence):
            score += 0.2
        
        scored.append((score, sentence))
    
    # Sort by score, take top N
    scored.sort(reverse=True, key=lambda x: x[0])
    top_sentences = [s[1] for s in scored[:max_sentences]]
    
    return " ".join(top_sentences)


def create_rolling_summary(messages: List[Dict[str, Any]], max_length: int = SUMMARY_MAX_LENGTH) -> str:
    """
    Create rolling summary of message batch
    
    Args:
        messages: List of message dicts
        max_length: Max summary length
        
    Returns:
        str: Summary text
    """
    if not messages:
        return ""
    
    # Combine all messages
    combined = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        combined.append(f"{role}: {content}")
    
    full_text = "\n".join(combined)
    
    # Extract key sentences
    summary = extract_key_sentences(full_text, max_sentences=5)
    
    # Truncate if too long
    if len(summary) > max_length:
        summary = summary[:max_length] + "..."
    
    return summary


# ═══════════════════════════════════════════════════════════════════
# SMART CONTEXT TRIMMING
# ═══════════════════════════════════════════════════════════════════

def trim_context_smart(
    messages: List[Dict[str, Any]],
    target_count: int,
    keep_first: int = 2,
    keep_last: int = 10
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Smart context trimming based on importance
    
    Strategy:
    1. Always keep first N messages (context)
    2. Always keep last N messages (recent)
    3. Score middle messages by importance
    4. Keep top-scored messages
    5. Create summary of removed messages
    
    Args:
        messages: All messages
        target_count: Target message count
        keep_first: Keep first N messages
        keep_last: Keep last N messages
        
    Returns:
        tuple: (trimmed_messages, summary_of_removed)
    """
    total = len(messages)
    
    if total <= target_count:
        return messages, ""
    
    # Keep first and last
    first_msgs = messages[:keep_first]
    last_msgs = messages[-keep_last:]
    middle_msgs = messages[keep_first:-keep_last]
    
    # Calculate how many middle messages to keep
    middle_budget = target_count - keep_first - keep_last
    
    if middle_budget <= 0:
        # Not enough budget, just keep first and last
        removed = middle_msgs
        kept = first_msgs + last_msgs
    else:
        # Score middle messages
        scored_middle = []
        for i, msg in enumerate(middle_msgs):
            content = msg.get("content", "")
            features = detect_content_features(content)
            
            importance = calculate_message_importance(
                message=msg,
                position=keep_first + i,
                total_messages=total,
                contains_question=features["contains_question"],
                contains_code=features["contains_code"],
                length=len(content)
            )
            
            scored_middle.append((importance, msg))
        
        # Sort by importance, keep top N
        scored_middle.sort(reverse=True, key=lambda x: x[0])
        kept_middle = [msg for score, msg in scored_middle[:middle_budget]]
        removed_middle = [msg for score, msg in scored_middle[middle_budget:]]
        
        # Reconstruct in chronological order
        # (We need to maintain temporal order)
        all_kept = first_msgs + kept_middle + last_msgs
        
        # Sort by original index to preserve order
        original_indices = {id(msg): i for i, msg in enumerate(messages)}
        kept = sorted(all_kept, key=lambda m: original_indices.get(id(m), 0))
        removed = removed_middle
    
    # Create summary of removed messages
    summary = create_rolling_summary(removed) if removed else ""
    
    log_info(f"[CONTEXT_TRIM] {total} → {len(kept)} messages (removed {len(removed)})")
    
    return kept, summary


# ═══════════════════════════════════════════════════════════════════
# CONTEXT COMPRESSION
# ═══════════════════════════════════════════════════════════════════

def compress_context(
    messages: List[Dict[str, Any]],
    token_budget: int = TOKEN_BUDGET
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Compress context to fit token budget
    
    Process:
    1. Estimate current token count
    2. If over budget, trim messages
    3. Create rolling summaries
    4. Return compressed context + metadata
    
    Args:
        messages: All messages
        token_budget: Max tokens allowed
        
    Returns:
        tuple: (compressed_messages, compression_stats)
    """
    if not messages:
        return messages, {"compressed": False}
    
    # Estimate tokens
    estimated_tokens = len(messages) * AVG_TOKENS_PER_MESSAGE
    
    if estimated_tokens <= token_budget:
        # No compression needed
        return messages, {
            "compressed": False,
            "original_count": len(messages),
            "compressed_count": len(messages),
            "token_reduction_pct": 0.0
        }
    
    # Calculate target message count
    target_count = int((token_budget / AVG_TOKENS_PER_MESSAGE) * COMPRESSION_RATIO)
    target_count = max(target_count, 20)  # Minimum 20 messages
    
    # Trim context
    compressed, summary = trim_context_smart(messages, target_count)
    
    # Add summary as system message (if any)
    if summary:
        summary_msg = {
            "role": "system",
            "content": f"[Context Summary - Previous {len(messages) - len(compressed)} messages]: {summary}",
            "timestamp": time.time(),
            "is_summary": True
        }
        compressed = [summary_msg] + compressed
    
    # Calculate stats
    original_tokens = estimated_tokens
    compressed_tokens = len(compressed) * AVG_TOKENS_PER_MESSAGE
    reduction_pct = ((original_tokens - compressed_tokens) / original_tokens) * 100
    
    log_info(f"[CONTEXT_COMPRESS] {len(messages)} msgs ({original_tokens} tokens) → {len(compressed)} msgs ({compressed_tokens} tokens), {reduction_pct:.1f}% reduction")
    
    return compressed, {
        "compressed": True,
        "original_count": len(messages),
        "compressed_count": len(compressed),
        "original_tokens": original_tokens,
        "compressed_tokens": compressed_tokens,
        "token_reduction_pct": reduction_pct,
        "summary_created": bool(summary)
    }


# ═══════════════════════════════════════════════════════════════════
# CONTEXT AWARENESS ENGINE
# ═══════════════════════════════════════════════════════════════════

class ContextAwarenessEngine:
    """Main context awareness engine"""
    
    def __init__(self):
        self.conversation_summaries: Dict[str, List[str]] = {}  # conversation_id -> summaries
        self.message_counts: Dict[str, int] = {}  # conversation_id -> count
        self.last_summary_at: Dict[str, int] = {}  # conversation_id -> message count at last summary
        
        log_info("[CONTEXT_ENGINE] Initialized")
    
    def process_context(
        self,
        conversation_id: str,
        messages: List[Dict[str, Any]],
        force_compress: bool = False
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Process conversation context with smart compression
        
        Args:
            conversation_id: Conversation ID
            messages: All messages
            force_compress: Force compression even if under threshold
            
        Returns:
            tuple: (processed_messages, stats)
        """
        message_count = len(messages)
        self.message_counts[conversation_id] = message_count
        
        # Detect long conversation
        is_long = message_count >= LONG_CONVERSATION_THRESHOLD
        
        # Check if rolling summary needed
        last_summary = self.last_summary_at.get(conversation_id, 0)
        needs_summary = (message_count - last_summary) >= ROLLING_SUMMARY_INTERVAL
        
        stats = {
            "conversation_id": conversation_id,
            "message_count": message_count,
            "is_long_conversation": is_long,
            "needs_rolling_summary": needs_summary,
            "timestamp": datetime.now().isoformat()
        }
        
        # Create rolling summary if needed
        if needs_summary and message_count >= ROLLING_SUMMARY_INTERVAL:
            batch_start = last_summary
            batch_end = message_count
            batch = messages[batch_start:batch_end]
            
            summary = create_rolling_summary(batch)
            
            if conversation_id not in self.conversation_summaries:
                self.conversation_summaries[conversation_id] = []
            
            self.conversation_summaries[conversation_id].append(summary)
            self.last_summary_at[conversation_id] = message_count
            
            stats["rolling_summary"] = summary
            log_info(f"[CONTEXT_ENGINE] Created rolling summary for {conversation_id} (msgs {batch_start}-{batch_end})")
        
        # Smart compression if needed
        if force_compress or message_count >= CONTEXT_TRIM_THRESHOLD:
            compressed, compress_stats = compress_context(messages)
            stats.update(compress_stats)
            return compressed, stats
        else:
            stats["compressed"] = False
            return messages, stats
    
    def get_conversation_summary(self, conversation_id: str) -> Optional[str]:
        """Get full conversation summary"""
        summaries = self.conversation_summaries.get(conversation_id, [])
        if not summaries:
            return None
        
        return "\n\n".join(summaries)
    
    def reset_conversation(self, conversation_id: str):
        """Reset conversation state"""
        self.conversation_summaries.pop(conversation_id, None)
        self.message_counts.pop(conversation_id, None)
        self.last_summary_at.pop(conversation_id, None)
        log_info(f"[CONTEXT_ENGINE] Reset conversation {conversation_id}")


# ═══════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════

_global_context_engine = None


def get_context_engine() -> ContextAwarenessEngine:
    """Get global context awareness engine"""
    global _global_context_engine
    if _global_context_engine is None:
        _global_context_engine = ContextAwarenessEngine()
    return _global_context_engine


def process_context(conversation_id: str, messages: List[Dict[str, Any]], force_compress: bool = False) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Shortcut: process context"""
    return get_context_engine().process_context(conversation_id, messages, force_compress)
