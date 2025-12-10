#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Core modules for Mordzix - Modularized architecture
"""

# Standard library imports
import dataclasses
from dataclasses import dataclass, asdict

# Config
from .config import *

# Ensure DB directory exists very early
def _ensure_db_dir():
    try:
        from pathlib import Path
        p = Path(DB_PATH)
        p.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        pass
_ensure_db_dir()


# Auth  
from .auth import *

# Helpers
from .helpers import *

# LLM
from .llm import *

# Memory (biggest module!)
from .memory import *

# Tools
from .tools import *

# Research
from .research import *

# Semantic
from .semantic import *

# Writing
from .writing import *

# Executor
from .executor import *

# Endpoints (for core/app.py imports)
try:
    from . import travel_endpoint
    from . import memory_endpoint
except ImportError as e:
    import warnings
    warnings.warn(f"Could not import endpoints: {e}")
    travel_endpoint = None
    memory_endpoint = None

__version__ = "3.3.0"

# Compatibility functions
def _save_turn_to_memory(user_message, assistant_message, user_id="default"):
    """Compatibility function for saving conversation turns to memory"""
    try:
        stm_add("user", user_message, user_id)
        stm_add("assistant", assistant_message, user_id)
        return True
    except:
        return False

def _auto_learn_from_turn(user_message, assistant_message):
    """Compatibility function for auto-learning from conversation"""
    # This is a stub - implement if needed
    return True

# Main exports list
__all__ = [
    # Config
    "AUTH_TOKEN", "BASE_DIR", "DB_PATH", "MORDZIX_SYSTEM_PROMPT",
    "CONTEXT_DICTIONARIES", "FASHION", "PL_SYNONYMS", "PL_COLLOC",
    
    # Auth
    "check_auth", "auth_dependency", "get_ip_address", "get_current_user",
    
    # Helpers
    "log_info", "log_warning", "log_error",
    "http_get", "http_get_json", "http_post_json",
    "normalize_text", "tokenize", "make_id",
    "tfidf_vec", "tfidf_cosine", "cosine_similarity",
    "embed_many", "tag_pii", "extract_profile_info",
    
    # LLM
    "call_llm", "call_llm_once", "call_llm_stream",
    
    # Memory
    "memory_manager", "time_manager",
    "AdvancedMemoryManager", "TimeManager",
    "ltm_add", "ltm_search_hybrid", "stm_add", "stm_get_context",
    "memory_add", "memory_get", "psy_get", "psy_tune",
    "cache_get", "cache_put", "system_stats",
    "_save_turn_to_memory", "_auto_learn_from_turn",  # Added compatibility functions
    
    # Tools
    "InternetSearcher", "internet_searcher",
    "tools_time_handler", "tools_search_handler",
    "recommendation_engine", "crypto_analyzer", "code_reviewer", "workflow_engine",
    
    # Research
    "autonauka", "web_learn", "answer_with_sources",
    "research_collect", "travel_search",
    
    # Semantic
    "SemanticAnalyzer", "semantic_analyzer",
    "semantic_analyze", "semantic_analyze_conversation",
    
    # Writing
    "write_creative_boost", "write_vinted", "write_social",
    "analyze_fashion_text", "write_auction_pro",
    "write_masterpiece_article", "write_sales_masterpiece", "write_technical_masterpiece",
    
    # Executor
    "Programista", "ExecResult", "dataclass", "asdict",  # Added dataclass exports
]
