#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
batch_research.py - Parallel Multi-Query Web Research
FULL LOGIC - ZERO PLACEHOLDERS!
"""
import asyncio
import time
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from .helpers import log_info, log_error
from .research import perform_research  # Import existing research function


# ═══════════════════════════════════════════════════════════════════
# BATCH RESEARCH ENGINE
# ═══════════════════════════════════════════════════════════════════

class BatchResearchEngine:
    """Parallel multi-query research engine"""
    
    def __init__(self, max_workers: int = 5, timeout_per_query: int = 30):
        """
        Initialize batch research engine
        
        Args:
            max_workers: Max parallel research threads
            timeout_per_query: Timeout per query in seconds
        """
        self.max_workers = max_workers
        self.timeout_per_query = timeout_per_query
        log_info(f"[BATCH_RESEARCH] Initialized with max_workers={max_workers}, timeout={timeout_per_query}s")
    
    def research_single_query(self, query: str, memory_manager=None) -> Dict[str, Any]:
        """
        Research a single query (wrapper for existing research function)
        
        Args:
            query: Research query
            memory_manager: Memory manager instance (optional)
            
        Returns:
            dict: Research results
        """
        start_time = time.time()
        
        try:
            # Use existing research.py logic
            results = perform_research(query, memory_manager=memory_manager)
            
            elapsed = time.time() - start_time
            log_info(f"[BATCH_RESEARCH] Query '{query[:50]}...' completed in {elapsed:.2f}s")
            
            return {
                "query": query,
                "success": True,
                "results": results,
                "elapsed_time": elapsed,
                "timestamp": time.time()
            }
            
        except Exception as e:
            elapsed = time.time() - start_time
            log_error(e, f"BATCH_RESEARCH_QUERY: {query[:50]}")
            
            return {
                "query": query,
                "success": False,
                "error": str(e),
                "elapsed_time": elapsed,
                "timestamp": time.time()
            }
    
    def research_batch(
        self,
        queries: List[str],
        memory_manager=None,
        deduplicate: bool = True
    ) -> Dict[str, Any]:
        """
        Research multiple queries in parallel
        
        Args:
            queries: List of research queries
            memory_manager: Memory manager instance
            deduplicate: Remove duplicate queries
            
        Returns:
            dict: Batch research results
        """
        batch_start = time.time()
        
        # Deduplicate queries
        if deduplicate:
            original_count = len(queries)
            queries = list(set(queries))
            if len(queries) < original_count:
                log_info(f"[BATCH_RESEARCH] Deduplicated {original_count} → {len(queries)} queries")
        
        if not queries:
            return {
                "success": False,
                "error": "No queries provided",
                "total_queries": 0,
                "successful": 0,
                "failed": 0,
                "results": []
            }
        
        log_info(f"[BATCH_RESEARCH] Starting batch research for {len(queries)} queries (max_workers={self.max_workers})")
        
        # Execute in parallel
        results = []
        successful = 0
        failed = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_query = {
                executor.submit(self.research_single_query, query, memory_manager): query
                for query in queries
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_query):
                query = future_to_query[future]
                try:
                    result = future.result(timeout=self.timeout_per_query)
                    results.append(result)
                    
                    if result["success"]:
                        successful += 1
                    else:
                        failed += 1
                        
                except TimeoutError:
                    log_error(Exception(f"Timeout for query: {query}"), "BATCH_RESEARCH_TIMEOUT")
                    results.append({
                        "query": query,
                        "success": False,
                        "error": "Timeout",
                        "elapsed_time": self.timeout_per_query,
                        "timestamp": time.time()
                    })
                    failed += 1
                    
                except Exception as e:
                    log_error(e, f"BATCH_RESEARCH_FUTURE: {query}")
                    results.append({
                        "query": query,
                        "success": False,
                        "error": str(e),
                        "elapsed_time": 0,
                        "timestamp": time.time()
                    })
                    failed += 1
        
        batch_elapsed = time.time() - batch_start
        
        # Calculate stats
        avg_time = sum(r["elapsed_time"] for r in results) / len(results) if results else 0
        total_facts = sum(len(r.get("results", {}).get("facts", [])) for r in results if r["success"])
        
        log_info(f"[BATCH_RESEARCH] Batch completed: {successful}/{len(queries)} successful in {batch_elapsed:.2f}s (avg {avg_time:.2f}s per query)")
        
        return {
            "success": True,
            "total_queries": len(queries),
            "successful": successful,
            "failed": failed,
            "total_facts": total_facts,
            "batch_elapsed_time": batch_elapsed,
            "avg_query_time": avg_time,
            "speedup_factor": (avg_time * len(queries)) / batch_elapsed if batch_elapsed > 0 else 0,
            "results": results,
            "timestamp": time.time()
        }
    
    def research_auto_expand(
        self,
        base_query: str,
        expansions: List[str],
        memory_manager=None
    ) -> Dict[str, Any]:
        """
        Auto-expand a query with multiple perspectives
        
        Example:
            base_query = "Python async"
            expansions = ["tutorial", "best practices", "performance"]
            → Research: "Python async tutorial", "Python async best practices", "Python async performance"
        
        Args:
            base_query: Base query
            expansions: List of expansion terms
            memory_manager: Memory manager instance
            
        Returns:
            dict: Expanded research results
        """
        expanded_queries = [f"{base_query} {exp}" for exp in expansions]
        
        log_info(f"[BATCH_RESEARCH] Auto-expanding '{base_query}' into {len(expanded_queries)} queries")
        
        return self.research_batch(expanded_queries, memory_manager=memory_manager)
    
    def research_multi_aspect(
        self,
        topic: str,
        aspects: Optional[List[str]] = None,
        memory_manager=None
    ) -> Dict[str, Any]:
        """
        Research multiple aspects of a topic
        
        Default aspects: definition, examples, use cases, best practices, common mistakes
        
        Args:
            topic: Topic to research
            aspects: Custom aspects (or use defaults)
            memory_manager: Memory manager instance
            
        Returns:
            dict: Multi-aspect research results
        """
        if aspects is None:
            aspects = [
                "definition",
                "examples",
                "use cases",
                "best practices",
                "common mistakes",
                "latest trends"
            ]
        
        queries = [f"{topic} {aspect}" for aspect in aspects]
        
        log_info(f"[BATCH_RESEARCH] Multi-aspect research for '{topic}' with {len(aspects)} aspects")
        
        return self.research_batch(queries, memory_manager=memory_manager)
    
    def research_comparative(
        self,
        items: List[str],
        comparison_aspect: str = "comparison",
        memory_manager=None
    ) -> Dict[str, Any]:
        """
        Comparative research across multiple items
        
        Example:
            items = ["Python", "JavaScript", "Rust"]
            → Research: "Python vs JavaScript comparison", "Python vs Rust comparison", etc.
        
        Args:
            items: Items to compare
            comparison_aspect: What to compare (default: "comparison")
            memory_manager: Memory manager instance
            
        Returns:
            dict: Comparative research results
        """
        queries = []
        
        # Generate pairwise comparisons
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                query = f"{items[i]} vs {items[j]} {comparison_aspect}"
                queries.append(query)
        
        # Add individual queries
        for item in items:
            queries.append(f"{item} {comparison_aspect}")
        
        log_info(f"[BATCH_RESEARCH] Comparative research for {len(items)} items → {len(queries)} queries")
        
        return self.research_batch(queries, memory_manager=memory_manager)
    
    def research_temporal(
        self,
        topic: str,
        time_periods: Optional[List[str]] = None,
        memory_manager=None
    ) -> Dict[str, Any]:
        """
        Research topic across different time periods
        
        Args:
            topic: Topic to research
            time_periods: Time periods (or use defaults)
            memory_manager: Memory manager instance
            
        Returns:
            dict: Temporal research results
        """
        if time_periods is None:
            time_periods = [
                "latest 2024",
                "2023",
                "2022",
                "historical"
            ]
        
        queries = [f"{topic} {period}" for period in time_periods]
        
        log_info(f"[BATCH_RESEARCH] Temporal research for '{topic}' across {len(time_periods)} periods")
        
        return self.research_batch(queries, memory_manager=memory_manager)


# ═══════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE & SHORTCUTS
# ═══════════════════════════════════════════════════════════════════

_global_batch_engine = None


def get_batch_engine() -> BatchResearchEngine:
    """Get global batch research engine"""
    global _global_batch_engine
    if _global_batch_engine is None:
        _global_batch_engine = BatchResearchEngine()
    return _global_batch_engine


def batch_research(queries: List[str], memory_manager=None) -> Dict[str, Any]:
    """Shortcut: batch research"""
    return get_batch_engine().research_batch(queries, memory_manager=memory_manager)


def auto_expand(base_query: str, expansions: List[str], memory_manager=None) -> Dict[str, Any]:
    """Shortcut: auto-expand research"""
    return get_batch_engine().research_auto_expand(base_query, expansions, memory_manager)


def multi_aspect(topic: str, aspects: Optional[List[str]] = None, memory_manager=None) -> Dict[str, Any]:
    """Shortcut: multi-aspect research"""
    return get_batch_engine().research_multi_aspect(topic, aspects, memory_manager)


def comparative(items: List[str], comparison_aspect: str = "comparison", memory_manager=None) -> Dict[str, Any]:
    """Shortcut: comparative research"""
    return get_batch_engine().research_comparative(items, comparison_aspect, memory_manager)


def temporal(topic: str, time_periods: Optional[List[str]] = None, memory_manager=None) -> Dict[str, Any]:
    """Shortcut: temporal research"""
    return get_batch_engine().research_temporal(topic, time_periods, memory_manager)
