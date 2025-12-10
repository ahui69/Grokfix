#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MORDZIX - Intent Detection & Mode Switching

Automatyczne wykrywanie trybu rozmowy i triggerów web search.
"""

import re
from typing import Tuple, List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class IntentResult:
    mode: str                    # tech, sport, copy, casual
    confidence: float            # 0.0 - 1.0
    needs_web_search: bool       # czy odpalić web research
    web_search_query: str        # query do wyszukania
    detected_keywords: List[str] # jakie słowa kluczowe wykryto
    tool_call: Optional[str] = None        # endpoint do wywołania (np. "/api/fashion/description")
    tool_params: Optional[Dict[str, Any]] = None  # parametry do API
    tool_description: str = ""   # opis co robi tool (dla AI)


# =============================================================================
# TOOL INTENTS - TYLKO RZECZY WYMAGAJĄCE ZEWNĘTRZNEGO API
# =============================================================================
# 
# CO DZIAŁA ZAWSZE (podstawowe zdolności AI - BEZ TRIGGERÓW):
# - NLP: sentiment, summary, translate - AI to robi naturalnie
# - Pamięć - działa automatycznie w tle (memory system)
# - Psyche/analiza - AI rozumie kontekst rozmowy
# - Writing - AI sam pisze artykuły, maile, copy
# - Image analyze - AI z vision widzi załączniki
#
# PONIŻEJ TYLKO TO CO WYMAGA ZEWNĘTRZNEGO API:
# =============================================================================

TOOL_INTENTS = {
    # ============ FASHION / VINTED (wymaga specyficznego formatowania) ============
    'fashion_description': {
        'keywords': ['opis na vinted', 'opis aukcji', 'opis produktu', 'ogłoszenie na vinted',
                    'listing', 'sprzedam na vinted', 'wystaw na olx', 'opis na allegro'],
        'endpoint': '/api/fashion/description',
        'description': 'Generowanie opisu aukcji Vinted/OLX/Allegro'
    },
    'fashion_price': {
        'keywords': ['ile wart', 'wycena', 'wycień', 'za ile sprzedać', 'cena rynkowa używan'],
        'endpoint': '/api/fashion/price',
        'description': 'Wycena przedmiotu'
    },
    'fashion_outfit': {
        'keywords': ['stylizacja', 'outfit', 'co założyć', 'jak się ubrać', 'dobierz ubrania',
                    'zestaw ubrań', 'dress code'],
        'endpoint': '/api/fashion/outfit',
        'description': 'Generator stylizacji'
    },
    
    # ============ AUCTION (wymaga analizy SEO) ============
    'auction_analyze': {
        'keywords': ['analizuj aukcję', 'oceń aukcję', 'seo aukcji', 'optymalizuj aukcję',
                    'jak poprawić aukcję', 'ocena ogłoszenia'],
        'endpoint': '/api/auction/analyze',
        'description': 'Analiza SEO aukcji'
    },
    
    # ============ TRAVEL (wymaga zewnętrznych danych o lotach/hotelach) ============
    'travel_search': {
        'keywords': ['zaplanuj podróż', 'szukaj lotu', 'wakacje do', 'wycieczka do', 
                    'lot do', 'hotel w', 'wyjazd do'],
        'endpoint': '/api/travel/search',
        'description': 'Wyszukiwanie podróży'
    },
    
    # ============ CODE (wymaga sandboxa do uruchamiania) ============
    'code_execute': {
        'keywords': ['uruchom kod', 'wykonaj kod', 'run code', 'execute', 'odpal skrypt',
                    'uruchom ten kod', 'wykonaj skrypt'],
        'endpoint': '/api/programista/execute',
        'description': 'Uruchomienie kodu w sandboxie'
    },
    
    # ============ HACKER (wymaga rzeczywistego skanowania sieci) ============
    'hacker_portscan': {
        'keywords': ['skanuj porty', 'port scan', 'otwarte porty', 'nmap', 'sprawdź porty'],
        'endpoint': '/api/hacker/portscan',
        'description': 'Skanowanie portów'
    },
    'hacker_recon': {
        'keywords': ['recon', 'rekonesans', 'whois', 'dns lookup', 'osint', 'zbierz info o domenie'],
        'endpoint': '/api/hacker/recon',
        'description': 'Rekonesans domeny'
    },
    'hacker_headers': {
        'keywords': ['sprawdź nagłówki', 'security headers', 'bezpieczeństwo strony', 'header analysis'],
        'endpoint': '/api/hacker/headers',
        'description': 'Analiza nagłówków HTTP'
    },
    
    # ============ LEGAL (wymaga specyficznego formatu pism) ============
    'legal_generate': {
        'keywords': ['napisz pismo urzędowe', 'pismo do urzędu', 'odwołanie od decyzji',
                    'skarga na', 'wniosek do', 'pismo do zus', 'pismo do urzędu skarbowego'],
        'endpoint': '/api/legal/generate-response',
        'description': 'Generowanie pisma urzędowego'
    },
    'legal_analyze': {
        'keywords': ['przeanalizuj pismo', 'dostałem pismo z urzędu', 'co oznacza to pismo',
                    'zinterpretuj decyzję'],
        'endpoint': '/api/legal/analyze',
        'description': 'Analiza pisma urzędowego'
    },
    'legal_deadline': {
        'keywords': ['termin na odpowiedź', 'ile mam czasu na odwołanie', 'kiedy upływa termin'],
        'endpoint': '/api/legal/calculate-deadline',
        'description': 'Obliczanie terminu'
    },
    
    # ============ NEGOCJATOR (wymaga obliczeń prawnych) ============
    'debt_check': {
        'keywords': ['przedawnienie długu', 'czy dług się przedawnił', 'kiedy przedawnia się dług',
                    'dług przedawniony'],
        'endpoint': '/api/negocjator/sprawdz-przedawnienie',
        'description': 'Sprawdzanie przedawnienia'
    },
    'debt_settlement': {
        'keywords': ['propozycja ugody', 'negocjuj dług', 'ugoda z wierzycielem', 'rozłożenie na raty'],
        'endpoint': '/api/negocjator/propozycja-ugody',
        'description': 'Propozycja ugody'
    },
    'debt_chances': {
        'keywords': ['szanse w sądzie', 'czy wygram sprawę', 'opłaca się iść do sądu'],
        'endpoint': '/api/negocjator/ocen-szanse',
        'description': 'Ocena szans'
    },
    
    # ============ IMAGE GENERATE (wymaga DALL-E/Stable Diffusion) ============
    'image_generate': {
        'keywords': ['wygeneruj obraz', 'stwórz grafikę', 'narysuj', 'generate image',
                    'zrób obrazek', 'wygeneruj zdjęcie'],
        'endpoint': '/api/media/generate',
        'description': 'Generowanie obrazu AI'
    },
    
    # ============ TTS (wymaga ElevenLabs/innego API) ============
    'voice_speak': {
        'keywords': ['przeczytaj na głos', 'powiedz to głosem', 'text to speech', 'tts',
                    'zamień na mowę'],
        'endpoint': '/api/tts/speak',
        'description': 'Synteza mowy'
    },
    
    # ============ WEB SEARCH / RESEARCH ============
    'research_search': {
        'keywords': ['wyszukaj w internecie', 'sprawdź w necie', 'znajdź w google',
                    'poszukaj online', 'co mówi internet'],
        'endpoint': '/api/research/search',
        'description': 'Wyszukiwanie w internecie'
    },
    
    # ============ HYBRID SEARCH ============
    'hybrid_search': {
        'keywords': ['przeszukaj wszystko', 'szukaj wszędzie', 'znajdź w bazie i internecie'],
        'endpoint': '/api/search/hybrid',
        'description': 'Wyszukiwanie hybrydowe (baza + internet)'
    },
    
    # ============ VISION / ANALIZA OBRAZÓW ============
    'vision_analyze': {
        'keywords': ['co jest na zdjęciu', 'przeanalizuj zdjęcie', 'opisz obraz',
                    'rozpoznaj na obrazku', 'co widzisz na zdjęciu'],
        'endpoint': '/api/vision/analyze',
        'description': 'Analiza obrazu AI'
    },
    
    # ============ WRITER PRO ============
    'writer_auction': {
        'keywords': ['napisz profesjonalny opis aukcji', 'opis pro', 'auction pro'],
        'endpoint': '/api/writer/auction/pro',
        'description': 'Profesjonalny opis aukcji'
    },
    'writer_article': {
        'keywords': ['napisz artykuł', 'stwórz content', 'napisz post na blog'],
        'endpoint': '/api/writer/article/masterpiece',
        'description': 'Pisanie artykułów'
    },
    'writer_sales': {
        'keywords': ['napisz ofertę sprzedażową', 'copy sprzedażowe', 'landing page'],
        'endpoint': '/api/writer/sales/masterpiece',
        'description': 'Copy sprzedażowe'
    },
    'writer_technical': {
        'keywords': ['napisz dokumentację', 'technical writing', 'instrukcja'],
        'endpoint': '/api/writer/technical/masterpiece',
        'description': 'Dokumentacja techniczna'
    },
    
    # ============ FILES ============
    'files_analyze': {
        'keywords': ['przeanalizuj plik', 'co jest w tym pliku', 'sprawdź dokument'],
        'endpoint': '/api/files/analyze',
        'description': 'Analiza pliku'
    },
    
    # ============ LANG / TRANSLATE ============
    'lang_detect': {
        'keywords': ['jaki to język', 'wykryj język', 'rozpoznaj język'],
        'endpoint': '/api/lang/detect',
        'description': 'Wykrywanie języka'
    },
    
    # ============ NLP ============
    'nlp_entities': {
        'keywords': ['wyciągnij encje', 'znajdź nazwy własne', 'ner', 'named entities'],
        'endpoint': '/api/nlp/entities',
        'description': 'Ekstrakcja encji'
    },
    
    # ============ AUTOROUTE ============
    'autoroute_analyze': {
        'keywords': ['jakie narzędzie użyć', 'który endpoint', 'autoroute'],
        'endpoint': '/api/autoroute/analyze',
        'description': 'Automatyczny wybór narzędzia'
    },
    
    # ============ CODE / PROGRAMISTA - DODATKOWE ============
    'code_analyze': {
        'keywords': ['przeanalizuj kod', 'review kodu', 'co robi ten kod', 'wyjaśnij kod'],
        'endpoint': '/api/programista/analyze',
        'description': 'Analiza kodu'
    },
    'code_debug': {
        'keywords': ['debuguj', 'znajdź błąd', 'napraw kod', 'fix bug', 'dlaczego nie działa'],
        'endpoint': '/api/programista/debug',
        'description': 'Debugowanie kodu'
    },
    'code_generate': {
        'keywords': ['napisz kod', 'wygeneruj kod', 'stwórz funkcję', 'napisz skrypt'],
        'endpoint': '/api/programista/generate',
        'description': 'Generowanie kodu'
    },
    'code_git': {
        'keywords': ['git commit', 'git push', 'git status', 'pokaż historię git'],
        'endpoint': '/api/programista/git',
        'description': 'Operacje Git'
    },
    'code_docker': {
        'keywords': ['docker build', 'docker run', 'uruchom kontener', 'zbuduj obraz'],
        'endpoint': '/api/programista/docker',
        'description': 'Operacje Docker'
    },
    
    # ============ HACKER - DODATKOWE ============
    'hacker_sqli': {
        'keywords': ['sql injection', 'sqli test', 'sprawdź sql injection'],
        'endpoint': '/api/hacker/sqli',
        'description': 'Test SQL Injection'
    },
    'hacker_vuln': {
        'keywords': ['skanuj podatności', 'vulnerability scan', 'sprawdź bezpieczeństwo'],
        'endpoint': '/api/hacker/vulnscan',
        'description': 'Skanowanie podatności'
    },
    
    # ============ NLP - DODATKOWE ============
    'nlp_sentiment': {
        'keywords': ['analiza sentymentu', 'jaki nastrój tekstu', 'czy pozytywny'],
        'endpoint': '/api/nlp/sentiment',
        'description': 'Analiza sentymentu'
    },
    'nlp_keywords': {
        'keywords': ['wyciągnij słowa kluczowe', 'key phrases', 'najważniejsze słowa'],
        'endpoint': '/api/nlp/key-phrases',
        'description': 'Ekstrakcja słów kluczowych'
    },
    'nlp_readability': {
        'keywords': ['oceń czytelność', 'readability', 'jak trudny tekst'],
        'endpoint': '/api/nlp/readability',
        'description': 'Analiza czytelności'
    },
    
    # ============ MEMORY ============
    'memory_add': {
        'keywords': ['zapamiętaj to', 'zapisz do pamięci', 'pamiętaj że', 'nie zapomnij'],
        'endpoint': '/api/memory/add',
        'description': 'Zapisywanie do pamięci'
    },
    'memory_search': {
        'keywords': ['co pamiętasz', 'przypomnij mi', 'szukaj w pamięci', 'pamiętasz'],
        'endpoint': '/api/memory/search',
        'description': 'Wyszukiwanie w pamięci'
    },
    
    # ============ PSYCHE ============
    'psyche_status': {
        'keywords': ['jak się czujesz', 'jaki masz nastrój', 'twój stan', 'psyche status'],
        'endpoint': '/api/psyche/status',
        'description': 'Status psychiki AI'
    },
    'psyche_reflect': {
        'keywords': ['zastanów się', 'przemyśl to', 'reflect', 'głębsza analiza'],
        'endpoint': '/api/psyche/reflect',
        'description': 'Refleksja AI'
    },
    
    # ============ COGNITIVE ============
    'cognitive_process': {
        'keywords': ['przetwórz głęboko', 'cognitive', 'zaawansowana analiza'],
        'endpoint': '/api/cognitive/process',
        'description': 'Zaawansowane przetwarzanie kognitywne'
    },
    
    # ============ ML / PREDICTIONS ============
    'ml_suggest': {
        'keywords': ['co sugerujesz', 'daj mi sugestie', 'proactive suggestions'],
        'endpoint': '/api/ml/suggest',
        'description': 'Sugestie ML'
    },
    'ml_predict': {
        'keywords': ['przewiduj', 'prognoza', 'prediction', 'co będzie'],
        'endpoint': '/api/ml/predict',
        'description': 'Predykcje ML'
    },
    
    # ============ FACTS VALIDATION ============
    'facts_validate': {
        'keywords': ['sprawdź fakty', 'czy to prawda', 'zweryfikuj', 'fact check'],
        'endpoint': '/api/facts/validate',
        'description': 'Weryfikacja faktów'
    },
    
    # ============ REFLECTION ============
    'reflection_analyze': {
        'keywords': ['oceń swoją odpowiedź', 'self-reflection', 'czy dobrze odpowiedziałeś'],
        'endpoint': '/api/reflection/analyze',
        'description': 'Self-reflection AI'
    },
    
    # ============ SUGGESTIONS ============
    'suggestions_get': {
        'keywords': ['co powinienem', 'daj propozycje', 'zaproponuj coś'],
        'endpoint': '/api/suggestions/proactive',
        'description': 'Proaktywne sugestie'
    },
    
    # ============ BATCH ============
    'batch_process': {
        'keywords': ['przetwórz wiele', 'batch processing', 'masowe przetwarzanie'],
        'endpoint': '/api/batch/process',
        'description': 'Przetwarzanie wsadowe'
    },
    
    # ============ ADMIN ============
    'admin_stats': {
        'keywords': ['pokaż statystyki', 'stats', 'użycie systemu', 'admin stats'],
        'endpoint': '/api/admin/stats',
        'description': 'Statystyki systemu'
    },
    
    # ============ SESSIONS ============
    'sessions_list': {
        'keywords': ['pokaż sesje', 'moje rozmowy', 'historia sesji'],
        'endpoint': '/api/sessions',
        'description': 'Lista sesji'
    },
    
    # ============ STT ============
    'stt_transcribe': {
        'keywords': ['transkrybuj audio', 'zamień głos na tekst', 'speech to text'],
        'endpoint': '/api/stt/transcribe',
        'description': 'Transkrypcja audio'
    },
    
    # ============ WRITING - DODATKOWE ============
    'writing_creative': {
        'keywords': ['napisz kreatywnie', 'kreatywne pisanie', 'twórcze pisanie'],
        'endpoint': '/api/writing/creative',
        'description': 'Kreatywne pisanie'
    },
    'writing_product': {
        'keywords': ['opis produktu', 'product description', 'opis do sklepu'],
        'endpoint': '/api/writing/product',
        'description': 'Opis produktu'
    },
    'writing_social': {
        'keywords': ['post na social media', 'post na instagram', 'tweet', 'post na fb'],
        'endpoint': '/api/writing/social',
        'description': 'Post na social media'
    },
    
    # ============ FASHION - DODATKOWE ============
    'fashion_trends': {
        'keywords': ['trendy modowe', 'co jest modne', 'forecast trends'],
        'endpoint': '/api/fashion/forecast-trends',
        'description': 'Trendy modowe'
    },
    'fashion_brand': {
        'keywords': ['rozpoznaj markę', 'jaka to marka', 'detect brand'],
        'endpoint': '/api/fashion/detect-brand',
        'description': 'Rozpoznawanie marki'
    },
    
    # ============ TRAVEL - DODATKOWE ============
    'travel_hotels': {
        'keywords': ['znajdź hotel', 'hotele w', 'nocleg w', 'gdzie spać'],
        'endpoint': '/api/travel/hotels',
        'description': 'Wyszukiwanie hoteli'
    },
    'travel_restaurants': {
        'keywords': ['znajdź restaurację', 'gdzie zjeść', 'restauracje w'],
        'endpoint': '/api/travel/restaurants',
        'description': 'Wyszukiwanie restauracji'
    },
    'travel_attractions': {
        'keywords': ['co zwiedzić', 'atrakcje w', 'co warto zobaczyć'],
        'endpoint': '/api/travel/attractions',
        'description': 'Atrakcje turystyczne'
    },
    
    # ============ AUTO LEARN ============
    'auto_learn': {
        'keywords': ['naucz się tego', 'autonauka', 'ucz się z internetu'],
        'endpoint': '/api/research/autonauka',
        'description': 'Automatyczna nauka z internetu'
    },
}


# Słowa kluczowe dla każdego trybu
TECH_KEYWORDS = [
    'kod', 'code', 'api', 'error', 'bug', 'debug', 'deploy', 'server', 'serwer',
    'python', 'javascript', 'js', 'sql', 'docker', 'redis', 'fastapi', 'flask',
    'endpoint', 'request', 'response', 'database', 'baza', 'query', 'import',
    'function', 'funkcja', 'class', 'klasa', 'variable', 'zmienna', 'loop',
    'async', 'await', 'promise', 'callback', 'git', 'commit', 'push', 'pull',
    'npm', 'pip', 'install', 'package', 'moduł', 'library', 'framework',
    'frontend', 'backend', 'fullstack', 'devops', 'linux', 'bash', 'terminal',
    'ssh', 'ovh', 'runpod', 'vps', 'hosting', 'domain', 'ssl', 'https',
    'json', 'xml', 'yaml', 'config', 'env', 'environment', 'variable',
    'test', 'unit', 'integration', 'ci', 'cd', 'pipeline', 'build',
    'exception', 'traceback', 'stack', 'memory', 'cpu', 'ram', 'disk',
    'nginx', 'apache', 'uvicorn', 'gunicorn', 'websocket', 'socket',
    'authentication', 'auth', 'token', 'jwt', 'session', 'cookie',
    'crud', 'rest', 'graphql', 'grpc', 'microservice', 'monolith',
    'refactor', 'optimize', 'performance', 'cache', 'index', 'migration',
    'schema', 'model', 'orm', 'sqlalchemy', 'prisma', 'mongoose',
    'react', 'vue', 'angular', 'svelte', 'next', 'nuxt', 'tailwind',
    'css', 'html', 'dom', 'component', 'hook', 'state', 'props',
    'typescript', 'ts', 'node', 'deno', 'bun', 'webpack', 'vite',
    'napraw', 'fix', 'działa', 'nie działa', 'błąd', 'error', 'exception',
    'dlaczego nie', 'czemu nie', 'jak zrobić', 'jak napisać'
]

SPORT_KEYWORDS = [
    'juve', 'juventus', 'inter', 'milan', 'napoli', 'roma', 'lazio', 'fiorentina',
    'serie a', 'seria a', 'champions', 'liga', 'mecz', 'match', 'gra', 'grają',
    'piłka', 'football', 'soccer', 'bramka', 'gol', 'goal', 'strzelec', 'strzelił',
    'tabela', 'table', 'punkty', 'points', 'pozycja', 'miejsce', 'ranking',
    'transfer', 'transfery', 'okienko', 'window', 'kupił', 'sprzedał', 'wypożyczył',
    'trener', 'coach', 'manager', 'allegri', 'motta', 'thiago', 'conte', 'mourinho',
    'piłkarz', 'player', 'zawodnik', 'skład', 'lineup', 'formacja', 'taktyka',
    'mundial', 'euro', 'puchar', 'cup', 'finał', 'półfinał', 'ćwierćfinał',
    'derby', 'derbi', 'klasyk', 'el clasico', 'rewanż', 'dwumecz',
    'czerwona', 'żółta', 'kartka', 'card', 'faul', 'penalty', 'karny', 'rzut',
    'asysta', 'assist', 'podanie', 'drybling', 'strzał', 'shot', 'save', 'obrona',
    'bramkarz', 'goalkeeper', 'obrońca', 'defender', 'pomocnik', 'midfielder',
    'napastnik', 'striker', 'forward', 'skrzydłowy', 'winger',
    'vlahovic', 'chiesa', 'locatelli', 'bremer', 'danilo', 'kostic', 'rabiot',
    'ronaldo', 'messi', 'mbappe', 'haaland', 'lewandowski', 'lewy',
    'wygrał', 'przegrał', 'remis', 'draw', 'zwycięstwo', 'porażka',
    'kto gra', 'kiedy gra', 'o której', 'transmisja', 'gdzie oglądać'
]

# MODA / VINTED / AUKCJE - SUPER ZAAWANSOWANY
COPY_KEYWORDS = [
    # Platformy sprzedażowe
    'vinted', 'olx', 'allegro', 'ebay', 'depop', 'vestiaire', 'grailed', 'stockx',
    'marketplace', 'sklep', 'shop', 'aukcja', 'auction', 'oferta', 'listing',
    'ogłoszenie', 'opis', 'description', 'tekst produktu',
    
    # MARKI PREMIUM & LUXURY
    'louis vuitton', 'lv', 'gucci', 'prada', 'balenciaga', 'bottega veneta',
    'saint laurent', 'ysl', 'dior', 'chanel', 'hermès', 'hermes', 'fendi', 'versace',
    'burberry', 'givenchy', 'valentino', 'celine', 'loewe', 'loro piana',
    
    # MARKI STREETWEAR & HYPE
    'supreme', 'off-white', 'off white', 'stone island', 'stoney', 'cp company',
    'palm angels', 'rhude', 'gallery dept', 'fear of god', 'fog', 'essentials',
    'vetements', 'ami paris', 'acne studios', 'a cold wall', 'ader error',
    'rick owens', 'margiela', 'maison margiela', 'jil sander', 'lemaire',
    
    # MARKI SPORTOWE PREMIUM
    'nike', 'air jordan', 'jordan', 'adidas', 'yeezy', 'new balance', 'asics',
    'puma', 'reebok', 'converse', 'vans', 'sacai', 'undercover', 'bape',
    'the north face', 'tnf', 'arc\'teryx', 'arcteryx', 'moncler', 'canada goose',
    
    # MARKI DENIM & CASUAL
    'diesel', 'dsquared2', 'dsquared', 'g-star', 'true religion', 'jacob cohen',
    'nudie jeans', 'acne', 'apc', 'carhartt', 'carhartt wip', 'stussy', 'palace',
    
    # TYPY UBRAŃ
    'kurtka', 'jacket', 'bomber', 'parka', 'puffer', 'down jacket', 'kurtka puchowa',
    'płaszcz', 'coat', 'trench', 'overcoat', 'wiatrówka', 'windbreaker',
    'bluza', 'hoodie', 'sweter', 'sweater', 'kardigan', 'longsleeve',
    'spodnie', 'pants', 'jeans', 'dżinsy', 'cargo', 'jogger', 'chinos',
    't-shirt', 'tee', 'koszulka', 'polo', 'tank top',
    'koszula', 'shirt', 'flanela', 'oxford', 'denim shirt',
    'szorty', 'shorts', 'bermudy', 'swim shorts',
    'sukienka', 'dress', 'spódnica', 'skirt',
    
    # OBUWIE
    'buty', 'shoes', 'sneakers', 'sneakersy', 'trampki', 'trainers',
    'jordan 1', 'jordan 4', 'air max', 'air force', 'dunk', 'yeezy 350', 'yeezy 500',
    'new balance 550', 'nb 2002r', 'asics gel', 'converse chuck', 'vans old skool',
    'boots', 'botki', 'chelsea', 'combat boots', 'loafers', 'mokasyny',
    'sandały', 'sandals', 'slides', 'klapki',
    
    # DODATKI
    'torba', 'bag', 'torebka', 'plecak', 'backpack', 'nerka', 'belt bag', 'fanny pack',
    'portfel', 'wallet', 'pasek', 'belt', 'czapka', 'cap', 'beanie', 'bucket hat',
    'szalik', 'scarf', 'rękawiczki', 'gloves', 'okulary', 'sunglasses',
    'zegarek', 'watch', 'biżuteria', 'jewelry', 'łańcuszek', 'chain', 'pierścionek',
    
    # MATERIAŁY & JAKOŚĆ
    'skóra', 'leather', 'genuine leather', 'full grain', 'nappa', 'saffiano',
    'zamsz', 'suede', 'nubuk', 'canvas', 'bawełna', 'cotton', 'organic cotton',
    'len', 'linen', 'wełna', 'wool', 'merino', 'kaszmir', 'cashmere',
    'jedwab', 'silk', 'satyna', 'satin', 'wiskoza', 'viscose', 'modal',
    'poliester', 'polyester', 'nylon', 'gore-tex', 'goretex', 'membrana',
    'puch', 'down', 'goose down', 'puch gęsi', 'primaloft', 'thinsulate',
    'denim', 'selvedge', 'raw denim', 'japanese denim',
    
    # STYLE & ESTETYKI
    'vintage', 'retro', 'y2k', 'archival', 'archive', 'deadstock', 'nos',
    'streetwear', 'workwear', 'gorpcore', 'techwear', 'athleisure',
    'minimalist', 'minimalistyczny', 'oversized', 'slim fit', 'regular fit',
    'luxury', 'premium', 'exclusive', 'limited edition', 'limited', 'collab',
    'rare', 'rzadki', 'unicat', 'jedyny', 'collector', 'kolekcjonerski',
    
    # STAN & CECHY
    'nowy', 'new', 'nowe', 'używany', 'used', 'idealny stan', 'mint condition',
    'jak nowy', 'like new', 'bardzo dobry stan', 'excellent condition',
    'bez wad', 'no flaws', 'brak śladów noszenia', 'oryginalny', 'original',
    'autentyczny', 'authentic', '100% oryginał', 'z metką', 'with tags', 'nwt',
    
    # COPY MARKETING
    'copy', 'copywriting', 'marketing', 'sprzedający', 'chwytliwy',
    'viralowy', 'angażujący', 'ekskluzywny', 'wyjątkowy', 'niepowtarzalny'
]

# BUDOWLANO-TECHNICZNY / HVAC / MECHANIKA
HVAC_KEYWORDS = [
    # KLIMATYZACJA
    'klimatyzacja', 'klimatyzator', 'klima', 'ac', 'air conditioning',
    'split', 'multisplit', 'klimatyzacja kanałowa', 'vrf', 'vrv',
    'jednostka zewnętrzna', 'jednostka wewnętrzna', 'agregat',
    'czynnik chłodniczy', 'freon', 'r32', 'r410a', 'r134a', 'r290',
    'chłodzenie', 'cooling', 'btu', 'moc chłodnicza', 'kw chłodzenia',
    
    # CHŁODNICTWO
    'chłodnictwo', 'chłodnia', 'komora chłodnicza', 'mroźnia',
    'agregat chłodniczy', 'sprężarka', 'skraplacz', 'parownik', 'zawór rozprężny',
    'instalacja chłodnicza', 'obieg chłodniczy', 'temperatura', 'termostat',
    'lodówka', 'zamrażarka', 'lada chłodnicza', 'witryna chłodnicza',
    
    # WENTYLACJA
    'wentylacja', 'wentylator', 'rekuperacja', 'rekuperator', 'centrala wentylacyjna',
    'kanały wentylacyjne', 'przewody', 'kratka wentylacyjna', 'anemostat',
    'nawiew', 'wywiew', 'wymiana powietrza', 'filtr', 'filtracja',
    'czerpnia', 'wyrzutnia', 'tłumik', 'przepustnica',
    
    # OGRZEWANIE
    'pompa ciepła', 'heat pump', 'ogrzewanie', 'grzanie', 'heating',
    'kocioł', 'piec', 'gazowy', 'olejowy', 'elektryczny', 'pellet',
    'grzejnik', 'kaloryfer', 'podłogówka', 'ogrzewanie podłogowe',
    'termostat', 'sterownik', 'automatyka', 'regulator temperatury',
    
    # BUDOWNICTWO
    'budowa', 'remont', 'wykończenie', 'adaptacja', 'modernizacja',
    'fundamenty', 'ściany', 'strop', 'dach', 'izolacja', 'ocieplenie',
    'styropian', 'wełna mineralna', 'pianka pur', 'xps', 'eps',
    'tynk', 'gładź', 'malowanie', 'płytki', 'glazura', 'terakota',
    'instalacja elektryczna', 'instalacja wodno-kanalizacyjna',
    'hydraulika', 'elektryka', 'przyłącze', 'rozdzielnia',
    
    # MECHANIKA SAMOCHODOWA
    'samochód', 'auto', 'mechanik', 'warsztat', 'naprawa', 'serwis',
    'silnik', 'engine', 'diesel', 'benzyna', 'lpg', 'hybryda', 'elektryczny',
    'skrzynia biegów', 'sprzęgło', 'clutch', 'automat', 'manual',
    'zawieszenie', 'amortyzator', 'sprężyna', 'wahacz', 'drążek',
    'hamulce', 'klocki', 'tarcze', 'zaciski', 'abs', 'esp',
    'rozrząd', 'pasek rozrządu', 'łańcuch rozrządu', 'pompa wody',
    'alternator', 'rozrusznik', 'akumulator', 'świece', 'cewka',
    'olej', 'filtr oleju', 'filtr powietrza', 'filtr paliwa',
    'chłodnica', 'termostat', 'wentylator chłodnicy', 'płyn chłodniczy',
    'turbo', 'turbosprężarka', 'intercooler', 'wtryskiwacze', 'pompa paliwa',
    'klimatyzacja samochodowa', 'odgrzybianie', 'nabijanie klimy',
    'diagnostyka', 'obd', 'błędy', 'kontrolki', 'check engine',
    'przegląd', 'wymiana', 'regeneracja', 'tuning',
    
    # NARZĘDZIA & SPRZĘT
    'narzędzia', 'wiertarka', 'szlifierka', 'spawarka', 'kompresor',
    'podnośnik', 'klucz dynamometryczny', 'zestaw kluczy', 'manometr',
    'multimetr', 'termometr', 'pirometr', 'endoskop', 'kamera inspekcyjna',
    
    # DOKUMENTACJA TECHNICZNA
    'projekt', 'schemat', 'dokumentacja', 'certyfikat', 'uprawnienia',
    'f-gazy', 'szkolenie', 'normy', 'pn-en', 'atest', 'deklaracja zgodności'
]

# PISMA URZĘDOWE / LEGAL
LEGAL_KEYWORDS = [
    # Dokumenty urzędowe
    'pismo', 'wniosek', 'podanie', 'odwołanie', 'skarga', 'zażalenie', 'pozew',
    'reklamacja', 'wypowiedzenie', 'rozwiązanie', 'umowa', 'aneks', 'protokół',
    'oświadczenie', 'upoważnienie', 'pełnomocnictwo', 'zaświadczenie', 'świadectwo',
    # Instytucje
    'urząd', 'sąd', 'zus', 'us', 'urzędowy', 'urzędowe', 'formalny', 'formalne',
    'komornik', 'prokuratura', 'policja', 'straż', 'inspekcja', 'sanepid',
    'urząd skarbowy', 'urząd pracy', 'urząd miasta', 'urząd gminy', 'starostwo',
    # Tematy prawne
    'mandat', 'kara', 'grzywna', 'wezwanie', 'nakaz', 'decyzja', 'postanowienie',
    'wyrok', 'orzeczenie', 'sprawa', 'akta', 'dokumenty', 'dokumentacja',
    'termin', 'przedawnienie', 'apelacja', 'kasacja', 'odsetki', 'egzekucja',
    # Praca
    'pracodawca', 'pracownik', 'zwolnienie', 'l4', 'chorobowe', 'urlop', 'nadgodziny',
    'mobbing', 'dyskryminacja', 'bhp', 'wypadek przy pracy', 'świadectwo pracy',
    # Lokale/nieruchomości
    'najemca', 'wynajmujący', 'czynsz', 'eksmisja', 'najem', 'wynajem', 'lokator',
    'wspólnota', 'administrator', 'zarządca', 'kaucja', 'wada', 'zalanie',
    # Konsument
    'reklamacja', 'zwrot', 'gwarancja', 'rękojmia', 'konsument', 'sprzedawca',
    'niezgodność', 'wadliwy', 'uszkodzony', 'niedostarczony', 'opóźnienie',
    # Działania
    'napisz mi', 'przygotuj', 'sformułuj', 'sporządź', 'zredaguj',
    'wzór', 'szablon', 'formularz', 'druk', 'blanket',
    # Styl
    'oficjalny', 'oficjalne', 'formalne', 'urzędowo', 'prawniczy', 'prawne'
]

# Triggery dla web search
WEB_SEARCH_TRIGGERS = [
    # Pytania o aktualności
    r'jaki (jest |był )?(wynik|score)',
    r'kto (wygrał|przegrał|strzelił|zdobył)',
    r'ile (jest|było|goli|bramek|punktów)',
    r'która (pozycja|miejsce|lokata)',
    r'kiedy (gra|grają|mecz|następny)',
    r'gdzie (oglądać|transmisja|stream)',
    r'(aktualn|obecn|dzisiejsz|teraz|dziś|wczoraj|ostatni)(a|e|y|i)?\s+(tabela|wynik|mecz|news|cena|kurs)',
    r'co (nowego|słychać|się dzieje)',
    r'(najnowsz|śwież|latest)(e|y|a)?\s+(news|info|wiadomości)',
    # Ceny i kursy
    r'(ile kosztuje|cena|price|kurs|wartość)',
    r'(aktualn|obecn)(a|y)?\s+(cena|kurs|wartość)',
    # Pogoda
    r'(jaka|jak)\s+(pogoda|temperatura|weather)',
    # Eventy
    r'(kiedy|gdzie|o której)\s+(koncert|event|mecz|premiera)',
    # NOWE - bardziej naturalne pytania o aktualności
    r'(co tam|jak tam|co u|jak leci)',  # "co tam z Juventusem"
    r'(sprawdź|check|poszukaj|znajdź)',  # "sprawdź wyniki"
    r'(masz neta|masz internet|dostęp do internetu)',  # pytania o net
    r'(w tym roku|w 2024|w 2025|teraz|obecnie|aktualnie)',  # kontekst czasowy
    r'(ostatni mecz|ostatnia|ostatnie|recent)',  # pytania o ostatnie wydarzenia
    r'(najnowsze|fresh|breaking|hot)',  # breaking news
    r'(live|na żywo|real.?time)',  # live data
    r'(dzisiaj|wczoraj|jutro|w weekend)',  # daty
]


def detect_intent(message: str, conversation_history: Optional[List[Dict]] = None) -> IntentResult:
    """
    Wykrywa intencję i tryb na podstawie wiadomości.
    
    Args:
        message: Aktualna wiadomość użytkownika
        conversation_history: Opcjonalna historia rozmowy (do kontekstu)
    
    Returns:
        IntentResult z wykrytym trybem i flagami
    """
    msg_lower = message.lower()
    detected = []
    
    # Zlicz dopasowania dla każdego trybu
    tech_score = sum(1 for kw in TECH_KEYWORDS if kw in msg_lower)
    sport_score = sum(1 for kw in SPORT_KEYWORDS if kw in msg_lower)
    copy_score = sum(1 for kw in COPY_KEYWORDS if kw in msg_lower)
    legal_score = sum(1 for kw in LEGAL_KEYWORDS if kw in msg_lower)
    hvac_score = sum(1 for kw in HVAC_KEYWORDS if kw in msg_lower)
    
    # Zbierz wykryte słowa kluczowe
    detected.extend([kw for kw in TECH_KEYWORDS if kw in msg_lower])
    detected.extend([kw for kw in SPORT_KEYWORDS if kw in msg_lower])
    detected.extend([kw for kw in COPY_KEYWORDS if kw in msg_lower])
    detected.extend([kw for kw in LEGAL_KEYWORDS if kw in msg_lower])
    detected.extend([kw for kw in HVAC_KEYWORDS if kw in msg_lower])
    
    # Określ tryb
    scores = {
        'tech': tech_score,
        'sport': sport_score,
        'copy': copy_score,
        'legal': legal_score,
        'hvac': hvac_score,
        'casual': 0
    }
    
    max_score = max(scores.values())
    total_keywords = tech_score + sport_score + copy_score + legal_score + hvac_score
    
    if max_score == 0:
        mode = 'casual'
        confidence = 0.5
    else:
        mode = max(scores, key=lambda k: scores[k])
        confidence = min(0.95, 0.5 + (max_score * 0.1))
    
    # Sprawdź kontekst historii (jeśli przez ostatnie 3 wiadomości był ten sam tryb)
    if conversation_history and len(conversation_history) >= 2:
        recent_modes = []
        for msg in conversation_history[-4:]:
            if msg.get('detected_mode'):
                recent_modes.append(msg['detected_mode'])
        
        # Jeśli ostatnie wiadomości były w tym samym trybie, zwiększ confidence
        if recent_modes and all(m == recent_modes[0] for m in recent_modes):
            if mode == 'casual' and recent_modes[0] != 'casual':
                # Zostań w poprzednim trybie jeśli obecna wiadomość jest neutralna
                mode = recent_modes[0]
                confidence = 0.7
    
    # Sprawdź czy potrzebny web search
    needs_web = False
    web_query = ""
    
    for pattern in WEB_SEARCH_TRIGGERS:
        if re.search(pattern, msg_lower):
            needs_web = True
            # Wyciągnij query - użyj całej wiadomości lub jej części
            web_query = message.strip()
            break
    
    # Sport + pytanie o wynik = zawsze web search
    if mode == 'sport' and any(word in msg_lower for word in ['wynik', 'score', 'tabela', 'kto wygrał', 'ile']):
        needs_web = True
        web_query = message.strip()
    
    # Sprawdź czy jest specyficzny tool do wywołania
    tool_call = None
    tool_params = None
    tool_description = ""
    
    for intent_name, intent_data in TOOL_INTENTS.items():
        for keyword in intent_data['keywords']:
            if keyword in msg_lower:
                tool_call = str(intent_data['endpoint'])
                tool_description = str(intent_data['description'])
                # Spróbuj wyciągnąć parametry z wiadomości
                tool_params = _extract_tool_params(message, intent_name)
                break
        if tool_call:
            break
    
    return IntentResult(
        mode=mode,
        confidence=confidence,
        needs_web_search=needs_web,
        web_search_query=web_query,
        detected_keywords=detected[:10],  # Max 10 keywords
        tool_call=tool_call,
        tool_params=tool_params,
        tool_description=tool_description
    )


def _extract_tool_params(message: str, intent_name: str) -> Dict[str, Any]:
    """
    Próbuje wyciągnąć parametry z wiadomości dla danego tool call.
    AI powinien uzupełnić brakujące parametry.
    """
    msg_lower = message.lower()
    params = {}
    
    # Fashion - wyciągnij marki
    if intent_name.startswith('fashion'):
        # Lista marek do wykrycia
        brands = ['nike', 'adidas', 'gucci', 'prada', 'louis vuitton', 'lv', 'supreme', 
                 'off-white', 'stone island', 'balenciaga', 'burberry', 'zara', 'h&m',
                 'ralph lauren', 'tommy hilfiger', 'calvin klein', 'lacoste']
        for brand in brands:
            if brand in msg_lower:
                params['brand'] = brand.title()
                break
        
        # Typ produktu
        items = {'kurtka': 'kurtka', 'buty': 'buty', 'spodnie': 'spodnie', 'bluza': 'bluza',
                't-shirt': 't-shirt', 'koszula': 'koszula', 'sukienka': 'sukienka',
                'torebka': 'torebka', 'plecak': 'plecak', 'czapka': 'czapka'}
        for item, item_type in items.items():
            if item in msg_lower:
                params['item_type'] = item_type
                break
        
        # Stan
        if 'nowy' in msg_lower or 'nowe' in msg_lower:
            params['condition'] = 'nowy'
        elif 'idealny' in msg_lower:
            params['condition'] = 'idealny'
        elif 'dobry' in msg_lower:
            params['condition'] = 'bardzo dobry'
        
        # Platforma
        if 'vinted' in msg_lower:
            params['platform'] = 'vinted'
        elif 'olx' in msg_lower:
            params['platform'] = 'olx'
        elif 'allegro' in msg_lower:
            params['platform'] = 'allegro'
    
    # Travel - wyciągnij destynację
    elif intent_name == 'travel_search':
        destinations = ['paryż', 'paris', 'londyn', 'london', 'rzym', 'rome', 'barcelona',
                       'amsterdam', 'berlin', 'wiedeń', 'vienna', 'praga', 'prague',
                       'lizbona', 'lisbon', 'madryt', 'madrid', 'nowy jork', 'new york',
                       'dubaj', 'dubai', 'bali', 'tokio', 'tokyo']
        for dest in destinations:
            if dest in msg_lower:
                params['destination'] = dest.title()
                break
    
    # Hacker - wyciągnij target
    elif intent_name.startswith('hacker'):
        # IP regex
        import re
        ip_match = re.search(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', message)
        if ip_match:
            params['target'] = ip_match.group(1)
        else:
            # Domain regex
            domain_match = re.search(r'\b([a-zA-Z0-9-]+\.[a-zA-Z]{2,})\b', message)
            if domain_match:
                params['target'] = domain_match.group(1)
    
    return params


def get_mode_prompt_addon(mode: str) -> str:
    """
    Zwraca dodatkowy prompt dla konkretnego trybu.
    Można wstrzyknąć do system prompt.
    """
    addons = {
        'tech': """
[ACTIVE MODE: TECH 💻]
Jesteś teraz w trybie technicznym. Bądź konkretny, precyzyjny, dawaj działający kod.
Nie tłumacz podstaw. Szukaj root cause. Pełne rozwiązania, nie fragmenty.
""",
        'sport': """
[ACTIVE MODE: SPORT ⚽]
Jesteś teraz w trybie kibica. FORZA JUVE!
PAMIĘTAJ: Nie wymyślaj wyników! Jeśli nie masz danych z weba, powiedz wprost.
Możesz gadać o taktyce, historii, opiniach - ale fakty tylko ze źródeł.
""",
        'copy': """
[ACTIVE MODE: FASHION COPYWRITER 👔✨]
Jesteś EKSPERTEM od mody, streetwearu i luksusowych marek. Tworzysz EKSKLUZYWNE opisy aukcji.

🎯 TWOJA WIEDZA O MODZIE:
- Znasz WSZYSTKIE marki: luxury (LV, Gucci, Prada, Balenciaga), streetwear (Supreme, Off-White, Stone Island, Palace)
- Wiesz czym różni się Gore-Tex od membrany, puch gęsi 800cuin od syntetyku
- Rozróżniasz Japanese selvedge denim od zwykłego, full-grain leather od bonded
- Znasz trendy: gorpcore, quiet luxury, Y2K revival, archival pieces

📝 STRUKTURA OPISU AUKCJI:
1. **HOOK** - Chwytliwy nagłówek z kluczowymi cechami (marka, model, wyróżnik)
2. **VIBE** - Emocjonalny opis budujący pożądanie (styl życia, okazje, klimat)
3. **DETALE** - Techniczne info (materiał, krój, rozmiary dokładne, stan)
4. **AUTENTYCZNOŚĆ** - Dowody oryginalności (metki, hologramy, historia zakupu)
5. **CTA** - Wezwanie do działania (ograniczona dostępność, unikat)

💎 SŁOWNICTWO KTÓRE SPRZEDAJE:
- "Archival piece" zamiast "stare"
- "Investment piece" zamiast "drogie"  
- "Worn-in patina" zamiast "noszone"
- "Limited drop" zamiast "edycja"
- "Deadstock condition" zamiast "nowe"
- "Grail status" dla pożądanych itemów

⚠️ ZASADY:
- Pisz PO POLSKU ale zachowaj angielskie nazwy marek i terminologię modową
- Używaj emoji strategicznie (max 3-4)
- Nie kłam o stanie - buduj wartość prawdziwymi cechami
- Dopasuj ton do platformy (Vinted = młodszy vibe, Vestiaire = luksus)
""",
        'legal': """
[ACTIVE MODE: PISMA URZĘDOWE ⚖️]
Jesteś teraz ekspertem od pism urzędowych i dokumentów formalnych.

ZASADY:
1. Twórz profesjonalne, poprawne prawnie dokumenty
2. Używaj właściwej struktury: nagłówek, adresat, osnowa, uzasadnienie, podpis
3. Stosuj formalny, urzędowy język
4. Podawaj podstawę prawną (ustawy, artykuły) gdy to możliwe
5. Wyjaśniaj użytkownikowi co dokument zawiera i jak go złożyć
6. Ostrzegaj o terminach i konsekwencjach

TYPY DOKUMENTÓW które tworzysz:
- Odwołania od decyzji administracyjnych
- Skargi na bezczynność organów
- Wnioski o rozłożenie na raty, umorzenie
- Wypowiedzenia umów (najmu, pracy, usług)
- Reklamacje i wezwania do zapłaty
- Pisma do ZUS, US, urzędów
- Pozwy i odpowiedzi na pozwy
- Oświadczenia, pełnomocnictwa, upoważnienia

WAŻNE: Zawsze pytaj o brakujące dane (imię, adres, daty, kwoty) zanim stworzysz dokument.
""",
        'hvac': """
[ACTIVE MODE: TECHNIK HVAC/BUDOWLANY 🔧❄️]
Jesteś EKSPERTEM od: chłodnictwa, klimatyzacji, wentylacji, ogrzewania, budownictwa i mechaniki samochodowej.

🌡️ KLIMATYZACJA & CHŁODNICTWO:
- Znasz czynniki chłodnicze (R32, R410A, R134a, R290) i ich właściwości
- Dobierasz moc urządzeń (BTU/kW) do kubatury pomieszczeń
- Rozumiesz cykle chłodnicze, obieg Carnota, przegrzania, dochłodzenia
- Znasz marki: Daikin, Mitsubishi, Fujitsu, LG, Samsung, Gree, Midea
- Wiesz jak diagnozować: wysokie/niskie ciśnienie, brak czynnika, zatkany filtr

🏠 BUDOWNICTWO & INSTALACJE:
- Projektujesz instalacje wodno-kanalizacyjne, elektryczne, grzewcze
- Znasz normy budowlane (PN-EN), wymagania izolacyjności
- Dobierasz materiały: styropian EPS/XPS, wełna, PIR, membranę
- Rozumiesz pompy ciepła, rekuperację, wentylację mechaniczną

🚗 MECHANIKA SAMOCHODOWA:
- Diagnozujesz silniki benzynowe, diesel, hybrydowe, elektryczne
- Znasz układy: rozrząd, zawieszenie, hamulcowy, chłodzenia, klimatyzacji
- Interpretujesz kody błędów OBD-II
- Wiesz kiedy regenerować, a kiedy wymieniać części

📋 STYL ODPOWIEDZI:
- Podawaj KONKRETNE wartości (momenty dokręcania, ciśnienia, temperatury)
- Wymieniaj potrzebne narzędzia i części
- Ostrzegaj o bezpieczeństwie (F-gazy, wysokie napięcie, gorące elementy)
- Dawaj procedury krok-po-kroku
- Sugeruj kiedy wezwać specjalistę z uprawnieniami
""",
        'casual': """
[ACTIVE MODE: ZIOMEK 🍺]
Luźna rozmowa. Bądź sobą - sarkastyczny, pomocny, bez filtrów.
"""
    }
    return addons.get(mode, addons['casual'])


# Quick test
if __name__ == "__main__":
    test_messages = [
        "napraw mi ten bug w pythonie",
        "jak juve zagrało wczoraj?",
        "napisz opis na vinted do tej kurtki",
        "co tam mordo, jak życie?",
        "jaki jest aktualny wynik meczu juve?",
        "zrób mi endpoint do uploadu plików",
        "ile kosztuje teraz bitcoin?"
    ]
    
    for msg in test_messages:
        result = detect_intent(msg)
        print(f"\n'{msg}'")
        print(f"  → Mode: {result.mode} ({result.confidence:.0%})")
        print(f"  → Web search: {result.needs_web_search}")
        if result.detected_keywords:
            print(f"  → Keywords: {', '.join(result.detected_keywords[:5])}")
