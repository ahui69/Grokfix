"""
Mostek kompatybilności dla starych endpointów (m.in. research_endpoint).

- Re-eksportuje wszystko z core.response_adapter
- Zapewnia istnienie funkcji _wrap_for_ui używanej przez legacy code
"""

from core.response_adapter import *  # type: ignore  # noqa: F401,F403

# Próba pobrania właściwego wrappera z core
try:
    from core.response_adapter import wrap_for_ui as _wrap_for_ui  # type: ignore
except Exception:
    try:
        from core.response_adapter import _wrap_for_ui  # type: ignore
    except Exception:
        # Fallback – prosta wersja, żeby legacy endpoint się nie wywalał
        def _wrap_for_ui(data):
            """
            Minimalny wrapper kompatybilności:
            po prostu zwraca dane tak jak są.
            Legacy UI oczekuje tej funkcji, więc musi istnieć.
            """
            return data
