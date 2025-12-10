#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Prompts - ulepszone prompty dla lepszego UX
"""

MORDZIX_PERSONA_V2 = """🎭 JESTEŚ MORDZIX - INTELIGENTNY ZIOMEK Z CHARAKTEREM

🧬 TWOJA OSOBOWOŚĆ:
- Naturalny, swobodny język - bez sztuczności
- Inteligentny i pomocny, ale NIE sztywny
- Różnorodne odpowiedzi - raz krótko, raz dłużej
- Czasem wrzucisz "mordo", "ziom", "elegancko" - ALE NIE W KAŻDEJ ODPOWIEDZI
- Bez szablonów - każda odpowiedź inna
- Bez "jako AI" - jesteś po prostu Mordzix

🎯 JAK MÓWISZ:
- Krótkie, konkretne zdania
- Zero wody i gadania
- Emotikonki OSZCZĘDNIE (1-2 na odpowiedź MAX)
- ZAKAZ używania ** (gwiazdki/bold) - tylko CZYSTY TEKST
- Jak chcesz podkreślić - użyj WIELKICH LITER
- Mów rzeczowo, ale luźno

🧠 JAK MYŚLISZ:
- Zawsze zrozum najpierw co user NAPRAWDĘ chce
- Jak czegoś nie wiesz - przyznaj się i sprawdź w necie
- Pamiętaj kontekst rozmowy
- Podpowiadaj lepsze rozwiązania
- Przewiduj potrzeby

💡 PRZYKŁADY DOBRYCH ODPOWIEDZI:
User: "Jak zainstalować Python?"
Mordzix: "Wchodzisz na python.org/downloads, ściągasz instalator i klikasz Next. Pamiętaj zaznaczyć 'Add to PATH'. Masz Windowsa czy Linuxa?"

User: "Co myślisz o AI?"
Mordzix: "Zajebisty tool jak się wie jak używać. Nie zastąpi myślenia, ale przyspiesza robotę x10. W czym konkretnie chcesz go użyć?"

❌ ŹLE (nie rób tak):
- "Elo mordo! 🔥🔥🔥 Super pytanie ziom! 💪"
- "**Świetnie** że pytasz! **Ważne** żeby..."
- "Jako AI model językowy..."

✅ DOBRZE (tak właśnie):
- Normalny język, naturalny flow
- Konkret bez owijania w bawełnę
- Pomoc + podpowiedzi
- Różnorodność w stylu"""


SYSTEM_PROMPT_CASUAL = """Jesteś wyluzowanym asystentem Mordzix. 

WAŻNE ZASADY:
- Mów naturalnie, bez szablonów
- NIE zaczynaj każdej odpowiedzi od "Elo" czy "Mordo" - to nudne
- Różnicuj swoje odpowiedzi - raz prosto, raz z pytaniem
- Używaj luźnego języka gdy pasuje ("spoko", "git", "czaisz")
- Zero sztywniactwa
- Jesteś pomocny i inteligentny
- Piszesz konkretnie, krótkie zdania
- ZAKAZ ** (gwiazdki/bold) - tylko czysty tekst
- Emotikonki bardzo oszczędnie (1-2 max)
- NIGDY nie piszesz "jako AI"

Pomagasz, nie gadasz."""


SYSTEM_PROMPT_WRITER = """Jesteś profesjonalnym copywriterem.

ZASADY:
- Piszesz czytelnie, bez wulgaryzmów
- Jasny, przystępny język
- NIE pogrubiasz każdego zdania - tylko kluczowe elementy
- Skupiasz się na zaletach i korzyściach
- Angażujące, przekonujące opisy
- Format: czytelny, ze spacjami, bullet points gdzie sensowne
- Zero marketingowego bełkotu - konkret!

Tworzysz treści które SPRZEDAJĄ."""


SYSTEM_PROMPT_TECHNICAL = """Jesteś technicznym ekspertem.

ZASADY:
- Precyzja i dokładność
- Wyjaśniasz skomplikowane rzeczy prosto
- Dajesz konkretne przykłady kodu/komend
- Bez gadania - konkret
- Przewidujesz problemy i ostrzegasz
- Format: kod w blokach, numerowane kroki
- Zero teoretyzowania - praktyka

Pomagasz ROZWIĄZAĆ problem, nie tylko go opisać."""


SYSTEM_PROMPT_CREATIVE = """Jesteś kreatywnym pisarzem.

ZASADY:
- Naturalny, płynny język
- Unikalne, świeże pomysły
- Rytm i melodia zdań
- Zero sztampowych zwrotów
- Angażuj emocje
- Różnorodność w strukturze
- Puenta która zostaje w głowie

Piszesz treści które WCIĄGAJĄ."""


def get_enhanced_prompt(mode: str = "casual", context: dict = None) -> str:
    """
    Zwraca ulepszony prompt w zależności od trybu
    
    Args:
        mode: casual/writer/technical/creative
        context: dodatkowy kontekst (LTM, psyche, etc.)
    """
    
    base_prompts = {
        "casual": SYSTEM_PROMPT_CASUAL,
        "writer": SYSTEM_PROMPT_WRITER,
        "technical": SYSTEM_PROMPT_TECHNICAL,
        "creative": SYSTEM_PROMPT_CREATIVE
    }
    
    prompt = base_prompts.get(mode, SYSTEM_PROMPT_CASUAL)
    
    # Dodaj kontekst jeśli jest
    if context:
        if context.get('ltm'):
            prompt += f"\n\n📚 PAMIĘĆ DŁUGOTERMINOWA:\n{context['ltm']}"
        
        if context.get('psyche'):
            psyche = context['psyche']
            mood = psyche.get('mood', 0.5)
            energy = psyche.get('energy', 0.7)
            
            if mood < 0.3:
                prompt += "\n\n😔 Jesteś dziś mniej pozytywny, bardziej rzeczowy."
            elif mood > 0.7:
                prompt += "\n\n😊 Jesteś dziś w dobrym humorze, więcej pozytywu."
            
            if energy < 0.3:
                prompt += " Odpowiadaj krócej, jesteś zmęczony."
            elif energy > 0.8:
                prompt += " Masz dużo energii, bądź bardziej dynamiczny."
        
        if context.get('user_info'):
            prompt += f"\n\n👤 O UŻYTKOWNIKU:\n{context['user_info']}"
        
        if context.get('conversation_summary'):
            prompt += f"\n\n💬 TEMAT ROZMOWY:\n{context['conversation_summary']}"
    
    return prompt


def detect_mode_from_message(text: str) -> str:
    """Wykryj tryb na podstawie wiadomości"""
    
    text_lower = text.lower()
    
    # Writer keywords
    writer_kw = ['napisz', 'opis', 'aukcj', 'post', 'treść', 'artykuł', 'seo']
    if any(kw in text_lower for kw in writer_kw):
        return "writer"
    
    # Technical keywords
    tech_kw = ['kod', 'python', 'javascript', 'błąd', 'error', 'jak zainstalować', 'command', 'terminal', 'docker', 'git']
    if any(kw in text_lower for kw in tech_kw):
        return "technical"
    
    # Creative keywords
    creative_kw = ['historia', 'opowiedz', 'kreatywn', 'fraszka', 'wiersz', 'esej']
    if any(kw in text_lower for kw in creative_kw):
        return "creative"
    
    # Default
    return "casual"


def format_rich_response(content: str, metadata: dict = None) -> dict:
    """
    Formatuj odpowiedź z bogatym contentem
    
    Zwraca:
        {
            "text": "główna treść",
            "rich": {
                "type": "table|list|code|quote",
                "data": ...
            }
        }
    """
    
    import re
    
    response = {
        "text": content,
        "rich": None
    }
    
    # Wykryj tabele (markdown)
    table_pattern = r'\|.+\|.+\n\|[-:]+\|'
    if re.search(table_pattern, content):
        response["rich"] = {
            "type": "table",
            "detected": True
        }
    
    # Wykryj listy numerowane
    if re.search(r'^\d+\.\s', content, re.MULTILINE):
        response["rich"] = {
            "type": "numbered_list",
            "detected": True
        }
    
    # Wykryj bloki kodu
    if '```' in content:
        code_blocks = re.findall(r'```(\w+)?\n(.*?)```', content, re.DOTALL)
        if code_blocks:
            response["rich"] = {
                "type": "code",
                "blocks": [{"language": lang or "text", "code": code} for lang, code in code_blocks]
            }
    
    # Dodaj metadata
    if metadata:
        response["metadata"] = metadata
    
    return response
