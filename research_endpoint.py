# -*- coding: utf-8 -*-
"""
core.research_endpoint – API do silnika researchu

Ścieżki:
- POST /api/research/search      – klasyczny research (frontend)
- POST /api/research/autonauka   – mocny research + zapis do LTM
- POST /api/research             – alias na search
- POST /api/research/run         – alias na search
- GET  /api/research/sources     – lista dostępnych źródeł
- GET  /api/research/test        – prosty test
- GET  /api/research/ping        – healthcheck modułu
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.auth import verify_token
from core.helpers import log_info, log_error
from core.research import perform_research
from core.config import SERPAPI_KEY, FIRECRAWL_API_KEY

router = APIRouter(
    prefix="/api/research",
    tags=["research"],
)


class ResearchRequest(BaseModel):
    query: str = Field(..., description="Pytanie / temat do zbadania")
    depth: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Poziom szczegółowości (1–5)",
    )
    max_sources: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maksymalna liczba źródeł",
    )
    timeout_s: int = Field(
        default=60,
        ge=5,
        le=300,
        description="Maksymalny czas researchu (sekundy)",
    )

    use_web: bool = Field(
        default=True,
        description="Czy korzystać z web / zewnętrznych źródeł",
    )
    use_memory: bool = Field(
        default=True,
        description="Czy korzystać z pamięci (STM/LTM)",
    )
    save_to_ltm: bool = Field(
        default=True,
        description="Czy wynik ma zostać zapisany do długoterminowej pamięci",
    )

    sources: Optional[List[str]] = Field(
        default=None,
        description="Lista wymuszonych źródeł (np. ['duckduckgo','wikipedia'])",
    )
    persona: Optional[str] = Field(
        default=None,
        description="Persona / styl (np. 'profesor prawa', 'growth hacker')",
    )
    system_prompt: Optional[str] = Field(
        default=None,
        description="Dodatkowy system prompt dla LLM",
    )

    extra: Dict[str, Any] = Field(
        default_factory=dict,
        description="Dodatkowe parametry przekazywane 1:1 do silnika",
    )


def _wrap_for_ui(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Standardowy wrapper odpowiedzi.

    Jeśli payload już posiada klucz 'ok', nie ruszamy go – to finalny format.
    W innym przypadku opakowujemy w {ok: True, data: ...}.
    """
    if isinstance(payload, dict) and "ok" in payload:
        return payload

    return {
        "ok": True,
        "data": payload,
    }


async def _run_engine(body: ResearchRequest, *, enforce_save: Optional[bool] = None) -> Dict[str, Any]:
    """
    Wspólny helper dla /search i /autonauka.
    """
    try:
        engine_kwargs: Dict[str, Any] = {
            "depth": body.depth,
            "max_sources": body.max_sources,
            "timeout_s": body.timeout_s,
            "use_web": body.use_web,
            "use_memory": body.use_memory,
            "save_to_ltm": body.save_to_ltm if enforce_save is None else enforce_save,
            "sources": body.sources,
            "persona": body.persona,
            "system_prompt": body.system_prompt,
        }
        engine_kwargs.update(body.extra)

        result = await perform_research(
            query=body.query,
            **engine_kwargs,
        )

        if not isinstance(result, dict):
            result = {"result": result}

        result.setdefault("query", body.query)
        result.setdefault("depth", body.depth)
        result.setdefault("status", "ok")
        result.setdefault(
            "saved_to_ltm",
            bool(engine_kwargs.get("save_to_ltm")),
        )

        return _wrap_for_ui(result)

    except HTTPException:
        raise
    except Exception as e:
        log_error(f"[RESEARCH] engine call failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# GŁÓWNE ENDPOINTY
# ---------------------------------------------------------------------------

@router.post("/search", summary="Główny research (web + pamięć)")
async def research_search(
    body: ResearchRequest,
    _auth: bool = Depends(verify_token),
) -> Dict[str, Any]:
    """
    Standardowe wywołanie researchu dla frontendu / batchy.

    Domyślnie:
    - use_web = True
    - use_memory = True
    - save_to_ltm = True
    """
    log_info(
        f"[RESEARCH] /search query='{body.query[:100]}' "
        f"depth={body.depth} max_sources={body.max_sources}"
    )
    return await _run_engine(body)


@router.post("/autonauka", summary="Mocny research + agresywna nauka (LTM)")
async def research_autonauka(
    body: ResearchRequest,
    _auth: bool = Depends(verify_token),
) -> Dict[str, Any]:
    """
    Wersja nastawiona na naukę:

    - ZAWSZE save_to_ltm = True (nawet jeśli w body było False)
    - Reszta parametrów jak w /search
    """
    log_info(
        f"[RESEARCH] /autonauka query='{body.query[:100]}' "
        f"depth={body.depth} max_sources={body.max_sources}"
    )
    return await _run_engine(body, enforce_save=True)


@router.post("/", summary="Alias na /search")
@router.post("/run", summary="Alias na /search (legacy)")
async def research_run(
    body: ResearchRequest,
    _auth: bool = Depends(verify_token),
) -> Dict[str, Any]:
    """
    Alias – stare klienty mogą uderzać w /api/research lub /api/research/run.
    """
    log_info(f"[RESEARCH] /run alias for /search query='{body.query[:80]}'")
    return await _run_engine(body)


# ---------------------------------------------------------------------------
# META / HEALTH
# ---------------------------------------------------------------------------

@router.get("/sources", summary="Lista dostępnych źródeł")
async def available_sources(
    _auth: bool = Depends(verify_token),
) -> Dict[str, Any]:
    """
    Zwraca listę źródeł, które silnik MOŻE używać.

    Nic nie maskujemy:
    - jeżeli klucz do SERPAPI / Firecrawl nie jest ustawiony → available=False
    """
    sources: Dict[str, Dict[str, Any]] = {
        "duckduckgo": {
            "available": True,
            "type": "free",
            "description": "DuckDuckGo HTML search – zawsze dostępne",
        },
        "wikipedia": {
            "available": True,
            "type": "free",
            "description": "Wikipedia API – zawsze dostępne",
        },
        "serpapi": {
            "available": bool(SERPAPI_KEY),
            "type": "paid",
            "description": "Google Search przez SERPAPI – wymaga SERPAPI_KEY w .env",
        },
        "arxiv": {
            "available": True,
            "type": "free",
            "description": "arXiv – artykuły naukowe",
        },
        "semantic_scholar": {
            "available": True,
            "type": "free",
            "description": "Semantic Scholar – naukowe źródła",
        },
        "firecrawl": {
            "available": bool(FIRECRAWL_API_KEY),
            "type": "paid",
            "description": "Firecrawl – crawling / scraping, wymaga FIRECRAWL_API_KEY",
        },
        "local_memory": {
            "available": True,
            "type": "local",
            "description": "Wewnętrzna pamięć MORDZIX (STM/LTM, baza + embeddingi)",
        },
    }

    return _wrap_for_ui({"sources": sources})


@router.get("/test", summary="Szybki test modułu research")
async def research_test(
    _auth: bool = Depends(verify_token),
) -> Dict[str, Any]:
    """
    Używane w testach integracyjnych / manualnych.
    """
    return _wrap_for_ui(
        {
            "status": "ok",
            "module": "research",
            "message": "research_endpoint działa",
        }
    )


@router.get("/ping", summary="Healthcheck modułu research")
async def research_ping(
    _auth: bool = Depends(verify_token),
) -> Dict[str, Any]:
    """
    Minimalny ping dla dashboardów itp.
    """
    return _wrap_for_ui({"status": "ok", "module": "research_endpoint"})
