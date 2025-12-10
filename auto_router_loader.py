from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import List, Set, Tuple

from fastapi import FastAPI, APIRouter

# root projektu (tam gdzie jest app.py, core/, legacy_root_py/ itd.)
ROOT = Path(__file__).resolve().parent.parent

# upewnij się, że root jest w sys.path
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXCLUDE_DIRS = {
    ".venv",
    "venv",
    "tests",
    "scripts",
    "frontend",
    "webui",
    "nginx",
    "docs",
    "__pycache__",
}

EXCLUDE_MODULES = {
    "app",
    "core.app",
    "core.app_fixed",
    "core.auto_router_loader",
}


def _iter_python_modules(root: Path) -> List[str]:
    """Zwraca listę nazw modułów do przeskanowania."""
    modules: List[str] = []

    for path in root.rglob("*.py"):
        # pomijamy śmieciowe katalogi
        if any(part in EXCLUDE_DIRS for part in path.parts):
            continue
        if any(part.startswith(".") for part in path.parts):
            continue

        rel = path.relative_to(root)
        parts = list(rel.parts)

        if parts[-1] == "__init__.py":
            continue

        parts[-1] = parts[-1].replace(".py", "")
        mod_name = ".".join(parts)

        if mod_name in EXCLUDE_MODULES:
            continue

        modules.append(mod_name)

    return sorted(set(modules))


def _is_apirouter(obj) -> bool:
    try:
        return isinstance(obj, APIRouter)
    except Exception:
        return False


def _collect_existing_signatures(app: FastAPI) -> Set[Tuple[str, Tuple[str, ...]]]:
    """Zbiera (path, metody) dla już podpiętych tras."""
    sigs: Set[Tuple[str, Tuple[str, ...]]] = set()
    for route in app.routes:
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", None) or set()
        methods_clean = tuple(sorted(m for m in methods if m not in {"HEAD", "OPTIONS"}))
        sigs.add((path, methods_clean))
    return sigs


def attach_all_routers(app: FastAPI) -> None:
    """
    Podpina WSZYSTKIE APIRouter z projektu do `app`,
    nie rozwalając istniejącej konfiguracji.

    - nie dotyka już podpiętych tras (sprawdza po (path, methods)),
    - każdemu routerowi próbuje zrobić include_router,
    - przy duplikatach / błędach wypisuje tylko ostrzeżenie.
    """
    print("======================================================================")
    print("[AUTO_ROUTERS] Start automatycznego podpinania wszystkich routerów")
    print("======================================================================")

    existing_sigs = _collect_existing_signatures(app)
    modules = _iter_python_modules(ROOT)

    total_routers = 0
    attached_routers = 0

    for mod_name in modules:
        try:
            mod = importlib.import_module(mod_name)
        except Exception as e:
            print(f"[AUTO_ROUTERS] [FAIL] Nie udalo sie zaimportowac {mod_name}: {e}")
            continue

        for attr_name in dir(mod):
            try:
                obj = getattr(mod, attr_name)
            except Exception:
                continue

            if not _is_apirouter(obj):
                continue

            router: APIRouter = obj  # type: ignore
            total_routers += 1

            # czy router wnosi cokolwiek nowego?
            has_new_route = False
            for route in router.routes:
                path = getattr(route, "path", "")
                methods = getattr(route, "methods", None) or set()
                methods_clean = tuple(
                    sorted(m for m in methods if m not in {"HEAD", "OPTIONS"})
                )
                sig = (path, methods_clean)
                if sig not in existing_sigs:
                    has_new_route = True
                    break

            if not has_new_route:
                print(
                    f"[AUTO_ROUTERS] [SKIP] Pomijam router {mod_name}.{attr_name} - "
                    f"wszystkie jego trasy sa juz w app"
                )
                continue

            try:
                app.include_router(router)
                attached_routers += 1
                existing_sigs = _collect_existing_signatures(app)
                print(f"[AUTO_ROUTERS] [OK] Podpieto router {mod_name}.{attr_name}")
            except Exception as e:
                print(
                    f"[AUTO_ROUTERS] [WARN] Problem z routerem {mod_name}.{attr_name}: {e}"
                )

    print("======================================================================")
    print(
        f"[AUTO_ROUTERS] Skan zakończony – znaleziono {total_routers} routerów, "
        f"nowo podpiętych: {attached_routers}"
    )
    print("======================================================================")
