# 🔥 MORDZIX AI - PEŁNY AUDYT I PLAN REFAKTORU

**Data audytu:** 2025-12-01  
**Wersja projektu:** Mix 3.3.0 / 4.0.0 / 5.0.0 (chaos wersji)  
**Autor audytu:** Senior Full-Stack / Architekt  

---

## 📊 STATYSTYKI PROJEKTU

| Metryka | Wartość |
|---------|---------|
| Plików łącznie | 185 |
| Rozmiar całkowity | 3.06 MB |
| Plików Python | 73 |
| Plików HTML | 5 |
| Entrypointów (serwery) | **4 (PROBLEM!)** |
| Duplikatów endpoint files | **6 (PROBLEM!)** |

---

## 🗺️ MAPA PROJEKTU

### Struktura katalogów

```
mordzix-ai/
├── .env                          # Konfiguracja (4.4KB)
├── .github/                      # GitHub config
├── core/                         # GŁÓWNY MODUŁ BACKEND (186 items!)
│   ├── __init__.py              # Eksporty modułów (127 linii)
│   ├── app.py                   # Entrypoint v5.0.0 (953 linii)
│   ├── app_fixed.py             # Entrypoint v5.0.1 (482 linii) - DUPLIKAT
│   ├── config.py                # Konfiguracja (466 linii)
│   ├── llm.py                   # Integracja LLM (426 linii)
│   ├── memory.py                # System pamięci (1768 linii, 75KB!)
│   ├── cognitive_engine.py      # Orchestrator AI (806 linii)
│   ├── tools_registry.py        # Registry narzędzi (1007 linii, 40KB)
│   ├── research.py              # Web research (793 linii)
│   ├── *_endpoint.py            # 17 endpointów
│   ├── legacy_versions/         # Stare wersje memory.py
│   └── ...                      # 50+ innych modułów
├── tests/                        # Testy (7 plików)
├── data/                         # Dane (feedback.db)
├── icons/                        # Ikony PWA (14 plików)
├── app.py                       # Entrypoint v4.0.0 (432 linii) - ROOT DUPLIKAT
├── app.py.OLD                   # Stary entrypoint - DO USUNIĘCIA
├── monolit.py                   # Mega-monolit 306KB (6577 linii!) - UŻYWANY W DOCKERFILE
├── chat.html                    # Frontend chat (79KB, 1717 linii)
├── chat_pro.html                # Frontend Pro (29KB, 878 linii)
├── index.html                   # Frontend PWA (12KB, 415 linii)
├── dashboard.html               # Dashboard (22KB)
├── *_endpoint.py                # 11 endpointów w ROOT - DUPLIKATY!
├── Dockerfile                   # Docker config
├── docker-compose.yml           # Docker compose
├── requirements.txt             # Dependencies
└── *.md                         # Dokumentacja (15+ plików)
```

### Backend - Entrypointy (PROBLEM: 4 różne!)

| Plik | Wersja | Linii | Status | Używane przez |
|------|--------|-------|--------|---------------|
| `app.py` (root) | 4.0.0 | 432 | ⚠️ DUPLIKAT | Dev lokalnie? |
| `core/app.py` | 5.0.0 | 953 | ✅ NAJNOWSZY | Nic (powinien być główny) |
| `core/app_fixed.py` | 5.0.1 | 482 | ⚠️ DUPLIKAT | Nic |
| `monolit.py` | 3.3.0 | 6577 | ⛔ STARY | **Dockerfile!** |

**🔴 KRYTYCZNE:** Dockerfile używa `monolit.py` ale dev prawdopodobnie używa `app.py`!

### Frontend - Pliki HTML (PROBLEM: 5 różnych!)

| Plik | Rozmiar | Linii | Opis |
|------|---------|-------|------|
| `chat.html` | 79KB | 1717 | Główny chat UI (inline CSS+JS) |
| `chat_pro.html` | 29KB | 878 | Alternatywny "Pro" UI |
| `index.html` | 12KB | 415 | PWA frontend |
| `dashboard.html` | 22KB | ~600 | Dashboard z feature'ami |
| `core/indexulr.html` | 82KB | ? | Nieużywany? |

**🔴 PROBLEM:** Wszystko inline (CSS+JS w HTML), brak build systemu, brak frameworka.

### Endpointy - Duplikaty (PROBLEM!)

**ROOT (11 plików):**
```
admin_endpoint.py       (44B - stub)
assistant_endpoint.py   (3.7KB)
captcha_endpoint.py     (3.3KB)
files_endpoint.py       (14.7KB)
internal_endpoint.py    (47B - stub)
programista_endpoint.py (8.2KB)
prometheus_endpoint.py  (8.4KB)
psyche_endpoint.py      (10.1KB)
stt_endpoint.py         (6KB)
travel_endpoint.py      (6.8KB)
tts_endpoint.py         (42B - stub)
```

**CORE (17 plików):**
```
assistant_endpoint.py   (7.9KB) - RÓŻNA WERSJA!
batch_endpoint.py       (5.6KB)
cognitive_endpoint.py   (18.4KB)
files_endpoint.py       (5.5KB) - RÓŻNA WERSJA!
hybrid_search_endpoint.py (22.2KB)
image_endpoint.py       (7.7KB)
lang_endpoint.py        (399B)
memory_endpoint.py      (3.7KB)
prometheus_endpoint.py  (961B) - RÓŻNA WERSJA!
psyche_endpoint.py      (6KB) - RÓŻNA WERSJA!
research_endpoint.py    (8.3KB)
stt_endpoint.py         (4.3KB) - RÓŻNA WERSJA!
suggestions_endpoint.py (5.2KB)
travel_endpoint.py      (6.8KB) - DUPLIKAT!
vision_endpoint.py      (4.1KB)
voice_endpoint.py       (8.4KB)
```

**🔴 DUPLIKATY (6 plików w obu lokalizacjach!):**
- `assistant_endpoint.py` - **RÓŻNE IMPLEMENTACJE!**
- `files_endpoint.py` - **RÓŻNE IMPLEMENTACJE!**
- `prometheus_endpoint.py` - **RÓŻNE IMPLEMENTACJE!**
- `psyche_endpoint.py` - **RÓŻNE IMPLEMENTACJE!**
- `stt_endpoint.py` - **RÓŻNE IMPLEMENTACJE!**
- `travel_endpoint.py` - Identyczne

### Chat-Related Files

**Endpointy chatu:**
- `POST /api/chat/assistant` - główny chat
- `POST /api/chat/assistant/stream` - streaming (symulowany!)
- `POST /api/chat/auto` - auto-learn

**Moduły LLM:**
- `core/llm.py` - DeepInfra API integration (426 linii)
- `core/advanced_llm.py` - rozszerzenia (2.5KB)
- `core/cognitive_engine.py` - orchestrator (806 linii)
- `core/advanced_cognitive_engine.py` - zaawansowany (32.7KB)

**Moduły pamięci:**
- `core/memory.py` - główny system (1768 linii, 75KB!)
- `core/hierarchical_memory.py` - hierarchiczna (43.7KB)
- `core/memory_store.py` - prosty store (14.7KB)
- `core/memory_endpoint.py` - API (3.7KB)
- `core/memory_persistence.py` - persistence (20.6KB)
- `core/advanced_memory.py` - zaawansowane (8.7KB)

---

## 🚨 PROBLEMY

### 1. KRYTYCZNE (Blokery)

#### 1.1 Cztery różne serwery/entrypointy
**Pliki:** `app.py`, `core/app.py`, `core/app_fixed.py`, `monolit.py`  
**Powaga:** 🔴 KRYTYCZNA  
**Problem:** Nie wiadomo który uruchamiać. Dockerfile używa `monolit.py` (stary), a dev używa `app.py`.  
**Rozwiązanie:** Wybrać JEDEN (`core/app.py`), usunąć resztę.

#### 1.2 Dockerfile używa starego monolitu
**Plik:** `Dockerfile` linia 47: `CMD python -m uvicorn monolit:app`  
**Powaga:** 🔴 KRYTYCZNA  
**Problem:** Produkcja uruchamia 306KB monolit zamiast zmodularyzowanego kodu.  
**Rozwiązanie:** Zmienić na `core.app:app`.

#### 1.3 Hardcoded auth token
**Pliki:** `app.py`, `assistant_endpoint.py`, `chat.html`, `chat_pro.html`, `dashboard.html`, `tests/`  
**Token:** `ssjjMijaja6969`  
**Powaga:** 🔴 KRYTYCZNA  
**Problem:** Token jest hardcoded w 8+ plikach, w tym w publicznym HTML!  
**Rozwiązanie:** Usunąć ze wszystkich plików, używać tylko z `.env`.

#### 1.4 Duplikaty endpoint files z RÓŻNYMI implementacjami
**Pliki:** 6 par plików (root vs core/)  
**Powaga:** 🔴 KRYTYCZNA  
**Problem:** `assistant_endpoint.py` w root (99 linii) vs core/ (202 linii) - RÓŻNA LOGIKA!  
**Rozwiązanie:** Usunąć wszystkie z root, używać tylko core/.

### 2. WYSOKIE

#### 2.1 Monolit 306KB nieużywany ale w repo
**Plik:** `monolit.py` (6577 linii)  
**Powaga:** 🟠 WYSOKA  
**Problem:** Ogromny plik który powinien być zmodularyzowany (już jest w core/).  
**Rozwiązanie:** Usunąć lub przenieść do archive/.

#### 2.2 Pięć różnych frontendów
**Pliki:** `chat.html`, `chat_pro.html`, `index.html`, `dashboard.html`, `core/indexulr.html`  
**Powaga:** 🟠 WYSOKA  
**Problem:** Brak jednego źródła prawdy dla UI.  
**Rozwiązanie:** Wybrać jeden frontend lub stworzyć nowy z frameworkiem.

#### 2.3 Symulowany streaming
**Plik:** `core/assistant_endpoint.py` linie 117-120  
**Powaga:** 🟠 WYSOKA  
**Problem:** Chunki 48 znaków co 10ms zamiast prawdziwego SSE od LLM.  
**Rozwiązanie:** Użyć `call_llm_stream` z prawdziwym SSE.

#### 2.4 Legacy files zaśmiecające repo
**Pliki:** `app.py.OLD`, `core/app.py.new` (pusty), `core/legacy_versions/`, `env.tmp`, `bn`  
**Powaga:** 🟠 WYSOKA  
**Rozwiązanie:** Usunąć lub przenieść do archive/.

### 3. ŚREDNIE

#### 3.1 Niespójne importy między root a core
**Problem:** Root endpointy używają `from core.X import Y`, core używa `.X`  
**Rozwiązanie:** Ustandaryzować na względne importy w core/.

#### 3.2 Brak session management na backendzie
**Problem:** Historia tylko w localStorage przeglądarki.  
**Rozwiązanie:** Dodać tabele sessions w SQLite, API do zarządzania.

#### 3.3 Pięć systemów pamięci
**Pliki:** `memory.py`, `hierarchical_memory.py`, `memory_store.py`, `advanced_memory.py`, `memory_persistence.py`  
**Problem:** Niespójne API, duplikacja funkcjonalności.  
**Rozwiązanie:** Użyć jednego unified memory z `memory.py`.

#### 3.4 Brak globalnego error handling
**Problem:** Każdy endpoint ma własny try/except.  
**Rozwiązanie:** Middleware do error handling.

### 4. NISKIE

#### 4.1 Brak .gitignore lub niekompletny
**Problem:** `__pycache__/`, `.mypy_cache/` w repo.  
**Rozwiązanie:** Dodać kompletny .gitignore.

#### 4.2 Dokumentacja rozproszona
**Pliki:** 15+ plików .md z nakładającą się treścią.  
**Rozwiązanie:** Skonsolidować do README.md + DEVELOPMENT.md.

---

## 📋 PLAN REFAKTORU (FAZY)

### PHASE 1 - Unifikacja Backendu
**Cel:** Jeden entrypoint, usunięcie duplikatów, czysta struktura.  
**Czas:** 1-2 dni

#### Pliki do ruszenia:
```
USUNĄĆ/PRZENIEŚĆ DO backup_legacy/:
- app.py (root)
- app.py.OLD
- monolit.py
- core/app_fixed.py
- core/app.py.new
- bn
- env.tmp
- mordzix-ai.zip
- Wszystkie *_endpoint.py z ROOT (11 plików)
- core/legacy_versions/
```

#### Kroki:

**1.1 Utwórz backup:**
```bash
mkdir backup_legacy
mv app.py backup_legacy/
mv app.py.OLD backup_legacy/
mv monolit.py backup_legacy/
mv core/app_fixed.py backup_legacy/
mv core/app.py.new backup_legacy/
mv bn backup_legacy/
mv env.tmp backup_legacy/
```

**1.2 Przenieś root endpointy:**
```bash
mv admin_endpoint.py backup_legacy/
mv assistant_endpoint.py backup_legacy/
mv captcha_endpoint.py backup_legacy/
mv files_endpoint.py backup_legacy/
mv internal_endpoint.py backup_legacy/
mv programista_endpoint.py backup_legacy/
mv prometheus_endpoint.py backup_legacy/
mv psyche_endpoint.py backup_legacy/
mv stt_endpoint.py backup_legacy/
mv travel_endpoint.py backup_legacy/
mv tts_endpoint.py backup_legacy/
```

**1.3 Napraw importy w `core/app.py`:**
- Linia 336: `import psyche_endpoint` → `from core import psyche_endpoint`
- Linia 346: `import programista_endpoint` → `from core import programista_endpoint`
- Etc. dla wszystkich zewnętrznych importów

**1.4 Utwórz nowy `main.py` w root:**
```python
#!/usr/bin/env python3
"""Mordzix AI - Entry Point"""
from core.app import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("core.app:app", host="0.0.0.0", port=8080, reload=True)
```

**1.5 Zaktualizuj Dockerfile:**
```dockerfile
# Linia 47 - zmień:
CMD ["uvicorn", "core.app:app", "--host", "0.0.0.0", "--port", "8080"]
```

**1.6 Test:**
```bash
python main.py
curl http://localhost:8080/health
curl http://localhost:8080/api/endpoints/list
```

---

### PHASE 2 - Naprawa Endpointu Chatu
**Cel:** Jeden oficjalny endpoint chatu z prawdziwym streamingiem.  
**Czas:** 1-2 dni

#### Pliki do ruszenia:
```
core/assistant_endpoint.py
core/llm.py
core/cognitive_engine.py
```

#### Docelowe API:

**POST /api/chat/assistant**

Request:
```json
{
  "messages": [
    {"role": "user", "content": "Cześć!"}
  ],
  "user_id": "user123",
  "session_id": "sess_abc123",
  "use_memory": true,
  "stream": false
}
```

Response:
```json
{
  "ok": true,
  "answer": "Hej! Co u Ciebie?",
  "session_id": "sess_abc123",
  "sources": [],
  "metadata": {
    "intent": "greeting",
    "model": "Qwen/Qwen3-Next-80B-A3B-Instruct",
    "processing_time_ms": 450
  }
}
```

**POST /api/chat/assistant/stream**

Response (SSE):
```
data: {"type": "start", "session_id": "sess_abc123"}

data: {"type": "chunk", "content": "Hej! "}

data: {"type": "chunk", "content": "Co u Ciebie?"}

data: {"type": "complete", "metadata": {...}}
```

#### Kroki:

**2.1 Napraw streaming w `core/llm.py`:**
```python
async def call_llm_stream_real(messages: List[dict], **opts):
    """Real SSE streaming from LLM API"""
    url = f"{LLM_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": opts.get("model", LLM_MODEL),
        "messages": messages,
        "stream": True,
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("POST", url, headers=headers, json=payload) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        content = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue
```

**2.2 Zaktualizuj `core/assistant_endpoint.py` - usunąć symulowany streaming (linie 117-120)**

**2.3 Test:**
```bash
# Non-streaming
curl -X POST http://localhost:8080/api/chat/assistant \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Cześć!"}]}'

# Streaming
curl -X POST http://localhost:8080/api/chat/assistant/stream \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Cześć!"}]}' \
  --no-buffer
```

---

### PHASE 3 - Unifikacja Frontendu
**Cel:** Jeden, nowoczesny frontend chatu.  
**Czas:** 2-3 dni

#### Pliki do ruszenia:
```
USUNĄĆ/PRZENIEŚĆ:
- chat.html → backup_legacy/
- chat_pro.html → backup_legacy/
- index.html → backup_legacy/
- dashboard.html → backup_legacy/
- core/indexulr.html → backup_legacy/

UTWORZYĆ:
- frontend/
  ├── index.html
  ├── css/
  │   └── styles.css
  └── js/
      ├── app.js
      ├── api.js
      └── chat.js
```

#### Docelowy Layout:
```
┌─────────────────────────────────────────────────────────────┐
│  [≡]  Mordzix AI                           [+] New Chat     │
├────────────┬────────────────────────────────────────────────┤
│  Sessions  │              Chat Messages                     │
│            │                                                │
│  ● Dzisiaj │    [User]: Cześć!                             │
│    └ Sess1 │                                                │
│    └ Sess2 │    [Mordzix]: Hej! Co mogę...                 │
│            │                                                │
│  ● Wczoraj │    [User]: Pomóż mi z kodem                   │
│    └ Sess3 │                                                │
├────────────┴────────────────────────────────────────────────┤
│  [📎] [🎤]  Napisz wiadomość...                    [Send]   │
└─────────────────────────────────────────────────────────────┘
```

#### Kroki:

**3.1 Utwórz strukturę:**
```bash
mkdir -p frontend/css frontend/js
```

**3.2 Utwórz `frontend/index.html`** - prosty HTML z dark theme

**3.3 Utwórz `frontend/js/api.js`:**
```javascript
const API_BASE = '';
const AUTH_TOKEN = localStorage.getItem('auth_token') || '';

export async function sendMessage(messages, sessionId, stream = true) {
  const url = `${API_BASE}/api/chat/assistant${stream ? '/stream' : ''}`;
  return fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${AUTH_TOKEN}`
    },
    body: JSON.stringify({ messages, session_id: sessionId })
  });
}

export async function getSessions() {
  return fetch(`${API_BASE}/api/sessions`, {
    headers: { 'Authorization': `Bearer ${AUTH_TOKEN}` }
  }).then(r => r.json());
}
```

**3.4 Zaktualizuj routing w `core/app.py`:**
```python
from fastapi.staticfiles import StaticFiles

# Serve frontend
app.mount("/css", StaticFiles(directory="frontend/css"), name="css")
app.mount("/js", StaticFiles(directory="frontend/js"), name="js")

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    with open("frontend/index.html") as f:
        return HTMLResponse(content=f.read())
```

**3.5 Test:**
```bash
python main.py
# Otwórz http://localhost:8080 w przeglądarce
```

---

### PHASE 4 - Sesje i Pamięć
**Cel:** Backend session management, ujednolicone memory API.  
**Czas:** 1-2 dni

#### Pliki do ruszenia:
```
UTWORZYĆ:
- core/sessions.py

ZMODYFIKOWAĆ:
- core/memory_endpoint.py
- core/app.py (dodać router)
```

#### Kroki:

**4.1 Utwórz `core/sessions.py`:**
```python
import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional
from .config import DB_PATH

def init_sessions_table():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT,
            messages TEXT NOT NULL DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def create_session(user_id: str, title: str = None) -> str:
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO sessions (id, user_id, title, messages) VALUES (?, ?, ?, ?)",
        (session_id, user_id, title or "New Chat", "[]")
    )
    conn.commit()
    conn.close()
    return session_id

def get_session(session_id: str) -> Optional[Dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def list_sessions(user_id: str, limit: int = 50) -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, title, created_at, updated_at FROM sessions WHERE user_id = ? ORDER BY updated_at DESC LIMIT ?",
        (user_id, limit)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
```

**4.2 Dodaj endpointy w `core/app.py`:**
```python
from .sessions import create_session, get_session, list_sessions

@app.post("/api/sessions")
async def api_create_session(user_id: str = "default"):
    session_id = create_session(user_id)
    return {"ok": True, "session_id": session_id}

@app.get("/api/sessions")
async def api_list_sessions(user_id: str = "default"):
    sessions = list_sessions(user_id)
    return {"ok": True, "sessions": sessions}

@app.get("/api/sessions/{session_id}")
async def api_get_session(session_id: str):
    session = get_session(session_id)
    return {"ok": True, "session": session}
```

**4.3 Test:**
```bash
curl -X POST "http://localhost:8080/api/sessions?user_id=test"
curl http://localhost:8080/api/sessions?user_id=test
```

---

### PHASE 5 - Cleanup i Security
**Cel:** Usunięcie hardcoded tokenów, cleanup dependencies.  
**Czas:** 1 dzień

#### Pliki do ruszenia:
```
- requirements.txt
- .gitignore (utworzyć/zaktualizować)
- Wszystkie pliki z hardcoded tokenem
```

#### Kroki:

**5.1 Usuń hardcoded token ze WSZYSTKICH plików:**
- `app.py` linia 57 - USUNIĘTY W PHASE 1
- `assistant_endpoint.py` linia 42 - zmień na `os.getenv("AUTH_TOKEN", "")`
- `chat.html` linia 708 - zmień na `localStorage.getItem('auth_token')`
- `chat_pro.html` linia 428 - zmień na `localStorage.getItem('auth_token')`
- `dashboard.html` linia 403 - zmień na `localStorage.getItem('auth_token')`

**5.2 Utwórz/zaktualizuj `.gitignore`:**
```gitignore
# Python
__pycache__/
*.pyc
*.pyo
.venv/
.mypy_cache/

# Data
*.db
*.sqlite
ltm_storage/
uploads/

# Config
.env
env.tmp

# IDE
.vscode/
.idea/

# Build
dist/
build/
*.egg-info/

# Backup
backup_legacy/
```

**5.3 Cleanup requirements.txt:**
```txt
# Core
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
pydantic>=2.9.0
python-dotenv>=1.0.0

# HTTP
httpx>=0.27.0
aiohttp>=3.9.0

# Database
aiosqlite>=0.20.0

# Web scraping
beautifulsoup4>=4.12.0
readability-lxml>=0.8.0
lxml>=5.2.0

# Utils
python-multipart>=0.0.9
orjson>=3.10.0
numpy>=1.26.0

# Monitoring
prometheus-client>=0.20.0

# Testing
pytest>=8.2.0
pytest-asyncio>=0.23.0
```

---

## 🚀 ULEPSZENIA / BOOSTY

### MUST HAVE (Duży impact, rozsądny koszt)

#### 1. Global Error Handler + Structured Logging
**Opis:** Centralne przechwytywanie błędów, spójne JSON response, logi z request ID.  
**Impact:** +stabilność, +debugging  
**Zakres:** Backend - `core/middleware.py`

**Implementacja:**
```python
# core/middleware.py
import logging
import json
import uuid
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "n/a")
        })

class GlobalErrorMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "ok": False,
                    "error": "internal_error",
                    "request_id": request_id
                }
            )
```

#### 2. Prawdziwy SSE Streaming
**Opis:** Stream z LLM API zamiast symulowanych chunków.  
**Impact:** +UX (szybsze odpowiedzi)  
**Zakres:** Backend - `core/llm.py`, `core/assistant_endpoint.py`

**Status:** Szczegóły w PHASE 2.

#### 3. Session Persistence
**Opis:** Sesje rozmów zapisywane na backendzie.  
**Impact:** +UX (historia po reload)  
**Zakres:** Backend + Frontend

**Status:** Szczegóły w PHASE 4.

### NICE TO HAVE (Fajny bonus)

#### 4. Connection Pooling dla LLM
**Opis:** Pool HTTP connections do LLM API.  
**Impact:** +wydajność  
**Zakres:** `core/llm.py`

```python
# Singleton AsyncClient
_llm_client: httpx.AsyncClient = None

def get_llm_client() -> httpx.AsyncClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = httpx.AsyncClient(
            timeout=60.0,
            limits=httpx.Limits(max_connections=100)
        )
    return _llm_client
```

#### 5. Response Caching
**Opis:** Cache dla powtarzalnych zapytań (Redis lub in-memory).  
**Impact:** +wydajność, -koszty API  
**Zakres:** `core/llm.py`

#### 6. Typing Indicators
**Opis:** Pokazywanie że AI "pisze".  
**Impact:** +UX  
**Zakres:** Frontend

#### 7. Message Reactions
**Opis:** Thumbs up/down na odpowiedzi AI.  
**Impact:** +UX, +feedback dla ML  
**Zakres:** Backend + Frontend

### FUTURE (Można później)

#### 8. Multi-modal Input
**Opis:** Obsługa obrazów/audio w chacie.  
**Impact:** +możliwości  
**Zakres:** Backend + Frontend

#### 9. Context Summarization
**Opis:** Automatyczne streszczanie długich konwersacji.  
**Impact:** +wydajność, +kontekst  
**Zakres:** `core/context_awareness.py`

#### 10. Conversation Analytics
**Opis:** Statystyki rozmów, popularne tematy.  
**Impact:** +insights  
**Zakres:** `core/conversation_analytics.py` (już istnieje - rozbudować)

---

## 📅 HARMONOGRAM

| Faza | Czas | Zależności |
|------|------|------------|
| PHASE 1 - Backend | 1-2 dni | - |
| PHASE 2 - Chat API | 1-2 dni | Phase 1 |
| PHASE 3 - Frontend | 2-3 dni | Phase 2 |
| PHASE 4 - Sessions | 1-2 dni | Phase 3 |
| PHASE 5 - Cleanup | 1 dzień | Phase 1-4 |
| **TOTAL** | **6-10 dni** | |

---

## ✅ CHECKLIST DLA WYKONAWCY

### Phase 1
- [ ] Utworzyć `backup_legacy/`
- [ ] Przenieść `app.py`, `app.py.OLD`, `monolit.py`
- [ ] Przenieść `core/app_fixed.py`, `core/app.py.new`
- [ ] Przenieść 11 endpoint files z root
- [ ] Naprawić importy w `core/app.py`
- [ ] Utworzyć `main.py`
- [ ] Zaktualizować `Dockerfile`
- [ ] Test: `curl http://localhost:8080/health`

### Phase 2
- [ ] Dodać `call_llm_stream_real` w `core/llm.py`
- [ ] Usunąć symulowany streaming
- [ ] Test: streaming endpoint

### Phase 3
- [ ] Utworzyć `frontend/` structure
- [ ] Przenieść stare HTML do backup
- [ ] Utworzyć nowy `index.html`, `app.js`, `api.js`
- [ ] Zaktualizować routing w `core/app.py`
- [ ] Test: UI w przeglądarce

### Phase 4
- [ ] Utworzyć `core/sessions.py`
- [ ] Dodać endpointy `/api/sessions`
- [ ] Zintegrować z chat endpoint
- [ ] Test: session CRUD

### Phase 5
- [ ] Usunąć hardcoded tokeny (8 plików)
- [ ] Zaktualizować `.gitignore`
- [ ] Cleanup `requirements.txt`
- [ ] Final test wszystkich endpointów

---

## 🎯 UNIKALNE SMACZKI - FEATURES KTÓRYCH NIE MA NIKT INNY

### 🧠 1. AI Memory Surgery (Chirurgia Pamięci)
**Opis:** User może EDYTOWAĆ co AI o nim pamięta. Dashboard z listą faktów które AI zapisał, możliwość usunięcia, edycji, dodania.

**Dlaczego unikalne:** Żaden chatbot nie daje takiej kontroli. ChatGPT/Claude mają "memory" ale nie możesz go edytować.

**Implementacja:**
```
GET  /api/memory/facts?user_id=X     → lista faktów o userze
PUT  /api/memory/facts/{id}          → edycja faktu
DELETE /api/memory/facts/{id}        → usunięcie
POST /api/memory/facts               → dodanie ręczne
```

**UI:** Sekcja "Co o Tobie wiem" w sidebar z edytowalnymi tagami.

---

### 🔀 2. Conversation Branching (Rozwidlenia Rozmów)
**Opis:** W dowolnym momencie rozmowy kliknij "Fork" i stwórz alternatywną wersję. Jak Git branches ale dla konwersacji.

**Dlaczego unikalne:** Możesz eksplorować "co by było gdyby zapytał inaczej" bez tracenia oryginalnej rozmowy.

**Implementacja:**
```python
# sessions table
parent_session_id TEXT,  -- NULL = root, inaczej = fork
fork_point_msg_id INT,   -- od której wiadomości fork
```

**UI:** Timeline z gałęziami, możliwość przeskakiwania między wersjami.

---

### 🎭 3. Persona Battles (Bitwy Osobowości)
**Opis:** Dwie persony AI debatują ze sobą na zadany temat. User ogląda i może interweniować.

**Dlaczego unikalne:** Nikt tego nie ma. Możesz zobaczyć jak "Mordzix-Brutal" kłóci się z "Mordzix-Filozof" o sens życia.

**Implementacja:**
```
POST /api/chat/battle
{
  "topic": "Czy AI zastąpi programistów?",
  "persona_a": "brutal_realist",
  "persona_b": "tech_optimist",
  "rounds": 5
}
```

**UI:** Split-screen z dwoma bąbelkami, animowane "versus".

---

### ⏰ 4. Time-Travel Context
**Opis:** Zapytaj AI "Co rozmawialiśmy o Pythonie 3 miesiące temu?" i dostaniesz podsumowanie z linkami do oryginalnych rozmów.

**Dlaczego unikalne:** Semantic search po CAŁEJ historii z timeline visualization.

**Implementacja:**
```
POST /api/memory/time-travel
{
  "query": "Python",
  "time_range": "3 months ago",
  "user_id": "X"
}
```

**Zwraca:** Timeline z highlights, cytaty, linki do pełnych sesji.

---

### 📊 5. AI Confidence Meter
**Opis:** Przy każdej odpowiedzi pokazuj "Pewność: 87%" z wyjaśnieniem skąd.

**Dlaczego unikalne:** Transparentność. User wie kiedy AI gada z dupy a kiedy jest pewny.

**Implementacja:**
```python
# W odpowiedzi:
{
  "answer": "...",
  "confidence": 0.87,
  "confidence_factors": {
    "memory_matches": 0.9,
    "web_sources": 0.85,
    "model_certainty": 0.86
  }
}
```

**UI:** Pasek confidence pod odpowiedzią, hover pokazuje breakdown.

---

### 🔮 6. Predictive Suggestions (Proaktywne Podpowiedzi)
**Opis:** AI przewiduje co zapytasz ZANIM napiszesz. "Pewnie chcesz wiedzieć o..." na podstawie kontekstu.

**Dlaczego unikalne:** Nie czeka na pytanie - sugeruje kierunki rozmowy.

**Implementacja:**
```python
# Po każdej odpowiedzi AI generuje:
{
  "suggestions": [
    {"text": "Pokaż mi przykład kodu", "confidence": 0.82},
    {"text": "Wyjaśnij to prościej", "confidence": 0.71},
    {"text": "Jakie są alternatywy?", "confidence": 0.65}
  ]
}
```

**UI:** Chipsy pod odpowiedzią, klik = wysyłka jako wiadomość.

---

### 🎮 7. Achievement System (Gamifikacja)
**Opis:** Odznaki za używanie AI: "Pierwszy tysiąc wiadomości", "Nocna sowa", "Code Master", "Polyglot".

**Dlaczego unikalne:** Engagement + fun factor. Ludzie będą chcieli "odblokowywać" achievementy.

**Implementacja:**
```sql
CREATE TABLE achievements (
  id TEXT PRIMARY KEY,
  user_id TEXT,
  achievement_type TEXT,  -- messages_1000, night_owl, code_master
  unlocked_at TIMESTAMP,
  metadata JSON
);
```

**Achievementy:**
- 🌙 **Nocna Sowa** - 50 rozmów po północy
- 💻 **Code Master** - 100 pytań o kod
- 🧠 **Memory Lord** - 500 faktów w LTM
- 🌍 **Polyglot** - rozmowy w 5 językach
- 🔥 **Streak Master** - 30 dni z rzędu
- 🎭 **Persona Collector** - użycie wszystkich person

---

### 📸 8. Screenshot-to-Context
**Opis:** Wklej screenshot → AI go analizuje i automatycznie dodaje do kontekstu rozmowy.

**Dlaczego unikalne:** Bezpośrednia integracja. Nie musisz opisywać co widzisz.

**Implementacja:**
```
POST /api/vision/screenshot
{
  "image_base64": "...",
  "session_id": "..."
}

# Zwraca:
{
  "description": "Screenshot IDE z błędem Python: ImportError...",
  "extracted_code": "from xyz import abc",
  "suggested_action": "Wygląda na błąd importu. Chcesz żebym pomógł?"
}
```

**UI:** Paste (Ctrl+V) w input → auto-upload → preview + analiza.

---

### 🔄 9. Response Regeneration z Parametrami
**Opis:** "Regeneruj" ale z opcjami: "Krócej", "Dłużej", "Bardziej technicznie", "Jak dla 5-latka", "Z przykładami".

**Dlaczego unikalne:** Kontrola nad stylem odpowiedzi bez ponownego pytania.

**Implementacja:**
```
POST /api/chat/regenerate
{
  "message_id": "msg_123",
  "modifiers": ["shorter", "more_examples", "eli5"]
}
```

**UI:** Dropdown przy "Regeneruj" z checkboxami.

---

### 🧩 10. Custom Tool Builder
**Opis:** User może stworzyć własne "narzędzie" AI przez UI. Np. "Mój Tłumacz PL→DE" z custom promptem.

**Dlaczego unikalne:** Każdy user ma własne mikro-aplikacje w AI.

**Implementacja:**
```sql
CREATE TABLE custom_tools (
  id TEXT PRIMARY KEY,
  user_id TEXT,
  name TEXT,
  description TEXT,
  system_prompt TEXT,
  parameters JSON,
  icon TEXT,
  created_at TIMESTAMP
);
```

**UI:** "Tool Builder" w settings → drag-and-drop parametry, test preview.

---

### 📡 11. Proactive Notifications
**Opis:** AI wysyła powiadomienia gdy ma coś istotnego: "Hej, znalazłem update do Twojego pytania o React z zeszłego tygodnia!"

**Dlaczego unikalne:** AI nie jest pasywny - sam inicjuje kontakt gdy ma wartość do dodania.

**Implementacja:**
- Background job sprawdzający:
  - Nowe info na tematy z poprzednich rozmów
  - Przypomnienia o niedokończonych zadaniach
  - Celebracje achievementów
- WebSocket/Push notifications

---

### 🎨 12. Mood-Aware Responses
**Opis:** AI analizuje Twój nastrój z tekstu i dostosowuje styl odpowiedzi. Smutny → więcej wsparcia, zestresowany → krótsze odpowiedzi.

**Dlaczego unikalne:** Emotional intelligence w praktyce.

**Implementacja:**
```python
# W cognitive_engine.py:
user_mood = analyze_sentiment(last_messages)

if user_mood == "stressed":
    response_style = "concise, calming"
elif user_mood == "curious":
    response_style = "detailed, exploratory"
elif user_mood == "frustrated":
    response_style = "solution-focused, empathetic"
```

---

### 🔗 13. Cross-Session Learning (Opt-in)
**Opis:** Learningi z rozmów jednego usera mogą (za zgodą) pomagać innym. "10 osób pytało o to samo - oto najlepsza odpowiedź."

**Dlaczego unikalne:** Collective intelligence bez naruszania prywatności.

**Implementacja:**
```sql
CREATE TABLE shared_knowledge (
  id TEXT PRIMARY KEY,
  topic TEXT,
  best_answer TEXT,
  upvotes INT,
  source_sessions TEXT[],  -- anonimowe
  created_at TIMESTAMP
);
```

---

### 📝 14. Conversation Templates
**Opis:** Zapisz "szablon rozmowy" i użyj go ponownie. Np. "Code Review Template", "Brainstorm Session", "Debug Helper".

**Dlaczego unikalne:** Reusable conversation patterns.

**Implementacja:**
```json
{
  "template_name": "Code Review",
  "initial_messages": [
    {"role": "system", "content": "Jesteś senior code reviewerem..."},
    {"role": "assistant", "content": "Wklej kod do review. Sprawdzę: 1) Bugs 2) Performance 3) Best practices"}
  ],
  "suggested_followups": ["Pokaż alternatywę", "Wyjaśnij bug", "Napisz testy"]
}
```

---

### ⚡ 15. Instant Actions (Slash Commands)
**Opis:** Wpisz `/tlumacz cześć` → natychmiastowe tłumaczenie bez pełnej odpowiedzi AI.

**Dlaczego unikalne:** Power-user shortcuts dla częstych akcji.

**Komendy:**
```
/tlumacz [tekst]     → tłumaczenie
/code [język]        → tryb code-only
/eli5 [temat]        → wyjaśnienie dla 5-latka
/summarize           → podsumuj ostatnie 10 wiadomości
/export              → eksport rozmowy
/mood                → pokaż nastrój AI
/facts               → co AI o mnie wie
/forget [temat]      → zapomnij o temacie
```

---

## 🏆 RANKING SMACZKÓW (Impact vs Effort)

| Smaczek | Impact | Effort | Priority |
|---------|--------|--------|----------|
| Predictive Suggestions | 🔥🔥🔥 | ⏱️ | **DO TERAZ** |
| AI Confidence Meter | 🔥🔥🔥 | ⏱️ | **DO TERAZ** |
| Slash Commands | 🔥🔥🔥 | ⏱️ | **DO TERAZ** |
| Screenshot-to-Context | 🔥🔥🔥 | ⏱️⏱️ | **DO TERAZ** |
| Response Regen z Params | 🔥🔥 | ⏱️ | SOON |
| Memory Surgery | 🔥🔥 | ⏱️⏱️ | SOON |
| Achievement System | 🔥🔥 | ⏱️⏱️ | SOON |
| Mood-Aware Responses | 🔥🔥 | ⏱️⏱️ | SOON |
| Conversation Branching | 🔥🔥 | ⏱️⏱️⏱️ | LATER |
| Persona Battles | 🔥🔥🔥 | ⏱️⏱️⏱️ | LATER |
| Time-Travel Context | 🔥🔥 | ⏱️⏱️⏱️ | LATER |
| Custom Tool Builder | 🔥🔥🔥 | ⏱️⏱️⏱️⏱️ | FUTURE |
| Proactive Notifications | 🔥🔥 | ⏱️⏱️⏱️ | FUTURE |
| Conversation Templates | 🔥 | ⏱️⏱️ | FUTURE |
| Cross-Session Learning | 🔥🔥 | ⏱️⏱️⏱️⏱️ | FUTURE |

---

## 💎 TOP 4 SMACZKI DO WDROŻENIA NATYCHMIAST

### 1. Predictive Suggestions
**Pliki:** `core/cognitive_engine.py`, `core/assistant_endpoint.py`, frontend

```python
# W odpowiedzi chatu dodaj:
async def generate_suggestions(context: str, last_response: str) -> List[dict]:
    prompt = f"""Na podstawie rozmowy zaproponuj 3 follow-up pytania które user prawdopodobnie zada.
    Kontekst: {context}
    Ostatnia odpowiedź: {last_response}
    
    Zwróć JSON: [{{"text": "...", "confidence": 0.0-1.0}}]"""
    
    result = await call_llm([{"role": "user", "content": prompt}], temperature=0.7)
    return json.loads(result)
```

### 2. AI Confidence Meter
**Pliki:** `core/cognitive_engine.py`

```python
def calculate_confidence(
    memory_results: List,
    web_sources: List,
    model_response: str
) -> dict:
    memory_score = min(len(memory_results) / 5, 1.0) if memory_results else 0.3
    web_score = min(len(web_sources) / 3, 1.0) if web_sources else 0.4
    
    # Heurystyki dla pewności modelu
    hedging_phrases = ["może", "prawdopodobnie", "nie jestem pewien", "chyba"]
    hedging_count = sum(1 for p in hedging_phrases if p in model_response.lower())
    model_score = max(0.5, 1.0 - (hedging_count * 0.15))
    
    overall = (memory_score * 0.3 + web_score * 0.3 + model_score * 0.4)
    
    return {
        "overall": round(overall, 2),
        "factors": {
            "memory_matches": round(memory_score, 2),
            "web_sources": round(web_score, 2),
            "model_certainty": round(model_score, 2)
        }
    }
```

### 3. Slash Commands
**Pliki:** `core/assistant_endpoint.py`, frontend

```python
SLASH_COMMANDS = {
    "/tlumacz": {"handler": "translate", "args": ["text"]},
    "/eli5": {"handler": "explain_simple", "args": ["topic"]},
    "/summarize": {"handler": "summarize_chat", "args": []},
    "/mood": {"handler": "show_mood", "args": []},
    "/facts": {"handler": "show_facts", "args": []},
    "/forget": {"handler": "forget_topic", "args": ["topic"]},
}

def parse_slash_command(message: str) -> Optional[dict]:
    if not message.startswith("/"):
        return None
    
    parts = message.split(" ", 1)
    cmd = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""
    
    if cmd in SLASH_COMMANDS:
        return {"command": cmd, "args": args, "config": SLASH_COMMANDS[cmd]}
    return None
```

### 4. Screenshot-to-Context
**Pliki:** `core/vision_endpoint.py`, frontend

```python
@router.post("/screenshot")
async def analyze_screenshot(
    image: UploadFile,
    session_id: str = None,
    _=Depends(_auth)
):
    # 1. OCR dla tekstu
    text = await extract_text_ocr(image)
    
    # 2. Vision model dla opisu
    description = await describe_image(image)
    
    # 3. Wykryj typ contentu
    content_type = detect_content_type(text, description)  # code, error, ui, document
    
    # 4. Suggested action
    if content_type == "error":
        suggestion = "Widzę błąd. Chcesz żebym pomógł go naprawić?"
    elif content_type == "code":
        suggestion = "Widzę kod. Chcesz review, wyjaśnienie, czy optymalizację?"
    else:
        suggestion = "Co chcesz zrobić z tym obrazem?"
    
    return {
        "ok": True,
        "description": description,
        "extracted_text": text,
        "content_type": content_type,
        "suggested_action": suggestion
    }
```

---

**KONIEC DOKUMENTU**

*Ten plan jest gotowy do wykonania krok po kroku.*
*Smaczki wyróżnią Mordzix AI na tle konkurencji.*
