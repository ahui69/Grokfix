#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM Batch Processing - System wsadowego przetwarzania zapytań do modeli językowych
Pozwala na efektywne przetwarzanie wielu zapytań jednocześnie, 
optymalizując wykorzystanie API i minimalizując opóźnienia.
"""

import asyncio
import time
import json
from typing import List, Dict, Any, Optional, Union, Callable, Tuple
from dataclasses import dataclass, field
import traceback
from collections import deque

from core.config import (
    LLM_MODEL, LLM_API_KEY, LLM_BASE_URL, 
    LLM_RETRIES, LLM_TIMEOUT, LLM_BACKOFF_S
)
from core.llm import call_llm, call_llm_raw

# ═══════════════════════════════════════════════════════════════════
# KONFIGURACJA WSADOWEGO PRZETWARZANIA
# ═══════════════════════════════════════════════════════════════════

# Parametry wsadowego przetwarzania
MAX_BATCH_SIZE = 10           # Maksymalna liczba zapytań w jednej partii
MAX_BATCH_WAIT_MS = 100       # Maksymalny czas oczekiwania na więcej zapytań (ms)
MIN_BATCH_SIZE = 2            # Minimalna liczba zapytań potrzebna do uruchomienia wsadowego przetwarzania
MAX_CONCURRENT_BATCHES = 3    # Maksymalna liczba równoległych przetwarzań wsadowych
BATCH_TIMEOUT = 30            # Globalny timeout dla wsadowego przetwarzania (sekundy)

# Metryki i monitoring
METRICS_WINDOW_SIZE = 100     # Liczba zapytań do przechowywania w metrykach


@dataclass
class BatchRequest:
    """Reprezentuje pojedyncze żądanie w partii"""
    id: str                      # Unikalny identyfikator żądania
    messages: List[Dict[str, Any]]  # Wiadomości do przetworzenia przez LLM
    params: Dict[str, Any]       # Parametry dla LLM (temperatura itp.)
    created_at: float = field(default_factory=time.time)  # Czas utworzenia żądania
    future: asyncio.Future = field(default_factory=asyncio.Future)  # Future do rozwiązania z odpowiedzią
    priority: int = 0            # Priorytet żądania (wyższy = ważniejsze)
    metadata: Dict[str, Any] = field(default_factory=dict)  # Dodatkowe metadane


@dataclass
class BatchMetrics:
    """Metryki dla procesora wsadowego"""
    total_requests: int = 0          # Całkowita liczba przetworzonych żądań
    total_batches: int = 0           # Całkowita liczba partii
    avg_batch_size: float = 0.0      # Średni rozmiar partii
    avg_wait_time: float = 0.0       # Średni czas oczekiwania (ms)
    avg_processing_time: float = 0.0  # Średni czas przetwarzania (ms)
    token_savings: int = 0           # Oszacowane oszczędności tokenów
    error_count: int = 0             # Liczba błędów
    
    # Historia ostatnich operacji dla wykresów
    recent_batch_sizes: deque = field(default_factory=lambda: deque(maxlen=METRICS_WINDOW_SIZE))
    recent_wait_times: deque = field(default_factory=lambda: deque(maxlen=METRICS_WINDOW_SIZE))
    recent_processing_times: deque = field(default_factory=lambda: deque(maxlen=METRICS_WINDOW_SIZE))


# ═══════════════════════════════════════════════════════════════════
# GŁÓWNA LOGIKA WSADOWEGO PRZETWARZANIA
# ═══════════════════════════════════════════════════════════════════

class LLMBatchProcessor:
    """
    Procesor wsadowy LLM - grupuje wiele zapytań w jeden batch
    dla zwiększenia wydajności i oszczędności tokenów.
    """
    
    def __init__(self):
        """Inicjalizuje procesor wsadowy"""
        # Kolejki i bufory
        self.pending_requests = asyncio.Queue()  # Kolejka oczekujących żądań
        self.batch_buffer = []  # Bufor dla aktualnie budowanej partii
        self.batch_buffer_lock = asyncio.Lock()  # Blokada dla bufora
        
        # Flagi stanu
        self.running = False
        self.batch_timer_task = None
        self.processor_tasks = []
        
        # Metryki i statystyki
        self.metrics = BatchMetrics()
        
        # Funkcja wywołania LLM
        self._llm_call_func = call_llm
        
        # Status i zarządzanie
        self.last_error = None
        self.active_batch_count = 0
    
    async def start(self):
        """Uruchamia procesor wsadowy"""
        if self.running:
            return
        
        self.running = True
        
        # Uruchom zadanie licznika czasu dla pierwszej partii
        self.batch_timer_task = asyncio.create_task(self._batch_timer())
        
        # Uruchom procesory wsadowe
        for _ in range(MAX_CONCURRENT_BATCHES):
            task = asyncio.create_task(self._batch_processor())
            self.processor_tasks.append(task)
        
        print(f"[INFO] LLM Batch Processor started with {MAX_CONCURRENT_BATCHES} processors")
    
    async def stop(self):
        """Zatrzymuje procesor wsadowy"""
        if not self.running:
            return
        
        self.running = False
        
        # Anuluj zadanie licznika czasu
        if self.batch_timer_task:
            self.batch_timer_task.cancel()
            try:
                await self.batch_timer_task
            except asyncio.CancelledError:
                pass
        
        # Anuluj procesory wsadowe
        for task in self.processor_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self.processor_tasks.clear()
        
        print("[INFO] LLM Batch Processor stopped")
    
    async def submit(self, messages: List[Dict[str, Any]], params: Dict[str, Any] = None, 
                     priority: int = 0, request_id: str = None) -> str:
        """
        Dodaje zapytanie do kolejki przetwarzania wsadowego
        
        Args:
            messages: Lista wiadomości do przetworzenia
            params: Parametry dla LLM (temperatura itp.)
            priority: Priorytet zapytania (wyższy = ważniejsze)
            request_id: Opcjonalny identyfikator zapytania
        
        Returns:
            Tekst odpowiedzi LLM
        """
        if not self.running:
            await self.start()
        
        # Przygotuj parametry LLM (domyślne jeśli nie podano)
        if params is None:
            params = {}
        
        # Wygeneruj identyfikator, jeśli nie podano
        if not request_id:
            request_id = f"req_{int(time.time() * 1000)}_{hash(str(messages))}"
        
        # Utwórz żądanie
        request = BatchRequest(
            id=request_id,
            messages=messages,
            params=params,
            priority=priority,
            metadata={
                "submit_time": time.time()
            }
        )
        
        # Dodaj do kolejki
        await self.pending_requests.put(request)
        
        # Poczekaj na odpowiedź
        try:
            result = await asyncio.wait_for(request.future, timeout=BATCH_TIMEOUT)
            return result
        except asyncio.TimeoutError:
            error_msg = f"Timeout waiting for batch request {request_id}"
            self.last_error = error_msg
            self.metrics.error_count += 1
            raise TimeoutError(error_msg)
    
    async def _batch_timer(self):
        """
        Zadanie licznika czasu dla partii - uruchamia przetwarzanie partii 
        po upływie MAX_BATCH_WAIT_MS, nawet jeśli nie osiągnięto MAX_BATCH_SIZE
        """
        while self.running:
            try:
                # Czekaj przez MAX_BATCH_WAIT_MS
                await asyncio.sleep(MAX_BATCH_WAIT_MS / 1000)
                
                async with self.batch_buffer_lock:
                    if len(self.batch_buffer) >= MIN_BATCH_SIZE:
                        # Czas upłynął, dodaj bieżącą partię do kolejki
                        await self._process_current_batch()
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.last_error = str(e)
                self.metrics.error_count += 1
                print(f"[ERROR] Batch timer error: {e}")
                traceback.print_exc()
    
    async def _process_current_batch(self):
        """Przetwarza bieżącą partię żądań"""
        if not self.batch_buffer:
            return
        
        # Pobierz aktualny bufor i zresetuj go
        current_batch = self.batch_buffer
        self.batch_buffer = []
        
        # Dodaj metryki
        batch_size = len(current_batch)
        wait_time = max(time.time() - req.created_at for req in current_batch) * 1000
        
        self.metrics.total_batches += 1
        self.metrics.recent_batch_sizes.append(batch_size)
        self.metrics.recent_wait_times.append(wait_time)
        self.metrics.avg_batch_size = sum(self.metrics.recent_batch_sizes) / len(self.metrics.recent_batch_sizes)
        self.metrics.avg_wait_time = sum(self.metrics.recent_wait_times) / len(self.metrics.recent_wait_times)
        
        # Dodaj do kolejki do przetworzenia
        for request in current_batch:
            await self.pending_requests.put(request)
    
    async def _batch_processor(self):
        """
        Procesor partii - pobiera żądania z kolejki i przetwarza je wsadowo
        gdy zbierze się wystarczająco dużo żądań
        """
        while self.running:
            try:
                # Czekaj na pierwszą wiadomość w kolejce
                first_request = await self.pending_requests.get()
                self.active_batch_count += 1
                
                # Zbierz podobne żądania do przetworzenia wsadowo
                batch = [first_request]
                batch_start_time = time.time()
                
                # Spróbuj pobrać więcej żądań z kolejki
                try:
                    while len(batch) < MAX_BATCH_SIZE and not self.pending_requests.empty():
                        # Pobierz następne żądanie bez czekania
                        next_request = self.pending_requests.get_nowait()
                        batch.append(next_request)
                except asyncio.QueueEmpty:
                    # Nie ma więcej żądań, kontynuuj z obecną partią
                    pass
                
                # Jeśli mamy tylko jedno żądanie, przetwórz je bez wsadowo
                if len(batch) == 1:
                    single_request = batch[0]
                    try:
                        # Wywołaj LLM z pojedynczym żądaniem
                        result = self._llm_call_func(
                            single_request.messages,
                            **single_request.params
                        )
                        # Ustaw wynik w future
                        single_request.future.set_result(result)
                        
                    except Exception as e:
                        # Obsłuż błąd i ustaw wyjątek w future
                        single_request.future.set_exception(e)
                        self.last_error = str(e)
                        self.metrics.error_count += 1
                        print(f"[ERROR] Single request processing error: {e}")
                    
                    # Zaktualizuj metryki
                    self.metrics.total_requests += 1
                    
                else:
                    # Przetwórz partię wsadowo
                    await self._process_batch(batch)
                
                # Zaktualizuj metryki czasu przetwarzania
                processing_time = (time.time() - batch_start_time) * 1000
                self.metrics.recent_processing_times.append(processing_time)
                self.metrics.avg_processing_time = (
                    sum(self.metrics.recent_processing_times) / 
                    len(self.metrics.recent_processing_times)
                )
                
                self.active_batch_count -= 1
                
                # Oznacz zadania jako zakończone w kolejce
                for _ in range(len(batch)):
                    self.pending_requests.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.last_error = str(e)
                self.metrics.error_count += 1
                print(f"[ERROR] Batch processor error: {e}")
                traceback.print_exc()
                
                # Zmniejsz licznik aktywnych partii
                self.active_batch_count -= 1
    
    async def _process_batch(self, batch: List[BatchRequest]):
        """
        Przetwarza partię żądań jednym wywołaniem LLM
        
        Args:
            batch: Lista żądań BatchRequest
        """
        # Oszacowanie oszczędności tokenów
        system_prompt_tokens = 0
        shared_history_tokens = 0
        
        try:
            # Przygotuj wywołania LLM dla każdego żądania w partii
            # TODO: Tutaj należy zaimplementować konkretną logikę wsadową
            # specyficzną dla używanego modelu LLM i API
            
            # Prosta implementacja zastępcza: przetwarzanie sekwencyjne
            # W rzeczywistej implementacji należy użyć bardziej zaawansowanej
            # logiki łączenia żądań w jedno wywołanie API
            for request in batch:
                try:
                    # Wywołaj LLM dla każdego żądania
                    result = self._llm_call_func(
                        request.messages,
                        **request.params
                    )
                    # Ustaw wynik w future
                    request.future.set_result(result)
                    
                except Exception as e:
                    # Obsłuż błąd i ustaw wyjątek w future
                    request.future.set_exception(e)
                    self.last_error = str(e)
                    self.metrics.error_count += 1
                    print(f"[ERROR] Batch request processing error: {e}")
            
            # Zaktualizuj metryki
            self.metrics.total_requests += len(batch)
            
            # Oszacowanie oszczędzonych tokenów (uproszczone)
            # W rzeczywistości należy dokładniej liczyć na podstawie tokenizacji
            token_savings = system_prompt_tokens + shared_history_tokens
            self.metrics.token_savings += token_savings
            
        except Exception as e:
            # Obsłuż błąd całej partii
            for request in batch:
                if not request.future.done():
                    request.future.set_exception(e)
            
            self.last_error = str(e)
            self.metrics.error_count += 1
            print(f"[ERROR] Batch processing error: {e}")
            traceback.print_exc()
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Pobiera aktualne metryki procesora wsadowego
        
        Returns:
            Słownik z metrykami
        """
        return {
            "total_requests": self.metrics.total_requests,
            "total_batches": self.metrics.total_batches,
            "avg_batch_size": round(self.metrics.avg_batch_size, 2),
            "avg_wait_time_ms": round(self.metrics.avg_wait_time, 2),
            "avg_processing_time_ms": round(self.metrics.avg_processing_time, 2),
            "token_savings": self.metrics.token_savings,
            "error_count": self.metrics.error_count,
            "active_batch_count": self.active_batch_count,
            "pending_requests": self.pending_requests.qsize(),
            "is_running": self.running,
            "last_error": self.last_error,
            "recent_batch_sizes": list(self.metrics.recent_batch_sizes),
            "recent_wait_times": list(self.metrics.recent_wait_times),
            "recent_processing_times": list(self.metrics.recent_processing_times)
        }


# ═══════════════════════════════════════════════════════════════════
# INTERFEJS PUBLICZNY
# ═══════════════════════════════════════════════════════════════════

# Globalny procesor wsadowy
batch_processor = LLMBatchProcessor()

async def process_batch(
    messages_list: List[List[Dict[str, Any]]], 
    params_list: List[Dict[str, Any]] = None
) -> List[str]:
    """
    Przetwarza wsadowo listę wiadomości i zwraca listę odpowiedzi
    
    Args:
        messages_list: Lista list wiadomości (każda wewnętrzna lista to wiadomości dla jednego wywołania LLM)
        params_list: Lista parametrów dla każdego wywołania LLM (opcjonalna)
        
    Returns:
        Lista odpowiedzi LLM
    """
    if params_list is None:
        params_list = [{} for _ in range(len(messages_list))]
    
    # Upewnij się, że listy mają tę samą długość
    assert len(messages_list) == len(params_list), "Liczba list wiadomości i parametrów musi być taka sama"
    
    # Uruchom procesor wsadowy, jeśli nie jest uruchomiony
    if not batch_processor.running:
        await batch_processor.start()
    
    # Przygotuj zadania
    tasks = []
    for messages, params in zip(messages_list, params_list):
        task = asyncio.create_task(batch_processor.submit(messages, params))
        tasks.append(task)
    
    # Czekaj na wszystkie zadania
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Obsłuż wyjątki i zwróć wyniki
    processed_results = []
    for result in results:
        if isinstance(result, Exception):
            # W przypadku błędu, zwróć komunikat błędu
            processed_results.append(f"Error: {str(result)}")
        else:
            processed_results.append(result)
    
    return processed_results

async def call_llm_batch(messages: List[Dict[str, Any]], **params) -> str:
    """
    Wywołuje LLM z wykorzystaniem procesora wsadowego
    
    Args:
        messages: Lista wiadomości dla LLM
        **params: Parametry dla LLM
        
    Returns:
        Tekst odpowiedzi LLM
    """
    return await batch_processor.submit(messages, params)

def get_batch_metrics() -> Dict[str, Any]:
    """
    Pobiera aktualne metryki procesora wsadowego
    
    Returns:
        Słownik z metrykami
    """
    return batch_processor.get_metrics()

async def shutdown_batch_processor():
    """Zatrzymuje procesor wsadowy"""
    await batch_processor.stop()


# ═══════════════════════════════════════════════════════════════════
# KOD TESTOWY
# ═══════════════════════════════════════════════════════════════════

async def run_test():
    """Funkcja testowa dla procesora wsadowego"""
    print("=" * 70)
    print("LLM Batch Processor Test")
    print("=" * 70)
    
    # Uruchom procesor wsadowy
    await batch_processor.start()
    
    # Przygotuj przykładowe wiadomości
    test_messages = []
    for i in range(5):
        messages = [
            {"role": "system", "content": "Jesteś pomocnym asystentem AI."},
            {"role": "user", "content": f"Podaj 3 ciekawe fakty o {['kosmosie', 'oceanach', 'górach', 'dinozaurach', 'programowaniu'][i]}"}
        ]
        test_messages.append(messages)
    
    # Parametry dla każdego wywołania
    test_params = [
        {"temperature": 0.7},
        {"temperature": 0.5},
        {"temperature": 0.3},
        {"temperature": 0.7},
        {"temperature": 0.5}
    ]
    
    print(f"Przetwarzanie {len(test_messages)} zapytań wsadowo...")
    start_time = time.time()
    
    # Przetwórz wsadowo
    results = await process_batch(test_messages, test_params)
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"Przetwarzanie zakończone w {duration:.2f} sekund")
    print(f"Średni czas na zapytanie: {(duration / len(test_messages)) * 1000:.2f} ms")
    
    # Wyświetl pierwsze 100 znaków każdej odpowiedzi
    for i, result in enumerate(results):
        print(f"\nOdpowiedź {i+1}: {result[:100]}...")
    
    # Wyświetl metryki
    metrics = get_batch_metrics()
    print("\nMetryki procesora wsadowego:")
    print(f"  Łączna liczba zapytań: {metrics['total_requests']}")
    print(f"  Łączna liczba partii: {metrics['total_batches']}")
    print(f"  Średni rozmiar partii: {metrics['avg_batch_size']}")
    print(f"  Średni czas oczekiwania: {metrics['avg_wait_time_ms']:.2f} ms")
    print(f"  Średni czas przetwarzania: {metrics['avg_processing_time_ms']:.2f} ms")
    print(f"  Oszacowane oszczędności tokenów: {metrics['token_savings']}")
    print(f"  Liczba błędów: {metrics['error_count']}")
    
    # Zatrzymaj procesor wsadowy
    await shutdown_batch_processor()
    print("\nProcesor wsadowy zatrzymany")


if __name__ == "__main__":
    # Uruchom test
    asyncio.run(run_test())