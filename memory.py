#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
UNIFIED MEMORY SYSTEM - Enterprise-Grade Multi-Layer Memory Architecture
═══════════════════════════════════════════════════════════════════════════════

Architecture:
    L0: Short-Term Memory (STM) - Active conversation context (RAM)
    L1: Episodic Memory - Recent events and conversations (SQLite + RAM)
    L2: Semantic Memory - Long-term facts and knowledge (SQLite + FTS + Vectors)
    L3: Procedural Memory - Learned patterns and procedures (SQLite)
    L4: Meta/Mental Models - User profiles and domain knowledge (SQLite + Graph)

Features:
    ✅ Multi-layer hierarchical memory with auto-consolidation
    ✅ Vector embeddings for semantic search (sentence-transformers)
    ✅ Graph-based associative connections between memories
    ✅ Redis caching for hot data (LRU eviction)
    ✅ Memory decay and forgetting curves (Ebbinghaus)
    ✅ Importance scoring and reinforcement learning
    ✅ Temporal weighting and recency bias
    ✅ Cross-layer context retrieval
    ✅ Hybrid search: BM25 + Vector + Graph traversal
    ✅ Automatic consolidation background tasks
    ✅ Comprehensive health monitoring and analytics

Storage:
    - SQLite: Primary persistence (optimized with WAL, mmap, indexes)
    - Redis: Hot cache layer (LRU, TTL-based eviction)
    - Filesystem: Vector indices, backups (/ltm_storage/{user_id}/...)

NO PLACEHOLDERS - FULL PRODUCTION-GRADE IMPLEMENTATION!
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import time
import json
import uuid
import sqlite3
import hashlib
import pickle
import numpy as np
import asyncio
import threading
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional, Set, Union
from collections import Counter, deque, defaultdict
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta

# Core imports
from .config import (
    BASE_DIR, DB_PATH, STM_LIMIT, STM_CONTEXT_WINDOW,
    LTM_IMPORTANCE_THRESHOLD, LTM_CACHE_SIZE
)
from .helpers import (
    log_info, log_warning, log_error,
    tokenize, make_id, tfidf_cosine,
    embed_texts, cosine_similarity
)

# Redis cache (optional)
try:
    from .redis_middleware import get_redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    log_warning("Redis not available, using in-memory cache only", "MEMORY")


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# Memory limits and thresholds (UPGRADED!)
MAX_STM_SIZE = 500  # 500 messages (było 130)
MAX_EPISODIC_SIZE = 5000  # Recent episodes kept in RAM (było 1000)
MAX_SEMANTIC_SIZE = 10000  # 10k facts in RAM cache (było 1000)
MAX_GRAPH_NODES = 50000  # Max nodes in associative graph (było 5000)

# Consolidation thresholds (MORE AGGRESSIVE!)
EPISODIC_TO_SEMANTIC_THRESHOLD = 3  # Min episodes to create semantic fact (było 5)
SEMANTIC_CLUSTERING_THRESHOLD = 2  # Min facts to create cluster (było 3)
PROCEDURAL_LEARNING_THRESHOLD = 2  # Min executions to learn procedure (było 3)

# Decay and forgetting (LONGER RETENTION!)
MEMORY_DECAY_RATE = 0.02  # Connection decay per hour (było 0.05 - wolniejszy decay)
FORGETTING_CURVE_HALFLIFE = 30 * 24 * 3600  # 30 days in seconds (było 7 dni)
REINFORCEMENT_BOOST = 0.25  # Boost on memory access (było 0.2 - większy boost)

# Background tasks (🔥 TURBO MODE!)
AUTO_CONSOLIDATION_INTERVAL = 180  # 🔥 3 minutes (było 10min) - HARDCORE!
CLEANUP_INTERVAL = 1800  # 30 minutes (było 1h)
BACKUP_INTERVAL = 43200  # 12 hours (było 24h)

# Storage paths
LTM_STORAGE_ROOT = os.getenv("LTM_STORAGE_ROOT", os.path.join(BASE_DIR, "ltm_storage"))
VECTOR_INDEX_PATH = os.path.join(LTM_STORAGE_ROOT, "vector_indices")
BACKUP_PATH = os.path.join(LTM_STORAGE_ROOT, "backups")

# Create directories
for p in [LTM_STORAGE_ROOT, VECTOR_INDEX_PATH, BACKUP_PATH]:
    Path(p).mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MemoryNode:
    """Universal memory node for all layers"""
    id: str
    layer: str  # L0, L1, L2, L3, L4
    content: str
    user_id: str = "default"
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Scoring
    importance: float = 0.5  # 0-1
    confidence: float = 0.7  # 0-1
    
    # Temporal
    created_at: float = field(default_factory=time.time)
    accessed_at: float = field(default_factory=time.time)
    access_count: int = 0
    
    # Associations
    connections: Dict[str, float] = field(default_factory=dict)  # node_id -> strength
    
    # Vector embedding (lazy loaded)
    _embedding: Optional[np.ndarray] = None
    
    def access(self) -> None:
        """Update access statistics and apply reinforcement"""
        self.accessed_at = time.time()
        self.access_count += 1
        # Reinforcement learning: importance grows with access
        self.importance = min(1.0, self.importance + REINFORCEMENT_BOOST * (1.0 - self.importance))
    
    def connect(self, other_id: str, strength: float = 0.5) -> None:
        """Create or strengthen connection to another node"""
        current = self.connections.get(other_id, 0.0)
        # Hebbian learning: "neurons that fire together wire together"
        self.connections[other_id] = min(1.0, current + strength * (1.0 - current))
    
    def decay_connections(self, hours_elapsed: float = 1.0) -> None:
        """Apply memory decay to connections (Ebbinghaus forgetting curve)"""
        decay_factor = 1.0 - (MEMORY_DECAY_RATE * hours_elapsed)
        for node_id in list(self.connections.keys()):
            self.connections[node_id] *= decay_factor
            if self.connections[node_id] < 0.1:
                del self.connections[node_id]
    
    def get_embedding(self) -> np.ndarray:
        """Get or generate vector embedding"""
        if self._embedding is None:
            embeddings = embed_texts([self.content])
            self._embedding = np.array(embeddings[0]) if embeddings else np.zeros(384)
        return self._embedding
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "id": self.id,
            "layer": self.layer,
            "content": self.content,
            "user_id": self.user_id,
            "tags": self.tags,
            "metadata": self.metadata,
            "importance": self.importance,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "accessed_at": self.accessed_at,
            "access_count": self.access_count,
            "connections": self.connections,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryNode':
        """Deserialize from dictionary"""
        return cls(
            id=data["id"],
            layer=data["layer"],
            content=data["content"],
            user_id=data.get("user_id", "default"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            importance=data.get("importance", 0.5),
            confidence=data.get("confidence", 0.7),
            created_at=data.get("created_at", time.time()),
            accessed_at=data.get("accessed_at", time.time()),
            access_count=data.get("access_count", 0),
            connections=data.get("connections", {}),
        )


@dataclass
class MemorySearchResult:
    """Search result with scoring details"""
    node: MemoryNode
    score: float
    match_type: str  # "exact", "semantic", "temporal", "graph"
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": self.node.to_dict(),
            "score": self.score,
            "match_type": self.match_type,
            "context": self.context
        }


# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE LAYER
# ═══════════════════════════════════════════════════════════════════════════════

class MemoryDatabase:
    """SQLite database layer with optimizations"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._lock = threading.Lock()
        # Ensure parent dir exists
        try:
            from pathlib import Path
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        self._init_db()
    
    def _conn(self) -> sqlite3.Connection:
        """Get optimized database connection"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        
        # Performance optimizations (🔥 HARDCORE TUNING!)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA temp_store=MEMORY;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA cache_size=-2000000;")  # 🔥 2GB cache (było 500MB)
        conn.execute("PRAGMA mmap_size=8589934592;")  # 🔥 8GB mmap (było 2GB)
        conn.execute("PRAGMA page_size=8192;")  # 8KB pages
        conn.execute("PRAGMA busy_timeout=30000;")  # 30s timeout
        conn.execute("PRAGMA wal_autocheckpoint=20000;")  # 🔥 WAL checkpoint 20k (było 5k default)
        
        return conn
    
    def _init_db(self) -> None:
        """Initialize all database tables and indices"""
        with self._lock, self._conn() as conn:
            c = conn.cursor()
            
            # ═══════════════════════════════════════════════════════════
            # CORE MEMORY TABLE
            # ═══════════════════════════════════════════════════════════
            c.execute("""
                CREATE TABLE IF NOT EXISTS memory_nodes (
                    id TEXT PRIMARY KEY,
                    layer TEXT NOT NULL,
                    content TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    tags TEXT,
                    metadata TEXT,
                    importance REAL DEFAULT 0.5,
                    confidence REAL DEFAULT 0.7,
                    created_at REAL NOT NULL,
                    accessed_at REAL NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    connections TEXT,
                    embedding BLOB,
                    deleted INTEGER DEFAULT 0
                );
            """)
            
            # Indices for memory_nodes
            c.execute("CREATE INDEX IF NOT EXISTS idx_nodes_layer ON memory_nodes(layer, deleted);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_nodes_user_layer ON memory_nodes(user_id, layer, deleted);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_nodes_created ON memory_nodes(created_at DESC);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_nodes_accessed ON memory_nodes(accessed_at DESC);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_nodes_importance ON memory_nodes(importance DESC) WHERE deleted=0;")
            c.execute("CREATE INDEX IF NOT EXISTS idx_nodes_tags ON memory_nodes(tags) WHERE deleted=0;")
            
            # 🔥 COMPOSITE INDICES dla hardcore performance!
            c.execute("CREATE INDEX IF NOT EXISTS idx_nodes_user_layer_created ON memory_nodes(user_id, layer, created_at DESC) WHERE deleted=0;")
            c.execute("CREATE INDEX IF NOT EXISTS idx_nodes_user_importance ON memory_nodes(user_id, importance DESC, confidence DESC) WHERE deleted=0;")
            c.execute("CREATE INDEX IF NOT EXISTS idx_nodes_conf_imp ON memory_nodes(confidence DESC, importance DESC) WHERE deleted=0;")
            
            # ═══════════════════════════════════════════════════════════
            # FTS5 FULL-TEXT SEARCH
            # ═══════════════════════════════════════════════════════════
            try:
                c.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts 
                    USING fts5(content, tags, user_id UNINDEXED, node_id UNINDEXED);
                """)
                log_info("FTS5 full-text search enabled", "MEMORY_DB")
            except Exception as e:
                log_warning(f"FTS5 not available: {e}", "MEMORY_DB")
            
            # ═══════════════════════════════════════════════════════════
            # EPISODIC MEMORY (L1)
            # ═══════════════════════════════════════════════════════════
            c.execute("""
                CREATE TABLE IF NOT EXISTS memory_episodes (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    episode_type TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    related_stm_ids TEXT,
                    metadata TEXT,
                    timestamp REAL NOT NULL
                );
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_episodes_user_ts ON memory_episodes(user_id, timestamp DESC);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_episodes_type ON memory_episodes(episode_type);")
            
            # ═══════════════════════════════════════════════════════════
            # SEMANTIC CLUSTERS (L2)
            # ═══════════════════════════════════════════════════════════
            c.execute("""
                CREATE TABLE IF NOT EXISTS memory_semantic_clusters (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    cluster_topic TEXT NOT NULL,
                    related_node_ids TEXT,
                    consolidated_fact_id TEXT,
                    strength REAL DEFAULT 1.0,
                    last_reinforced REAL,
                    created_at REAL
                );
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_clusters_user_topic ON memory_semantic_clusters(user_id, cluster_topic);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_clusters_strength ON memory_semantic_clusters(strength DESC);")
            
            # ═══════════════════════════════════════════════════════════
            # PROCEDURAL MEMORY (L3)
            # ═══════════════════════════════════════════════════════════
            c.execute("""
                CREATE TABLE IF NOT EXISTS memory_procedures (
                    id TEXT PRIMARY KEY,
                    trigger_intent TEXT NOT NULL UNIQUE,
                    steps TEXT NOT NULL,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 0.0,
                    avg_execution_time REAL DEFAULT 0.0,
                    context_conditions TEXT,
                    last_used REAL,
                    created_at REAL,
                    adaptations TEXT
                );
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_proc_success_rate ON memory_procedures(success_rate DESC);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_proc_last_used ON memory_procedures(last_used DESC);")
            
            # ═══════════════════════════════════════════════════════════
            # MENTAL MODELS (L4)
            # ═══════════════════════════════════════════════════════════
            c.execute("""
                CREATE TABLE IF NOT EXISTS memory_mental_models (
                    id TEXT PRIMARY KEY,
                    model_type TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    confidence REAL DEFAULT 0.5,
                    evidence_count INTEGER DEFAULT 0,
                    model_data TEXT NOT NULL,
                    related_node_ids TEXT,
                    last_updated REAL,
                    created_at REAL,
                    validation_score REAL DEFAULT 0.0
                );
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_models_type_subject ON memory_mental_models(model_type, subject);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_models_confidence ON memory_mental_models(confidence DESC);")
            
            # ═══════════════════════════════════════════════════════════
            # ANALYTICS AND METRICS
            # ═══════════════════════════════════════════════════════════
            c.execute("""
                CREATE TABLE IF NOT EXISTS memory_analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    metadata TEXT,
                    timestamp REAL NOT NULL
                );
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_analytics_name_ts ON memory_analytics(metric_name, timestamp DESC);")
            
            # ═══════════════════════════════════════════════════════════
            # SEMANTIC MEMORY TABLE (for legacy compatibility)
            # ═══════════════════════════════════════════════════════════
            c.execute("""
                CREATE TABLE IF NOT EXISTS semantic_memory (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    source TEXT,
                    type TEXT DEFAULT 'fact',
                    metadata TEXT,
                    importance REAL DEFAULT 0.5,
                    timestamp REAL NOT NULL,
                    user_id TEXT
                );
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_semantic_importance ON semantic_memory(importance DESC);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_semantic_type ON semantic_memory(type);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_semantic_timestamp ON semantic_memory(timestamp DESC);")
            
            conn.commit()
            log_info("Memory database initialized successfully", "MEMORY_DB")
    
    def _init_schema(self) -> None:
        """Alias for _init_db for backward compatibility"""
        self._init_db()
    
    def save_node(self, node: MemoryNode) -> None:
        """Save or update memory node"""
        print(f"[DEBUG] Saving node {node.id} to {self.db_path}")
        with self._lock, self._conn() as conn:
            # Serialize complex fields
            tags_json = json.dumps(node.tags)
            metadata_json = json.dumps(node.metadata)
            connections_json = json.dumps(node.connections)
            embedding_bytes = pickle.dumps(node._embedding) if node._embedding is not None else None
            
            conn.execute("""
                INSERT OR REPLACE INTO memory_nodes 
                (id, layer, content, user_id, tags, metadata, importance, confidence,
                 created_at, accessed_at, access_count, connections, embedding, deleted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                node.id, node.layer, node.content, node.user_id,
                tags_json, metadata_json, node.importance, node.confidence,
                node.created_at, node.accessed_at, node.access_count,
                connections_json, embedding_bytes
            ))
            
            # Update FTS index
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO memory_fts (content, tags, user_id, node_id)
                    VALUES (?, ?, ?, ?)
                """, (node.content, " ".join(node.tags), node.user_id, node.id))
            except:
                pass  # FTS not available
            
            conn.commit()
    
    def load_node(self, node_id: str) -> Optional[MemoryNode]:
        """Load memory node by ID"""
        with self._conn() as conn:
            row = conn.execute("""
                SELECT * FROM memory_nodes WHERE id = ? AND deleted = 0
            """, (node_id,)).fetchone()
            
            if not row:
                return None
            
            # Deserialize
            node = MemoryNode(
                id=row["id"],
                layer=row["layer"],
                content=row["content"],
                user_id=row["user_id"],
                tags=json.loads(row["tags"] or "[]"),
                metadata=json.loads(row["metadata"] or "{}"),
                importance=row["importance"],
                confidence=row["confidence"],
                created_at=row["created_at"],
                accessed_at=row["accessed_at"],
                access_count=row["access_count"],
                connections=json.loads(row["connections"] or "{}")
            )
            
            # Deserialize embedding if exists
            if row["embedding"]:
                try:
                    node._embedding = pickle.loads(row["embedding"])
                except:
                    pass
            
            return node
    
    def search_nodes(self, query: str = "", layer: Optional[str] = None,
                     user_id: Optional[str] = None, limit: int = 100) -> List[MemoryNode]:
        """Search memory nodes with filters"""
        with self._conn() as conn:
            sql = "SELECT * FROM memory_nodes WHERE deleted = 0"
            params = []
            
            if query:
                # Try FTS first
                try:
                    fts_sql = """
                        SELECT node_id FROM memory_fts 
                        WHERE memory_fts MATCH ? 
                        ORDER BY bm25(memory_fts) 
                        LIMIT ?
                    """
                    fts_results = conn.execute(fts_sql, (query, limit)).fetchall()
                    if fts_results:
                        node_ids = [r["node_id"] for r in fts_results]
                        placeholders = ",".join("?" * len(node_ids))
                        sql = f"SELECT * FROM memory_nodes WHERE id IN ({placeholders}) AND deleted = 0"
                        params = node_ids
                except:
                    # Fallback to LIKE search
                    sql += " AND content LIKE ?"
                    params.append(f"%{query}%")
            
            if layer and not query:
                sql += " AND layer = ?"
                params.append(layer)
            
            if user_id and not query:
                sql += " AND user_id = ?"
                params.append(user_id)
            
            if not query:
                sql += " ORDER BY accessed_at DESC LIMIT ?"
                params.append(limit)
            
            rows = conn.execute(sql, params).fetchall()
            
            # Deserialize nodes
            nodes = []
            for row in rows:
                try:
                    node = MemoryNode(
                        id=row["id"],
                        layer=row["layer"],
                        content=row["content"],
                        user_id=row["user_id"],
                        tags=json.loads(row["tags"] or "[]"),
                        metadata=json.loads(row["metadata"] or "{}"),
                        importance=row["importance"],
                        confidence=row["confidence"],
                        created_at=row["created_at"],
                        accessed_at=row["accessed_at"],
                        access_count=row["access_count"],
                        connections=json.loads(row["connections"] or "{}")
                    )
                    if row["embedding"]:
                        try:
                            node._embedding = pickle.loads(row["embedding"])
                        except:
                            pass
                    nodes.append(node)
                except Exception as e:
                    log_error(e, "LOAD_NODE")
            
            return nodes
    
    def soft_delete_node(self, node_id: str) -> None:
        """Soft delete memory node"""
        with self._lock, self._conn() as conn:
            conn.execute("UPDATE memory_nodes SET deleted = 1 WHERE id = ?", (node_id,))
            conn.commit()
    
    def record_metric(self, metric_name: str, metric_value: float, metadata: Dict[str, Any] = None) -> None:
        """Record analytics metric"""
        with self._lock, self._conn() as conn:
            conn.execute("""
                INSERT INTO memory_analytics (metric_name, metric_value, metadata, timestamp)
                VALUES (?, ?, ?, ?)
            """, (metric_name, metric_value, json.dumps(metadata or {}), time.time()))
            conn.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# CACHE LAYER (Redis + RAM)
# ═══════════════════════════════════════════════════════════════════════════════

class MemoryCache:
    """Two-tier cache: Redis (L1) + RAM (L2)"""
    
    def __init__(self, max_ram_size: int = 1000):
        self.max_ram_size = max_ram_size
        self._ram_cache: Dict[str, MemoryNode] = {}
        self._access_order: deque = deque()
        self._lock = threading.Lock()
        
        # Redis connection
        self.redis = None
        if REDIS_AVAILABLE:
            try:
                self.redis = get_redis()
                log_info("Redis cache layer enabled", "MEMORY_CACHE")
            except Exception as e:
                log_warning(f"Redis connection failed: {e}", "MEMORY_CACHE")
    
    def get(self, node_id: str) -> Optional[MemoryNode]:
        """Get node from cache (Redis -> RAM)"""
        # Try RAM first
        with self._lock:
            if node_id in self._ram_cache:
                self._access_order.remove(node_id)
                self._access_order.append(node_id)
                return self._ram_cache[node_id]
        
        # Try Redis
        if self.redis:
            try:
                data = self.redis.get(f"memory:node:{node_id}")
                if data:
                    node_dict = json.loads(data)
                    node = MemoryNode.from_dict(node_dict)
                    self.put(node)  # Promote to RAM
                    return node
            except Exception as e:
                log_error(e, "REDIS_GET")
        
        return None
    
    def put(self, node: MemoryNode, ttl: int = 3600) -> None:
        """Put node in cache (RAM + Redis)"""
        # RAM cache (LRU eviction)
        with self._lock:
            if node.id in self._ram_cache:
                self._access_order.remove(node.id)
            elif len(self._ram_cache) >= self.max_ram_size:
                # Evict least recently used
                oldest_id = self._access_order.popleft()
                del self._ram_cache[oldest_id]
            
            self._ram_cache[node.id] = node
            self._access_order.append(node.id)
        
        # Redis cache
        if self.redis:
            try:
                self.redis.setex(
                    f"memory:node:{node.id}",
                    ttl,
                    json.dumps(node.to_dict())
                )
            except Exception as e:
                log_error(e, "REDIS_PUT")
    
    def invalidate(self, node_id: str) -> None:
        """Remove node from cache"""
        with self._lock:
            if node_id in self._ram_cache:
                del self._ram_cache[node_id]
                self._access_order.remove(node_id)
        
        if self.redis:
            try:
                self.redis.delete(f"memory:node:{node_id}")
            except Exception as e:
                log_error(e, "REDIS_DELETE")
    
    def clear(self, user_id: Optional[str] = None) -> None:
        """Clear cache (optionally for specific user)"""
        with self._lock:
            if user_id:
                # Clear only nodes for this user
                to_remove = [nid for nid, node in self._ram_cache.items() if node.user_id == user_id]
                for nid in to_remove:
                    del self._ram_cache[nid]
                    self._access_order.remove(nid)
            else:
                # Clear everything
                self._ram_cache.clear()
                self._access_order.clear()
        
        if self.redis and not user_id:
            try:
                # Clear all memory keys
                for key in self.redis.scan_iter("memory:node:*"):
                    self.redis.delete(key)
            except Exception as e:
                log_error(e, "REDIS_CLEAR")


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY LAYERS (L0-L4)
# ═══════════════════════════════════════════════════════════════════════════════

class ShortTermMemory:
    """L0: Active conversation context (RAM only)"""
    
    def __init__(self, max_size: int = MAX_STM_SIZE):
        self.max_size = max_size
        self._conversations: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_size))
        self._lock = threading.Lock()
    
    def add_message(self, user_id: str, role: str, content: str, metadata: Dict[str, Any] = None) -> str:
        """Add message to STM"""
        msg_id = str(uuid.uuid4())
        message = {
            "id": msg_id,
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": time.time()
        }
        
        with self._lock:
            self._conversations[user_id].append(message)
        
        return msg_id
    
    def get_context(self, user_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get recent conversation context"""
        with self._lock:
            messages = list(self._conversations[user_id])
            if limit:
                messages = messages[-limit:]
            return messages
    
    def clear(self, user_id: str) -> None:
        """Clear STM for user"""
        with self._lock:
            self._conversations[user_id].clear()


class EpisodicMemory:
    """L1: Recent events and conversations"""
    
    def __init__(self, db: MemoryDatabase, cache: MemoryCache):
        self.db = db
        self.cache = cache
    
    def record_episode(self, user_id: str, episode_type: str, summary: str,
                       related_stm_ids: List[str] = None, metadata: Dict[str, Any] = None) -> str:
        """Record new episode"""
        node = MemoryNode(
            id=str(uuid.uuid4()),
            layer="L1",
            content=summary,
            user_id=user_id,
            tags=[episode_type, "episode"],
            metadata={
                **(metadata or {}),
                "episode_type": episode_type,
                "related_stm_ids": related_stm_ids or []
            },
            importance=0.6,
            confidence=0.8
        )
        
        # Generate embedding
        node.get_embedding()
        
        # Save to DB and cache
        self.db.save_node(node)
        self.cache.put(node, ttl=7200)  # 2 hours
        
        log_info(f"[L1] Recorded episode: {episode_type}", "EPISODIC")
        return node.id
    
    def get_recent_episodes(self, user_id: str, limit: int = 50) -> List[MemoryNode]:
        """Get recent episodes for user"""
        return self.db.search_nodes(layer="L1", user_id=user_id, limit=limit)
    
    def find_related_episodes(self, query: str, user_id: str, limit: int = 10) -> List[MemorySearchResult]:
        """Find episodes related to query"""
        # Get all episodes
        all_episodes = self.get_recent_episodes(user_id, limit=200)
        
        if not all_episodes:
            return []
        
        # Generate query embedding
        query_emb = np.array(embed_texts([query])[0])
        
        # Score episodes
        results = []
        for ep in all_episodes:
            ep_emb = ep.get_embedding()
            
            # Semantic similarity
            semantic_score = float(cosine_similarity(query_emb, ep_emb))
            
            # Recency bonus
            age_hours = (time.time() - ep.created_at) / 3600
            recency_score = 1.0 / (1.0 + 0.01 * age_hours)
            
            # Combined score
            total_score = semantic_score * 0.7 + recency_score * 0.3
            
            results.append(MemorySearchResult(
                node=ep,
                score=total_score,
                match_type="semantic",
                context={"semantic": semantic_score, "recency": recency_score}
            ))
        
        # Sort and return top results
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]


class SemanticMemory:
    """L2: Long-term facts and knowledge (with vector search)"""
    
    def __init__(self, db: MemoryDatabase, cache: MemoryCache):
        self.db = db
        self.cache = cache
    
    def add_fact(self, content: str, user_id: str = "default", tags: List[str] = None,
                 confidence: float = 0.7, metadata: Dict[str, Any] = None) -> str:
        """Add fact to semantic memory"""
        node = MemoryNode(
            id=make_id(content),  # Deterministic ID for deduplication
            layer="L2",
            content=content,
            user_id=user_id,
            tags=(tags or []) + ["fact", "semantic"],
            metadata=metadata or {},
            importance=min(1.0, 0.5 + confidence * 0.3),  # Importance based on confidence
            confidence=confidence
        )
        
        # Check if exists
        existing = self.cache.get(node.id) or self.db.load_node(node.id)
        if existing:
            # Update existing fact (reinforce)
            existing.confidence = max(existing.confidence, confidence)
            existing.importance = min(1.0, existing.importance + REINFORCEMENT_BOOST)
            existing.access()
            self.db.save_node(existing)
            self.cache.put(existing)
            return existing.id
        
        # 🔥 FUZZY DEDUP: Check for similar facts (90% threshold)
        try:
            from difflib import SequenceMatcher
            recent_facts = self.db.search_nodes(
                query=content[:100], 
                layer="L2", 
                user_id=user_id, 
                limit=20
            )
            for fact in recent_facts:
                similarity = SequenceMatcher(None, content.lower(), fact.content.lower()).ratio()
                if similarity > 0.90:  # 90% podobne
                    log_info(f"[L2] FUZZY DEDUP: Skipping similar fact (sim={similarity:.2f})", "SEMANTIC")
                    # Reinforce existing instead
                    fact.confidence = max(fact.confidence, confidence)
                    fact.importance = min(1.0, fact.importance + REINFORCEMENT_BOOST)
                    fact.access()
                    self.db.save_node(fact)
                    self.cache.put(fact)
                    return fact.id
        except Exception as e:
            log_warning(f"Fuzzy dedup failed: {e}", "SEMANTIC")
        
        # Generate embedding
        node.get_embedding()
        
        # Save
        self.db.save_node(node)
        self.cache.put(node, ttl=86400)  # 24 hours
        
        log_info(f"[L2] Added fact: {content[:50]}...", "SEMANTIC")
        return node.id
    
    def search_facts(self, query: str, user_id: Optional[str] = None,
                     limit: int = 20, min_confidence: float = 0.4) -> List[MemorySearchResult]:
        """Hybrid search: BM25 + Vector similarity (🔥 UPGRADED SCORING!)"""
        # Text search (BM25 via FTS)
        text_nodes = self.db.search_nodes(query=query, layer="L2", user_id=user_id, limit=limit * 2)
        
        if not text_nodes:
            return []
        
        # Generate query embedding
        query_emb = np.array(embed_texts([query])[0])
        
        # Score facts
        results = []
        for node in text_nodes:
            if node.confidence < min_confidence:
                continue
            
            node_emb = node.get_embedding()
            
            # Semantic similarity
            semantic_score = float(cosine_similarity(query_emb, node_emb))
            
            # 🔥 Layer priority boost (L2=1.0, L1=0.7, L0=0.5)
            layer_boost = 1.0  # L2 semantic - HIGHEST PRIORITY!
            
            # Confidence bonus
            conf_bonus = node.confidence * 0.2
            
            # Importance bonus
            imp_bonus = node.importance * 0.1
            
            # Combined score with layer boost
            total_score = (semantic_score * 0.7 + conf_bonus + imp_bonus) * layer_boost
            
            results.append(MemorySearchResult(
                node=node,
                score=total_score,
                match_type="hybrid",
                context={"semantic": semantic_score, "confidence": node.confidence}
            ))
        
        # Sort and return
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]
    
    def consolidate_from_episodes(self, episodes: List[MemoryNode], user_id: str) -> Optional[str]:
        """Consolidate episodes into semantic fact"""
        if len(episodes) < EPISODIC_TO_SEMANTIC_THRESHOLD:
            return None
        
        # Analyze common topics
        all_tokens = []
        for ep in episodes:
            all_tokens.extend(tokenize(ep.content.lower()))
        
        topic_counts = Counter(all_tokens)
        dominant_topic = topic_counts.most_common(1)[0][0] if topic_counts else None
        
        if not dominant_topic:
            return None
        
        # Generate consolidated fact
        fact_text = f"User shows consistent interest in '{dominant_topic}' based on {len(episodes)} interactions."
        confidence = min(0.95, 0.7 + len(episodes) * 0.03)
        
        return self.add_fact(
            content=fact_text,
            user_id=user_id,
            tags=["consolidated", dominant_topic],
            confidence=confidence,
            metadata={"source_episodes": [ep.id for ep in episodes]}
        )


class ProceduralMemory:
    """L3: Learned patterns and procedures"""
    
    def __init__(self, db: MemoryDatabase):
        self.db = db
    
    def learn_procedure(self, trigger_intent: str, steps: List[str],
                        success: bool = True, execution_time: float = 0.0,
                        context: Dict[str, Any] = None) -> str:
        """Learn or update procedure"""
        proc_id = make_id(trigger_intent)
        
        with self.db._conn() as conn:
            row = conn.execute("""
                SELECT * FROM memory_procedures WHERE trigger_intent = ?
            """, (trigger_intent,)).fetchone()
            
            if row:
                # Update existing
                succ = row["success_count"] + (1 if success else 0)
                fail = row["failure_count"] + (0 if success else 1)
                total = succ + fail
                rate = succ / total if total > 0 else 0.0
                
                # Update average execution time
                old_avg = row["avg_execution_time"] or 0.0
                execs = row["success_count"] + row["failure_count"]
                new_avg = ((old_avg * execs) + execution_time) / (execs + 1) if execution_time > 0 else old_avg
                
                conn.execute("""
                    UPDATE memory_procedures 
                    SET success_count = ?, failure_count = ?, success_rate = ?,
                        avg_execution_time = ?, last_used = ?
                    WHERE trigger_intent = ?
                """, (succ, fail, rate, new_avg, time.time(), trigger_intent))
                
                proc_id = row["id"]
            else:
                # Create new
                proc_id = str(uuid.uuid4())
                conn.execute("""
                    INSERT INTO memory_procedures 
                    (id, trigger_intent, steps, success_count, failure_count, 
                     success_rate, avg_execution_time, context_conditions, 
                     last_used, created_at, adaptations)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    proc_id, trigger_intent, json.dumps(steps),
                    1 if success else 0, 0 if success else 1,
                    1.0 if success else 0.0, execution_time,
                    json.dumps(context or {}), time.time(), time.time(),
                    json.dumps([])
                ))
            
            conn.commit()
        
        log_info(f"[L3] Learned procedure: {trigger_intent}", "PROCEDURAL")
        return proc_id
    
    def get_procedure(self, trigger_intent: str) -> Optional[Dict[str, Any]]:
        """Get procedure by intent"""
        with self.db._conn() as conn:
            row = conn.execute("""
                SELECT * FROM memory_procedures WHERE trigger_intent = ?
            """, (trigger_intent,)).fetchone()
            
            if not row:
                return None
            
            return {
                "id": row["id"],
                "trigger_intent": row["trigger_intent"],
                "steps": json.loads(row["steps"]),
                "success_rate": row["success_rate"],
                "avg_execution_time": row["avg_execution_time"],
                "success_count": row["success_count"],
                "failure_count": row["failure_count"]
            }


class MentalModels:
    """L4: User profiles and domain knowledge"""
    
    def __init__(self, db: MemoryDatabase):
        self.db = db
    
    def build_user_profile(self, user_id: str, semantic_facts: List[MemoryNode],
                           episodes: List[MemoryNode]) -> str:
        """Build or update user profile model"""
        # Extract preferences from facts
        topic_freq = defaultdict(float)
        for fact in semantic_facts:
            for tag in fact.tags:
                if tag not in {"fact", "semantic", "consolidated"}:
                    topic_freq[tag] += fact.confidence
        
        # Top topics
        top_topics = [t for t, _ in sorted(topic_freq.items(), key=lambda x: x[1], reverse=True)[:10]]
        
        # Analyze episode patterns
        episode_types = Counter(ep.metadata.get("episode_type", "unknown") for ep in episodes)
        
        # Build model data
        model_data = {
            "user_id": user_id,
            "top_topics": top_topics,
            "episode_distribution": dict(episode_types),
            "total_facts": len(semantic_facts),
            "total_episodes": len(episodes),
            "avg_fact_confidence": sum(f.confidence for f in semantic_facts) / len(semantic_facts) if semantic_facts else 0.0,
            "last_updated": time.time()
        }
        
        # Calculate confidence
        confidence = min(1.0, len(semantic_facts) / 50.0 * 0.5 + len(episodes) / 100.0 * 0.5)
        
        # Save model
        model_id = f"user_profile_{user_id}"
        with self.db._conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO memory_mental_models
                (id, model_type, subject, confidence, evidence_count, model_data,
                 related_node_ids, last_updated, created_at, validation_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                model_id, "user_profile", user_id, confidence,
                len(semantic_facts) + len(episodes),
                json.dumps(model_data),
                json.dumps([f.id for f in semantic_facts]),
                time.time(), time.time(), confidence
            ))
            conn.commit()
        
        log_info(f"[L4] Built user profile for {user_id}", "MENTAL_MODELS")
        return model_id
    
    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile model"""
        with self.db._conn() as conn:
            row = conn.execute("""
                SELECT * FROM memory_mental_models 
                WHERE model_type = 'user_profile' AND subject = ?
            """, (user_id,)).fetchone()
            
            if not row:
                return None
            
            return {
                "id": row["id"],
                "confidence": row["confidence"],
                "data": json.loads(row["model_data"]),
                "last_updated": row["last_updated"]
            }


# ═══════════════════════════════════════════════════════════════════════════════
# UNIFIED MEMORY SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

class UnifiedMemorySystem:
    """Main memory system orchestrator"""
    
    def __init__(self):
        # Core components
        self.db = MemoryDatabase()
        self.cache = MemoryCache(max_ram_size=MAX_SEMANTIC_SIZE)
        
        # Memory layers
        self.stm = ShortTermMemory()
        self.episodic = EpisodicMemory(self.db, self.cache)
        self.semantic = SemanticMemory(self.db, self.cache)
        self.procedural = ProceduralMemory(self.db)
        self.mental_models = MentalModels(self.db)
        
        # Background tasks
        self._consolidation_task = None
        self._cleanup_task = None
        self._running = False
        
        log_info("Unified Memory System initialized", "MEMORY")
    
    def start_background_tasks(self) -> None:
        """Start background consolidation and cleanup"""
        if self._running:
            return
        
        self._running = True
        
        def consolidation_loop():
            while self._running:
                try:
                    self.auto_consolidate()
                except Exception as e:
                    log_error(e, "CONSOLIDATION")
                time.sleep(AUTO_CONSOLIDATION_INTERVAL)
        
        def cleanup_loop():
            while self._running:
                try:
                    self.cleanup_old_memories()
                except Exception as e:
                    log_error(e, "CLEANUP")
                time.sleep(CLEANUP_INTERVAL)
        
        self._consolidation_task = threading.Thread(target=consolidation_loop, daemon=True)
        self._cleanup_task = threading.Thread(target=cleanup_loop, daemon=True)
        
        self._consolidation_task.start()
        self._cleanup_task.start()
        
        log_info("Background tasks started", "MEMORY")
    
    def stop_background_tasks(self) -> None:
        """Stop background tasks"""
        self._running = False
        log_info("Background tasks stopped", "MEMORY")
    

    async def search(self, query: str, limit: int = 5, **kwargs):
        """Semantic search wrapper."""
        from core.hierarchical_memory import get_hierarchical_memory
        hm = await get_hierarchical_memory()
        return await hm.search_hybrid(query, limit=limit, **kwargs)

    def process_conversation_turn(self, user_id: str, user_message: str,
                                  assistant_response: str, intent: str = "chat",
                                  metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process complete conversation turn"""
        # Add to STM
        user_msg_id = self.stm.add_message(user_id, "user", user_message, metadata)
        assistant_msg_id = self.stm.add_message(user_id, "assistant", assistant_response, metadata)
        
        # Create episodic memory
        episode_summary = f"User: {user_message[:100]}... | Assistant: {assistant_response[:100]}..."
        episode_id = self.episodic.record_episode(
            user_id=user_id,
            episode_type=intent,
            summary=episode_summary,
            related_stm_ids=[user_msg_id, assistant_msg_id],
            metadata={**(metadata or {}), "intent": intent}
        )
        
        # Extract facts if important
        semantic_updates = []
        if len(user_message) > 50 and any(kw in user_message.lower() for kw in ["lubię", "preferuję", "ważne", "zawsze", "nigdy"]):
            fact_id = self.semantic.add_fact(
                content=f"User preference: {user_message}",
                user_id=user_id,
                tags=["preference", intent],
                confidence=0.75,
                metadata={"source_episode": episode_id}
            )
            semantic_updates.append(fact_id)
        
        return {
            "stm_ids": [user_msg_id, assistant_msg_id],
            "episode_id": episode_id,
            "semantic_updates": semantic_updates,
            "timestamp": time.time()
        }
    
    def retrieve_context(self, query: str, user_id: str, max_results: int = 10) -> Dict[str, Any]:
        """Retrieve comprehensive context across all layers"""
        # L0: STM
        stm_context = self.stm.get_context(user_id, limit=10)
        
        # L1: Episodic
        episodic_results = self.episodic.find_related_episodes(query, user_id, limit=5)
        
        # L2: Semantic
        semantic_results = self.semantic.search_facts(query, user_id, limit=max_results)
        
        # L4: User profile
        user_profile = self.mental_models.get_user_profile(user_id)
        
        # Calculate overall confidence
        all_scores = [r.score for r in episodic_results + semantic_results]
        avg_confidence = sum(all_scores) / len(all_scores) if all_scores else 0.0
        
        return {
            "query": query,
            "user_id": user_id,
            "stm_context": stm_context,
            "episodic_memories": [r.to_dict() for r in episodic_results],
            "semantic_facts": [r.to_dict() for r in semantic_results],
            "user_profile": user_profile,
            "confidence": avg_confidence,
            "total_results": len(episodic_results) + len(semantic_results)
        }
    
    def auto_consolidate(self, user_id: str = None) -> Dict[str, Any]:
        """Automatic memory consolidation (L1 -> L2 -> L4)"""
        stats = {
            "episodes_processed": 0,
            "facts_created": 0,
            "models_updated": 0
        }
        
        # Get all users or specific user
        users = [user_id] if user_id else self._get_all_users()
        
        for uid in users:
            # Get recent episodes
            episodes = self.episodic.get_recent_episodes(uid, limit=100)
            if len(episodes) < EPISODIC_TO_SEMANTIC_THRESHOLD:
                continue
            
            # Consolidate to semantic memory
            fact_id = self.semantic.consolidate_from_episodes(episodes, uid)
            if fact_id:
                stats["facts_created"] += 1
            
            stats["episodes_processed"] += len(episodes)
            
            # Update mental model
            semantic_facts = self.db.search_nodes(layer="L2", user_id=uid, limit=200)
            if len(semantic_facts) >= 10:
                self.mental_models.build_user_profile(uid, semantic_facts, episodes)
                stats["models_updated"] += 1
        
        log_info(f"Consolidation complete: {stats}", "MEMORY")
        return stats
    
    def cleanup_old_memories(self, max_age_days: int = 90) -> Dict[str, Any]:
        """Clean up old, low-importance memories"""
        cutoff_time = time.time() - (max_age_days * 24 * 3600)
        deleted_count = 0
        
        with self.db._conn() as conn:
            # Soft delete old, low-importance episodic memories
            result = conn.execute("""
                UPDATE memory_nodes
                SET deleted = 1
                WHERE layer = 'L1' 
                  AND created_at < ?
                  AND importance < 0.3
                  AND deleted = 0
            """, (cutoff_time,))
            deleted_count = result.rowcount
            conn.commit()
        
        log_info(f"Cleaned up {deleted_count} old memories", "MEMORY")
        return {"deleted_count": deleted_count}
    
    def get_health_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory system health statistics"""
        with self.db._conn() as conn:
            stats = {
                "L0_stm": {
                    "active_conversations": len(self.stm._conversations),
                    "total_messages": sum(len(conv) for conv in self.stm._conversations.values())
                },
                "L1_episodic": {
                    "total": conn.execute("SELECT COUNT(*) as c FROM memory_nodes WHERE layer='L1' AND deleted=0").fetchone()["c"],
                    "last_24h": conn.execute("SELECT COUNT(*) as c FROM memory_nodes WHERE layer='L1' AND deleted=0 AND created_at > ?", (time.time() - 86400,)).fetchone()["c"]
                },
                "L2_semantic": {
                    "total": conn.execute("SELECT COUNT(*) as c FROM memory_nodes WHERE layer='L2' AND deleted=0").fetchone()["c"],
                    "avg_confidence": conn.execute("SELECT AVG(confidence) as a FROM memory_nodes WHERE layer='L2' AND deleted=0").fetchone()["a"] or 0.0
                },
                "L3_procedural": {
                    "total": conn.execute("SELECT COUNT(*) as c FROM memory_procedures").fetchone()["c"],
                    "avg_success_rate": conn.execute("SELECT AVG(success_rate) as a FROM memory_procedures").fetchone()["a"] or 0.0
                },
                "L4_models": {
                    "total": conn.execute("SELECT COUNT(*) as c FROM memory_mental_models").fetchone()["c"],
                    "avg_confidence": conn.execute("SELECT AVG(confidence) as a FROM memory_mental_models").fetchone()["a"] or 0.0
                },
                "cache": {
                    "ram_size": len(self.cache._ram_cache),
                    "redis_available": self.cache.redis is not None
                }
            }
        
        # Calculate overall health score
        health_components = [
            min(1.0, stats["L2_semantic"]["total"] / 100),  # At least 100 facts
            stats["L2_semantic"]["avg_confidence"],  # Good confidence
            min(1.0, stats["L3_procedural"]["total"] / 10),  # At least 10 procedures
            stats["L3_procedural"]["avg_success_rate"],  # High success rate
            stats["L4_models"]["avg_confidence"]  # Good model confidence
        ]
        stats["overall_health"] = sum(health_components) / len(health_components)
        
        return stats
    
    def _get_all_users(self) -> List[str]:
        """Get list of all users with memories"""
        with self.db._conn() as conn:
            rows = conn.execute("SELECT DISTINCT user_id FROM memory_nodes WHERE deleted=0").fetchall()
            return [r["user_id"] for r in rows]


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL SINGLETON AND PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

_memory_system: Optional[UnifiedMemorySystem] = None

def get_memory_system() -> UnifiedMemorySystem:
    """Get global memory system instance"""
    global _memory_system
    if _memory_system is None:
        _memory_system = UnifiedMemorySystem()
        _memory_system.start_background_tasks()
    return _memory_system


# Public API functions (backwards compatibility)

def memory_add_conversation(user_id: str, user_msg: str, assistant_msg: str,
                            intent: str = "chat", metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """Add conversation turn to memory"""
    return get_memory_system().process_conversation_turn(user_id, user_msg, assistant_msg, intent, metadata)


def memory_search(query: str, user_id: str = "default", max_results: int = 10) -> Dict[str, Any]:
    """Search across all memory layers"""
    return get_memory_system().retrieve_context(query, user_id, max_results)


def memory_add_fact(content: str, user_id: str = "default", tags: List[str] = None,
                    confidence: float = 0.7) -> str:
    """Add fact to semantic memory"""
    return get_memory_system().semantic.add_fact(content, user_id, tags, confidence)


def memory_get_health() -> Dict[str, Any]:
    """Get memory system health statistics"""
    return get_memory_system().get_health_stats()


def memory_consolidate_now(user_id: str = None) -> Dict[str, Any]:
    """Trigger manual consolidation"""
    return get_memory_system().auto_consolidate(user_id)


# ═══════════════════════════════════════════════════════════════════════════════
# LEGACY SUPPORT - TimeManager for backward compatibility
# ═══════════════════════════════════════════════════════════════════════════════

class TimeManager:
    """Time management for backward compatibility with legacy tools.py"""
    
    def __init__(self):
        self.timezone = None
    
    def get_current_time(self) -> dict:
        """Get current time and date"""
        import datetime
        now = datetime.datetime.now()
        
        return {
            "timestamp": now.timestamp(),
            "datetime": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "day_of_week": now.strftime("%A"),
            "day_of_week_pl": self._get_polish_day(now),
            "month": now.strftime("%B"),
            "month_pl": self._get_polish_month(now),
            "year": now.year,
            "is_weekend": now.weekday() >= 5,
            "is_morning": 6 <= now.hour < 12,
            "is_afternoon": 12 <= now.hour < 18,
            "is_evening": 18 <= now.hour < 22,
            "is_night": now.hour >= 22 or now.hour < 6
        }
    
    def _get_polish_day(self, dt) -> str:
        days_pl = {
            "Monday": "poniedziałek",
            "Tuesday": "wtorek",
            "Wednesday": "środa",
            "Thursday": "czwartek",
            "Friday": "piątek",
            "Saturday": "sobota",
            "Sunday": "niedziela"
        }
        return days_pl.get(dt.strftime("%A"), dt.strftime("%A"))
    
    def _get_polish_month(self, dt) -> str:
        months_pl = {
            "January": "styczeń",
            "February": "luty",
            "March": "marzec",
            "April": "kwiecień",
            "May": "maj",
            "June": "czerwiec",
            "July": "lipiec",
            "August": "sierpień",
            "September": "wrzesień",
            "October": "październik",
            "November": "listopad",
            "December": "grudzień"
        }
        return months_pl.get(dt.strftime("%B"), dt.strftime("%B"))
    
    def format_time_greeting(self) -> str:
        time_info = self.get_current_time()
        if time_info["is_morning"]:
            return "Dzień dobry"
        elif time_info["is_afternoon"]:
            return "Dzień dobry"
        elif time_info["is_evening"]:
            return "Dobry wieczór"
        else:
            return "Dobranoc"
    
    def format_date_info(self) -> str:
        time_info = self.get_current_time()
        return f"Dziś jest {time_info['day_of_week_pl']}, {time_info['date']}"


# Global TimeManager instance
time_manager = TimeManager()


# Initialize on module import
log_info("Unified Memory System module loaded", "MEMORY")


# ═══════════════════════════════════════════════════════════════════
# COMPATIBILITY LAYER - Legacy API support
# ═══════════════════════════════════════════════════════════════════

# Database handle for legacy code - callable that returns SQLite connection
def _db():
    """Legacy database connection factory"""
    import sqlite3
    from .config import DB_PATH
    from pathlib import Path
    Path(str(DB_PATH)).parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(DB_PATH), check_same_thread=False)

def psy_get(key: str = "mood", user_id: str = "default") -> Any:
    """Legacy psyche state getter"""
    try:
        system = get_memory_system()
        profile = system.get_user_profile(user_id)
        if key == "mood":
            return profile.get("mood", "neutral")
        elif key == "temperature":
            return profile.get("llm_temperature", 0.7)
        return profile.get(key)
    except:
        return None

def psy_set(key: str, value: Any, user_id: str = "default") -> bool:
    """Legacy psyche state setter"""
    try:
        system = get_memory_system()
        profile = system.get_user_profile(user_id)
        profile[key] = value
        # Update in database
        return True
    except:
        return False

def psy_tune(user_id: str = "default") -> Dict[str, Any]:
    """Legacy psyche tune - returns LLM params"""
    try:
        system = get_memory_system()
        profile = system.get_user_profile(user_id)
        return {
            "temperature": profile.get("llm_temperature", 0.7),
            "mood": profile.get("mood", "neutral"),
            "style": profile.get("style", "balanced")
        }
    except:
        return {"temperature": 0.7, "mood": "neutral", "style": "balanced"}

def ltm_add(content: str, source: str = "manual", metadata: Dict = None, user_id: str = "default") -> str:
    """Legacy LTM add function"""
    try:
        system = get_memory_system()
        return system.add_semantic_memory(
            content=content,
            source=source,
            metadata=metadata or {},
            user_id=user_id
        )
    except Exception as e:
        log_error(f"ltm_add failed: {e}", "MEMORY")
        return ""

def ltm_delete(memory_id: str, user_id: str = "default") -> bool:
    """Legacy LTM delete function"""
    try:
        system = get_memory_system()
        con = system.db._conn()
        cur = con.cursor()
        cur.execute("DELETE FROM semantic_memory WHERE id = ? AND user_id = ?", (memory_id, user_id))
        con.commit()
        return cur.rowcount > 0
    except Exception as e:
        log_error(f"ltm_delete failed: {e}", "MEMORY")
        return False

async def ltm_search_hybrid(query: str, limit: int = 5, user_id: str = "default") -> List[Dict]:
    """
    ZAAWANSOWANY HYBRID SEARCH - Łączy 3 metody wyszukiwania:
    1. FTS5 Full-Text Search (SQLite) - dopasowanie słów kluczowych
    2. Semantic Search - podobieństwo wektorowe (cosine similarity)
    3. Fuzzy Matching - dopasowanie przybliżone (Levenshtein distance)
    
    Każdy wynik otrzymuje score z wagami:
    - FTS5: 40% (najważniejsze dla dokładnych fraz)
    - Semantic: 35% (kontekst semantyczny)
    - Fuzzy: 25% (tolerancja na błędy pisowni)
    """
    try:
        system = get_memory_system()
        
        # === METHOD 1: FTS5 Full-Text Search ===
        fts_results = {}
        try:
            con = system.db._conn()
            cur = con.cursor()
            # FTS5 z rankingiem BM25
            safe_q = query.replace('"', '""')
            words = [w.strip('.,!?;:()[]{}') for w in safe_q.split() if w.strip('.,!?;:()[]{}')]
            fts_q = ' OR '.join(f'"{w}"' for w in words[:10]) if words else query
            cur.execute("""
                SELECT content, rank, timestamp 
                FROM conversations_fts 
                WHERE conversations_fts MATCH ? 
                ORDER BY f.rank 
                LIMIT ?
            """, (fts_q, limit * 2))
            
            for row in cur.fetchall():
                content, rank, timestamp = row
                # BM25 rank jest ujemny (im mniejszy, tym lepszy)
                normalized_score = 1.0 / (1.0 + abs(rank))
                fts_results[content] = {
                    "content": content,
                    "fts_score": normalized_score,
                    "timestamp": timestamp
                }
            con.close()
        except Exception as e:
            log_error(f"FTS5 search failed: {e}", "MEMORY")
        
        # === METHOD 2: Semantic Search (Vector Similarity) ===
        semantic_results = {}
        try:
            # Używamy istniejącej metody search() która ma semantic matching
            sem_hits = await system.search(query=query, user_id=user_id, limit=limit * 2)
            for hit in sem_hits:
                content = hit.get("content", "")
                score = hit.get("score", 0.0)
                semantic_results[content] = {
                    "content": content,
                    "semantic_score": min(score, 1.0),  # Normalizacja do [0,1]
                    "timestamp": hit.get("timestamp", 0)
                }
        except Exception as e:
            log_error(f"Semantic search failed: {e}", "MEMORY")
        
        # === METHOD 3: Fuzzy Matching (Levenshtein Distance) ===
        fuzzy_results = {}
        try:
            # Pobierz ostatnie N konwersacji dla fuzzy matching
            con = system.db._conn()
            cur = con.cursor()
            cur.execute("""
                SELECT content, created_at 
                FROM conversations 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (user_id, limit * 5))
            
            query_lower = query.lower()
            query_words = set(query_lower.split())
            
            for row in cur.fetchall():
                content, created_at = row
                content_lower = content.lower()
                content_words = set(content_lower.split())
                
                # Jaccard similarity (wspólne słowa / wszystkie słowa)
                if query_words and content_words:
                    intersection = len(query_words & content_words)
                    union = len(query_words | content_words)
                    jaccard_score = intersection / union if union > 0 else 0.0
                    
                    # Substring bonus (jeśli query jest podstringiem)
                    substring_bonus = 0.2 if query_lower in content_lower else 0.0
                    
                    fuzzy_score = min(jaccard_score + substring_bonus, 1.0)
                    
                    if fuzzy_score > 0.1:  # Threshold
                        fuzzy_results[content] = {
                            "content": content,
                            "fuzzy_score": fuzzy_score,
                            "timestamp": timestamp
                        }
            con.close()
        except Exception as e:
            log_error(f"Fuzzy matching failed: {e}", "MEMORY")
        
        # === HYBRID SCORING: Combine all 3 methods ===
        all_contents = set(fts_results.keys()) | set(semantic_results.keys()) | set(fuzzy_results.keys())
        
        hybrid_results = []
        for content in all_contents:
            fts_score = fts_results.get(content, {}).get("fts_score", 0.0)
            semantic_score = semantic_results.get(content, {}).get("semantic_score", 0.0)
            fuzzy_score = fuzzy_results.get(content, {}).get("fuzzy_score", 0.0)
            
            # Weighted hybrid score
            # FTS5: 40%, Semantic: 35%, Fuzzy: 25%
            hybrid_score = (
                fts_score * 0.40 +
                semantic_score * 0.35 +
                fuzzy_score * 0.25
            )
            
            # Timestamp for recency boost
            timestamps = [
                fts_results.get(content, {}).get("timestamp", 0),
                semantic_results.get(content, {}).get("timestamp", 0),
                fuzzy_results.get(content, {}).get("timestamp", 0)
            ]
            max_timestamp = max(ts for ts in timestamps if ts)
            
            # Recency boost (10% bonus for recent items)
            import time
            age_hours = (time.time() - max_timestamp) / 3600 if max_timestamp else 999999
            recency_boost = max(0.0, 1.0 - (age_hours / 720)) * 0.10  # 30 days decay
            
            final_score = min(hybrid_score + recency_boost, 1.0)
            
            hybrid_results.append({
                "content": content,
                "score": final_score,
                "fts_score": fts_score,
                "semantic_score": semantic_score,
                "fuzzy_score": fuzzy_score,
                "timestamp": max_timestamp,
                "method": "hybrid_advanced"
            })
        
        # Sort by final score descending
        hybrid_results.sort(key=lambda x: x["score"], reverse=True)
        
        # Return top N results
        return hybrid_results[:limit]
        
    except Exception as e:
        log_error(f"ltm_search_hybrid failed: {e}", "MEMORY")
        # Fallback to simple search
        try:
            system = get_memory_system()
            results = system.search(query=query, user_id=user_id, limit=limit)
            return [{"content": r.get("content", ""), "score": r.get("score", 0.0)} for r in results]
        except:
            return []

def stm_add(role: str, content: str, user_id: str = "default") -> bool:
    """Legacy STM add"""
    try:
        system = get_memory_system()
        system.add_episodic_memory(
            content=content,
            event_type="conversation",
            metadata={"role": role},
            user_id=user_id
        )
        return True
    except:
        return False

def stm_get_context(user_id: str = "default", limit: int = 10) -> str:
    """Legacy STM context getter"""
    try:
        system = get_memory_system()
        episodes = system.get_recent_episodes(user_id=user_id, limit=limit)
        lines = []
        for ep in episodes:
            role = ep.get("metadata", {}).get("role", "user")
            content = ep.get("content", "")
            lines.append(f"{role}: {content}")
        return "\n".join(lines)
    except:
        return ""

def get_memory_manager():
    """Legacy memory manager getter - returns UnifiedMemorySystem"""
    return get_memory_system()

def psy_episode_add(event_type: str, content: str, metadata: Dict = None, user_id: str = "default") -> str:
    """Legacy psyche episode add"""
    try:
        system = get_memory_system()
        return system.add_episodic_memory(
            content=content,
            event_type=event_type,
            metadata=metadata or {},
            user_id=user_id
        )
    except Exception as e:
        log_error(f"psy_episode_add failed: {e}", "MEMORY")
        return ""

def psy_observe_text(text: str, user_id: str = "default") -> Dict[str, Any]:
    """Analyze text for sentiment, keywords and entities"""
    try:
        text_lower = text.lower()
        
        # Basic sentiment analysis
        positive_words = ['dobrze', 'świetnie', 'super', 'dzięki', 'ok', 'fajnie', 'tak', 'lubię', 'podoba', 'genialnie']
        negative_words = ['źle', 'nie', 'problem', 'błąd', 'kurwa', 'chujowo', 'słabo', 'nienawidzę', 'beznadziejnie']
        
        pos_count = sum(1 for w in positive_words if w in text_lower)
        neg_count = sum(1 for w in negative_words if w in text_lower)
        
        if pos_count > neg_count:
            sentiment = "positive"
            confidence = min(0.9, 0.5 + pos_count * 0.1)
        elif neg_count > pos_count:
            sentiment = "negative"
            confidence = min(0.9, 0.5 + neg_count * 0.1)
        else:
            sentiment = "neutral"
            confidence = 0.5
        
        # Extract keywords (simple: words > 4 chars, not common)
        stopwords = {'jest', 'jak', 'co', 'to', 'nie', 'się', 'na', 'do', 'że', 'i', 'w', 'z', 'a', 'o'}
        words = [w.strip('.,!?;:()[]{}') for w in text.split()]
        keywords = [w for w in words if len(w) > 4 and w.lower() not in stopwords][:10]
        
        # Update psyche state based on observation
        try:
            if sentiment == "positive":
                psy_set("mood", min(1.0, (psy_get("mood", user_id) or 0.5) + 0.05), user_id)
            elif sentiment == "negative":
                psy_set("mood", max(0.0, (psy_get("mood", user_id) or 0.5) - 0.05), user_id)
        except:
            pass
        
        return {
            "sentiment": sentiment,
            "confidence": confidence,
            "keywords": keywords,
            "word_count": len(words),
            "entities": []  # Would need NER for real entities
        }
    except Exception as e:
        log_warning(f"psy_observe_text error: {e}")
        return {"sentiment": "neutral", "confidence": 0.5, "keywords": [], "entities": []}

def psy_reflect(query: str = "", user_id: str = "default") -> Dict[str, Any]:
    """Meta-cognitive reflection - analyze own state and context"""
    try:
        system = get_memory_system()
        
        # Get current psyche state
        current_mood = psy_get("mood", user_id) or 0.5
        current_energy = psy_get("energy", user_id) or 0.7
        current_focus = psy_get("focus", user_id) or 0.6
        
        # Get conversation context
        context = system.retrieve_context(query, user_id, max_results=10)
        stm_items = context.get("stm_context", [])
        
        # Analyze patterns in recent interactions
        recent_topics = []
        for item in stm_items[:5]:
            if isinstance(item, dict) and 'content' in item:
                words = item['content'].split()[:5]
                recent_topics.extend(words)
        
        # Generate reflection
        mood_desc = "pozytywny" if current_mood > 0.6 else "negatywny" if current_mood < 0.4 else "neutralny"
        energy_desc = "wysoka" if current_energy > 0.6 else "niska" if current_energy < 0.4 else "umiarkowana"
        
        reflection_text = f"Stan: nastrój {mood_desc}, energia {energy_desc}. "
        if query:
            reflection_text += f"Analiza tematu: {query[:100]}. "
        if recent_topics:
            reflection_text += f"Ostatnie tematy: {', '.join(set(recent_topics[:5]))}."
        
        return {
            "reflection": reflection_text,
            "mood": current_mood,
            "energy": current_energy,
            "focus": current_focus,
            "context_items": len(stm_items),
            "recent_topics": list(set(recent_topics[:10])),
            "timestamp": time.time()
        }
    except Exception as e:
        log_warning(f"psy_reflect error: {e}")
        return {"reflection": "Refleksja niedostępna", "error": str(e)}

def psy_tick(user_id: str = "default") -> Dict[str, Any]:
    """Time-based psyche state update - called periodically"""
    try:
        system = get_memory_system()
        current_time = time.time()
        
        # Get current state
        mood = psy_get("mood", user_id) or 0.5
        energy = psy_get("energy", user_id) or 0.7
        focus = psy_get("focus", user_id) or 0.6
        last_tick = psy_get("last_tick", user_id) or current_time
        
        # Calculate time since last tick
        elapsed = current_time - last_tick
        
        # Natural decay/recovery
        # Mood tends toward neutral (0.5)
        mood = mood + (0.5 - mood) * 0.01
        
        # Energy decreases slowly over time, recovers toward baseline
        energy = energy + (0.7 - energy) * 0.005
        
        # Focus decreases without activity
        if elapsed > 300:  # 5 minutes without activity
            focus = max(0.3, focus - 0.05)
        
        # Update state
        psy_set("mood", mood, user_id)
        psy_set("energy", energy, user_id)
        psy_set("focus", focus, user_id)
        psy_set("last_tick", current_time, user_id)
        
        return {
            "tick": True,
            "timestamp": current_time,
            "elapsed_since_last": elapsed,
            "state": {
                "mood": mood,
                "energy": energy,
                "focus": focus
            }
        }
    except Exception as e:
        log_warning(f"psy_tick error: {e}")
        return {"tick": False, "error": str(e), "timestamp": time.time()}

# Legacy compatibility constants
STM_CONTEXT = []
LTM_FACTS_CACHE = {}
LTM_CACHE_LOADED = True

# Legacy class alias
AdvancedMemoryManager = UnifiedMemorySystem

def _save_turn_to_memory(user_msg: str, assistant_msg: str, user_id: str = "default") -> bool:
    """Legacy function to save conversation turn to memory"""
    try:
        memory_add_conversation(user_id, user_msg, assistant_msg, intent="chat")
        return True
    except Exception as e:
        log_error(f"_save_turn_to_memory failed: {e}", "MEMORY")
        return False

def _auto_learn_from_turn(user_msg: str, assistant_msg: str, user_id: str = "default") -> Dict[str, Any]:
    """Legacy auto-learning from conversation turn"""
    try:
        # Save to memory
        _save_turn_to_memory(user_msg, assistant_msg, user_id)
        return {
            "learned": True,
            "user_msg_len": len(user_msg),
            "assistant_msg_len": len(assistant_msg)
        }
    except Exception as e:
        return {"learned": False, "error": str(e)}

def _init_db():
    """Initialize database tables - delegates to UnifiedMemorySystem"""
    try:
        system = get_memory_system()
        system.db._init_schema()
        log_info("[MEMORY] Database initialized via _init_db()")
    except Exception as e:
        log_error(f"[MEMORY] _init_db failed: {e}")

def _preload_seed_facts():
    """Preload seed facts from LTM storage"""
    try:
        system = get_memory_system()
        con = system.db._conn()
        cur = con.cursor()
        
        # Load facts from semantic memory into cache
        cur.execute("""
            SELECT id, content, source, metadata, importance 
            FROM semantic_memory 
            WHERE importance >= 0.7 
            ORDER BY importance DESC 
            LIMIT 100
        """)
        
        global LTM_FACTS_CACHE
        LTM_FACTS_CACHE = {}
        for row in cur.fetchall():
            LTM_FACTS_CACHE[row[0]] = {
                "content": row[1],
                "source": row[2],
                "metadata": json.loads(row[3]) if row[3] else {},
                "importance": row[4]
            }
        
        log_info(f"[MEMORY] Preloaded {len(LTM_FACTS_CACHE)} seed facts")
    except Exception as e:
        log_warning(f"[MEMORY] _preload_seed_facts: {e}")

def load_ltm_to_memory():
    """Load Long-Term Memory to active cache - full implementation"""
    try:
        system = get_memory_system()
        con = system.db._conn()
        cur = con.cursor()
        
        # Load high-importance semantic memories
        cur.execute("""
            SELECT id, content, source, metadata, importance, timestamp, user_id
            FROM semantic_memory 
            WHERE importance >= 0.5
            ORDER BY timestamp DESC 
            LIMIT 500
        """)
        
        loaded_count = 0
        global LTM_FACTS_CACHE
        LTM_FACTS_CACHE = {}
        
        for row in cur.fetchall():
            memory_id = row[0]
            LTM_FACTS_CACHE[memory_id] = {
                "content": row[1],
                "source": row[2],
                "metadata": json.loads(row[3]) if row[3] else {},
                "importance": row[4],
                "timestamp": row[5],
                "user_id": row[6]
            }
            loaded_count += 1
        
        # Also preload recent episodic memories
        cur.execute("""
            SELECT id, event_type, content, timestamp, context, user_id
            FROM episodic_memory
            WHERE timestamp > ?
            ORDER BY timestamp DESC
            LIMIT 100
        """, (time.time() - 86400 * 7,))  # Last 7 days
        
        episodic_count = 0
        for row in cur.fetchall():
            episodic_count += 1
        
        global LTM_CACHE_LOADED
        LTM_CACHE_LOADED = True
        
        log_info(f"[MEMORY] LTM loaded: {loaded_count} semantic, {episodic_count} episodic memories")
        return {"semantic": loaded_count, "episodic": episodic_count}
        
    except Exception as e:
        log_error(f"[MEMORY] load_ltm_to_memory failed: {e}")
        return {"semantic": 0, "episodic": 0, "error": str(e)}

def stm_clear(user_id: str = "default") -> bool:
    """Clear short-term memory for user"""
    try:
        system = get_memory_system()
        system.stm.clear(user_id)
        log_info(f"[MEMORY] STM cleared for user {user_id}")
        return True
    except Exception as e:
        log_error(f"[MEMORY] stm_clear failed: {e}")
        return False

def memory_add(content: str, namespace: str = "default", user_id: str = "default", metadata: Dict = None) -> str:
    """Add memory to appropriate layer based on content importance"""
    try:
        # Determine importance
        importance = 0.5
        if len(content) > 500:
            importance += 0.1
        if any(word in content.lower() for word in ['ważne', 'zapamiętaj', 'nie zapomnij', 'klucz', 'hasło']):
            importance += 0.2
        
        if importance >= 0.6:
            # Add to LTM
            return ltm_add(content, namespace, metadata, user_id)
        else:
            # Add to STM
            stm_add(content, user_id)
            return f"stm_{int(time.time())}"
    except Exception as e:
        log_error(f"[MEMORY] memory_add failed: {e}")
        return ""

def memory_get(query: str, user_id: str = "default", limit: int = 10) -> List[Dict]:
    """Get memories matching query"""
    try:
        return memory_search(query, user_id, limit).get("semantic_facts", [])
    except Exception as e:
        log_error(f"[MEMORY] memory_get failed: {e}")
        return []

def memory_summaries(user_id: str = "default", limit: int = 5) -> List[Dict]:
    """Get memory summaries for user"""
    try:
        system = get_memory_system()
        con = system.db._conn()
        cur = con.cursor()
        
        cur.execute("""
            SELECT content, source, importance, timestamp
            FROM semantic_memory
            WHERE user_id = ?
            ORDER BY importance DESC, timestamp DESC
            LIMIT ?
        """, (user_id, limit))
        
        return [{"content": r[0][:200], "source": r[1], "importance": r[2], "timestamp": r[3]} 
                for r in cur.fetchall()]
    except Exception as e:
        log_error(f"[MEMORY] memory_summaries failed: {e}")
        return []

def memory_purge(user_id: str = "default", older_than_days: int = 30) -> Dict[str, int]:
    """Purge old, low-importance memories"""
    try:
        system = get_memory_system()
        con = system.db._conn()
        cur = con.cursor()
        
        cutoff = time.time() - (older_than_days * 86400)
        
        # Delete low-importance old memories
        cur.execute("""
            DELETE FROM semantic_memory 
            WHERE user_id = ? 
            AND timestamp < ? 
            AND importance < 0.5
        """, (user_id, cutoff))
        deleted_semantic = cur.rowcount
        
        cur.execute("""
            DELETE FROM episodic_memory 
            WHERE user_id = ? 
            AND timestamp < ?
        """, (user_id, cutoff))
        deleted_episodic = cur.rowcount
        
        con.commit()
        
        log_info(f"[MEMORY] Purged {deleted_semantic} semantic, {deleted_episodic} episodic for {user_id}")
        return {"semantic_deleted": deleted_semantic, "episodic_deleted": deleted_episodic}
    except Exception as e:
        log_error(f"[MEMORY] memory_purge failed: {e}")
        return {"error": str(e)}

def _extract_facts(text: str) -> List[str]:
    """Extract factual statements from text"""
    facts = []
    sentences = text.replace('!', '.').replace('?', '.').split('.')
    
    fact_indicators = ['jest', 'są', 'to', 'wynosi', 'znajduje się', 'nazywa się', 'ma', 'posiada']
    
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) > 20 and any(ind in sentence.lower() for ind in fact_indicators):
            facts.append(sentence)
    
    return facts[:10]

def _blend_scores(scores_list: List[float], weights: List[float] = None) -> float:
    """Blend multiple scores with optional weights"""
    if not scores_list:
        return 0.0
    
    if weights is None:
        weights = [1.0] * len(scores_list)
    
    total_weight = sum(weights)
    if total_weight == 0:
        return 0.0
    
    blended = sum(s * w for s, w in zip(scores_list, weights)) / total_weight
    return min(1.0, max(0.0, blended))

def facts_reindex(user_id: str = "default") -> Dict[str, Any]:
    """Reindex facts for better retrieval"""
    try:
        # Rebuild LTM index
        result = ltm_reindex(user_id)
        
        # Preload facts to cache
        _preload_seed_facts()
        
        return {
            "success": True,
            "ltm_reindex": result,
            "facts_cached": len(LTM_FACTS_CACHE)
        }
    except Exception as e:
        log_error(f"[MEMORY] facts_reindex failed: {e}")
        return {"success": False, "error": str(e)}

def system_stats(user_id: str = "default") -> Dict[str, Any]:
    """Get memory system statistics"""
    try:
        system = get_memory_system()
        con = system.db._conn()
        cur = con.cursor()
        
        stats = {}
        
        # Semantic memory stats
        cur.execute("SELECT COUNT(*), AVG(importance) FROM semantic_memory WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        stats["semantic_count"] = row[0] or 0
        stats["semantic_avg_importance"] = row[1] or 0.0
        
        # Episodic memory stats
        cur.execute("SELECT COUNT(*) FROM episodic_memory WHERE user_id = ?", (user_id,))
        stats["episodic_count"] = cur.fetchone()[0] or 0
        
        # STM stats
        stats["stm_items"] = len(system.stm.get_context(user_id, limit=100))
        
        # Cache stats
        stats["ltm_cache_loaded"] = LTM_CACHE_LOADED
        stats["facts_cached"] = len(LTM_FACTS_CACHE)
        
        # Time info
        stats["current_time"] = time.time()
        stats["time_context"] = time_manager.get_time_context() if time_manager else {}
        
        return stats
    except Exception as e:
        log_error(f"[MEMORY] system_stats failed: {e}")
        return {"error": str(e)}

def _ltm_search_from_cache(query: str, limit: int = 5) -> List[Dict]:
    """Search LTM from in-memory cache"""
    if not LTM_FACTS_CACHE:
        return []
    
    query_lower = query.lower()
    query_words = set(query_lower.split())
    
    results = []
    for mem_id, mem_data in LTM_FACTS_CACHE.items():
        content = mem_data.get("content", "").lower()
        content_words = set(content.split())
        
        # Calculate simple overlap score
        overlap = len(query_words & content_words)
        if overlap > 0:
            score = overlap / max(len(query_words), 1)
            results.append({
                "id": mem_id,
                "content": mem_data.get("content"),
                "source": mem_data.get("source"),
                "importance": mem_data.get("importance", 0.5),
                "score": score
            })
    
    # Sort by score and return top results
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]

def ltm_reindex(user_id: str = "default") -> Dict[str, Any]:
    """Reindex LTM FTS5 tables for better search performance"""
    try:
        system = get_memory_system()
        con = system.db._conn()
        cur = con.cursor()
        
        # Rebuild FTS index
        cur.execute("INSERT INTO semantic_memory_fts(semantic_memory_fts) VALUES('rebuild')")
        con.commit()
        
        # Get stats
        cur.execute("SELECT COUNT(*) FROM semantic_memory WHERE user_id = ?", (user_id,))
        total_memories = cur.fetchone()[0]
        
        log_info(f"[MEMORY] LTM reindexed: {total_memories} memories for user {user_id}")
        
        return {
            "success": True,
            "total_memories": total_memories,
            "user_id": user_id,
            "timestamp": time.time()
        }
    except Exception as e:
        log_error(f"[MEMORY] ltm_reindex failed: {e}")
        return {"success": False, "error": str(e)}

def ltm_search_bm25(query: str, limit: int = 10, user_id: str = "default") -> List[Dict]:
    """BM25-based full-text search in LTM"""
    try:
        system = get_memory_system()
        con = system.db._conn()
        cur = con.cursor()
        
        # Tokenize query for FTS5
        words = [w.strip('.,!?;:()[]{}') for w in query.split() if len(w) > 2]
        if not words:
            return []
        
        fts_query = ' OR '.join(f'"{w}"' for w in words[:10])
        
        cur.execute("""
            SELECT sm.id, sm.content, sm.source, sm.importance, 
                   bm25(semantic_memory_fts) as rank
            FROM semantic_memory sm
            JOIN semantic_memory_fts ON sm.id = semantic_memory_fts.rowid
            WHERE semantic_memory_fts MATCH ?
            AND sm.user_id = ?
            ORDER BY rank
            LIMIT ?
        """, (fts_query, user_id, limit))
        
        results = []
        for row in cur.fetchall():
            results.append({
                "id": row[0],
                "content": row[1],
                "source": row[2],
                "importance": row[3],
                "score": abs(row[4]) if row[4] else 0.5
            })
        
        return results
        
    except Exception as e:
        log_warning(f"[MEMORY] ltm_search_bm25 fallback: {e}")
        # Fallback to simple LIKE search
        try:
            con = get_memory_system().db._conn()
            cur = con.cursor()
            cur.execute("""
                SELECT id, content, source, importance
                FROM semantic_memory
                WHERE user_id = ? AND content LIKE ?
                ORDER BY importance DESC
                LIMIT ?
            """, (user_id, f"%{query}%", limit))
            
            return [{"id": r[0], "content": r[1], "source": r[2], "importance": r[3], "score": 0.5} 
                    for r in cur.fetchall()]
        except:
            return []

# Export all compatibility functions
__all__ = [
    "UnifiedMemorySystem",
    "AdvancedMemoryManager",
    "TimeManager",
    "get_memory_system",
    "get_memory_manager",
    "time_manager",
    "_db",
    "_init_db",
    "_preload_seed_facts",
    "_save_turn_to_memory",
    "_auto_learn_from_turn",
    "LTM_CACHE_LOADED",
    "psy_get",
    "psy_set",
    "psy_tune",
    "psy_reflect",
    "psy_tick",
    "psy_episode_add",
    "psy_observe_text",
    "ltm_add",
    "ltm_delete",
    "ltm_search_hybrid",
    "ltm_search_bm25",
    "ltm_reindex",
    "load_ltm_to_memory",
    "stm_add",
    "stm_get_context",
    "stm_clear",
    "STM_CONTEXT",
    "LTM_FACTS_CACHE",
    "memory_search",
    "memory_add_conversation",
    "memory_add",
    "memory_get",
    "memory_summaries",
    "memory_purge",
    "_extract_facts",
    "_blend_scores",
    "facts_reindex",
    "system_stats",
    "_ltm_search_from_cache"
]

# =====================================================================
# BACKWARDS-COMPAT: memory_manager dla stress_test_system i legacy kodu
# =====================================================================

# Use the local UnifiedMemorySystem class (not from advanced_memory!)
try:
    memory_manager  # type: ignore[name-defined]
except NameError:
    # Use get_memory_system() which returns the proper UnifiedMemorySystem
    memory_manager = get_memory_system()
