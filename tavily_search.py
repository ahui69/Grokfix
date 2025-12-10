#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MORDZIX - Tavily Search Integration

Tavily to znacznie lepszy web search niż DuckDuckGo:
- AI-optimized results
- Better relevance
- Includes answer extraction
- 1000 free requests/month

Docs: https://docs.tavily.com/
"""

import os
import httpx
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .helpers import log_info, log_warning, log_error

# Config
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
TAVILY_BASE_URL = "https://api.tavily.com"
TAVILY_TIMEOUT = 30


@dataclass
class TavilyResult:
    title: str
    url: str
    content: str
    score: float
    raw_content: Optional[str] = None


async def tavily_search(
    query: str,
    max_results: int = 5,
    search_depth: str = "basic",  # "basic" or "advanced"
    include_answer: bool = True,
    include_raw_content: bool = False,
    include_domains: List[str] = None,
    exclude_domains: List[str] = None,
) -> Dict[str, Any]:
    """
    Search using Tavily API.
    
    Args:
        query: Search query
        max_results: Max results to return (1-10)
        search_depth: "basic" (fast) or "advanced" (better, uses more credits)
        include_answer: Include AI-generated answer
        include_raw_content: Include full page content (uses more credits)
        include_domains: Only search these domains
        exclude_domains: Exclude these domains
    
    Returns:
        {
            "answer": "AI generated answer...",
            "results": [TavilyResult, ...],
            "query": "original query",
            "response_time": 1.23
        }
    """
    if not TAVILY_API_KEY:
        log_warning("[TAVILY] No API key configured (TAVILY_API_KEY)")
        return {"error": "no_api_key", "results": [], "answer": None}
    
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "max_results": min(max_results, 10),
        "search_depth": search_depth,
        "include_answer": include_answer,
        "include_raw_content": include_raw_content,
    }
    
    if include_domains:
        payload["include_domains"] = include_domains
    if exclude_domains:
        payload["exclude_domains"] = exclude_domains
    
    try:
        async with httpx.AsyncClient(timeout=TAVILY_TIMEOUT) as client:
            response = await client.post(
                f"{TAVILY_BASE_URL}/search",
                json=payload
            )
            
            if response.status_code != 200:
                error_text = response.text
                log_error(f"[TAVILY] API error {response.status_code}: {error_text}")
                return {"error": f"api_error_{response.status_code}", "results": [], "answer": None}
            
            data = response.json()
            
            # Parse results
            results = []
            for item in data.get("results", []):
                results.append(TavilyResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    content=item.get("content", ""),
                    score=item.get("score", 0.0),
                    raw_content=item.get("raw_content") if include_raw_content else None
                ))
            
            log_info(f"[TAVILY] Found {len(results)} results for: {query[:50]}...")
            
            return {
                "answer": data.get("answer"),
                "results": results,
                "query": query,
                "response_time": data.get("response_time", 0),
                "sources_count": len(results)
            }
            
    except httpx.TimeoutException:
        log_error(f"[TAVILY] Timeout for query: {query[:50]}...")
        return {"error": "timeout", "results": [], "answer": None}
    except Exception as e:
        log_error(f"[TAVILY] Error: {e}")
        return {"error": str(e), "results": [], "answer": None}


async def tavily_search_simple(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Simplified search - returns list of dicts compatible with existing research module.
    """
    result = await tavily_search(query, max_results=max_results)
    
    sources = []
    for r in result.get("results", []):
        sources.append({
            "source": "tavily",
            "title": r.title,
            "url": r.url,
            "snippet": r.content,
            "score": r.score
        })
    
    return sources


def is_tavily_available() -> bool:
    """Check if Tavily API is configured."""
    return bool(TAVILY_API_KEY)


# Sync wrapper for compatibility
def tavily_search_sync(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Synchronous wrapper for tavily_search."""
    return asyncio.run(tavily_search(query, max_results))


# Test
if __name__ == "__main__":
    async def test():
        result = await tavily_search("What is the latest news about Juventus FC?", max_results=3)
        print(f"Answer: {result.get('answer', 'N/A')[:200]}...")
        print(f"Results: {len(result.get('results', []))}")
        for r in result.get("results", []):
            print(f"  - {r.title}: {r.url}")
    
    asyncio.run(test())
