
import re
from urllib.parse import urlparse

# Duża whitelist domen (z sensownych źródeł: encyklopedie, gov, uczelnie, media, sporty, technologia)
ALLOWED_DOMAINS = set([
    # Encyklopedie / wiedza
    "wikipedia.org","pl.wikipedia.org","britannica.com","scholar.google.com",
    # Rządy / prawo / instytucje
    "gov.pl","europa.eu","eur-lex.europa.eu","who.int","cdc.gov","ema.europa.eu","un.org","nasa.gov","noaa.gov",
    # Uczelnie / repozytoria
    "arxiv.org","nature.com","science.org","sciencedirect.com","acm.org","ieee.org","springer.com","ox.ac.uk","cam.ac.uk",
    "harvard.edu","mit.edu","stanford.edu","berkeley.edu","uw.edu","uw.edu.pl","agh.edu.pl","pwr.edu.pl","pw.edu.pl",
    # Biznes/tech oficjalne
    "openai.com","meta.com","about.fb.com","google.com","blog.google","developers.google.com","cloud.google.com",
    "microsoft.com","learn.microsoft.com","github.com","gitlab.com","docs.python.org","pypi.org","kubernetes.io",
    "docker.com","docs.docker.com","rust-lang.org","go.dev","nodejs.org","npmjs.com","mozilla.org","mdn.dev","developer.apple.com",
    # Media ogólne PL / świat (wiarygodne redakcje)
    "bbc.com","bbc.co.uk","reuters.com","apnews.com","theguardian.com","nytimes.com","wsj.com","ft.com","bloomberg.com",
    "economist.com","washingtonpost.com","time.com","aljazeera.com",
    "tvn24.pl","wyborcza.pl","onet.pl","rmf24.pl","polsatnews.pl","interia.pl","money.pl","bankier.pl","pb.pl",
    # Sport oficjalne i tabele
    "uefa.com","fifa.com","premierleague.com","laliga.com","bundesliga.com","seriea.com","mls.com",
    "nba.com","wnba.com","nfl.com","nhl.com","mlb.com","uefa.tv","transfermarkt.com","flashscore.com","sofascore.com",
    # Kursy/krypto/oficjalne
    "ecb.europa.eu","nbp.pl","stooq.pl","yahoo.com","finance.yahoo.com","coinmarketcap.com","coingecko.com",
    # Dokumentacje / RFC
    "ietf.org","datatracker.ietf.org","rfc-editor.org","w3.org","whatwg.org","sqlite.org","postgresql.org","mysql.com","mariadb.org",
    # Stack (do weryfikacji technicznej, bez kopiowania)
    "stackoverflow.com","superuser.com","serverfault.com",
])

def _hostname(url: str) -> str:
    try:
        h = urlparse(url).hostname or ""
        return h.lower()
    except Exception:
        return ""

def is_allowed(url: str) -> bool:
    h = _hostname(url)
    if not h:
        return False
    return any(h == d or h.endswith("." + d) for d in ALLOWED_DOMAINS)

def filter_sources(sources):
    cleaned = []
    for s in sources or []:
        try:
            url = s.get("url") if isinstance(s, dict) else str(s)
        except Exception:
            url = None
        if url and is_allowed(url):
            cleaned.append(s if isinstance(s, dict) else {"title": url, "url": url})
    return cleaned

# --- Rozszerzenia: TLD i per-tenant ---
import os, json
from pathlib import Path

# Dozwolone sufiksy TLD (globalne) – domyślnie .pl, .com, .xyz
_GLOBAL_TLD_SUFFIXES = [s.strip().lower() for s in os.getenv("RESEARCH_ALLOW_TLDS", ".pl,.com,.xyz").split(",") if s.strip()]

def _tenant_overrides(tenant_id: str):
    """
    Wczytuje nadpisania per-tenant z pliku tenants/<TENANT>/research_whitelist.json
    Format:
    {
      "domains": ["example.com", "sub.domain.pl"],
      "tlds": [".dev", ".io"]
    }
    """
    if not tenant_id:
        return {"domains": [], "tlds": []}
    try:
        p = Path(os.getenv("WORKSPACE",".")) / "tenants" / tenant_id / "research_whitelist.json"
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            d = [str(x).lower() for x in (data.get("domains") or [])]
            t = [str(x).lower() for x in (data.get("tlds") or [])]
            return {"domains": d, "tlds": t}
    except Exception:
        pass
    return {"domains": [], "tlds": []}

def is_allowed_with_tenant(url: str, tenant_id: str = "") -> bool:
    h = _hostname(url)
    if not h:
        return False
    # 1) twarda globalna lista domen
    if any(h == d or h.endswith("." + d) for d in ALLOWED_DOMAINS):
        return True
    # 2) globalne TLD-sufiksy (.pl/.com/.xyz)
    for suf in _GLOBAL_TLD_SUFFIXES:
        if suf and (h.endswith(suf) or h == suf.lstrip(".")):
            return True
    # 3) per-tenant – domeny i TLD
    ov = _tenant_overrides(tenant_id or "")
    if any(h == d or h.endswith("." + d) for d in ov["domains"]):
        return True
    for suf in ov["tlds"]:
        if suf and (h.endswith(suf) or h == suf.lstrip(".")):
            return True
    return False

def filter_sources_tenant(sources, tenant_id: str = ""):
    cleaned = []
    for s in sources or []:
        try:
            url = s.get("url") if isinstance(s, dict) else str(s)
        except Exception:
            url = None
        if url and is_allowed_with_tenant(url, tenant_id):
            cleaned.append(s if isinstance(s, dict) else {"title": url, "url": url})
    return cleaned


# ============================================================================
# TAVILY INTEGRATION (PRIMARY WEB SEARCH)
# ============================================================================

import asyncio
import hashlib
import time
from typing import Dict, Any

# Web search cache (in-memory, 30 min TTL)
_SEARCH_CACHE: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL = 1800  # 30 minutes


def _cache_key(query: str) -> str:
    return hashlib.md5(query.lower().strip().encode()).hexdigest()


def _get_cached(query: str):
    key = _cache_key(query)
    if key in _SEARCH_CACHE:
        entry = _SEARCH_CACHE[key]
        if time.time() - entry["ts"] < _CACHE_TTL:
            return entry["results"]
        else:
            del _SEARCH_CACHE[key]
    return None


def _set_cache(query: str, results: list):
    key = _cache_key(query)
    _SEARCH_CACHE[key] = {"results": results, "ts": time.time()}
    # Cleanup old entries (max 500)
    if len(_SEARCH_CACHE) > 500:
        oldest = sorted(_SEARCH_CACHE.items(), key=lambda x: x[1]["ts"])[:100]
        for k, _ in oldest:
            del _SEARCH_CACHE[k]


async def smart_web_search(query: str, max_results: int = 10, tenant_id: str = "", timeout_s: float = None, sources: list = None, **kwargs) -> list:
    """
    Smart web search - PARALLEL Brave + Tavily with caching.
    
    Features:
    - Parallel requests (asyncio.gather)
    - 30 min cache
    - Deduplication by URL
    - Brave PRIMARY (50 req/s, unlimited)
    - Tavily SECONDARY (AI-optimized)
    - DuckDuckGo fallback
    """
    from .helpers import log_info, log_warning
    
    # Check cache first
    cached = _get_cached(query)
    if cached:
        log_info(f"[RESEARCH] Cache HIT: {len(cached)} results")
        return cached
    
    results = []
    existing_urls = set()
    
    # Parallel search tasks
    async def search_brave():
        try:
            from .brave_search import brave_search_simple, is_brave_available
            if is_brave_available():
                return await brave_search_simple(query, max_results=max_results)
        except Exception as e:
            log_warning(f"[RESEARCH] Brave failed: {e}")
        return []
    
    async def search_tavily():
        try:
            from .tavily_search import tavily_search_simple, is_tavily_available
            if is_tavily_available():
                return await tavily_search_simple(query, max_results=max_results)
        except Exception as e:
            log_warning(f"[RESEARCH] Tavily failed: {e}")
        return []
    
    # Run in parallel
    brave_results, tavily_results = await asyncio.gather(
        search_brave(),
        search_tavily(),
        return_exceptions=True
    )
    
    # Handle exceptions
    if isinstance(brave_results, Exception):
        log_warning(f"[RESEARCH] Brave exception: {brave_results}")
        brave_results = []
    if isinstance(tavily_results, Exception):
        log_warning(f"[RESEARCH] Tavily exception: {tavily_results}")
        tavily_results = []
    
    # Merge results (Brave first - primary)
    for r in (brave_results or []):
        url = r.get("url")
        if url and url not in existing_urls:
            results.append(r)
            existing_urls.add(url)
    
    # Add Tavily results (dedupe)
    for r in (tavily_results or []):
        url = r.get("url")
        if url and url not in existing_urls:
            results.append(r)
            existing_urls.add(url)
    
    log_info(f"[RESEARCH] Brave: {len(brave_results or [])}, Tavily: {len(tavily_results or [])}, Total: {len(results)}")
    
    # Fallback to DuckDuckGo if not enough results
    if len(results) < 3:
        try:
            from .semantic import basic_web_search
            ddg_results = await basic_web_search(query, max_results=max_results)
            for dr in (ddg_results or []):
                url = dr.get("url")
                if url and url not in existing_urls:
                    results.append(dr)
                    existing_urls.add(url)
        except Exception:
            pass
    
    # Filter by allowed domains
    filtered = filter_sources_tenant(results, tenant_id)
    
    # Cache results
    _set_cache(query, filtered)
    
    return filtered
