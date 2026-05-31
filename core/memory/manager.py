import json
import logging
import os
import sqlite3
import sys
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

# --- Database Initialization ---
def init_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Initialize the SQLite memory database and create the tables if they don't exist."""
    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
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
        """Clear all content in memories, FTS, and playbook tables (for testing)."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories")
            cursor.execute("DELETE FROM memories_fts")
            cursor.execute("DELETE FROM playbook")
            conn.commit()
            logger.info("Purged all table records from the database.")
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to clear database: {e}")
            raise
        finally:
            conn.close()
