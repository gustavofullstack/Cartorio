import datetime
import hashlib
import json
import os
import sqlite3
from typing import Dict, Any, List, Optional
from brain.privacy_sanitizer import PrivacySanitizer

class TraceabilityLogger:
    """
    Records and queries execution traceability for every agent action across the BRAIN pipeline.
    """
    
    def __init__(self, db_path: str = "/Users/gustavoalmeida/Cartorio/brain.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_traceability (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_name TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    input_summary TEXT,
                    output_summary TEXT,
                    confidence_score REAL,
                    data_hash TEXT,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.commit()

    def log_action(self, agent_name: str, action_type: str, input_data: Any, output_data: Any, confidence_score: float = 1.0) -> Dict[str, Any]:
        """
        Logs an agent action into the database after sanitizing PII.
        """
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        input_str = PrivacySanitizer.sanitize(str(input_data))[:1000]
        output_str = PrivacySanitizer.sanitize(str(output_data))[:1000]
        
        combined_payload = f"{agent_name}:{action_type}:{input_str}:{output_str}:{timestamp}"
        data_hash = hashlib.sha256(combined_payload.encode('utf-8')).hexdigest()[:16]

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO agent_traceability (agent_name, action_type, input_summary, output_summary, confidence_score, data_hash, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (agent_name, action_type, input_str, output_str, confidence_score, data_hash, timestamp))
            conn.commit()

        return {
            "agent_name": agent_name,
            "action_type": action_type,
            "confidence_score": confidence_score,
            "data_hash": data_hash,
            "timestamp": timestamp
        }

    def get_logs(self, agent_name: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieves traceability logs.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if agent_name:
                cursor.execute("""
                    SELECT * FROM agent_traceability WHERE agent_name = ? ORDER BY id DESC LIMIT ?
                """, (agent_name, limit))
            else:
                cursor.execute("""
                    SELECT * FROM agent_traceability ORDER BY id DESC LIMIT ?
                """, (limit,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
