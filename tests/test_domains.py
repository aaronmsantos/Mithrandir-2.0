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
    assert "Louvre" in result_list.stdout


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
    # Test travel router choice '5' (Exit)
    result_travel = runner.invoke(app, ["run", "travel"], input="5\n")
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


def test_linkedin_parsing_and_sync(tmp_path, monkeypatch):
    """Test LinkedIn copy-pasted content parsing and Agent.MD coordinates syncing."""
    from domains.profile import ProfileDomain
    from unittest.mock import mock_open, patch
    
    profile = ProfileDomain()
    
    # Realistic copy-pasted LinkedIn profile text
    raw_content = """Aaron Miguel Santos
GTM Operations Lead at Fonoa

About
Experienced GTM Operations Lead. Skilled in Claude Code and HubSpot.

Experience
GTM Operations Lead
Fonoa
Jan 2024 - Present
Lead go-to-market operations, automation, and analytics.

Education
University of Washington
Bachelor of Science
2015 - 2019

Skills
Claude Code, Clay, Salesforce, HubSpot, Vercel, Base44, Slack, Python, Git

Languages
English, Spanish
"""
    
    # 1. Test fallback parser directly
    parsed = profile._parse_linkedin_content_fallback(raw_content)
    assert parsed["name"] == "Aaron Miguel Santos"
    assert parsed["headline"] == "GTM Operations Lead at Fonoa"
    assert any(e["company"] == "Fonoa" for e in parsed["experience"])
    assert "Python" in parsed["skills"]
    assert "English" in parsed["languages"]
    
    # 2. Test import_profile with is_linkedin=True
    # Mock sync_agent_coordinates to avoid modifying real Agent.MD
    with patch.object(ProfileDomain, "sync_agent_coordinates") as mock_sync:
        mem_id = profile.import_profile(raw_content=raw_content, is_linkedin=True)
        assert mem_id > 0
        mock_sync.assert_called_once()
        
        # Verify stored memory
        latest = profile.get_latest_profile()
        assert latest is not None
        assert latest["metadata"]["parsed"] is True
        assert latest["metadata"]["profile_data"]["name"] == "Aaron Miguel Santos"
        
    # 3. Test Agent.MD sync logic with mock file read/write
    mock_agent_content = """# 🔮 Mithrandir 2.0 Agent Guidelines ✨
## 🧭 Profile & Growth Coordinates ⚡️
*   **GTM Engineering Stack (Fonoa)**: Claude Code is the primary tool and work surface. Also utilizes Clay, Salesforce, HubSpot, Vercel, Base44, and Slack. Focuses on consistently improving mastery of IDEs and agentic coding platforms to maintain a position of strength at Fonoa.
"""
    
    m_open = mock_open(read_data=mock_agent_content)
    with patch("builtins.open", m_open), \
         patch("pathlib.Path.exists", return_value=True):
         
        success = profile.sync_agent_coordinates(parsed)
        assert success is True
        
        # Check what was written
        written_data = "".join(call.args[0] for call in m_open().write.call_args_list)
        assert "Python" in written_data
        assert "Git" in written_data


def test_travel_confirmation_parsing(tmp_path):
    """Test travel confirmation parsing, Bourdain enrichment, and directory scanning."""
    from domains.travel import TravelDomain
    
    travel = TravelDomain()
    
    # 1. Delta flight confirmation
    delta_text = """
    Delta Air Lines Flight DL 1284
    Confirmation: ABCDEF
    JFK to MIA
    June 15, 2026
    """
    parsed_flight = travel._parse_travel_confirmation_fallback(delta_text)
    assert parsed_flight["carrier"] == "Delta Airlines"
    assert parsed_flight["flight_number"] == "DL1284"
    assert parsed_flight["confirmation_code"] == "ABCDEF"
    assert parsed_flight["destination"] == "JFK to MIA"
    
    # 1b. Delta flight confirmation with "Confirmation Code:" and same-day/multi-day dates
    delta_text2 = """
    Delta Air Lines Flight
    Confirmation Code: GDR5CV
    Destination: Amsterdam, Netherlands
    Route: JFK to AMS
    Depart: June 7, 2026
    Arrive: June 8, 2026
    """
    parsed_flight2 = travel._parse_travel_confirmation_fallback(delta_text2)
    assert parsed_flight2["confirmation_code"] == "GDR5CV"
    assert parsed_flight2["start_date"] == "2026-06-07"
    assert parsed_flight2["end_date"] == "2026-06-08"

    # 1c. Single-day flight confirmation
    delta_text3 = """
    Delta Air Lines Flight
    Confirmation Code: GDN4HF
    Route: CDG to ATH
    Depart: June 15, 2026
    Arrive: June 15, 2026
    """
    parsed_flight3 = travel._parse_travel_confirmation_fallback(delta_text3)
    assert parsed_flight3["confirmation_code"] == "GDN4HF"
    assert parsed_flight3["start_date"] == "2026-06-15"
    assert parsed_flight3["end_date"] == "2026-06-15"
    
    # 2. IHG Hotel confirmation
    ihg_text = """
    Kimpton Fitzroy London
    Confirmation Number: 98765432
    Check-in: 2026-08-01
    Check-out: 2026-08-08
    """
    parsed_hotel = travel._parse_travel_confirmation_fallback(ihg_text)
    assert parsed_hotel["hotel_name"] == "Kimpton Fitzroy London"
    assert parsed_hotel["confirmation_code"] == "98765432"
    assert parsed_hotel["start_date"] == "2026-08-01"
    assert parsed_hotel["end_date"] == "2026-08-08"
    
    # 2b. Airbnb lodging confirmation
    airbnb_text = """
    Cozy Apartment Airbnb listing in Rome
    Confirmation Code: HMTR2D9
    Check-in: 2026-09-01
    Check-out: 2026-09-05
    """
    parsed_airbnb = travel._parse_travel_confirmation_fallback(airbnb_text)
    assert "Airbnb" in parsed_airbnb["hotel_name"]
    assert parsed_airbnb["confirmation_code"] == "HMTR2D9"
    assert parsed_airbnb["start_date"] == "2026-09-01"
    assert parsed_airbnb["end_date"] == "2026-09-05"
    
    # 3. Test Bourdain activity enricher fallback
    enriched = travel.bourdain_activity_enricher(["Sightseeing"], "Paris")
    assert "Sightseeing" in enriched
    assert len(enriched) > 1
    
    # 4. Test directory scanner
    incoming_dir = tmp_path / "incoming_travel"
    incoming_dir.mkdir()
    
    flight_file = incoming_dir / "flight.txt"
    flight_file.write_text(delta_text)
    
    hotel_file = incoming_dir / "hotel.txt"
    hotel_file.write_text(ihg_text)
    
    # Run scanner
    ids = travel.import_confirmation_files(incoming_dir)
    assert len(ids) == 2
    
    # Verify database storage
    trip1 = travel.manager.get_memory(ids[0])
    trip2 = travel.manager.get_memory(ids[1])
    assert trip1 is not None
    assert trip2 is not None
    
    # Verify files moved to processed/
    processed_dir = incoming_dir / "processed"
    assert processed_dir.exists()
    assert (processed_dir / "flight.txt").exists()
    assert (processed_dir / "hotel.txt").exists()
    assert not flight_file.exists()
    assert not hotel_file.exists()


def test_travel_ingestion_optimizations(tmp_path):
    """Test travel ingestion optimizations including HTML parsing, SkyTeam carriers, international dates, and audit callbacks."""
    from domains.travel import TravelDomain, HTMLTextExtractor
    
    # 1. Test HTMLTextExtractor visibility stripping
    html_content = """
    <html>
    <head>
        <style>body { color: blue; }</style>
        <script>alert("test");</script>
    </head>
    <body>
        <h1>Air France Flight Confirmation</h1>
        <p>Confirmation Code: <b>AF6789</b></p>
        <p>Depart: 15 June 2026</p>
        <p>Route: CDG to ATH</p>
    </body>
    </html>
    """
    extractor = HTMLTextExtractor()
    extractor.feed(html_content)
    plain_text = extractor.get_text()
    
    assert "style" not in plain_text.lower()
    assert "alert" not in plain_text.lower()
    assert "Air France Flight Confirmation" in plain_text
    assert "Confirmation Code: AF6789" in plain_text
    
    # 2. Test auto-extraction of HTML inside parse_travel_confirmation
    travel = TravelDomain()
    parsed = travel.parse_travel_confirmation(html_content)
    assert parsed["carrier"] == "Air France"
    assert parsed["flight_number"] == "AF6789"
    assert parsed["confirmation_code"] == "AF6789"
    assert parsed["start_date"] == "2026-06-15"
    assert parsed["destination"] == "CDG to ATH"
    
    # 3. Test international date parsing (DD-Month-YYYY)
    snippet_date2 = """
    KLM flight to Amsterdam
    Conf: KLM543
    15-Jun-2026
    """
    parsed2 = travel.parse_travel_confirmation(snippet_date2)
    assert parsed2["carrier"] == "KLM"
    assert parsed2["flight_number"] == "KLM543"
    assert parsed2["start_date"] == "2026-06-15"
    
    # 4. Test directory scanner with audit callback
    incoming_dir = tmp_path / "incoming_travel_opt"
    incoming_dir.mkdir()
    
    file_pass = incoming_dir / "pass.txt"
    file_pass.write_text("Delta Airlines flight DL 100, JFK to AMS, June 7, 2026, Confirmation: GDR5CV")
    
    file_block = incoming_dir / "block.txt"
    file_block.write_text("United Airlines flight UA 999, JFK to FRA, June 7, 2026, Confirmation: UAX999")
    
    # Define an audit callback that blocks United Airlines
    def audit_cb(content, metadata):
        # Allow Delta, block United
        return "Delta" in content
        
    ids = travel.import_confirmation_files(incoming_dir, audit_callback=audit_cb)
    
    # Only the passing file (Delta) should be processed and archived
    assert len(ids) == 1
    
    processed_dir = incoming_dir / "processed"
    assert (processed_dir / "pass.txt").exists()
    assert not (processed_dir / "block.txt").exists()
    assert file_block.exists()  # Kept in incoming directory
    
    # 5. Test native PDF ingestion with mock
    from unittest.mock import MagicMock, patch
    
    pdf_file = incoming_dir / "flight_doc.pdf"
    pdf_file.write_text("dummy binary pdf data")
    
    # Mock pypdf.PdfReader to simulate extracting text from PDF
    mock_reader = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Delta Airlines DL 100 JFK to AMS June 7, 2026 Confirmation: GDR5CV"
    mock_reader.pages = [mock_page]
    
    with patch("pypdf.PdfReader", return_value=mock_reader):
        pdf_id = travel.import_confirmation_file(pdf_file)
        assert pdf_id > 0
        
        # Verify the database entry has the parsed text details
        pdf_trip = travel.manager.get_memory(pdf_id)
        assert pdf_trip is not None
        assert pdf_trip["metadata"]["parsed_data"]["carrier"] == "Delta Airlines"
        assert pdf_trip["metadata"]["parsed_data"]["flight_number"] == "DL100"
        assert pdf_trip["metadata"]["parsed_data"]["confirmation_code"] == "GDR5CV"


def test_delta_mqd_status_and_calculator(setup_test_db, tmp_path):
    """Test YTD MQD status tracking, partner optimizer calculations, and their respective CLI commands."""
    import datetime
    travel = TravelDomain(setup_test_db)
    
    # 1. Test partner MQD calculation directly
    # Delta flight (revenue basis)
    delta_res = travel.calculate_partner_mqd("Delta Airlines", 3000, "X", 800)
    assert delta_res["mqds_earned"] == 720  # 90% of 800
    assert delta_res["mqd_ratio"] == pytest.approx(0.9, abs=0.01)
    assert not delta_res["is_optimized"]
    
    # Partner Business (Air France)
    af_res = travel.calculate_partner_mqd("Air France", 5000, "J", 1500)
    assert af_res["mqds_earned"] == 2000  # 40% of 5000
    assert af_res["mqd_ratio"] == pytest.approx(1.33, abs=0.01)
    assert af_res["is_optimized"]
    
    # 2. Seed some travel memories to test YTD summary
    year = datetime.date.today().year
    
    # Add a card headstart memory
    travel.manager.add_memory(
        category="travel",
        content=f"Card Headstart: Reserve\nDate: {year}-01-15\nMQDs: $2,500",
        metadata={
            "type": "card_headstart",
            "card_name": "Amex Reserve",
            "start_date": f"{year}-01-15",
            "end_date": f"{year}-01-15",
            "mqds": 2500
        }
    )
    
    # Add a flight memory
    travel.manager.add_memory(
        category="travel",
        content=f"Parsed Flight Travel Confirmation for JFK to AMS.\nDates: {year}-03-10 to {year}-03-15\nCarrier: Delta Airlines, Flight #: DL100\nMetrics: 3,500 Miles, $1,200 MQDs",
        metadata={
            "type": "travel_confirmation",
            "destination": "AMS",
            "start_date": f"{year}-03-10",
            "end_date": f"{year}-03-15",
            "parsed_data": {
                "type": "flight",
                "carrier": "Delta Airlines",
                "flight_number": "DL100",
                "mqds": 1200
            }
        }
    )
    
    # Fetch summary and check metrics
    summary = travel.get_ytd_mqd_summary(year=year)
    assert summary["total_mqds"] == 3700
    assert summary["breakdown"]["flights"] == 1200
    assert summary["breakdown"]["headstarts"] == 2500
    
    # Silver status target is 5000, so remaining should be 1300
    assert summary["tiers"]["Silver"]["needed"] == 1300
    assert summary["tiers"]["Silver"]["percentage"] == pytest.approx(74.0, abs=0.1)
    
    # 3. Test CLI travel status
    result_status = runner.invoke(app, ["travel", "status", "--year", str(year)])
    assert result_status.exit_code == 0
    assert "Delta Medallion Status Tracker" in result_status.stdout
    assert "$3,700" in result_status.stdout
    
    # 4. Test CLI travel optimize
    result_opt = runner.invoke(app, [
        "travel", "optimize",
        "--carrier", "KLM",
        "--distance", "6000",
        "--class", "W",
        "--price", "1200"
    ])
    assert result_opt.exit_code == 0
    assert "Flight MQD Optimization Report" in result_opt.stdout
    assert "Estimated MQDs Earned: $1,800" in result_opt.stdout
    assert "HIGHLY OPTIMIZED ROUTE" in result_opt.stdout
    
    # 5. Test CLI travel run loop for status and optimize
    result_loop_status = runner.invoke(app, ["run", "travel"], input="3\n")
    assert result_loop_status.exit_code == 0
    assert "Delta Medallion Status Tracker" in result_loop_status.stdout
    
    result_loop_opt = runner.invoke(app, ["run", "travel"], input="4\nKLM\n6000\nW\n1200\n")
    assert result_loop_opt.exit_code == 0
    assert "Flight MQD Optimization Report" in result_loop_opt.stdout

