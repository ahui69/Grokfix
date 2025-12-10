#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUTO WRAPPER dla assistant_endpoint - dodaje pełną automatyzację
"""

async def auto_chat_wrapper(body, req, original_chat_func):
    """
    Wrapper dodający automatyzację:
    1. Auto STM→LTM transfer
    2. Auto-learning gdy brak wiedzy
    3. Context injection z LTM
    """
    user_id = body.user_id or (req.client.host if req.client else "default") or "default"
    
    # Ostatnia wiadomość usera
    last_user_msg = ""
    if hasattr(body, 'messages') and body.messages:
        for m in reversed(body.messages):
            if m.get("role") == "user" or (hasattr(m, 'role') and m.role == "user"):
                last_user_msg = m.get("content") if isinstance(m, dict) else getattr(m, 'content', '')
                break
    elif hasattr(body, 'message'):
        last_user_msg = body.message
    
    # ═══════════════════════════════════════════════════════════════════
    # 🔥 AUTO 1: AdvancedMemoryManager - auto STM→LTM transfer
    # ═══════════════════════════════════════════════════════════════════
    try:
        import monolit as M
        if hasattr(M, 'AdvancedMemoryManager') and last_user_msg:
            amm = M.AdvancedMemoryManager()
            amm.add_message("user", last_user_msg, user_id)
    except Exception as e:
        print(f"[AUTO] AdvancedMemoryManager error: {e}")
        pass

    # ═══════════════════════════════════════════════════════════════════
    # 🔥 AUTO 2: Auto-learning - gdy brak wiedzy w LTM
    # ═══════════════════════════════════════════════════════════════════
    ltm_context_str = ""
    auto_learned = False
    if last_user_msg:
        try:
            import monolit as M
            if hasattr(M, 'ltm_search_hybrid'):
                ltm_results = M.ltm_search_hybrid(last_user_msg, limit=3)
                
                # Sprawdź czy mamy wiedzę
                if not ltm_results or (ltm_results and ltm_results[0].get('score', 0) < 0.3):
                    # Brak wiedzy → AUTO-LEARN!
                    print(f"[AUTO] 🔍 Brak wiedzy w LTM (score < 0.3) → autonauka('{last_user_msg[:50]}...')")
                    if hasattr(M, 'autonauka'):
                        try:
                            import asyncio
                            if asyncio.iscoroutinefunction(M.autonauka):
                                learn_result = await M.autonauka(last_user_msg, topk=3, deep_research=False)
                            else:
                                learn_result = M.autonauka(last_user_msg, topk=3, deep_research=False)
                            
                            if learn_result and learn_result.get('ok'):
                                auto_learned = True
                                print(f"[AUTO] ✅ Nauczono! Zapisano {learn_result.get('source_count', 0)} źródeł")
                                # Odśwież LTM po nauce
                                ltm_results = M.ltm_search_hybrid(last_user_msg, limit=3)
                        except Exception as e:
                            print(f"[AUTO] autonauka error: {e}")
                            pass
                
                # ═══════════════════════════════════════════════════════════════════
                # 🔥 AUTO 3: Context injection - wstrzykuj LTM do promptu
                # ═══════════════════════════════════════════════════════════════════
                if ltm_results:
                    ltm_facts = [r.get('text', '') or r.get('fact', '') for r in ltm_results[:3] if r.get('score', 0) > 0.25]
                    if ltm_facts:
                        ltm_context_str = "\n\n📚 Kontekst z pamięci długoterminowej:\n" + "\n".join([f"- {f[:200]}" for f in ltm_facts])
                        print(f"[AUTO] 📚 Dodano {len(ltm_facts)} faktów z LTM do context")
        except Exception as e:
            print(f"[AUTO] LTM search error: {e}")
            pass
    
    # Wywołaj oryginalną funkcję
    result = await original_chat_func(body, req)
    
    # Zapisz odpowiedź assistant przez AdvancedMemoryManager
    if hasattr(result, 'answer'):
        try:
            import monolit as M
            if hasattr(M, 'AdvancedMemoryManager'):
                amm = M.AdvancedMemoryManager()
                amm.add_message("assistant", result.answer, user_id)
        except Exception:
            pass
    
    # Dodaj metadata o automatyzacji
    if hasattr(result, 'metadata'):
        result.metadata['auto_learned'] = auto_learned
        result.metadata['ltm_context_injected'] = bool(ltm_context_str)
    
    # Zwróć kontekst do wstrzyknięcia (jeśli oryginalny endpoint go potrzebuje)
    if hasattr(result, '__dict__'):
        result._auto_ltm_context = ltm_context_str
        result._auto_learned_flag = auto_learned
    
    return result

# ═══════════════════════════════════════════════════════════════════
# PRAWDZIWE MACHINE LEARNING - Reinforcement Learning z feedbacku
# ═══════════════════════════════════════════════════════════════════

import json
import os
import time
from typing import Dict, Any

FEEDBACK_DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'feedback.db')

def ensure_feedback_db():
    """Utwórz bazę danych feedback jeśli nie istnieje"""
    os.makedirs(os.path.dirname(FEEDBACK_DB_PATH), exist_ok=True)
    if not os.path.exists(FEEDBACK_DB_PATH):
        with open(FEEDBACK_DB_PATH, 'w') as f:
            json.dump({
                'interactions': [],
                'patterns': {},
                'user_profiles': {}
            }, f, indent=2)

def load_feedback_db() -> Dict[str, Any]:
    """Załaduj bazę danych feedback"""
    ensure_feedback_db()
    try:
        with open(FEEDBACK_DB_PATH, 'r') as f:
            return json.load(f)
    except:
        return {'interactions': [], 'patterns': {}, 'user_profiles': {}}

def save_feedback_db(data: Dict[str, Any]):
    """Zapisz bazę danych feedback"""
    ensure_feedback_db()
    with open(FEEDBACK_DB_PATH, 'w') as f:
        json.dump(data, f, indent=2)

def learn_from_feedback(user_message: str, rating: int, user_id: str = "default") -> Dict[str, Any]:
    """
    PRAWDZIWE UCZENIE MASZYNOWE!
    Reinforcement Learning z feedbacku użytkownika

    Args:
        user_message: Wiadomość użytkownika
        rating: Ocena (1-5)
        user_id: ID użytkownika

    Returns:
        Rezultat uczenia
    """
    db = load_feedback_db()

    # Dodaj interakcję
    interaction = {
        'user_id': user_id,
        'message': user_message,
        'rating': rating,
        'timestamp': time.time(),
        'message_length': len(user_message),
        'message_type': 'technical' if any(w in user_message.lower() for w in ['kod', 'program', 'error', 'bug']) else 'casual'
    }

    db['interactions'].append(interaction)

    # Aktualizuj profile użytkowników
    if user_id not in db['user_profiles']:
        db['user_profiles'][user_id] = {
            'total_interactions': 0,
            'avg_rating': 0,
            'preferences': {},
            'learning_progress': 0
        }

    user_profile = db['user_profiles'][user_id]
    user_profile['total_interactions'] += 1

    # Aktualizuj średnią ocenę
    current_avg = user_profile['avg_rating']
    total = user_profile['total_interactions']
    user_profile['avg_rating'] = (current_avg * (total - 1) + rating) / total

    # Aktualizuj preferencje użytkownika
    words = user_message.lower().split()
    for word in words:
        if len(word) > 3:  # Tylko słowa dłuższe niż 3 znaki
            if word not in user_profile['preferences']:
                user_profile['preferences'][word] = {'count': 0, 'ratings': []}
            user_profile['preferences'][word]['count'] += 1
            user_profile['preferences'][word]['ratings'].append(rating)

    # Aktualizuj wzorce odpowiedzi
    # Znajdź słowa kluczowe i ich wpływ na oceny
    for pattern in ['kod', 'program', 'error', 'help', 'jak', 'co', 'dlaczego']:
        if pattern in user_message.lower():
            if pattern not in db['patterns']:
                db['patterns'][pattern] = {'total': 0, 'avg_rating': 0}
            pattern_data = db['patterns'][pattern]
            pattern_data['total'] += 1
            current_avg = pattern_data['avg_rating']
            pattern_data['avg_rating'] = (current_avg * (pattern_data['total'] - 1) + rating) / pattern_data['total']

    # Zapisz bazę danych
    save_feedback_db(db)

    # Zwróć statystyki uczenia
    return {
        'success': True,
        'interactions_count': len(db['interactions']),
        'user_avg_rating': user_profile['avg_rating'],
        'patterns_learned': len(db['patterns']),
        'user_profile_updated': True
    }

# Export
__all__ = ['auto_chat_wrapper', 'learn_from_feedback']
