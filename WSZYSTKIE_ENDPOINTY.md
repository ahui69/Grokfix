# WSZYSTKIE ENDPOINTY MORDZIX

Łącznie: **177** endpointów.

| Metoda | Ścieżka | Nazwa | Opis |
|--------|---------|-------|------|
| `GET` | `/` | serve_frontend | Główny interfejs czatu - Angular SPA lub WebUI |
| `GET` | `/api` | api_status | Status API |
| `POST` | `/api/admin/cache/clear` | clear_cache | 🗑️ Clear cache |
| `GET` | `/api/admin/cache/stats` | cache_stats | 📊 Get cache statistics |
| `POST` | `/api/admin/jwt/rotate` | admin_rotate_jwt |  |
| `GET` | `/api/admin/ratelimit/config` | rate_limit_config | ⚙️ Get rate limit configuration |
| `GET` | `/api/admin/ratelimit/usage/{user_id}` | rate_limit_usage | 📈 Get rate limit usage for user |
| `GET` | `/api/automation/status` | automation_status | Podsumowanie automatycznych narzędzi i fast path. |
| `POST` | `/api/autoroute/analyze` | analyze_route | 🎯 Analizuje input użytkownika i zwraca najlepszy endpoint  Usage z frontu: ```javascript const result = await fetch('/api/autoroute/analyze', {     method: 'POST',     body: JSON.stringify({       ... |
| `GET` | `/api/autoroute/endpoints` | get_available_endpoints | 📋 Zwraca mapę wszystkich dostępnych endpointów dla frontu  Przydatne do generowania UI, podpowiedzi, itp. |
| `POST` | `/api/autoroute/execute` | execute_route | ⚡ Analizuje input I AUTOMATYCZNIE WYKONUJE odpowiedni endpoint  To jest główna funkcja dla frontu - one-click routing! |
| `GET` | `/api/autoroute/stats` | get_routing_stats | 📊 Statystyki routingu dla dashboardu admina |
| `GET` | `/api/batch/metrics` | batch_metrics_endpoint | Pobiera metryki procesora wsadowego |
| `POST` | `/api/batch/process` | batch_process_endpoint | Wykonuje wsadowe przetwarzanie zapytań LLM |
| `POST` | `/api/batch/shutdown` | batch_shutdown_endpoint | Zatrzymuje procesor wsadowy |
| `POST` | `/api/batch/submit` | batch_submit_endpoint | Dodaje pojedyncze zapytanie do wsadowego przetwarzania |
| `GET` | `/api/captcha/balance` | get_balance | Sprawdź saldo 2captcha |
| `POST` | `/api/captcha/solve` | solve_captcha | Rozwiąż captcha przez 2captcha API |
| `POST` | `/api/chat/assistant` | chat_assistant |  |
| `POST` | `/api/chat/assistant/stream` | chat_assistant_stream |  |
| `POST` | `/api/chat/auto` | force_auto_learn |  |
| `POST` | `/api/code/deps/install` | deps_install | 📦 Install dependencies  Wymaga confirm=True! |
| `POST` | `/api/code/docker/build` | docker_build | 🐳 Build Docker image  Wymaga confirm=True! |
| `POST` | `/api/code/docker/run` | docker_run | 🚀 Run Docker container  Wymaga confirm=True! |
| `POST` | `/api/code/exec` | exec_command | 🔧 Execute shell command  Wymaga confirm=True dla bezpieczeństwa! Użyj dry_run=True dla preview. |
| `POST` | `/api/code/format` | format_code | 💅 Format code  Wymaga confirm=True jeśli check=False! |
| `POST` | `/api/code/git` | git | 🔀 Git operations  Wymaga confirm=True dla destructive ops (commit, push)! |
| `POST` | `/api/code/init` | project_init | 🆕 Initialize new project  Creates: src/, tests/, README.md, pyproject.toml/package.json |
| `POST` | `/api/code/lint` | lint | ✨ Lint code  Wymaga confirm=True jeśli fix=True! |
| `POST` | `/api/code/plan` | plan | 📋 Plan project steps  Zwraca rekomendowane kroki dla projektu |
| `GET` | `/api/code/read` | read_file | 📖 Read file |
| `GET` | `/api/code/snapshot` | snapshot | 📊 System snapshot - dostępne narzędzia  Zwraca informacje o dostępnych narzędziach programistycznych |
| `POST` | `/api/code/test` | test | 🧪 Run tests  Wymaga confirm=True! |
| `GET` | `/api/code/tree` | read_tree | 🌳 Read project tree |
| `POST` | `/api/code/write` | write_file | 📝 Write file  Wymaga confirm=True! |
| `POST` | `/api/cognitive/nlp/analyze` | nlp_advanced_analysis | 🔍 ZAAWANSOWANA ANALIZA NLP  Kompleksowa analiza tekstu z wykorzystaniem spaCy (pl_core_news_sm): - NER (Named Entity Recognition): osoby, organizacje, lokalizacje, daty - Keywords extraction: najwa... |
| `POST` | `/api/cognitive/proactive/suggestions` | generate_proactive_suggestions | 💡 PROAKTYWNE SUGESTIE  Generuje inteligentne sugestie na podstawie: - Analizy kontekstu konwersacji - Wzorców użytkownika - Tematów i intencji - Predykcji potrzeb  **Zwraca:** - suggestions: Lista ... |
| `POST` | `/api/cognitive/process` | cognitive_process | 🧠 PEŁNE PRZETWARZANIE KOGNITYWNE  Orkiestracja wszystkich 5 systemów kognitywnych: 1. Self-Reflection - dynamiczna refleksja 2. Knowledge Compression - kompresja wiedzy 3. Multi-Agent Orchestrator ... |
| `POST` | `/api/cognitive/psychology/analyze` | analyze_emotional_state | 🧠 ANALIZA EMOCJONALNA  Zaawansowana analiza psychologiczna wiadomości: - Podstawowe emocje (Plutchik's wheel: joy, trust, fear, surprise, sadness, disgust, anger, anticipation) - PAD model: valence... |
| `GET` | `/api/cognitive/psychology/state/{user_id}` | get_psychology_state | 📊 STAN PSYCHOLOGICZNY AI  Pobiera aktualny stan emocjonalny AI dla danego użytkownika |
| `POST` | `/api/cognitive/reflect` | self_reflect | 🔄 DYNAMICZNA REKURENCJA UMYSŁOWA  AI ocenia swoją odpowiedź i poprawia ją przez wielopoziomową refleksję: - SURFACE: Podstawowa ewaluacja (faktyczność, jasność) - MEDIUM: Logika, kompletność, konte... |
| `GET` | `/api/cognitive/reflection/summary` | get_reflection_summary | 📊 PODSUMOWANIE REFLEKSJI  Zwraca statystyki wszystkich procesów refleksji: - Total reflections, average score, cycle time - Depth distribution - Total insights & corrections - Meta-patterns |
| `POST` | `/api/cognitive/semantic/analyze` | semantic_analysis | 🧬 ANALIZA SEMANTYCZNA  Zaawansowana analiza semantyczna tekstu: - Embeddingi (sentence-transformers) - Ekstrakcja konceptów - Identyfikacja relacji - Podobieństwo semantyczne (jeśli compare_with)  ... |
| `GET` | `/api/cognitive/status` | cognitive_status | 📊 STATUS SYSTEMÓW KOGNITYWNYCH  Zwraca status wszystkich zaawansowanych systemów |
| `GET` | `/api/cognitive/tools/list` | list_cognitive_tools | 🛠️ LISTA NARZĘDZI KOGNITYWNYCH  Zwraca listę wszystkich dostępnych narzędzi z tools_registry |
| `GET` | `/api/endpoints/list` | list_endpoints | Lista wszystkich endpointów API |
| `GET` | `/api/fashion/categories` | get_fashion_categories | Pobiera dostępne kategorie mody |
| `POST` | `/api/fashion/detect-brand` | detect_brand | Rozpoznaje markę z obrazu |
| `POST` | `/api/fashion/forecast-trends` | forecast_trends | Prognozuje trendy modowe |
| `POST` | `/api/fashion/generate-outfit` | generate_outfit | Generuje stylizację na podstawie okazji i pogody |
| `GET` | `/api/fashion/occasions` | get_occasions | Pobiera dostępne okazje |
| `GET` | `/api/fashion/stats` | get_fashion_stats | Pobiera statystyki AI Fashion |
| `GET` | `/api/fashion/weather-types` | get_weather_types | Pobiera typy pogody |
| `POST` | `/api/ff/proxy` | proxy |  |
| `POST` | `/api/files/analyze` | analyze_file | 🔍 Analyze uploaded file  Extract text, metadata, dimensions, etc. |
| `POST` | `/api/files/batch/analyze` | batch_analyze | 🔍 Batch analyze multiple files |
| `POST` | `/api/files/delete` | delete_file | 🗑️ Delete file |
| `GET` | `/api/files/download` | download_file | 📥 Download file by ID |
| `GET` | `/api/files/list` | list_files | 📋 List all uploaded files |
| `GET` | `/api/files/stats` | files_stats | 📊 Files statistics |
| `GET` | `/api/files/thumb/{tenant}/{day}/{name}` | thumb |  |
| `POST` | `/api/files/upload` | upload |  |
| `POST` | `/api/files/upload` | upload_file | 📤 Upload file (multipart/form-data)  Supports: PDF, images, ZIP, text files, video, audio, code files Max size: 50MB |
| `POST` | `/api/files/upload/base64` | upload_base64 | 📤 Upload file (base64 encoded)  For frontend that sends files as base64 |
| `GET` | `/api/files/{tenant}/{day}/{name}` | download |  |
| `POST` | `/api/hacker/exploit/sqli` | sql_injection_scanner | 💉 SQL Injection Tester - test parametrów na SQLi |
| `GET` | `/api/hacker/exploits/list` | list_exploit_modules | 🎯 Lista dostępnych modułów exploitów |
| `POST` | `/api/hacker/recon/domain` | domain_reconnaissance | 🕵️ Domain Reconnaissance - zbieraj intel o domenie |
| `POST` | `/api/hacker/scan/ports` | network_scan | 🔍 Port Scanner - skanuj porty na targecie |
| `POST` | `/api/hacker/scan/vulnerabilities` | vulnerability_scanner | 🔐 Vulnerability Scanner - szukaj podatności |
| `GET` | `/api/hacker/tools/status` | hacker_tools_status | 🛠️ Status narzędzi hackingowych |
| `GET` | `/api/image/file/{tenant}/{name}` | image_file |  |
| `POST` | `/api/image/generate` | generate |  |
| `GET` | `/api/internal/ui` | ui_info | Return manifest and optionally token for UI. Token is returned only if env UI_EXPOSE_TOKEN=1 or request is local. |
| `GET` | `/api/internal/ui_token` | ui_token | Return the AUTH_TOKEN only if UI_EXPOSE_TOKEN=1 or request is local. |
| `POST` | `/api/lang/detect` | detect |  |
| `POST` | `/api/memory/add` | add |  |
| `GET` | `/api/memory/export` | export |  |
| `POST` | `/api/memory/import` | import_ |  |
| `POST` | `/api/memory/optimize` | optimize |  |
| `POST` | `/api/memory/search` | search |  |
| `GET` | `/api/memory/status` | status | Status systemu pamięci |
| `GET` | `/api/ml/model-info` | get_model_info | Informacje o modelu ML |
| `POST` | `/api/ml/predict-suggestions` | predict_suggestions | Przewiduje sugestie ML (95% accuracy) |
| `POST` | `/api/ml/record-feedback` | record_feedback | Zapisuje feedback dla ML model |
| `POST` | `/api/ml/retrain` | retrain_model | Retrenuje model ML |
| `GET` | `/api/ml/stats` | get_stats | Pobiera statystyki ML model |
| `POST` | `/api/nlp/analyze` | analyze_text | Przeprowadza kompleksową analizę NLP pojedynczego tekstu  - **text**: Tekst do analizy (1-10000 znaków) - **use_cache**: Czy używać cache'a (domyślnie True) |
| `POST` | `/api/nlp/batch-analyze` | batch_analyze_texts | Przeprowadza analizę NLP dla wielu tekstów wsadowo  - **texts**: Lista tekstów (1-50 tekstów) - **batch_size**: Rozmiar wsadu (1-20) |
| `POST` | `/api/nlp/entities` | extract_entities | Ekstrahuje encje nazwane z tekstu  - **text**: Tekst do analizy - **use_cache**: Czy używać cache'a |
| `POST` | `/api/nlp/extract-topics` | extract_topics | Ekstrahuje tematy z kolekcji tekstów  - **texts**: Lista tekstów (1-100 tekstów) - **num_topics**: Liczba tematów do ekstrakcji (1-20) |
| `POST` | `/api/nlp/key-phrases` | extract_key_phrases | Ekstrahuje frazy kluczowe z tekstu  - **text**: Tekst do analizy - **use_cache**: Czy używać cache'a |
| `POST` | `/api/nlp/readability` | calculate_readability | Oblicza ocenę czytelności tekstu  - **text**: Tekst do analizy - **use_cache**: Czy używać cache'a |
| `POST` | `/api/nlp/sentiment` | analyze_sentiment | Analizuje sentyment tekstu  - **text**: Tekst do analizy - **use_cache**: Czy używać cache'a |
| `GET` | `/api/nlp/stats` | get_nlp_stats | Zwraca statystyki procesora NLP  - Statystyki użycia, wydajności i modeli językowych |
| `GET` | `/api/prometheus/health` | health_check | Health check dla Prometheus |
| `GET` | `/api/prometheus/metrics` | get_prometheus_metrics | Endpoint dla Prometheus - metryki w formacie tekstowym |
| `GET` | `/api/prometheus/stats` | get_stats | Statystyki w formacie JSON |
| `POST` | `/api/psyche` | psyche_analyze | Analiza wiadomości i aktualizacja stanu |
| `GET` | `/api/psyche/history` | psyche_history | Ostatnie wiadomości |
| `POST` | `/api/psyche/reset` | psyche_reset | Reset stanu |
| `GET` | `/api/psyche/state` | psyche_state | Pobierz bieżący stan |
| `POST` | `/api/psyche/state` | psyche_state_set | Ustaw stan |
| `POST` | `/api/research/autonauka` | run_autonauka | 🧠 AUTO-NAUKA Z WEB RESEARCH  Pełna pipeline: 1. Wyszukiwanie w wielu źródłach (DDG, Wiki, SERPAPI, arXiv, S2) 2. Scraping treści (Firecrawl lub fallback) 3. Analiza semantyczna i embedding 4. Gener... |
| `POST` | `/api/research/search` | web_search | 🌐 OGÓLNE WYSZUKIWANIE W INTERNECIE  Przeszukuje wiele źródeł: - DuckDuckGo (zawsze) - Wikipedia (zawsze) - SERPAPI/Google (jeśli klucz API) - arXiv (tryb full/grounded) - Semantic Scholar (tryb ful... |
| `GET` | `/api/research/sources` | available_sources | 📚 LISTA DOSTĘPNYCH ŹRÓDEŁ  Zwraca informacje o dostępnych źródłach danych i ich statusie. |
| `GET` | `/api/research/test` | test_research | 🧪 TEST WEB SEARCH  Testuje czy research działa poprawnie. |
| `POST` | `/api/search/compare` | compare_methods | 🔬 PORÓWNANIE METOD WYSZUKIWANIA  Wykonuje wyszukiwanie wszystkimi 3 metodami oddzielnie i pokazuje różnice w wynikach. |
| `POST` | `/api/search/hybrid` | hybrid_search | 🔥 ZAAWANSOWANE WYSZUKIWANIE HYBRYDOWE 🔥  Łączy 3 metody: - FTS5 Full-Text Search (40%) - Semantic Vector Search (35%) - Fuzzy String Matching (25%)  Zwraca najlepsze wyniki z breakdown score'ów i t... |
| `GET` | `/api/search/stats` | search_stats | Statystyki pamięci użytkownika |
| `GET` | `/api/search/test` | test_search | Quick test endpoint - GET request dla łatwego testowania  Example: /api/search/test?q=python&limit=10 |
| `GET` | `/api/search/widget` | search_widget | 🎨 FRONTEND WIDGET - Interaktywny interfejs do testowania hybrid search |
| `GET` | `/api/stt/file/{tenant}/{name}` | stt_file |  |
| `GET` | `/api/stt/providers` | list_stt_providers | Lista dostępnych providerów STT |
| `POST` | `/api/stt/transcribe` | transcribe |  |
| `POST` | `/api/stt/transcribe` | transcribe_audio | Zamień audio na tekst (Speech-to-Text)  Wspierane formaty: mp3, wav, m4a, webm, ogg Max size: 25MB |
| `POST` | `/api/suggestions/analyze` | analyze_message | Analizuje wiadomość bez generowania sugestii |
| `POST` | `/api/suggestions/generate` | generate_suggestions | Generuje proaktywne sugestie dla wiadomości |
| `POST` | `/api/suggestions/inject` | inject_suggestions | Dodaje sugestie do promptu |
| `GET` | `/api/suggestions/stats` | get_stats | Pobiera statystyki sugestii |
| `GET` | `/api/travel/attractions/{city}` | get_attractions | 🏛️ Szybki dostęp do atrakcji |
| `GET` | `/api/travel/geocode` | geocode_city | 📍 Pobierz współrzędne geograficzne miasta  Używa OpenTripMap API do geocodingu  Przykład: ``` GET /api/travel/geocode?city=Gdańsk ```  Zwraca: ```json {     "ok": true,     "city": "Gdańsk",     "c... |
| `GET` | `/api/travel/hotels/{city}` | get_hotels | 🏨 Szybki dostęp do hoteli |
| `GET` | `/api/travel/restaurants/{city}` | get_restaurants | 🍽️ Szybki dostęp do restauracji |
| `GET` | `/api/travel/search` | search_travel | 🗺️ Wyszukaj miejsca w mieście  Parametry: - city: nazwa miasta (np. "Warszawa", "Kraków") - what: co szukamy   - "attractions" - atrakcje turystyczne   - "hotels" - hotele   - "restaurants" - resta... |
| `GET` | `/api/travel/trip-plan` | plan_trip | 🗓️ Zaplanuj wycieczkę (AI-powered)  Generuje plan wycieczki bazując na: - Długość pobytu (dni) - Zainteresowania - Dostępne atrakcje  Przykład: ``` GET /api/travel/trip-plan?city=Kraków&days=2&inte... |
| `POST` | `/api/tts/speak` | speak | Generuje audio z tekstu  Body:     {         "text": "Tekst do wypowiedzenia",         "voice": "rachel"  // opcjonalnie: rachel, antoni, adam, bella     }  Returns:     audio/mpeg (MP3) |
| `GET` | `/api/tts/voices` | list_voices | Lista dostępnych głosów |
| `POST` | `/api/vision/describe` | describe |  |
| `POST` | `/api/vision/ocr` | ocr |  |
| `GET` | `/api/voice/file/{tenant}/{name}` | voice_file |  |
| `POST` | `/api/voice/tts` | tts |  |
| `POST` | `/api/writer/article/masterpiece` | create_masterpiece_article | Generuj mistrzowski artykuł  Args:     request: Parametry artykułu  Returns:     Kompletny artykuł |
| `GET` | `/api/writer/auction/knowledge` | get_auction_knowledge | Pobierz wiedzę aukcyjną z bazy  Returns:     Wiedza aukcyjna pogrupowana tematycznie |
| `POST` | `/api/writer/auction/learn` | learn_auction_knowledge | Naucz system wiedzy aukcyjnej  Args:     request: Elementy wiedzy aukcyjnej do nauczenia  Returns:     Status nauki |
| `POST` | `/api/writer/auction/pro` | create_auction_pro_description | Zaawansowane generowanie opisu aukcji  Args:     request: Parametry zaawansowanego opisu aukcji  Returns:     Profesjonalny opis aukcji |
| `GET` | `/api/writer/auction/tags` | get_auction_tags | Sugeruj tagi dla aukcji  Args:     title: Tytuł aukcji     description: Opis aukcji  Returns:     Sugerowane tagi |
| `POST` | `/api/writer/creative` | create_creative_text | Generuj kreatywny tekst na zadany temat  Args:     request: Parametry tekstu kreatywnego  Returns:     Wygenerowany tekst kreatywny |
| `POST` | `/api/writer/fashion/analyze` | analyze_fashion_content | Analizuj tekst pod kątem mody i stylu  Args:     text: Tekst do analizy  Returns:     Analiza modowa tekstu |
| `POST` | `/api/writer/product` | create_product_description | Generuj opis produktu dla różnych platform  Args:     request: Parametry opisu produktu  Returns:     Opis produktu |
| `POST` | `/api/writer/sales/masterpiece` | create_sales_masterpiece | Generuj mistrzowski tekst sprzedażowy  Args:     request: Parametry tekstu sprzedażowego  Returns:     Profesjonalny tekst sprzedażowy |
| `POST` | `/api/writer/social` | create_social_media_post | Generuj posty na media społecznościowe  Args:     request: Parametry posta społecznościowego  Returns:     Lista wariantów postów |
| `GET` | `/api/writer/status` | get_writer_status | Status modułu Writer Pro  Returns:     Informacje o dostępności funkcji pisarskich |
| `POST` | `/api/writer/technical/masterpiece` | create_technical_masterpiece | Generuj mistrzowską dokumentację techniczną  Args:     request: Parametry dokumentacji technicznej  Returns:     Kompletna dokumentacja techniczna |
| `GET` | `/api/writer/templates` | get_writing_templates | Pobierz dostępne szablony pisarskie  Returns:     Lista dostępnych szablonów i ich parametrów |
| `POST` | `/api/writing/auction` | auction_description | Generator opisów aukcyjnych. |
| `GET` | `/api/writing/auction/kb/fetch` | fetch_auction_kb | Pobierz bazę wiedzy aukcyjnej. |
| `POST` | `/api/writing/auction/kb/learn` | learn_auction_kb | Naucz bazę wiedzy aukcyjnej nowych elementów. |
| `POST` | `/api/writing/auction/pro` | auction_pro_description | Generator profesjonalnych opisów aukcyjnych z wersją A/B. |
| `POST` | `/api/writing/auction/suggest-tags` | suggest_auction_tags | Sugeruj tagi dla aukcji. |
| `POST` | `/api/writing/creative` | creative_writing | Kreatywne pisanie artykułów, esejów i tekstów. |
| `POST` | `/api/writing/fashion/analyze` | fashion_analysis | Analiza tekstu pod kątem elementów mody. |
| `POST` | `/api/writing/masterpiece/article` | masterpiece_article | Generator mistrzowskich artykułów. |
| `POST` | `/api/writing/masterpiece/sales` | sales_masterpiece | Generator mistrzowskich tekstów sprzedażowych. |
| `POST` | `/api/writing/masterpiece/technical` | technical_masterpiece | Generator mistrzowskich wyjaśnień technicznych. |
| `POST` | `/api/writing/social` | social_media_post | Generator postów do mediów społecznościowych. |
| `POST` | `/api/writing/vinted` | vinted_description | Generator opisów dla Vinted. |
| `GET` | `/app` | serve_frontend | Główny interfejs czatu - Angular SPA lub WebUI |
| `GET` | `/balance` | get_balance | Sprawdź saldo 2captcha |
| `GET` | `/chat` | serve_frontend | Główny interfejs czatu - Angular SPA lub WebUI |
| `GET` | `/docs` | swagger_ui_html |  |
| `GET` | `/docs/oauth2-redirect` | swagger_ui_redirect |  |
| `GET` | `/favicon.ico` | serve_favicon | Favicon |
| `GET` | `/health` | health | Health check |
| `GET` | `/health` | health_check | Health check dla Prometheus |
| `GET` | `/manifest.webmanifest` | serve_manifest | Web App Manifest |
| `GET` | `/metrics` | _metrics |  |
| `GET` | `/metrics` | get_prometheus_metrics | Endpoint dla Prometheus - metryki w formacie tekstowym |
| `GET` | `/ngsw-worker.js` | serve_service_worker | Service worker (Angular PWA lub legacy). |
| `GET` | `/openapi.json` | openapi |  |
| `GET` | `/redoc` | redoc_html |  |
| `POST` | `/solve` | solve_captcha | Rozwiąż captcha przez 2captcha API |
| `GET` | `/stats` | get_stats | Statystyki w formacie JSON |
| `GET` | `/status` | api_status | Status API |
| `GET` | `/sw.js` | serve_service_worker | Service worker (Angular PWA lub legacy). |
| `GET` | `/webui/` | webui_index |  |
| `GET` | `/{full_path:path}` | angular_catch_all | Przekieruj wszystkie nieznane ścieżki do Angular SPA (dla routingu) |
