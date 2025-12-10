"""
MORDZIX AI - Session Management (PHASE 6 - Full Security)

SQLite-based session storage with:
- User ownership validation
- Connection pooling
- Graceful shutdown support
- Structured logging
"""

import sqlite3
import uuid
import json
import threading
import atexit
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from queue import Queue

from .helpers import log_info, log_error, log_warning

# Database path
DB_PATH = Path(__file__).parent.parent / "data" / "sessions.db"

# AUDIT FIX: Content length limit
MAX_CONTENT_LENGTH = 100000  # 100k chars max per message

# =====================================================================
# CONNECTION POOL (prevents opening new connection per request)
# =====================================================================

class ConnectionPool:
    """Simple SQLite connection pool"""
    
    def __init__(self, db_path: Path, pool_size: int = 5):
        self.db_path = db_path
        self.pool_size = pool_size
        self._pool: Queue = Queue(maxsize=pool_size)
        self._lock = threading.Lock()
        self._initialized = False
        
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection with proper settings"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Enable foreign keys and WAL mode for better concurrency
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 5000")  # 5 second timeout
        return conn
    
    def initialize(self):
        """Initialize the connection pool"""
        with self._lock:
            if self._initialized:
                return
            for _ in range(self.pool_size):
                self._pool.put(self._create_connection())
            self._initialized = True
            log_info(f"[SESSIONS] Connection pool initialized with {self.pool_size} connections")
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool"""
        if not self._initialized:
            self.initialize()
        
        conn = self._pool.get()
        try:
            yield conn
        finally:
            self._pool.put(conn)
    
    def close_all(self):
        """Close all connections in the pool (for graceful shutdown)"""
        with self._lock:
            while not self._pool.empty():
                try:
                    conn = self._pool.get_nowait()
                    conn.close()
                except:
                    pass
            self._initialized = False
            log_info("[SESSIONS] Connection pool closed")


# Global connection pool
_pool = ConnectionPool(DB_PATH)


def get_db():
    """Get database connection from pool"""
    return _pool.get_connection()


def shutdown_sessions():
    """Graceful shutdown - close all connections"""
    _pool.close_all()


# Register shutdown handler
atexit.register(shutdown_sessions)


def init_sessions_db():
    """Initialize sessions database tables"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Sessions table with user_id for ownership
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL DEFAULT 'default',
                title TEXT NOT NULL DEFAULT 'Nowa rozmowa',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                title_custom INTEGER DEFAULT 0
            )
        """)
        
        # Migration: Add user_id column if it doesn't exist
        try:
            cursor.execute("ALTER TABLE sessions ADD COLUMN user_id TEXT DEFAULT 'default'")
            conn.commit()
            log_info("[SESSIONS] Added user_id column")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Migration: Add title_custom column if it doesn't exist
        try:
            cursor.execute("ALTER TABLE sessions ADD COLUMN title_custom INTEGER DEFAULT 0")
            conn.commit()
            log_info("[SESSIONS] Added title_custom column")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Messages table (linked to sessions)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                attachments TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        """)
        
        # Migration: Add attachments column if it doesn't exist
        try:
            cursor.execute("ALTER TABLE messages ADD COLUMN attachments TEXT DEFAULT '[]'")
            conn.commit()
            log_info("[SESSIONS] Added attachments column")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Indexes for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_session 
            ON messages(session_id, created_at)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_user 
            ON sessions(user_id, updated_at)
        """)
        
        conn.commit()
        log_info("[SESSIONS] Database initialized")


# =====================================================================
# SESSION CRUD (with user ownership)
# =====================================================================

def create_session(title: str = "Nowa rozmowa", user_id: str = "default") -> Dict[str, Any]:
    """
    Create a new chat session
    
    Args:
        title: Session title
        user_id: Owner user ID
        
    Returns:
        Dict with session data: {id, title, created_at, updated_at, message_count, user_id}
    """
    session_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (id, user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, user_id, title, now, now)
        )
        conn.commit()
    
    log_info(f"[SESSIONS] Created session {session_id} for user {user_id}")
    
    return {
        "id": session_id,
        "user_id": user_id,
        "title": title,
        "created_at": now,
        "updated_at": now,
        "message_count": 0
    }


def list_sessions(user_id: str = "default", limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """
    List sessions for a specific user, ordered by most recent first
    
    Args:
        user_id: Owner user ID (only returns their sessions)
        limit: Max sessions to return
        offset: Pagination offset
        
    Returns:
        List of session dicts with message counts
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                s.id, 
                s.user_id,
                s.title, 
                s.created_at, 
                s.updated_at,
                COUNT(m.id) as message_count
            FROM sessions s
            LEFT JOIN messages m ON s.id = m.session_id
            WHERE s.user_id = ?
            GROUP BY s.id
            ORDER BY s.updated_at DESC
            LIMIT ? OFFSET ?
        """, (user_id, limit, offset))
        
        rows = cursor.fetchall()
        
    return [
        {
            "id": row["id"],
            "user_id": row["user_id"],
            "title": row["title"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "message_count": row["message_count"]
        }
        for row in rows
    ]


def get_session(session_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get a single session by ID
    
    Args:
        session_id: Session UUID
        user_id: If provided, validates ownership
        
    Returns:
        Session dict with messages, or None if not found/unauthorized
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get session (with optional user check)
        if user_id:
            cursor.execute(
                "SELECT id, user_id, title, created_at, updated_at FROM sessions WHERE id = ? AND user_id = ?",
                (session_id, user_id)
            )
        else:
            cursor.execute(
                "SELECT id, user_id, title, created_at, updated_at FROM sessions WHERE id = ?",
                (session_id,)
            )
        row = cursor.fetchone()
        
        if not row:
            return None
        
        # Get messages with attachments
        cursor.execute(
            "SELECT role, content, attachments, created_at FROM messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,)
        )
        messages = cursor.fetchall()
        
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "title": row["title"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "messages": [
            {
                "role": m["role"], 
                "content": m["content"], 
                "attachments": json.loads(m["attachments"] or "[]"),
                "created_at": m["created_at"]
            }
            for m in messages
        ]
    }


def verify_session_ownership(session_id: str, user_id: str) -> bool:
    """
    Verify that a user owns a session
    
    Args:
        session_id: Session UUID
        user_id: User ID to check
        
    Returns:
        True if user owns the session, False otherwise
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id)
        )
        return cursor.fetchone() is not None


def update_session(session_id: str, title: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Update session title (sets title_custom flag)
    
    Args:
        session_id: Session UUID
        title: New title
        user_id: If provided, validates ownership
        
    Returns:
        Updated session dict, or None if not found/unauthorized
    """
    now = datetime.utcnow().isoformat()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute(
                "UPDATE sessions SET title = ?, updated_at = ?, title_custom = 1 WHERE id = ? AND user_id = ?",
                (title, now, session_id, user_id)
            )
        else:
            cursor.execute(
                "UPDATE sessions SET title = ?, updated_at = ?, title_custom = 1 WHERE id = ?",
                (title, now, session_id)
            )
        conn.commit()
        
        if cursor.rowcount == 0:
            return None
    
    return get_session(session_id, user_id)


def delete_session(session_id: str, user_id: Optional[str] = None) -> bool:
    """
    Delete a session and all its messages
    
    Args:
        session_id: Session UUID
        user_id: If provided, validates ownership
        
    Returns:
        True if deleted, False if not found/unauthorized
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Delete messages first (foreign key)
        cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        
        # Delete session (with optional user check)
        if user_id:
            cursor.execute("DELETE FROM sessions WHERE id = ? AND user_id = ?", (session_id, user_id))
        else:
            cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
        
        deleted = cursor.rowcount > 0
    
    if deleted:
        log_info(f"[SESSIONS] Deleted session: {session_id}")
    
    return deleted


# =====================================================================
# MESSAGE MANAGEMENT
# =====================================================================

def add_message(
    session_id: str, 
    role: str, 
    content: str, 
    attachments: Optional[List[Dict]] = None,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Add a message to a session
    
    Args:
        session_id: Session UUID
        role: 'user' or 'assistant'
        content: Message content
        attachments: List of attachment dicts
        user_id: If provided, validates ownership
        
    Returns:
        Message dict with id and created_at
        
    Raises:
        ValueError: If content exceeds MAX_CONTENT_LENGTH
        PermissionError: If user doesn't own the session
    """
    # Validate content length
    if len(content) > MAX_CONTENT_LENGTH:
        raise ValueError(f"Content too long: {len(content)} chars (max {MAX_CONTENT_LENGTH})")
    
    # Validate ownership if user_id provided
    if user_id and not verify_session_ownership(session_id, user_id):
        raise PermissionError(f"User {user_id} does not own session {session_id}")
    
    now = datetime.utcnow().isoformat()
    attachments_json = json.dumps(attachments or [])
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Insert message
        cursor.execute(
            "INSERT INTO messages (session_id, role, content, attachments, created_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, attachments_json, now)
        )
        message_id = cursor.lastrowid
        
        # Update session timestamp
        cursor.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (now, session_id)
        )
        
        # Auto-update title only if not custom (first user message)
        if role == "user":
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM messages WHERE session_id = ? AND role = 'user'",
                (session_id,)
            )
            user_msg_count = cursor.fetchone()["cnt"]
            
            if user_msg_count == 1:
                cursor.execute(
                    "SELECT title_custom FROM sessions WHERE id = ?",
                    (session_id,)
                )
                row = cursor.fetchone()
                if row and row["title_custom"] == 0:
                    title = content[:50] + ("..." if len(content) > 50 else "")
                    cursor.execute(
                        "UPDATE sessions SET title = ? WHERE id = ?",
                        (title, session_id)
                    )
        
        conn.commit()
    
    return {
        "id": message_id,
        "session_id": session_id,
        "role": role,
        "content": content,
        "attachments": attachments or [],
        "created_at": now
    }


def get_session_messages(
    session_id: str, 
    limit: int = 100, 
    offset: int = 0,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get messages for a session with pagination
    
    Args:
        session_id: Session UUID
        limit: Max messages to return
        offset: Number of messages to skip
        user_id: If provided, validates ownership
        
    Returns:
        Dict with messages list and has_more flag
        
    Raises:
        PermissionError: If user doesn't own the session
    """
    # Validate ownership if user_id provided
    if user_id and not verify_session_ownership(session_id, user_id):
        raise PermissionError(f"User {user_id} does not own session {session_id}")
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM messages WHERE session_id = ?",
            (session_id,)
        )
        total = cursor.fetchone()["cnt"]
        
        # Get messages
        cursor.execute(
            """
            SELECT role, content, attachments FROM messages 
            WHERE session_id = ? 
            ORDER BY created_at ASC 
            LIMIT ? OFFSET ?
            """,
            (session_id, limit, offset)
        )
        rows = cursor.fetchall()
    
    return {
        "messages": [
            {
                "role": row["role"], 
                "content": row["content"],
                "attachments": json.loads(row["attachments"] or "[]")
            } 
            for row in rows
        ],
        "has_more": (offset + len(rows)) < total,
        "total": total
    }


def add_conversation_pair(
    session_id: str, 
    user_content: str, 
    assistant_content: str,
    user_attachments: Optional[List[Dict]] = None,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Add user and assistant messages in a single transaction
    Prevents race condition where user message is saved but assistant isn't
    
    Args:
        session_id: Session UUID
        user_content: User message content
        assistant_content: Assistant response content
        user_attachments: Attachments from user message
        user_id: If provided, validates ownership
        
    Returns:
        Dict with both message IDs
        
    Raises:
        PermissionError: If user doesn't own the session
    """
    # Validate ownership if user_id provided
    if user_id and not verify_session_ownership(session_id, user_id):
        raise PermissionError(f"User {user_id} does not own session {session_id}")
    
    now = datetime.utcnow().isoformat()
    user_attachments_json = json.dumps(user_attachments or [])
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        try:
            # Insert user message
            cursor.execute(
                "INSERT INTO messages (session_id, role, content, attachments, created_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, "user", user_content, user_attachments_json, now)
            )
            user_msg_id = cursor.lastrowid
            
            # Insert assistant message
            cursor.execute(
                "INSERT INTO messages (session_id, role, content, attachments, created_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, "assistant", assistant_content, "[]", now)
            )
            assistant_msg_id = cursor.lastrowid
            
            # Update session timestamp
            cursor.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (now, session_id)
            )
            
            # Auto-update title only if not custom
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM messages WHERE session_id = ? AND role = 'user'",
                (session_id,)
            )
            user_msg_count = cursor.fetchone()["cnt"]
            
            if user_msg_count == 1:
                cursor.execute(
                    "SELECT title_custom FROM sessions WHERE id = ?",
                    (session_id,)
                )
                row = cursor.fetchone()
                if row and row["title_custom"] == 0:
                    title = user_content[:50] + ("..." if len(user_content) > 50 else "")
                    cursor.execute(
                        "UPDATE sessions SET title = ? WHERE id = ?",
                        (title, session_id)
                    )
            
            conn.commit()
            
            return {
                "user_message_id": user_msg_id,
                "assistant_message_id": assistant_msg_id,
                "session_id": session_id,
                "created_at": now
            }
            
        except Exception as e:
            conn.rollback()
            log_error(e, "ADD_CONVERSATION_PAIR")
            raise


# Initialize database on module load
try:
    init_sessions_db()
except Exception as e:
    log_error(e, "SESSIONS_INIT")
