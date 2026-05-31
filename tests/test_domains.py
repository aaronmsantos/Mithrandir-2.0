import os
import pytest
from pathlib import Path
from typer.testing import CliRunner

# Ensure encryption key is defined for the tests
os.environ["MITHRANDIR_JOURNAL_KEY"] = "cw-Z35q6XG49tO08R1x5y4Q9W2vB7uL4pT2mB8eJ6g8="

from main import app
from core.memory.manager import MemoryManager
from domains.personal import PersonalDomain
from domains.investing import InvestingDomain
from domains.travel import TravelDomain
from domains.work import WorkDomain
from domains.projects import ProjectsDomain

runner = CliRunner()


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    """Auto-use fixture that redirects SQLite database path to a temp path for all tests."""
    test_db = tmp_path / "test_mithrandir_memory_domains.db"
    # Monkeypatch the DB_PATH global variables in the core modules
    monkeypatch.setattr("core.memory.manager.DB_PATH", test_db)
    monkeypatch.setattr("core.harness.DB_PATH", test_db)
    yield test_db


# --- Domain Python Classes Tests ---

def test_personal_domain_direct(setup_test_db):
    """Test PersonalDomain journal additions, listings, and search directly."""
    personal = PersonalDomain(setup_test_db)
    
    # Add entry
    mem_id = personal.add_journal_entry("I feel optimistic about building Mithrandir 2.0 today.", 9)
    assert mem_id > 0
    
    # List entries
    entries = personal.list_journal_entries()
    assert len(entries) == 1
    assert entries[0]["content"] == "I feel optimistic about building Mithrandir 2.0 today."
    assert entries[0]["metadata"]["mood_score"] == 9
    
    # Search
    results = personal.list_journal_entries(query="optimistic")
    assert len(results) == 1
    
    results_empty = personal.list_journal_entries(query="pessimistic")
    assert len(results_empty) == 0


def test_investing_domain_direct(setup_test_db):
    """Test InvestingDomain confluence calculations, saves, and listings directly."""
    investing = InvestingDomain(setup_test_db)
    
    # 1. Test calculation logic for different scoring outcomes
    # High score: Buy strength
    report_high = investing.calculate_confluence(9, 9, 9, 8, 8, 8, 9, 9, 9)
    assert report_high["final_score"] == pytest.approx(8.67, abs=0.01)
    assert report_high["recommendation"] == "Buy strength"
    
    # Medium score: Wait
    report_med = investing.calculate_confluence(6, 6, 6, 6, 6, 6, 6, 6, 6)
    assert report_med["final_score"] == 6.0
    assert report_med["recommendation"] == "Wait"
    
    # Low-medium score: Buy silence
    report_low_med = investing.calculate_confluence(4, 4, 4, 4, 4, 4, 4, 4, 4)
    assert report_low_med["final_score"] == 4.0
    assert report_low_med["recommendation"] == "Buy silence"
    
    # Low score: Trim strength
    report_low = investing.calculate_confluence(2, 2, 2, 2, 2, 2, 2, 2, 2)
    assert report_low["final_score"] == 2.0
    assert report_low["recommendation"] == "Trim strength"
    
    # Save a report
    mem_id = investing.save_confluence_report(report_high)
    assert mem_id > 0
    
    # List reports
    reports = investing.list_confluence_reports()
    assert len(reports) == 1
    assert reports[0]["metadata"]["final_score"] == pytest.approx(8.67, abs=0.01)
    assert reports[0]["metadata"]["recommendation"] == "Buy strength"


def test_travel_domain_direct(setup_test_db):
    """Test TravelDomain itinerary additions and listings directly."""
    travel = TravelDomain(setup_test_db)
    mem_id = travel.add_itinerary(
        destination="Tokyo",
        start_date="2026-10-10",
        end_date="2026-10-20",
        activities=["Visit Sensoji", "Eat Sushi"],
        packing_list=["Passport", "Camera", "Adapter"]
    )
    assert mem_id > 0
    
    trips = travel.list_itineraries()
    assert len(trips) == 1
    assert trips[0]["metadata"]["destination"] == "Tokyo"
    assert "Visit Sensoji" in trips[0]["metadata"]["activities"]


def test_work_domain_direct(setup_test_db):
    """Test WorkDomain task additions and listings directly."""
    work = WorkDomain(setup_test_db)
    mem_id = work.add_task(
        task_name="Deploy Mithrandir 2.0",
        description="Verify all unit tests pass and release main CLI.",
        status="In Progress",
        due_date="2026-06-01",
        priority="High"
    )
    assert mem_id > 0
    
    tasks = work.list_tasks()
    assert len(tasks) == 1
    assert tasks[0]["metadata"]["task_name"] == "Deploy Mithrandir 2.0"
    assert tasks[0]["metadata"]["priority"] == "High"


def test_projects_domain_direct(setup_test_db):
    """Test ProjectsDomain backlog task additions and listings directly."""
    projects = ProjectsDomain(setup_test_db)
    mem_id = projects.add_project_task(
        project_name="Mithrandir Core",
        task_name="FTS5 Encryption Isolation",
        complexity="M",
        description="Verify journals are not stored in FTS search virtual table.",
        status="Backlog"
    )
    assert mem_id > 0
    
    tasks = projects.list_project_tasks()
    assert len(tasks) == 1
    assert tasks[0]["metadata"]["project_name"] == "Mithrandir Core"
    assert tasks[0]["metadata"]["complexity"] == "M"


# --- CLI Commands Integration Tests ---

def test_cli_journal_commands():
    """Test 'journal add/write', 'journal list', and 'journal search' CLI commands."""
    # Test add command with options
    result_add = runner.invoke(app, ["journal", "add", "-c", "Perfect weather today.", "-m", "10"])
    assert result_add.exit_code == 0
    assert "safely encrypted and stored" in result_add.stdout
    assert "In-Memory Plaintext Review" in result_add.stdout
    
    # Test list command
    result_list = runner.invoke(app, ["journal", "list"])
    assert result_list.exit_code == 0
    assert "Perfect weather today." in result_list.stdout
    assert "10/10" in result_list.stdout
    
    # Test search command
    result_search = runner.invoke(app, ["journal", "search", "weather"])
    assert result_search.exit_code == 0
    assert "Perfect weather today." in result_search.stdout
    
    # Test search command with no matches
    result_search_none = runner.invoke(app, ["journal", "search", "rainy"])
    assert result_search_none.exit_code == 0
    assert "No journal entries found matching criteria" in result_search_none.stdout


def test_cli_invest_commands():
    """Test 'invest calculate' and 'invest list' CLI commands."""
    # Test calculate with options
    result_calc = runner.invoke(app, [
        "invest", "calculate",
        "--tom-lee", "8.0", "--cpi", "7.0", "--flows", "9.0",
        "--fintwit", "5.0", "--cnbc", "4.0", "--skeptics", "6.0",
        "--sr", "8.0", "--momentum", "8.0", "--volume", "8.0"
    ])
    assert result_calc.exit_code == 0
    assert "Confluence Score" in result_calc.stdout
    assert "Macro Section" in result_calc.stdout
    
    # Test list
    result_list = runner.invoke(app, ["invest", "list"])
    assert result_list.exit_code == 0
    assert "8.00/10" in result_list.stdout  # Macro score is (8+7+9)/3 = 8


def test_cli_travel_commands():
    """Test 'travel add' and 'travel list' CLI commands."""
    result_add = runner.invoke(app, [
        "travel", "add",
        "-d", "Paris",
        "--start", "2026-07-01",
        "--end", "2026-07-07",
        "-a", "Visit Louvre, Climb Eiffel",
        "-p", "Beret, Euro Coins, Camera"
    ])
    assert result_add.exit_code == 0
    assert "Itinerary logged under travel" in result_add.stdout
    
    result_list = runner.invoke(app, ["travel", "list"])
    assert result_list.exit_code == 0
    assert "Paris" in result_list.stdout
    assert "Visit Louvre" in result_list.stdout


def test_cli_work_commands():
    """Test 'work add' and 'work list' CLI commands."""
    result_add = runner.invoke(app, [
        "work", "add",
        "-t", "Release Blog Post",
        "-d", "Write a summary of Mithrandir 2.0 release.",
        "-s", "Todo",
        "--due", "2026-06-05",
        "-p", "Medium"
    ])
    assert result_add.exit_code == 0
    assert "Work task logged" in result_add.stdout
    
    result_list = runner.invoke(app, ["work", "list"])
    assert result_list.exit_code == 0
    assert "Release Blog Post" in result_list.stdout


def test_cli_projects_commands():
    """Test 'projects add' and 'projects list' CLI commands."""
    result_add = runner.invoke(app, [
        "projects", "add",
        "-p", "Mithrandir Mobile",
        "-t", "Proto",
        "-c", "XL",
        "-d", "Build a quick Flutter dashboard wrapper.",
        "-s", "Proposed"
    ])
    assert result_add.exit_code == 0
    assert "AI sprint task logged" in result_add.stdout
    
    result_list = runner.invoke(app, ["projects", "list"])
    assert result_list.exit_code == 0
    assert "Mithrandir" in result_list.stdout
    assert "Mobile" in result_list.stdout
    assert "Proto" in result_list.stdout


def test_cli_memory_compact_commands():
    """Test 'memory compact' and standalone 'compact' CLI commands."""
    # First add a memory that can trigger compaction rule fallback
    manager = MemoryManager()
    manager.add_memory("coding", "Always use container queries for responsive layout elements.")
    
    result_compact1 = runner.invoke(app, ["memory", "compact"])
    assert result_compact1.exit_code == 0
    assert "Memory compaction completed successfully" in result_compact1.stdout
    
    result_compact2 = runner.invoke(app, ["compact"])
    assert result_compact2.exit_code == 0
    assert "Memory compaction completed successfully" in result_compact2.stdout


def test_cli_run_interactive_routers():
    """Test 'run' command interactive routes for travel, work, and projects."""
    # Test travel router choice '3' (Exit)
    result_travel = runner.invoke(app, ["run", "travel"], input="3\n")
    assert result_travel.exit_code == 0
    assert "Exited Travel loop." in result_travel.stdout

    # Test work router choice '3' (Exit)
    result_work = runner.invoke(app, ["run", "work"], input="3\n")
    assert result_work.exit_code == 0
    assert "Exited Work loop." in result_work.stdout

    # Test projects router choice '3' (Exit)
    result_projects = runner.invoke(app, ["run", "projects"], input="3\n")
    assert result_projects.exit_code == 0
    assert "Exited Projects loop." in result_projects.stdout

    # Test invalid domain
    result_invalid = runner.invoke(app, ["run", "invalid"])
    assert result_invalid.exit_code == 1
    assert "Unknown domain" in result_invalid.stdout


def test_cli_chat_command(monkeypatch):
    """Test 'chat' CLI command interactive input loop and log generation."""
    # Mock _call_llm_api to avoid network request and return a mocked response
    monkeypatch.setattr("main._call_llm_api", lambda x: "Recalled details: modern container queries are standard now.")
    
    # Run chat with simulated input: first query, then exit
    result = runner.invoke(app, ["chat"], input="How should I design responsive widgets?\nexit\n")
    assert result.exit_code == 0
    assert "Mithrandir Interactive Chat" in result.stdout
    assert "Recalled Fenced Context" in result.stdout
    assert "Recalled details: modern container queries" in result.stdout
    assert "Ending chat session. Bye!" in result.stdout
    
    # Check that the turn is stored in database as category 'chat'
    manager = MemoryManager()
    chat_memories = manager.search_memories(category="chat")
    assert len(chat_memories) == 1
    assert "How should I design responsive widgets?" in chat_memories[0]["content"]
    assert "Recalled details" in chat_memories[0]["content"]


def test_cli_prompt_commands(monkeypatch):
    """Test 'prompt translate' / 'prompt optimize' CLI commands."""
    monkeypatch.setattr("core.prompt_optimizer._call_llm_api", lambda x: "# MACHINE ENGLISH\nWrite simple python code.")
    
    result = runner.invoke(app, ["prompt", "translate", "--text", "Write a python script"])
    assert result.exit_code == 0
    assert "Machine English Translation" in result.stdout
    assert "Write simple python code" in result.stdout

    # Check database logging
    manager = MemoryManager()
    mems = manager.search_memories(category="prompt_optimization")
    assert len(mems) == 1
    assert "Write a python script" in mems[0]["content"]


def test_cli_memory_export_command(tmp_path, monkeypatch):
    """Test 'memory export' CLI command and check that files have clean timestamps."""
    # Temporarily override output workspace folder to test temp directory
    export_dir = tmp_path / "exports"
    monkeypatch.setattr("core.memory.manager.WORKSPACE_DIR", tmp_path)
    
    # Pre-populate some memories
    manager = MemoryManager()
    manager.add_memory("chat", "Hello world")
    
    result = runner.invoke(app, ["memory", "export"])
    assert result.exit_code == 0
    assert "Export complete!" in result.stdout
    
    # Verify that a file was written in target_dir
    written_files = list((tmp_path / "data" / "exports").glob("memories_*.json"))
    assert len(written_files) == 1
    # Filename contains timestamp
    assert "memories_" in written_files[0].name


def test_profile_domain_and_cli(tmp_path):
    """Test importing and showing professional history via ProfileDomain and CLI commands."""
    from domains.profile import ProfileDomain
    profile = ProfileDomain()
    
    # Test file setup
    profile_file = tmp_path / "profile_history.md"
    profile_file.write_text("Fonoa GTM Operations lead since 2024. Skilled in Claude Code.")
    
    # 1. Direct Python test
    mem_id = profile.import_profile(profile_file)
    assert mem_id > 0
    
    latest = profile.get_latest_profile()
    assert latest is not None
    assert latest["content"] == "Fonoa GTM Operations lead since 2024. Skilled in Claude Code."
    
    # 2. CLI Import test
    cli_file = tmp_path / "cli_history.md"
    cli_file.write_text("Skilled in Muay Thai and investing ASTS options.")
    
    result_import = runner.invoke(app, ["profile", "import", str(cli_file)])
    assert result_import.exit_code == 0
    assert "safely imported" in result_import.stdout
    
    # 3. CLI Show test
    result_show = runner.invoke(app, ["profile", "show"])
    assert result_show.exit_code == 0
    assert "Skilled in Muay Thai" in result_show.stdout
