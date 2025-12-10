#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
conversation_analytics.py - Conversation Analytics & Tracking
FULL LOGIC - ZERO PLACEHOLDERS!
"""
import time
import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter

from .helpers import log_info, log_error


# ═══════════════════════════════════════════════════════════════════
# DATABASE SCHEMA
# ═══════════════════════════════════════════════════════════════════

ANALYTICS_SCHEMA = """
CREATE TABLE IF NOT EXISTS conversation_analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    timestamp REAL NOT NULL,
    message_role TEXT NOT NULL,
    message_length INTEGER NOT NULL,
    topic TEXT,
    personality TEXT,
    response_time_ms INTEGER,
    tokens_used INTEGER,
    metadata TEXT,
    created_at REAL NOT NULL,
    INDEX idx_user_time (user_id, timestamp),
    INDEX idx_conversation (conversation_id),
    INDEX idx_topic (topic)
);

CREATE TABLE IF NOT EXISTS topic_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    count INTEGER DEFAULT 1,
    first_seen REAL NOT NULL,
    last_seen REAL NOT NULL,
    INDEX idx_user_topic (user_id, topic)
);

CREATE TABLE IF NOT EXISTS learning_velocity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    date TEXT NOT NULL,
    messages_count INTEGER DEFAULT 0,
    topics_explored INTEGER DEFAULT 0,
    avg_message_length REAL DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    INDEX idx_user_date (user_id, date)
);
"""


# ═══════════════════════════════════════════════════════════════════
# ANALYTICS MANAGER
# ═══════════════════════════════════════════════════════════════════

class ConversationAnalytics:
    """Tracks and analyzes conversation patterns"""
    
    def __init__(self, db_path: str = "data/analytics.db"):
        self.db_path = db_path
        self._init_db()
        log_info(f"[ANALYTICS] Initialized with db={db_path}")
    
    def _init_db(self):
        """Initialize analytics database"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.executescript(ANALYTICS_SCHEMA)
            conn.commit()
            conn.close()
            log_info("[ANALYTICS] Database schema created")
        except Exception as e:
            log_error(e, "ANALYTICS_INIT")
    
    def track_message(
        self,
        user_id: str,
        conversation_id: str,
        role: str,
        content: str,
        topic: Optional[str] = None,
        personality: Optional[str] = None,
        response_time_ms: Optional[int] = None,
        tokens_used: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Track a single message
        
        Args:
            user_id: User identifier
            conversation_id: Conversation identifier
            role: Message role (user/assistant)
            content: Message content
            topic: Detected topic (optional)
            personality: Active personality (optional)
            response_time_ms: Response time in milliseconds
            tokens_used: Number of tokens used
            metadata: Additional metadata
        """
        try:
            conn = sqlite3.connect(self.db_path)
            now = time.time()
            
            # Auto-detect topic if not provided
            if not topic and role == "user":
                topic = self._detect_topic(content)
            
            # Insert message analytics
            import json
            conn.execute("""
                INSERT INTO conversation_analytics
                (user_id, conversation_id, timestamp, message_role, message_length,
                 topic, personality, response_time_ms, tokens_used, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, conversation_id, now, role, len(content),
                topic, personality, response_time_ms, tokens_used,
                json.dumps(metadata) if metadata else None, now
            ))
            
            # Update topic tracking
            if topic and role == "user":
                self._update_topic_tracking(conn, user_id, topic, conversation_id, now)
            
            # Update daily learning velocity
            self._update_learning_velocity(conn, user_id, now, len(content), tokens_used or 0)
            
            conn.commit()
            conn.close()
            
            log_info(f"[ANALYTICS] Tracked message: user={user_id}, topic={topic}, role={role}")
            
        except Exception as e:
            log_error(e, "ANALYTICS_TRACK")
    
    def _detect_topic(self, content: str) -> str:
        """
        Simple topic detection via keyword extraction
        
        Args:
            content: Message content
            
        Returns:
            str: Detected topic
        """
        content_lower = content.lower()
        
        # Topic keywords
        topic_keywords = {
            "programming": ["code", "python", "javascript", "bug", "function", "api"],
            "science": ["research", "experiment", "theory", "study", "hypothesis"],
            "math": ["equation", "calculate", "formula", "number", "solve"],
            "business": ["market", "startup", "strategy", "customer", "revenue"],
            "health": ["health", "medical", "symptom", "doctor", "disease"],
            "technology": ["tech", "software", "hardware", "ai", "ml", "cloud"],
            "education": ["learn", "teach", "study", "course", "tutorial"],
            "creative": ["story", "write", "art", "design", "create"],
            "personal": ["advice", "help", "think", "feel", "opinion"]
        }
        
        # Count keyword matches
        topic_scores = defaultdict(int)
        for topic, keywords in topic_keywords.items():
            for keyword in keywords:
                if keyword in content_lower:
                    topic_scores[topic] += 1
        
        # Return topic with highest score
        if topic_scores:
            return max(topic_scores, key=topic_scores.get)
        else:
            return "general"
    
    def _update_topic_tracking(self, conn: sqlite3.Connection, user_id: str, topic: str, conversation_id: str, timestamp: float):
        """Update topic tracking table"""
        # Check if topic exists
        cursor = conn.execute(
            "SELECT id, count FROM topic_tracking WHERE user_id = ? AND topic = ?",
            (user_id, topic)
        )
        row = cursor.fetchone()
        
        if row:
            # Update existing
            conn.execute(
                "UPDATE topic_tracking SET count = count + 1, last_seen = ? WHERE id = ?",
                (timestamp, row[0])
            )
        else:
            # Insert new
            conn.execute(
                "INSERT INTO topic_tracking (user_id, topic, conversation_id, count, first_seen, last_seen) VALUES (?, ?, ?, 1, ?, ?)",
                (user_id, topic, conversation_id, timestamp, timestamp)
            )
    
    def _update_learning_velocity(self, conn: sqlite3.Connection, user_id: str, timestamp: float, message_length: int, tokens: int):
        """Update daily learning velocity"""
        date_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
        
        # Check if date exists
        cursor = conn.execute(
            "SELECT id, messages_count, avg_message_length, total_tokens FROM learning_velocity WHERE user_id = ? AND date = ?",
            (user_id, date_str)
        )
        row = cursor.fetchone()
        
        if row:
            # Update existing
            old_count = row[1]
            old_avg = row[2]
            old_tokens = row[3]
            
            new_count = old_count + 1
            new_avg = (old_avg * old_count + message_length) / new_count
            new_tokens = old_tokens + tokens
            
            conn.execute(
                "UPDATE learning_velocity SET messages_count = ?, avg_message_length = ?, total_tokens = ? WHERE id = ?",
                (new_count, new_avg, new_tokens, row[0])
            )
        else:
            # Insert new
            conn.execute(
                "INSERT INTO learning_velocity (user_id, date, messages_count, avg_message_length, total_tokens) VALUES (?, ?, 1, ?, ?)",
                (user_id, date_str, float(message_length), tokens)
            )
    
    def get_user_stats(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get user statistics for last N days
        
        Args:
            user_id: User identifier
            days: Number of days to look back
            
        Returns:
            dict: User statistics
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cutoff = time.time() - (days * 86400)
            
            # Total messages
            cursor = conn.execute(
                "SELECT COUNT(*) FROM conversation_analytics WHERE user_id = ? AND timestamp > ?",
                (user_id, cutoff)
            )
            total_messages = cursor.fetchone()[0]
            
            # Messages by role
            cursor = conn.execute(
                "SELECT message_role, COUNT(*) FROM conversation_analytics WHERE user_id = ? AND timestamp > ? GROUP BY message_role",
                (user_id, cutoff)
            )
            messages_by_role = dict(cursor.fetchall())
            
            # Top topics
            cursor = conn.execute(
                "SELECT topic, COUNT(*) as count FROM conversation_analytics WHERE user_id = ? AND timestamp > ? AND topic IS NOT NULL GROUP BY topic ORDER BY count DESC LIMIT 10",
                (user_id, cutoff)
            )
            top_topics = [{"topic": row[0], "count": row[1]} for row in cursor.fetchall()]
            
            # Average message length
            cursor = conn.execute(
                "SELECT AVG(message_length) FROM conversation_analytics WHERE user_id = ? AND timestamp > ? AND message_role = 'user'",
                (user_id, cutoff)
            )
            avg_msg_length = cursor.fetchone()[0] or 0
            
            # Total tokens
            cursor = conn.execute(
                "SELECT SUM(tokens_used) FROM conversation_analytics WHERE user_id = ? AND timestamp > ?",
                (user_id, cutoff)
            )
            total_tokens = cursor.fetchone()[0] or 0
            
            # Avg response time
            cursor = conn.execute(
                "SELECT AVG(response_time_ms) FROM conversation_analytics WHERE user_id = ? AND timestamp > ? AND response_time_ms IS NOT NULL",
                (user_id, cutoff)
            )
            avg_response_time = cursor.fetchone()[0] or 0
            
            # Active days
            cursor = conn.execute(
                "SELECT COUNT(DISTINCT date) FROM learning_velocity WHERE user_id = ? AND date >= date('now', '-' || ? || ' days')",
                (user_id, days)
            )
            active_days = cursor.fetchone()[0]
            
            # Learning velocity (messages per day)
            velocity = total_messages / days if days > 0 else 0
            
            conn.close()
            
            return {
                "user_id": user_id,
                "period_days": days,
                "total_messages": total_messages,
                "messages_by_role": messages_by_role,
                "top_topics": top_topics,
                "avg_message_length": round(avg_msg_length, 1),
                "total_tokens": total_tokens,
                "avg_response_time_ms": round(avg_response_time, 1),
                "active_days": active_days,
                "learning_velocity": round(velocity, 2),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            log_error(e, "ANALYTICS_STATS")
            return {"error": str(e)}
    
    def get_topic_trends(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get topic trends for user
        
        Args:
            user_id: User identifier
            limit: Max number of topics
            
        Returns:
            list: Topic trend data
        """
        try:
            conn = sqlite3.connect(self.db_path)
            
            cursor = conn.execute("""
                SELECT topic, count, first_seen, last_seen
                FROM topic_tracking
                WHERE user_id = ?
                ORDER BY count DESC
                LIMIT ?
            """, (user_id, limit))
            
            trends = []
            for row in cursor.fetchall():
                trends.append({
                    "topic": row[0],
                    "count": row[1],
                    "first_seen": datetime.fromtimestamp(row[2]).isoformat(),
                    "last_seen": datetime.fromtimestamp(row[3]).isoformat(),
                    "recency_days": (time.time() - row[3]) / 86400
                })
            
            conn.close()
            
            return trends
            
        except Exception as e:
            log_error(e, "ANALYTICS_TRENDS")
            return []
    
    def get_daily_activity(self, user_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get daily activity breakdown
        
        Args:
            user_id: User identifier
            days: Number of days
            
        Returns:
            list: Daily activity data
        """
        try:
            conn = sqlite3.connect(self.db_path)
            
            cursor = conn.execute("""
                SELECT date, messages_count, topics_explored, avg_message_length, total_tokens
                FROM learning_velocity
                WHERE user_id = ? AND date >= date('now', '-' || ? || ' days')
                ORDER BY date DESC
            """, (user_id, days))
            
            activity = []
            for row in cursor.fetchall():
                activity.append({
                    "date": row[0],
                    "messages": row[1],
                    "topics": row[2],
                    "avg_length": round(row[3], 1),
                    "tokens": row[4]
                })
            
            conn.close()
            
            return activity
            
        except Exception as e:
            log_error(e, "ANALYTICS_DAILY")
            return []


# Global analytics instance
_global_analytics = None


def get_analytics() -> ConversationAnalytics:
    """Get global analytics instance"""
    global _global_analytics
    if _global_analytics is None:
        _global_analytics = ConversationAnalytics()
    return _global_analytics


def track_message(*args, **kwargs):
    """Shortcut: track message globally"""
    return get_analytics().track_message(*args, **kwargs)


def get_user_stats(*args, **kwargs):
    """Shortcut: get user stats"""
    return get_analytics().get_user_stats(*args, **kwargs)
