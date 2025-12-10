from __future__ import annotations
import sys
import importlib
import pkgutil
from pathlib import Path
from typing import Dict, List

try:
    from fastapi import APIRouter
except Exception:
    print("❌ Brak fastapi w venv – odpal to wewnątrz .venv")
    sys.exit(1)


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def iter_python_modules(root: Path) -> List[str]:
    """
    Zwraca listę nazw modułów do importu, np. core.assistant_endpoint,
    legacy_root_py.hacker_endpoint itd.
    """
    modules: List[str] = []

    for path in root.rglob("*.py"):
        # pomijamy śmieci
        if any(part.startswith(".") for part in path.parts):
            continue
        if ".venv" in path.parts or "venv" in path.parts:
            continue
        if path.name == "__init__.py":
            continue
        if path.parts and path.parts[0] in {"tests", "scripts"}:
            # testy / skrypty CI nas tu nie interesują
            continue

        rel = path.relative_to(ROOT)
        parts = list(rel.parts)
        parts[-1] = parts[-1].replace(".py", "")
        mod_name = ".".join(parts)
        modules.append(mod_name)

    return sorted(set(modules))


def is_apirouter(obj) -> bool:
    try:
        return isinstance(obj, APIRouter)
    except Exception:
        return False


def main() -> None:
    modules = iter_python_modules(ROOT)

    found: Dict[str, Dict[str, List[str]]] = {}

    for mod_name in modules:
        try:
            mod = importlib.import_module(mod_name)
        except Exception:
            # Nie panikujemy – niektóre moduły mogą wymagać rzeczy zewnętrznych
            continue

        for attr_name in dir(mod):
            try:
                attr = getattr(mod, attr_name)
            except Exception:
                continue

            if not is_apirouter(attr):
                continue

            router: APIRouter = attr  # type: ignore
            key = mod_name

            if key not in found:
                found[key] = {}

            routes_desc: List[str] = []
            for route in router.routes:
                path = getattr(route, "path", "<?>")
                methods = getattr(route, "methods", set())
                methods_s = ",".join(sorted(m for m in methods if m not in {"HEAD", "OPTIONS"}))
                routes_desc.append(f"{path} [{methods_s}]")

            found[key][attr_name] = sorted(routes_desc)

    print("======================================================================")
    print("WSZYSTKIE ZNALEZIONE APIRouter W PROJEKCIE (NIEZALEŻNIE OD include_router)")
    print("======================================================================")
    total_routes = 0
    total_routers = 0

    for mod_name in sorted(found.keys()):
        print(f"\n📦 {mod_name}")
        for router_name, routes in found[mod_name].items():
            total_routers += 1
            print(f"  └─ router: {router_name}  (liczba tras: {len(routes)})")
            for r in routes:
                print(f"      • {r}")
                total_routes += 1

    print("\n======================================================================")
    print(f"SUMA: {total_routers} routerów, {total_routes} tras (łącznie, nawet niewpiętych)")
    print("======================================================================")


if __name__ == "__main__":
    main()
