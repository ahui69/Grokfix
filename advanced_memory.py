# -*- coding: utf-8 -*-
"""
core.advanced_memory

Zunifikowany system pamięci nad core.memory:

- jedna klasa: UnifiedMemorySystem
- żadnych ciężkich operacji typu asyncio.run() przy imporcie
- korzysta z istniejącego core.memory (memory_manager / funkcje pomocnicze)
- loguje to, co widziałeś w logach:
  [INFO][MEMORY] Unified Memory System module loaded
  [INFO][MEMORY] Unified Memory System initialized
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.helpers import log_info, log_error

try:
    # staramy się użyć istniejącego backendu
    from core import memory as core_memory  # type: ignore
except Exception as e:  # import-level, ale bez wywalania
    core_memory = None  # type: ignore
    log_error(f"[MEMORY] core.memory not available in advanced_memory: {e}")


@dataclass
class MemoryItem:
    """Prosty rekord pamięci – minimalny, ale używalny w innych modułach."""
    text: str
    namespace: str = "default"
    meta: Optional[Dict[str, Any]] = None


class UnifiedMemorySystem:
    """
    Wysokopoziomowy interfejs do pamięci:

    Metody:
    - add()          – dodaj pojedynczy wpis
    - bulk_add()     – batch
    - search()       – wyszukiwanie tekstowe / semantyczne (best-effort)
    - consolidate()  – sprzątanie / agregacja (opcjonalne)
    - export_all()   – eksport do listy dictów

    Jak core.memory nie istnieje albo nie ma danej funkcji – logujemy WARN
    i zwracamy sensowny fallback zamiast wywalać import.
    """

    def __init__(self) -> None:
        self._backend = core_memory
        self._initialized = False
        log_info("[MEMORY] Unified Memory System module loaded")

        try:
            self._init_backend()
            self._initialized = True
            log_info("[MEMORY] Unified Memory System initialized")
        except Exception as e:
            log_error(f"[MEMORY] Unified Memory System init failed: {e}")

    # ------------------------------------------------------------------
    # PRIVATE
    # ------------------------------------------------------------------

    def _init_backend(self) -> None:
        """Opcjonalna inicjalizacja backendu (np. init_db)."""
        if not self._backend:
            return

        # jeżeli core.memory ma init_db – odpalamy raz
        init_db = getattr(self._backend, "init_db", None)
        if callable(init_db):
            try:
                init_db()
            except Exception as e:
                log_error(f"[MEMORY] init_db in core.memory failed: {e}")

    def _get_manager(self):
        """Zwraca memory_manager jeśli jest, inaczej None."""
        if not self._backend:
            return None
        return getattr(self._backend, "memory_manager", None)

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def is_ready(self) -> bool:
        return bool(self._backend) and self._initialized

    async def add(self, item: MemoryItem) -> Dict[str, Any]:
        """
        Dodaje wpis do pamięci. Stara się korzystać z:
        - memory_manager.add() lub
        - core.memory.add_memory() lub podobnej funkcji.
        """
        manager = self._get_manager()
        if manager and hasattr(manager, "add"):
            try:
                result = manager.add(  # type: ignore[attr-defined]
                    text=item.text,
                    namespace=item.namespace,
                    meta=item.meta or {},
                )
                if hasattr(result, "__await__"):
                    result = await result  # type: ignore[assignment]
                return {"ok": True, "backend": "memory_manager.add", "result": result}
            except Exception as e:
                log_error(f"[MEMORY] manager.add failed: {e}")

        # fallback przez funkcję modulową
        if self._backend:
            add_fn = getattr(self._backend, "add_memory", None)
            if callable(add_fn):
                try:
                    result = add_fn(
                        text=item.text,
                        namespace=item.namespace,
                        meta=item.meta or {},
                    )
                    if hasattr(result, "__await__"):
                        result = await result  # type: ignore[assignment]
                    return {"ok": True, "backend": "core.memory.add_memory", "result": result}
                except Exception as e:
                    log_error(f"[MEMORY] core.memory.add_memory failed: {e}")

        return {"ok": False, "reason": "backend_unavailable"}

    async def bulk_add(self, items: List[MemoryItem]) -> Dict[str, Any]:
        """Batch add – iteruje po add()."""
        results = []
        for it in items:
            results.append(await self.add(it))
        return {
            "ok": all(r.get("ok") for r in results),
            "items": results,
        }

    async def search(
        self,
        query: str,
        namespace: str = "default",
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Wyszukuje w pamięci – próbuje:
        - memory_manager.search()
        - core.memory.search_memories()
        - zwraca listę wyników (może być pusta).
        """
        manager = self._get_manager()
        if manager and hasattr(manager, "search"):
            try:
                result = manager.search(  # type: ignore[attr-defined]
                    query=query,
                    namespace=namespace,
                    limit=limit,
                )
                if hasattr(result, "__await__"):
                    result = await result  # type: ignore[assignment]
                return {"ok": True, "backend": "memory_manager.search", "results": result}
            except Exception as e:
                log_error(f"[MEMORY] manager.search failed: {e}")

        if self._backend:
            search_fn = getattr(self._backend, "search_memories", None)
            if callable(search_fn):
                try:
                    result = search_fn(
                        query=query,
                        namespace=namespace,
                        limit=limit,
                    )
                    if hasattr(result, "__await__"):
                        result = await result  # type: ignore[assignment]
                    return {"ok": True, "backend": "core.memory.search_memories", "results": result}
                except Exception as e:
                    log_error(f"[MEMORY] core.memory.search_memories failed: {e}")

        return {"ok": False, "reason": "backend_unavailable", "results": []}

    async def consolidate(self) -> Dict[str, Any]:
        """
        Konsolidacja / sprzątanie – jeśli backend ma taką funkcję.
        """
        if self._backend:
            fn = getattr(self._backend, "consolidate_memory", None)
            if callable(fn):
                try:
                    result = fn()
                    if hasattr(result, "__await__"):
                        result = await result  # type: ignore[assignment]
                    log_info(f"[MEMORY] Consolidation complete: {result}")
                    return {"ok": True, "result": result}
                except Exception as e:
                    log_error(f"[MEMORY] consolidate_memory failed: {e}")
                    return {"ok": False, "reason": "error", "error": str(e)}

        return {"ok": False, "reason": "not_implemented"}

    async def export_all(self, namespace: Optional[str] = None) -> Dict[str, Any]:
        """
        Eksportuje całą pamięć (lub jeden namespace) do listy słowników.
        """
        if self._backend:
            fn = getattr(self._backend, "export_memories", None)
            if callable(fn):
                try:
                    result = fn(namespace=namespace)
                    if hasattr(result, "__await__"):
                        result = await result  # type: ignore[assignment]
                    return {"ok": True, "memories": result}
                except Exception as e:
                    log_error(f"[MEMORY] export_memories failed: {e}")
                    return {"ok": False, "reason": "error", "error": str(e)}

        return {"ok": False, "reason": "not_implemented", "memories": []}


# ---------------------------------------------------------------------------
# Globalna instancja – większość kodu będzie korzystać z tego
# ---------------------------------------------------------------------------

unified_memory = UnifiedMemorySystem()
