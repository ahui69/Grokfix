from core.assistant_endpoint import router as assistant_router
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================
MORDZIX AI PRO - Entry Point
Version: 6.0.0 (December 2025)
============================================

Zaawansowany asystent AI z:
- Pamięcią długoterminową
- Web search w czasie rzeczywistym
- Generowaniem obrazów
- Trybami: Tech, Sport, Moda/Vinted, HVAC/Budowlany, Pisma urzędowe
- Obsługą załączników (tekst, PDF, obrazy)
"""

import os
import sys
from pathlib import Path

# Dodaj katalog główny do PYTHONPATH
ROOT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(ROOT_DIR))

# Załaduj zmienne środowiskowe
from dotenv import load_dotenv
load_dotenv(ROOT_DIR / ".env")

from core.app import app

def print_banner():
    """Wyświetla banner startowy"""
    try:
        print("""
╔══════════════════════════════════════════════════════════════╗
║                    MORDZIX AI PRO 6.0                        ║
║══════════════════════════════════════════════════════════════║
║  Tryby:  Tech | Sport | Moda | HVAC | Legal                  ║
║  Features: Memory | WebSearch | Images | Files               ║
╚══════════════════════════════════════════════════════════════╝
""")
    except UnicodeEncodeError:
        print("\n=== MORDZIX AI PRO 6.0 ===\n")

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", os.getenv("BACKEND_PORT", "8080")))
    reload = os.getenv("RELOAD", "false").lower() == "true"
    workers = int(os.getenv("WORKERS", "1"))
    
    print_banner()
    print(f"[START] Host: {host}:{port}")
    print(f"[START] Workers: {workers}, Reload: {reload}")
    print(f"[START] Docs: http://localhost:{port}/docs")
    print(f"[START] Frontend: http://localhost:{port}/")
    print(f"[START] Admin: http://localhost:{port}/admin")
    print()
    
    uvicorn.run(
        "core.app:app",
        host=host,
        port=port,
        reload=reload,
        workers=1 if reload else workers,
        log_level="info",
        access_log=True
    )
