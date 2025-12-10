# 🔥 MORDZIX AI DASHBOARD

## Nowy kompletny frontend ze wszystkimi endpointami!

### 📍 URL:
```
http://localhost:8080/dashboard
```

---

## ✅ CO MA DASHBOARD:

### 1. 💬 **CHAT AI**
- Pełna konwersacja z AI
- Pamięć, kontekst, auto-learning
- Link do pełnego czatu

### 2. 🎤 **VOICE (STT)**
- Upload pliku audio (mp3, wav, webm, ogg)
- Transkrypcja mowy na tekst
- 3 providery: OpenAI, Groq, DeepInfra

### 3. 🔊 **TEXT-TO-SPEECH**
- Zamień tekst na mowę
- 3 głosy: Rachel, Adam, Bella
- Odtwarzanie audio inline

### 4. 📁 **FILES**
- Upload plików (wielokrotny)
- Lista uploadowanych plików
- Analiza PDF/obrazów/OCR

### 5. ✈️ **TRAVEL**
- Wyszukiwanie hoteli
- Wyszukiwanie restauracji
- Atrakcje turystyczne
- Dowolne miasto

### 6. 🧠 **PSYCHE AI**
- Aktualny stan psychiczny AI
- Mood, energy, stress
- Reset psyche

### 7. ⚙️ **ADMIN**
- Cache statistics
- Clear cache
- Rate limiting info

### 8. 💾 **MEMORY (LTM)**
- Wyszukiwanie w pamięci długoterminowej
- Dodawanie nowych faktów
- Full-text search

### 9. 📊 **SYSTEM STATUS**
- Health check
- API status
- Auto-refresh przy otwarciu

---

## 🎨 DESIGN:

- ✅ Dark theme
- ✅ Responsywny (grid layout)
- ✅ Hover effects
- ✅ Loading states
- ✅ Error handling
- ✅ Wszystkie karty w jednym view
- ✅ No page reloads - AJAX

---

## 🔧 JAK UŻYWAĆ:

### 1. Uruchom serwer:
```bash
python3 app.py
# lub
./start.sh
```

### 2. Otwórz dashboard:
```
http://localhost:8080/dashboard
```

### 3. Wszystkie funkcje działają bez przeładowania strony!

---

## 📡 ENDPOINTY API (wykorzystane):

```
POST /api/chat/assistant              - Chat
POST /api/stt/transcribe               - Voice→Text
POST /api/tts/speak                    - Text→Voice
POST /api/files/upload                 - Upload plików
GET  /api/files/list                   - Lista plików
GET  /api/travel/search                - Travel search
GET  /api/psyche/status                - Psyche status
POST /api/psyche/reset                 - Reset psyche
GET  /api/admin/cache/stats            - Cache stats
POST /api/admin/cache/clear            - Clear cache
GET  /api/memory/ltm/search            - Search LTM
POST /api/memory/ltm/add               - Add to LTM
GET  /health                           - Health check
GET  /status                           - API status
```

---

## 🚀 DODATKOWE ENDPOINTY (można dodać do UI):

### Programista (Code Executor):
```
POST /api/code/exec                    - Wykonaj kod
GET  /api/code/tree                    - File tree
POST /api/code/write                   - Zapisz plik
GET  /api/code/read                    - Czytaj plik
```

### Captcha:
```
POST /api/captcha/solve                - Rozwiąż captcha
GET  /api/captcha/balance              - Sprawdź balance
```

### Prometheus:
```
GET  /api/prometheus/metrics           - Prometheus metrics
GET  /api/prometheus/health            - Health metrics
GET  /api/prometheus/stats             - Detailed stats
```

---

## 💡 CO MOŻESZ DODAĆ SAMODZIELNIE:

1. **Programista card** - wykonywanie kodu w dashboardzie
2. **Captcha solver** - rozwiązywanie captcha
3. **Metrics viewer** - wykresy Prometheus
4. **History viewer** - historia konwersacji
5. **Feedback system** - thumbs up/down
6. **Settings panel** - konfiguracja AI

---

## 🎯 PRZYKŁAD UŻYCIA:

### Chat:
1. Wpisz wiadomość w textarea
2. Kliknij "Wyślij"
3. Odpowiedź pojawi się poniżej

### Voice:
1. Wybierz plik audio
2. Kliknij "Transkrybuj"
3. Tekst pojawi się poniżej

### TTS:
1. Wpisz tekst
2. Wybierz głos
3. Kliknij "Przeczytaj"
4. Audio odtworzy się automatycznie

Wszystko działa **BEZ PRZEŁADOWANIA STRONY**!

---

## 🔥 SUMMARY:

- **8 głównych funkcji** w jednym dashboardzie
- **Czysty UI** bez bałaganu
- **Wszystko działa przez AJAX** - zero przeładowań
- **Auto-auth** - token wbudowany
- **Error handling** - komunikaty o błędach
- **Responsive** - działa na mobile

**TO JEST KOMPLETNY FRONTEND DO TWOJEGO API!** 🚀
