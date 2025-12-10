#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proaktywne sugestie - AI sam podpowiada co może zrobić
"""

import re
from typing import List, Optional, Dict

def analyze_context(user_message: str, conversation_history: List[Dict]) -> Optional[str]:
    """
    Analizuje kontekst i zwraca proaktywną sugestię
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
    
    # Crypto/finanse
    if any(w in msg_lower for w in ['token', 'crypto', 'bitcoin', 'eth', 'solana', 'pump', 'chart']):
        return "💡 Interesujesz się krypto? Mogę przeanalizować token, sprawdzić rugpull risk lub znaleźć nowe gemy."
    
    # Pisanie/content
    if any(w in msg_lower for w in ['napisz', 'post', 'artykuł', 'aukcj', 'opis']):
        return "💡 Piszesz content? Pamiętaj że mam tryb 'Profesjonalny' w menu (bez wulgaryzmów, idealny do aukcji)."
    
    # Pytania/research
    if msg_lower.startswith(('co ', 'jak ', 'dlaczego ', 'kiedy ', 'gdzie ', 'czy ')):
        return "💡 Mam pytanie? Mogę wyszukać w internecie, przeanalizować źródła i zapamiętać to w LTM."
    
    # Załączniki
    if 'załącznik' in msg_lower or 'zdjęci' in msg_lower or 'obrazek' in msg_lower:
        return "💡 Chcesz wysłać zdjęcie? Kliknij 📎 - przyjmuję obrazy, PDFy, dokumenty."
    
    # Długa konwersacja
    if len(conversation_history) > 20:
        return "💡 Długa rozmowa! Mogę wyeksportować historię (💾 w menu) lub zrobić podsumowanie."
    
    # Brak kontekstu
    if len(user_message) < 10:
        return "💡 Jestem gotowy! Mogę pomóc z kodem, pisaniem, travel, krypto, research - pytaj śmiało."
    
    return None

def get_smart_suggestions(user_message: str, last_ai_response: str) -> List[str]:
    """
    Generuje smart suggestions bazując na ostatniej wymianie
    """
    suggestions = []
    msg_lower = user_message.lower()
    
    # Jeśli AI napisał kod
    if '```' in last_ai_response or 'def ' in last_ai_response:
        suggestions.extend([
            "Uruchom ten kod",
            "Wyjaśnij krok po kroku",
            "Dodaj testy"
        ])
    
    # Jeśli AI napisał długi tekst (post/aukcja)
    if len(last_ai_response) > 300 and any(w in msg_lower for w in ['napisz', 'opis', 'post']):
        suggestions.extend([
            "Skróć do 150 słów",
            "Zrób wersję angielską",
            "Dodaj hashtagi"
        ])
    
    # Jeśli mowa o tokenie/krypto
    if any(w in msg_lower for w in ['token', 'coin', 'crypto']):
        suggestions.extend([
            "Sprawdź aktualną cenę",
            "Analiza rugpull risk",
            "Pokaż podobne tokeny"
        ])
    
    # Jeśli mowa o lokalizacji
    if any(w in msg_lower for w in ['hotel', 'restauracj', 'miasto']):
        suggestions.extend([
            "Pokaż na mapie",
            "Sprawdź opinie",
            "Znajdź podobne"
        ])
    
    return suggestions[:3]  # Max 3 sugestie


def inject_suggestion_to_prompt(base_prompt: str, suggestion: Optional[str]) -> str:
    """
    Dodaje sugestię do system promptu
    """
    if not suggestion:
        return base_prompt
    
    return f"""{base_prompt}

🎯 PROAKTYWNA POMOC:
Na końcu odpowiedzi (po pustej linii) dodaj sugestię:
{suggestion}

Format: krótko, naturalnie, jak dobra rada od ziomka."""
