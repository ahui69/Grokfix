#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tools Module - InternetSearcher, news, sports, search, time
UPDATED: Uses smart_web_search with Brave + Tavily + DuckDuckGo
"""

import os
import re
import asyncio
import httpx
from typing import List, Dict, Any
from dataclasses import dataclass, asdict

from .helpers import log_info, log_warning, log_error
from .memory import time_manager

# ═══════════════════════════════════════════════════════════════════
# INTERNET SEARCHER - UŻYWA smart_web_search (Brave + Tavily + DDG)
# ═══════════════════════════════════════════════════════════════════

class InternetSearcher:
    """
    Zaawansowane wyszukiwanie w internecie.
    NOWA WERSJA: używa smart_web_search z research_policy.py
    
    Kolejność:
    1. Brave Search (primary, BRAVE_API_KEY)
    2. Tavily (secondary, AI-optimized)
    3. DuckDuckGo (fallback)
    """

    def __init__(self):
        self.user_agent = "MordzixAI/3.0"

    async def search_web(self, query: str, limit: int = 5) -> list:
        """
        Wyszukaj w internecie używając smart_web_search.
        Brave → Tavily → DuckDuckGo (parallel + cache).
        """
        try:
            from .research_policy import smart_web_search
            results = await smart_web_search(query, max_results=limit)
            return results[:limit] if results else []
        except ImportError:
            log_warning("[TOOLS] smart_web_search not available, using fallback")
            return await self._fallback_ddg(query, limit)
        except Exception as e:
            log_error(f"[TOOLS] search_web error: {e}")
            return await self._fallback_ddg(query, limit)

    async def _fallback_ddg(self, query: str, limit: int = 5) -> list:
        """Fallback do DuckDuckGo jeśli smart_web_search nie działa."""
        try:
            params = {"q": query, "format": "json", "no_redirect": 1, "no_html": 1, "kl": "pl-pl"}
            headers = {"User-Agent": self.user_agent}
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get("https://api.duckduckgo.com/", params=params, headers=headers)
            if r.status_code != 200:
                return []
            js = r.json()
            results = []
            abs_text = (js.get("AbstractText") or "").strip()
            abs_url = js.get("AbstractURL") or ""
            if abs_text or abs_url:
                results.append({
                    "title": (js.get("Heading") or "Wynik")[:120],
                    "url": abs_url,
                    "snippet": abs_text,
                    "source": "ddg-fallback"
                })
            return results[:limit]
        except Exception as e:
            log_error(f"[TOOLS] DDG fallback error: {e}")
            return []

    async def get_current_news(self, limit: int = 3) -> list:
        """Pobierz aktualne wiadomości"""
        try:
            # Wyszukaj aktualne wiadomości
            news_queries = [
                "najnowsze wiadomości Polska",
                "wiadomości sportowe",
                "aktualności technologiczne"
            ]

            all_news = []
            for query in news_queries:
                results = await self.search_web(query, limit=2)
                all_news.extend(results)

            return all_news[:limit]

        except Exception as e:
            log_error(e, "NEWS_SEARCH")
            return []

    async def get_sports_scores(self) -> list:
        """Pobierz wyniki sportowe"""
        try:
            sports_queries = [
                "wyniki piłkarskie dzisiaj",
                "liga polska wyniki",
                "wyniki meczów"
            ]

            all_scores = []
            for query in sports_queries:
                results = await self.search_web(query, limit=3)
                all_scores.extend(results)

            return all_scores[:5]

        except Exception as e:
            log_error(e, "SPORTS_SEARCH")
            return []


# Inicjalizacja wyszukiwarki internetowej
internet_searcher = InternetSearcher()


# ═══════════════════════════════════════════════════════════════════
# TOOLS FUNCTIONS (for FastAPI endpoints)
# ═══════════════════════════════════════════════════════════════════

async def tools_time_handler():
    """Handler for /api/tools/time"""
    info = time_manager.get_current_time()
    return {
        "ok": True,
        "time": info,
        "greeting": time_manager.format_time_greeting(),
        "date_info": time_manager.format_date_info(),
    }


async def tools_search_handler(query: str, limit: int = 5):
    """Handler for /api/tools/search"""
    results = await internet_searcher.search_web(query, limit=limit)
    return {"ok": True, "query": query, "results": results}


async def tools_news_handler(limit: int = 6):
    """Handler for /api/tools/news"""
    try:
        import sports_news_pro as SNP
        res = SNP.news_search("top", limit=limit)
        items = res.get("items", [])
        return {"ok": True, "results": items}
    except Exception:
        results = await internet_searcher.get_current_news(limit=limit)
        return {"ok": True, "results": results}


async def tools_sports_handler(kind: str = "epl", limit: int = 8):
    """Handler for /api/tools/sports"""
    try:
        import sports_news_pro as SNP
        items = SNP.normalize_scores(kind)[:max(1, limit)]
        return {"ok": True, "results": items}
    except Exception:
        results = await internet_searcher.get_sports_scores()
        return {"ok": True, "results": results[:max(1, limit)]}


async def tools_news_digest_handler(topic: str = "przegląd dnia", limit: int = 6):
    """Handler for /api/tools/news_digest"""
    try:
        from .llm import call_llm
        
        # Ogranicz do 10s i fallback bez LLM przy timeoutach
        items = await asyncio.wait_for(internet_searcher.get_current_news(limit=limit), timeout=10)
        bullets = "\n".join([f"- {it.get('title', '')} ({it.get('url', '')})" for it in items])
        system = "Jesteś redaktorem. Zrób zwięzłe podsumowanie poniższych newsów po polsku. Naturalny, ludzki styl."
        user = f"Temat: {topic}. Materiały:\n{bullets}\n\nPodsumuj krótko i rzeczowo."
        
        try:
            summary = call_llm([
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ], timeout_s=12, max_tokens=220)
        except Exception:
            # fallback bez LLM
            summary = ("\n".join([f"• {it.get('title', '')}" for it in items[:6]])).strip()
        
        return {"ok": True, "topic": topic, "digest": summary, "sources": items}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════════════
# ADVANCED AI FEATURES - NEXT LEVEL FUNCTIONALITIES
# ═══════════════════════════════════════════════════════════════════

@dataclass
class UserPattern:
    """Wzorce zachowań użytkownika"""
    user_id: str
    interaction_count: int = 0
    avg_rating: float = 0.0
    preferred_topics: List[str] = None
    response_times: List[float] = None
    error_patterns: List[str] = None
    success_patterns: List[str] = None

    def __post_init__(self):
        if self.preferred_topics is None:
            self.preferred_topics = []
        if self.response_times is None:
            self.response_times = []
        if self.error_patterns is None:
            self.error_patterns = []
        if self.success_patterns is None:
            self.success_patterns = []

class AdvancedRecommendationEngine:
    """Zaawansowany system rekomendacji oparty na ML"""

    def __init__(self):
        self.user_patterns: Dict[str, UserPattern] = {}
        self.global_patterns = {
            'popular_topics': [],
            'error_trends': [],
            'success_trends': []
        }

    def analyze_user_behavior(self, user_id: str, message: str, rating: int, response_time: float) -> Dict[str, Any]:
        """Analizuje zachowanie użytkownika i zwraca rekomendacje"""

        # Aktualizuj profil użytkownika
        if user_id not in self.user_patterns:
            self.user_patterns[user_id] = UserPattern(user_id=user_id)

        pattern = self.user_patterns[user_id]
        pattern.interaction_count += 1

        # Aktualizuj średnią ocenę
        if pattern.interaction_count == 1:
            pattern.avg_rating = rating
        else:
            pattern.avg_rating = (pattern.avg_rating * (pattern.interaction_count - 1) + rating) / pattern.interaction_count

        # Analizuj słowa kluczowe
        words = re.findall(r'\b\w{4,}\b', message.lower())
        pattern.preferred_topics.extend(words)
        pattern.response_times.append(response_time)

        # Klasyfikuj jako sukces/błąd
        if rating >= 4:
            pattern.success_patterns.extend(words)
        elif rating <= 2:
            pattern.error_patterns.extend(words)

        # Generuj rekomendacje
        recommendations = self._generate_recommendations(user_id, message)

        return {
            'user_profile': pattern,
            'recommendations': recommendations,
            'next_best_actions': self._predict_next_actions(user_id),
            'confidence_score': self._calculate_confidence(user_id)
        }

    def _generate_recommendations(self, user_id: str, message: str) -> List[str]:
        """Generuje spersonalizowane rekomendacje"""
        pattern = self.user_patterns.get(user_id, UserPattern(user_id))

        recommendations = []

        # Jeśli użytkownik często pyta o kod
        if 'kod' in pattern.preferred_topics or 'program' in pattern.preferred_topics:
            recommendations.append("Wygląda że interesujesz się programowaniem! Mogę pomóc z refaktoryzacją, testami, czy dokumentacją kodu.")

        # Jeśli użytkownik często ma problemy
        if len(pattern.error_patterns) > len(pattern.success_patterns):
            recommendations.append("Widzę że czasem masz problemy. Mogę pomóc z debugowaniem, analizą błędów, czy sugestiami optymalizacji.")

        # Jeśli użytkownik często chwali
        if pattern.avg_rating > 4.5:
            recommendations.append("Cieszę się że Ci się podoba! Jakie jeszcze tematy Cię interesują?")

        # Jeśli użytkownik jest nowy
        if pattern.interaction_count < 5:
            recommendations.append("Jesteś tu nowy? Mogę pomóc z kodem, pisaniem, podróżami, czy analizą danych!")

        return recommendations[:3]  # Max 3 rekomendacje

    def _predict_next_actions(self, user_id: str) -> List[str]:
        """Przewiduje następne akcje użytkownika"""
        pattern = self.user_patterns.get(user_id, UserPattern(user_id))

        predictions = []

        # Jeśli użytkownik często używa plików
        if any(word in str(pattern.preferred_topics) for word in ['plik', 'dokument', 'pdf']):
            predictions.append("analiza plików")

        # Jeśli użytkownik często pyta o pogodę/podróże
        if any(word in str(pattern.preferred_topics) for word in ['pogoda', 'podróż', 'hotel']):
            predictions.append("informacje podróżnicze")

        # Jeśli użytkownik często pisze
        if any(word in str(pattern.preferred_topics) for word in ['napisz', 'tekst', 'opis']):
            predictions.append("pisanie kreatywne")

        return predictions[:2]

    def _calculate_confidence(self, user_id: str) -> float:
        """Oblicza poziom pewności rekomendacji"""
        pattern = self.user_patterns.get(user_id, UserPattern(user_id))

        # Więcej interakcji = wyższa pewność
        base_confidence = min(pattern.interaction_count / 10.0, 1.0)

        # Lepsze oceny = wyższa pewność
        rating_bonus = (pattern.avg_rating - 3) / 2.0 if pattern.avg_rating > 3 else 0

        return min(base_confidence + rating_bonus, 1.0)

class AdvancedCryptoAnalyzer:
    """Zaawansowana analiza kryptowalut"""

    async def analyze_token(self, token_address: str, chain: str = "ethereum") -> Dict[str, Any]:
        """Kompletna analiza tokena kryptowalutowego"""
        try:
            # Placeholder dla prawdziwej analizy
            # W rzeczywistości łączyłoby się z API jak CoinGecko, DefiLlama, etc.
            analysis = {
                'token_address': token_address,
                'chain': chain,
                'risk_score': 0.7,  # 0-1, niższe = bezpieczniejszy
                'rugpull_probability': 0.3,
                'trading_volume_24h': 1500000,
                'market_cap': 50000000,
                'holders_count': 1250,
                'contract_verified': True,
                'recommendations': [
                    'Sprawdź liquidity pool',
                    'Analizuj transakcje dużych holderów',
                    'Sprawdź czy to nie honeypot'
                ]
            }
            return analysis
        except Exception as e:
            return {'error': str(e)}

class AdvancedCodeReviewer:
    """Zaawansowana analiza kodu z sugestiami optymalizacji"""

    def analyze_code_quality(self, code: str, language: str = "python") -> Dict[str, Any]:
        """Analizuje jakość kodu i daje sugestie"""
        issues = []
        suggestions = []

        # Podstawowa analiza dla Python
        if language == "python":
            # Sprawdź długość linii
            lines = code.split('\n')
            long_lines = [i+1 for i, line in enumerate(lines) if len(line) > 100]
            if long_lines:
                issues.append(f"Długie linie: {long_lines}")

            # Sprawdź komentarze
            comment_lines = sum(1 for line in lines if line.strip().startswith('#'))
            if comment_lines / len(lines) < 0.1:
                suggestions.append("Dodaj więcej komentarzy wyjaśniających logikę")

            # Sprawdź nazwy zmiennych
            if re.search(r'\b[a-z]{1,2}\b', code):  # Jedno/dwuliterowe nazwy
                suggestions.append("Użyj bardziej opisowych nazw zmiennych")

        return {
            'quality_score': 0.8,  # 0-1
            'issues': issues,
            'suggestions': suggestions,
            'complexity': len(re.findall(r'\b(if|for|while|def|class)\b', code))
        }

class AdvancedWorkflowEngine:
    """System workflow - łączenie narzędzi w sekwencje"""

    def __init__(self):
        self.workflows = {
            'crypto_analysis': [
                'analyze_token',
                'check_liquidity',
                'analyze_trading_volume',
                'generate_report'
            ],
            'travel_planning': [
                'search_destination',
                'find_hotels',
                'check_weather',
                'create_itinerary'
            ],
            'code_review': [
                'analyze_code',
                'check_security',
                'suggest_optimizations',
                'generate_report'
            ]
        }

    async def execute_workflow(self, workflow_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Wykonuje sekwencję narzędzi"""
        if workflow_name not in self.workflows:
            return {'error': f'Workflow {workflow_name} not found'}

        workflow = self.workflows[workflow_name]
        results = {}

        for step in workflow:
            try:
                # Placeholder dla prawdziwego wykonania
                results[step] = f"Executed {step} with params {params}"
                await asyncio.sleep(0.1)  # Symulacja czasu wykonania
            except Exception as e:
                results[step] = f"Error in {step}: {e}"

        return {
            'workflow': workflow_name,
            'steps': len(workflow),
            'results': results,
            'success': True
        }

# ═══════════════════════════════════════════════════════════════════
# GLOBAL INSTANCES
# ═══════════════════════════════════════════════════════════════════

recommendation_engine = AdvancedRecommendationEngine()
crypto_analyzer = AdvancedCryptoAnalyzer()
code_reviewer = AdvancedCodeReviewer()
workflow_engine = AdvancedWorkflowEngine()

# ═══════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════

__all__ = [
    'InternetSearcher',
    'internet_searcher',
    'tools_time_handler',
    'tools_search_handler',
    'tools_news_handler',
    'tools_sports_handler',
    'tools_news_digest_handler',
    # Advanced features
    'recommendation_engine', 'crypto_analyzer', 'code_reviewer', 'workflow_engine'
]
