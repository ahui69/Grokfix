# -*- coding: utf-8 -*-
"""
core.research – centralny silnik researchu MORDZIX-AI

Założenia:
- JEDEN punkt wejścia: async perform_research(...)
- Alias run_research(...) i sync research(...) dla legacy
- Zero twardych zależności, wszystko "best effort":
  - jak jest pamięć → używamy
  - jak jest LLM → podsumowujemy
  - jak nie ma czegoś → zwracamy info, ale import działa

Ten moduł MA SIĘ IMPORTOWAĆ zawsze (testy, batch_research, endpointy).
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Sequence

from core.helpers import log_info, log_error


# ---------------------------------------------------------------------------
# MODELE WEWNĘTRZNE
# ---------------------------------------------------------------------------

@dataclass
class SourceHit:
    source: str
    title: str
    url: str
    snippet: str
    score: float = 0.0
    meta: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["meta"] = d.get("meta") or {}
        return d


@dataclass
class ResearchContext:
    query: str
    depth: int
    max_sources: int
    timeout_s: int
    use_web: bool
    use_memory: bool
    save_to_ltm: bool
    sources: Optional[List[str]]
    persona: Optional[str]
    system_prompt: Optional[str]
    extra: Dict[str, Any]


# ---------------------------------------------------------------------------
# HELPERY – BEZ TWARDYCH IMPORTÓW
# ---------------------------------------------------------------------------

def _get_llm():
    """Lazy import call_llm – jak są cyrki z importem, po prostu zwraca None."""
    try:
        from core.llm import call_llm  # type: ignore
        return call_llm
    except Exception as e:
        log_error(f"[RESEARCH] LLM not available: {e}")
        return None


def _get_memory_module():
    try:
        import core.memory as memory  # type: ignore
        return memory
    except Exception as e:
        log_error(f"[RESEARCH] memory module not available: {e}")
        return None


def _get_hier_memory():
    try:
        from core.hierarchical_memory import get_hierarchical_memory  # type: ignore
        return get_hierarchical_memory()
    except Exception as e:
        log_error(f"[RESEARCH] hierarchical memory not available: {e}")
        return None


def _now_ms() -> int:
    return int(time.time() * 1000)


# ---------------------------------------------------------------------------
# GŁÓWNA LOGIKA RESEARCHU
# ---------------------------------------------------------------------------

async def _search_memory(ctx: ResearchContext) -> List[SourceHit]:
    hits: List[SourceHit] = []

    if not ctx.use_memory:
        return hits

    memory_mod = _get_memory_module()
    if not memory_mod:
        return hits

    try:
        # 1) klasyczna pamięć
        if hasattr(memory_mod, "search_memory"):
            res = await memory_mod.search_memory(
                query=ctx.query,
                limit=min(ctx.max_sources, 10),
            )
            for item in res or []:
                hits.append(
                    SourceHit(
                        source="memory",
                        title=item.get("title") or item.get("summary") or "memory",
                        url=item.get("id") or "",
                        snippet=item.get("content")[:400],
                        score=float(item.get("score", 0.0)),
                        meta={"raw": item},
                    )
                )
        # 2) LTM / inne API – best effort
        elif hasattr(memory_mod, "search_memories"):
            res = await memory_mod.search_memories(
                ctx.query, limit=min(ctx.max_sources, 10)
            )
            for item in res or []:
                hits.append(
                    SourceHit(
                        source="memory",
                        title=item.get("title") or item.get("summary") or "memory",
                        url=item.get("id") or "",
                        snippet=item.get("content")[:400],
                        score=float(item.get("score", 0.0)),
                        meta={"raw": item},
                    )
                )
    except Exception as e:
        log_error(f"[RESEARCH] memory search failed: {e}")

    # 3) hierarchical memory (jeśli jest)
    try:
        hmem = _get_hier_memory()
        if hmem and hasattr(hmem, "search"):
            res = await hmem.search(
                ctx.query,
                limit=min(ctx.max_sources, 10),
            )
            for item in res or []:
                hits.append(
                    SourceHit(
                        source="hier_memory",
                        title=item.get("title") or item.get("summary") or "hmem",
                        url=item.get("id") or "",
                        snippet=item.get("content")[:400],
                        score=float(item.get("score", 0.0)),
                        meta={"raw": item},
                    )
                )
    except Exception as e:
        log_error(f"[RESEARCH] hierarchical memory search failed: {e}")

    return hits


async def _search_web(ctx: ResearchContext) -> List[SourceHit]:
    """
    Tu robimy TYLKO "best effort":

    - próbujemy core.research_policy (jeśli istnieje)
    - próbujemy core.semantic / inne helpery
    - jak nic nie ma → zwracamy pustą listę, ale nie wywalamy importu
    """
    if not ctx.use_web:
        return []

    hits: List[SourceHit] = []

    # 1) próbujemy użyć research_policy, jeśli jest
    try:
        import core.research_policy as policy  # type: ignore

        if hasattr(policy, "smart_web_search"):
            res = await policy.smart_web_search(
                query=ctx.query,
                max_results=ctx.max_sources,
                timeout_s=ctx.timeout_s,
                sources=ctx.sources,
            )
            for item in res or []:
                hits.append(
                    SourceHit(
                        source=item.get("source") or "web",
                        title=item.get("title") or "",
                        url=item.get("url") or "",
                        snippet=item.get("snippet") or "",
                        score=float(item.get("score", 0.0)),
                        meta={"raw": item},
                    )
                )
            return hits
    except Exception as e:
        log_error(f"[RESEARCH] research_policy.smart_web_search failed: {e}")

    # 2) fallback – jeśli jest semantic / inne helpery
    try:
        import core.semantic as semantic  # type: ignore

        if hasattr(semantic, "basic_web_search"):
            res = await semantic.basic_web_search(
                query=ctx.query,
                max_results=ctx.max_sources,
            )
            for item in res or []:
                hits.append(
                    SourceHit(
                        source=item.get("source") or "web",
                        title=item.get("title") or "",
                        url=item.get("url") or "",
                        snippet=item.get("snippet") or "",
                        score=float(item.get("score", 0.0)),
                        meta={"raw": item},
                    )
                )
    except Exception as e:
        log_error(f"[RESEARCH] fallback web search failed: {e}")

    return hits


async def _summarize_with_llm(
    ctx: ResearchContext,
    hits: Sequence[SourceHit],
) -> Dict[str, Any]:
    call_llm = _get_llm()
    if not call_llm:
        return {
            "ok": False,
            "reason": "llm_unavailable",
            "summary": None,
        }

    snippets = []
    for h in hits[: ctx.max_sources]:
        snippets.append(
            f"[{h.source}] {h.title}\n{h.snippet}\nURL: {h.url}\n"
        )

    joined = "\n\n---\n\n".join(snippets) if snippets else "(brak źródeł)"

    system = (
        ctx.system_prompt
        or "Jesteś modułem researchowym asystenta. Łącz informacje z wielu źródeł, "
        "oznaczaj niepewność i nie zmyślaj faktów."
    )

    user = (
        f"ZAPYTANIE:\n{ctx.query}\n\n"
        f"FRAGMENTY ŹRÓDEŁ:\n{joined}\n\n"
        "Zrób podsumowanie, najważniejsze fakty, możliwe niepewności "
        "i ewentualne rekomendacje dalszego researchu."
    )

    if ctx.persona:
        system += f"\nPersona: {ctx.persona}"

    try:
        llm_resp = call_llm(
            prompt=user,
            system_prompt=system,
        )
        content = llm_resp if isinstance(llm_resp, str) else llm_resp.get("content", str(llm_resp))
        return {
            "ok": True,
            "summary": content,
        }
    except Exception as e:
        log_error(f"[RESEARCH] LLM summary failed: {e}")
        return {
            "ok": False,
            "reason": "llm_error",
            "summary": None,
        }


async def _maybe_save_to_ltm(ctx: ResearchContext, final_payload: Dict[str, Any]) -> None:
    if not ctx.save_to_ltm:
        return

    memory_mod = _get_memory_module()
    if not memory_mod:
        return

    try:
        content_parts = []

        summary = final_payload.get("summary")
        if summary:
            content_parts.append(str(summary))

        for h in final_payload.get("sources", []):
            try:
                snippet = h.get("snippet") or ""
                if snippet:
                    content_parts.append(snippet)
            except Exception:
                continue

        content = "\n\n---\n\n".join(content_parts)[:8000]

        if hasattr(memory_mod, "add_memory"):
            await memory_mod.add_memory(
                text=content,
                metadata={
                    "type": "research",
                    "query": ctx.query,
                    "timestamp_ms": _now_ms(),
                    "depth": ctx.depth,
                },
            )
        elif hasattr(memory_mod, "store_memory"):
            await memory_mod.store_memory(
                content=content,
                meta={
                    "type": "research",
                    "query": ctx.query,
                    "timestamp_ms": _now_ms(),
                    "depth": ctx.depth,
                },
            )
    except Exception as e:
        log_error(f"[RESEARCH] save_to_ltm failed: {e}")


# ---------------------------------------------------------------------------
# PUBLICZNE API
# ---------------------------------------------------------------------------

async def perform_research(
    query: str,
    *,
    depth: int = 2,
    max_sources: int = 5,
    timeout_s: int = 60,
    use_web: bool = True,
    use_memory: bool = True,
    save_to_ltm: bool = True,
    sources: Optional[List[str]] = None,
    persona: Optional[str] = None,
    system_prompt: Optional[str] = None,
    **extra: Any,
) -> Dict[str, Any]:
    """
    Główny silnik researchu – tego używa:
    - core.research_endpoint
    - core.batch_research
    - legacy_root_py.research_endpoint
    - testy

    Zwraca SŁOWNIK, zawsze:
    {
      "ok": bool,
      "query": ...,
      "depth": ...,
      "sources": [ ... ],
      "summary": "...",
      "meta": { ... }
    }
    """
    ctx = ResearchContext(
        query=query,
        depth=depth,
        max_sources=max_sources,
        timeout_s=timeout_s,
        use_web=use_web,
        use_memory=use_memory,
        save_to_ltm=save_to_ltm,
        sources=sources,
        persona=persona,
        system_prompt=system_prompt,
        extra=extra,
    )

    started = _now_ms()
    log_info(
        f"[RESEARCH] perform_research start: '{query[:80]}' "
        f"depth={depth} web={use_web} mem={use_memory} save_to_ltm={save_to_ltm}"
    )

    # odpalamy memory + web równolegle
    tasks = []
    tasks.append(_search_memory(ctx))
    tasks.append(_search_web(ctx))

    mem_hits, web_hits = await asyncio.gather(*tasks)
    all_hits: List[SourceHit] = []
    all_hits.extend(mem_hits)
    all_hits.extend(web_hits)

    # podsumowanie LLM (jeśli jest)
    summary_info = await _summarize_with_llm(ctx, all_hits)

    payload: Dict[str, Any] = {
        "ok": True,
        "query": query,
        "depth": depth,
        "sources": [h.to_dict() for h in all_hits],
        "summary": summary_info.get("summary"),
        "llm_status": summary_info.get("reason") or ("ok" if summary_info.get("ok") else "unknown"),
        "meta": {
            "use_web": use_web,
            "use_memory": use_memory,
            "save_to_ltm": save_to_ltm,
            "max_sources": max_sources,
            "timeout_s": timeout_s,
            "sources_requested": sources,
            "elapsed_ms": _now_ms() - started,
        },
    }

    # zapis do LTM – fire & forget
    try:
        await _maybe_save_to_ltm(ctx, payload)
        payload["saved_to_ltm"] = True
    except Exception:
        payload["saved_to_ltm"] = False

    log_info(
        f"[RESEARCH] done: '{query[:80]}' hits={len(all_hits)} "
        f"elapsed={payload['meta']['elapsed_ms']}ms"
    )

    return payload


# ---------------------------------------------------------------------------
# ALIASY – DLA KOMPATYBILNOŚCI
# ---------------------------------------------------------------------------

async def run_research(
    query: str,
    depth: int = 2,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Alias – stare moduły mogą wołać run_research()."""
    return await perform_research(query=query, depth=depth, **kwargs)


def research(
    query: str,
    depth: int = 2,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Sync alias – gdy ktoś z legacy świata odpala research() bez async.

    Uwaga: jak już jest event loop, robimy osobny run, żeby nie wywalić
    "event loop is running". To jest brzydkie, ale bezpieczne.
    """
    async def _runner() -> Dict[str, Any]:
        return await perform_research(query=query, depth=depth, **kwargs)

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        return asyncio.run(_runner())
    else:
        return loop.run_until_complete(_runner())

# ============================================================================
#  KOMPATYBILNE API: AUTONAUKA + TRAVEL_SEARCH
# ============================================================================

from typing import Any, Dict


async def autonauka(query: str, depth: int = 2, **kwargs: Any) -> Dict[str, Any]:
    """
    Historyczne API używane przez różne moduły (stress_test_system, legacy itp.).

    Implementacja:
    - deleguje do perform_research(...)
    - NIE wywala importu jak cokolwiek pójdzie bokiem – tylko loguje.
    """
    from core.helpers import log_info, log_error  # lokalny import, żeby uniknąć kółek

    log_info(f"[AUTONAUKA] Start autonauka for query={query!r}, depth={depth}")

    try:
        # import tutaj, żeby przy imporcie modułu nie robić ciężkich zależności
        from core.research import perform_research  # type: ignore  # noqa
    except Exception as e:
        log_error(f"[AUTONAUKA] perform_research unavailable: {e}")
        return {
            "ok": False,
            "error": "perform_research_unavailable",
            "details": str(e),
        }

    try:
        result = await perform_research(  # type: ignore[call-arg]
            query=query,
            depth=depth,
            mode="autonauka",
            **kwargs,
        )
        log_info("[AUTONAUKA] Finished successfully")
        return result
    except Exception as e:
        log_error(f"[AUTONAUKA] perform_research failed: {e}")
        return {
            "ok": False,
            "error": "autonauka_failed",
            "details": str(e),
        }


async def travel_search(query: str, depth: int = 1, **kwargs: Any) -> Dict[str, Any]:
    """
    API używane przez travel_endpoint i legacy research_endpoint.

    Pod spodem to po prostu wyszukiwarka oparta na silniku research.
    """
    from core.helpers import log_info, log_error  # lokalny import

    log_info(f"[TRAVEL] travel_search for query={query!r}, depth={depth}")

    try:
        from core.research import perform_research  # type: ignore  # noqa
    except Exception as e:
        log_error(f"[TRAVEL] perform_research unavailable: {e}")
        return {
            "ok": False,
            "error": "perform_research_unavailable",
            "details": str(e),
        }

    try:
        result = await perform_research(  # type: ignore[call-arg]
            query=query,
            depth=depth,
            mode="travel",
            **kwargs,
        )
        return result
    except Exception as e:
        log_error(f"[TRAVEL] perform_research failed: {e}")
        return {
            "ok": False,
            "error": "travel_search_failed",
            "details": str(e),
        }


# ============================================================================
#  KOMPATYBILNE API: AUTONAUKA + TRAVEL_SEARCH
# ============================================================================

from typing import Any, Dict


async def autonauka(query: str, depth: int = 2, **kwargs: Any) -> Dict[str, Any]:
    """
    Historyczne API używane przez różne moduły (stress_test_system, legacy itp.).

    Implementacja:
    - deleguje do perform_research(...)
    - NIE wywala importu jak cokolwiek pójdzie bokiem – tylko loguje.
    """
    from core.helpers import log_info, log_error  # lokalny import, żeby uniknąć kółek

    log_info(f"[AUTONAUKA] Start autonauka for query={query!r}, depth={depth}")

    try:
        # import tutaj, żeby przy imporcie modułu nie robić ciężkich zależności
        from core.research import perform_research  # type: ignore  # noqa
    except Exception as e:
        log_error(f"[AUTONAUKA] perform_research unavailable: {e}")
        return {
            "ok": False,
            "error": "perform_research_unavailable",
            "details": str(e),
        }

    try:
        result = await perform_research(  # type: ignore[call-arg]
            query=query,
            depth=depth,
            mode="autonauka",
            **kwargs,
        )
        log_info("[AUTONAUKA] Finished successfully")
        return result
    except Exception as e:
        log_error(f"[AUTONAUKA] perform_research failed: {e}")
        return {
            "ok": False,
            "error": "autonauka_failed",
            "details": str(e),
        }


async def travel_search(query: str, depth: int = 1, **kwargs: Any) -> Dict[str, Any]:
    """
    API używane przez travel_endpoint i legacy research_endpoint.

    Pod spodem to po prostu wyszukiwarka oparta na silniku research.
    """
    from core.helpers import log_info, log_error  # lokalny import

    log_info(f"[TRAVEL] travel_search for query={query!r}, depth={depth}")

    try:
        from core.research import perform_research  # type: ignore  # noqa
    except Exception as e:
        log_error(f"[TRAVEL] perform_research unavailable: {e}")
        return {
            "ok": False,
            "error": "perform_research_unavailable",
            "details": str(e),
        }

    try:
        result = await perform_research(  # type: ignore[call-arg]
            query=query,
            depth=depth,
            mode="travel",
            **kwargs,
        )
        return result
    except Exception as e:
        log_error(f"[TRAVEL] perform_research failed: {e}")
        return {
            "ok": False,
            "error": "travel_search_failed",
            "details": str(e),
        }


async def otm_geoname(query: str, **kwargs: Any) -> Dict[str, Any]:
    """
    Kompatybilne API dla core.travel_endpoint.

    Na razie lekki wrapper na perform_research z trybem 'travel_geoname'.
    Jak będzie potrzeba – można tu podpiąć realne OpenTripMap.
    """
    from core.helpers import log_info, log_error  # lokalny import

    log_info(f"[TRAVEL] otm_geoname for query={query!r}")

    try:
        from core.research import perform_research  # type: ignore  # noqa
    except Exception as e:
        log_error(f"[TRAVEL] perform_research unavailable in otm_geoname: {e}")
        return {
            "ok": False,
            "error": "perform_research_unavailable",
            "details": str(e),
        }

    try:
        result = await perform_research(  # type: ignore[call-arg]
            query=query,
            mode="travel_geoname",
            **kwargs,
        )
        return result
    except Exception as e:
        log_error(f"[TRAVEL] otm_geoname perform_research failed: {e}")
        return {
            "ok": False,
            "error": "otm_geoname_failed",
            "details": str(e),
        }

async def serp_maps(query: str, **kwargs: Any) -> Dict[str, Any]:
    """
    Kompatybilne API dla core.travel_endpoint.

    Stare travel_endpoint woła core.research.serp_maps.
    Tu robimy lekki wrapper na perform_research z osobnym trybem.
    """
    from core.helpers import log_info, log_error  # lokalny import

    log_info(f"[TRAVEL] serp_maps for query={query!r}")

    try:
        from core.research import perform_research  # type: ignore  # noqa
    except Exception as e:
        log_error(f"[TRAVEL] perform_research unavailable in serp_maps: {e}")
        return {
            "ok": False,
            "error": "perform_research_unavailable",
            "details": str(e),
        }

    try:
        result = await perform_research(  # type: ignore[call-arg]
            query=query,
            mode="serp_maps",
            **kwargs,
        )
        return result
    except Exception as e:
        log_error(f"[TRAVEL] serp_maps perform_research failed: {e}")
        return {
            "ok": False,
            "error": "serp_maps_failed",
            "details": str(e),
        }

async def serp_maps(query: str, **kwargs: Any) -> Dict[str, Any]:
    """
    Kompatybilne API dla core.travel_endpoint.

    Stare travel_endpoint woła core.research.serp_maps.
    Tu robimy lekki wrapper na perform_research z osobnym trybem.
    """
    from core.helpers import log_info, log_error  # lokalny import

    log_info(f"[TRAVEL] serp_maps for query={query!r}")

    try:
        from core.research import perform_research  # type: ignore  # noqa
    except Exception as e:
        log_error(f"[TRAVEL] perform_research unavailable in serp_maps: {e}")
        return {
            "ok": False,
            "error": "perform_research_unavailable",
            "details": str(e),
        }

    try:
        result = await perform_research(  # type: ignore[call-arg]
            query=query,
            mode="serp_maps",
            **kwargs,
        )
        return result
    except Exception as e:
        log_error(f"[TRAVEL] serp_maps perform_research failed: {e}")
        return {
            "ok": False,
            "error": "serp_maps_failed",
            "details": str(e),
        }

# ============================================================================
#  STUBY KOMPATYBILNOŚCI DLA TRAVEL_ENDPOINT
#  używane w core.travel_endpoint: serp_maps / otm_geoname
# ============================================================================

from typing import Any, Dict  # my mamy już wyżej, ale import idempotentny

async def serp_maps(query: str, **kwargs: Any) -> Dict[str, Any]:
    """
    Stub pod mapy (SERP / inne). Zwraca pustą listę, ale nie rozwala endpointu.
    """
    from core.helpers import log_info
    log_info(f"[TRAVEL] serp_maps STUB for query={query!r}")
    return {
        "ok": True,
        "source": "serp_maps_stub",
        "query": query,
        "results": [],
    }


async def otm_geoname(query: str, **kwargs: Any) -> Dict[str, Any]:
    """
    Stub pod OpenTripMap / geoname. Zwraca pustą listę.
    """
    from core.helpers import log_info
    log_info(f"[TRAVEL] otm_geoname STUB for query={query!r}")
    return {
        "ok": True,
        "source": "otm_geoname_stub",
        "query": query,
        "results": [],
    }
