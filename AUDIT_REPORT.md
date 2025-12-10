# 🔍 MORDZIX AI - RAPORT AUDYTU KODU

**Data audytu:** 2025-12-04  
**Audytor:** Senior Full-Stack Architect  
**Zakres:** Backend (core/), Frontend (frontend/), Security, Sessions, Chat API  
**Kontekst:** Post-refactor PHASE 1-5 według `AUDIT_REFACTOR_PLAN.md`

---

## 📋 EXECUTIVE SUMMARY

### ✅ Mocne strony
- Solidna architektura po refaktorze - jeden entrypoint, czysta struktura
- Prawdziwy streaming SSE w chat API
- Session management w SQLite dobrze zaprojektowany
- Frontend Grok-style czysty i responsywny
- Zaawansowany cognitive engine z memory integration

### 🔴 Krytyczne problemy wymagające natychmiastowej naprawy
1. **Hardcoded LLM API key** w `core/config.py` - wyciek do repo
2. **XSS vulnerability** w frontend markdown rendering
3. **Brak walidacji długości** wiadomości - DoS risk
4. **Rate limiting nie działa** w multi-worker setup

### 🎯 TOP 3 priorytety (1-2 dni pracy)
1. Fix security - usunąć hardcoded secrets (2h)
2. Dodać input validation (3h)
3. Naprawić XSS w frontend (30min)

---

## [BACKEND – ENTRYPOINT]

### ✅ KRYTYCZNE
**BRAK** - entrypoint jest poprawnie zunifikowany.

### 🟡 DO POPRAWY

**1. Auto-router loader - ciche niepowodzenia**
- **Plik:** `core/app.py:957-962`
- **Problem:** Try/except przy ładowaniu routerów - serwer startuje nawet jeśli część nie działa
- **Fix:** Dodać diagnostyczny endpoint `/api/health/routers`

**2. Rate limiting nie działa w produkcji**
- **Plik:** `core/app.py:71-100`
- **Problem:** `_RATE_BUCKETS` dict w pamięci - nie shared między workerami, memory leak
- **Fix:** Użyć Redis lub biblioteki `slowapi`

**3. Exception handler wyciek informacji**
- **Plik:** `core/app.py:56-59`
- **Problem:** Zwraca `type(exc).__name__` - ujawnia strukturę kodu
- **Fix:** W produkcji zwracać tylko generic error

**4. Health check bez sprawdzania dependencies**
- **Plik:** `core/app.py:713-716`
- **Problem:** Nie sprawdza czy baza/LLM API działa
- **Fix:** Dodać checks dla DB, LLM API, memory system

---

## [BACKEND – CHAT API]

### 🔴 KRYTYCZNE

**1. Brak walidacji długości wiadomości (DoS)**
- **Plik:** `core/assistant_endpoint.py:58-120`
- **Problem:** User może wysłać 10MB tekstu
- **Efekt:** Timeout LLM, zużycie pamięci, DoS, wysokie koszty
- **Fix:**
```python
MAX_MESSAGE_LENGTH = 50000
for msg in body.messages:
    if len(msg.content) > MAX_MESSAGE_LENGTH:
        raise HTTPException(413, "Message too long")
```

**2. Race condition w zapisie do sesji**
- **Plik:** `core/assistant_endpoint.py:84-89, 108-113`
- **Problem:** User message i assistant message zapisywane osobno - przy błędzie niekompletna historia
- **Fix:** Zapisywać obie wiadomości w jednej transakcji po sukcesie

### 🟡 DO POPRAWY

**1. Streaming bez timeoutu**
- **Problem:** Generator może się zawiesić jeśli LLM przestanie odpowiadać
- **Fix:** `async with asyncio.timeout(120):`

**2. Duplikaty w kontekście**
- **Problem:** 500 wiadomości może zawierać duplikaty (retry)
- **Fix:** Deduplikacja po (role, content hash)

**3. Memory injection za duża**
- **Problem:** 50 memory items + 500 messages = >100k tokenów
- **Fix:** Zmniejszyć do 20 items + 200 messages, monitoring długości

**4. Fallback blokuje event loop**
- **Problem:** `call_llm()` synchroniczny w async funkcji
- **Fix:** `await asyncio.to_thread(call_llm, ...)`

### 💡 POMYSŁY

- Cache dla powtarzalnych zapytań (Redis, TTL 1h)
- Streaming progress indicators (`{"type": "thinking", "stage": "..."}`)
- Conversation summarization dla długich sesji (co 50 wiadomości)

---

## [BACKEND – SESJE]

### ✅ KRYTYCZNE
**BRAK** - implementacja solidna.

### 🟡 DO POPRAWY

**1. Brak PRAGMA dla SQLite**
- **Problem:** Brak WAL mode i foreign_keys=ON
- **Fix:**
```python
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA foreign_keys=ON")
```

**2. Brak limitu długości content**
- **Problem:** User może zapisać 100MB w message
- **Fix:** Walidacja `MAX_CONTENT_LENGTH = 100000`

**3. Auto-title nadpisuje custom title**
- **Problem:** User zmienia tytuł, potem wysyła wiadomość → tytuł nadpisany
- **Fix:** Dodać kolumnę `title_custom BOOLEAN`

**4. Brak paginacji messages**
- **Problem:** Nie można pobrać wiadomości 101-200
- **Fix:** Dodać parametr `offset`, zwracać `has_more`

### 💡 BOOSTY

- Session archiving (>90 dni do archive table)
- Session search (FTS5 na content)
- Session export (JSON/Markdown download)

---

## [FRONTEND]

### 🔴 KRYTYCZNE

**1. XSS w markdown rendering**
- **Plik:** `frontend/js/chat.js:515`
- **Problem:** `marked.parse()` pozwala na HTML, `innerHTML` wykonuje scripts
- **Efekt:** XSS, kradzież tokenu, session hijacking
- **Fix (PILNE):**
```javascript
// Dodaj DOMPurify
html = DOMPurify.sanitize(marked.parse(content));
element.innerHTML = html;
```

**2. Token w localStorage (nie HttpOnly)**
- **Plik:** `frontend/js/api.js:12-20`
- **Problem:** Token dostępny dla JavaScript - przy XSS atakujący kradnie
- **Fix:** Użyć HttpOnly cookie (wymaga backend change) lub CSP header

### 🟡 UX DO POPRAWY

**1. Brak reconnect przy utracie połączenia**
- **Problem:** Stream urwie się → błąd, brak retry
- **Fix:** Exponential backoff retry (3 próby)

**2. Brak loading state**
- **Problem:** `loadSessions()` bez spinnera
- **Fix:** Skeleton loader

**3. Duplikacja przy szybkim klikaniu Send**
- **Problem:** Brak blokady non-streaming requestów
- **Fix:** Dodać `this.isSending` flag

**4. Brak autosave draftu**
- **Problem:** Odświeżenie strony = utrata tekstu
- **Fix:** Autosave do localStorage co 2s

**5. Brak keyboard shortcuts**
- Ctrl+K - nowa sesja
- Ctrl+/ - focus input
- Esc - stop streaming

**6. Session list bez preview**
- **Problem:** Tylko tytuł, trudno odróżnić sesje
- **Fix:** Dodać preview ostatniej wiadomości (50 chars)

### 💡 BOOSTY

- Offline support (Service Worker + IndexedDB)
- Voice input (Web Speech API)
- Message reactions (thumbs up/down)
- Dark/Light theme toggle

---

## [SECURITY]

### 🔴 KRYTYCZNE

**1. Hardcoded LLM API key**
- **Plik:** `core/config.py:52`
- **Problem:** `LLM_API_KEY = os.getenv("LLM_API_KEY", "w52XW0XN6zoV9hdY8OONhLu6tvnFaXbZ")`
- **KRYTYCZNE:** Klucz w kodzie, wyciek do repo, atakujący może użyć
- **Fix (NATYCHMIAST):**
```python
LLM_API_KEY = os.getenv("LLM_API_KEY")
if not LLM_API_KEY:
    raise RuntimeError("LLM_API_KEY must be set!")
```

### 🟡 DO POPRAWY

**1. AUTH_TOKEN może być pusty**
- **Problem:** Pusty string wyłącza auth
- **Fix:** W produkcji wymagać tokenu

**2. Brak rate limiting per user**
- **Problem:** Limit per IP, atakujący z wieloma IP obchodzi
- **Fix:** Rate limit per `user_id` + IP

**3. Brak HTTPS enforcement**
- **Problem:** Token może wyciec przez HTTP
- **Fix:** Middleware sprawdzający `request.url.scheme`

**4. SQLite bez WAL mode**
- **Problem:** Lock na całą bazę podczas write
- **Fix:** `PRAGMA journal_mode=WAL`

**5. Brak sanitization w session title**
- **Problem:** User może wstawić `\n\r` lub bardzo długi string
- **Fix:** `title.strip()[:200].replace('\n', ' ')`

### 💡 WZMOCNIENIE

- Token rotation (JWT z expiration)
- Audit log (wszystkie operacje)
- Content Security Policy header
- Request signing (HMAC)

---

## [TESTY – PROPOZYCJE]

### Unit Tests (5 testów)

1. **sessions.create_session()** - tworzy z UUID, title, message_count=0
2. **sessions.add_message()** - zapisuje i aktualizuje timestamp
3. **llm.call_llm()** - używa fallback gdy main failuje
4. **assistant_endpoint** - waliduje długość (HTTP 413)
5. **cognitive_engine** - deduplikuje messages

### Integration Tests (5 testów)

6. **POST /api/chat/assistant** - zwraca odpowiedź, zapisuje do sesji
7. **POST /api/chat/assistant/stream** - SSE z start/chunk/complete
8. **GET /api/sessions** - lista sesji sorted by updated_at DESC
9. **DELETE /api/sessions/{id}** - usuwa sesję i messages
10. **Rate limiting** - 161. request = HTTP 429

### E2E Tests (5 scenariuszy)

11. **User tworzy sesję i wysyła wiadomość** - wyświetlone, zapisane
12. **User przełącza między sesjami** - poprawna historia
13. **Streaming** - tokeny stopniowo, cursor animowany
14. **Błąd API** - toast notification
15. **XSS protection** - HTML zescapowany

---

## 🎯 PLAN DZIAŁANIA (PRIORYTET)

### 🔥 NATYCHMIAST (2-3h)

**1. Fix hardcoded secrets**
```python
# core/config.py
LLM_API_KEY = os.getenv("LLM_API_KEY")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
if not LLM_API_KEY or not AUTH_TOKEN:
    raise RuntimeError("Required env vars not set!")
```

**2. Fix XSS**
```html
<!-- frontend/index.html -->
<script src="https://cdn.jsdelivr.net/npm/dompurify@3.0.6/dist/purify.min.js"></script>
```
```javascript
// frontend/js/chat.js
html = DOMPurify.sanitize(marked.parse(content));
```

**3. Add input validation**
```python
# core/assistant_endpoint.py
MAX_MESSAGE_LENGTH = 50000
for msg in body.messages:
    if len(msg.content) > MAX_MESSAGE_LENGTH:
        raise HTTPException(413, "Message too long")
```

### ⚡ DZIEŃ 1 (4-6h)

4. Fix rate limiting (Redis lub slowapi)
5. Add SQLite PRAGMA (WAL, foreign_keys)
6. Fix streaming timeout
7. Add health check dla dependencies

### 📅 DZIEŃ 2-3 (8-12h)

8. Fix race condition w sessions
9. Add message deduplication
10. Reduce memory injection size
11. Add session pagination
12. Frontend reconnect logic
13. Loading states + UX improvements

### 🚀 PÓŹNIEJ (nice-to-have)

14. Conversation summarization
15. Session search (FTS5)
16. Session export
17. Offline support
18. Voice input
19. Audit logging

---

## 📊 PODSUMOWANIE

**Status:** Projekt w dobrym stanie po refaktorze, ale wymaga pilnych poprawek security.

**Gotowość produkcyjna:** 70% - po naprawieniu TOP 3 → 95%

**Największe ryzyka:**
1. Hardcoded API key (wyciek = koszty)
2. XSS (kradzież sesji)
3. Brak walidacji (DoS)

**Rekomendacja:** Napraw TOP 3 (3h pracy) przed deploymentem produkcyjnym. Reszta to optymalizacje które można zrobić iteracyjnie.

---

**Koniec raportu**
