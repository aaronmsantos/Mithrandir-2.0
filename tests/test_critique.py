import os
import pytest
from pathlib import Path
from core.memory.manager import MemoryManager
from core.memory.sentinel import DriftSentinel

@pytest.fixture
def test_db(tmp_path, monkeypatch):
    """Fixture to set up a temporary database path for testing."""
    db_file = tmp_path / "test_critique.db"
    monkeypatch.setattr("core.memory.manager.DB_PATH", db_file)
    return db_file

def test_critique_draft_llm(test_db, monkeypatch):
    """Verify draft critique parsing when LLM returns a structured JSON result."""
    llm_json = {
        "fact_verification": [
            {
                "finding": "ACV matches stored memory of 150000 USD",
                "severity": "INFO",
                "is_valid": True
            }
        ],
        "voice_alignment": {
            "assessment": "Draft shows high professional tone",
            "score": 95,
            "issues": []
        },
        "playbook_compliance": [
            {
                "rule": "Always verify champion",
                "status": "COMPLIANT",
                "details": "Champion John Doe is addressed"
            }
        ],
        "sentence_rewrites": []
    }
    
    import json
    monkeypatch.setattr("core.memory.compactor._call_llm_api", lambda prompt: json.dumps(llm_json))

    sentinel = DriftSentinel(test_db)
    result = sentinel.critique_draft(
        draft_text="Hello John Doe, following up on our proposal.",
        deal_name="Acme Corp"
    )

    assert result is not None
    assert result["voice_alignment"]["score"] == 95
    assert result["fact_verification"][0]["is_valid"] is True
    assert len(result["playbook_compliance"]) == 1

def test_critique_draft_fallback(test_db, monkeypatch):
    """Verify local fallback critique is executed and reports correct compliance and rewrites when offline."""
    monkeypatch.setattr("core.memory.compactor._call_llm_api", lambda prompt: None)

    manager = MemoryManager(test_db)
    
    # 1. Seed deal facts in memory
    manager.add_memory(
        category="work",
        content="GTM Deal: Beta LLC\nStage: Discovery\nACV: 75000 USD\nChampion: Jane Smith",
        metadata={
            "type": "gtm_deal",
            "deal_name": "Beta LLC",
            "stage": "Discovery",
            "acv": "75000",
            "champion": "Jane Smith"
        }
    )

    # 2. Seed playbook rules
    manager.upsert_playbook_topic(
        topic="GTM",
        summary="GTM guidelines",
        rules=["Always address Jane.", "Never use weak language."]
    )

    sentinel = DriftSentinel(test_db)
    
    # Critique draft that has "just checking" and lacks champion "Jane Smith"
    result = sentinel.critique_draft(
        draft_text="I am just checking in to see if you had a chance to read the document.",
        deal_name="Beta LLC"
    )

    # Verify fact check warning (Jane Smith is missing)
    facts = result["fact_verification"]
    assert any("Jane Smith" in f["finding"] and f["severity"] == "WARNING" for f in facts)

    # Verify tone / voice assessment has issues
    voice = result["voice_alignment"]
    assert voice["score"] < 90
    assert any("just checking" in issue for issue in voice["issues"])

    # Verify sentence rewrites has suggestions
    rewrites = result["sentence_rewrites"]
    assert len(rewrites) > 0
    assert "Following up" in rewrites[0]["rewritten"]
