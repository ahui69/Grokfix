#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TOOLS REGISTRY - Mapowanie wszystkich endpointów na format OpenAI Function Calling
Każdy z 121 endpointów opisany jako tool który może wywołać AI
"""

from typing import Dict, List, Any, Optional
import json

# ═══════════════════════════════════════════════════════════════════
# TOOLS REGISTRY - 121 endpointów jako tools dla AI
# ═══════════════════════════════════════════════════════════════════

TOOLS_REGISTRY: List[Dict[str, Any]] = [
    
    # ═══════════════════════════════════════════════════════════════════
    # ASSISTANT ENDPOINT (10 endpoints)
    # ═══════════════════════════════════════════════════════════════════
    {
        "name": "chat_assistant",
        "description": "Główna rozmowa z AI - pełna kognicja, pamięć, uczenie. Użyj gdy user chce normalnie pogadać.",
        "endpoint": "POST /api/chat/assistant",
        "parameters": {
            "type": "object",
            "properties": {
                "messages": {"type": "array", "description": "Historia konwersacji", "items": {"type": "object"}},
                "user_id": {"type": "string", "description": "ID użytkownika"},
                "use_memory": {"type": "boolean", "description": "Czy używać pamięci", "default": True},
                "auto_learn": {"type": "boolean", "description": "Czy auto-uczyć się z rozmowy", "default": True}
            },
            "required": ["messages", "user_id"]
        },
        "example": {"messages": [{"role": "user", "content": "Jak się masz?"}], "user_id": "web_user", "use_memory": True}
    },
    {
        "name": "chat_stream",
        "description": "Streaming odpowiedzi AI - jak chat_assistant ale z SSE (Server-Sent Events)",
        "endpoint": "POST /api/chat/assistant/stream",
        "parameters": {
            "type": "object",
            "properties": {
                "messages": {"type": "array", "items": {"type": "object"}},
                "user_id": {"type": "string"}
            },
            "required": ["messages", "user_id"]
        }
    },
    {
        "name": "auto_learn_web",
        "description": "Automatyczna nauka z internetu - wyszukuje w Google/SERPAPI, scrapuje strony, uczy się faktów",
        "endpoint": "POST /api/auto",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Co wyszukać i nauczyć się"},
                "topk": {"type": "integer", "description": "Ile wyników", "default": 8}
            },
            "required": ["query"]
        },
        "example": {"query": "Python async/await tutorial", "topk": 5}
    },
    
    # ═══════════════════════════════════════════════════════════════════
    # RESEARCH ENDPOINT (4 endpoints)
    # ═══════════════════════════════════════════════════════════════════
    {
        "name": "web_search",
        "description": "Wyszukiwanie w internecie - Brave Search (primary) + Tavily (AI-optimized) + DuckDuckGo (fallback). Parallel, cached 30min.",
        "endpoint": "POST /api/research/search",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Zapytanie do wyszukiwarki"},
                "max_results": {"type": "integer", "default": 10}
            },
            "required": ["query"]
        },
        "example": {"query": "best restaurants Paris 2025", "max_results": 5}
    },
    {
        "name": "autonauka",
        "description": "Pełna autonauka - wyszukuje, scrapuje, embeduje, zapisuje do LTM. Najbardziej zaawansowane research.",
        "endpoint": "POST /api/research/autonauka",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "topk": {"type": "integer", "default": 8},
                "fetch": {"type": "integer", "default": 6}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_sources",
        "description": "Pobiera zapisane źródła z poprzednich wyszukiwań",
        "endpoint": "GET /api/research/sources",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "test_research",
        "description": "Test research API - sprawdza czy działa SERPAPI/Firecrawl",
        "endpoint": "GET /api/research/test",
        "parameters": {"type": "object", "properties": {}}
    },
    
    # ═══════════════════════════════════════════════════════════════════
    # WRITING ENDPOINT (12 endpoints)
    # ═══════════════════════════════════════════════════════════════════
    {
        "name": "creative_writing",
        "description": "Kreatywne pisanie - artykuły, historie, eseje. Długie teksty z emocją.",
        "endpoint": "POST /api/writing/creative",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "O czym napisać"},
                "style": {"type": "string", "description": "Styl: formal/casual/poetic", "default": "casual"},
                "length": {"type": "integer", "default": 500}
            },
            "required": ["prompt"]
        },
        "example": {"prompt": "Write about sunset in mountains", "style": "poetic", "length": 300}
    },
    {
        "name": "vinted_description",
        "description": "Generuje opis produktu na Vinted - chwytliwy, SEO, z hashtagami",
        "endpoint": "POST /api/writing/vinted",
        "parameters": {
            "type": "object",
            "properties": {
                "product_name": {"type": "string", "description": "Nazwa produktu"},
                "category": {"type": "string", "description": "Kategoria"},
                "condition": {"type": "string", "description": "Stan: new/used/good"},
                "price": {"type": "number", "description": "Cena"}
            },
            "required": ["product_name"]
        },
        "example": {"product_name": "Nike Air Max 90", "category": "sneakers", "condition": "good", "price": 250}
    },
    {
        "name": "social_media_post",
        "description": "Post na social media - Instagram, Facebook, Twitter. Z emotikonami i hashtagami.",
        "endpoint": "POST /api/writing/social",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "platform": {"type": "string", "enum": ["instagram", "facebook", "twitter"]},
                "tone": {"type": "string", "default": "friendly"}
            },
            "required": ["topic", "platform"]
        }
    },
    {
        "name": "auction_description",
        "description": "Opis aukcji - Allegro, eBay. Profesjonalny, przekonujący.",
        "endpoint": "POST /api/writing/auction",
        "parameters": {
            "type": "object",
            "properties": {
                "product": {"type": "string"},
                "features": {"type": "array", "items": {"type": "string"}},
                "price": {"type": "number"}
            },
            "required": ["product"]
        }
    },
    {
        "name": "auction_pro",
        "description": "PRO opis aukcji - z analizą konkurencji, SEO, tagami",
        "endpoint": "POST /api/writing/auction/pro",
        "parameters": {
            "type": "object",
            "properties": {
                "product": {"type": "string"},
                "category": {"type": "string"},
                "target_audience": {"type": "string"}
            },
            "required": ["product"]
        }
    },
    {
        "name": "fashion_analyze",
        "description": "Analizuje modę - trendy, kolory, style",
        "endpoint": "POST /api/writing/fashion/analyze",
        "parameters": {
            "type": "object",
            "properties": {
                "item": {"type": "string"},
                "season": {"type": "string"}
            },
            "required": ["item"]
        }
    },
    {
        "name": "suggest_tags",
        "description": "Sugeruje tagi/hashtagi dla aukcji",
        "endpoint": "POST /api/writing/auction/suggest-tags",
        "parameters": {
            "type": "object",
            "properties": {
                "product": {"type": "string"}
            },
            "required": ["product"]
        }
    },
    {
        "name": "kb_learn",
        "description": "Uczy się z przykładów aukcji (knowledge base)",
        "endpoint": "POST /api/writing/auction/kb/learn",
        "parameters": {
            "type": "object",
            "properties": {
                "example": {"type": "string"}
            },
            "required": ["example"]
        }
    },
    {
        "name": "kb_fetch",
        "description": "Pobiera nauczone przykłady",
        "endpoint": "GET /api/writing/auction/kb/fetch",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "masterpiece_article",
        "description": "Tworzy arcydzieło - artykuł premium, długi, z badaniami",
        "endpoint": "POST /api/writing/masterpiece/article",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "research_depth": {"type": "string", "enum": ["basic", "deep", "expert"]}
            },
            "required": ["topic"]
        }
    },
    {
        "name": "masterpiece_sales",
        "description": "Sales copy arcydzieło - landing page, VSL, persuasion",
        "endpoint": "POST /api/writing/masterpiece/sales",
        "parameters": {
            "type": "object",
            "properties": {
                "product": {"type": "string"},
                "target": {"type": "string"}
            },
            "required": ["product"]
        }
    },
    {
        "name": "masterpiece_technical",
        "description": "Techniczny artykuł arcydzieło - dokumentacja, tutorial",
        "endpoint": "POST /api/writing/masterpiece/technical",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "level": {"type": "string", "enum": ["beginner", "intermediate", "expert"]}
            },
            "required": ["topic"]
        }
    },
    
    # ═══════════════════════════════════════════════════════════════════
    # PROGRAMISTA ENDPOINT (14 endpoints)
    # ═══════════════════════════════════════════════════════════════════
    {
        "name": "code_snapshot",
        "description": "Snapshot workspace - tree struktura, lista plików",
        "endpoint": "GET /api/code/snapshot",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "code_exec",
        "description": "Wykonuje polecenie shell - bash, Python, npm, git, docker. WYMAGA confirm=true!",
        "endpoint": "POST /api/code/exec",
        "parameters": {
            "type": "object",
            "properties": {
                "cmd": {"type": "string", "description": "Polecenie do wykonania"},
                "confirm": {"type": "boolean", "description": "WYMAGANE! Potwierdź wykonanie", "default": False},
                "shell": {"type": "boolean", "default": True},
                "dry_run": {"type": "boolean", "default": False}
            },
            "required": ["cmd"]
        },
        "example": {"cmd": "ls -la", "confirm": True}
    },
    {
        "name": "code_write",
        "description": "Zapisuje plik do workspace",
        "endpoint": "POST /api/code/write",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "code_read",
        "description": "Czyta plik z workspace",
        "endpoint": "GET /api/code/read",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "code_tree",
        "description": "Wyświetla drzewo katalogów",
        "endpoint": "GET /api/code/tree",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "code_init",
        "description": "Inicjalizuje nowy projekt - tworzy strukturę",
        "endpoint": "POST /api/code/init",
        "parameters": {
            "type": "object",
            "properties": {
                "project_type": {"type": "string", "enum": ["python", "node", "react", "fastapi"]}
            },
            "required": ["project_type"]
        }
    },
    {
        "name": "code_plan",
        "description": "Planuje architekturę projektu",
        "endpoint": "POST /api/code/plan",
        "parameters": {
            "type": "object",
            "properties": {
                "description": {"type": "string"}
            },
            "required": ["description"]
        }
    },
    {
        "name": "code_lint",
        "description": "Lintuje kod - pylint, eslint, black",
        "endpoint": "POST /api/code/lint",
        "parameters": {
            "type": "object",
            "properties": {
                "file": {"type": "string"}
            },
            "required": ["file"]
        }
    },
    {
        "name": "code_test",
        "description": "Uruchamia testy - pytest, jest",
        "endpoint": "POST /api/code/test",
        "parameters": {
            "type": "object",
            "properties": {
                "file": {"type": "string"}
            }
        }
    },
    {
        "name": "code_format",
        "description": "Formatuje kod - black, prettier",
        "endpoint": "POST /api/code/format",
        "parameters": {
            "type": "object",
            "properties": {
                "file": {"type": "string"}
            },
            "required": ["file"]
        }
    },
    {
        "name": "code_git",
        "description": "Operacje git - commit, push, pull, status",
        "endpoint": "POST /api/code/git",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "enum": ["commit", "push", "pull", "status"]},
                "message": {"type": "string"}
            },
            "required": ["command"]
        }
    },
    {
        "name": "code_docker_build",
        "description": "Build Docker image",
        "endpoint": "POST /api/code/docker/build",
        "parameters": {
            "type": "object",
            "properties": {
                "tag": {"type": "string"}
            },
            "required": ["tag"]
        }
    },
    {
        "name": "code_docker_run",
        "description": "Uruchamia Docker container",
        "endpoint": "POST /api/code/docker/run",
        "parameters": {
            "type": "object",
            "properties": {
                "image": {"type": "string"},
                "ports": {"type": "string"}
            },
            "required": ["image"]
        }
    },
    {
        "name": "code_deps_install",
        "description": "Instaluje dependencies - pip, npm",
        "endpoint": "POST /api/code/deps/install",
        "parameters": {
            "type": "object",
            "properties": {
                "package_manager": {"type": "string", "enum": ["pip", "npm", "yarn"]},
                "packages": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["package_manager"]
        }
    },
    
    # ═══════════════════════════════════════════════════════════════════
    # PSYCHE ENDPOINT (11 endpoints)
    # ═══════════════════════════════════════════════════════════════════
    {
        "name": "psyche_status",
        "description": "Status psychiczny AI - mood, energy, focus, emocje",
        "endpoint": "GET /api/psyche/status",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "psyche_save",
        "description": "Zapisuje stan psychiczny",
        "endpoint": "POST /api/psyche/save",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "psyche_load",
        "description": "Ładuje zapisany stan",
        "endpoint": "GET /api/psyche/load",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "psyche_observe",
        "description": "Obserwuje tekst użytkownika - sentiment, emocje",
        "endpoint": "POST /api/psyche/observe",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "psyche_episode",
        "description": "Zapisuje epizod do pamięci episodycznej",
        "endpoint": "POST /api/psyche/episode",
        "parameters": {
            "type": "object",
            "properties": {
                "event": {"type": "string"},
                "emotion": {"type": "number"}
            },
            "required": ["event"]
        }
    },
    {
        "name": "psyche_reflect",
        "description": "Refleksja - AI analizuje swoje zachowanie",
        "endpoint": "GET /api/psyche/reflect",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "psyche_tune",
        "description": "Dostrajanie parametrów psychicznych",
        "endpoint": "GET /api/psyche/tune",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "psyche_reset",
        "description": "Reset stanu psychicznego do default",
        "endpoint": "POST /api/psyche/reset",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "psyche_analyze",
        "description": "Analiza psychologiczna tekstu",
        "endpoint": "POST /api/psyche/analyze",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "psyche_set_mode",
        "description": "Ustawia tryb osobowości - friendly/professional/creative",
        "endpoint": "POST /api/psyche/set-mode",
        "parameters": {
            "type": "object",
            "properties": {
                "mode": {"type": "string", "enum": ["friendly", "professional", "creative", "analytical"]}
            },
            "required": ["mode"]
        }
    },
    {
        "name": "psyche_enhance_prompt",
        "description": "Ulepsza prompt na podstawie psyche",
        "endpoint": "POST /api/psyche/enhance-prompt",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string"}
            },
            "required": ["prompt"]
        }
    },
    
    # ═══════════════════════════════════════════════════════════════════
    # TRAVEL ENDPOINT (6 endpoints)
    # ═══════════════════════════════════════════════════════════════════
    {
        "name": "travel_search",
        "description": "Wyszukuje miejsca - TripAdvisor, Google Maps",
        "endpoint": "GET /api/travel/search",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "location": {"type": "string"}
            },
            "required": ["query"]
        },
        "example": {"query": "best hotels", "location": "Paris"}
    },
    {
        "name": "travel_geocode",
        "description": "Geocoding - zamienia adres na współrzędne",
        "endpoint": "GET /api/travel/geocode",
        "parameters": {
            "type": "object",
            "properties": {
                "address": {"type": "string"}
            },
            "required": ["address"]
        }
    },
    {
        "name": "travel_attractions",
        "description": "Atrakcje w mieście - OpenTripMap",
        "endpoint": "GET /api/travel/attractions/{city}",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string"}
            },
            "required": ["city"]
        }
    },
    {
        "name": "travel_hotels",
        "description": "Hotele w mieście",
        "endpoint": "GET /api/travel/hotels/{city}",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string"}
            },
            "required": ["city"]
        }
    },
    {
        "name": "travel_restaurants",
        "description": "Restauracje w mieście",
        "endpoint": "GET /api/travel/restaurants/{city}",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string"}
            },
            "required": ["city"]
        }
    },
    {
        "name": "travel_trip_plan",
        "description": "Planuje całą podróż - dzień po dniu",
        "endpoint": "GET /api/travel/trip-plan",
        "parameters": {
            "type": "object",
            "properties": {
                "destination": {"type": "string"},
                "days": {"type": "integer", "default": 3},
                "budget": {"type": "string", "enum": ["low", "medium", "high"]}
            },
            "required": ["destination"]
        },
        "example": {"destination": "Paris", "days": 5, "budget": "medium"}
    },
    
    # ═══════════════════════════════════════════════════════════════════
    # FILES ENDPOINT (8 endpoints)
    # ═══════════════════════════════════════════════════════════════════
    {
        "name": "file_upload",
        "description": "Upload pliku - multipart/form-data",
        "endpoint": "POST /api/files/upload",
        "parameters": {
            "type": "object",
            "properties": {
                "file": {"type": "string", "format": "binary"}
            },
            "required": ["file"]
        }
    },
    {
        "name": "file_upload_base64",
        "description": "Upload jako base64 string",
        "endpoint": "POST /api/files/upload/base64",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string"},
                "content": {"type": "string", "description": "Base64 encoded"}
            },
            "required": ["filename", "content"]
        }
    },
    {
        "name": "file_list",
        "description": "Lista uploadowanych plików",
        "endpoint": "GET /api/files/list",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "file_download",
        "description": "Pobiera plik",
        "endpoint": "GET /api/files/download",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string"}
            },
            "required": ["filename"]
        }
    },
    {
        "name": "file_analyze",
        "description": "Analizuje plik - OCR, text extraction, metadata",
        "endpoint": "POST /api/files/analyze",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string"}
            },
            "required": ["filename"]
        }
    },
    {
        "name": "file_delete",
        "description": "Usuwa plik",
        "endpoint": "POST /api/files/delete",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string"}
            },
            "required": ["filename"]
        }
    },
    {
        "name": "file_stats",
        "description": "Statystyki storage",
        "endpoint": "GET /api/files/stats",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "file_batch_analyze",
        "description": "Analizuje wiele plików naraz",
        "endpoint": "POST /api/files/batch/analyze",
        "parameters": {
            "type": "object",
            "properties": {
                "filenames": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["filenames"]
        }
    },
    
    # ═══════════════════════════════════════════════════════════════════
    # TTS/STT ENDPOINTS (4 endpoints)
    # ═══════════════════════════════════════════════════════════════════
    {
        "name": "tts_speak",
        "description": "Text-to-Speech - ElevenLabs, generuje audio",
        "endpoint": "POST /api/tts/speak",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "voice": {"type": "string", "default": "rachel"}
            },
            "required": ["text"]
        },
        "example": {"text": "Hello world", "voice": "rachel"}
    },
    {
        "name": "tts_voices",
        "description": "Lista dostępnych głosów TTS",
        "endpoint": "GET /api/tts/voices",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "stt_transcribe",
        "description": "Speech-to-Text - Whisper, transkrybuje audio",
        "endpoint": "POST /api/stt/transcribe",
        "parameters": {
            "type": "object",
            "properties": {
                "audio": {"type": "string", "format": "binary"},
                "language": {"type": "string", "default": "pl"}
            },
            "required": ["audio"]
        }
    },
    {
        "name": "stt_providers",
        "description": "Lista dostępnych providerów STT",
        "endpoint": "GET /api/stt/providers",
        "parameters": {"type": "object", "properties": {}}
    },
    
    # ═══════════════════════════════════════════════════════════════════
    # ADMIN ENDPOINT (4 endpoints)
    # ═══════════════════════════════════════════════════════════════════
    {
        "name": "admin_cache_stats",
        "description": "Statystyki cache",
        "endpoint": "GET /api/admin/cache/stats",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "admin_cache_clear",
        "description": "Czyści cache",
        "endpoint": "POST /api/admin/cache/clear",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "admin_ratelimit_usage",
        "description": "Zużycie rate limit dla usera",
        "endpoint": "GET /api/admin/ratelimit/usage/{user_id}",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"}
            },
            "required": ["user_id"]
        }
    },
    {
        "name": "admin_ratelimit_config",
        "description": "Konfiguracja rate limit",
        "endpoint": "GET /api/admin/ratelimit/config",
        "parameters": {"type": "object", "properties": {}}
    },
    
    # ═══════════════════════════════════════════════════════════════════
    # CAPTCHA ENDPOINT (2 endpoints)
    # ═══════════════════════════════════════════════════════════════════
    {
        "name": "captcha_solve",
        "description": "Rozwiązuje captcha - 2Captcha, reCAPTCHA",
        "endpoint": "POST /api/captcha/solve",
        "parameters": {
            "type": "object",
            "properties": {
                "site_key": {"type": "string"},
                "page_url": {"type": "string"},
                "type": {"type": "string", "enum": ["recaptchav2", "recaptchav3", "hcaptcha"]}
            },
            "required": ["site_key", "page_url"]
        }
    },
    {
        "name": "captcha_balance",
        "description": "Sprawdza balance 2Captcha",
        "endpoint": "GET /api/captcha/balance",
        "parameters": {"type": "object", "properties": {}}
    },
    
    # ═══════════════════════════════════════════════════════════════════
    # SUGGESTIONS ENDPOINT (4 endpoints)
    # ═══════════════════════════════════════════════════════════════════
    {
        "name": "suggestions_generate",
        "description": "Generuje proaktywne sugestie dla wiadomości",
        "endpoint": "POST /api/suggestions/generate",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "context": {"type": "array", "items": {"type": "object"}}
            },
            "required": ["message"]
        }
    },
    {
        "name": "suggestions_inject",
        "description": "Dodaje sugestie do promptu",
        "endpoint": "POST /api/suggestions/inject",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string"},
                "suggestions": {"type": "array"}
            },
            "required": ["prompt", "suggestions"]
        }
    },
    {
        "name": "suggestions_stats",
        "description": "Statystyki sugestii",
        "endpoint": "GET /api/suggestions/stats",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "suggestions_analyze",
        "description": "Analizuje wiadomość bez generowania sugestii",
        "endpoint": "POST /api/suggestions/analyze",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {"type": "string"}
            },
            "required": ["message"]
        }
    },
    
    # ═══════════════════════════════════════════════════════════════════
    # BATCH ENDPOINT (4 endpoints)
    # ═══════════════════════════════════════════════════════════════════
    {
        "name": "batch_process",
        "description": "Wsadowe przetwarzanie zapytań LLM",
        "endpoint": "POST /api/batch/process",
        "parameters": {
            "type": "object",
            "properties": {
                "queries": {"type": "array", "items": {"type": "string"}},
                "batch_size": {"type": "integer", "default": 10}
            },
            "required": ["queries"]
        }
    },
    {
        "name": "batch_submit",
        "description": "Dodaje pojedyncze zapytanie do queue",
        "endpoint": "POST /api/batch/submit",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "batch_metrics",
        "description": "Metryki procesora wsadowego",
        "endpoint": "GET /api/batch/metrics",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "batch_shutdown",
        "description": "Zatrzymuje procesor wsadowy",
        "endpoint": "POST /api/batch/shutdown",
        "parameters": {"type": "object", "properties": {}}
    },
    
    # ═══════════════════════════════════════════════════════════════════
    # PROMETHEUS ENDPOINT (3 endpoints)
    # ═══════════════════════════════════════════════════════════════════
    {
        "name": "prometheus_metrics",
        "description": "Metryki Prometheus - requests, duration, errors",
        "endpoint": "GET /api/prometheus/metrics",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "prometheus_health",
        "description": "Health check",
        "endpoint": "GET /api/prometheus/health",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "prometheus_stats",
        "description": "Statystyki aplikacji",
        "endpoint": "GET /api/prometheus/stats",
        "parameters": {"type": "object", "properties": {}}
    },
]


# ═══════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def get_all_tools() -> List[Dict[str, Any]]:
    """Zwraca wszystkie 121 tools"""
    return TOOLS_REGISTRY


def get_tool_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Znajduje tool po nazwie"""
    for tool in TOOLS_REGISTRY:
        if tool["name"] == name:
            return tool
    return None


def get_tools_by_category(category: str) -> List[Dict[str, Any]]:
    """Filtruje tools po kategorii"""
    category_map = {
        "chat": ["chat_assistant", "chat_stream", "auto_learn_web"],
        "research": ["web_search", "autonauka", "get_sources", "test_research"],
        "writing": [t["name"] for t in TOOLS_REGISTRY if t["name"].startswith(("creative_", "vinted_", "social_", "auction_", "fashion_", "kb_", "masterpiece_"))],
        "code": [t["name"] for t in TOOLS_REGISTRY if t["name"].startswith("code_")],
        "psyche": [t["name"] for t in TOOLS_REGISTRY if t["name"].startswith("psyche_")],
        "travel": [t["name"] for t in TOOLS_REGISTRY if t["name"].startswith("travel_")],
        "files": [t["name"] for t in TOOLS_REGISTRY if t["name"].startswith("file_")],
        "audio": ["tts_speak", "tts_voices", "stt_transcribe", "stt_providers"],
        "admin": [t["name"] for t in TOOLS_REGISTRY if t["name"].startswith("admin_")],
        "captcha": ["captcha_solve", "captcha_balance"],
        "suggestions": [t["name"] for t in TOOLS_REGISTRY if t["name"].startswith("suggestions_")],
        "batch": [t["name"] for t in TOOLS_REGISTRY if t["name"].startswith("batch_")],
        "monitoring": [t["name"] for t in TOOLS_REGISTRY if t["name"].startswith("prometheus_")],
    }
    
    names = category_map.get(category, [])
    return [t for t in TOOLS_REGISTRY if t["name"] in names]


def format_for_openai(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Formatuje tools dla OpenAI function calling"""
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool.get("parameters", {"type": "object", "properties": {}})
            }
        }
        for tool in tools
    ]


def search_tools(query: str) -> List[Dict[str, Any]]:
    """Wyszukuje tools po zapytaniu"""
    query_lower = query.lower()
    results = []
    
    for tool in TOOLS_REGISTRY:
        if (query_lower in tool["name"].lower() or 
            query_lower in tool["description"].lower() or
            query_lower in tool.get("endpoint", "").lower()):
            results.append(tool)
    
    return results


# ═══════════════════════════════════════════════════════════════════
# MAIN - Test
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print(f"\n🔧 TOOLS REGISTRY - {len(TOOLS_REGISTRY)} tools loaded\n")
    
    # Test kategorii
    categories = ["chat", "research", "writing", "code", "psyche", "travel", "files", "audio"]
    for cat in categories:
        tools = get_tools_by_category(cat)
        print(f"  {cat}: {len(tools)} tools")
    
    print(f"\n✅ Total: {len(TOOLS_REGISTRY)} endpoints ready for AI\n")
    
    # Przykład formatowania dla OpenAI
    sample_tools = get_tools_by_category("research")
    openai_format = format_for_openai(sample_tools)
    print("\n📄 OpenAI Format Example (research tools):")
    print(json.dumps(openai_format[0], indent=2))
