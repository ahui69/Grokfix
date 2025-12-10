#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MORDZIX - Smart Context Window

Inteligentne przycinanie kontekstu - zamiast ostatnich N wiadomości,
wybiera najważniejsze fragmenty używając TF-IDF scoring.
"""

import re
import math
from collections import Counter
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

from .helpers import log_info


@dataclass
class ScoredMessage:
    index: int
    role: str
    content: str
    score: float
    tokens_estimate: int


def estimate_tokens(text: str) -> int:
    """Estimate token count (rough: ~4 chars per token)."""
    return len(text) // 4 + 1


def tokenize_simple(text: str) -> List[str]:
    """Simple tokenization for TF-IDF."""
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    tokens = text.split()
    # Remove stopwords (basic Polish + English)
    stopwords = {
        'i', 'a', 'o', 'w', 'z', 'na', 'do', 'to', 'że', 'się', 'nie', 'jest',
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
        'co', 'jak', 'czy', 'ale', 'bo', 'gdy', 'tak', 'już', 'tylko', 'też',
        'ten', 'ta', 'te', 'tym', 'tej', 'tego', 'tych', 'być', 'mieć'
    }
    return [t for t in tokens if t not in stopwords and len(t) > 2]


def compute_tfidf(documents: List[str]) -> List[Dict[str, float]]:
    """Compute TF-IDF scores for each document."""
    # Tokenize all documents
    doc_tokens = [tokenize_simple(doc) for doc in documents]
    
    # Document frequency
    df = Counter()
    for tokens in doc_tokens:
        unique_tokens = set(tokens)
        for token in unique_tokens:
            df[token] += 1
    
    n_docs = len(documents)
    tfidf_scores = []
    
    for tokens in doc_tokens:
        tf = Counter(tokens)
        total_tokens = len(tokens) or 1
        
        scores = {}
        for token, count in tf.items():
            tf_score = count / total_tokens
            idf_score = math.log(n_docs / (df[token] + 1)) + 1
            scores[token] = tf_score * idf_score
        
        tfidf_scores.append(scores)
    
    return tfidf_scores


def compute_relevance_to_query(
    message: str, 
    query: str, 
    all_tfidf: List[Dict[str, float]],
    msg_index: int
) -> float:
    """Compute relevance score of message to current query."""
    query_tokens = set(tokenize_simple(query))
    msg_tokens = tokenize_simple(message)
    
    if not query_tokens or not msg_tokens:
        return 0.0
    
    # Overlap score
    msg_token_set = set(msg_tokens)
    overlap = len(query_tokens & msg_token_set)
    overlap_score = overlap / len(query_tokens) if query_tokens else 0
    
    # TF-IDF weighted score
    tfidf_score = 0.0
    if msg_index < len(all_tfidf):
        msg_tfidf = all_tfidf[msg_index]
        for token in query_tokens:
            if token in msg_tfidf:
                tfidf_score += msg_tfidf[token]
    
    return overlap_score * 0.6 + tfidf_score * 0.4


def select_important_messages(
    messages: List[Dict[str, Any]],
    current_query: str,
    max_tokens: int = 4000,
    min_messages: int = 5,
    max_messages: int = 50
) -> List[Dict[str, Any]]:
    """
    Select most important messages for context.
    
    Strategy:
    1. Always include last N messages (recency)
    2. Score older messages by relevance to current query
    3. Include high-scoring messages up to token limit
    """
    if not messages:
        return []
    
    # Always keep last 5 messages
    recent_count = min(5, len(messages))
    recent_messages = messages[-recent_count:]
    older_messages = messages[:-recent_count] if len(messages) > recent_count else []
    
    if not older_messages:
        return recent_messages
    
    # Compute TF-IDF for all messages
    all_contents = [m.get("content", "") for m in messages]
    all_tfidf = compute_tfidf(all_contents)
    
    # Score older messages
    scored = []
    for i, msg in enumerate(older_messages):
        content = msg.get("content", "")
        relevance = compute_relevance_to_query(content, current_query, all_tfidf, i)
        
        # Bonus for user messages (usually more important context)
        if msg.get("role") == "user":
            relevance *= 1.2
        
        # Bonus for longer messages (more context)
        length_bonus = min(1.0, len(content) / 500) * 0.2
        
        scored.append(ScoredMessage(
            index=i,
            role=msg.get("role", "unknown"),
            content=content,
            score=relevance + length_bonus,
            tokens_estimate=estimate_tokens(content)
        ))
    
    # Sort by score (descending)
    scored.sort(key=lambda x: x.score, reverse=True)
    
    # Select messages up to token limit
    selected_older = []
    tokens_used = sum(estimate_tokens(m.get("content", "")) for m in recent_messages)
    
    for sm in scored:
        if tokens_used + sm.tokens_estimate > max_tokens:
            continue
        if len(selected_older) + recent_count >= max_messages:
            break
        
        selected_older.append(older_messages[sm.index])
        tokens_used += sm.tokens_estimate
    
    # Sort selected by original order (chronological)
    selected_older.sort(key=lambda m: messages.index(m))
    
    # Combine: selected older + recent
    result = selected_older + recent_messages
    
    log_info(f"[SMART_CONTEXT] Selected {len(result)}/{len(messages)} messages ({tokens_used} tokens)")
    
    return result


def build_smart_context(
    messages: List[Dict[str, Any]],
    current_query: str,
    summary: str = None,
    max_tokens: int = 6000
) -> List[Dict[str, str]]:
    """
    Build optimized context for LLM.
    
    Args:
        messages: All conversation messages
        current_query: Current user query
        summary: Optional summary of older conversation
        max_tokens: Max tokens for context
    
    Returns:
        Optimized list of messages for LLM
    """
    context = []
    tokens_budget = max_tokens
    
    # Add summary if available
    if summary:
        summary_tokens = estimate_tokens(summary)
        if summary_tokens < tokens_budget * 0.3:  # Max 30% for summary
            context.append({
                "role": "system",
                "content": f"[STRESZCZENIE WCZEŚNIEJSZEJ ROZMOWY]\n{summary}"
            })
            tokens_budget -= summary_tokens
    
    # Select important messages
    selected = select_important_messages(
        messages,
        current_query,
        max_tokens=tokens_budget,
        min_messages=5,
        max_messages=30
    )
    
    # Add selected messages
    for msg in selected:
        context.append({
            "role": msg.get("role", "user"),
            "content": msg.get("content", "")
        })
    
    return context


def trim_context_to_limit(
    messages: List[Dict[str, str]],
    max_tokens: int = 8000
) -> List[Dict[str, str]]:
    """
    Trim context to fit token limit, keeping most recent.
    """
    if not messages:
        return []
    
    total_tokens = sum(estimate_tokens(m.get("content", "")) for m in messages)
    
    if total_tokens <= max_tokens:
        return messages
    
    # Remove oldest messages until under limit
    result = list(messages)
    while total_tokens > max_tokens and len(result) > 2:
        removed = result.pop(0)
        total_tokens -= estimate_tokens(removed.get("content", ""))
    
    log_info(f"[SMART_CONTEXT] Trimmed to {len(result)} messages ({total_tokens} tokens)")
    
    return result
