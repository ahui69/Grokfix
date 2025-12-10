# 🧠 CO DZIEJE SIĘ GDY PISZESZ W CZACIE - PEŁNY FLOW

## ⚡ KROK-PO-KROKU - CO SIĘ AUTOMATYCZNIE WYWOŁUJE

Gdy wpiszesz wiadomość typu "Cześć!" i klikniesz Enter:

---

### 1️⃣ FRONTEND (Angular)
**Plik**: `frontend/src/app/components/chat/chat.component.ts`

```typescript
sendMessage() {
  // 1. Dodaje twoją wiadomość do UI
  this.chatService.addMessage('user', 'Cześć!');
  
  // 2. Tworzy request
  const request = {
    messages: [{ role: 'user', content: 'Cześć!' }],
    user_id: 'web_user',
    use_memory: true,      // ← PAMIĘĆ WŁĄCZONA!
    auto_learn: true       // ← AUTO-NAUKA WŁĄCZONA!
  };
  
  // 3. Wysyła do backend API
  POST /api/chat/assistant
}
```

---

### 2️⃣ BACKEND ENDPOINT (FastAPI)
**Plik**: `assistant_endpoint.py` → funkcja `chat_assistant()`

```python
@router.post("/assistant")
async def chat_assistant(body: ChatRequest):
    # 1. Autoryzacja (Bearer token)
    # 2. Deleguje do COGNITIVE ENGINE:
    result = await cognitive_engine.process_message(
        user_id="web_user",
        messages=[{"role":"user","content":"Cześć!"}],
        req=request
    )
    
    # 3. Po otrzymaniu odpowiedzi → ZAPIS DO PAMIĘCI:
    _save_turn_to_memory("Cześć!", result["answer"], "web_user")
    
    # 4. Jeśli auto_learn=True → AUTO-NAUKA:
    if body.auto_learn:
        _auto_learn_from_turn("Cześć!", result["answer"])
    
    return result
```

---

### 3️⃣ COGNITIVE ENGINE (Główny mózg)
**Plik**: `core/cognitive_engine.py` → klasa `CognitiveEngine`

#### Etap A: FAST PATH CHECK
```python
# Sprawdza czy to jest proste zapytanie
# które można obsłużyć bez pełnej kognicji
for handler in FAST_PATH_HANDLERS:
    if handler.can_handle("Cześć!"):
        return quick_response
```

**FAST PATH HANDLERS** (11 sztuk):
1. ✅ `intent_health()` - "/health" → status
2. ✅ `intent_help()` - "pomoc" → instrukcje
3. ✅ `intent_memory_stats()` - "statystyki pamięci"
4. ✅ `intent_psyche_status()` - "stan psychiki"
5. ✅ `intent_who_are_you()` - "kim jesteś"
6. ✅ `intent_clear_memory()` - "wyczyść pamięć"
7. ✅ `intent_search_memory()` - "szukaj w pamięci X"
8. ✅ `intent_web_search()` - "szukaj w internecie X"
9. ✅ `intent_time_date()` - "która godzina" / "jaka data"
10. ✅ `intent_weather()` - "pogoda"
11. ✅ `intent_calculate()` - "oblicz 2+2"

Jeśli ŻADEN nie pasuje → przechodzi dalej...

---

#### Etap B: COGNITIVE MODE DETECTION
```python
# Analizuje typ zapytania i dobiera tryb:
if "wyjaśnij" or "dlaczego" in message:
    mode = FULL_COGNITIVE  # Pełna refleksja
elif "polityka" or "kontrowersja" in message:
    mode = MULTI_AGENT     # Wiele perspektyw
elif "przyszłość" or "trend" in message:
    mode = PREDICTIVE      # Predykcje
else:
    mode = ENHANCED        # Standardowy
```

**DOSTĘPNE TRYBY:**
- `BASIC` - Prosty LLM call
- `ENHANCED` - LLM + pamięć
- `ADVANCED` - LLM + pamięć + psyche
- `FULL_COGNITIVE` - Wszystko + refleksja
- `MULTI_AGENT` - Wiele agentów (debata)
- `PREDICTIVE` - Predykcje przyszłości

---

#### Etap C: PRZYGOTOWANIE KONTEKSTU
```python
# 1. Pobiera OSTATNIE 10 WIADOMOŚCI z konwersacji
context = messages[-10:]

# 2. HIERARCHICAL MEMORY - pobiera episody:
memory_context = get_hierarchical_context(
    query="Cześć!",
    user_id="web_user"
)
# Zwraca:
# - episodic_memories (przeszłe rozmowy)
# - semantic_knowledge (fakty)
# - procedural_knowledge (jak robić rzeczy)
# - working_memory (STM - krótkoterminowa)

# 3. PSYCHE STATUS:
psyche_state = {
    "mood": 0.75,      # Nastrój AI
    "energy": 0.80,    # Energia
    "focus": 0.90      # Skupienie
}
```

---

#### Etap D: ADVANCED COGNITIVE ENGINE
**Plik**: `core/advanced_cognitive_engine.py`

```python
cognitive_result = await self.advanced_engine.process_message(
    user_message="Cześć!",
    user_id="web_user",
    conversation_context=context,
    cognitive_mode=ENHANCED
)
```

**CO ROBI ADVANCED ENGINE:**

##### 1. **SYSTEM REFLEKSJI** (`core/self_reflection.py`)
```python
# Analizuje własne odpowiedzi i uczy się z nich
reflection_insights = await reflect_on_response(
    user_query="Cześć!",
    initial_response="...",
    conversation_history=context
)
# Zwraca: [
#   {"improvement_type": "tone", "suggestion": "..."},
#   {"improvement_type": "clarity", "suggestion": "..."}
# ]
```

##### 2. **MULTI-AGENT SYSTEM** (`core/multi_agent.py`)
```python
# Tworzy wiele agentów o różnych perspektywach
agents = [
    {"name": "Analyst", "perspective": "analytical"},
    {"name": "Creative", "perspective": "creative"},
    {"name": "Critic", "perspective": "critical"}
]

agent_responses = []
for agent in agents:
    response = await agent.generate_response("Cześć!")
    agent_responses.append(response)

# Syntetyzuje wszystkie perspektywy
final_answer = synthesize_perspectives(agent_responses)
```

##### 3. **INNER LANGUAGE** (`core/inner_language.py`)
```python
# Kompresuje wiedzę do wewnętrznego języka
inner_thought = await compress_to_inner_language(
    external_input="Cześć!",
    context=memory_context
)
# Zwraca: {
#   "compressed_form": "GREET_NEW_USER_FRIENDLY",
#   "compression_level": 0.85,
#   "semantic_tokens": ["greeting", "friendly", "casual"]
# }
```

##### 4. **FUTURE PREDICTOR** (`core/future_predictor.py`)
```python
# Przewiduje co użytkownik może zapytać dalej
predictions = await predict_user_next_questions(
    current_query="Cześć!",
    user_history=context,
    user_profile=user_model
)
# Zwraca: [
#   {"query": "Jak się masz?", "probability": 0.45},
#   {"query": "Co potrafisz?", "probability": 0.35},
#   {"query": "Pomóż mi z...", "probability": 0.20}
# ]
```

##### 5. **KNOWLEDGE COMPRESSION** (`core/knowledge_compression.py`)
```python
# Kompresuje wiedzę do wektorów
compressed_knowledge = await compress_knowledge(
    raw_facts=ltm_results,
    query="Cześć!",
    compression_ratio=0.3
)
# Zwraca: {
#   "knowledge_vectors": [...],
#   "core_concepts": ["greeting", "politeness"],
#   "research_sources": [...]
# }
```

---

#### Etap E: WEB RESEARCH (jeśli potrzebne)
**Plik**: `core/research.py` → funkcja `autonauka()`

```python
# Jeśli zapytanie wymaga aktualnej wiedzy:
if needs_web_research("Cześć!"):  # False dla "Cześć!"
    web_result = await autonauka(
        query="Cześć!",
        topk=8,
        user_id="web_user"
    )
    # Używa:
    # - SERPAPI (Google search)
    # - Firecrawl (scraping)
    # - Embeddings (semantic search)
    # - LTM (long-term memory storage)
```

---

#### Etap F: LLM GENERATION
**Plik**: `core/llm.py` → funkcja `call_llm()`

```python
# Przygotowuje finalny prompt:
messages = [
    {
        "role": "system",
        "content": """Jesteś Mordzix AI - zaawansowany asystent kognitywny.
        
        KONTEKST Z PAMIĘCI:
        - Episodic: [poprzednie rozmowy]
        - Semantic: [fakty z LTM]
        - Procedural: [procedury]
        
        PSYCHE STATE:
        - Mood: 0.75
        - Energy: 0.80
        - Focus: 0.90
        
        REFLECTION INSIGHTS:
        - [insights z refleksji]
        
        PREDICTIONS:
        - Użytkownik prawdopodobnie zapyta: "Jak się masz?"
        """
    },
    {"role": "user", "content": "Cześć!"}
]

# Wywołuje LLM (GLM-4.5 przez DeepInfra)
response = await llm_client.chat_completion(
    messages=messages,
    temperature=0.7,
    max_tokens=2000
)
# → "Cześć! Jak mogę Ci dzisiaj pomóc?"
```

---

### 4️⃣ POST-PROCESSING (Po wygenerowaniu odpowiedzi)

#### A. ZAPIS DO PAMIĘCI STM (Short-Term Memory)
**Plik**: `core/memory.py` → `_save_turn_to_memory()`

```python
# Zapisuje w bazie SQLite:
INSERT INTO stm (user_id, role, content, timestamp)
VALUES 
  ('web_user', 'user', 'Cześć!', 1729123456.789),
  ('web_user', 'assistant', 'Cześć! Jak mogę...', 1729123458.123)
```

#### B. AUTO-LEARNING (Jeśli auto_learn=True)
**Plik**: `core/memory.py` → `_auto_learn_from_turn()`

```python
# Analizuje rozmowę i wydobywa fakty:
facts_to_learn = extract_facts_from_conversation(
    user_msg="Cześć!",
    assistant_msg="Cześć! Jak mogę..."
)

# Zapisuje do LTM (Long-Term Memory):
for fact in facts_to_learn:
    ltm_save(
        fact=fact,
        confidence=0.85,
        embedding=embed(fact)
    )
```

#### C. PSYCHE UPDATE
**Plik**: `core/memory.py` → `psy_observe_text()`

```python
# Analizuje tekst użytkownika pod kątem emocji:
sentiment = analyze_sentiment("Cześć!")  # → 0.7 (pozytywny)

# Aktualizuje stan psychiczny AI:
UPDATE psyche_state SET
  mood = mood * 0.9 + sentiment * 0.1,
  energy = energy - 0.01,
  focus = focus + 0.02
WHERE id = 1
```

#### D. USER MODEL UPDATE
**Plik**: `core/user_model.py` → `update_user_model()`

```python
# Aktualizuje profil użytkownika:
user_model.update({
    "last_interaction": "2025-10-16T15:30:45",
    "interaction_count": +1,
    "preferred_tone": "friendly",
    "topics_of_interest": ["general_chat"],
    "engagement_level": 0.8
})
```

---

### 5️⃣ RESPONSE DO FRONTENDU

```json
{
  "ok": true,
  "answer": "Cześć! Jak mogę Ci dzisiaj pomóc?",
  "sources": [],
  "metadata": {
    "source": "advanced_cognitive_engine",
    "cognitive_mode": "enhanced",
    "processing_time": 1.234,
    "confidence_score": 0.95,
    "originality_score": 0.75,
    "reflection_insights_count": 2,
    "agent_perspectives_count": 0,
    "future_predictions_count": 3,
    "memory_context_used": true,
    "hierarchical_memory": true,
    "predicted_follow_ups": [
      "Jak się masz?",
      "Co potrafisz?",
      "Pomóż mi..."
    ]
  }
}
```

---

## 📊 PODSUMOWANIE - CO SIĘ DZIEJE AUTOMATYCZNIE:

### ✅ ZAWSZE WYWOŁYWANE (dla każdej wiadomości):

1. **Authorization** - Bearer token check
2. **Cognitive Engine** - główny orchestrator
3. **Fast Path Check** - 11 intent handlers
4. **Cognitive Mode Detection** - wybór trybu przetwarzania
5. **Memory Context** - pobranie kontekstu z pamięci:
   - Hierarchical Memory (episodic, semantic, procedural)
   - STM (short-term - ostatnie 10 wiadomości)
   - LTM (long-term - fakty)
6. **Psyche Status** - stan emocjonalny AI
7. **LLM Generation** - wywołanie modelu GLM-4.5
8. **STM Save** - zapis rozmowy do bazy
9. **Psyche Update** - aktualizacja stanu
10. **User Model Update** - aktualizacja profilu użytkownika

### 🔧 OPCJONALNIE WYWOŁYWANE (zależy od trybu/zapytania):

11. **Self-Reflection** - analiza własnych odpowiedzi
12. **Multi-Agent** - wiele perspektyw (dla kontrowersyjnych tematów)
13. **Inner Language** - kompresja semantyczna
14. **Future Predictor** - przewidywanie następnych pytań
15. **Knowledge Compression** - kompresja wiedzy do wektorów
16. **Web Research (autonauka)** - tylko jeśli zapytanie wymaga internetu:
    - SERPAPI search
    - Firecrawl scraping
    - Embeddings
    - LTM save
17. **Auto-Learning** - ekstrakcja faktów i zapis do LTM

---

## 🎯 LICZBY:

- **Minimum systemów wywołanych**: 10
- **Maximum systemów wywołanych**: 17
- **Liczba baz danych**: 1 (SQLite z 6 tabelami)
- **Liczba modeli AI**: 2 (GLM-4.5 + embeddings)
- **Liczba external API**: do 4 (SERPAPI, Firecrawl, Stability, ElevenLabs)
- **Średni czas przetwarzania**: 1-3 sekundy

---

## 📁 KLUCZOWE PLIKI:

```
assistant_endpoint.py          ← Główny endpoint
core/cognitive_engine.py       ← Orchestrator
core/advanced_cognitive_engine.py  ← 5 systemów kognitywnych
core/intent_dispatcher.py      ← 11 fast path handlers
core/memory.py                 ← STM/LTM/Psyche
core/hierarchical_memory.py    ← Hierarchical memory
core/self_reflection.py        ← Refleksja
core/multi_agent.py            ← Multi-agent
core/inner_language.py         ← Inner language
core/future_predictor.py       ← Predykcje
core/knowledge_compression.py  ← Kompresja wiedzy
core/research.py               ← autonauka (web)
core/llm.py                    ← GLM-4.5 client
core/user_model.py             ← Profil użytkownika
```

---

**TO WSZYSTKO DZIEJE SIĘ AUTOMATYCZNIE GDY WPISZESZ "CZEŚĆ!"** 🚀
