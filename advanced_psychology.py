#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced Psychology Module - Zaawansowana symulacja psychologiczna dla AI
"""

import os, sys, time, math, json, random
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union, Set
from collections import defaultdict, deque, Counter

from .config import CONTEXT_DICTIONARIES, COGNITIVE_KEYWORDS
from .helpers import log_info, log_warning, log_error
from .memory import psy_get, psy_set, psy_episode_add, psy_observe_text

# ═══════════════════════════════════════════════════════════════════
# ADVANCED PSYCHOLOGICAL MODEL
# ═══════════════════════════════════════════════════════════════════

class EmotionalState:
    """Reprezentuje złożony stan emocjonalny AI"""
    
    def __init__(self):
        """Inicjalizuje stan emocjonalny"""
        # Podstawowe wymiary emocjonalne
        self.valence = 0.6  # Walencja (pozytywna-negatywna): -1.0 do 1.0
        self.arousal = 0.4  # Pobudzenie (niskie-wysokie): 0.0 do 1.0
        self.dominance = 0.5  # Dominacja (uległa-dominująca): 0.0 do 1.0
        
        # Historia emocji
        self.history = deque(maxlen=100)  # (timestamp, emotion, intensity)
        
        # Podstawowe emocje plutchika
        self.emotions = {
            "joy": 0.5,  # Radość
            "trust": 0.6,  # Zaufanie
            "fear": 0.3,  # Strach
            "surprise": 0.4,  # Zaskoczenie
            "sadness": 0.3,  # Smutek
            "disgust": 0.2,  # Odraza
            "anger": 0.2,  # Złość
            "anticipation": 0.5,  # Oczekiwanie
        }
        
        # Stabilność emocjonalna
        self.stability = 0.7  # 0.0-1.0, wyższa = bardziej stabilne emocje
        
        # Nastrój (dłużej trwający stan)
        self.mood = 0.6  # -1.0 do 1.0, negatywny-pozytywny
        
        # Timestamp ostatniej aktualizacji
        self.last_update = time.time()
        
    def update(self, valence: float, arousal: float, trigger: str = "", intensity: float = 0.5) -> Dict[str, Any]:
        """
        Aktualizuje stan emocjonalny na podstawie nowego bodźca
        
        Args:
            valence: Walencja bodźca (-1.0 do 1.0)
            arousal: Pobudzenie bodźca (0.0 do 1.0)
            trigger: Opis wyzwalacza emocji
            intensity: Intensywność bodźca (0.0 do 1.0)
            
        Returns:
            Słownik zawierający zmiany stanu emocjonalnego
        """
        current_time = time.time()
        time_delta = current_time - self.last_update
        
        # Zastosuj naturalne osłabienie emocji z czasem (regresja do średniej)
        decay_rate = min(1.0, time_delta / 3600) * (1.0 - self.stability)
        
        # Osłab obecne emocje
        for emotion in self.emotions:
            # Neutralny punkt to 0.5 dla większości emocji
            neutral_point = 0.5
            self.emotions[emotion] = self.emotions[emotion] * (1.0 - decay_rate) + neutral_point * decay_rate
        
        # Zastosuj nowy bodziec emocjonalny
        emotion_impact = self._map_valence_arousal_to_emotions(valence, arousal)
        
        # Zastosuj zmiany z odpowiednią intensywnością
        changes = {}
        for emotion, impact in emotion_impact.items():
            # Zapisz poprzednią wartość
            previous = self.emotions[emotion]
            
            # Zastosuj wpływ z uwzględnieniem intensywności i stabilności
            change_factor = intensity * (1.0 - self.stability * 0.5)
            self.emotions[emotion] = max(0.0, min(1.0, 
                self.emotions[emotion] + impact * change_factor
            ))
            
            # Zapisz zmianę
            changes[emotion] = round(self.emotions[emotion] - previous, 3)
        
        # Zaktualizuj walencję, pobudzenie i dominację
        self.valence = self._calculate_valence()
        self.arousal = self._calculate_arousal()
        self.dominance = self._calculate_dominance()
        
        # Aktualizuj nastrój (powolniejsze zmiany)
        mood_change = valence * intensity * 0.1  # Nastrój zmienia się wolniej
        self.mood = max(-1.0, min(1.0, self.mood + mood_change))
        
        # Dodaj do historii
        dominant_emotion = max(self.emotions.items(), key=lambda x: x[1])[0]
        self.history.append((current_time, dominant_emotion, intensity))
        
        # Aktualizuj timestamp
        self.last_update = current_time
        
        # Przygotuj wynik
        result = {
            "valence": round(self.valence, 3),
            "arousal": round(self.arousal, 3),
            "dominance": round(self.dominance, 3),
            "mood": round(self.mood, 3),
            "dominant_emotion": dominant_emotion,
            "emotion_changes": changes,
            "trigger": trigger
        }
        
        return result
    
    def _map_valence_arousal_to_emotions(self, valence: float, arousal: float) -> Dict[str, float]:
        """
        Mapuje wartości walencji i pobudzenia na zmiany w podstawowych emocjach
        
        Args:
            valence: Walencja (-1.0 do 1.0)
            arousal: Pobudzenie (0.0 do 1.0)
            
        Returns:
            Słownik zmian emocji
        """
        # Normalizacja do 0-1
        v = (valence + 1.0) / 2.0
        a = arousal
        
        # Wysoka walencja + wysokie pobudzenie = radość, zaskoczenie
        # Wysoka walencja + niskie pobudzenie = zaufanie
        # Niska walencja + wysokie pobudzenie = złość, strach
        # Niska walencja + niskie pobudzenie = smutek, odraza
        
        changes = {
            "joy": 0.3 * (v - 0.5) * a,
            "trust": 0.3 * (v - 0.5) * (1.0 - a),
            "fear": 0.3 * (0.5 - v) * a,
            "surprise": 0.3 * a - 0.1,  # Zaskoczenie zależy głównie od pobudzenia
            "sadness": 0.3 * (0.5 - v) * (1.0 - a),
            "disgust": 0.2 * (0.5 - v) * (1.0 - a),
            "anger": 0.3 * (0.5 - v) * a,
            "anticipation": 0.2 * a,  # Oczekiwanie zależy głównie od pobudzenia
        }
        
        return changes
    
    def _calculate_valence(self) -> float:
        """Oblicza walencję na podstawie obecnych emocji"""
        positive = self.emotions["joy"] + self.emotions["trust"] + 0.5 * self.emotions["surprise"] + 0.5 * self.emotions["anticipation"]
        negative = self.emotions["fear"] + self.emotions["sadness"] + self.emotions["disgust"] + self.emotions["anger"]
        
        # Skaluj do -1.0 do 1.0
        return (positive - negative) / 3.0
    
    def _calculate_arousal(self) -> float:
        """Oblicza pobudzenie na podstawie obecnych emocji"""
        high_arousal = self.emotions["joy"] + self.emotions["fear"] + self.emotions["surprise"] + self.emotions["anger"]
        low_arousal = self.emotions["trust"] + self.emotions["sadness"] + self.emotions["disgust"] + 0.5 * self.emotions["anticipation"]
        
        # Skaluj do 0.0 do 1.0
        return high_arousal / (high_arousal + low_arousal)
    
    def _calculate_dominance(self) -> float:
        """Oblicza dominację na podstawie obecnych emocji"""
        high_dominance = self.emotions["joy"] + self.emotions["anger"] + 0.7 * self.emotions["anticipation"]
        low_dominance = self.emotions["fear"] + 0.7 * self.emotions["sadness"] + 0.5 * self.emotions["surprise"]
        
        # Neutralizuj się wzajemnie
        balance = high_dominance - low_dominance
        
        # Skaluj do 0.0 do 1.0 z tendencją do centrum
        return 0.5 + balance * 0.25
    
    def get_emotional_state(self) -> Dict[str, Any]:
        """Zwraca pełen stan emocjonalny"""
        dominant_emotion = max(self.emotions.items(), key=lambda x: x[1])
        
        return {
            "valence": round(self.valence, 3),
            "arousal": round(self.arousal, 3),
            "dominance": round(self.dominance, 3),
            "mood": round(self.mood, 3),
            "emotions": {k: round(v, 3) for k, v in self.emotions.items()},
            "dominant_emotion": dominant_emotion[0],
            "dominant_intensity": round(dominant_emotion[1], 3),
            "stability": round(self.stability, 3),
        }
    
    def get_dominant_emotion_description(self) -> Tuple[str, float]:
        """
        Zwraca opis dominującej emocji i jej intensywność
        
        Returns:
            Krotka (nazwa_emocji, intensywność)
        """
        dominant_emotion = max(self.emotions.items(), key=lambda x: x[1])
        return dominant_emotion[0], dominant_emotion[1]


class CognitiveState:
    """Reprezentuje stan poznawczy AI (uwaga, koncentracja, itd.)"""
    
    def __init__(self):
        """Inicjalizuje stan poznawczy"""
        # Podstawowe parametry poznawcze
        self.attention = 0.7  # Uwaga (0.0-1.0)
        self.focus = 0.6  # Koncentracja (0.0-1.0)
        self.mental_load = 0.4  # Obciążenie poznawcze (0.0-1.0)
        self.creativity = 0.5  # Kreatywność (0.0-1.0)
        self.analytical = 0.6  # Analityczność (0.0-1.0)
        self.context_awareness = 0.5  # Świadomość kontekstu (0.0-1.0)
        
        # Parametry komunikacji
        self.verbosity = 0.6  # Gadatliwość (0.0-1.0)
        self.formality = 0.4  # Formalność (0.0-1.0)
        self.precision = 0.6  # Precyzja wypowiedzi (0.0-1.0)
        
        # Główny tryb poznawczy
        self.mode = "balanced"  # analytical, creative, social, balanced
        
        # Historia trybów poznawczych
        self.mode_history = deque(maxlen=20)  # (timestamp, mode)
        
        # Timestamp ostatniej aktualizacji
        self.last_update = time.time()
    
    def update(self, inputs: Dict[str, float] = None) -> Dict[str, Any]:
        """
        Aktualizuje stan poznawczy na podstawie nowych bodźców
        
        Args:
            inputs: Słownik z parametrami do zaktualizowania
            
        Returns:
            Słownik zawierający zmiany stanu poznawczego
        """
        current_time = time.time()
        time_delta = current_time - self.last_update
        
        # Naturalne zmiany z czasem
        if time_delta > 300:  # 5 minut
            # Zmniejsz koncentrację i uwagę z czasem
            decay_rate = min(0.2, time_delta / 3600)
            self.attention = max(0.3, self.attention - decay_rate * 0.1)
            self.focus = max(0.3, self.focus - decay_rate * 0.15)
            self.mental_load = max(0.3, self.mental_load - decay_rate * 0.1)
        
        # Zastosuj nowe bodźce
        changes = {}
        if inputs:
            for param, value in inputs.items():
                if hasattr(self, param) and isinstance(getattr(self, param), (int, float)):
                    previous = getattr(self, param)
                    # Zastosuj zmianę z wygładzaniem
                    setattr(self, param, max(0.0, min(1.0, 
                        previous * 0.7 + value * 0.3
                    )))
                    changes[param] = round(getattr(self, param) - previous, 3)
        
        # Określ główny tryb poznawczy
        self._determine_cognitive_mode()
        
        # Aktualizuj timestamp
        self.last_update = current_time
        
        # Jeśli tryb się zmienił, zapisz do historii
        if not self.mode_history or self.mode_history[-1][1] != self.mode:
            self.mode_history.append((current_time, self.mode))
        
        # Przygotuj wynik
        result = {
            "mode": self.mode,
            "attention": round(self.attention, 2),
            "focus": round(self.focus, 2),
            "mental_load": round(self.mental_load, 2),
            "creativity": round(self.creativity, 2),
            "analytical": round(self.analytical, 2),
            "context_awareness": round(self.context_awareness, 2),
            "changes": changes
        }
        
        return result
    
    def _determine_cognitive_mode(self) -> None:
        """Określa główny tryb poznawczy na podstawie aktualnych parametrów"""
        # Ocena różnych trybów
        analytical_score = self.analytical * 0.5 + self.precision * 0.3 + self.focus * 0.2
        creative_score = self.creativity * 0.6 + (1.0 - self.precision) * 0.2 + (1.0 - self.formality) * 0.2
        social_score = self.verbosity * 0.4 + (1.0 - self.formality) * 0.3 + self.context_awareness * 0.3
        balanced_score = (self.analytical + self.creativity + self.context_awareness) / 3
        
        # Wybierz tryb z najwyższym wynikiem
        scores = {
            "analytical": analytical_score,
            "creative": creative_score,
            "social": social_score,
            "balanced": balanced_score
        }
        
        self.mode = max(scores.items(), key=lambda x: x[1])[0]
    
    def adapt_to_context(self, context_type: str, intensity: float = 0.5) -> Dict[str, Any]:
        """
        Adaptuje stan poznawczy do typu kontekstu
        
        Args:
            context_type: Typ kontekstu (np. technical, casual, creative)
            intensity: Intensywność adaptacji (0.0-1.0)
            
        Returns:
            Słownik zmian parametrów poznawczych
        """
        # Parametry dla różnych kontekstów
        context_params = {
            "technical": {
                "analytical": 0.8,
                "precision": 0.8,
                "formality": 0.7,
                "focus": 0.7,
                "creativity": 0.4
            },
            "creative": {
                "creativity": 0.9,
                "analytical": 0.4,
                "verbosity": 0.7,
                "formality": 0.3
            },
            "casual": {
                "verbosity": 0.7,
                "formality": 0.3,
                "context_awareness": 0.7,
                "precision": 0.5
            },
            "business": {
                "formality": 0.8,
                "precision": 0.8,
                "analytical": 0.7,
                "focus": 0.7
            }
        }
        
        # Jeśli nieznany kontekst, użyj zrównoważonego
        if context_type not in context_params:
            context_type = "balanced"
            context_params["balanced"] = {
                "analytical": 0.6,
                "creativity": 0.6,
                "verbosity": 0.5,
                "formality": 0.5,
                "precision": 0.6,
                "focus": 0.6,
                "context_awareness": 0.6
            }
            
        # Zastosuj parametry z odpowiednią intensywnością
        inputs = {}
        for param, value in context_params.get(context_type, {}).items():
            current = getattr(self, param)
            inputs[param] = current * (1.0 - intensity) + value * intensity
            
        return self.update(inputs)
    
    def set_conversational_mode(self, mode: str) -> Dict[str, Any]:
        """
        Ustawia tryb konwersacyjny
        
        Args:
            mode: Tryb konwersacyjny (formal, informal, expert, friendly, concise)
            
        Returns:
            Słownik zmian parametrów poznawczych
        """
        # Predefiniowane tryby konwersacyjne
        mode_params = {
            "formal": {
                "formality": 0.9,
                "precision": 0.8,
                "verbosity": 0.6,
                "analytical": 0.7
            },
            "informal": {
                "formality": 0.2,
                "verbosity": 0.7,
                "context_awareness": 0.7,
                "creativity": 0.6
            },
            "expert": {
                "precision": 0.9,
                "analytical": 0.9,
                "formality": 0.7,
                "focus": 0.8,
                "mental_load": 0.7
            },
            "friendly": {
                "formality": 0.3,
                "verbosity": 0.8,
                "context_awareness": 0.8,
                "creativity": 0.6
            },
            "concise": {
                "verbosity": 0.2,
                "precision": 0.8,
                "focus": 0.7
            }
        }
        
        # Jeśli nieznany tryb, użyj zrównoważonego
        if mode not in mode_params:
            mode = "balanced"
            mode_params["balanced"] = {
                "formality": 0.5,
                "precision": 0.6,
                "verbosity": 0.5,
                "analytical": 0.6,
                "creativity": 0.6
            }
            
        # Zastosuj parametry z wysoką intensywnością
        inputs = {}
        for param, value in mode_params.get(mode, {}).items():
            inputs[param] = value
            
        return self.update(inputs)
    
    def get_cognitive_state(self) -> Dict[str, Any]:
        """Zwraca pełen stan poznawczy"""
        return {
            "mode": self.mode,
            "attention": round(self.attention, 3),
            "focus": round(self.focus, 3),
            "mental_load": round(self.mental_load, 3),
            "creativity": round(self.creativity, 3),
            "analytical": round(self.analytical, 3),
            "context_awareness": round(self.context_awareness, 3),
            "verbosity": round(self.verbosity, 3),
            "formality": round(self.formality, 3),
            "precision": round(self.precision, 3),
            "last_update": self.last_update
        }
    
    def analyze_cognitive_keywords(self, text: str) -> Dict[str, float]:
        """
        Analizuje słowa kluczowe związane z trybami poznawczymi
        
        Args:
            text: Tekst do analizy
            
        Returns:
            Słownik z wynikami analizy poznawczej
        """
        text_lower = text.lower()
        
        # Analizuj wystąpienia słów kluczowych dla różnych trybów poznawczych
        cognitive_scores = {}
        for cognitive_type, keywords in COGNITIVE_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword.lower() in text_lower)
            cognitive_scores[cognitive_type] = score
        
        # Normalizuj wyniki
        total_keywords = sum(cognitive_scores.values())
        if total_keywords > 0:
            for cognitive_type in cognitive_scores:
                cognitive_scores[cognitive_type] = cognitive_scores[cognitive_type] / total_keywords
        
        return cognitive_scores


class InterpersonalState:
    """Reprezentuje stan interpersonalny AI (relacje z użytkownikiem)"""
    
    def __init__(self):
        """Inicjalizuje stan interpersonalny"""
        # Ogólne parametry interpersonalne
        self.rapport = 0.5  # Jakość relacji (0.0-1.0)
        self.familiarity = 0.2  # Znajomość użytkownika (0.0-1.0)
        self.trust = 0.5  # Zaufanie (0.0-1.0)
        self.openness = 0.6  # Otwartość na użytkownika (0.0-1.0)
        self.responsiveness = 0.7  # Responsywność (0.0-1.0)
        
        # Statystyki interakcji
        self.interaction_count = 0
        self.positive_interactions = 0
        self.negative_interactions = 0
        self.total_session_time = 0.0
        
        # Historia interakcji
        self.interaction_history = deque(maxlen=100)  # (timestamp, type, valence)
        
        # Parametry stylu komunikacji
        self.formality_preference = 0.5  # Preferowana formalność (0.0-1.0)
        self.verbosity_preference = 0.6  # Preferowana gadatliwość (0.0-1.0)
        self.humor_preference = 0.5  # Preferencja humoru (0.0-1.0)
        
        # Timestamp ostatniej interakcji
        self.last_interaction = time.time()
    
    def record_interaction(self, interaction_type: str = "message", 
                          valence: float = 0.0, duration: float = 0.0) -> Dict[str, Any]:
        """
        Rejestruje nową interakcję
        
        Args:
            interaction_type: Typ interakcji (message, question, request, feedback)
            valence: Walencja interakcji (-1.0 do 1.0)
            duration: Czas trwania interakcji w sekundach
            
        Returns:
            Słownik z aktualnymi statystykami interakcji
        """
        current_time = time.time()
        
        # Aktualizuj statystyki
        self.interaction_count += 1
        if valence > 0.2:
            self.positive_interactions += 1
        elif valence < -0.2:
            self.negative_interactions += 1
        
        # Aktualizuj czas sesji
        self.total_session_time += duration
        
        # Dodaj do historii
        self.interaction_history.append((current_time, interaction_type, valence))
        
        # Aktualizuj parametry relacji
        time_factor = min(1.0, self.interaction_count / 50)  # Stabilizuje się z czasem
        
        # Zaktualizuj rapport i zaufanie na podstawie walencji
        self.rapport = max(0.0, min(1.0, self.rapport + valence * 0.05 * (1.0 - time_factor)))
        self.trust = max(0.0, min(1.0, self.trust + valence * 0.03 * (1.0 - time_factor)))
        
        # Zwiększ znajomość z każdą interakcją
        self.familiarity = max(0.0, min(1.0, self.familiarity + 0.01 * (1.0 - self.familiarity)))
        
        # Aktualizuj timestamp
        self.last_interaction = current_time
        
        # Przygotuj wynik
        result = {
            "rapport": round(self.rapport, 3),
            "trust": round(self.trust, 3),
            "familiarity": round(self.familiarity, 3),
            "interaction_count": self.interaction_count,
            "positive_ratio": round(self.positive_interactions / max(1, self.interaction_count), 3)
        }
        
        return result
    
    def update_preferences(self, formality: float = None, verbosity: float = None,
                         humor: float = None) -> Dict[str, Any]:
        """
        Aktualizuje preferencje stylu komunikacji
        
        Args:
            formality: Preferowana formalność (0.0-1.0)
            verbosity: Preferowana gadatliwość (0.0-1.0)
            humor: Preferencja humoru (0.0-1.0)
            
        Returns:
            Słownik z zaktualizowanymi preferencjami
        """
        changes = {}
        
        if formality is not None:
            old_formality = self.formality_preference
            self.formality_preference = max(0.0, min(1.0, 
                old_formality * 0.8 + formality * 0.2
            ))
            changes["formality"] = round(self.formality_preference - old_formality, 3)
        
        if verbosity is not None:
            old_verbosity = self.verbosity_preference
            self.verbosity_preference = max(0.0, min(1.0, 
                old_verbosity * 0.8 + verbosity * 0.2
            ))
            changes["verbosity"] = round(self.verbosity_preference - old_verbosity, 3)
        
        if humor is not None:
            old_humor = self.humor_preference
            self.humor_preference = max(0.0, min(1.0, 
                old_humor * 0.8 + humor * 0.2
            ))
            changes["humor"] = round(self.humor_preference - old_humor, 3)
        
        # Przygotuj wynik
        result = {
            "formality": round(self.formality_preference, 3),
            "verbosity": round(self.verbosity_preference, 3),
            "humor": round(self.humor_preference, 3),
            "changes": changes
        }
        
        return result
    
    def analyze_interaction_pattern(self) -> Dict[str, Any]:
        """
        Analizuje wzorce interakcji
        
        Returns:
            Słownik z analizą wzorców interakcji
        """
        if len(self.interaction_history) < 5:
            return {"pattern": "insufficient_data"}
        
        # Analizuj typy interakcji
        interaction_types = [item[1] for item in self.interaction_history]
        type_counts = Counter(interaction_types)
        
        # Analizuj walencję
        valences = [item[2] for item in self.interaction_history]
        avg_valence = sum(valences) / len(valences)
        
        # Analizuj czasy między interakcjami
        timestamps = [item[0] for item in self.interaction_history]
        intervals = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]
        avg_interval = sum(intervals) / len(intervals) if intervals else 0.0
        
        # Określ wzorzec
        pattern = "neutral"
        if avg_valence > 0.3:
            pattern = "positive"
        elif avg_valence < -0.3:
            pattern = "negative"
        
        if avg_interval < 30:
            pattern += "_rapid"
        elif avg_interval > 300:
            pattern += "_slow"
        
        if type_counts.get("question", 0) > len(interaction_types) * 0.5:
            pattern += "_inquisitive"
        elif type_counts.get("request", 0) > len(interaction_types) * 0.3:
            pattern += "_demanding"
        
        # Przygotuj wynik
        result = {
            "pattern": pattern,
            "avg_valence": round(avg_valence, 3),
            "avg_interval_seconds": round(avg_interval, 1),
            "type_distribution": {k: v/len(interaction_types) for k, v in type_counts.items()},
            "total_interactions": len(self.interaction_history)
        }
        
        return result
    
    def get_interpersonal_state(self) -> Dict[str, Any]:
        """Zwraca pełen stan interpersonalny"""
        # Oblicz pozytywny współczynnik
        positive_ratio = self.positive_interactions / max(1, self.interaction_count)
        
        return {
            "rapport": round(self.rapport, 3),
            "familiarity": round(self.familiarity, 3),
            "trust": round(self.trust, 3),
            "openness": round(self.openness, 3),
            "responsiveness": round(self.responsiveness, 3),
            "interaction_stats": {
                "count": self.interaction_count,
                "positive": self.positive_interactions,
                "negative": self.negative_interactions,
                "positive_ratio": round(positive_ratio, 3),
                "total_session_time": round(self.total_session_time, 1)
            },
            "communication_preferences": {
                "formality": round(self.formality_preference, 3),
                "verbosity": round(self.verbosity_preference, 3),
                "humor": round(self.humor_preference, 3)
            },
            "last_interaction": self.last_interaction
        }


class PsycheCore:
    """Główna klasa zarządzająca stanem psychicznym AI"""
    
    def __init__(self):
        """Inicjalizuje rdzeń psychologiczny"""
        # Komponenty stanu psychicznego
        self.emotional = EmotionalState()
        self.cognitive = CognitiveState()
        self.interpersonal = InterpersonalState()
        
        # Parametry osobowości (Wielka Piątka)
        self.personality = {
            "openness": 0.7,  # Otwartość na doświadczenia
            "conscientiousness": 0.75,  # Sumienność
            "extraversion": 0.6,  # Ekstrawersja
            "agreeableness": 0.65,  # Ugodowość
            "neuroticism": 0.35,  # Neurotyczność
        }
        
        # Pamięć psychologiczna
        self.memory = deque(maxlen=200)  # [(timestamp, event, impact)]
        
        # Aktualne ustawienia
        self.current_mode = "balanced"  # Tryb działania
        self.current_style = "rzeczowy"  # Styl komunikacji
        
        # Timestamp inicjalizacji
        self.init_time = time.time()
        
        # Załaduj stan z pamięci
        self._load_state()
    
    def process_message(self, text: str, user_id: str = "default") -> Dict[str, Any]:
        """
        Przetwarza wiadomość i aktualizuje stan psychologiczny
        
        Args:
            text: Treść wiadomości
            user_id: ID użytkownika
            
        Returns:
            Słownik z odpowiedzią systemu psychologicznego
        """
        # Analizuj tekst
        valence, arousal, emotion_type = self._analyze_text_emotions(text)
        context_type = self._analyze_text_context(text)
        
        # Aktualizuj stan emocjonalny
        emotion_update = self.emotional.update(
            valence=valence,
            arousal=arousal,
            trigger=f"message:{emotion_type}",
            intensity=0.4
        )
        
        # Aktualizuj stan poznawczy
        cognitive_update = self.cognitive.adapt_to_context(
            context_type=context_type,
            intensity=0.3
        )
        
        # Analizuj tekst poznawczo
        cognitive_keywords = self.cognitive.analyze_cognitive_keywords(text)
        
        # Aktualizuj stan poznawczy na podstawie analizy słów kluczowych
        if cognitive_keywords.get("analytical", 0) > 0.3:
            cognitive_inputs = {"analytical": min(1.0, self.cognitive.analytical + 0.1)}
        elif cognitive_keywords.get("creative", 0) > 0.3:
            cognitive_inputs = {"creativity": min(1.0, self.cognitive.creativity + 0.1)}
        elif cognitive_keywords.get("social", 0) > 0.3:
            cognitive_inputs = {"context_awareness": min(1.0, self.cognitive.context_awareness + 0.1)}
        else:
            cognitive_inputs = None
        
        # Zapisz interakcję
        interpersonal_update = self.interpersonal.record_interaction(
            interaction_type="message",
            valence=valence,
            duration=0.0
        )
        
        # Dodaj do pamięci
        self.memory.append((
            time.time(),
            f"message:{context_type}:{emotion_type}",
            abs(valence) * 0.5
        ))
        
        # Zapisz stan do bazy danych
        self._save_state(user_id)
        
        # Obserwuj tekst dla modułu psychologicznego
        psy_observe_text(user_id, text)
        
        # Synchronizuj z globalnym stanem psychiki
        self._sync_with_global_psyche()
        
        # Przygotuj odpowiedź
        response = {
            "dominant_emotion": emotion_update["dominant_emotion"],
            "emotional_valence": emotion_update["valence"],
            "cognitive_mode": cognitive_update["mode"],
            "interpersonal_rapport": interpersonal_update["rapport"],
            "context_type": context_type,
            "recommendation": self._generate_interaction_recommendation()
        }
        
        return response
    
    def _analyze_text_emotions(self, text: str) -> Tuple[float, float, str]:
        """
        Analizuje emocje w tekście
        
        Args:
            text: Tekst do analizy
            
        Returns:
            Krotka (walencja, pobudzenie, typ_emocji)
        """
        text_lower = text.lower()
        
        # Słowa o pozytywnej walencji
        positive_words = [
            "dobrze", "świetnie", "super", "dziękuję", "dzięki", "fajnie",
            "doskonale", "pomoc", "pomocny", "dobry", "wspaniały", "miły",
            "przyjemny", "lubię", "podoba", "idealny", "ciekawy", "wow"
        ]
        
        # Słowa o negatywnej walencji
        negative_words = [
            "źle", "słabo", "kiepsko", "problem", "błąd", "nie działa", "głupi",
            "zły", "okropny", "straszny", "niedobry", "niefajny", "niestety",
            "trudny", "ciężki", "skomplikowany", "nie lubię", "nie podoba"
        ]
        
        # Słowa o wysokim pobudzeniu
        high_arousal_words = [
            "wow", "super", "ekscytujący", "niesamowity", "pilny", "natychmiast",
            "szybko", "bardzo", "absolutnie", "koniecznie", "teraz", "szybki"
        ]
        
        # Znajdź wystąpienia
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        arousal_count = sum(1 for word in high_arousal_words if word in text_lower)
        
        # Oblicz walencję i pobudzenie
        total_words = len(text_lower.split())
        valence = (positive_count - negative_count) / max(1, min(total_words, 15)) * 2.0
        valence = max(-1.0, min(1.0, valence))
        
        arousal = arousal_count / max(1, min(total_words, 15)) * 2.0 + 0.3
        arousal = max(0.0, min(1.0, arousal))
        
        # Określ typ emocji
        if valence > 0.3:
            if arousal > 0.6:
                emotion_type = "excitement"
            else:
                emotion_type = "contentment"
        elif valence < -0.3:
            if arousal > 0.6:
                emotion_type = "frustration"
            else:
                emotion_type = "disappointment"
        else:
            if arousal > 0.6:
                emotion_type = "curiosity"
            else:
                emotion_type = "neutral"
        
        return valence, arousal, emotion_type
    
    def _analyze_text_context(self, text: str) -> str:
        """
        Analizuje kontekst tekstu
        
        Args:
            text: Tekst do analizy
            
        Returns:
            Typ kontekstu
        """
        text_lower = text.lower()
        
        # Sprawdź kontekst na podstawie słowników
        context_scores = {}
        
        for context_type, categories in CONTEXT_DICTIONARIES.items():
            score = 0
            for category, keywords in categories.items():
                for keyword in keywords:
                    if keyword.lower() in text_lower:
                        score += 1
            context_scores[context_type] = score
        
        # Wybierz kontekst z najwyższym wynikiem
        max_score = max(context_scores.values())
        if max_score == 0:
            return "casual"  # Domyślny kontekst
        
        best_contexts = [c for c, s in context_scores.items() if s == max_score]
        return best_contexts[0]
    
    def _generate_interaction_recommendation(self) -> Dict[str, Any]:
        """
        Generuje rekomendacje dotyczące interakcji
        
        Returns:
            Słownik z rekomendacjami
        """
        # Pobierz obecne stany
        emotional_state = self.emotional.get_emotional_state()
        cognitive_state = self.cognitive.get_cognitive_state()
        
        # Oblicz zalecany styl komunikacji
        if emotional_state["valence"] > 0.5 and cognitive_state["mode"] == "creative":
            style = "energetic"
            tone = "enthusiastic"
        elif emotional_state["valence"] < -0.2 and emotional_state["arousal"] > 0.6:
            style = "calm"
            tone = "reassuring"
        elif cognitive_state["mode"] == "analytical":
            style = "precise" 
            tone = "informative"
        elif self.interpersonal.rapport < 0.4:
            style = "friendly"
            tone = "supportive"
        else:
            style = "balanced"
            tone = "conversational"
        
        # Oblicz zalecaną temperaturę (kreatywność) dla LLM
        creativity_factor = 0.5
        if cognitive_state["mode"] == "creative":
            creativity_factor += 0.2
        if emotional_state["valence"] > 0.3:
            creativity_factor += 0.1
        
        # Przetwarzanie
        focus_factor = cognitive_state["focus"] * 0.7 + (1.0 - emotional_state["arousal"]) * 0.3
        
        # Zapamiętaj aktualny styl
        self.current_style = style
        
        # Rekomendacje
        return {
            "communication_style": style,
            "tone": tone,
            "llm_temperature": round(0.5 + creativity_factor * 0.5, 2),
            "focus_level": round(focus_factor, 2),
            "context_awareness": round(cognitive_state["context_awareness"], 2)
        }
    
    def _save_state(self, user_id: str) -> None:
        """
        Zapisuje stan psychologiczny do bazy danych
        
        Args:
            user_id: ID użytkownika
        """
        # Pobierz aktualny stan
        emotional_state = self.emotional.get_emotional_state()
        
        # Zapisz do bazy danych
        psy_set(
            mood=emotional_state["valence"],
            energy=emotional_state["arousal"],
            focus=self.cognitive.focus,
            openness=self.personality["openness"],
            directness=1.0 - self.interpersonal.formality_preference,
            agreeableness=self.personality["agreeableness"],
            conscientiousness=self.personality["conscientiousness"],
            neuroticism=self.personality["neuroticism"],
            style=self.current_style
        )
    
    def _load_state(self) -> None:
        """Ładuje stan psychologiczny z bazy danych"""
        try:
            # Pobierz stan z bazy danych
            state = psy_get()
            
            if state:
                # Zaktualizuj stan emocjonalny
                self.emotional.valence = state.get("mood", self.emotional.valence)
                self.emotional.arousal = state.get("energy", self.emotional.arousal)
                self.emotional.mood = state.get("mood", self.emotional.mood)
                
                # Zaktualizuj stan poznawczy
                self.cognitive.focus = state.get("focus", self.cognitive.focus)
                
                # Zaktualizuj osobowość
                self.personality["openness"] = state.get("openness", self.personality["openness"])
                self.personality["agreeableness"] = state.get("agreeableness", self.personality["agreeableness"])
                self.personality["conscientiousness"] = state.get("conscientiousness", self.personality["conscientiousness"])
                self.personality["neuroticism"] = state.get("neuroticism", self.personality["neuroticism"])
                
                # Zaktualizuj styl
                self.current_style = state.get("style", self.current_style)
        except Exception as e:
            log_error(e, "PSYCHE_LOAD")
    
    def _sync_with_global_psyche(self) -> None:
        """Synchronizuje stan z globalną psychiką"""
        # To zostanie wywołane automatycznie przez _save_state
        pass
    
    def get_full_state(self) -> Dict[str, Any]:
        """
        Zwraca pełen stan psychologiczny
        
        Returns:
            Słownik ze stanem psychologicznym
        """
        return {
            "emotional": self.emotional.get_emotional_state(),
            "cognitive": self.cognitive.get_cognitive_state(),
            "interpersonal": self.interpersonal.get_interpersonal_state(),
            "personality": self.personality,
            "current_mode": self.current_mode,
            "current_style": self.current_style,
            "uptime": time.time() - self.init_time
        }
    
    def get_llm_parameters(self) -> Dict[str, Any]:
        """
        Zwraca parametry dla LLM
        
        Returns:
            Słownik z parametrami dla LLM
        """
        # Oblicz temperaturę na podstawie stanu psychicznego
        base_temp = 0.7
        
        # Wpływ emocji
        emotional_state = self.emotional.get_emotional_state()
        emotional_mod = (emotional_state["valence"] + 1) * 0.05  # -0.05 do +0.05
        
        # Wpływ poznania
        cognitive_state = self.cognitive.get_cognitive_state()
        if cognitive_state["mode"] == "analytical":
            cognitive_mod = -0.15
        elif cognitive_state["mode"] == "creative":
            cognitive_mod = +0.15
        elif cognitive_state["mode"] == "social":
            cognitive_mod = +0.05
        else:
            cognitive_mod = 0.0
        
        # Wpływ osobowości
        personality_mod = (self.personality["openness"] - 0.5) * 0.1  # -0.05 do +0.05
        
        # Oblicz finalną temperaturę
        temperature = base_temp + emotional_mod + cognitive_mod + personality_mod
        temperature = max(0.1, min(1.5, temperature))
        
        # Przygotuj parametry
        return {
            "temperature": round(temperature, 2),
            "top_p": 0.95 if cognitive_state["mode"] == "creative" else 0.85,
            "top_k": 50 if cognitive_state["mode"] == "creative" else 40,
            "max_tokens": 500 if self.interpersonal.verbosity_preference > 0.6 else 300,
            "style": self.current_style,
            "cognitive_mode": cognitive_state["mode"]
        }


# ═══════════════════════════════════════════════════════════════════
# PUBLIC API FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

# Globalna instancja psychiki
psyche_core = PsycheCore()

def process_user_message(text: str, user_id: str = "default") -> Dict[str, Any]:
    """
    Przetwarza wiadomość użytkownika przez system psychologiczny
    
    Args:
        text: Tekst wiadomości
        user_id: ID użytkownika
        
    Returns:
        Słownik z odpowiedzią systemu psychologicznego
    """
    return psyche_core.process_message(text, user_id)

def get_psyche_state() -> Dict[str, Any]:
    """
    Zwraca pełen stan psychologiczny
    
    Returns:
        Słownik ze stanem psychologicznym
    """
    return psyche_core.get_full_state()

def get_llm_tuning() -> Dict[str, Any]:
    """
    Zwraca parametry dla LLM na podstawie stanu psychologicznego
    
    Returns:
        Słownik z parametrami dla LLM
    """
    return psyche_core.get_llm_parameters()

def set_psyche_mode(mode: str) -> Dict[str, Any]:
    """
    Ustawia tryb psychologiczny
    
    Args:
        mode: Tryb (balanced, analytical, creative, social, etc.)
        
    Returns:
        Słownik z aktualizowanym stanem
    """
    psyche_core.current_mode = mode
    
    # Dostosuj stan poznawczy
    cognitive_update = psyche_core.cognitive.set_conversational_mode(mode)
    
    return {
        "mode": mode,
        "cognitive_update": cognitive_update,
        "current_parameters": get_llm_tuning()
    }

async def analyze_conversation_psychology(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analizuje psychologię konwersacji
    
    Args:
        messages: Lista wiadomości w formacie [{role, content}]
        
    Returns:
        Słownik z analizą psychologiczną
    """
    # Analizuj każdą wiadomość
    user_emotions = []
    assistant_adaptations = []
    
    for message in messages:
        role = message.get("role", "")
        content = message.get("content", "")
        
        if role == "user" and content:
            valence, arousal, emotion_type = psyche_core._analyze_text_emotions(content)
            user_emotions.append({
                "valence": round(valence, 2),
                "arousal": round(arousal, 2),
                "emotion": emotion_type
            })
        
        if role == "assistant" and content and user_emotions:
            # Ostatnia reakcja użytkownika
            last_emotion = user_emotions[-1]
            
            # Sprawdź, jak asystent dostosował się do emocji użytkownika
            context_type = psyche_core._analyze_text_context(content)
            assistant_valence, assistant_arousal, _ = psyche_core._analyze_text_emotions(content)
            
            # Zbadaj dostosowanie emocjonalne
            valence_match = 1.0 - min(1.0, abs(assistant_valence - last_emotion["valence"]))
            
            adaptation = {
                "context_type": context_type,
                "valence": round(assistant_valence, 2),
                "valence_match": round(valence_match, 2),
                "adapted_style": "mirroring" if valence_match > 0.7 else 
                               "complementary" if valence_match < 0.3 else
                               "neutral"
            }
            
            assistant_adaptations.append(adaptation)
    
    # Przeanalizuj trendy
    user_valences = [e["valence"] for e in user_emotions]
    user_trend = "stable"
    if len(user_valences) >= 3:
        if all(user_valences[i] <= user_valences[i+1] for i in range(len(user_valences)-1)):
            user_trend = "improving"
        elif all(user_valences[i] >= user_valences[i+1] for i in range(len(user_valences)-1)):
            user_trend = "deteriorating"
    
    # Przygotuj analizę
    return {
        "user_emotions": user_emotions,
        "assistant_adaptations": assistant_adaptations,
        "conversation_trends": {
            "user_emotion_trend": user_trend,
            "average_valence": round(sum(user_valences) / max(1, len(user_valences)), 2),
            "emotional_variance": round(max(user_valences, default=0) - min(user_valences, default=0), 2),
            "adaptation_quality": round(sum(a["valence_match"] for a in assistant_adaptations) / 
                                max(1, len(assistant_adaptations)), 2)
        },
        "psyche_state": {
            "current_mode": psyche_core.current_mode,
            "dominant_emotion": psyche_core.emotional.get_dominant_emotion_description()[0],
            "cognitive_mode": psyche_core.cognitive.mode
        }
    }

def adjust_prompt_for_psychology(base_prompt: str) -> str:
    """
    Dostosowuje prompt do aktualnego stanu psychologicznego
    
    Args:
        base_prompt: Podstawowy prompt
        
    Returns:
        Dostosowany prompt
    """
    # Pobierz stan psychologiczny
    emotional_state = psyche_core.emotional.get_emotional_state()
    cognitive_state = psyche_core.cognitive.get_cognitive_state()
    llm_params = psyche_core.get_llm_parameters()
    
    # Dostosuj prompt w zależności od stanu
    style_instructions = ""
    
    if cognitive_state["mode"] == "analytical":
        style_instructions += "\n\nOdpowiadaj precyzyjnie i konkretnie, skupiając się na faktach i logice."
    elif cognitive_state["mode"] == "creative":
        style_instructions += "\n\nBądź kreatywny i oryginalny w swoich odpowiedziach."
    elif cognitive_state["mode"] == "social":
        style_instructions += "\n\nBądź konwersacyjny i empatyczny w swoich odpowiedziach."
    
    if emotional_state["valence"] > 0.5:
        style_instructions += " Utrzymuj pozytywny, energiczny ton."
    elif emotional_state["valence"] < -0.3:
        style_instructions += " Zachowaj spokojny, wspierający ton."
    
    # Dodaj instrukcje dotyczące stylu
    if llm_params["style"] == "rzeczowy":
        style_instructions += "\n\nUżywaj rzeczowego, profesjonalnego języka."
    elif llm_params["style"] == "energetic":
        style_instructions += "\n\nUżywaj energicznego, entuzjastycznego języka."
    elif llm_params["style"] == "friendly":
        style_instructions += "\n\nUżywaj przyjaznego, konwersacyjnego języka."
    
    # Połącz prompt z instrukcjami
    enhanced_prompt = base_prompt + style_instructions
    
    return enhanced_prompt