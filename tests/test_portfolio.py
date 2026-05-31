import os
import pytest
from pathlib import Path
from typer.testing import CliRunner
from datetime import datetime

# Ensure encryption key is defined for the tests
os.environ["MITHRANDIR_JOURNAL_KEY"] = "cw-Z35q6XG49tO08R1x5y4Q9W2vB7uL4pT2mB8eJ6g8="

from main import app
from core.memory.manager import MemoryManager
from domains.portfolio import PortfolioDomain

runner = CliRunner()


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    """Auto-use fixture that redirects SQLite database path to a temp path for all tests."""
    test_db = tmp_path / "test_mithrandir_memory_portfolio.db"
    # Monkeypatch the DB_PATH global variables in the core modules
    monkeypatch.setattr("core.memory.manager.DB_PATH", test_db)
    monkeypatch.setattr("core.harness.DB_PATH", test_db)
    yield test_db


def test_portfolio_database_operations(setup_test_db):
    """Tests MemoryManager portfolio DB schema insertion, retrieval, and deduplication."""
    manager = MemoryManager(setup_test_db)
    
    # Verify tables are initialized and empty
    stmts = manager.get_portfolio_statements()
    assert len(stmts) == 0

    # Add mock statement
    stmt1 = {
        "statement_id": "test_stmt_01",
        "account_key": "roth_ira",
        "account_number": "7SZ1953714",
        "period_start": "2026-01-01",
        "period_end": "2026-01-31",
        "opening_total_value": 48161.20,
        "closing_total_value": 55000.00,
        "opening_cash": 161.20,
        "closing_cash": 1000.00,
        "opening_securities": 48000.00,
        "closing_securities": 54000.00,
        "deposits": 1500.00,
        "withdrawals": 0.00,
        "dividends_interest": 25.50,
        "file_path": "/mock/path/stmt_jan.pdf",
        "is_canonical": 1
    }
    
    success = manager.add_portfolio_statement(stmt1)
    assert success is True
    
    # Query statements
    stmts = manager.get_portfolio_statements()
    assert len(stmts) == 1
    assert stmts[0]["statement_id"] == "test_stmt_01"
    assert stmts[0]["closing_total_value"] == 55000.00
    
    # Add mock position
    pos1 = {
        "statement_id": "test_stmt_01",
        "ticker": "PLTR",
        "quantity": 100.0,
        "price": 35.0,
        "market_value": 3500.0,
        "percent_of_account": 6.36
    }
    success_pos = manager.add_portfolio_position(pos1)
    assert success_pos is True
    
    # Query positions
    positions = manager.get_statement_positions("test_stmt_01")
    assert len(positions) == 1
    assert positions[0]["ticker"] == "PLTR"
    assert positions[0]["market_value"] == 3500.0


def test_duplicate_statement_resolution(setup_test_db):
    """Tests duplicate statement matching and marking resolution."""
    manager = MemoryManager(setup_test_db)
    
    stmt1 = {
        "statement_id": "stmt_orig",
        "account_key": "personal_brokerage",
        "account_number": "7SL3547517",
        "period_start": "2026-02-01",
        "period_end": "2026-02-28",
        "opening_total_value": 29246.92,
        "closing_total_value": 31000.00,
        "file_path": "/mock/path/stmt_feb.pdf",
        "is_canonical": 1
    }
    
    stmt2 = {
        "statement_id": "stmt_duplicate",
        "account_key": "personal_brokerage",
        "account_number": "7SL3547517",
        "period_start": "2026-02-01",
        "period_end": "2026-02-28",
        "opening_total_value": 29246.92,
        "closing_total_value": 31000.00,
        "file_path": "/mock/path/stmt_feb_dup.pdf",
        "is_canonical": 1
    }
    
    manager.add_portfolio_statement(stmt1)
    manager.add_portfolio_statement(stmt2)
    
    # Check that both are stored
    all_stmts = manager.get_portfolio_statements(canonical_only=False)
    assert len(all_stmts) == 2
    
    # Resolve and mark canonical
    manager.mark_duplicate_statements("personal_brokerage", "2026-02-28", "stmt_orig")
    
    # Query only canonical
    canonical = manager.get_portfolio_statements(canonical_only=True)
    assert len(canonical) == 1
    assert canonical[0]["statement_id"] == "stmt_orig"
    assert canonical[0]["is_canonical"] == 1
    
    # Query non-canonical
    non_canonical = [s for s in manager.get_portfolio_statements(canonical_only=False) if s["is_canonical"] == 0]
    assert len(non_canonical) == 1
    assert non_canonical[0]["statement_id"] == "stmt_duplicate"


def test_performance_calculations(setup_test_db):
    """Tests YTD, raw cumulative returns, and CAGR calculations."""
    portfolio = PortfolioDomain(setup_test_db)
    
    # Setup series of statements for Roth IRA
    statements = [
        # Inception May 31, 2025
        {
            "statement_id": "ira_01",
            "account_key": "roth_ira",
            "account_number": "7SZ1953714",
            "period_start": "2025-05-01",
            "period_end": "2025-05-31",
            "opening_total_value": 10000.0,
            "closing_total_value": 11000.0,
            "deposits": 1000.0,
            "withdrawals": 0.0,
            "file_path": "/mock/ira_01.pdf"
        },
        # Dec 31, 2025 (2026 anchor)
        {
            "statement_id": "ira_02",
            "account_key": "roth_ira",
            "account_number": "7SZ1953714",
            "period_start": "2025-12-01",
            "period_end": "2025-12-31",
            "opening_total_value": 11000.0,
            "closing_total_value": 12000.0,
            "deposits": 0.0,
            "withdrawals": 0.0,
            "file_path": "/mock/ira_02.pdf"
        },
        # Latest 2026 statement
        {
            "statement_id": "ira_03",
            "account_key": "roth_ira",
            "account_number": "7SZ1953714",
            "period_start": "2026-04-01",
            "period_end": "2026-04-30",
            "opening_total_value": 12000.0,
            "closing_total_value": 15000.0,
            "deposits": 2000.0,
            "withdrawals": 0.0,
            "file_path": "/mock/ira_03.pdf"
        }
    ]
    
    for s in statements:
        portfolio.manager.add_portfolio_statement(s)
        
    metrics = portfolio.calculate_performance_metrics()
    assert "roth_ira" in metrics
    
    m = metrics["roth_ira"]
    assert m["start_value"] == 10000.0
    assert m["end_value"] == 15000.0
    assert m["raw_cumulative_return"] == 0.50  # (15k - 10k) / 10k
    
    # 2026 YTD Return: Dec 31 close is 12,000, latest close is 15,000
    # YTD = (15k - 12k) / 12k = 25%
    assert m["ytd_2026"] == 0.25
    
    # CAGR since start: May 31, 2025 to April 30, 2026 is approx 11 months (0.916 years)
    # Expected CAGR > 40% (since value grew 50% in under a year)
    assert m["cagr"] > 0.40


def test_cli_subcommands(setup_test_db):
    """Tests the Typer CLI commands integration for portfolio."""
    # Test validate command output when empty
    result = runner.invoke(app, ["portfolio", "validate"])
    assert result.exit_code == 0
    assert "No statement data found" in result.output

    # Test status command when empty
    result_status = runner.invoke(app, ["portfolio", "status"])
    assert result_status.exit_code == 0
    assert "No statements found" in result_status.output
