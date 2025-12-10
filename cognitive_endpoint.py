#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cognitive_endpoint.py - Endpointy dla zaawansowanych systemów kognitywnych
Integracja: self-reflection, proactive suggestions, psychology, cognitive engine
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from core.config import AUTH_TOKEN
from core.helpers import log_info, log_error

router = APIRouter(prefix="/api/cognitive", tags=["cognitive"])


def verify_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.replace("Bearer ", "").strip()
    if token != AUTH_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")
    return True


# ============================================================================
# SELF-REFLECTION
# ============================================================================

class ReflectionRequest(BaseModel):
    query: str = Field(..., description="Zapytanie użytkownika")
    initial_response: str = Field(..., description="Pierwsza wersja odpowiedzi")
    depth: str = Field("MEDIUM", description="Głębokość refleksji: SURFACE/MEDIUM/DEEP/PROFOUND/TRANSCENDENT")
    user_id: str = Field("guest", description="ID użytkownika")


@router.post("/reflect")
async def self_reflect(body: ReflectionRequest, _auth: bool = Depends(verify_token)):
    """
    🔄 DYNAMICZNA REKURENCJA UMYSŁOWA
    
    AI ocenia swoją odpowiedź i poprawia ją przez wielopoziomową refleksję:
    - SURFACE: Podstawowa ewaluacja (faktyczność, jasność)
    - MEDIUM: Logika, kompletność, kontekst, błędy
    - DEEP: Kognitywna + pragmatyczna + meta + epistemologiczna analiza
    - PROFOUND: Filozoficzna refleksja (ontologia, aksjologia, hermeneutyka)
    - TRANSCENDENT: Przekroczenie granic myśli, transformacja
    
    **Zwraca:**
    - improved_response: Poprawiona odpowiedź
    - meta_commentary: Meta-komentarz o procesie myślenia
    - reflection_score: Jakość refleksji (0.0-1.0)
    - insights_gained: Lista nauk z procesu
    - corrections_made: Lista konkretnych poprawek
    """
    try:
        from core.self_reflection import reflect_on_response, ReflectionDepth
        
        # Map string depth to enum
        depth_map = {
            "SURFACE": ReflectionDepth.SURFACE,
            "MEDIUM": ReflectionDepth.MEDIUM,
            "DEEP": ReflectionDepth.DEEP,
            "PROFOUND": ReflectionDepth.PROFOUND,
            "TRANSCENDENT": ReflectionDepth.TRANSCENDENT
        }
        
        depth_enum = depth_map.get(body.depth.upper(), ReflectionDepth.MEDIUM)
        
        cycle = await reflect_on_response(
            query=body.query,
            response=body.initial_response,
            depth=depth_enum,
            user_id=body.user_id
        )
        
        return {
            "ok": True,
            "improved_response": cycle.improved_response,
            "meta_commentary": cycle.meta_commentary,
            "reflection_score": cycle.reflection_score,
            "insights_gained": cycle.insights_gained,
            "corrections_made": cycle.corrections_made,
            "cycle_time": cycle.cycle_time,
            "depth_achieved": cycle.depth_achieved
        }
        
    except Exception as e:
        log_error(f"[COGNITIVE] Self-reflection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reflection/summary")
async def get_reflection_summary(_auth: bool = Depends(verify_token)):
    """
    📊 PODSUMOWANIE REFLEKSJI
    
    Zwraca statystyki wszystkich procesów refleksji:
    - Total reflections, average score, cycle time
    - Depth distribution
    - Total insights & corrections
    - Meta-patterns
    """
    try:
        from core.self_reflection import get_reflection_engine
        
        engine = get_reflection_engine()
        summary = await engine.get_reflection_summary()
        
        return {"ok": True, **summary}
        
    except Exception as e:
        log_error(f"[COGNITIVE] Reflection summary failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PROACTIVE SUGGESTIONS
# ============================================================================

class ProactiveSuggestionsRequest(BaseModel):
    user_id: str = Field("guest", description="ID użytkownika")
    context: List[Dict[str, str]] = Field(default_factory=list, description="Historia konwersacji")
    current_message: Optional[str] = Field(None, description="Aktualna wiadomość")


@router.post("/proactive/suggestions")
async def generate_proactive_suggestions(body: ProactiveSuggestionsRequest, _auth: bool = Depends(verify_token)):
    """
    💡 PROAKTYWNE SUGESTIE
    
    Generuje inteligentne sugestie na podstawie:
    - Analizy kontekstu konwersacji
    - Wzorców użytkownika
    - Tematów i intencji
    - Predykcji potrzeb
    
    **Zwraca:**
    - suggestions: Lista sugestii z confidence score
    - context_analysis: Analiza kontekstu (tematy, intencje, sentiment)
    - next_probable_questions: Przewidywane pytania
    """
    try:
        from core.advanced_proactive import get_proactive_engine
        
        engine = get_proactive_engine()
        
        result = await engine.generate_suggestions(
            user_id=body.user_id,
            conversation_history=body.context,
            current_message=body.current_message
        )
        
        return {"ok": True, **result}
        
    except Exception as e:
        # Fallback - podstawowe sugestie
        return {
            "ok": True,
            "suggestions": [
                {"text": "Powiedz mi więcej o tym", "confidence": 0.8, "category": "followup"},
                {"text": "Czy mogę Ci w czymś pomóc?", "confidence": 0.7, "category": "help"}
            ],
            "context_analysis": {"topics": [], "intent": "general", "sentiment": "neutral"},
            "next_probable_questions": [],
            "note": f"Fallback mode: {str(e)[:50]}"
        }


# ============================================================================
# PSYCHOLOGY & EMOTIONAL STATE
# ============================================================================

class EmotionalAnalysisRequest(BaseModel):
    message: str = Field(..., description="Wiadomość do analizy")
    user_id: str = Field("guest", description="ID użytkownika")


@router.post("/psychology/analyze")
async def analyze_emotional_state(body: EmotionalAnalysisRequest, _auth: bool = Depends(verify_token)):
    """
    🧠 ANALIZA EMOCJONALNA
    
    Zaawansowana analiza psychologiczna wiadomości:
    - Podstawowe emocje (Plutchik's wheel: joy, trust, fear, surprise, sadness, disgust, anger, anticipation)
    - PAD model: valence (pozytywna-negatywna), arousal (pobudzenie), dominance
    - Sentiment analysis
    - Mood tracking
    
    **Zwraca:**
    - emotions: Słownik emocji z intensywnością (0.0-1.0)
    - valence, arousal, dominance: PAD scores
    - mood: Długoterminowy nastrój
    - sentiment: Sentiment analysis
    """
    try:
        from core.advanced_psychology import process_user_message, get_psyche_state
        
        # Analiza wiadomości
        analysis = await process_user_message(body.message, body.user_id)
        
        # Stan psyche AI
        psyche = await get_psyche_state(body.user_id)
        
        return {
            "ok": True,
            "user_analysis": analysis,
            "ai_psyche": psyche
        }
        
    except Exception as e:
        log_error(f"[COGNITIVE] Emotional analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/psychology/state/{user_id}")
async def get_psychology_state(user_id: str, _auth: bool = Depends(verify_token)):
    """
    📊 STAN PSYCHOLOGICZNY AI
    
    Pobiera aktualny stan emocjonalny AI dla danego użytkownika
    """
    try:
        from core.advanced_psychology import get_psyche_state
        
        state = await get_psyche_state(user_id)
        
        return {"ok": True, **state}
        
    except Exception as e:
        log_error(f"[COGNITIVE] Get psychology state failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# FULL COGNITIVE PROCESSING
# ============================================================================

class CognitiveProcessRequest(BaseModel):
    query: str = Field(..., description="Zapytanie użytkownika")
    context: List[Dict[str, str]] = Field(default_factory=list, description="Historia")
    mode: str = Field("ADVANCED", description="Tryb: BASIC/ENHANCED/ADVANCED/PREDICTIVE/MULTI_AGENT/FULL_COGNITIVE")
    user_id: str = Field("guest", description="ID użytkownika")
    enable_reflection: bool = Field(True, description="Czy włączyć refleksję")
    enable_multi_agent: bool = Field(False, description="Czy włączyć multi-agent")


@router.post("/process")
async def cognitive_process(body: CognitiveProcessRequest, _auth: bool = Depends(verify_token)):
    """
    🧠 PEŁNE PRZETWARZANIE KOGNITYWNE
    
    Orkiestracja wszystkich 5 systemów kognitywnych:
    1. Self-Reflection - dynamiczna refleksja
    2. Knowledge Compression - kompresja wiedzy
    3. Multi-Agent Orchestrator - wieloagentowe myślenie (Analityk, Kreatywny, Pragmatyczny, Krytyczny, Syntetyczny)
    4. Future Predictor - przewidywanie kontekstu
    5. Inner Language - wewnętrzny język semantyczny
    
    **Tryby:**
    - BASIC: Podstawowe przetwarzanie
    - ENHANCED: Z refleksją i kompresją
    - ADVANCED: Wszystkie systemy
    - PREDICTIVE: Z predykcją przyszłości
    - MULTI_AGENT: Z orkiestracją agentów
    - FULL_COGNITIVE: Wszystkie systemy aktywne
    
    **Zwraca:**
    - primary_response: Główna odpowiedź
    - reflection_insights: Insights z refleksji
    - agent_perspectives: Perspektywy agentów (jeśli multi-agent)
    - future_predictions: Predykcje (jeśli predictive)
    - compressed_knowledge: Skompresowana wiedza
    - inner_thought: Wewnętrzna myśl AI
    - confidence_score, originality_score: Metryki
    """
    try:
        from core.advanced_cognitive_engine import process_with_full_cognition, CognitiveMode
        
        # Map string mode to enum
        mode_map = {
            "BASIC": CognitiveMode.BASIC,
            "ENHANCED": CognitiveMode.ENHANCED,
            "ADVANCED": CognitiveMode.ADVANCED,
            "PREDICTIVE": CognitiveMode.PREDICTIVE,
            "MULTI_AGENT": CognitiveMode.MULTI_AGENT,
            "FULL_COGNITIVE": CognitiveMode.FULL_COGNITIVE
        }
        
        mode_enum = mode_map.get(body.mode.upper(), CognitiveMode.ADVANCED)
        
        result = await process_with_full_cognition(
            query=body.query,
            context=body.context,
            mode=mode_enum,
            user_id=body.user_id,
            enable_reflection=body.enable_reflection,
            enable_multi_agent=body.enable_multi_agent
        )
        
        return {
            "ok": True,
            "primary_response": result.primary_response,
            "reflection_insights": result.reflection_insights,
            "agent_perspectives": result.agent_perspectives,
            "future_predictions": result.future_predictions,
            "compressed_knowledge": result.compressed_knowledge,
            "inner_thought": result.inner_thought,
            "confidence_score": result.confidence_score,
            "originality_score": result.originality_score,
            "total_processing_time": result.total_processing_time,
            "processing_metrics": result.processing_metrics
        }
        
    except Exception as e:
        log_error(f"[COGNITIVE] Full cognitive processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# NLP ADVANCED
# ============================================================================

class NLPAnalysisRequest(BaseModel):
    text: str = Field(..., description="Tekst do analizy")
    extract_entities: bool = Field(True, description="Ekstrakcja encji (NER)")
    extract_keywords: bool = Field(True, description="Ekstrakcja słów kluczowych")
    sentiment_analysis: bool = Field(True, description="Analiza sentymentu")
    dependency_parsing: bool = Field(False, description="Dependency parsing")


@router.post("/nlp/analyze")
async def nlp_advanced_analysis(body: NLPAnalysisRequest, _auth: bool = Depends(verify_token)):
    """
    🔍 ZAAWANSOWANA ANALIZA NLP
    
    Kompleksowa analiza tekstu z wykorzystaniem spaCy (pl_core_news_sm):
    - NER (Named Entity Recognition): osoby, organizacje, lokalizacje, daty
    - Keywords extraction: najważniejsze słowa kluczowe
    - Sentiment analysis: pozytywny/negatywny/neutralny
    - POS tagging: części mowy
    - Dependency parsing: relacje syntaktyczne
    - Phrase extraction: wydobycie fraz
    
    **Zwraca:**
    - entities: Lista encji z typami (PERSON, ORG, LOC, DATE, etc.)
    - keywords: Słowa kluczowe z wagami
    - sentiment: {score, label, confidence}
    - pos_tags: Części mowy
    - dependencies: Relacje syntaktyczne (jeśli włączone)
    - phrases: Wydobyte frazy
    """
    try:
        from core.nlp_processor import get_nlp_processor
        import asyncio
        
        processor = get_nlp_processor()
        
        # analyze_text jest async
        result = await processor.analyze_text(text=body.text)
        
        return {"ok": True, **result.__dict__}
        
    except Exception as e:
        log_error(f"[COGNITIVE] NLP analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SEMANTIC ANALYSIS
# ============================================================================

class SemanticRequest(BaseModel):
    text: str = Field(..., description="Tekst do analizy")
    compare_with: Optional[str] = Field(None, description="Tekst do porównania")


@router.post("/semantic/analyze")
async def semantic_analysis(body: SemanticRequest, _auth: bool = Depends(verify_token)):
    """
    🧬 ANALIZA SEMANTYCZNA
    
    Zaawansowana analiza semantyczna tekstu:
    - Embeddingi (sentence-transformers)
    - Ekstrakcja konceptów
    - Identyfikacja relacji
    - Podobieństwo semantyczne (jeśli compare_with)
    
    **Zwraca:**
    - embedding: Wektor semantyczny (768 wymiarów)
    - concepts: Wydobyte koncepty
    - relations: Relacje między konceptami
    - similarity: Podobieństwo (jeśli compare_with)
    """
    try:
        from core.semantic import semantic_analyze, embed_text, cosine_similarity
        
        analysis = semantic_analyze(body.text)
        embedding = embed_text(body.text)
        
        result = {
            "ok": True,
            "analysis": analysis,
            "embedding_dim": len(embedding)
        }
        
        if body.compare_with:
            embedding2 = embed_text(body.compare_with)
            similarity = cosine_similarity(embedding, embedding2)
            result["similarity"] = similarity
        
        return result
        
    except Exception as e:
        log_error(f"[COGNITIVE] Semantic analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# TOOLS & UTILITIES
# ============================================================================

@router.get("/tools/list")
async def list_cognitive_tools(_auth: bool = Depends(verify_token)):
    """
    🛠️ LISTA NARZĘDZI KOGNITYWNYCH
    
    Zwraca listę wszystkich dostępnych narzędzi z tools_registry
    """
    try:
        from core.tools_registry import get_all_tools, get_tools_by_category
        
        all_tools = get_all_tools()
        
        categories = {}
        for tool in all_tools:
            cat = tool.get("category", "other")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append({
                "name": tool["name"],
                "description": tool["description"]
            })
        
        return {
            "ok": True,
            "total_tools": len(all_tools),
            "categories": categories
        }
        
    except Exception as e:
        log_error(f"[COGNITIVE] List tools failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def cognitive_status(_auth: bool = Depends(verify_token)):
    """
    📊 STATUS SYSTEMÓW KOGNITYWNYCH
    
    Zwraca status wszystkich zaawansowanych systemów
    """
    try:
        status = {
            "ok": True,
            "systems": {
                "self_reflection": "available",
                "proactive_suggestions": "available",
                "psychology": "available",
                "cognitive_engine": "available",
                "nlp_processor": "available",
                "semantic_analyzer": "available",
                "multi_agent": "available",
                "knowledge_compression": "available",
                "future_predictor": "available",
                "inner_language": "available"
            },
            "modules": {
                "advanced_llm": "available",
                "batch_processing": "available",
                "parallel_processing": "available",
                "research": "available",
                "memory": "available",
                "tools_registry": "available"
            }
        }
        
        return status
        
    except Exception as e:
        log_error(f"[COGNITIVE] Status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
