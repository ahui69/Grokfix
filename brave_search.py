#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MORDZIX - Brave Search API Integration

Brave Search Pro:
- High quality results
- No tracking
- AI summaries
- News, images, videos

Docs: https://brave.com/search/api/
"""

import os
import httpx
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .helpers import log_info, log_warning, log_error

# Config
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "")
BRAVE_BASE_URL = "https://api.search.brave.com/res/v1"
BRAVE_TIMEOUT = 30


@dataclass
class BraveResult:
    title: str
    url: str
    description: str
    age: Optional[str] = None  # e.g. "2 hours ago"
    extra_snippets: Optional[List[str]] = None


async def brave_web_search(
    query: str,
    max_results: int = 5,
    country: str = "pl",
    search_lang: str = "pl",
    freshness: Optional[str] = None,  # "pd" (past day), "pw" (past week), "pm" (past month)
) -> Dict[str, Any]:
    """
    Search using Brave Search API.
    
    Args:
        query: Search query
        max_results: Max results (1-20)
        country: Country code (pl, us, etc.)
        search_lang: Search language
        freshness: Time filter - "pd", "pw", "pm", "py" or None
    
    Returns:
        {
            "results": [BraveResult, ...],
            "query": "original query",
            "news": [...],  # if available
            "infobox": {...}  # if available
        }
    """
    if not BRAVE_API_KEY:
        log_warning("[BRAVE] No API key configured (BRAVE_API_KEY)")
        return {"error": "no_api_key", "results": []}
    
    params = {
        "q": query,
        "count": min(max_results, 20),
        "country": country,
        "search_lang": search_lang,
        "text_decorations": False,
    }
    
    if freshness:
        params["freshness"] = freshness
    
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": BRAVE_API_KEY
    }
    
    try:
        async with httpx.AsyncClient(timeout=BRAVE_TIMEOUT) as client:
            response = await client.get(
                f"{BRAVE_BASE_URL}/web/search",
                params=params,
                headers=headers
            )
            
            if response.status_code != 200:
                error_text = response.text
                log_error(f"[BRAVE] API error {response.status_code}: {error_text[:200]}")
                return {"error": f"api_error_{response.status_code}", "results": []}
            
            data = response.json()
            
            # Parse web results
            results = []
            web_results = data.get("web", {}).get("results", [])
            for item in web_results[:max_results]:
                results.append(BraveResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    description=item.get("description", ""),
                    age=item.get("age"),
                    extra_snippets=item.get("extra_snippets")
                ))
            
            # Parse news if available
            news = []
            news_results = data.get("news", {}).get("results", [])
            for item in news_results[:3]:
                news.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "description": item.get("description", ""),
                    "age": item.get("age"),
                    "source": item.get("meta_url", {}).get("hostname", "")
                })
            
            # Parse infobox if available
            infobox = None
            if data.get("infobox"):
                ib = data["infobox"]
                infobox = {
                    "title": ib.get("title", ""),
                    "description": ib.get("description", ""),
                    "url": ib.get("url", ""),
                    "attributes": ib.get("attributes", [])
                }
            
            log_info(f"[BRAVE] Found {len(results)} results, {len(news)} news for: {query[:50]}...")
            
            return {
                "results": results,
                "news": news,
                "infobox": infobox,
                "query": query,
                "sources_count": len(results) + len(news)
            }
            
    except httpx.TimeoutException:
        log_error(f"[BRAVE] Timeout for query: {query[:50]}...")
        return {"error": "timeout", "results": []}
    except Exception as e:
        log_error(f"[BRAVE] Error: {e}")
        return {"error": str(e), "results": []}


async def brave_news_search(
    query: str,
    max_results: int = 5,
    country: str = "pl",
    freshness: str = "pw",  # past week by default for news
) -> List[Dict[str, Any]]:
    """
    Search news specifically using Brave.
    """
    if not BRAVE_API_KEY:
        return []
    
    params = {
        "q": query,
        "count": min(max_results, 20),
        "country": country,
        "freshness": freshness,
    }
    
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": BRAVE_API_KEY
    }
    
    try:
        async with httpx.AsyncClient(timeout=BRAVE_TIMEOUT) as client:
            response = await client.get(
                f"{BRAVE_BASE_URL}/news/search",
                params=params,
                headers=headers
            )
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            news = []
            for item in data.get("results", [])[:max_results]:
                news.append({
                    "source": "brave_news",
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("description", ""),
                    "age": item.get("age"),
                    "publisher": item.get("meta_url", {}).get("hostname", "")
                })
            
            return news
            
    except Exception as e:
        log_error(f"[BRAVE] News search error: {e}")
        return []


async def brave_search_simple(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Simplified search - returns list of dicts compatible with research module.
    """
    result = await brave_web_search(query, max_results=max_results)
    
    sources = []
    
    # Add web results
    for r in result.get("results", []):
        sources.append({
            "source": "brave",
            "title": r.title,
            "url": r.url,
            "snippet": r.description,
            "age": r.age
        })
    
    # Add news results
    for n in result.get("news", []):
        sources.append({
            "source": "brave_news",
            "title": n.get("title", ""),
            "url": n.get("url", ""),
            "snippet": n.get("description", ""),
            "age": n.get("age")
        })
    
    return sources


def is_brave_available() -> bool:
    """Check if Brave API is configured."""
    return bool(BRAVE_API_KEY)


# Test
if __name__ == "__main__":
    async def test():
        result = await brave_web_search("Juventus FC news", max_results=3)
        print(f"Results: {len(result.get('results', []))}")
        print(f"News: {len(result.get('news', []))}")
        for r in result.get("results", []):
            print(f"  - {r.title}: {r.url}")
    
    asyncio.run(test())
