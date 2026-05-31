import json
import logging
import math
import os
import sqlite3
import sys
import urllib.request
from pathlib import Path

# Add project root directory to sys.path to allow execution of scripts directly
_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
from typing import Any, Dict, List, Optional
from cryptography.fernet import Fernet

# --- Setup Logging ---
logger = logging.getLogger("mithrandir")
logger.setLevel(logging.INFO)

# Make sure stderr logging matches mithrandir system formatting if not configured
if not logger.handlers:
    stderr_handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter(
        "⚡️ [%(levelname)s] %(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    stderr_handler.setFormatter(formatter)
    logger.addHandler(stderr_handler)
    logger.propagate = False

# --- Path Configurations ---
WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = WORKSPACE_DIR / ".env"
DB_PATH = WORKSPACE_DIR / "mithrandir_memory.db"

# --- Environment Loading ---
def load_env() -> Dict[str, str]:
    """Manually parse .env file if it exists, without introducing extra dependencies."""
    env_vars = {}
    if ENV_PATH.exists():
        with open(ENV_PATH, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip()
                    # Inject into os.environ for compatibility
                    os.environ[k.strip()] = v.strip()
    return env_vars

# Load environment at module initialization
load_env()

# --- Symmetric Encryption Helpers ---
def _get_fernet() -> Fernet:
    """Helper to initialize the Fernet cipher using MITHRANDIR_JOURNAL_KEY."""
    key = os.environ.get("MITHRANDIR_JOURNAL_KEY")
    if not key:
        logger.error("MITHRANDIR_JOURNAL_KEY environment variable not set in environment or .env file.")
        raise ValueError("MITHRANDIR_JOURNAL_KEY environment variable not set")
    try:
        return Fernet(key.encode())
    except Exception as e:
        logger.error(f"Invalid MITHRANDIR_JOURNAL_KEY structure: {e}")
        raise ValueError(f"Invalid MITHRANDIR_JOURNAL_KEY: {e}")

def encrypt_journal(text: str) -> str:
    """Encrypt journal content using AES-256 Fernet."""
    if not text:
        return ""
    f = _get_fernet()
    return f.encrypt(text.encode()).decode()

def decrypt_journal(encrypted_text: str) -> str:
    """Decrypt journal content using AES-256 Fernet."""
    if not encrypted_text:
        return ""
    f = _get_fernet()
    try:
        return f.decrypt(encrypted_text.encode()).decode()
    except Exception as e:
        logger.error(f"Failed to decrypt journal text: {e}")
        return "[DECRYPTION_ERROR]"

# --- Vector Embedding & Similarity Helpers ---
def get_embedding(text: str) -> Optional[List[float]]:
    """
    Fetch a 768-dimension vector from the Gemini embeddings API
    (model text-embedding-004) using urllib. Handles offline/missing key scenarios.
    """
    if not text or not text.strip():
        return None

    gemini_key = os.environ.get("GEMINI_API_KEY")
    def is_valid(key: Optional[str]) -> bool:
        return bool(key and "placeholder" not in key.lower() and "your_" not in key.lower())

    if not is_valid(gemini_key):
        logger.warning("GEMINI_API_KEY is not set or invalid; skipping embedding generation.")
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={gemini_key}"
    data = {
        "model": "models/text-embedding-004",
        "content": {
            "parts": [{"text": text}]
        }
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            embedding = res_data.get("embedding", {}).get("values")
            if embedding and len(embedding) == 768:
                return embedding
            else:
                logger.warning(f"Embedding returned unexpected structure or dimension: {res_data}")
                return None
    except Exception as e:
        logger.warning(f"Failed to fetch vector embedding: {e}")
        return None

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculate the cosine similarity between two vectors using pure Python and math."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot_product = sum(x * y for x, y in zip(v1, v2))
    norm_v1 = math.sqrt(sum(x * x for x in v1))
    norm_v2 = math.sqrt(sum(y * y for y in v2))
    if norm_v1 == 0.0 or norm_v2 == 0.0:
        return 0.0
    return dot_product / (norm_v1 * norm_v2)

# --- Database Initialization ---
def init_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Initialize the SQLite memory database and create the tables if they don't exist."""
    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()
    
    # 1. Create memories table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            category TEXT NOT NULL,
            content TEXT NOT NULL,
            metadata TEXT DEFAULT '{}'
        )
    """)
    
    # 2. Create memories_fts virtual table (FTS5)
    # ThisIndexes only non-journal content.
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
            content,
            category
        )
    """)
    
    # 3. Create playbook table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS playbook (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            topic TEXT NOT NULL UNIQUE,
            summary TEXT NOT NULL,
            rules TEXT NOT NULL
        )
    """)
    
    # 4. Create portfolio_statements table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_statements (
            statement_id TEXT PRIMARY KEY,
            account_key TEXT NOT NULL,
            account_number TEXT NOT NULL,
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            opening_total_value REAL NOT NULL,
            closing_total_value REAL NOT NULL,
            opening_cash REAL DEFAULT 0.0,
            closing_cash REAL DEFAULT 0.0,
            opening_securities REAL DEFAULT 0.0,
            closing_securities REAL DEFAULT 0.0,
            deposits REAL DEFAULT 0.0,
            withdrawals REAL DEFAULT 0.0,
            dividends_interest REAL DEFAULT 0.0,
            file_path TEXT NOT NULL,
            is_canonical INTEGER DEFAULT 1,
            added_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 5. Create portfolio_positions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            statement_id TEXT NOT NULL,
            ticker TEXT NOT NULL,
            quantity REAL NOT NULL,
            price REAL NOT NULL,
            market_value REAL NOT NULL,
            percent_of_account REAL,
            FOREIGN KEY (statement_id) REFERENCES portfolio_statements (statement_id) ON DELETE CASCADE
        )
    """)

    # 6. Create memory_embeddings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memory_embeddings (
            memory_id INTEGER PRIMARY KEY,
            embedding TEXT NOT NULL,
            FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    logger.info(f"Mithrandir 2.0 database tables initialized successfully at {db_path}.")
    return conn

# --- Memory Manager Class ---
class MemoryManager:
    """Manages CRUD operations and searches on the Mithrandir 2.0 durable memory layer."""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        init_db(self.db_path)

    def get_connection(self) -> sqlite3.Connection:
        """Establish and return an sqlite3 connection with Row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def add_memory(self, category: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        """
        Add a memory to the database. Encrypts 'content' if category is 'journal'.
        Indexes 'content' in FTS5 only if category is NOT 'journal'.
        """
        meta_str = json.dumps(metadata or {})
        is_journal = category.lower() == "journal"
        
        if is_journal:
            stored_content = encrypt_journal(content)
        else:
            stored_content = content

        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            # Insert into memories
            cursor.execute(
                "INSERT INTO memories (category, content, metadata) VALUES (?, ?, ?)",
                (category, stored_content, meta_str)
            )
            memory_id = cursor.lastrowid
            
            # Index non-journal content in FTS5 virtual table
            if not is_journal:
                cursor.execute(
                    "INSERT INTO memories_fts (rowid, content, category) VALUES (?, ?, ?)",
                    (memory_id, content, category)
                )
            
            # Fetch and store vector embedding
            embedding = get_embedding(content)
            if embedding:
                cursor.execute(
                    "INSERT INTO memory_embeddings (memory_id, embedding) VALUES (?, ?)",
                    (memory_id, json.dumps(embedding))
                )
            
            conn.commit()
            logger.info(f"Recorded memory ID {memory_id} under category '{category}'")
            return memory_id
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to add memory of category '{category}': {e}")
            raise
        finally:
            conn.close()

    def get_memory(self, memory_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a specific memory by ID. Automatically decrypts journal entries."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, timestamp, category, content, metadata FROM memories WHERE id = ?",
                (memory_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None

            category = row["category"]
            is_journal = category.lower() == "journal"
            raw_content = row["content"]

            if is_journal:
                content = decrypt_journal(raw_content)
            else:
                content = raw_content

            return {
                "id": row["id"],
                "timestamp": row["timestamp"],
                "category": category,
                "content": content,
                "metadata": json.loads(row["metadata"] or "{}")
            }
        except Exception as e:
            logger.error(f"Failed to retrieve memory ID {memory_id}: {e}")
            raise
        finally:
            conn.close()

    def update_memory(self, memory_id: int, category: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update an existing memory. Synchronizes with FTS5 index and encrypts if category is 'journal'."""
        meta_str = json.dumps(metadata or {})
        is_journal = category.lower() == "journal"
        
        if is_journal:
            stored_content = encrypt_journal(content)
        else:
            stored_content = content

        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT category FROM memories WHERE id = ?", (memory_id,))
            row = cursor.fetchone()
            if not row:
                logger.warning(f"Memory ID {memory_id} not found for update.")
                return False

            old_category = row["category"]
            old_is_journal = old_category.lower() == "journal"

            # Update base memories table
            cursor.execute(
                "UPDATE memories SET category = ?, content = ?, metadata = ? WHERE id = ?",
                (category, stored_content, meta_str, memory_id)
            )

            # Update FTS5 index dynamically based on state transitions
            if old_is_journal and not is_journal:
                cursor.execute(
                    "INSERT INTO memories_fts (rowid, content, category) VALUES (?, ?, ?)",
                    (memory_id, content, category)
                )
            elif not old_is_journal and is_journal:
                cursor.execute(
                    "DELETE FROM memories_fts WHERE rowid = ?",
                    (memory_id,)
                )
            elif not is_journal:
                cursor.execute(
                    "UPDATE memories_fts SET content = ?, category = ? WHERE rowid = ?",
                    (content, category, memory_id)
                )

            # Fetch and store vector embedding
            embedding = get_embedding(content)
            if embedding:
                cursor.execute(
                    "INSERT OR REPLACE INTO memory_embeddings (memory_id, embedding) VALUES (?, ?)",
                    (memory_id, json.dumps(embedding))
                )
            else:
                cursor.execute(
                    "DELETE FROM memory_embeddings WHERE memory_id = ?",
                    (memory_id,)
                )
            
            conn.commit()
            logger.info(f"Updated memory ID {memory_id} successfully.")
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to update memory ID {memory_id}: {e}")
            raise
        finally:
            conn.close()

    def delete_memory(self, memory_id: int) -> bool:
        """Delete a memory and purge it from FTS5 virtual table."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            cursor.execute("DELETE FROM memories_fts WHERE rowid = ?", (memory_id,))
            conn.commit()
            logger.info(f"Deleted memory ID {memory_id} and its FTS5 index entry.")
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to delete memory ID {memory_id}: {e}")
            raise
        finally:
            conn.close()

    def search_memories(self, query: Optional[str] = None, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search memories matching optionally a query string and category filter.
        Uses FTS5 for indexing search on non-journal content.
        Performs decrypt-and-match search in memory for 'journal' entries.
        """
        results = []
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Determine which categories to query
            search_non_journal = True
            search_journal = False
            
            if category:
                category_lower = category.lower()
                if category_lower == "journal":
                    search_non_journal = False
                    search_journal = True
                else:
                    search_non_journal = True
                    search_journal = False
            else:
                search_non_journal = True
                search_journal = True

            # 1. Search non-journal entries using FTS5 (if query is present)
            if search_non_journal:
                if query:
                    clean_query = query.replace('"', '""')
                    sql = """
                        SELECT m.id, m.timestamp, m.category, m.content, m.metadata
                        FROM memories m
                        JOIN memories_fts f ON m.id = f.rowid
                        WHERE memories_fts MATCH ?
                    """
                    params = [clean_query]
                    if category:
                        sql += " AND m.category = ?"
                        params.append(category)
                    
                    try:
                        cursor.execute(sql, params)
                        rows = cursor.fetchall()
                    except sqlite3.OperationalError as oe:
                        # Fail-safe: fall back to LIKE search if FTS5 syntax parser fails
                        logger.warning(f"FTS5 search failed, falling back to LIKE search: {oe}")
                        fallback_sql = """
                            SELECT id, timestamp, category, content, metadata
                            FROM memories
                            WHERE content LIKE ? AND category != 'journal'
                        """
                        fallback_params = [f"%{query}%"]
                        if category:
                            fallback_sql += " AND category = ?"
                            fallback_params.append(category)
                        cursor.execute(fallback_sql, fallback_params)
                        rows = cursor.fetchall()
                else:
                    sql = "SELECT id, timestamp, category, content, metadata FROM memories WHERE category != 'journal'"
                    params = []
                    if category:
                        sql += " AND category = ?"
                        params.append(category)
                    cursor.execute(sql, params)
                    rows = cursor.fetchall()

                for row in rows:
                    results.append({
                        "id": row["id"],
                        "timestamp": row["timestamp"],
                        "category": row["category"],
                        "content": row["content"],
                        "metadata": json.loads(row["metadata"] or "{}")
                    })

            # 2. Search journal entries (decrypt in-memory and match)
            if search_journal:
                sql = "SELECT id, timestamp, category, content, metadata FROM memories WHERE category = 'journal'"
                cursor.execute(sql)
                rows = cursor.fetchall()
                for row in rows:
                    decrypted_content = decrypt_journal(row["content"])
                    if query and query.lower() not in decrypted_content.lower():
                        continue
                    results.append({
                        "id": row["id"],
                        "timestamp": row["timestamp"],
                        "category": row["category"],
                        "content": decrypted_content,
                        "metadata": json.loads(row["metadata"] or "{}")
                    })
            
            # Sort chronologically descending (most recent first)
            results.sort(key=lambda x: (x["timestamp"], x["id"]), reverse=True)
            return results
        except Exception as e:
            logger.error(f"Error executing memory search: {e}")
            raise
        finally:
            conn.close()

    def semantic_search_memories(self, query: str, category: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search memories by vector similarity using Gemini text-embedding-004.
        Falls back to FTS5 keyword search if offline or missing key.
        """
        query_emb = get_embedding(query)
        if not query_emb:
            logger.warning("Gemini embeddings API failed or key missing. Falling back to traditional FTS5/keyword search.")
            return self.search_memories(query=query, category=category)[:limit]

        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            sql = """
                SELECT m.id, m.timestamp, m.category, m.content, m.metadata, e.embedding
                FROM memories m
                JOIN memory_embeddings e ON m.id = e.memory_id
            """
            params = []
            if category:
                sql += " WHERE m.category = ?"
                params.append(category)
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            scored_memories = []
            for row in rows:
                try:
                    emb_list = json.loads(row["embedding"])
                except Exception:
                    continue
                
                sim = cosine_similarity(query_emb, emb_list)
                
                cat = row["category"]
                raw_content = row["content"]
                if cat.lower() == "journal":
                    content = decrypt_journal(raw_content)
                else:
                    content = raw_content
                    
                scored_memories.append({
                    "id": row["id"],
                    "timestamp": row["timestamp"],
                    "category": cat,
                    "content": content,
                    "metadata": json.loads(row["metadata"] or "{}"),
                    "similarity": sim
                })
                
            scored_memories.sort(key=lambda x: x["similarity"], reverse=True)
            return scored_memories[:limit]
        except Exception as e:
            logger.error(f"Error executing semantic memory search: {e}")
            raise
        finally:
            conn.close()

    # --- Playbook Operations ---
    def upsert_playbook_topic(self, topic: str, summary: str, rules: List[str]) -> int:
        """Upsert a topic in the playbook table (replaces on duplicate topic)."""
        rules_str = json.dumps(rules)
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO playbook (topic, summary, rules, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(topic) DO UPDATE SET
                    summary = excluded.summary,
                    rules = excluded.rules,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (topic, summary, rules_str)
            )
            cursor.execute("SELECT id FROM playbook WHERE topic = ?", (topic,))
            row = cursor.fetchone()
            playbook_id = row["id"]
            conn.commit()
            logger.info(f"Upserted playbook topic '{topic}' (ID: {playbook_id})")
            return playbook_id
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to upsert playbook topic '{topic}': {e}")
            raise
        finally:
            conn.close()

    def get_playbook_topic(self, topic: str) -> Optional[Dict[str, Any]]:
        """Retrieve a playbook topic details."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, updated_at, topic, summary, rules FROM playbook WHERE topic = ?",
                (topic,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "updated_at": row["updated_at"],
                    "topic": row["topic"],
                    "summary": row["summary"],
                    "rules": json.loads(row["rules"] or "[]")
                }
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve playbook topic '{topic}': {e}")
            raise
        finally:
            conn.close()

    def list_playbook_topics(self) -> List[Dict[str, Any]]:
        """List all topics available in the playbook."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, updated_at, topic, summary, rules FROM playbook ORDER BY topic ASC")
            results = []
            for row in cursor.fetchall():
                results.append({
                    "id": row["id"],
                    "updated_at": row["updated_at"],
                    "topic": row["topic"],
                    "summary": row["summary"],
                    "rules": json.loads(row["rules"] or "[]")
                })
            return results
        except Exception as e:
            logger.error(f"Failed to list playbook topics: {e}")
            raise
        finally:
            conn.close()

    def export_memories(self, export_dir: Optional[Path] = None) -> Path:
        """
        Export all database memories (including decrypted journal entries for backup traceability)
        to a JSON file. The output filename contains an ISO-8601 timestamp.
        """
        import datetime
        target_dir = export_dir or (WORKSPACE_DIR / "data" / "exports")
        target_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp_str = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        filename = f"memories_{timestamp_str}.json"
        export_file = target_dir / filename
        
        memories = self.search_memories()
        
        # Structure the export
        export_data = {
            "exported_at": datetime.datetime.now().isoformat(),
            "total_records": len(memories),
            "memories": memories
        }
        
        with open(export_file, "w") as f:
            json.dump(export_data, f, indent=2)
            
        logger.info(f"Successfully exported memories to {export_file}")
        return export_file

    def clear_all(self):
        """Clear all content in memories, FTS, playbook, and portfolio tables (for testing)."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories")
            cursor.execute("DELETE FROM memories_fts")
            cursor.execute("DELETE FROM playbook")
            cursor.execute("DELETE FROM portfolio_positions")
            cursor.execute("DELETE FROM portfolio_statements")
            cursor.execute("DELETE FROM memory_embeddings")
            conn.commit()
            logger.info("Purged all table records from the database.")
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to clear database: {e}")
            raise
        finally:
            conn.close()

    def clear_portfolio_data(self):
        """Clear only portfolio statements and positions from the database."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM portfolio_positions")
            cursor.execute("DELETE FROM portfolio_statements")
            conn.commit()
            logger.info("Purged portfolio tables successfully.")
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to clear portfolio tables: {e}")
            raise
        finally:
            conn.close()

    def add_portfolio_statement(self, s: Dict[str, Any]) -> bool:
        """Add or update a parsed portfolio statement in SQLite memory."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO portfolio_statements (
                    statement_id, account_key, account_number, period_start, period_end,
                    opening_total_value, closing_total_value, opening_cash, closing_cash,
                    opening_securities, closing_securities, deposits, withdrawals,
                    dividends_interest, file_path, is_canonical
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                s["statement_id"], s["account_key"], s["account_number"], s["period_start"], s["period_end"],
                s["opening_total_value"], s["closing_total_value"], s.get("opening_cash", 0.0), s.get("closing_cash", 0.0),
                s.get("opening_securities", 0.0), s.get("closing_securities", 0.0), s.get("deposits", 0.0),
                s.get("withdrawals", 0.0), s.get("dividends_interest", 0.0), s["file_path"], s.get("is_canonical", 1)
            ))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to add portfolio statement {s.get('statement_id')}: {e}")
            raise
        finally:
            conn.close()

    def add_portfolio_position(self, p: Dict[str, Any]) -> bool:
        """Add a position snapshot holding associated with a statement."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO portfolio_positions (
                    statement_id, ticker, quantity, price, market_value, percent_of_account
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                p["statement_id"], p["ticker"], p["quantity"], p["price"], p["market_value"], p.get("percent_of_account")
            ))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to add portfolio position for {p.get('statement_id')} / {p.get('ticker')}: {e}")
            raise
        finally:
            conn.close()

    def get_portfolio_statements(self, account_key: Optional[str] = None, canonical_only: bool = True) -> List[Dict[str, Any]]:
        """Retrieve statements chronologically. Filters by account and canonical choice."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            sql = "SELECT * FROM portfolio_statements"
            params = []
            conditions = []
            if account_key:
                conditions.append("account_key = ?")
                params.append(account_key)
            if canonical_only:
                conditions.append("is_canonical = 1")
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            sql += " ORDER BY period_end ASC"
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to query portfolio statements: {e}")
            raise
        finally:
            conn.close()

    def get_statement_positions(self, statement_id: str) -> List[Dict[str, Any]]:
        """Retrieve all holdings associated with a specific statement."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM portfolio_positions WHERE statement_id = ?", (statement_id,))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to query portfolio positions for statement {statement_id}: {e}")
            raise
        finally:
            conn.close()

    def mark_duplicate_statements(self, account_key: str, period_end: str, keep_statement_id: str):
        """Deduplicate records by marking non-canonical duplicates for the same month/account."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE portfolio_statements
                SET is_canonical = 0
                WHERE account_key = ? AND period_end = ? AND statement_id != ?
            """, (account_key, period_end, keep_statement_id))
            cursor.execute("""
                UPDATE portfolio_statements
                SET is_canonical = 1
                WHERE statement_id = ?
            """, (keep_statement_id,))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to mark duplicate statements: {e}")
            raise
        finally:
            conn.close()
