import os
import pytest
from pathlib import Path
from typer.testing import CliRunner
from unittest.mock import MagicMock

# Ensure encryption key is defined for the tests
os.environ["MITHRANDIR_JOURNAL_KEY"] = "cw-Z35q6XG49tO08R1x5y4Q9W2vB7uL4pT2mB8eJ6g8="

from main import app
from core.memory.manager import MemoryManager
from core.memory.sentinel import DriftSentinel

runner = CliRunner()


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    """Auto-use fixture that redirects SQLite database path to a temp path for all tests."""
    test_db = tmp_path / "test_mithrandir_memory_sentinel.db"
    # Monkeypatch the DB_PATH global variables in the core modules
    monkeypatch.setattr("core.memory.manager.DB_PATH", test_db)
    monkeypatch.setattr("core.harness.DB_PATH", test_db)
    yield test_db


def test_sentinel_local_fallback_investing(setup_test_db):
    """Verify local fallback detects restricted keyword violations for Investing."""
    manager = MemoryManager(setup_test_db)
    # Seed L2 playbook with rules
    manager.upsert_playbook_topic(
        topic="Investing",
        summary="Investing guidelines.",
        rules=["Never trade on emotion.", "Always calculate confluence score."]
    )

    sentinel = DriftSentinel(setup_test_db)
    
    # 1. Violation: restricted keyword 'trade' (from "Never trade...") is present
    violations = sentinel.audit_entry(
        category="investing",
        content="I decided to trade without calculating since I was feeling emotional.",
        metadata={}
    )
    assert len(violations) > 0
    assert any("trade" in v["justification"].lower() for v in violations)

    # 2. Violation: required keyword 'calculate' is missing
    violations_missing = sentinel.audit_entry(
        category="investing",
        content="Decided to buy index funds.",
        metadata={}
    )
    assert len(violations_missing) > 0
    assert any("calculate" in v["justification"].lower() for v in violations_missing)


def test_sentinel_local_fallback_travel(setup_test_db):
    """Verify local fallback detects travel guidelines constraints."""
    manager = MemoryManager(setup_test_db)
    # Seed L2 playbook with travel rules
    manager.upsert_playbook_topic(
        topic="Travel",
        summary="Travel preferences.",
        rules=["Always fly Delta airlines.", "Never book random hotels."]
    )

    sentinel = DriftSentinel(setup_test_db)

    # 1. Violation: Always fly Delta, but Delta is missing
    violations = sentinel.audit_entry(
        category="travel",
        content="Booking flights via United Airlines.",
        metadata={}
    )
    assert len(violations) > 0
    assert any("fly" in v["justification"].lower() for v in violations)


def test_cli_journal_sentinel_abort(setup_test_db, monkeypatch):
    """Verify CLI journal add prompts and aborts if sentinel flags violations and user declines."""
    # Seed L2 playbook rules for journal (General Operations)
    manager = MemoryManager(setup_test_db)
    manager.upsert_playbook_topic(
        topic="General Operations",
        summary="General journal guidelines.",
        rules=["Never leak secrets.", "Always write positive thoughts."]
    )

    # Mock sentinel to return a violation
    mock_audit = MagicMock(return_value=[{
        "rule": "Always write positive thoughts.",
        "justification": "Content seems unhappy.",
        "severity": "WARNING"
    }])
    monkeypatch.setattr("core.memory.sentinel.DriftSentinel.audit_entry", mock_audit)

    # Invoke journal add, simulate user typing 'n' (decline)
    result = runner.invoke(
        app,
        ["journal", "add", "-c", "I am feeling extremely down today.", "-m", "2"],
        input="n\n"
    )
    assert result.exit_code == 1
    assert "Aborted journal write to prevent cognitive drift" in result.stdout

    # Verify no memory was stored
    memories = manager.search_memories(category="journal")
    assert len(memories) == 0


def test_cli_journal_sentinel_proceed(setup_test_db, monkeypatch):
    """Verify CLI journal add prompts and proceeds if sentinel flags violations and user approves."""
    manager = MemoryManager(setup_test_db)
    manager.upsert_playbook_topic(
        topic="General Operations",
        summary="General journal guidelines.",
        rules=["Never leak secrets.", "Always write positive thoughts."]
    )

    mock_audit = MagicMock(return_value=[{
        "rule": "Always write positive thoughts.",
        "justification": "Content seems unhappy.",
        "severity": "WARNING"
    }])
    monkeypatch.setattr("core.memory.sentinel.DriftSentinel.audit_entry", mock_audit)

    # Invoke journal add, simulate user typing 'y' (approve)
    result = runner.invoke(
        app,
        ["journal", "add", "-c", "I am feeling down today.", "-m", "3"],
        input="y\n"
    )
    assert result.exit_code == 0
    assert "safely encrypted and stored" in result.stdout

    # Verify memory was stored
    memories = manager.search_memories(category="journal")
    assert len(memories) == 1
    assert memories[0]["content"] == "I am feeling down today."


def test_cli_invest_sentinel_abort(setup_test_db, monkeypatch):
    """Verify CLI invest calculate prompts and aborts on sentinel violation when user declines."""
    manager = MemoryManager(setup_test_db)
    manager.upsert_playbook_topic(
        topic="Investing",
        summary="Investing guidelines.",
        rules=["Never trade on emotion."]
    )

    mock_audit = MagicMock(return_value=[{
        "rule": "Never trade on emotion.",
        "justification": "Mocked emotional trade violation.",
        "severity": "WARNING"
    }])
    monkeypatch.setattr("core.memory.sentinel.DriftSentinel.audit_entry", mock_audit)

    result = runner.invoke(app, [
        "invest", "calculate",
        "--tom-lee", "8.0", "--cpi", "7.0", "--flows", "9.0",
        "--fintwit", "5.0", "--cnbc", "4.0", "--skeptics", "6.0",
        "--sr", "8.0", "--momentum", "8.0", "--volume", "8.0"
    ], input="n\n")

    assert result.exit_code == 1
    assert "Aborted saving confluence report to prevent cognitive drift" in result.stdout
    assert len(manager.search_memories(category="investing")) == 0


def test_cli_travel_sentinel_abort(setup_test_db, monkeypatch):
    """Verify CLI travel add prompts and aborts on sentinel violation when user declines."""
    manager = MemoryManager(setup_test_db)
    manager.upsert_playbook_topic(
        topic="Travel",
        summary="Travel guidelines.",
        rules=["Always fly Delta."]
    )

    mock_audit = MagicMock(return_value=[{
        "rule": "Always fly Delta.",
        "justification": "Flying United.",
        "severity": "WARNING"
    }])
    monkeypatch.setattr("core.memory.sentinel.DriftSentinel.audit_entry", mock_audit)

    result = runner.invoke(app, [
        "travel", "add",
        "-d", "Paris",
        "--start", "2026-07-01",
        "--end", "2026-07-07",
        "-a", "Louvre",
        "-p", "Beret"
    ], input="n\n")

    assert result.exit_code == 1
    assert "Aborted saving itinerary to prevent cognitive drift" in result.stdout
    assert len(manager.search_memories(category="travel")) == 0
