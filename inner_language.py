"""
🧠 WŁASNY JĘZYK WEWNĘTRZNY (Inner Language Code)
==============================================

Ostatni element zaawansowanej architektury kognitywnej - wewnętrzny język semantyczny
dla szybszego przetwarzania myśli i lepszych skojarzeń kontekstowych.

Autor: Zaawansowany System Kognitywny MRD
Data: 15 października 2025
"""

import asyncio
import json
import time
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from enum import Enum
import hashlib
import math
from itertools import combinations

from .config import *
from .llm import get_llm_client
from .memory import get_memory_manager
from .hierarchical_memory import get_hierarchical_memory
from .helpers import log_info, log_error, log_warning

class TokenType(Enum):
    """Typy tokenów w języku wewnętrznym"""
    CONCEPT = "concept"         # Pojęcie abstrakcyjne
    ENTITY = "entity"           # Konkretna jednostka
    RELATION = "relation"       # Relacja między elementami
    ACTION = "action"           # Akcja/czasownik
    PROPERTY = "property"       # Właściwość/cecha
    EMOTION = "emotion"         # Stan emocjonalny
    META = "meta"              # Meta-informacja
    PATTERN = "pattern"         # Wzorzec myślowy

class SemanticDimension(Enum):
    """Wymiary semantyczne tokenów"""
    ABSTRACTION = "abstraction"     # Poziom abstrakcji (0-1)
    CERTAINTY = "certainty"         # Pewność (0-1)
    IMPORTANCE = "importance"       # Ważność (0-1)
    TEMPORALITY = "temporality"     # Czasowość (-1 przeszłość, 0 teraź, 1 przyszłość)
    EMOTIONALITY = "emotionality"   # Nacechowanie emocjonalne (-1 do 1)
    COMPLEXITY = "complexity"       # Złożoność pojęciowa (0-1)
    NOVELTY = "novelty"            # Nowość (0-1)

@dataclass
class InnerToken:
    """Token w języku wewnętrznym"""
    token_id: str
    surface_form: str           # Forma powierzchniowa w języku naturalnym
    semantic_core: str          # Rdzeń semantyczny
    token_type: TokenType
    dimensions: Dict[SemanticDimension, float]
    associations: List[str]     # ID powiązanych tokenów
    activation_level: float     # Poziom aktywacji (0-1)
    creation_time: datetime
    usage_count: int
    context_patterns: List[str] # Wzorce kontekstów użycia
    compression_ratio: float    # Stosunek kompresji vs pełna forma

@dataclass
class SemanticCluster:
    """Klaster semantyczny tokenów"""
    cluster_id: str
    core_tokens: List[str]      # ID tokenów centralnych
    peripheral_tokens: List[str] # ID tokenów peryferyjnych
    cluster_theme: str          # Główny temat klastra
    coherence_score: float      # Spójność klastra (0-1)
    activation_history: List[Tuple[datetime, float]]
    inter_cluster_links: Dict[str, float]  # Linki do innych klastrów

@dataclass
class ThoughtPattern:
    """Wzorzec myślowy"""
    pattern_id: str
    token_sequence: List[str]   # Sekwencja tokenów
    trigger_conditions: List[str]
    completion_probability: float
    usage_frequency: float
    effectiveness_score: float
    context_specificity: float

@dataclass
class InnerThought:
    """Myśl w języku wewnętrznym"""
    thought_id: str
    token_chain: List[str]      # Łańcuch tokenów
    semantic_vector: List[float] # Wektor semantyczny
    compression_level: float    # Poziom kompresji (0-1)
    processing_time: float      # Czas przetwarzania
    confidence: float           # Pewność myśli
    originality: float          # Oryginalność
    surface_translation: str    # Tłumaczenie na język naturalny
    
    def get(self, key: str, default=None):
        """Dict-like access for backward compatibility"""
        return getattr(self, key, default)

class InnerLanguageProcessor:
    """
    🧠 Procesor Własnego Języka Wewnętrznego
    
    Implementuje zaawansowany system językowy dla wewnętrznego przetwarzania:
    - Tworzenie semantycznych tokenów i klastrów
    - Kompresja myśli do form symbolicznych
    - Szybkie kojarzenia i pattern matching
    - Meta-językowe refleksje nad własnym myśleniem
    """
    
    def __init__(self):
        self.llm_client = get_llm_client()
        self.memory = get_memory_manager()
        self.hierarchical_memory = get_hierarchical_memory()
        
        # Słownik tokenów
        self.token_dictionary: Dict[str, InnerToken] = {}
        
        # Klastry semantyczne
        self.semantic_clusters: Dict[str, SemanticCluster] = {}
        
        # Wzorce myślowe
        self.thought_patterns: Dict[str, ThoughtPattern] = {}
        
        # Historia myśli
        self.thought_history: deque = deque(maxlen=1000)
        
        # Sieci skojarzeniowe
        self.association_network: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        
        # Parametry systemu
        self.min_token_frequency = 3      # Min częstotliwość dla zachowania tokena
        self.max_tokens = 10000          # Max tokenów w słowniku
        self.cluster_threshold = 0.7     # Próg podobieństwa dla klastrowania
        self.activation_decay = 0.9      # Tempo zanikania aktywacji
        self.compression_target = 0.3    # Docelowy poziom kompresji
        
        # Metryki wydajności
        self.performance_metrics = {
            "compression_ratio": 0.0,
            "association_speed": 0.0,
            "pattern_recognition_accuracy": 0.0,
            "translation_quality": 0.0,
            "total_tokens": 0,
            "active_clusters": 0,
            "thoughts_processed": 0
        }
        
        log_info("[INNER_LANGUAGE] Procesor Własnego Języka Wewnętrznego zainicjalizowany")
    
    async def process_natural_language_input(
        self,
        text: str,
        context: Dict[str, Any] = None
    ) -> InnerThought:
        """
        INTELIGENTNE przetwarzanie - zachowaj LLM ale zoptymalizuj dla real-time
        """

        try:
            start_time = time.time()

            # FAST CACHE CHECK - jeśli już przetworzyliśmy podobne
            cache_key = hash(text[:50]) % 1000
            if hasattr(self, '_thought_cache') and cache_key in self._thought_cache:
                cached = self._thought_cache[cache_key]
                if cached['text'][:50] == text[:50]:  # Dokładne dopasowanie początku
                    return cached['thought']

            # SZYBKA TOKENIZACJA jako baza
            words = text.lower().split()
            base_tokens = [f"WORD_{word[:8]}" for word in words[:8]]

            # LLM tylko dla KLUCZOWYCH słów - nie dla całego tekstu!
            key_words = [word for word in words if len(word) > 3][:5]  # Max 5 słów

            if key_words:
                # MINI LLM CALL - tylko dla kluczowych słów
                mini_prompt = f"Kluczowe aspekty: {', '.join(key_words)}. Podaj 3 główne kategorie znaczeniowe."

                try:
                    mini_response = await self.llm_client.chat_completion([{
                        "role": "system",
                        "content": "Jesteś szybkim analizatorem semantycznym. Odpowiadaj bardzo krótko."
                    }, {
                        "role": "user",
                        "content": mini_prompt
                    }], timeout=1.0)  # Timeout 1 sekunda!

                    # Parsuj kategorie
                    categories = mini_response.split(',')[:3]
                    enhanced_tokens = base_tokens[:5]  # Zachowaj podstawę

                    # Dodaj kategorie jako tokeny
                    for cat in categories:
                        cat_clean = cat.strip()[:10]
                        if cat_clean:
                            enhanced_tokens.append(f"CAT_{cat_clean}")

                except Exception:
                    # Fallback do podstawowej tokenizacji
                    enhanced_tokens = base_tokens
            else:
                enhanced_tokens = base_tokens

            # WEKTOR SEMANTYCZNY - mieszanka hash + kategorie
            semantic_vector = []

            # Hash słów
            for word in words[:6]:
                semantic_vector.append(hash(word) % 100 / 100.0)

            # Hash kategorii jeśli są
            for token in enhanced_tokens[-3:]:
                semantic_vector.append(hash(token) % 100 / 100.0)

            # Wypełnij do 64
            while len(semantic_vector) < 64:
                semantic_vector.append(0.5)

            semantic_vector = semantic_vector[:64]

            thought = InnerThought(
                thought_id=hashlib.md5(f"{text}_{time.time()}".encode()).hexdigest()[:12],
                token_chain=enhanced_tokens,
                semantic_vector=semantic_vector,
                compression_level=len(enhanced_tokens) / len(words) if words else 1.0,
                processing_time=time.time() - start_time,
                confidence=0.9,  # Wyższa pewność dzięki LLM
                originality=0.6,  # Średnia oryginalność
                surface_translation=text
            )

            # CACHE dla przyszłych wywołań
            if not hasattr(self, '_thought_cache'):
                self._thought_cache = {}
            self._thought_cache[cache_key] = {
                'text': text,
                'thought': thought,
                'timestamp': time.time()
            }

            # Oczyść stary cache (max 1000 wpisów)
            if len(self._thought_cache) > 1000:
                oldest_keys = sorted(self._thought_cache.keys(),
                                   key=lambda k: self._thought_cache[k]['timestamp'])[:100]
                for key in oldest_keys:
                    del self._thought_cache[key]

            return thought

        except Exception as e:
            log_error(f"[INNER_LANGUAGE] Błąd: {e}")
            return await self._create_fallback_thought(text)

    async def _analyze_semantic_content(
        self, 
        text: str, 
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Analizuj zawartość semantyczną tekstu"""
        
        analysis_prompt = f"""
        Przeanalizuj semantyczną strukturę następującego tekstu:
        
        TEKST: {text}
        KONTEKST: {json.dumps(context or {}, ensure_ascii=False)}
        
        Zidentyfikuj:
        1. Kluczowe pojęcia (concepts)
        2. Konkretne jednostki (entities)  
        3. Relacje między elementami
        4. Akcje/czasowniki
        5. Właściwości/cechy
        6. Stany emocjonalne
        7. Meta-informacje
        8. Wzorce myślowe
        
        Dla każdego elementu określ wymiary semantyczne:
        - Poziom abstrakcji (0-1)
        - Pewność (0-1)
        - Ważność (0-1)
        - Czasowość (-1 przeszłość, 0 teraź, 1 przyszłość)
        - Nacechowanie emocjonalne (-1 do 1)
        - Złożoność (0-1)
        - Nowość (0-1)
        
        Format JSON:
        {{
          "concepts": [{{"text": "przykład", "dimensions": {{"abstraction": 0.5, "certainty": 0.8}}}},
          "entities": [{{"text": "osoba", "dimensions": {{"abstraction": 0.2, "certainty": 0.9}}}},
          "relations": [],
          "actions": [{{"text": "rozumieć", "dimensions": {{"abstraction": 0.3, "certainty": 0.7}}}},
          "properties": [],
          "emotions": [],
          "meta": [],
          "patterns": []
        }}
        """
        
        try:
            analysis_response = await self.llm_client.chat_completion([{
                "role": "system",
                "content": "Jesteś ekspertem w analizie semantycznej. Analizujesz strukturę znaczeniową tekstów."
            }, {
                "role": "user", 
                "content": analysis_prompt
            }])
            
            # Parsuj JSON
            try:
                # Usuń markdown code blocks jeśli są
                clean_response = analysis_response.strip()
                if clean_response.startswith('```json'):
                    clean_response = clean_response[7:]
                if clean_response.startswith('```'):
                    clean_response = clean_response[3:]
                if clean_response.endswith('```'):
                    clean_response = clean_response[:-3]
                clean_response = clean_response.strip()
                
                analysis = json.loads(clean_response)
                
                # Dodatkowa walidacja struktury JSON
                if not isinstance(analysis, dict):
                    raise ValueError("Odpowiedź nie jest obiektem JSON")
                
                # Sprawdź czy zawiera wymagane klucze
                required_keys = ["concepts", "entities", "actions"]
                if not any(key in analysis for key in required_keys):
                    raise ValueError("Brak wymaganych kluczy w odpowiedzi JSON")
                
                return analysis
                
            except (json.JSONDecodeError, ValueError) as e:
                log_warning(f"[INNER_LANGUAGE] Nieprawidłowy JSON z LLM: {e}, odpowiedź: {analysis_response[:500]}...")
                return self._fallback_semantic_analysis(text)
                
        except Exception as e:
            log_error(f"[INNER_LANGUAGE] Błąd analizy semantycznej: {e}")
            return self._fallback_semantic_analysis(text)
    
    def _fallback_semantic_analysis(self, text: str) -> Dict[str, Any]:
        """Fallback analiza semantyczna"""
        
        words = text.lower().split()
        
        # Prosta klasyfikacja na podstawie POS tagging (symulacja)
        concepts = [word for word in words if len(word) > 4][:5]
        entities = [word for word in words if word.istitle()]
        actions = [word for word in words if word.endswith(('ić', 'ać', 'ować'))]
        
        return {
            "concepts": [{"text": concept, "dimensions": self._default_dimensions()} for concept in concepts],
            "entities": [{"text": entity, "dimensions": self._default_dimensions()} for entity in entities],
            "relations": [],
            "actions": [{"text": action, "dimensions": self._default_dimensions()} for action in actions],
            "properties": [],
            "emotions": [],
            "meta": [],
            "patterns": []
        }
    
    def _validate_dimensions(self, dimensions: Dict[str, Any]) -> Dict[str, float]:
        """Walidacja i normalizacja wymiarów semantycznych"""
        
        validated = {}
        
        # Sprawdź każdy możliwy wymiar
        for dim_name in ["abstraction", "certainty", "importance", "temporality", "emotionality", "complexity", "novelty"]:
            value = dimensions.get(dim_name)
            
            # Sprawdź czy wartość nie jest None
            if value is None:
                log_warning(f"[INNER_LANGUAGE] Dimension {dim_name} is None, using default")
                validated[dim_name] = self._default_dimensions()[dim_name]
                continue
            
            # Sprawdź typ wartości
            if isinstance(value, str):
                try:
                    # Usuń ewentualne cudzysłowy i dodatkowe znaki
                    clean_value = value.strip().strip('"').strip("'")
                    log_warning(f"[INNER_LANGUAGE] String dimension {dim_name}: '{value}' -> '{clean_value}'")
                    # Jeśli zawiera JSON-like content, wyciągnij pierwszą liczbę
                    import re
                    numbers = re.findall(r'[0-9.]+', clean_value)
                    if numbers:
                        validated[dim_name] = float(numbers[0])
                    else:
                        validated[dim_name] = self._default_dimensions()[dim_name]
                except (ValueError, IndexError) as e:
                    log_warning(f"[INNER_LANGUAGE] Error parsing dimension {dim_name}: {e}")
                    validated[dim_name] = self._default_dimensions()[dim_name]
            # Jeśli wartość jest liczbą, upewnij się że jest float
            elif isinstance(value, (int, float)):
                validated[dim_name] = float(value)
            # W przeciwnym razie użyj domyślnej
            else:
                log_warning(f"[INNER_LANGUAGE] Invalid dimension type {dim_name}: {type(value)} = {value}")
                validated[dim_name] = self._default_dimensions()[dim_name]
        
        return validated
    
    def _default_dimensions(self):
        """Zwraca domyślne wymiary semantyczne"""
        return {
            "abstraction": 0.5,
            "certainty": 0.5,
            "importance": 0.4,
            "temporality": 0.0,
            "emotionality": 0.2,
            "complexity": 0.3,
            "novelty": 0.1
        }
    
    async def _map_to_inner_tokens(
        self, 
        text: str, 
        semantic_analysis: Dict[str, Any]
    ) -> List[str]:
        """Mapuj elementy semantyczne na tokeny wewnętrzne"""
        
        token_chain = []
        
        # Przejdź przez wszystkie kategorie semantyczne
        for category, elements in semantic_analysis.items():
            if category in ["concepts", "entities", "relations", "actions", "properties", "emotions", "meta", "patterns"]:
                # Mapuj kategorię na TokenType
                type_mapping = {
                    "concepts": TokenType.CONCEPT,
                    "entities": TokenType.ENTITY,
                    "relations": TokenType.RELATION,
                    "actions": TokenType.ACTION,
                    "properties": TokenType.PROPERTY,
                    "emotions": TokenType.EMOTION,
                    "meta": TokenType.META,
                    "patterns": TokenType.PATTERN
                }
                token_type = type_mapping.get(category, TokenType.CONCEPT)
                
                for element in elements:
                    if isinstance(element, dict) and "text" in element:
                        # Walidacja dimensions
                        dimensions = element.get("dimensions", self._default_dimensions())
                        validated_dimensions = self._validate_dimensions(dimensions)
                        
                        token_id = await self._get_or_create_token(
                            surface_form=element["text"],
                            token_type=token_type,
                            dimensions=validated_dimensions
                        )
                        token_chain.append(token_id)
        
        return token_chain
    
    async def _get_or_create_token(
        self, 
        surface_form: str, 
        token_type: TokenType,
        dimensions: Dict[str, float]
    ) -> str:
        """Pobierz istniejący token lub stwórz nowy"""
        
        # Generuj rdzeń semantyczny
        semantic_core = await self._extract_semantic_core(surface_form, token_type)
        
        # Sprawdź czy token już istnieje
        for token_id, token in self.token_dictionary.items():
            if (token.semantic_core == semantic_core and 
                token.token_type == token_type):
                
                # Aktualizuj istniejący token
                token.usage_count += 1
                token.activation_level = min(token.activation_level + 0.1, 1.0)
                
                # Uśrednij wymiary
                for dim_name, dim_value in dimensions.items():
                    if hasattr(SemanticDimension, dim_name.upper()):
                        dim_enum = getattr(SemanticDimension, dim_name.upper())
                        if dim_enum in token.dimensions:
                            token.dimensions[dim_enum] = (token.dimensions[dim_enum] + dim_value) / 2
                        else:
                            token.dimensions[dim_enum] = dim_value
                
                return token_id
        
        # Stwórz nowy token
        token_id = hashlib.md5(f"{semantic_core}_{token_type.value}_{time.time()}".encode()).hexdigest()[:8]
        
        # Konwertuj wymiary string -> enum
        enum_dimensions = {}
        for dim_name, dim_value in dimensions.items():
            try:
                dim_enum = getattr(SemanticDimension, dim_name.upper())
                enum_dimensions[dim_enum] = dim_value
            except AttributeError:
                continue
        
        new_token = InnerToken(
            token_id=token_id,
            surface_form=surface_form,
            semantic_core=semantic_core,
            token_type=token_type,
            dimensions=enum_dimensions,
            associations=[],
            activation_level=0.5,
            creation_time=datetime.now(),
            usage_count=1,
            context_patterns=[],
            compression_ratio=len(semantic_core) / len(surface_form) if surface_form else 1.0
        )
        
        self.token_dictionary[token_id] = new_token
        
        # Ograniczenia słownika
        await self._manage_dictionary_size()
        
        return token_id
    
    async def _extract_semantic_core(self, surface_form: str, token_type: TokenType) -> str:
        """Wydobądź rdzeń semantyczny z formy powierzchniowej"""
        
        # Prosta heurystyka - można rozbudować o stemming/lemmatyzację
        core = surface_form.lower().strip()
        
        # Usuń końcówki fleksyjne (uproszczone)
        if token_type == TokenType.ACTION:
            for suffix in ['ować', 'ić', 'ać', 'eć', 'nąć']:
                if core.endswith(suffix):
                    core = core[:-len(suffix)]
                    break
        elif token_type == TokenType.PROPERTY:
            for suffix in ['owy', 'ny', 'ski', 'cki']:
                if core.endswith(suffix):
                    core = core[:-len(suffix)]
                    break
        
        return core[:20]  # Ogranicz długość
    
    async def _compress_token_chain(self, token_chain: List[str]) -> List[str]:
        """Skompresuj łańcuch tokenów"""
        
        if len(token_chain) <= 3:
            return token_chain
        
        # METODA 1: Usuń tokeny o niskiej aktywacji
        filtered_chain = []
        for token_id in token_chain:
            if token_id in self.token_dictionary:
                token = self.token_dictionary[token_id]
                if token.activation_level > 0.3:  # Threshold aktywacji
                    filtered_chain.append(token_id)
        
        # METODA 2: Zastąp sekwencje wzorcami
        pattern_compressed = await self._apply_pattern_compression(filtered_chain)
        
        # METODA 3: Cluster tokenów podobnych
        cluster_compressed = await self._apply_cluster_compression(pattern_compressed)
        
        return cluster_compressed
    
    async def _apply_pattern_compression(self, token_chain: List[str]) -> List[str]:
        """Zastosuj kompresję wzorcami"""
        
        # Sprawdź znane wzorce
        for pattern in self.thought_patterns.values():
            if (len(pattern.token_sequence) <= len(token_chain) and
                pattern.usage_frequency > 0.1):
                
                # Sprawdź czy wzorzec pasuje
                for i in range(len(token_chain) - len(pattern.token_sequence) + 1):
                    subsequence = token_chain[i:i + len(pattern.token_sequence)]
                    
                    if self._sequences_match(subsequence, pattern.token_sequence, similarity_threshold=0.8):
                        # Zastąp wzorcem
                        compressed = (token_chain[:i] + 
                                    [f"PATTERN_{pattern.pattern_id}"] + 
                                    token_chain[i + len(pattern.token_sequence):])
                        return await self._apply_pattern_compression(compressed)
        
        return token_chain
    
    def _sequences_match(self, seq1: List[str], seq2: List[str], similarity_threshold: float = 0.8) -> bool:
        """Sprawdź czy sekwencje tokenów są podobne"""
        
        if len(seq1) != len(seq2):
            return False
        
        matches = sum(1 for a, b in zip(seq1, seq2) if a == b)
        similarity = matches / len(seq1)
        
        return similarity >= similarity_threshold
    
    async def _apply_cluster_compression(self, token_chain: List[str]) -> List[str]:
        """Zastosuj kompresję klastrami"""
        
        # Znajdź tokeny należące do tego samego klastra
        compressed_chain = []
        i = 0
        
        while i < len(token_chain):
            current_token = token_chain[i]
            
            # Sprawdź czy następne tokeny należą do tego samego klastra
            cluster_id = self._find_token_cluster(current_token)
            if cluster_id:
                cluster_tokens = [current_token]
                j = i + 1
                
                while j < len(token_chain) and j < i + 3:  # Max 3 tokeny w grupie
                    if self._find_token_cluster(token_chain[j]) == cluster_id:
                        cluster_tokens.append(token_chain[j])
                        j += 1
                    else:
                        break
                
                if len(cluster_tokens) > 1:
                    # Zastąp grupę reprezentantem klastra
                    compressed_chain.append(f"CLUSTER_{cluster_id}")
                    i = j
                else:
                    compressed_chain.append(current_token)
                    i += 1
            else:
                compressed_chain.append(current_token)
                i += 1
        
        return compressed_chain
    
    def _find_token_cluster(self, token_id: str) -> Optional[str]:
        """Znajdź klaster dla tokena"""
        
        for cluster_id, cluster in self.semantic_clusters.items():
            if token_id in cluster.core_tokens or token_id in cluster.peripheral_tokens:
                return cluster_id
        
        return None
    
    async def _generate_semantic_vector(self, token_chain: List[str]) -> List[float]:
        """Generuj wektor semantyczny dla łańcucha tokenów"""
        
        if not token_chain:
            return [0.0] * 64  # Domyślny wymiar wektora
        
        # METODA 1: Średnia ważona wektorów tokenów
        vector = [0.0] * 64
        total_weight = 0.0
        
        for token_id in token_chain:
            if token_id.startswith("PATTERN_") or token_id.startswith("CLUSTER_"):
                # Specjalne traktowanie wzorców i klastrów
                token_weight = 1.0
                token_vector = self._generate_pattern_cluster_vector(token_id)
            elif token_id in self.token_dictionary:
                token = self.token_dictionary[token_id]
                token_weight = token.activation_level * token.dimensions.get(SemanticDimension.IMPORTANCE, 0.5)
                token_vector = self._token_to_vector(token)
            else:
                continue
            
            # Dodaj ważony wkład tokena
            for i in range(len(vector)):
                vector[i] += token_vector[i] * token_weight
            
            total_weight += token_weight
        
        # Normalizuj
        if total_weight > 0:
            vector = [v / total_weight for v in vector]
        
        return vector
    
    def _token_to_vector(self, token: InnerToken) -> List[float]:
        """Konwertuj token na wektor"""
        
        # Bazowy wektor na podstawie typu tokena
        type_vectors = {
            TokenType.CONCEPT: [1, 0, 0, 0, 0, 0, 0, 0],
            TokenType.ENTITY: [0, 1, 0, 0, 0, 0, 0, 0],
            TokenType.RELATION: [0, 0, 1, 0, 0, 0, 0, 0],
            TokenType.ACTION: [0, 0, 0, 1, 0, 0, 0, 0],
            TokenType.PROPERTY: [0, 0, 0, 0, 1, 0, 0, 0],
            TokenType.EMOTION: [0, 0, 0, 0, 0, 1, 0, 0],
            TokenType.META: [0, 0, 0, 0, 0, 0, 1, 0],
            TokenType.PATTERN: [0, 0, 0, 0, 0, 0, 0, 1]
        }
        
        base_vector = type_vectors.get(token.token_type, [0] * 8)
        
        # Dodaj wymiary semantyczne
        dimensions_vector = [
            token.dimensions.get(dim, 0.0) for dim in SemanticDimension.__members__.values()
        ]
        
        # Dodaj hash rdzenia semantycznego jako pseudo-embedding
        core_hash = hash(token.semantic_core) % 1000000
        hash_vector = [(core_hash >> i) & 1 for i in range(20)]  # 20-bitowy hash
        
        # Kombinuj wszystkie składniki
        full_vector = base_vector + dimensions_vector + hash_vector
        
        # Dopełnij do 64 wymiarów
        while len(full_vector) < 64:
            full_vector.append(0.0)
        
        return full_vector[:64]
    
    def _generate_pattern_cluster_vector(self, special_token: str) -> List[float]:
        """Generuj wektor dla wzorców i klastrów"""
        
        if special_token.startswith("PATTERN_"):
            pattern_id = special_token.replace("PATTERN_", "")
            if pattern_id in self.thought_patterns:
                pattern = self.thought_patterns[pattern_id]
                # Średnia wektorów tokenów w wzorcu
                vectors = []
                for token_id in pattern.token_sequence:
                    if token_id in self.token_dictionary:
                        vectors.append(self._token_to_vector(self.token_dictionary[token_id]))
                
                if vectors:
                    return [sum(v[i] for v in vectors) / len(vectors) for i in range(64)]
        
        elif special_token.startswith("CLUSTER_"):
            cluster_id = special_token.replace("CLUSTER_", "")
            if cluster_id in self.semantic_clusters:
                cluster = self.semantic_clusters[cluster_id]
                # Średnia wektorów tokenów w klastrze
                vectors = []
                for token_id in cluster.core_tokens + cluster.peripheral_tokens:
                    if token_id in self.token_dictionary:
                        vectors.append(self._token_to_vector(self.token_dictionary[token_id]))
                
                if vectors:
                    return [sum(v[i] for v in vectors) / len(vectors) for i in range(64)]
        
        return [0.0] * 64
    
    async def _calculate_thought_confidence(
        self, 
        token_chain: List[str], 
        semantic_vector: List[float]
    ) -> float:
        """Oblicz pewność myśli"""
        
        confidence = 0.0
        
        # Składnik 1: Jakość tokenów
        token_quality = 0.0
        valid_tokens = 0
        
        for token_id in token_chain:
            if token_id in self.token_dictionary:
                token = self.token_dictionary[token_id]
                token_quality += token.dimensions.get(SemanticDimension.CERTAINTY, 0.5)
                valid_tokens += 1
        
        if valid_tokens > 0:
            confidence += (token_quality / valid_tokens) * 0.4
        
        # Składnik 2: Spójność semantyczna
        vector_magnitude = math.sqrt(sum(v**2 for v in semantic_vector))
        if vector_magnitude > 0:
            confidence += min(vector_magnitude / 10.0, 0.3)  # Normalizacja
        
        # Składnik 3: Rozpoznane wzorce
        pattern_bonus = len([t for t in token_chain if t.startswith("PATTERN_")]) * 0.1
        confidence += min(pattern_bonus, 0.3)
        
        return min(confidence, 1.0)
    
    async def _assess_thought_originality(self, token_chain: List[str]) -> float:
        """Oceń oryginalność myśli"""
        
        originality = 0.0
        
        # Składnik 1: Nowość tokenów
        novelty_sum = 0.0
        valid_tokens = 0
        
        for token_id in token_chain:
            if token_id in self.token_dictionary:
                token = self.token_dictionary[token_id]
                novelty_sum += token.dimensions.get(SemanticDimension.NOVELTY, 0.5)
                valid_tokens += 1
        
        if valid_tokens > 0:
            originality += (novelty_sum / valid_tokens) * 0.5
        
        # Składnik 2: Unikalna kombinacja
        chain_signature = "_".join(sorted(token_chain))
        is_unique = True
        
        for past_thought in list(self.thought_history)[-100:]:  # Sprawdź ostatnie 100
            past_signature = "_".join(sorted(past_thought.token_chain))
            if chain_signature == past_signature:
                is_unique = False
                break
        
        if is_unique:
            originality += 0.5
        
        return min(originality, 1.0)
    
    async def _update_association_networks(self, token_chain: List[str]):
        """Aktualizuj sieci skojarzeniowe"""
        
        # Aktualizuj powiązania między tokenami w łańcuchu
        for i, token1 in enumerate(token_chain):
            for j, token2 in enumerate(token_chain):
                if i != j and token1 in self.token_dictionary and token2 in self.token_dictionary:
                    # Siła skojarzeń maleje z odległością
                    distance = abs(i - j)
                    association_strength = 1.0 / (distance + 1) * 0.1
                    
                    self.association_network[token1][token2] += association_strength
                    
                    # Aktualizuj listy skojarzeń w tokenach
                    token1_obj = self.token_dictionary[token1]
                    if token2 not in token1_obj.associations:
                        token1_obj.associations.append(token2)
    
    async def _manage_dictionary_size(self):
        """Zarządzaj rozmiarem słownika tokenów"""
        
        if len(self.token_dictionary) > self.max_tokens:
            # Usuń tokeny o najniższej częstotliwości i aktywacji
            tokens_by_score = []
            
            for token_id, token in self.token_dictionary.items():
                score = token.usage_count * token.activation_level
                tokens_by_score.append((score, token_id))
            
            # Sortuj i usuń najsłabsze
            tokens_by_score.sort()
            tokens_to_remove = tokens_by_score[:len(self.token_dictionary) - self.max_tokens + 100]
            
            for _, token_id in tokens_to_remove:
                del self.token_dictionary[token_id]
                
                # Usuń z sieci skojarzeń
                if token_id in self.association_network:
                    del self.association_network[token_id]
                
                for other_token in self.association_network:
                    if token_id in self.association_network[other_token]:
                        del self.association_network[other_token][token_id]
    
    async def _create_fallback_thought(self, text: str) -> InnerThought:
        """Stwórz prostą myśl jako fallback"""
        
        return InnerThought(
            thought_id=hashlib.md5(f"fallback_{text}_{time.time()}".encode()).hexdigest()[:12],
            token_chain=[f"FALLBACK_{word}" for word in text.split()[:5]],
            semantic_vector=[0.5] * 64,
            compression_level=0.1,
            processing_time=0.01,
            confidence=0.3,
            originality=0.1,
            surface_translation=text
        )
    
    async def translate_to_natural_language(
        self, 
        inner_thought: InnerThought,
        style: str = "natural",
        max_length: int = 500
    ) -> str:
        """
        Przetłumacz myśl z języka wewnętrznego na naturalny
        
        Args:
            inner_thought: Myśl w języku wewnętrznym
            style: Styl tłumaczenia ("natural", "technical", "poetic")
            max_length: Maksymalna długość
            
        Returns:
            str: Tekst w języku naturalnym
        """
        
        try:
            # Dekompresuj tokeny na powierzchnie językowe
            surface_elements = []
            
            for token_id in inner_thought.token_chain:
                if token_id.startswith("PATTERN_"):
                    # Rozwiń wzorzec
                    pattern_id = token_id.replace("PATTERN_", "")
                    if pattern_id in self.thought_patterns:
                        pattern = self.thought_patterns[pattern_id]
                        for sub_token in pattern.token_sequence:
                            if sub_token in self.token_dictionary:
                                surface_elements.append(self.token_dictionary[sub_token].surface_form)
                    
                elif token_id.startswith("CLUSTER_"):
                    # Rozwiń klaster
                    cluster_id = token_id.replace("CLUSTER_", "")
                    if cluster_id in self.semantic_clusters:
                        cluster = self.semantic_clusters[cluster_id]
                        surface_elements.append(f"[{cluster.cluster_theme}]")
                
                elif token_id in self.token_dictionary:
                    token = self.token_dictionary[token_id]
                    surface_elements.append(token.surface_form)
                
                else:
                    # Fallback tokeny
                    if token_id.startswith("FALLBACK_"):
                        surface_elements.append(token_id.replace("FALLBACK_", ""))
            
            # Użyj LLM do stylizacji i naturalizacji
            raw_text = " ".join(surface_elements)
            
            stylization_prompt = f"""
            Przekształć następujące elementy semantyczne na płynny tekst w języku polskim:
            
            ELEMENTY: {raw_text}
            STYL: {style}
            KONTEKST: Kompresja myśli: {inner_thought.compression_level:.2f}, Pewność: {inner_thought.confidence:.2f}
            
            Wytyczne:
            1. Zachowaj znaczenie wszystkich elementów
            2. Użyj stylu: {style}
            3. Maksymalna długość: {max_length} znaków
            4. Naturalny, płynny język polski
            
            Zwróć tylko przetłumaczony tekst.
            """
            
            translated = await self.llm_client.chat_completion([{
                "role": "system",
                "content": f"Jesteś ekspertem w tłumaczeniu języka wewnętrznego na naturalny. Specjalizujesz się w stylu: {style}."
            }, {
                "role": "user",
                "content": stylization_prompt
            }])
            
            # Ogranicz długość
            if len(translated) > max_length:
                translated = translated[:max_length-3] + "..."
            
            return translated
            
        except Exception as e:
            log_error(f"[INNER_LANGUAGE] Błąd tłumaczenia: {e}")
            return " ".join(surface_elements) if surface_elements else inner_thought.surface_translation
    
    async def find_associations(
        self, 
        query_tokens: List[str], 
        max_associations: int = 10,
        min_strength: float = 0.1
    ) -> List[Tuple[str, float]]:
        """
        Znajdź skojarzenia dla zestawu tokenów
        
        Args:
            query_tokens: Lista tokenów zapytania
            max_associations: Maksymalna liczba skojarzeń
            min_strength: Minimalna siła skojarzenia
            
        Returns:
            List[Tuple[str, float]]: Lista (token_id, siła_skojarzenia)
        """
        
        associations = defaultdict(float)
        
        for query_token in query_tokens:
            if query_token in self.association_network:
                for associated_token, strength in self.association_network[query_token].items():
                    if strength >= min_strength:
                        associations[associated_token] += strength
        
        # Sortuj i ogranicz
        sorted_associations = sorted(associations.items(), key=lambda x: x[1], reverse=True)
        return sorted_associations[:max_associations]
    
    async def discover_thought_patterns(
        self, 
        min_frequency: int = 3,
        min_effectiveness: float = 0.6
    ) -> List[ThoughtPattern]:
        """
        Odkryj wzorce myślowe z historii
        
        Args:
            min_frequency: Minimalna częstotliwość wzorca
            min_effectiveness: Minimalna skuteczność
            
        Returns:
            List[ThoughtPattern]: Lista odkrytych wzorców
        """
        
        patterns = []
        
        # Analizuj sekwencje tokenów w historii myśli
        sequence_counts = defaultdict(int)
        
        for thought in self.thought_history:
            # Generuj wszystkie subsequencje długości 2-4
            for length in range(2, min(5, len(thought.token_chain) + 1)):
                for i in range(len(thought.token_chain) - length + 1):
                    subsequence = tuple(thought.token_chain[i:i + length])
                    sequence_counts[subsequence] += 1
        
        # Filtruj wzorce według częstotliwości
        for sequence, count in sequence_counts.items():
            if count >= min_frequency:
                # Oblicz skuteczność wzorca
                effectiveness = await self._calculate_pattern_effectiveness(list(sequence))
                
                if effectiveness >= min_effectiveness:
                    pattern = ThoughtPattern(
                        pattern_id=hashlib.md5(str(sequence).encode()).hexdigest()[:8],
                        token_sequence=list(sequence),
                        trigger_conditions=[],  # TODO: określ warunki
                        completion_probability=count / len(self.thought_history),
                        usage_frequency=count / len(self.thought_history),
                        effectiveness_score=effectiveness,
                        context_specificity=0.5  # TODO: oblicz
                    )
                    patterns.append(pattern)
                    
                    # Dodaj do słownika wzorców
                    self.thought_patterns[pattern.pattern_id] = pattern
        
        log_info(f"[INNER_LANGUAGE] Odkryto {len(patterns)} nowych wzorców myślowych")
        return patterns
    
    async def _calculate_pattern_effectiveness(self, token_sequence: List[str]) -> float:
        """Oblicz skuteczność wzorca myślowego"""
        
        # Prosta heurystyka - można rozbudować
        effectiveness = 0.0
        
        # Bonus za różnorodność typów tokenów
        token_types = set()
        for token_id in token_sequence:
            if token_id in self.token_dictionary:
                token = self.token_dictionary[token_id]
                token_types.add(token.token_type)
        
        effectiveness += len(token_types) / len(TokenType) * 0.4
        
        # Bonus za wysoką aktywację tokenów
        avg_activation = 0.0
        valid_tokens = 0
        
        for token_id in token_sequence:
            if token_id in self.token_dictionary:
                token = self.token_dictionary[token_id]
                avg_activation += token.activation_level
                valid_tokens += 1
        
        if valid_tokens > 0:
            effectiveness += (avg_activation / valid_tokens) * 0.6
        
        return min(effectiveness, 1.0)
    
    async def cluster_semantic_tokens(
        self, 
        similarity_threshold: float = 0.7,
        min_cluster_size: int = 3
    ) -> List[SemanticCluster]:
        """
        Klastruj tokeny semantycznie podobne
        
        Args:
            similarity_threshold: Próg podobieństwa
            min_cluster_size: Minimalna wielkość klastra
            
        Returns:
            List[SemanticCluster]: Lista klastrów
        """
        
        try:
            log_info("[INNER_LANGUAGE] Klastrowanie tokenów semantycznych...")
            
            # Oblicz macierz podobieństw
            token_ids = list(self.token_dictionary.keys())
            similarity_matrix = {}
            
            for i, token_id1 in enumerate(token_ids):
                similarity_matrix[token_id1] = {}
                for j, token_id2 in enumerate(token_ids):
                    if i <= j:
                        similarity = await self._calculate_token_similarity(token_id1, token_id2)
                        similarity_matrix[token_id1][token_id2] = similarity
                        if token_id2 not in similarity_matrix:
                            similarity_matrix[token_id2] = {}
                        similarity_matrix[token_id2][token_id1] = similarity
            
            # Prosty algorytm klastrowania (można zastąpić zaawansowanymi)
            clusters = []
            used_tokens = set()
            
            for token_id in token_ids:
                if token_id in used_tokens:
                    continue
                
                # Znajdź podobne tokeny
                cluster_tokens = [token_id]
                used_tokens.add(token_id)
                
                for other_token in token_ids:
                    if (other_token not in used_tokens and 
                        similarity_matrix[token_id][other_token] >= similarity_threshold):
                        cluster_tokens.append(other_token)
                        used_tokens.add(other_token)
                
                # Stwórz klaster jeśli wystarczająco duży
                if len(cluster_tokens) >= min_cluster_size:
                    cluster_theme = await self._determine_cluster_theme(cluster_tokens)
                    
                    cluster = SemanticCluster(
                        cluster_id=hashlib.md5(f"cluster_{time.time()}_{len(clusters)}".encode()).hexdigest()[:8],
                        core_tokens=cluster_tokens[:3],  # Najbardziej reprezentatywne
                        peripheral_tokens=cluster_tokens[3:],
                        cluster_theme=cluster_theme,
                        coherence_score=await self._calculate_cluster_coherence(cluster_tokens),
                        activation_history=[(datetime.now(), 0.5)],
                        inter_cluster_links={}
                    )
                    
                    clusters.append(cluster)
                    self.semantic_clusters[cluster.cluster_id] = cluster
            
            log_info(f"[INNER_LANGUAGE] Utworzono {len(clusters)} klastrów semantycznych")
            return clusters
            
        except Exception as e:
            log_error(f"[INNER_LANGUAGE] Błąd klastrowania: {e}")
            return []
    
    async def _calculate_token_similarity(self, token_id1: str, token_id2: str) -> float:
        """Oblicz podobieństwo między tokenami"""
        
        if token_id1 == token_id2:
            return 1.0
        
        if token_id1 not in self.token_dictionary or token_id2 not in self.token_dictionary:
            return 0.0
        
        token1 = self.token_dictionary[token_id1]
        token2 = self.token_dictionary[token_id2]
        
        similarity = 0.0
        
        # Składnik 1: Typ tokena
        if token1.token_type == token2.token_type:
            similarity += 0.3
        
        # Składnik 2: Podobieństwo wymiarów semantycznych
        dim_similarities = []
        for dim in SemanticDimension.__members__.values():
            val1 = token1.dimensions.get(dim, 0.5)
            val2 = token2.dimensions.get(dim, 0.5)
            dim_sim = 1.0 - abs(val1 - val2)
            dim_similarities.append(dim_sim)
        
        similarity += sum(dim_similarities) / len(dim_similarities) * 0.4
        
        # Składnik 3: Rdzeń semantyczny
        core_sim = self._string_similarity(token1.semantic_core, token2.semantic_core)
        similarity += core_sim * 0.2
        
        # Składnik 4: Skojarzenia
        if token_id2 in token1.associations or token_id1 in token2.associations:
            similarity += 0.1
        
        return min(similarity, 1.0)
    
    def _string_similarity(self, str1: str, str2: str) -> float:
        """Oblicz podobieństwo stringów"""
        
        if not str1 or not str2:
            return 0.0
        
        # Prosta miara Jaccarda na poziomie znaków
        set1 = set(str1.lower())
        set2 = set(str2.lower())
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    async def _determine_cluster_theme(self, token_ids: List[str]) -> str:
        """Określ główny temat klastra"""
        
        surface_forms = []
        token_types = defaultdict(int)
        
        for token_id in token_ids:
            if token_id in self.token_dictionary:
                token = self.token_dictionary[token_id]
                surface_forms.append(token.surface_form)
                token_types[token.token_type.value] += 1
        
        # Najczęstszy typ tokena
        dominant_type = max(token_types.items(), key=lambda x: x[1])[0] if token_types else "general"
        
        # Pierwszy element jako reprezentant
        representative = surface_forms[0] if surface_forms else "unknown"
        
        return f"{dominant_type}_{representative}"[:50]
    
    async def _calculate_cluster_coherence(self, token_ids: List[str]) -> float:
        """Oblicz spójność klastra"""
        
        if len(token_ids) < 2:
            return 1.0
        
        similarities = []
        
        for i, token_id1 in enumerate(token_ids):
            for j, token_id2 in enumerate(token_ids):
                if i < j:
                    similarity = await self._calculate_token_similarity(token_id1, token_id2)
                    similarities.append(similarity)
        
        return sum(similarities) / len(similarities) if similarities else 0.0
    
    async def get_inner_language_report(self) -> Dict[str, Any]:
        """Pobierz raport systemu języka wewnętrznego"""
        
        # Aktualizuj metryki
        self.performance_metrics["total_tokens"] = len(self.token_dictionary)
        self.performance_metrics["active_clusters"] = len(self.semantic_clusters)
        
        # Analiza tokenów według typów
        token_type_distribution = defaultdict(int)
        for token in self.token_dictionary.values():
            token_type_distribution[token.token_type.value] += 1
        
        # Top tokeny według aktywacji
        top_tokens = sorted(
            self.token_dictionary.values(),
            key=lambda t: t.activation_level * t.usage_count,
            reverse=True
        )[:10]
        
        # Najsilniejsze skojarzenia
        top_associations = []
        for token1, assocs in list(self.association_network.items())[:5]:
            for token2, strength in sorted(assocs.items(), key=lambda x: x[1], reverse=True)[:3]:
                if token1 in self.token_dictionary and token2 in self.token_dictionary:
                    top_associations.append({
                        "token1": self.token_dictionary[token1].surface_form,
                        "token2": self.token_dictionary[token2].surface_form,
                        "strength": strength
                    })
        
        report = {
            "performance_metrics": self.performance_metrics,
            "token_statistics": {
                "total_tokens": len(self.token_dictionary),
                "type_distribution": dict(token_type_distribution),
                "avg_activation": sum(t.activation_level for t in self.token_dictionary.values()) / len(self.token_dictionary) if self.token_dictionary else 0,
                "avg_usage": sum(t.usage_count for t in self.token_dictionary.values()) / len(self.token_dictionary) if self.token_dictionary else 0
            },
            "top_tokens": [
                {
                    "surface_form": token.surface_form,
                    "type": token.token_type.value,
                    "activation": token.activation_level,
                    "usage_count": token.usage_count,
                    "associations": len(token.associations)
                }
                for token in top_tokens
            ],
            "clustering": {
                "total_clusters": len(self.semantic_clusters),
                "avg_cluster_size": sum(len(c.core_tokens) + len(c.peripheral_tokens) for c in self.semantic_clusters.values()) / len(self.semantic_clusters) if self.semantic_clusters else 0,
                "avg_coherence": sum(c.coherence_score for c in self.semantic_clusters.values()) / len(self.semantic_clusters) if self.semantic_clusters else 0
            },
            "patterns": {
                "total_patterns": len(self.thought_patterns),
                "avg_effectiveness": sum(p.effectiveness_score for p in self.thought_patterns.values()) / len(self.thought_patterns) if self.thought_patterns else 0,
                "avg_frequency": sum(p.usage_frequency for p in self.thought_patterns.values()) / len(self.thought_patterns) if self.thought_patterns else 0
            },
            "top_associations": top_associations,
            "recent_thoughts": [
                {
                    "compression_level": thought.compression_level,
                    "confidence": thought.confidence,
                    "originality": thought.originality,
                    "processing_time": thought.processing_time,
                    "tokens_count": len(thought.token_chain)
                }
                for thought in list(self.thought_history)[-5:]
            ]
        }
        
        return report

# Globalna instancja procesora
_inner_language_processor = None

def get_inner_language_processor() -> InnerLanguageProcessor:
    """Pobierz globalną instancję procesora języka wewnętrznego"""
    global _inner_language_processor
    if _inner_language_processor is None:
        _inner_language_processor = InnerLanguageProcessor()
    return _inner_language_processor

async def process_inner_thought(text: str, context: Dict[str, Any] = None) -> InnerThought:
    """
    Główna funkcja przetwarzania myśli na język wewnętrzny
    
    Args:
        text: Tekst w języku naturalnym
        context: Kontekst przetwarzania
        
    Returns:
        InnerThought: Przetworzona myśl
    """
    processor = get_inner_language_processor()
    return await processor.process_natural_language_input(text, context)

async def translate_inner_thought(
    inner_thought: InnerThought, 
    style: str = "natural"
) -> str:
    """
    Przetłumacz myśl z języka wewnętrznego na naturalny
    
    Args:
        inner_thought: Myśl w języku wewnętrznym
        style: Styl tłumaczenia
        
    Returns:
        str: Tekst w języku naturalnym
    """
    processor = get_inner_language_processor()
    return await processor.translate_to_natural_language(inner_thought, style)

# Test funkcji
if __name__ == "__main__":
    async def test_inner_language():
        """Test systemu języka wewnętrznego"""
        
        test_inputs = [
            "Jak mogę lepiej zrozumieć sztuczną inteligencję?",
            "Czy AI może być kreatywna i czy to oznacza świadomość?",
            "Interesuje mnie implementacja algorytmów uczenia maszynowego w praktyce.",
            "Zastanawiam się nad etyką sztucznej inteligencji i jej wpływem na społeczeństwo."
        ]
        
        print("🧠 TEST JĘZYKA WEWNĘTRZNEGO")
        print("=" * 60)
        
        processor = get_inner_language_processor()
        
        # Test przetwarzania input
        thoughts = []
        for i, text in enumerate(test_inputs, 1):
            print(f"\n📝 INPUT {i}: {text}")
            print("-" * 50)
            
            # Przetwórz na język wewnętrzny
            inner_thought = await process_inner_thought(text)
            thoughts.append(inner_thought)
            
            print(f"🔧 Tokeny ({len(inner_thought.token_chain)}): {inner_thought.token_chain[:5]}...")
            print(f"📊 Kompresja: {inner_thought.compression_level:.2f}")
            print(f"🎯 Pewność: {inner_thought.confidence:.2f}")
            print(f"✨ Oryginalność: {inner_thought.originality:.2f}")
            print(f"⏱️ Czas: {inner_thought.processing_time:.3f}s")
            
            # Przetłumacz z powrotem
            translation = await translate_inner_thought(inner_thought, "natural")
            print(f"🔄 Tłumaczenie: {translation[:100]}...")
        
        # Test wykrywania wzorców
        print(f"\n🔍 WYKRYWANIE WZORCÓW MYŚLOWYCH")
        print("-" * 40)
        
        patterns = await processor.discover_thought_patterns(min_frequency=1)
        print(f"Odkryto wzorców: {len(patterns)}")
        
        for pattern in patterns[:3]:
            print(f"  Wzorzec: {pattern.token_sequence}")
            print(f"  Skuteczność: {pattern.effectiveness_score:.2f}")
            print(f"  Częstotliwość: {pattern.usage_frequency:.2f}")
        
        # Test klastrowania
        print(f"\n🧩 KLASTROWANIE SEMANTYCZNE")
        print("-" * 35)
        
        clusters = await processor.cluster_semantic_tokens(similarity_threshold=0.5, min_cluster_size=2)
        print(f"Utworzono klastrów: {len(clusters)}")
        
        for cluster in clusters[:3]:
            print(f"  Klaster: {cluster.cluster_theme}")
            print(f"  Tokeny: {len(cluster.core_tokens + cluster.peripheral_tokens)}")
            print(f"  Spójność: {cluster.coherence_score:.2f}")
        
        # Test skojarzeń
        print(f"\n🔗 TEST SKOJARZEŃ")
        print("-" * 25)
        
        if thoughts:
            sample_tokens = thoughts[0].token_chain[:3]
            associations = await processor.find_associations(sample_tokens, max_associations=5)
            
            print(f"Skojarzenia dla: {sample_tokens}")
            for token_id, strength in associations:
                if token_id in processor.token_dictionary:
                    surface = processor.token_dictionary[token_id].surface_form
                    print(f"  {surface}: {strength:.3f}")
        
        # Raport końcowy
        report = await processor.get_inner_language_report()
        print(f"\n📊 RAPORT SYSTEMU:")
        print(f"Tokenów ogółem: {report['token_statistics']['total_tokens']}")
        print(f"Klastrów: {report['clustering']['total_clusters']}")
        print(f"Wzorców: {report['patterns']['total_patterns']}")
        print(f"Średnia kompresja: {report['performance_metrics']['compression_ratio']:.2f}")
        print(f"Myśli przetworzone: {report['performance_metrics']['thoughts_processed']}")
    
    # Uruchom test
    asyncio.run(test_inner_language())