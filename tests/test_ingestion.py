import os
import pytest
from pathlib import Path
from core.memory.manager import MemoryManager
from core.memory.ingestion_pipeline import GTM_Ingestion_Pipeline

@pytest.fixture
def test_db(tmp_path, monkeypatch):
    """Fixture to set up a temporary database path for testing."""
    db_file = tmp_path / "test_ingestion.db"
    monkeypatch.setattr("core.memory.manager.DB_PATH", db_file)
    return db_file

def test_csv_ingestion(test_db):
    """Verify that CSV ingestion maps headers and saves deal facts correctly without dollar signs."""
    csv_content = (
        "Opportunity,Status,Amount,Primary Contact\n"
        "Acme Corp,Proposal,150000 USD,John Doe\n"
        "Beta LLC,Discovery,75000,Jane Smith\n"
        "Gamma Inc,Negotiation,300000,Bob Vance\n"
    )
    
    csv_file = test_db.parent / "test_deals.csv"
    with open(csv_file, "w", encoding="utf-8") as f:
        f.write(csv_content)

    pipeline = GTM_Ingestion_Pipeline(test_db)
    memory_ids = pipeline.ingest_csv(csv_file)

    assert len(memory_ids) == 3

    # Check memories table
    manager = MemoryManager(test_db)
    memories = manager.search_memories(category="work")
    assert len(memories) == 3

    # Verify Acme Corp attributes
    acme = next(m for m in memories if "Acme Corp" in m["content"])
    assert acme["metadata"]["deal_name"] == "Acme Corp"
    assert acme["metadata"]["stage"] == "Proposal"
    assert acme["metadata"]["acv"] == "150000"
    assert acme["metadata"]["champion"] == "John Doe"

    # Verify dollar signs are cleaned (Beta LLC)
    beta = next(m for m in memories if "Beta LLC" in m["content"])
    assert beta["metadata"]["acv"] == "75000"
    assert "dollar" not in beta["content"]

def test_transcript_ingestion_llm(test_db, monkeypatch):
    """Verify that transcript ingestion works correctly when LLM returns valid JSON."""
    llm_json = {
        "deal_name": "Omega Co",
        "stage": "Negotiation",
        "acv": "250000 USD",
        "champion": "Sarah Connor",
        "next_steps": ["Draft contract", "Schedule final review"]
    }
    
    # Mock LLM API to return the valid JSON string
    import json
    monkeypatch.setattr("core.memory.compactor._call_llm_api", lambda prompt: json.dumps(llm_json))

    transcript_content = "This is a transcript from a sales meeting with Sarah Connor about Omega Co."
    transcript_file = test_db.parent / "transcript.txt"
    with open(transcript_file, "w", encoding="utf-8") as f:
        f.write(transcript_content)

    pipeline = GTM_Ingestion_Pipeline(test_db)
    memory_id = pipeline.ingest_transcript(transcript_file, deal_name="Omega Co")

    manager = MemoryManager(test_db)
    memory = manager.get_memory(memory_id)

    assert memory is not None
    assert memory["metadata"]["deal_name"] == "Omega Co"
    assert memory["metadata"]["stage"] == "Negotiation"
    assert memory["metadata"]["acv"] == "250000 USD"
    assert memory["metadata"]["champion"] == "Sarah Connor"
    assert "Draft contract" in memory["metadata"]["next_steps"]

def test_transcript_ingestion_local_fallback(test_db, monkeypatch):
    """Verify that transcript ingestion falls back to local heuristic parsing when LLM fails."""
    # Mock LLM API to fail (return None)
    monkeypatch.setattr("core.memory.compactor._call_llm_api", lambda prompt: None)

    transcript_content = (
        "Meeting with target customer Delta Ltd.\n"
        "Key Contact: Richard Hendricks\n"
        "Target contract value: 80000\n"
        "Let us map out the next steps:\n"
        "Next Steps: Prepare the presentation demo\n"
        "Next Steps: Send pricing list\n"
    )
    transcript_file = test_db.parent / "transcript_fallback.txt"
    with open(transcript_file, "w", encoding="utf-8") as f:
        f.write(transcript_content)

    pipeline = GTM_Ingestion_Pipeline(test_db)
    memory_id = pipeline.ingest_transcript(transcript_file, deal_name="Delta Ltd")

    manager = MemoryManager(test_db)
    memory = manager.get_memory(memory_id)

    assert memory is not None
    assert memory["metadata"]["deal_name"] == "Delta Ltd"
    assert memory["metadata"]["champion"] == "Richard Hendricks"
    assert memory["metadata"]["acv"] == "80000"
    assert "Prepare the presentation demo" in memory["metadata"]["next_steps"]
