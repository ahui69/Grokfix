# 🚀 MORDZIX AI PRO

> **Profesjonalna platforma AI z zaawansowanymi modułami**

![Version](https://img.shields.io/badge/version-6.0.0-blue)
![Status](https://img.shields.io/badge/status-production-green)
![Endpoints](https://img.shields.io/badge/endpoints-186+-purple)
![License](https://img.shields.io/badge/license-proprietary-red)

---

## 📋 Spis treści

- [Architektura](#-architektura)
- [Szybki start](#-szybki-start)
- [Moduły](#-moduły)
- [API Endpoints](#-api-endpoints)
- [Frontend](#-frontend)
- [Konfiguracja](#-konfiguracja)
- [Deployment](#-deployment)

---

## 🏗️ Architektura

```
mordzix-ai/
├── core/                      # Backend modules
│   ├── app.py                 # Main FastAPI application
│   ├── llm.py                 # LLM integration (GLM-4, OpenAI)
│   ├── memory.py              # Multi-layer memory system
│   ├── cognitive_engine.py    # Cognitive processing
│   ├── legal_office_endpoint.py   # 📜 Moduł pism urzędowych
│   ├── media_endpoint.py      # 🎤 TTS + Image Generation
│   ├── programista_endpoint.py # 💻 Code execution
│   └── ... (31 endpoint modules)
│
├── frontend/                  # Web UI
│   ├── index.html            # Main chat interface
│   ├── legal.html            # Legal documents module
│   ├── admin.html            # Admin panel
│   ├── css/styles.css        # Professional styling
│   └── js/
│       ├── api.js            # API client
│       └── chat.js           # Chat logic
│
├── main.py                   # Entry point
├── start.bat / start.sh      # Startup scripts
├── requirements.txt          # Dependencies
└── .env                      # Configuration
```

---

## 🚀 Szybki start

### Windows
```powershell
# 1. Klonuj repozytorium
git clone https://github.com/your-repo/mordzix-ai.git
cd mordzix-ai

# 2. Utwórz środowisko
python -m venv venv
.\venv\Scripts\activate

# 3. Zainstaluj zależności
pip install -r requirements.txt

# 4. Skonfiguruj .env (skopiuj .env.example)
copy .env.example .env
# Edytuj .env i ustaw klucze API

# 5. Uruchom
.\start.bat
# lub
python main.py
```

### Linux / Mac
```bash
chmod +x start.sh
./start.sh
```

### Dostęp
- **Chat UI:** http://localhost:8080
- **Admin Panel:** http://localhost:8080/admin
- **Pisma Urzędowe:** http://localhost:8080/legal
- **API Docs:** http://localhost:8080/docs

---

## 📦 Moduły

### 💬 Chat AI
Główny interfejs konwersacyjny z:
- Streaming responses
- Context memory (STM + LTM)
- Web search integration
- File attachments
- Voice input (STT)

### ⚖️ Pisma Urzędowe (Legal Office)
Profesjonalny moduł do obsługi korespondencji urzędowej:

| Instytucja | Obsługiwane pisma | Terminy |
|------------|-------------------|---------|
| **Urząd Skarbowy** | Odwołania, zażalenia, wnioski | 7-30 dni |
| **ZUS** | Odwołania, sprzeciwy od orzeczeń | 14-30 dni |
| **Komornik Sądowy** | Skargi na czynności, wnioski | 7 dni |
| **Sąd Cywilny** | Sprzeciwy od nakazów, apelacje | 7-60 dni |
| **Prokuratura** | Zażalenia, wyjaśnienia | 7-30 dni |
| **WSA/NSA** | Skargi administracyjne | 30 dni |
| **Urząd Miasta** | Odwołania, wnioski | 14 dni |
| **PIP** | Odwołania od nakazów | 14 dni |

**Funkcje:**
- ✅ OCR skanów pism (Vision API)
- ✅ Automatyczna identyfikacja instytucji i typu pisma
- ✅ Generowanie odpowiedzi z podstawami prawnymi
- ✅ Kalkulator terminów
- ✅ Baza 50+ aktów prawnych
- ✅ Wiedza ekonomiczna (odsetki, przedawnienie, opłaty)

### 🎤 Media Module
- **TTS (Text-to-Speech):** ElevenLabs, Edge TTS
- **Image Generation:** Stability AI, Replicate
- **OCR:** Vision API (GLM-4V)

### 💻 Programista (Code Executor)
- Wykonywanie kodu Python
- Analiza i refaktoryzacja
- Linting i formatowanie
- Zarządzanie zależnościami

### 🧠 Memory System
Multi-warstwowy system pamięci:
- **STM:** Short-Term Memory (sesja)
- **LTM:** Long-Term Memory (SQLite + embeddings)
- **Associative:** Graf asocjacji
- **Decay:** Automatyczne zapominanie

### 🔍 Web Search
- Tavily API
- Brave Search
- DuckDuckGo
- Auto-detekcja intencji

---

## 🔌 API Endpoints

### Główne kategorie (186+ endpointów)

| Kategoria | Prefix | Endpointy |
|-----------|--------|-----------|
| Chat | `/api/chat` | 8 |
| Sessions | `/api/sessions` | 12 |
| Memory | `/api/memory` | 15 |
| Legal Office | `/api/legal` | 6 |
| Media (TTS/Images) | `/api/tts`, `/api/media` | 8 |
| Code | `/api/code` | 12 |
| NLP | `/api/nlp` | 10 |
| Search | `/api/search`, `/api/research` | 14 |
| ML | `/api/ml` | 8 |
| Admin | `/api/admin` | 10 |
| Cognitive | `/api/cognitive` | 12 |
| Vision | `/api/vision` | 6 |
| ... | ... | ... |

### Przykłady użycia

#### Chat
```bash
curl -X POST http://localhost:8080/api/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Cześć!", "session_id": "abc123"}'
```

#### Analiza pisma urzędowego
```bash
curl -X POST http://localhost:8080/api/legal/analyze \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "content=Treść pisma..." \
  -F "is_image=false"
```

#### Generowanie odpowiedzi prawnej
```bash
curl -X POST http://localhost:8080/api/legal/generate-response \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "document_analysis": {...},
    "response_type": "odwolanie",
    "user_arguments": "Nie zgadzam się z decyzją..."
  }'
```

#### TTS
```bash
curl -X POST http://localhost:8080/api/tts/generate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "Witaj świecie!", "voice": "adam"}'
```

---

## 🖥️ Frontend

### Strony

| URL | Opis |
|-----|------|
| `/` | Główny chat |
| `/legal` | Moduł pism urzędowych |
| `/admin` | Panel administracyjny |
| `/docs` | Swagger API docs |

### Funkcje UI

- 🌙 Dark/Light theme
- ⌨️ Keyboard shortcuts (Ctrl+K, Ctrl+N)
- 📎 File attachments
- 🎤 Voice input
- 🔊 TTS output
- 📱 Responsive design
- ⚡ Real-time streaming

---

## ⚙️ Konfiguracja

### Zmienne środowiskowe (.env)

```env
# === AUTHENTICATION ===
AUTH_TOKEN=your_secret_token

# === LLM ===
LLM_PROVIDER=zhipu          # openai, zhipu, local
ZHIPU_API_KEY=your_key
OPENAI_API_KEY=your_key     # optional
LLM_MODEL=glm-4-flash
TEMPERATURE=0.7
MAX_TOKENS=4096

# === MEMORY ===
MEMORY_ENABLED=true
MEMORY_STM_SIZE=100
MEMORY_LTM_SIZE=10000

# === WEB SEARCH ===
TAVILY_API_KEY=your_key
BRAVE_API_KEY=your_key

# === MEDIA ===
ELEVENLABS_API_KEY=your_key
STABILITY_API_KEY=your_key
REPLICATE_API_KEY=your_key

# === SERVER ===
HOST=0.0.0.0
PORT=8080
```

---

## 🚢 Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8080

CMD ["python", "main.py"]
```

```bash
docker build -t mordzix-ai .
docker run -p 8080:8080 --env-file .env mordzix-ai
```

### Docker Compose

```yaml
version: '3.8'
services:
  mordzix:
    build: .
    ports:
      - "8080:8080"
    env_file:
      - .env
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

### VPS (OVH/DigitalOcean)

```bash
# 1. SSH do serwera
ssh user@your-server

# 2. Klonuj repo
git clone https://github.com/your-repo/mordzix-ai.git
cd mordzix-ai

# 3. Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Konfiguracja
cp .env.example .env
nano .env

# 5. Systemd service
sudo nano /etc/systemd/system/mordzix.service
```

```ini
[Unit]
Description=Mordzix AI
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/mordzix-ai
ExecStart=/path/to/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable mordzix
sudo systemctl start mordzix
```

---

## 📊 Statystyki

| Metryka | Wartość |
|---------|---------|
| Endpointy API | 186+ |
| Routers | 31 |
| Akty prawne | 50+ |
| Instytucje | 10 |
| Typy odpowiedzi | 6 |
| Frontend pages | 3 |

---

## 🔒 Bezpieczeństwo

- Token-based authentication (Bearer)
- Rate limiting (60 req/min)
- Input sanitization
- XSS protection (DOMPurify)
- CORS configuration

---

## 📞 Support

- **Docs:** http://localhost:8080/docs
- **Admin:** http://localhost:8080/admin
- **Issues:** GitHub Issues

---

**© 2024 Mordzix AI PRO - All Rights Reserved**
