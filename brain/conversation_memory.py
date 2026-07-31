import sqlite3
import datetime
import json
from typing import Dict, Any, List, Optional
from brain.privacy_sanitizer import PrivacySanitizer

class ConversationMemoryManager:
    """
    Multi-Turn Conversation Memory and State Persistence Manager.
    Prevents loss of context across messages by storing entities, intent, and turns in SQLite.
    """

    def __init__(self, db_path: str = "/Users/gustavoalmeida/Cartorio/brain.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    message_text TEXT NOT NULL,
                    entities_json TEXT,
                    timestamp TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_state (
                    session_id TEXT PRIMARY KEY,
                    current_act TEXT,
                    active_zip TEXT,
                    client_name TEXT,
                    last_updated TEXT
                )
            """)
            conn.commit()

    def add_turn(self, session_id: str, sender: str, message: str, entities: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        sanitized_msg = PrivacySanitizer.sanitize(message)
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        entities_str = json.dumps(entities or {}, ensure_ascii=False)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO conversation_memory (session_id, sender, message_text, entities_json, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, sender, sanitized_msg, entities_str, now))
            conn.commit()

        return {"session_id": session_id, "sender": sender, "message": sanitized_msg, "timestamp": now}

    def get_conversation_context(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM conversation_memory WHERE session_id = ? ORDER BY id DESC LIMIT ?
            """, (session_id, limit))
            rows = cursor.fetchall()
            turns = [dict(r) for r in reversed(rows)]
            return turns

    def update_session_state(self, session_id: str, act: Optional[str] = None, zip_file: Optional[str] = None, client: Optional[str] = None):
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO session_state (session_id, current_act, active_zip, client_name, last_updated)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    current_act=COALESCE(excluded.current_act, session_state.current_act),
                    active_zip=COALESCE(excluded.active_zip, session_state.active_zip),
                    client_name=COALESCE(excluded.client_name, session_state.client_name),
                    last_updated=excluded.last_updated
            """, (session_id, act, zip_file, client, now))
            conn.commit()

    def get_session_state(self, session_id: str) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM session_state WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            return dict(row) if row else {"session_id": session_id, "current_act": None, "active_zip": None, "client_name": None}
