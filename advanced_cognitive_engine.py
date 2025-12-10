"""
🔗 INTEGRACJA SYSTEMÓW KOGNITYWNYCH
=================================

Integracja wszystkich 5 zaawansowanych systemów kognitywnych z głównym silnikiem.
Implementacja orchestracji, konfiguracji i sterowania przepływem przetwarzania.

Autor: Zaawansowany System Kognitywny MRD
Data: 15 października 2025
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .config import *
from .llm import get_llm_client
from .memory import get_memory_manager
from .hierarchical_memory import get_hierarchical_memory_system
from .helpers import log_info, log_error, log_warning

# Import wszystkich systemów kognitywnych (opcjonalne - fallback jeśli brak)
try:
    from .self_reflection import get_self_reflection_engine, ReflectionDepth
except ImportError:
    get_self_reflection_engine = None
    ReflectionDepth = None

try:
    from .knowledge_compression import get_knowledge_compressor
except ImportError:
    get_knowledge_compressor = None

try:
    from .multi_agent_orchestrator import get_multi_agent_orchestrator
except ImportError:
    get_multi_agent_orchestrator = None

try:
    from .future_predictor import get_future_predictor, PredictionHorizon
except ImportError:
    get_future_predictor = None
    PredictionHorizon = None

try:
    from .inner_language import get_inner_language_processor
except ImportError:
    get_inner_language_processor = None


class CognitiveMode(Enum):
    """Tryby pracy systemu kognitywnego"""
    BASIC = "basic"                    # Tylko podstawowe przetwarzanie
    ENHANCED = "enhanced"              # Z refleksją i kompresją
    ADVANCED = "advanced"              # Ze wszystkimi systemami
    PREDICTIVE = "predictive"          # Z predykcją przyszłości
    MULTI_AGENT = "multi_agent"        # Z orkiestracją agentów
    FULL_COGNITIVE = "full_cognitive"  # Wszystkie systemy aktywne


class ProcessingStage(Enum):
    """Etapy przetwarzania kognitywnego"""
    INPUT_ANALYSIS = "input_analysis"
    INNER_LANGUAGE = "inner_language"
    MEMORY_SEARCH = "memory_search"
    KNOWLEDGE_COMPRESSION = "knowledge_compression"
    MULTI_AGENT = "multi_agent"
    RESPONSE_GENERATION = "response_generation"
    SELF_REFLECTION = "self_reflection"
    FUTURE_PREDICTION = "future_prediction"
    OUTPUT_SYNTHESIS = "output_synthesis"


@dataclass
class CognitiveResult:
    """Wynik przetwarzania kognitywnego"""
    primary_response: str
    reflection_insights: List[Dict[str, Any]]
    agent_perspectives: List[Dict[str, Any]]
    future_predictions: List[Dict[str, Any]]
    compressed_knowledge: Dict[str, Any]
    inner_thought: Dict[str, Any]
    processing_metrics: Dict[str, float]
    confidence_score: float
    originality_score: float
    total_processing_time: float


class AdvancedCognitiveEngine:
    """
    🧠 Zaawansowany Silnik Kognitywny
    
    Orkiestracja wszystkich 5 systemów kognitywnych:
    1. Self-Reflection Engine - dynamiczna refleksja
    2. Knowledge Compression - kompresja i transfer learning  
    3. Multi-Agent Orchestrator - wieloagentowe myślenie
    4. Future Predictor - przewidywanie kontekstu
    5. Inner Language - wewnętrzny język semantyczny
    """
    
    def __init__(self):
        self.llm_client = get_llm_client()
        self.memory = get_memory_manager()
        self.hierarchical_memory = get_hierarchical_memory_system()
        
        # Inicjalizacja systemów kognitywnych (z fallbackiem jeśli brak)
        self.self_reflection = get_self_reflection_engine() if get_self_reflection_engine else None
        self.knowledge_compressor = get_knowledge_compressor() if get_knowledge_compressor else None
        self.multi_agent = get_multi_agent_orchestrator() if get_multi_agent_orchestrator else None
        self.future_predictor = get_future_predictor() if get_future_predictor else None
        self.inner_language = get_inner_language_processor() if get_inner_language_processor else None
        
        # Konfiguracja
        self.default_mode = CognitiveMode.ENHANCED
        self.enable_caching = True
        self.parallel_processing = True
        self.adaptive_depth = True
        
        # Metryki
        self.processing_stats = {
            "total_requests": 0,
            "avg_processing_time": 0.0,
            "cache_hit_rate": 0.0,
            "reflection_improvements": 0,
            "prediction_accuracy": 0.0,
            "knowledge_synthesis_count": 0,
            "multi_agent_consensus_rate": 0.0
        }
        
        log_info("[COGNITIVE_ENGINE] Zaawansowany silnik kognitywny zainicjalizowany")
    
    async def process_message(
        self,
        user_message: str,
        user_id: str,
        conversation_context: List[Dict[str, Any]] = None,
        cognitive_mode: CognitiveMode = None,
        enable_prediction: bool = True,
        reflection_depth: ReflectionDepth = None,
        custom_agents: List[str] = None
    ) -> CognitiveResult:
        """
        Główna funkcja przetwarzania wiadomości przez wszystkie systemy kognitywne
        """
        
        start_time = time.time()
        processing_metrics: Dict[str, float] = {}
        
        try:
            # Ustaw domyślny tryb
            if cognitive_mode is None:
                cognitive_mode = self.default_mode
            
            log_info(f"[COGNITIVE_ENGINE] Przetwarzanie w trybie: {cognitive_mode.value}")
            
            # ETAP 1: Analiza input i konwersja na język wewnętrzny
            stage_start = time.time()
            inner_thought = await self._process_inner_language(user_message, conversation_context)
            processing_metrics["inner_language_time"] = time.time() - stage_start
            
            # ETAP 2: Wyszukiwanie w pamięci z kompresją wiedzy
            stage_start = time.time()
            memory_context, compressed_knowledge = await self._enhanced_memory_search(
                user_message, user_id, inner_thought
            )
            processing_metrics["memory_search_time"] = time.time() - stage_start
            
            # ETAP 3: Sprawdź predykcje z cache (jeśli włączone)
            prediction_hit = None
            if (
                enable_prediction 
                and cognitive_mode in [CognitiveMode.PREDICTIVE, CognitiveMode.FULL_COGNITIVE]
                and self.future_predictor is not None
            ):
                prediction_hit = await self.future_predictor.check_prediction_hit(user_id, user_message)
                if prediction_hit:
                    log_info("[COGNITIVE_ENGINE] 🎯 PREDICTION HIT - używam przygotowanej odpowiedzi")
            
            # ETAP 4: Generacja odpowiedzi (podstawowa lub z cache)
            stage_start = time.time()
            if prediction_hit and getattr(prediction_hit, "preparation_confidence", 0) > 0.7:
                primary_response = prediction_hit.prepared_content
                processing_metrics["response_generation_time"] = 0.01  # Cache hit
            else:
                primary_response = await self._generate_enhanced_response(
                    user_message, memory_context, compressed_knowledge, inner_thought, cognitive_mode
                )
                processing_metrics["response_generation_time"] = time.time() - stage_start
            
            # ETAP 5: Wieloagentowa analiza (jeśli włączona)
            agent_perspectives: List[Dict[str, Any]] = []
            if (
                cognitive_mode in [CognitiveMode.MULTI_AGENT, CognitiveMode.FULL_COGNITIVE]
                and self.multi_agent is not None
            ):
                stage_start = time.time()
                agent_perspectives = await self._orchestrate_multi_agent_analysis(
                    user_message, primary_response, conversation_context, custom_agents
                )
                processing_metrics["multi_agent_time"] = time.time() - stage_start
            
            # ETAP 6: Self-reflection i poprawa (jeśli włączona)
            reflection_insights: List[Dict[str, Any]] = []
            final_response = primary_response
            
            if (
                cognitive_mode in [CognitiveMode.ENHANCED, CognitiveMode.ADVANCED, CognitiveMode.FULL_COGNITIVE]
                and self.self_reflection is not None
            ):
                stage_start = time.time()
                
                # Adaptacyjna głębokość refleksji
                if ReflectionDepth is not None:
                    if reflection_depth is None:
                        reflection_depth = await self._determine_reflection_depth(
                            user_message, primary_response, cognitive_mode
                        )
                    
                    reflection_result = await self.self_reflection.reflect_on_response(
                        original_query=user_message,
                        initial_response=primary_response,
                        context=conversation_context or [],
                        depth=reflection_depth,
                        agent_feedback=agent_perspectives
                    )
                    
                    reflection_insights = reflection_result.get("insights", [])
                    improved_response = reflection_result.get("improved_response")
                    
                    if improved_response and len(improved_response) > len(primary_response) * 0.8:
                        final_response = improved_response
                        self.processing_stats["reflection_improvements"] += 1
                
                processing_metrics["reflection_time"] = time.time() - stage_start
            
            # ETAP 7: Predykcja przyszłych zapytań (jeśli włączona)
            future_predictions: List[Dict[str, Any]] = []
            if (
                enable_prediction 
                and cognitive_mode in [CognitiveMode.PREDICTIVE, CognitiveMode.FULL_COGNITIVE]
                and self.future_predictor is not None
            ):
                stage_start = time.time()
                future_predictions = await self._generate_future_predictions(
                    user_id, user_message, conversation_context
                )
                processing_metrics["future_prediction_time"] = time.time() - stage_start
            
            # ETAP 8: Oblicz metryki końcowe
            confidence_score = await self._calculate_overall_confidence(
                final_response, reflection_insights, agent_perspectives, compressed_knowledge
            )
            
            originality_score = await self._calculate_originality_score(
                inner_thought, compressed_knowledge, agent_perspectives
            )
            
            total_time = time.time() - start_time
            processing_metrics["total_time"] = total_time
            
            # ETAP 9: Aktualizuj statystyki
            await self._update_processing_stats(total_time, confidence_score, len(future_predictions))
            
            # Stwórz wynik
            result = CognitiveResult(
                primary_response=final_response,
                reflection_insights=reflection_insights,
                agent_perspectives=agent_perspectives,
                future_predictions=future_predictions,
                compressed_knowledge=compressed_knowledge,
                inner_thought={
                    "token_chain": getattr(inner_thought, "token_chain", []) if inner_thought else [],
                    "compression_level": getattr(inner_thought, "compression_level", 0.0) if inner_thought else 0.0,
                    "confidence": getattr(inner_thought, "confidence", 0.5) if inner_thought else 0.5,
                    "originality": getattr(inner_thought, "originality", 0.5) if inner_thought else 0.5,
                },
                processing_metrics=processing_metrics,
                confidence_score=confidence_score,
                originality_score=originality_score,
                total_processing_time=total_time
            )
            
            log_info(f"[COGNITIVE_ENGINE] Przetwarzanie zakończone: {total_time:.2f}s, confidence: {confidence_score:.2f}")
            return result
            
        except Exception as e:
            log_error(f"[COGNITIVE_ENGINE] Błąd przetwarzania kognitywnego: {e}")
            return await self._create_fallback_result(user_message)
    
    async def _process_inner_language(
        self, 
        user_message: str, 
        conversation_context: List[Dict[str, Any]] = None
    ):
        """Przetwórz wiadomość na język wewnętrzny"""
        
        context_data = {
            "conversation_length": len(conversation_context) if conversation_context else 0,
            "recent_topics": [msg.get("content", "")[:100] for msg in (conversation_context or [])[-3:]],
            "message_type": "question" if "?" in user_message else "statement"
        }
        
        # Fallback if inner_language is None
        if self.inner_language:
            return await self.inner_language.process_natural_language_input(user_message, context_data)
        else:
            # Basic fallback processing
            return {
                "analyzed_intent": "general_query",
                "tokens": user_message.split(),
                "sentiment": "neutral",
                "entities": [],
                "context_aware": False
            }
    
    async def _enhanced_memory_search(
        self, 
        user_message: str, 
        user_id: str,
        inner_thought
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Rozszerzone wyszukiwanie w pamięci z kompresją wiedzy"""
        
        # Standardowe wyszukiwanie w pamięci
        memory_results = await self.hierarchical_memory.search_hybrid(
            query=user_message,
            user_id=user_id,
            max_results=10
        )
        
        # Kompresja i synteza wiedzy
        if len(memory_results) > 3 and self.knowledge_compressor:
            conversations = []
            for result in memory_results:
                if result.get("conversation_context"):
                    conversations.append({
                        "messages": result["conversation_context"],
                        "timestamp": result.get("timestamp", datetime.now()),
                        "user_id": user_id
                    })
            
            try:
                compressed_knowledge = await self.knowledge_compressor.compress_conversations(
                    conversations, user_id
                )
                
                if len(conversations) > 1:
                    synthesized = await self.knowledge_compressor.synthesize_new_knowledge(
                        compressed_knowledge.get("knowledge_vectors", []),
                        user_id,
                        current_topic=user_message[:100]
                    )
                    compressed_knowledge.update(synthesized)
            except Exception as e:
                log_warning(f"[COGNITIVE_ENGINE] Knowledge compression failed: {e}")
                compressed_knowledge = {}
        else:
            compressed_knowledge = {}
        
        return memory_results, compressed_knowledge
    
    async def _generate_enhanced_response(
        self,
        user_message: str,
        memory_context: List[Dict[str, Any]],
        compressed_knowledge: Dict[str, Any],
        inner_thought,
        cognitive_mode: CognitiveMode
    ) -> str:
        """Generuj ulepszoną odpowiedź z pełnym kontekstem"""
        
        context_elements: List[str] = []
        
        # Dodaj compressed knowledge
        if compressed_knowledge.get("compressed_themes"):
            context_elements.append(
                f"Skompresowane tematy: {', '.join(compressed_knowledge['compressed_themes'][:5])}"
            )
        
        if compressed_knowledge.get("thinking_patterns"):
            patterns = compressed_knowledge["thinking_patterns"]
            if patterns:
                context_elements.append(f"Wzorce myślowe: {patterns[0].get('description', '')}")
        
        # Dodaj inner language insights
        if inner_thought:
            compression = getattr(inner_thought, "compression_level", 0.0)
            try:
                context_elements.append(f"Kompresja myśli: {float(compression):.2f}")
            except Exception:
                context_elements.append("Kompresja myśli: N/D")
            
            if getattr(inner_thought, "confidence", 0.5) > 0.7:
                context_elements.append("Wysoka pewność interpretacji")
        
        # Dodaj memory context (skrócony)
        if memory_context:
            relevant_memories = [mem.get("content", "")[:200] for mem in memory_context[:3]]
            context_elements.append(f"Pamięć kontekstowa: {'; '.join(relevant_memories)}")
        
        enhanced_prompt = f"""
Odpowiedz na zapytanie użytkownika, wykorzystując dostępny kontekst.

ZAPYTANIE: {user_message}

KONTEKST KOGNITYWNY:
{chr(10).join(f"- {element}" for element in context_elements)}

TRYB PRZETWARZANIA: {cognitive_mode.value}

Wytyczne odpowiedzi:
1. Wykorzystaj wszystkie dostępne informacje kontekstowe.
2. Dostosuj szczegółowość do trybu kognitywnego.
3. Zachowaj naturalność i płynność odpowiedzi.
4. Bądź konkretny i praktyczny.

Odpowiedź:
""".strip()
        
        system_msg = (
            f"Jesteś zaawansowanym asystentem AI z możliwościami kognitywnego przetwarzania "
            f"w trybie {cognitive_mode.value}. Wykorzystujesz kontekst z pamięci, kompresji wiedzy "
            f"i analizy wewnętrznego języka. Odpowiadasz po polsku."
        )
        
        try:
            # Spróbuj użyć klienta LLM z metodą chat_completion
            if self.llm_client is None or not hasattr(self.llm_client, "chat_completion"):
                raise RuntimeError("LLM client nie ma metody chat_completion")
            
            messages = [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": enhanced_prompt},
            ]
            
            chat_fn = self.llm_client.chat_completion
            
            # Jeśli to funkcja asynchroniczna
            if asyncio.iscoroutinefunction(chat_fn):
                response = await chat_fn(messages)
            else:
                # Synchroniczna – odpal w executorze, żeby nie blokować event loopa
                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(None, chat_fn, messages)
            
            return response
        
        except Exception as e:
            log_error(f"[COGNITIVE_ENGINE] Błąd generacji odpowiedzi z llm_client: {e} – fallback do call_llm")
            # Fallback: klasyczny call_llm, który wiemy, że działa
            try:
                from .llm import call_llm
                
                fallback_response = call_llm(
                    prompt=enhanced_prompt,
                    system_prompt=system_msg,
                    max_tokens=800
                )
                return fallback_response
            except Exception as inner_e:
                log_error(f"[COGNITIVE_ENGINE] Fallback call_llm też się wywalił: {inner_e}")
                return (
                    "Przepraszam, wystąpił błąd podczas przetwarzania Twojego zapytania. "
                    f"Treść zapytania: {user_message}"
                )
    
    async def _orchestrate_multi_agent_analysis(
        self,
        user_message: str,
        primary_response: str,
        conversation_context: List[Dict[str, Any]],
        custom_agents: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Orkiestruj analizę wieloagentową"""
        
        if self.multi_agent is None:
            return []
        
        try:
            result = await self.multi_agent.orchestrate_multi_agent_response(
                user_query=user_message,
                initial_response=primary_response,
                conversation_context=conversation_context or [],
                custom_agents=custom_agents
            )
            return result.get("agent_responses", [])
        except Exception as e:
            log_error(f"[COGNITIVE_ENGINE] Błąd analizy wieloagentowej: {e}")
            return []
    
    async def _determine_reflection_depth(
        self,
        user_message: str,
        primary_response: str,
        cognitive_mode: CognitiveMode
    ):
        """Określ adaptacyjną głębokość refleksji"""
        
        if ReflectionDepth is None:
            return None
        
        base_depths = {
            CognitiveMode.BASIC: ReflectionDepth.SURFACE,
            CognitiveMode.ENHANCED: ReflectionDepth.MEDIUM,
            CognitiveMode.ADVANCED: ReflectionDepth.DEEP,
            CognitiveMode.PREDICTIVE: ReflectionDepth.DEEP,
            CognitiveMode.MULTI_AGENT: ReflectionDepth.PROFOUND,
            CognitiveMode.FULL_COGNITIVE: ReflectionDepth.TRANSCENDENT,
        }
        
        base_depth = base_depths.get(cognitive_mode, ReflectionDepth.MEDIUM)
        depth_modifiers = 0
        
        if len(user_message) > 100:
            depth_modifiers += 1
        if "?" in user_message:
            depth_modifiers += 1
        if any(word in user_message.lower() for word in ["dlaczego", "jak", "w jaki sposób", "wyjaśnij"]):
            depth_modifiers += 1
        
        if len(primary_response) > 500:
            depth_modifiers += 1
        
        deep_keywords = ["etyka", "filozofia", "moralność", "znaczenie", "sens", "wartości", "przekonania"]
        if any(keyword in user_message.lower() for keyword in deep_keywords):
            depth_modifiers += 2
        
        depth_levels = list(ReflectionDepth)
        current_index = depth_levels.index(base_depth)
        new_index = min(current_index + depth_modifiers, len(depth_levels) - 1)
        
        return depth_levels[new_index]
    
    async def _generate_future_predictions(
        self,
        user_id: str,
        user_message: str,
        conversation_context: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generuj predykcje przyszłych zapytań"""
        
        if self.future_predictor is None or PredictionHorizon is None:
            return []
        
        try:
            immediate_predictions = await self.future_predictor.predict_user_intentions(
                user_id, user_message, conversation_context, PredictionHorizon.IMMEDIATE
            )
            
            short_term_predictions = await self.future_predictor.predict_user_intentions(
                user_id, user_message, conversation_context, PredictionHorizon.SHORT_TERM
            )
            
            all_predictions: List[Dict[str, Any]] = []
            
            for prediction in immediate_predictions[:3]:
                all_predictions.append({
                    "query": prediction.predicted_query,
                    "confidence": prediction.confidence,
                    "horizon": "immediate",
                    "triggers": prediction.context_triggers
                })
            
            for prediction in short_term_predictions[:3]:
                all_predictions.append({
                    "query": prediction.predicted_query,
                    "confidence": prediction.confidence,
                    "horizon": "short_term",
                    "triggers": prediction.context_triggers
                })
            
            return all_predictions
            
        except Exception as e:
            log_error(f"[COGNITIVE_ENGINE] Błąd predykcji przyszłości: {e}")
            return []
    
    async def _calculate_overall_confidence(
        self,
        final_response: str,
        reflection_insights: List[Dict[str, Any]],
        agent_perspectives: List[Dict[str, Any]],
        compressed_knowledge: Dict[str, Any]
    ) -> float:
        """Oblicz ogólną pewność wyniku"""
        
        confidence = 0.0
        
        if len(final_response) > 100:
            confidence += 0.3
        
        if reflection_insights:
            reflection_confidence = sum(
                insight.get("confidence", 0.5) for insight in reflection_insights
            ) / len(reflection_insights)
            confidence += reflection_confidence * 0.3
        
        if agent_perspectives:
            agent_confidence = sum(
                perspective.get("confidence", 0.5) for perspective in agent_perspectives
            ) / len(agent_perspectives)
            confidence += agent_confidence * 0.2
        
        if compressed_knowledge.get("knowledge_vectors"):
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    async def _calculate_originality_score(
        self,
        inner_thought,
        compressed_knowledge: Dict[str, Any],
        agent_perspectives: List[Dict[str, Any]]
    ) -> float:
        """Oblicz oryginalność odpowiedzi"""
        
        originality = 0.0
        
        if inner_thought and hasattr(inner_thought, "originality"):
            originality += getattr(inner_thought, "originality", 0.0) * 0.4
        
        if compressed_knowledge.get("synthetic_memories"):
            originality += 0.3
        
        if len(agent_perspectives) > 3:
            originality += 0.3
        
        return min(originality, 1.0)
    
    async def _update_processing_stats(
        self,
        processing_time: float,
        confidence_score: float,
        predictions_count: int
    ):
        """Aktualizuj statystyki przetwarzania"""
        
        self.processing_stats["total_requests"] += 1
        
        current_avg = self.processing_stats["avg_processing_time"]
        total_requests = self.processing_stats["total_requests"]
        self.processing_stats["avg_processing_time"] = (
            (current_avg * (total_requests - 1) + processing_time) / total_requests
        )
        
        if predictions_count > 0:
            self.processing_stats["prediction_accuracy"] = (
                self.processing_stats["prediction_accuracy"] * 0.9 + confidence_score * 0.1
            )
    
    async def _create_fallback_result(self, user_message: str) -> CognitiveResult:
        """Stwórz podstawowy wynik w przypadku grubszego błędu - używa plain LLM"""
        
        try:
            from .llm import call_llm
            fallback_response = call_llm(
                prompt=user_message,
                system_prompt=(
                    "Jesteś pomocnym asystentem AI. Odpowiadaj po polsku, naturalnie i konkretnie."
                ),
                max_tokens=500
            )
        except Exception as llm_error:
            log_warning(f"[COGNITIVE_ENGINE] Fallback LLM failed: {llm_error}")
            fallback_response = (
                "Nie udało się przetworzyć zapytania. Spróbuj ponownie za chwilę. "
                f"Treść zapytania: {user_message}"
            )
        
        return CognitiveResult(
            primary_response=fallback_response,
            reflection_insights=[],
            agent_perspectives=[],
            future_predictions=[],
            compressed_knowledge={},
            inner_thought={},
            processing_metrics={"total_time": 0.1, "fallback": True},
            confidence_score=0.5,
            originality_score=0.3,
            total_processing_time=0.1
        )
    
    async def get_cognitive_status(self) -> Dict[str, Any]:
        """Pobierz status wszystkich systemów kognitywnych"""
        
        try:
            tasks = []
            
            if self.self_reflection is not None:
                tasks.append(self.self_reflection.get_reflection_report())
            else:
                tasks.append(asyncio.sleep(0, result={"error": "self_reflection not initialized"}))
            
            if self.knowledge_compressor is not None:
                tasks.append(self.knowledge_compressor.get_compression_report())
            else:
                tasks.append(asyncio.sleep(0, result={"error": "knowledge_compressor not initialized"}))
            
            if self.multi_agent is not None:
                tasks.append(self.multi_agent.get_orchestration_report())
            else:
                tasks.append(asyncio.sleep(0, result={"error": "multi_agent not initialized"}))
            
            if self.future_predictor is not None:
                tasks.append(self.future_predictor.get_prediction_report())
            else:
                tasks.append(asyncio.sleep(0, result={"error": "future_predictor not initialized"}))
            
            if self.inner_language is not None:
                tasks.append(self.inner_language.get_inner_language_report())
            else:
                tasks.append(asyncio.sleep(0, result={"error": "inner_language not initialized"}))
            
            reports = await asyncio.gather(*tasks, return_exceptions=True)
            
            status = {
                "cognitive_engine": {
                    "processing_stats": self.processing_stats,
                    "active_systems": sum(
                        1 for r in reports 
                        if isinstance(r, dict) and "error" not in r
                    ),
                    "default_mode": self.default_mode.value
                },
                "self_reflection": reports[0],
                "knowledge_compression": reports[1],
                "multi_agent": reports[2],
                "future_prediction": reports[3],
                "inner_language": reports[4],
            }
            
            return status
            
        except Exception as e:
            log_error(f"[COGNITIVE_ENGINE] Błąd pobierania statusu: {e}")
            return {"error": str(e)}


# Globalna instancja silnika
_advanced_cognitive_engine: Optional[AdvancedCognitiveEngine] = None


def get_advanced_cognitive_engine() -> AdvancedCognitiveEngine:
    """Pobierz globalną instancję zaawansowanego silnika kognitywnego"""
    global _advanced_cognitive_engine
    if _advanced_cognitive_engine is None:
        _advanced_cognitive_engine = AdvancedCognitiveEngine()
    return _advanced_cognitive_engine


# Główne funkcje API
async def process_with_full_cognition(
    user_message: str,
    user_id: str,
    conversation_context: List[Dict[str, Any]] = None,
    mode: str = "enhanced"
) -> Dict[str, Any]:
    """
    Główna funkcja przetwarzania z pełną kognicją
    """
    
    engine = get_advanced_cognitive_engine()
    
    try:
        cognitive_mode = CognitiveMode(mode)
    except ValueError:
        cognitive_mode = CognitiveMode.ENHANCED
    
    result = await engine.process_message(
        user_message=user_message,
        user_id=user_id,
        conversation_context=conversation_context,
        cognitive_mode=cognitive_mode
    )
    
    return {
        "response": result.primary_response,
        "reflection_insights": result.reflection_insights,
        "agent_perspectives": result.agent_perspectives,
        "future_predictions": result.future_predictions,
        "compressed_knowledge": result.compressed_knowledge,
        "inner_thought": result.inner_thought,
        "metrics": {
            "processing_time": result.total_processing_time,
            "confidence": result.confidence_score,
            "originality": result.originality_score,
            **result.processing_metrics
        }
    }


if __name__ == "__main__":
    async def test_advanced_cognitive_engine():
        """Test zaawansowanego silnika kognitywnego"""
        
        test_queries = [
            "Jak działa uczenie maszynowe i czy AI może być kreatywna?",
            "Jakie są etyczne implikacje sztucznej inteligencji?",
            "Pomóż mi zrozumieć różnice między sieciami neuronowymi a tradycyjnymi algorytmami.",
            "Co sądzisz o przyszłości pracy w dobie automatyzacji?"
        ]
        
        print("🧠 TEST ZAAWANSOWANEGO SILNIKA KOGNITYWNEGO")
        print("=" * 70)
        
        engine = get_advanced_cognitive_engine()
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n🎯 TEST {i}: {query}")
            print("-" * 60)
            
            modes = [CognitiveMode.BASIC, CognitiveMode.ENHANCED, CognitiveMode.FULL_COGNITIVE]
            
            for mode in modes:
                print(f"\n📊 TRYB: {mode.value.upper()}")
                
                result = await engine.process_message(
                    user_message=query,
                    user_id=f"test_user_{i}",
                    cognitive_mode=mode
                )
                
                print(f"⏱️  Czas: {result.total_processing_time:.2f}s")
                print(f"🎯 Pewność: {result.confidence_score:.2f}")
                print(f"✨ Oryginalność: {result.originality_score:.2f}")
                print(f"📝 Odpowiedź: {result.primary_response[:100]}...")
                
                if result.reflection_insights:
                    print(f"🔍 Refleksji: {len(result.reflection_insights)}")
                
                if result.agent_perspectives:
                    print(f"👥 Perspektyw agentów: {len(result.agent_perspectives)}")
                
                if result.future_predictions:
                    print(f"🔮 Predykcji: {len(result.future_predictions)}")
        
        print(f"\n📊 STATUS SYSTEMU KOGNITYWNEGO")
        print("-" * 40)
        
        status = await engine.get_cognitive_status()
        
        main_stats = status.get("cognitive_engine", {}).get("processing_stats", {})
        print(f"📈 Zapytania ogółem: {main_stats.get('total_requests', 0)}")
        print(f"⏱️  Średni czas: {main_stats.get('avg_processing_time', 0):.2f}s")
        print(f"🎯 Dokładność predykcji: {main_stats.get('prediction_accuracy', 0):.2f}")
        print(f"🔧 Ulepszeń refleksyjnych: {main_stats.get('reflection_improvements', 0)}")
    
    asyncio.run(test_advanced_cognitive_engine())
