# 🧹 RAPORT CZYSZCZENIA PROJEKTU MORDZIX AI

## ✅ PLIKI DO ZACHOWANIA (UŻYWANE)

### 📦 GŁÓWNE PLIKI APLIKACJI
- `app.py` - główna aplikacja FastAPI ⭐
- `chat_pro.html` - interfejs użytkownika (Twój) ⭐
- `chat.html` - backup interfejsu

### 🔌 ENDPOINTY (WSZYSTKIE UŻYWANE)
- `assistant_endpoint.py` - główny chat ⭐
- `psyche_endpoint.py` - stan psychiczny AI ⭐
- `programista_endpoint.py` - wykonywanie kodu ⭐
- `files_endpoint.py` - upload i analiza plików ⭐
- `travel_endpoint.py` - wyszukiwanie podróży ⭐
- `admin_endpoint.py` - statystyki i cache ⭐
- `captcha_endpoint.py` - rozwiązywanie captcha ⭐
- `prometheus_endpoint.py` - metryki ⭐
- `tts_endpoint.py` - text-to-speech ⭐
- `stt_endpoint.py` - speech-to-text ⭐
- `writing_endpoint.py` - generowanie tekstów ⭐
- `suggestions_endpoint.py` - proaktywne sugestie ⭐
- `batch_endpoint.py` - przetwarzanie wsadowe ⭐

### 🧠 CORE MODULES (LOGIKA BIZNESOWA)
- `core/config.py` - konfiguracja
- `core/auth.py` - autoryzacja
- `core/llm.py` - komunikacja z LLM
- `core/memory.py` - pamięć STM/LTM
- `core/semantic.py` - analiza semantyczna
- `core/research.py` - autonauka i research
- `core/tools.py` - narzędzia (search, news)
- `core/writing.py` - pisanie tekstów
- `core/executor.py` - wykonywanie kodu
- `core/helpers.py` - funkcje pomocnicze
- `core/cognitive_engine.py` - silnik kognitywny ⭐
- `core/hierarchical_memory.py` - pamięć hierarchiczna ⭐
- `core/advanced_psychology.py` - psychologia zaawansowana ⭐
- `core/user_model.py` - model użytkownika ⭐
- `core/multi_agent_orchestrator.py` - system wieloagentowy ⭐
- `core/knowledge_compression.py` - kompresja wiedzy ⭐

### 🔧 POMOCNICZE MODUŁY
- `assistant_auto.py` - wrapper automatyzacji ⭐
- `batch_processing.py` - przetwarzanie wsadowe LLM ⭐
- `advanced_proactive.py` - zaawansowane sugestie (używane przez suggestions_endpoint) ⭐
- `vision_provider.py` - analiza obrazów ⭐
- `tts_elevenlabs.py` - ElevenLabs TTS ⭐
- `captcha_solver.py` - rozwiązywanie captcha ⭐

### 📄 KONFIGURACJA I DEPLOYMENT
- `.env` - zmienne środowiskowe
- `requirements.txt` - zależności Python
- `Dockerfile` - kontener Docker
- `docker-compose.yml` - orkiestracja
- `pytest.ini` - konfiguracja testów
- `manifest.webmanifest` - PWA manifest
- `sw.js` - service worker

### 📚 DOKUMENTACJA (PRZYDATNA)
- `README.md` - główna dokumentacja
- `API_EXAMPLES_AUTONAUKA.md` - przykłady API autonauki
- `AUTONAUKA_WIKI.md` - wiki autonauki
- `QUICK_START.md` - szybki start
- `DEPLOYMENT.md` - deployment

### 🗄️ DANE
- `mem.db` - baza danych pamięci ⭐
- `data/` - folder z danymi
- `out/` - folder wyjściowy
- `icons/` - ikony aplikacji

### 🧪 TESTY (OPCJONALNE - MOŻNA ZOSTAWIĆ)
- `tests/` - testy jednostkowe
- `test_autonauka_integration.py`
- `test_hierarchical_memory.py`

---

## ❌ PLIKI DO USUNIĘCIA (NIEUŻYWANE/DUPLIKATY)

### 🗑️ NIEUŻYWANE MODUŁY
- `advanced_llm.py` - NIE UŻYWANY (funkcjonalność w batch_processing.py)
- `enhanced_prompts.py` - NIE UŻYWANY (prompty są w core/)
- `proactive_suggestions.py` - STARA WERSJA (używamy advanced_proactive.py)
- `monolit.py` - STARY MONOLIT (wszystko przeniesione do core/) ⚠️

### 📁 DUPLIKATY I ARCHIWA
- `mordzix-ai/` - DUPLIKAT całego projektu
- `mordzix-ai.zip` - archiwum
- `.mypy_cache/` - cache mypy
- `.pytest_cache/` - cache pytest
- `__pycache__/` - cache Python

### 📝 ZBĘDNA DOKUMENTACJA
- `DASHBOARD_INFO.md` - nieaktualne
- `ENDPOINTS_STATUS.md` - nieaktualne
- `PERSONALITIES.md` - nieaktualne
- `README_AUTO.md` - duplikat
- `INSTALL_OVH.md` - specyficzne dla OVH
- `INSTALL_OVH_CORRECTED.txt` - specyficzne dla OVH
- `QUICK_START_OVH.txt` - specyficzne dla OVH
- `QUICK_START_WEB_ENABLED.md` - duplikat
- `START_OVH.sh` - specyficzne dla OVH

### 🔧 ZBĘDNE SKRYPTY
- `start_full.ps1` - nieużywany
- `start_full.sh` - nieużywany
- `personality_switcher.js` - nieużywany
- `stress_test_system.py` - test (można usunąć)
- `ultra_destruction_test.py` - test (można usunąć)

### 📊 LOGI I WYNIKI
- `server_error.txt` - stare logi
- `server_output.txt` - stare logi
- `stress_test_results.json` - wyniki testów
- `endpoints.json` - nieaktualne

### 🗂️ INNE
- `env.tmp` - tymczasowy plik
- `requirements_versioned.txt` - duplikat (mamy requirements.txt)
- `.github/` - jeśli nie używasz GitHub Actions

---

## 📊 PODSUMOWANIE

### ✅ ZACHOWUJEMY:
- **13 endpointów** - wszystkie działające
- **16 modułów core/** - pełna logika biznesowa
- **6 pomocniczych modułów** - używane przez endpointy
- **Konfiguracja i deployment** - Docker, requirements, .env
- **Dokumentacja** - tylko przydatna
- **Baza danych** - mem.db

### ❌ USUWAMY:
- **4 nieużywane moduły** - advanced_llm, enhanced_prompts, proactive_suggestions, monolit
- **Duplikaty** - mordzix-ai/, mordzix-ai.zip
- **Cache** - __pycache__, .mypy_cache, .pytest_cache
- **Zbędne docs** - 8 plików
- **Zbędne skrypty** - 5 plików
- **Logi i wyniki** - 4 pliki

### 💾 OSZCZĘDNOŚĆ MIEJSCA:
Szacunkowo **~50-100 MB** (głównie duplikaty i cache)

---

## ⚠️ UWAGA PRZED USUNIĘCIEM

### 🔴 KRYTYCZNE - NIE USUWAJ:
- `monolit.py` - MOŻE być używany przez stare importy (sprawdź!)
- `mem.db` - BAZA DANYCH z pamięcią AI
- `core/` - CAŁA logika biznesowa
- `.env` - zmienne środowiskowe

### 🟡 OPCJONALNE - MOŻESZ USUNĄĆ:
- `tests/` - jeśli nie testujesz
- Dokumentacja OVH - jeśli nie używasz OVH
- Stare logi i wyniki testów

### 🟢 BEZPIECZNE - USUŃ ŚMIAŁO:
- Cache folders (__pycache__, .mypy_cache, .pytest_cache)
- mordzix-ai/ i mordzix-ai.zip
- Nieużywane moduły (advanced_llm.py, enhanced_prompts.py)
