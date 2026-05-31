import os
import tempfile
import sqlite3
import pytest
from pathlib import Path

# Ensure encryption key is defined for the tests
os.environ["MITHRANDIR_JOURNAL_KEY"] = "cw-Z35q6XG49tO08R1x5y4Q9W2vB7uL4pT2mB8eJ6g8="

from core.memory.manager import (
    MemoryManager,
    encrypt_journal,
    decrypt_journal,
    init_db
)
from core.memory.fenced_context import get_fenced_context
from core.memory.compactor import MemoryCompactor

@pytest.fixture
def temp_db():
    """Fixture that creates a temporary database file and yields its path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_path = Path(f.name)
    
    yield temp_path
    
    # Cleanup after test
    if temp_path.exists():
        try:
            temp_path.unlink()
        except OSError:
            pass

def test_journal_encryption_decryption():
    """Verify that journal entries are correctly encrypted and decrypted using Fernet."""
    secret_text = "This is a confidential journal log containing api key 12345."
    
    encrypted = encrypt_journal(secret_text)
    assert encrypted != secret_text
    assert len(encrypted) > len(secret_text)
    
    decrypted = decrypt_journal(encrypted)
    assert decrypted == secret_text
    
    # Decrypting empty values should return empty
    assert decrypt_journal("") == ""
    assert encrypt_journal("") == ""

def test_database_initialization(temp_db):
    """Verify that all required tables and FTS5 indexes are successfully initialized."""
    conn = init_db(temp_db)
    cursor = conn.cursor()
    
    # Retrieve all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    assert "memories" in tables
    assert "playbook" in tables
    
    # Check for FTS5 virtual table structures (sqlite creates shadow tables for fts5)
    # The virtual table itself shows up in the tables list
    assert "memories_fts" in tables
    
    conn.close()

def test_add_and_get_memory(temp_db):
    """Verify that memories are written, encrypted on category 'journal', and correctly decrypted on retrieve."""
    manager = MemoryManager(temp_db)
    
    # 1. Non-journal memory (plaintext)
    meta = {"session_id": "test-123", "user": "alice"}
    mem_id_1 = manager.add_memory(
        category="investing",
        content="Bought 10 shares of AAPL stock.",
        metadata=meta
    )
    
    retrieved_1 = manager.get_memory(mem_id_1)
    assert retrieved_1 is not None
    assert retrieved_1["category"] == "investing"
    assert retrieved_1["content"] == "Bought 10 shares of AAPL stock."
    assert retrieved_1["metadata"] == meta
    
    # Check raw DB content to verify it's stored in plaintext
    conn = sqlite3.connect(temp_db)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT content FROM memories WHERE id = ?", (mem_id_1,)).fetchone()
    assert row["content"] == "Bought 10 shares of AAPL stock."
    conn.close()
    
    # 2. Journal memory (encrypted)
    mem_id_2 = manager.add_memory(
        category="journal",
        content="Secret keys generated for deployment: 8A72B.",
        metadata={"secure": True}
    )
    
    retrieved_2 = manager.get_memory(mem_id_2)
    assert retrieved_2 is not None
    assert retrieved_2["category"] == "journal"
    assert retrieved_2["content"] == "Secret keys generated for deployment: 8A72B."
    assert retrieved_2["metadata"] == {"secure": True}
    
    # Verify raw DB content is encrypted and does not contain raw string
    conn = sqlite3.connect(temp_db)
    row = conn.execute("SELECT content FROM memories WHERE id = ?", (mem_id_2,)).fetchone()
    assert "8A72B" not in row[0]
    conn.close()

def test_search_memories_and_on_disk_security(temp_db):
    """
    Verify search works for FTS5 (non-journal) and in-memory matching (journal).
    Verify that journal contents are NOT indexed in the FTS5 table to prevent leak.
    """
    manager = MemoryManager(temp_db)
    
    # Add non-journal entries
    manager.add_memory("coding", "Implement pytest tests for MemoryManager.")
    manager.add_memory("investing", "Purchase AAPL shares on market dips.")
    
    # Add journal entry
    manager.add_memory("journal", "Critical incident: DB connection failed due to wrong password 'xyzzy'.")
    
    # 1. Search non-journal (FTS5)
    results_fts = manager.search_memories(query="pytest")
    assert len(results_fts) == 1
    assert results_fts[0]["category"] == "coding"
    assert "pytest" in results_fts[0]["content"]

    # 2. Search journal (In-memory decrypt & match)
    results_journal = manager.search_memories(query="xyzzy")
    assert len(results_journal) == 1
    assert results_journal[0]["category"] == "journal"
    assert "xyzzy" in results_journal[0]["content"]
    
    # 3. Verify security: the word 'xyzzy' must NOT exist in the FTS5 virtual table
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT rowid FROM memories_fts WHERE memories_fts MATCH 'xyzzy'")
    fts_rows = cursor.fetchall()
    assert len(fts_rows) == 0, "Journal secrets must not be indexed in FTS5"
    
    # Verify we can also perform category filtering
    res_filtered = manager.search_memories(query="xyzzy", category="coding")
    assert len(res_filtered) == 0
    
    res_filtered_ok = manager.search_memories(query="xyzzy", category="journal")
    assert len(res_filtered_ok) == 1
    conn.close()

def test_playbook_operations(temp_db):
    """Test upserting, retrieving, and listing playbook topics/rules."""
    manager = MemoryManager(temp_db)
    
    # Upsert new topic
    t_id = manager.upsert_playbook_topic(
        topic="Git Workflow",
        summary="Standard Git protocols for branching.",
        rules=["Always pull main before branching.", "Squash commits before merge."]
    )
    
    p = manager.get_playbook_topic("Git Workflow")
    assert p is not None
    assert p["id"] == t_id
    assert p["topic"] == "Git Workflow"
    assert p["summary"] == "Standard Git protocols for branching."
    assert p["rules"] == ["Always pull main before branching.", "Squash commits before merge."]
    
    # Re-upsert (update) topic
    manager.upsert_playbook_topic(
        topic="Git Workflow",
        summary="Standard Git protocols.",
        rules=["Always pull main before branching.", "Squash commits before merge.", "Delete local branches after merge."]
    )
    
    p_updated = manager.get_playbook_topic("Git Workflow")
    assert len(p_updated["rules"]) == 3
    assert "Delete local branches after merge." in p_updated["rules"]
    assert p_updated["summary"] == "Standard Git protocols."
    
    # List topics
    all_playbooks = manager.list_playbook_topics()
    assert len(all_playbooks) == 1
    assert all_playbooks[0]["topic"] == "Git Workflow"

def test_fenced_context(temp_db, monkeypatch):
    """Verify that get_fenced_context returns XML wrapped logs and playbook guidelines."""
    # Point global DB_PATH in fenced_context to temp_db
    monkeypatch.setattr("core.memory.fenced_context.MemoryManager", lambda: MemoryManager(temp_db))
    
    manager = MemoryManager(temp_db)
    manager.add_memory("coding", "Always use container queries for responsive grid widgets.")
    manager.upsert_playbook_topic(
        topic="UI Layout Guidelines",
        summary="Rules for modern UI layouts.",
        rules=["Do not use absolute positioning when flexbox suffices."]
    )
    
    # Query without filter should retrieve everything
    xml_context = get_fenced_context(query=None)
    
    # Check structure
    assert "<recalled_context>" in xml_context
    assert "</recalled_context>" in xml_context
    assert "<memories>" in xml_context
    assert "Always use container queries for responsive grid widgets." in xml_context
    assert "UI Layout Guidelines" in xml_context
    assert "Do not use absolute positioning when flexbox suffices." in xml_context

def test_compactor_deterministic_fallback(temp_db):
    """Verify that MemoryCompactor compiles playbook topics/rules from memories using fallback."""
    compactor = MemoryCompactor(temp_db)
    manager = compactor.manager
    
    # Insert memories with actionable advice keywords
    manager.add_memory("investing", "We must verify quarterly earnings reports before scaling long options.")
    manager.add_memory("investing", "Always set stop-loss targets at 5% below dynamic support bands.")
    manager.add_memory("git_rules", "Developers should write meaningful commit messages.")
    
    # Run compaction
    updated = compactor.run_compaction()
    assert updated >= 2
    
    # Verify playbook was populated
    inv_playbook = manager.get_playbook_topic("Investing")
    assert inv_playbook is not None
    assert len(inv_playbook["rules"]) >= 2
    # Rules should be formatted (capitalized, ending in period)
    assert "We must verify quarterly earnings reports before scaling long options." in inv_playbook["rules"]
    assert "Always set stop-loss targets at 5% below dynamic support bands." in inv_playbook["rules"]
    
    git_playbook = manager.get_playbook_topic("Git_Rules")
    assert git_playbook is not None
    assert "Developers should write meaningful commit messages." in git_playbook["rules"]
    
    # Run compaction again to check reconciliation/deduplication
    updated_again = compactor.run_compaction()
    inv_playbook_2 = manager.get_playbook_topic("Investing")
    # Rule count should remain the same (deduplicated)
    assert len(inv_playbook_2["rules"]) == len(inv_playbook["rules"])

def test_wal_mode_and_db_settings(temp_db):
    """Verify WAL mode, synchronous, and busy_timeout settings are applied."""
    manager = MemoryManager(temp_db)
    conn = manager.get_connection()
    try:
        cursor = conn.cursor()
        # Check journal mode
        cursor.execute("PRAGMA journal_mode")
        journal_mode = cursor.fetchone()[0]
        assert journal_mode.lower() == "wal"
        
        # Check synchronous mode (NORMAL is 1, FULL is 2, OFF is 0)
        cursor.execute("PRAGMA synchronous")
        synch = cursor.fetchone()[0]
        assert synch == 1 or synch == "1" or str(synch).lower() == "normal"
        
        # Check busy_timeout
        cursor.execute("PRAGMA busy_timeout")
        timeout = cursor.fetchone()[0]
        assert timeout == 5000
    finally:
        conn.close()

def test_cosine_similarity():
    """Verify pure-Python cosine similarity calculations."""
    from core.memory.manager import cosine_similarity
    # Identical vectors -> 1.0
    v1 = [1.0, 2.0, 3.0]
    v2 = [1.0, 2.0, 3.0]
    assert abs(cosine_similarity(v1, v2) - 1.0) < 1e-6
    
    # Orthogonal vectors -> 0.0
    v3 = [1.0, 0.0]
    v4 = [0.0, 1.0]
    assert abs(cosine_similarity(v3, v4) - 0.0) < 1e-6
    
    # Opposite vectors -> -1.0
    v5 = [1.0, 1.0]
    v6 = [-1.0, -1.0]
    assert abs(cosine_similarity(v5, v6) - (-1.0)) < 1e-6
    
    # Empty or dimension-mismatched vectors
    assert cosine_similarity([], [1.0]) == 0.0
    assert cosine_similarity([1.0], [1.0, 2.0]) == 0.0

def test_semantic_search_fallback(temp_db, monkeypatch):
    """Verify that semantic_search_memories falls back to FTS5 when get_embedding returns None."""
    # Force get_embedding to return None
    monkeypatch.setattr("core.memory.manager.get_embedding", lambda text: None)
    
    manager = MemoryManager(temp_db)
    manager.add_memory("coding", "Writing Python test suites is highly recommended.")
    manager.add_memory("investing", "Diversify stock holdings to minimize risk.")
    
    # This should fall back to FTS5 search
    results = manager.semantic_search_memories(query="Writing", limit=5)
    assert len(results) == 1
    assert "Writing Python test suites" in results[0]["content"]

def test_semantic_search_success(temp_db, monkeypatch):
    """Verify semantic search with mock embeddings works correctly and ranks by similarity."""
    def mock_get_embedding(text: str):
        vec = [0.0] * 768
        if "python" in text.lower():
            vec[0] = 1.0
        elif "finance" in text.lower():
            vec[1] = 1.0
        return vec
        
    monkeypatch.setattr("core.memory.manager.get_embedding", mock_get_embedding)
    
    manager = MemoryManager(temp_db)
    id1 = manager.add_memory("coding", "I love coding in python language.")
    id2 = manager.add_memory("investing", "Finance is all about options trading.")
    
    results = manager.semantic_search_memories(query="python query", limit=5)
    
    assert len(results) == 2
    assert results[0]["id"] == id1
    assert results[0]["similarity"] > 0.9
    assert results[1]["id"] == id2
    assert abs(results[1]["similarity"] - 0.0) < 1e-6

def test_fenced_context_with_query_merging(temp_db, monkeypatch):
    """Verify that get_fenced_context merges and deduplicates FTS5 and vector search results."""
    def mock_get_embedding(text: str):
        vec = [0.0] * 768
        if "container" in text or "queries" in text:
            vec[0] = 1.0
        return vec
        
    monkeypatch.setattr("core.memory.manager.get_embedding", mock_get_embedding)
    monkeypatch.setattr("core.memory.fenced_context.MemoryManager", lambda: MemoryManager(temp_db))
    
    manager = MemoryManager(temp_db)
    manager.add_memory("coding", "Always use container queries for responsive grid widgets.")
    
    xml_context = get_fenced_context(query="queries")
    assert "<recalled_context>" in xml_context
    assert "Always use container queries for responsive grid widgets." in xml_context
    assert xml_context.count("Always use container queries") == 1

def test_llm_api_retry_backoff(monkeypatch):
    """Verify that _call_llm_api retries up to 3 times with exponential backoff on failure."""
    import urllib.error
    
    call_count = 0
    
    def mock_urlopen(req, timeout=None):
        nonlocal call_count
        call_count += 1
        raise urllib.error.URLError("Connection refused")
        
    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)
    
    sleep_calls = []
    monkeypatch.setattr("time.sleep", lambda seconds: sleep_calls.append(seconds))
    
    monkeypatch.setenv("GEMINI_API_KEY", "mock-gemini-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    
    from core.memory.compactor import _call_llm_api
    
    result = _call_llm_api("test prompt")
    
    assert result is None
    assert call_count == 4
    assert sleep_calls == [1, 2, 4]
