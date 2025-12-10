# -*- coding: utf-8 -*-
"""
MORDZIX AI - Production Server (root app.py)

- importuje główną aplikację z core.app
- odpala auto-router loader (podpina wszystkie APIRouter z projektu)
- startuje Uvicorna, gdy uruchomione jako `python app.py`
"""

from core.app import app
from core.auto_router_loader import attach_all_routers


# podpinamy wszystkie routery (legacy_root_py, stare endpointy itd.)
attach_all_routers(app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info",
    )
