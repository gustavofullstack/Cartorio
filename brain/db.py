import os
import json
import sqlite3
import hashlib
import datetime
from typing import Dict, Any, List, Optional
from brain.privacy_sanitizer import PrivacySanitizer

class BrainDatabase:
    """
    SQLite database interface for the BRAIN system.
    Handles indexing of documents, legal rules, fee tables, and requirements.
    """

    def __init__(self, db_path: str = "/Users/gustavoalmeida/Cartorio/brain.db"):
        self.db_path = db_path
        self.init_schema()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Documents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT UNIQUE NOT NULL,
                    extension TEXT NOT NULL,
                    word_count INTEGER,
                    char_count INTEGER,
                    category TEXT NOT NULL,
                    text_content TEXT,
                    sanitized_text TEXT,
                    data_hash TEXT,
                    created_at TEXT
                )
            """)
            
            # Document Requirements Checklist table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS document_requirements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    act_name TEXT NOT NULL,
                    required_doc_name TEXT NOT NULL,
                    is_mandatory INTEGER DEFAULT 1,
                    description TEXT
                )
            """)
            
            # Mandatory Legal Clauses table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mandatory_clauses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    act_name TEXT NOT NULL,
                    clause_title TEXT NOT NULL,
                    mandatory_text TEXT NOT NULL,
                    legal_basis TEXT
                )
            """)
            
            # Fee & Emoluments Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fee_tables (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    table_code TEXT NOT NULL,
                    act_type TEXT NOT NULL,
                    min_value REAL,
                    max_value REAL,
                    fee_amount REAL,
                    notes TEXT
                )
            """)
            
            # CNJ & Regulatory Norms table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS provimentos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provimento_num TEXT NOT NULL,
                    year INTEGER,
                    title TEXT NOT NULL,
                    summary TEXT,
                    key_articles TEXT
                )
            """)

            conn.commit()

    def populate_from_inventory(self, inventory_json_path: str = "/Users/gustavoalmeida/Cartorio/inventory.json"):
        if not os.path.exists(inventory_json_path):
            print(f"Inventory file not found at {inventory_json_path}")
            return
        
        with open(inventory_json_path, 'r', encoding='utf-8') as f:
            inventory = json.load(f)

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for item in inventory:
                raw_text = item.get("text", "")
                sanitized_text = PrivacySanitizer.sanitize(raw_text)
                data_hash = hashlib.sha256(raw_text.encode('utf-8')).hexdigest()[:16]

                cursor.execute("""
                    INSERT INTO documents (filename, extension, word_count, char_count, category, text_content, sanitized_text, data_hash, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(filename) DO UPDATE SET
                        word_count=excluded.word_count,
                        char_count=excluded.char_count,
                        category=excluded.category,
                        sanitized_text=excluded.sanitized_text,
                        data_hash=excluded.data_hash
                """, (
                    item["filename"],
                    item["extension"],
                    item["word_count"],
                    item["char_count"],
                    item.get("initial_category", "Geral"),
                    raw_text,
                    sanitized_text,
                    data_hash,
                    now
                ))
            conn.commit()
            print(f"Populated DB with {len(inventory)} documents from inventory.")

    def search_documents(self, query: str, category: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            sql = "SELECT id, filename, extension, word_count, category, sanitized_text FROM documents WHERE 1=1"
            params = []
            if category:
                sql += " AND category = ?"
                params.append(category)
            if query:
                sql += " AND (filename LIKE ? OR sanitized_text LIKE ?)"
                params.append(f"%{query}%")
                params.append(f"%{query}%")
            sql += " LIMIT ?"
            params.append(limit)

            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_document_by_filename(self, filename: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE filename = ?", (filename,))
            row = cursor.fetchone()
            return dict(row) if row else None
