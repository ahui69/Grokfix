#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced Proactive Suggestions System - Zaawansowany system proaktywnych sugestii

Zawiera integrację ze stanem psychologicznym AI, modelami użytkownika
i analizą kontekstu konwersacji. System przewiduje potrzeby użytkownika
i proaktywnie generuje trafne sugestie w odpowiednim momencie.
"""

import re
import json
import asyncio
import time
from typing import List, Dict, Any, Optional, Tuple, Union, Set
from collections import defaultdict, Counter, deque

# Import z core
from core.memory import ltm_search_hybrid, stm_get_context
from core.advanced_psychology import get_psyche_state, process_user_message
from core.user_model import user_model_manager
from core.helpers import log_info, log_warning, log_error
from core.semantic import embed_text, cosine_similarity
from core.config import CONTEXT_DICTIONARIES


# ═══════════════════════════════════════════════════════════════════
# ANALIZA KONTEKSTU I KONWERSACJI
# ═══════════════════════════════════════════════════════════════════

class ConversationAnalyzer:
    """Zaawansowany analizator konwersacji i kontekstu"""
    
    def __init__(self):
        """Inicjalizuje analizator"""
        # Słowniki tematów i intencji
        self.topic_keywords = self._initialize_topic_keywords()
        self.intent_patterns = self._initialize_intent_patterns()
        
        # Statystyki i pamięć
        self.recent_topics = deque(maxlen=10)  # (timestamp, topic, score)
        self.recent_intents = deque(maxlen=10)  # (timestamp, intent, confidence)
        
        # Analiza długoterminowa
        self.topic_frequency = Counter()
        self.intent_frequency = Counter()
        
        # Pamięć bieżącej sesji
        self.session_start = time.time()
        self.message_count = 0
        self.session_topics = set()
        self.session_intents = set()
        
        # Stany i flagi
        self.is_focused_conversation = True
        self.is_casual_conversation = False
        self.awaiting_response = False
        
        # Threshold do klasyfikacji
        self.topic_threshold = 0.3
        self.intent_threshold = 0.25
        
    def _initialize_topic_keywords(self) -> Dict[str, List[str]]:
        """Inicjalizuje słownik słów kluczowych dla tematów"""
        # Poszerzona lista słów kluczowych z CONTEXT_DICTIONARIES
        topics = {
            "programming": [
                "kod", "program", "funkcja", "klasa", "metoda", "zmienna", "debuguj", "kompiluj",
                "python", "javascript", "java", "c++", "rust", "go", "typescript", "react", 
                "algorytm", "framework", "biblioteka", "api", "backend", "frontend", "baza danych", 
                "sql", "nosql", "error", "bug", "błąd", "commit", "git", "github", "merge"
            ],
            "ai_ml": [
                "ai", "sztuczna inteligencja", "uczenie maszynowe", "machine learning", "deep learning",
                "neural network", "sieć neuronowa", "gpt", "llm", "embedding", "token", "fine-tuning",
                "prompt", "inference", "model", "pytorch", "tensorflow", "transformer", "chatbot",
                "klasyfikacja", "regresja", "dataset", "trenowanie", "dane", "data science", "bert"
            ],
            "travel": [
                "podróż", "hotel", "lot", "bilet", "restauracja", "turystyka", "zwiedzanie", 
                "wakacje", "urlop", "wycieczka", "miasto", "wyjazd", "rezerwacja", "atrakcje",
                "lotnisko", "bagaż", "voucher", "mapa", "paszport", "waluta", "wymiana", "wiza",
                "transport", "warszawa", "kraków", "wrocław", "gdańsk", "trip", "travel"
            ],
            "crypto_finance": [
                "bitcoin", "ethereum", "token", "crypto", "kryptowaluta", "blockchain", "defi",
                "solana", "pump", "swap", "chart", "portfel", "wallet", "giełda", "exchange",
                "inwestycja", "staking", "yield", "trading", "altcoin", "nft", "tokenizacja",
                "smart contract", "kontrakt", "rugpull", "kapitalizacja", "btc", "eth"
            ],
            "writing_content": [
                "napisz", "artykuł", "post", "blog", "esej", "opis", "ogłoszenie", "aukcja",
                "recenzja", "podsumowanie", "tekst", "headline", "tytuł", "format", "styl",
                "seo", "copywriting", "content", "treść", "publikacja", "hashtag", "social media",
                "newsletter", "mail", "email", "podpis", "nagłówek", "biografia", "portfolio"
            ],
            "creative": [
                "pomysł", "kreatywny", "oryginalny", "twórczy", "inspiracja", "design", "projekt",
                "sztuka", "grafika", "muzyka", "film", "wideo", "animacja", "logo", "branding",
                "ilustracja", "fotografia", "rysunek", "malarstwo", "obraz", "kompozycja", 
                "kreacja", "wyobraź", "namaluj", "narysuj", "zaprojektuj", "edytuj"
            ],
            "business": [
                "biznes", "firma", "spółka", "startup", "przedsiębiorstwo", "produkt", "usługa",
                "marketing", "sprzedaż", "rynek", "klient", "konkurencja", "strategia", "analiza",
                "rozwój", "wzrost", "przychód", "zysk", "rentowność", "roi", "kpi", "model biznesowy",
                "pitch", "inwestor", "finansowanie", "budżet", "koszt", "zarządzanie", "zespół"
            ],
            "personal": [
                "ja", "ty", "my", "mój", "twój", "nasz", "mnie", "tobie", "nas", "osobisty",
                "prywatny", "relacja", "związek", "rodzina", "przyjaciel", "emocje", "uczucia",
                "problem", "pomoc", "rada", "pytanie", "odpowiedź", "opinia", "feedback", "zdanie",
                "myślę", "czuję", "uważam", "wierzę", "chcę", "potrzebuję", "lubię", "podoba"
            ]
        }
        
        # Dodaj tematy z CONTEXT_DICTIONARIES
        for context_type, categories in CONTEXT_DICTIONARIES.items():
            if context_type not in topics:
                topics[context_type] = []
            for category, keywords in categories.items():
                topics[context_type].extend(keywords)
        
        return topics
    
    def _initialize_intent_patterns(self) -> Dict[str, List[str]]:
        """Inicjalizuje wzorce dla intencji"""
        return {
            "question": [
                r"^(co|jak|dlaczego|kiedy|gdzie|czy|kto)\s",
                r"\?$",
                r"powiedz mi",
                r"wyjaśnij",
                r"wytłumacz",
                r"odpowiedz",
                r"które",
                r"ile",
                r"w jaki sposób"
            ],
            "request": [
                r"^(zrób|napisz|stwórz|wygeneruj|oblicz|przeanalizuj)",
                r"proszę (o|cię|ciebie)",
                r"możesz (proszę|)",
                r"chciał(a)?bym",
                r"potrzebuję",
                r"pomóż mi",
                r"chcę (żebyś|abyś)"
            ],
            "feedback": [
                r"(świetnie|dobrze|źle|kiepsko|nie|tak|zgadzam|nie zgadzam)",
                r"to (jest|było) (świetne|dobre|złe|kiepskie|niewłaściwe)",
                r"podoba mi się",
                r"nie podoba mi się",
                r"nie rozumiem",
                r"to nie to",
                r"dokładnie",
                r"właśnie"
            ],
            "greeting": [
                r"^(cześć|hej|witaj|dzień dobry|dobry wieczór|siema|siemka|hello)",
                r"jak się masz",
                r"co słychać",
                r"miło cię (widzieć|spotkać)",
                r"^hej"
            ],
            "closing": [
                r"(do widzenia|do zobaczenia|pa pa|papa|cześć|na razie|dobranoc)",
                r"(dziękuję|dzięki) .{0,20}$",
                r"muszę (iść|kończyć|lecieć)",
                r"to wszystko",
                r"na dziś koniec"
            ],
            "follow_up": [
                r"^(a |oraz |również |ponadto |dodatkowo |jeszcze |też |także |przy okazji)",
                r"^jeszcze jedno",
                r"^co więcej",
                r"^a co (z|jeśli)",
                r"^a jak",
                r"^co jeszcze"
            ]
        }
        
    def analyze_message(self, user_id: str, message: str) -> Dict[str, Any]:
        """
        Analizuje wiadomość i kontekst
        
        Args:
            user_id: ID użytkownika
            message: Treść wiadomości
            
        Returns:
            Słownik wyników analizy
        """
        if not message.strip():
            return {
                "main_topic": None,
                "topics": [],
                "main_intent": None,
                "intents": [],
                "is_focused": self.is_focused_conversation,
                "is_casual": self.is_casual_conversation
            }
        
        # Zwiększ licznik wiadomości
        self.message_count += 1
        
        # Analizuj tematy
        topics = self._detect_topics(message)
        main_topic = None
        if topics:
            main_topic = topics[0][0]
            self.topic_frequency.update([main_topic])
            self.session_topics.add(main_topic)
            self.recent_topics.append((time.time(), main_topic, topics[0][1]))
        
        # Analizuj intencje
        intents = self._detect_intents(message)
        main_intent = None
        if intents:
            main_intent = intents[0][0]
            self.intent_frequency.update([main_intent])
            self.session_intents.add(main_intent)
            self.recent_intents.append((time.time(), main_intent, intents[0][1]))
        
        # Aktualizuj flagi
        self._update_conversation_state(message, main_topic, main_intent)
        
        # Przygotuj wynik
        result = {
            "main_topic": main_topic,
            "topics": [(t, round(s, 3)) for t, s in topics],
            "main_intent": main_intent,
            "intents": [(i, round(c, 3)) for i, c in intents],
            "is_focused": self.is_focused_conversation,
            "is_casual": self.is_casual_conversation,
            "message_count": self.message_count
        }
        
        return result
    
    def _detect_topics(self, text: str) -> List[Tuple[str, float]]:
        """
        Wykrywa tematy w tekście
        
        Args:
            text: Tekst do analizy
            
        Returns:
            Lista krotek (temat, wynik)
        """
        text_lower = text.lower()
        scores = {}
        
        # Policz występowanie słów kluczowych dla każdego tematu
        for topic, keywords in self.topic_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    # Daj wyższy wynik dla dokładnych dopasowań całych słów
                    if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', text_lower):
                        score += 1.0
                    else:
                        score += 0.5
            
            # Normalizuj wynik względem liczby słów kluczowych
            norm_score = score / max(10, len(keywords))
            if norm_score > self.topic_threshold:
                scores[topic] = norm_score
        
        # Sortuj według wyniku
        sorted_topics = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_topics
    
    def _detect_intents(self, text: str) -> List[Tuple[str, float]]:
        """
        Wykrywa intencje w tekście
        
        Args:
            text: Tekst do analizy
            
        Returns:
            Lista krotek (intencja, pewność)
        """
        text_lower = text.lower()
        confidences = {}
        
        # Sprawdź wzorce dla każdej intencji
        for intent, patterns in self.intent_patterns.items():
            confidence = 0
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    confidence += 0.3
            
            if confidence > self.intent_threshold:
                confidences[intent] = min(1.0, confidence)
        
        # Dodatkowe reguły
        # Jeśli wiadomość jest krótka i kończy się znakiem zapytania
        if len(text) < 50 and text.strip().endswith("?"):
            confidences["question"] = max(confidences.get("question", 0), 0.8)
        
        # Jeśli wiadomość zaczyna się od czasownika w trybie rozkazującym
        if re.match(r"^[A-Z].*[^?]$", text) and any(text_lower.startswith(v) for v in ["zrób", "dodaj", "znajdź", "pokaż", "oblicz"]):
            confidences["request"] = max(confidences.get("request", 0), 0.7)
        
        # Sortuj według pewności
        sorted_intents = sorted(confidences.items(), key=lambda x: x[1], reverse=True)
        return sorted_intents
    
    def _update_conversation_state(self, message: str, main_topic: Optional[str], main_intent: Optional[str]) -> None:
        """
        Aktualizuje stan konwersacji
        
        Args:
            message: Wiadomość
            main_topic: Główny temat
            main_intent: Główna intencja
        """
        # Sprawdź, czy konwersacja jest skoncentrowana
        if len(self.recent_topics) >= 3:
            topics = [t[1] for t in self.recent_topics[-3:]]
            if len(set(topics)) <= 2:  # Maks 2 różne tematy w ostatnich 3 wiadomościach
                self.is_focused_conversation = True
            else:
                self.is_focused_conversation = False
        
        # Sprawdź, czy konwersacja jest nieformalna
        if main_intent == "greeting" or main_intent == "closing":
            self.is_casual_conversation = True
        
        if len(message) < 15 or message.count(" ") < 3:
            self.is_casual_conversation = True
        
        # Jeśli temat jest biznesowy lub techniczny, to nie jest casual
        if main_topic in ["programming", "ai_ml", "business", "crypto_finance"]:
            self.is_casual_conversation = False
        
        # Jeśli temat jest osobisty, to prawdopodobnie casual
        if main_topic == "personal":
            self.is_casual_conversation = True
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """
        Zwraca podsumowanie konwersacji
        
        Returns:
            Słownik z podsumowaniem
        """
        # Najczęstszy temat
        most_common_topic = self.topic_frequency.most_common(1)
        top_topic = most_common_topic[0][0] if most_common_topic else None
        
        # Najczęstsza intencja
        most_common_intent = self.intent_frequency.most_common(1)
        top_intent = most_common_intent[0][0] if most_common_intent else None
        
        # Oblicz złożoność konwersacji (ile różnych tematów i intencji)
        topic_complexity = len(self.session_topics)
        intent_complexity = len(self.session_intents)
        
        # Czas trwania sesji
        session_duration = time.time() - self.session_start
        
        return {
            "dominant_topic": top_topic,
            "dominant_intent": top_intent,
            "topic_complexity": topic_complexity,
            "intent_complexity": intent_complexity,
            "message_count": self.message_count,
            "session_duration_seconds": int(session_duration),
            "is_focused": self.is_focused_conversation,
            "is_casual": self.is_casual_conversation
        }


# ═══════════════════════════════════════════════════════════════════
# GENERATOR SUGESTII
# ═══════════════════════════════════════════════════════════════════

class ProactiveSuggestionGenerator:
    """Generator proaktywnych sugestii bazujący na kontekście, psychice i użytkowniku"""
    
    def __init__(self):
        """Inicjalizuje generator"""
        # Komponenty
        self.conversation_analyzer = ConversationAnalyzer()
        
        # Konfiguracja
        self.suggestion_threshold = 0.6  # Próg dla wyświetlenia sugestii
        self.suggestion_cooldown = 300  # Minimalna przerwa między sugestiami (sekundy)
        self.max_suggestions = 3  # Maksymalna liczba sugestii
        
        # Pamięć sugestii
        self.recent_suggestions = deque(maxlen=20)  # (timestamp, suggestion, context)
        self.last_suggestion_time = 0
        
        # Baza wiedzy o sugestiach
        self.suggestion_templates = self._initialize_suggestion_templates()
        self.situational_triggers = self._initialize_situational_triggers()
        
        # Statystyki
        self.suggestion_stats = {
            "generated": 0,
            "by_topic": defaultdict(int),
            "by_intent": defaultdict(int)
        }
        
    def _initialize_suggestion_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        """Inicjalizuje szablony sugestii dla różnych tematów"""
        return {
            "programming": [
                {
                    "text": "💡 Mogę przeanalizować ten błąd i zaproponować rozwiązanie",
                    "conditions": {"intent": "question", "keywords": ["błąd", "error", "bug", "nie działa"]},
                    "priority": 0.9
                },
                {
                    "text": "💡 Chcesz, żebym zoptymalizował ten kod pod kątem wydajności?",
                    "conditions": {"keywords": ["kod", "funkcja", "powolny", "optymalizacja"]},
                    "priority": 0.8
                },
                {
                    "text": "💡 Mogę dodać testy jednostkowe do tego kodu",
                    "conditions": {"keywords": ["test", "testowanie", "unittest", "pytest"]},
                    "priority": 0.7
                },
                {
                    "text": "💡 Mogę zrefaktoryzować ten kod, aby był bardziej czytelny",
                    "conditions": {"keywords": ["refaktor", "czytelność", "czysty kod", "clean"]},
                    "priority": 0.7
                },
                {
                    "text": "💡 Potrzebujesz pomocy z integracją Git/GitHub?",
                    "conditions": {"keywords": ["git", "github", "commit", "merge", "branch"]},
                    "priority": 0.7
                }
            ],
            "ai_ml": [
                {
                    "text": "💡 Mogę zaprojektować prompt inżynieryjny dla tego przypadku",
                    "conditions": {"keywords": ["prompt", "gpt", "llm", "chatgpt"]},
                    "priority": 0.8
                },
                {
                    "text": "💡 Chcesz przeanalizować architekturę tego modelu AI?",
                    "conditions": {"keywords": ["model", "architektura", "neural", "sieć"]},
                    "priority": 0.7
                },
                {
                    "text": "💡 Mogę pomóc w przygotowaniu danych do treningu modelu",
                    "conditions": {"keywords": ["dane", "dataset", "trenowanie", "uczenie"]},
                    "priority": 0.7
                }
            ],
            "travel": [
                {
                    "text": "💡 Mogę znaleźć najlepsze hotele w tej lokalizacji",
                    "conditions": {"keywords": ["hotel", "nocleg", "gdzie spać"]},
                    "priority": 0.9
                },
                {
                    "text": "💡 Chcesz zobaczyć popularne restauracje w okolicy?",
                    "conditions": {"keywords": ["restauracja", "jedzenie", "gdzie zjeść", "knajpa"]},
                    "priority": 0.8
                },
                {
                    "text": "💡 Mogę zaplanować trasę zwiedzania na 1-3 dni",
                    "conditions": {"intent": "request", "keywords": ["zwiedzanie", "atrakcje", "zabytki", "plan"]},
                    "priority": 0.8
                },
                {
                    "text": "💡 Potrzebujesz sprawdzić pogodę dla tego miejsca?",
                    "conditions": {"keywords": ["pogoda", "temperatura", "klimat"]},
                    "priority": 0.7
                }
            ],
            "crypto_finance": [
                {
                    "text": "💡 Mogę przeanalizować potencjalne ryzyko tego tokena",
                    "conditions": {"keywords": ["token", "crypto", "ryzyko", "rugpull"]},
                    "priority": 0.9
                },
                {
                    "text": "💡 Chcesz porównać ten projekt z podobnymi?",
                    "conditions": {"keywords": ["projekt", "porównanie", "podobne", "alternatywa"]},
                    "priority": 0.8
                },
                {
                    "text": "💡 Mogę sprawdzić aktualne statystyki on-chain",
                    "conditions": {"keywords": ["on-chain", "statystyki", "transakcje", "wolumen"]},
                    "priority": 0.8
                }
            ],
            "writing_content": [
                {
                    "text": "💡 Mogę napisać alternatywną wersję w innym stylu",
                    "conditions": {"keywords": ["napisz", "tekst", "styl", "wersja"]},
                    "priority": 0.8
                },
                {
                    "text": "💡 Chcesz dodać angielską wersję tego tekstu?",
                    "conditions": {"keywords": ["tłumaczenie", "po angielsku", "wersja", "język"]},
                    "priority": 0.8
                },
                {
                    "text": "💡 Mogę zoptymalizować ten tekst pod kątem SEO",
                    "conditions": {"keywords": ["seo", "pozycjonowanie", "google", "keywords"]},
                    "priority": 0.7
                },
                {
                    "text": "💡 Potrzebujesz skróconej wersji tego tekstu?",
                    "conditions": {"keywords": ["skrócić", "podsumowanie", "krótszy", "streszczenie"]},
                    "priority": 0.7
                }
            ],
            "creative": [
                {
                    "text": "💡 Mogę wygenerować więcej wariantów tego pomysłu",
                    "conditions": {"keywords": ["pomysł", "wariant", "wersja", "opcja"]},
                    "priority": 0.8
                },
                {
                    "text": "💡 Chcesz, żebym rozwinął ten koncept bardziej szczegółowo?",
                    "conditions": {"keywords": ["koncept", "rozwinąć", "szczegóły", "rozwinięcie"]},
                    "priority": 0.8
                },
                {
                    "text": "💡 Mogę zaproponować kreatywne rozwiązanie tego problemu",
                    "conditions": {"keywords": ["problem", "rozwiązanie", "kreatywny", "pomysł"]},
                    "priority": 0.7
                }
            ],
            "business": [
                {
                    "text": "💡 Mogę przygotować analizę SWOT dla tego pomysłu",
                    "conditions": {"keywords": ["analiza", "swot", "biznes", "firma"]},
                    "priority": 0.8
                },
                {
                    "text": "💡 Chcesz zobaczyć przykładowy model biznesowy?",
                    "conditions": {"keywords": ["model biznesowy", "przychody", "koszty", "monetyzacja"]},
                    "priority": 0.8
                },
                {
                    "text": "💡 Mogę stworzyć szkic pitch decku dla tego pomysłu",
                    "conditions": {"keywords": ["pitch", "prezentacja", "inwestor", "startup"]},
                    "priority": 0.7
                }
            ],
            "personal": [
                {
                    "text": "💡 Jeśli potrzebujesz szczegółowej porady w tej kwestii, powiedz więcej",
                    "conditions": {"intent": "question", "keywords": ["rada", "porada", "problem", "pomóż"]},
                    "priority": 0.8
                },
                {
                    "text": "💡 Chcesz, żebym rozważył to z innej perspektywy?",
                    "conditions": {"keywords": ["perspektywa", "punkt widzenia", "inaczej", "alternatywa"]},
                    "priority": 0.8
                },
                {
                    "text": "💡 Mogę pomóc podjąć decyzję metodą za i przeciw",
                    "conditions": {"keywords": ["decyzja", "wybór", "za i przeciw", "nie wiem co"]},
                    "priority": 0.7
                }
            ],
            "general": [
                {
                    "text": "💡 Czy mogę pomóc w czymś jeszcze?",
                    "conditions": {"intent": "closing"},
                    "priority": 0.6
                },
                {
                    "text": "💡 Masz jakieś pytania dotyczące mojej odpowiedzi?",
                    "conditions": {"no_response_time": 60},
                    "priority": 0.5
                },
                {
                    "text": "💡 Może cię zainteresować powiązany temat...",
                    "conditions": {"contextual_memory_available": True},
                    "priority": 0.7
                }
            ]
        }
        
    def _initialize_situational_triggers(self) -> List[Dict[str, Any]]:
        """Inicjalizuje wyzwalacze sytuacyjne dla sugestii"""
        return [
            {
                "name": "long_conversation",
                "conditions": {"message_count": 20},
                "suggestion": "💡 Długa rozmowa! Mogę zrobić podsumowanie kluczowych punktów.",
                "priority": 0.7
            },
            {
                "name": "repeated_question",
                "conditions": {"repeated_intent": "question", "count": 3},
                "suggestion": "💡 Widzę, że masz wiele pytań. Może pomogę ci znaleźć bardziej kompleksowe źródło informacji?",
                "priority": 0.7
            },
            {
                "name": "frustrated_user",
                "conditions": {"emotional_valence": "<0.3", "messages": 3},
                "suggestion": "💡 Wygląda na to, że mogę lepiej pomóc. Może spróbujmy innego podejścia?",
                "priority": 0.9
            },
            {
                "name": "technical_to_casual",
                "conditions": {"topic_shift": ["programming", "personal"]},
                "suggestion": "💡 Chcesz na chwilę odejść od tematów technicznych? Jestem otwarty na rozmowę o wszystkim.",
                "priority": 0.7
            },
            {
                "name": "research_opportunity",
                "conditions": {"intent": "question", "no_ltm_match": True},
                "suggestion": "💡 To interesujące pytanie! Chcesz, żebym poszukał więcej informacji na ten temat?",
                "priority": 0.8
            }
        ]
    
    async def generate_suggestions(
        self, 
        user_id: str, 
        message: str, 
        conversation_history: List[Dict[str, Any]],
        last_ai_response: str = "",
        force_suggestion: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Generuje proaktywne sugestie na podstawie kontekstu, stanu psychicznego i historii
        
        Args:
            user_id: ID użytkownika
            message: Wiadomość użytkownika
            conversation_history: Historia konwersacji
            last_ai_response: Ostatnia odpowiedź AI
            force_suggestion: Wymuś sugestię nawet jeśli cooldown nie minął
            
        Returns:
            Lista sugestii w formacie [{text, score, context}]
        """
        # Sprawdź cooldown
        current_time = time.time()
        if not force_suggestion and (current_time - self.last_suggestion_time) < self.suggestion_cooldown:
            return []
        
        # Analizuj wiadomość
        analysis = self.conversation_analyzer.analyze_message(user_id, message)
        main_topic = analysis.get("main_topic")
        main_intent = analysis.get("main_intent")
        
        # Pobierz stan psychiczny
        psyche_state = get_psyche_state()
        
        # Analizuj emocjonalnie wiadomość użytkownika
        emotional_analysis = process_user_message(message, user_id)
        
        # Wybierz odpowiednie szablony na podstawie tematu i intencji
        candidate_suggestions = []
        
        # 1. Szablony z głównego tematu
        if main_topic and main_topic in self.suggestion_templates:
            topic_templates = self.suggestion_templates[main_topic]
            candidate_suggestions.extend(self._evaluate_templates(
                topic_templates, 
                message, 
                main_intent,
                emotional_analysis
            ))
        
        # 2. Zawsze sprawdź szablony ogólne
        general_templates = self.suggestion_templates.get("general", [])
        candidate_suggestions.extend(self._evaluate_templates(
            general_templates, 
            message, 
            main_intent,
            emotional_analysis
        ))
        
        # 3. Sprawdź wyzwalacze sytuacyjne
        situational_suggestions = self._check_situational_triggers(
            user_id, message, conversation_history, 
            analysis, psyche_state, emotional_analysis
        )
        candidate_suggestions.extend(situational_suggestions)
        
        # 4. Sprawdź pamięć LTM dla kontekstowych sugestii
        contextual_suggestions = await self._generate_contextual_suggestions(
            user_id, message, main_topic
        )
        candidate_suggestions.extend(contextual_suggestions)
        
        # Usuń duplikaty i sortuj według score
        unique_suggestions = {}
        for sugg in candidate_suggestions:
            if sugg["text"] not in unique_suggestions or unique_suggestions[sugg["text"]]["score"] < sugg["score"]:
                unique_suggestions[sugg["text"]] = sugg
        
        # Sortuj według score
        sorted_suggestions = sorted(unique_suggestions.values(), key=lambda x: x["score"], reverse=True)
        
        # Filtruj sugestie, które niedawno były pokazywane
        recent_texts = [s[1] for s in self.recent_suggestions]
        filtered_suggestions = [
            s for s in sorted_suggestions 
            if s["text"] not in recent_texts or force_suggestion
        ]
        
        # Jeśli znaleziono sugestie, zaktualizuj czas ostatniej sugestii
        if filtered_suggestions:
            self.last_suggestion_time = current_time
            
            # Zapisz sugestie do historii
            for sugg in filtered_suggestions[:self.max_suggestions]:
                self.recent_suggestions.append((current_time, sugg["text"], sugg["context"]))
                self.suggestion_stats["generated"] += 1
                if main_topic:
                    self.suggestion_stats["by_topic"][main_topic] += 1
                if main_intent:
                    self.suggestion_stats["by_intent"][main_intent] += 1
        
        return filtered_suggestions[:self.max_suggestions]
    
    def _evaluate_templates(
        self, 
        templates: List[Dict[str, Any]], 
        message: str, 
        intent: Optional[str],
        emotional_analysis: Dict[str, Any]
    ) -> List[Dict[str, float]]:
        """
        Ocenia szablony sugestii pod kątem dopasowania
        
        Args:
            templates: Lista szablonów
            message: Wiadomość użytkownika
            intent: Intencja użytkownika
            emotional_analysis: Analiza emocjonalna
        
        Returns:
            Lista pasujących sugestii z wynikami
        """
        message_lower = message.lower()
        matching_suggestions = []
        
        for template in templates:
            score = template.get("priority", 0.5)
            conditions = template.get("conditions", {})
            
            # Sprawdź warunki
            # 1. Zgodność intencji
            if "intent" in conditions and conditions["intent"] != intent:
                continue
            
            # 2. Obecność słów kluczowych
            if "keywords" in conditions:
                keywords_found = sum(1 for kw in conditions["keywords"] if kw.lower() in message_lower)
                if keywords_found == 0:
                    continue
                score += 0.1 * min(keywords_found, 3)  # Max +0.3 za słowa kluczowe
            
            # 3. Dostosowanie emocjonalne
            if emotional_analysis and "valence" in emotional_analysis:
                if emotional_analysis["valence"] < 0 and "negative_emotion" in conditions:
                    score += 0.2
                elif emotional_analysis["valence"] > 0 and "positive_emotion" in conditions:
                    score += 0.2
            
            # Jeśli przeszedł warunki, dodaj do pasujących
            if score >= self.suggestion_threshold:
                matching_suggestions.append({
                    "text": template["text"],
                    "score": score,
                    "context": {
                        "template_type": "standard",
                        "conditions_met": list(conditions.keys())
                    }
                })
        
        return matching_suggestions
    
    def _check_situational_triggers(
        self,
        user_id: str,
        message: str,
        conversation_history: List[Dict[str, Any]],
        analysis: Dict[str, Any],
        psyche_state: Dict[str, Any],
        emotional_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Sprawdza wyzwalacze sytuacyjne
        
        Args:
            user_id: ID użytkownika
            message: Wiadomość użytkownika
            conversation_history: Historia konwersacji
            analysis: Analiza bieżącej wiadomości
            psyche_state: Stan psychiczny AI
            emotional_analysis: Analiza emocjonalna
            
        Returns:
            Lista sugestii sytuacyjnych
        """
        triggered_suggestions = []
        
        # Sprawdź każdy wyzwalacz
        for trigger in self.situational_triggers:
            trigger_conditions = trigger.get("conditions", {})
            trigger_score = trigger.get("priority", 0.5)
            conditions_met = True
            
            # Sprawdź warunki
            for cond_name, cond_value in trigger_conditions.items():
                # Liczba wiadomości
                if cond_name == "message_count":
                    if analysis.get("message_count", 0) < cond_value:
                        conditions_met = False
                        break
                
                # Powtarzająca się intencja
                if cond_name == "repeated_intent":
                    intent_value = trigger_conditions.get("repeated_intent")
                    count_value = trigger_conditions.get("count", 2)
                    
                    intent_count = sum(1 for msg in conversation_history[-5:] 
                                     if msg.get("role") == "user" and "intent" in msg and msg["intent"] == intent_value)
                    
                    if intent_count < count_value:
                        conditions_met = False
                        break
                
                # Stan emocjonalny
                if cond_name == "emotional_valence":
                    if "<" in cond_value:
                        threshold = float(cond_value.replace("<", ""))
                        if not emotional_analysis or emotional_analysis.get("valence", 0.5) >= threshold:
                            conditions_met = False
                            break
                    elif ">" in cond_value:
                        threshold = float(cond_value.replace(">", ""))
                        if not emotional_analysis or emotional_analysis.get("valence", 0.5) <= threshold:
                            conditions_met = False
                            break
                
                # Zmiana tematu
                if cond_name == "topic_shift":
                    from_topic, to_topic = cond_value
                    if len(conversation_history) < 3:
                        conditions_met = False
                        break
                    
                    previous_topics = [msg.get("topic") for msg in conversation_history[-3:] 
                                     if msg.get("role") == "user" and "topic" in msg]
                    
                    if from_topic not in previous_topics or analysis.get("main_topic") != to_topic:
                        conditions_met = False
                        break
                
                # Brak dopasowań LTM
                if cond_name == "no_ltm_match" and cond_value is True:
                    # To będzie sprawdzane w osobnej funkcji _generate_contextual_suggestions
                    pass
            
            # Jeśli wszystkie warunki spełnione, dodaj sugestię
            if conditions_met:
                triggered_suggestions.append({
                    "text": trigger["suggestion"],
                    "score": trigger_score,
                    "context": {
                        "template_type": "situational",
                        "trigger_name": trigger["name"]
                    }
                })
        
        return triggered_suggestions
    
    async def _generate_contextual_suggestions(
        self,
        user_id: str,
        message: str,
        topic: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        Generuje sugestie na podstawie kontekstu i pamięci LTM
        
        Args:
            user_id: ID użytkownika
            message: Wiadomość użytkownika
            topic: Główny temat
            
        Returns:
            Lista sugestii kontekstowych
        """
        # Pobierz powiązane fakty z LTM
        ltm_results = await asyncio.to_thread(ltm_search_hybrid, message, limit=3)
        
        # Jeśli nie znaleziono powiązanych faktów, zaproponuj naukę
        if not ltm_results:
            if any(q in message.lower() for q in ["co to", "czym jest", "jak działa", "wyjaśnij"]):
                return [{
                    "text": "💡 Mogę poszukać więcej informacji na ten temat w internecie",
                    "score": 0.85,
                    "context": {
                        "template_type": "contextual",
                        "trigger": "no_ltm_match"
                    }
                }]
            return []
        
        # Jeśli znaleziono powiązane fakty, zaproponuj głębsze wejście w temat
        if len(ltm_results) >= 2:
            related_text = ltm_results[1].get("text", "")
            if len(related_text) > 20:
                # Wydobądź temat z powiązanego faktu
                related_topic = self._extract_topic_from_text(related_text)
                if related_topic and related_topic != topic:
                    return [{
                        "text": f"💡 Może zainteresuje cię też powiązany temat: {related_topic}",
                        "score": 0.75,
                        "context": {
                            "template_type": "contextual",
                            "trigger": "related_topic"
                        }
                    }]
        
        return []
    
    def _extract_topic_from_text(self, text: str) -> Optional[str]:
        """
        Wydobywa temat z tekstu
        
        Args:
            text: Tekst do analizy
            
        Returns:
            Wydobyty temat lub None
        """
        # Proste podejście - poszukaj rzeczowników na początku tekstu
        first_sentence = text.split(".")[0].strip()
        
        # Poszukaj pierwszego istotnego rzeczownika
        important_nouns = ["technologia", "metoda", "system", "framework", "język", "algorytm", 
                          "platforma", "protokół", "narzędzie", "biblioteka", "koncept", "teoria"]
        
        for noun in important_nouns:
            if noun in first_sentence.lower():
                # Zwróć fragment tekstu zawierający ten rzeczownik
                start_idx = first_sentence.lower().find(noun)
                end_idx = start_idx + 30
                fragment = first_sentence[start_idx:min(end_idx, len(first_sentence))]
                # Jeśli fragment kończy się w środku zdania, znajdź ostatni koniec słowa
                if end_idx < len(first_sentence):
                    last_space = fragment.rfind(" ")
                    if last_space > 0:
                        fragment = fragment[:last_space]
                return fragment
        
        # Jeśli nie znaleziono konkretnego rzeczownika, zwróć pierwsze 3-5 słów
        words = first_sentence.split()
        if len(words) >= 3:
            return " ".join(words[:min(5, len(words))])
        
        return None
    
    def inject_suggestion_to_prompt(self, base_prompt: str, suggestions: List[Dict[str, Any]]) -> str:
        """
        Dodaje sugestie do promptu systemowego
        
        Args:
            base_prompt: Bazowy prompt systemowy
            suggestions: Lista sugestii
            
        Returns:
            Prompt z dodanymi sugestiami
        """
        if not suggestions:
            return base_prompt
        
        # Wybierz najlepszą sugestię
        best_suggestion = suggestions[0]["text"]
        
        enhanced_prompt = f"""{base_prompt}

🎯 PROAKTYWNA POMOC:
Na końcu odpowiedzi (po pustej linii) dodaj tę sugestię:
{best_suggestion}

Format: naturalny, konwersacyjny, jakbyś z własnej inicjatywy chciał pomóc."""
        
        return enhanced_prompt
    
    def get_suggestion_stats(self) -> Dict[str, Any]:
        """
        Zwraca statystyki sugestii
        
        Returns:
            Słownik statystyk sugestii
        """
        return {
            "total_generated": self.suggestion_stats["generated"],
            "by_topic": dict(self.suggestion_stats["by_topic"]),
            "by_intent": dict(self.suggestion_stats["by_intent"]),
            "recent_suggestions": list(self.recent_suggestions)
        }


# ═══════════════════════════════════════════════════════════════════
# INTERFEJS PUBLICZNY
# ═══════════════════════════════════════════════════════════════════

# Globalna instancja generatora sugestii
suggestion_generator = ProactiveSuggestionGenerator()

async def get_proactive_suggestions(
    user_id: str, 
    message: str, 
    conversation_history: List[Dict[str, Any]] = None,
    last_ai_response: str = "",
    force: bool = False
) -> List[Dict[str, Any]]:
    """
    Główna funkcja do generowania proaktywnych sugestii
    
    Args:
        user_id: ID użytkownika
        message: Wiadomość użytkownika
        conversation_history: Historia konwersacji (opcjonalna)
        last_ai_response: Ostatnia odpowiedź AI
        force: Wymuś sugestię nawet jeśli cooldown nie minął
        
    Returns:
        Lista sugestii w formacie [{text, score, context}]
    """
    if conversation_history is None:
        conversation_history = []
    
    suggestions = await suggestion_generator.generate_suggestions(
        user_id=user_id,
        message=message,
        conversation_history=conversation_history,
        last_ai_response=last_ai_response,
        force_suggestion=force
    )
    
    return suggestions

def inject_suggestions_to_prompt(base_prompt: str, suggestions: List[Dict[str, Any]]) -> str:
    """
    Dodaje sugestie do promptu systemowego
    
    Args:
        base_prompt: Bazowy prompt systemowy
        suggestions: Lista sugestii z get_proactive_suggestions()
        
    Returns:
        Prompt z dodanymi sugestiami
    """
    return suggestion_generator.inject_suggestion_to_prompt(base_prompt, suggestions)

def get_smart_suggestions(user_message: str, last_ai_response: str = "") -> List[str]:
    """
    Legacy funkcja - zwraca listę prostych sugestii (kompatybilność wsteczna)
    
    Args:
        user_message: Wiadomość użytkownika
        last_ai_response: Ostatnia odpowiedź AI
        
    Returns:
        Lista prostych tekstów sugestii
    """
    msg_lower = user_message.lower()
    suggestions = []
    
    # Kod/programowanie
    if '```' in last_ai_response or 'def ' in last_ai_response:
        suggestions.extend([
            "Uruchom ten kod",
            "Wyjaśnij krok po kroku",
            "Dodaj testy"
        ])
    
    # Post/aukcja
    elif len(last_ai_response) > 300 and any(w in msg_lower for w in ['napisz', 'opis', 'post']):
        suggestions.extend([
            "Skróć do 150 słów",
            "Zrób wersję angielską",
            "Dodaj hashtagi"
        ])
    
    # Token/krypto
    elif any(w in msg_lower for w in ['token', 'coin', 'crypto']):
        suggestions.extend([
            "Sprawdź aktualną cenę",
            "Analiza rugpull risk",
            "Pokaż podobne tokeny"
        ])
    
    # Lokalizacja/travel
    elif any(w in msg_lower for w in ['hotel', 'restauracj', 'miasto']):
        suggestions.extend([
            "Pokaż na mapie",
            "Sprawdź opinie",
            "Znajdź podobne"
        ])
    
    # Domyślne
    if not suggestions:
        suggestions = [
            "Powiedz więcej",
            "Podaj przykład", 
            "Alternatywne rozwiązanie"
        ]
    
    return suggestions[:3]  # Max 3 sugestie

def analyze_context(user_message: str, conversation_history: List[Dict] = None) -> Optional[str]:
    """
    Legacy funkcja - analizuje kontekst (kompatybilność wsteczna)
    
    Args:
        user_message: Wiadomość użytkownika
        conversation_history: Historia konwersacji
        
    Returns:
        Sugestia lub None
    """
    msg_lower = user_message.lower()
    
    # Kod/programowanie
    if any(w in msg_lower for w in ['error', 'błąd', 'bug', 'nie działa', 'crashuje', 'traceback']):
        return "💡 Widzę że masz problem z kodem. Mogę przeanalizować błąd, zaproponować fix lub uruchomić debugger."
    
    if any(w in msg_lower for w in ['kod', 'funkcj', 'class', 'def ', 'import ', 'git ']):
        return "💡 Piszesz kod? Mogę ci pomóc z refaktoringiem, testami, dokumentacją lub code review."
    
    # Travel/lokalizacja
    if any(w in msg_lower for w in ['hotel', 'restauracj', 'lot', 'bilet', 'podróż', 'warszaw', 'krakó', 'wrocław']):
        return "💡 Planujesz podróż? Mogę znaleźć najlepsze hotele, restauracje, atrakcje i sprawdzić pogodę."
    
    # Brak konkretnego kontekstu
    if len(user_message) < 10:
        return "💡 Jestem gotowy! Mogę pomóc z kodem, pisaniem, travel, krypto, research - pytaj śmiało."
    
    return None