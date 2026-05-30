import logging
import os
import sqlite3
import sys
import uuid
from pathlib import Path
from typing import Dict, Optional

# Third-party dependencies
import typer
from cryptography.fernet import Fernet
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# --- Setup Typer and Rich ---
app = typer.Typer(help="🛡️ Mithrandir 2.0 Operator Harness CLI ⚡️")
console = Console()

# --- Logging Configuration (Stderr Only) ---
logger = logging.getLogger("mithrandir")
logger.setLevel(logging.INFO)
# Prevent propagation to the root logger to avoid double logging
logger.propagate = False

stderr_handler = logging.StreamHandler(sys.stderr)
formatter = logging.Formatter(
    "⚡️ [%(levelname)s] %(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
stderr_handler.setFormatter(formatter)
logger.addHandler(stderr_handler)

# --- Path Configurations ---
WORKSPACE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = WORKSPACE_DIR / ".env"
DB_PATH = WORKSPACE_DIR / "mithrandir_memory.db"


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


def init_db() -> sqlite3.Connection:
    """Initialize the SQLite memory/state database and session schema."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


@app.command()
def init_session(session_id: Optional[str] = None):
    """Initialize a new agent session in the SQLite database."""
    logger.info("Initializing database session...")
    
    # Ensure DB is created
    conn = init_db()
    cursor = conn.cursor()
    
    # Generate UUID if not provided
    s_id = session_id or str(uuid.uuid4())
    
    try:
        cursor.execute(
            "INSERT INTO sessions (session_id, status) VALUES (?, ?)",
            (s_id, "ACTIVE")
        )
        conn.commit()
        logger.info(f"Successfully recorded active session {s_id} in SQLite memory.")
        console.print(f"[bold green]Session Initialized Successfully:[/bold green] {s_id}")
    except sqlite3.IntegrityError:
        logger.warning(f"Session {s_id} already exists in database.")
        console.print(f"[bold yellow]Session already exists:[/bold yellow] {s_id}")
    finally:
        conn.close()


@app.command()
def doctor():
    """Run Mithrandir 2.0 system diagnostics checker."""
    logger.info("Running Mithrandir 2.0 system diagnostics...")
    env_vars = load_env()
    
    # Diagnostic Table
    table = Table(title="🛡️ Mithrandir 2.0 Diagnostics Report", show_header=True, header_style="bold magenta")
    table.add_column("Check Component", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details", style="white")

    # 1. Check Python Version
    py_version = sys.version_info
    py_ver_str = f"{py_version.major}.{py_version.minor}.{py_version.micro}"
    if py_version.major >= 3 and py_version.minor >= 8:
        table.add_row("Python Version", "[green]PASS[/green]", f"Running v{py_ver_str} (>= 3.8 required)")
    else:
        table.add_row("Python Version", "[red]FAIL[/red]", f"Running v{py_ver_str} (upgrade recommended)")

    # 2. Check SQLite Availability
    try:
        conn = sqlite3.connect(":memory:")
        sqlite_ver = conn.execute("select sqlite_version();").fetchone()[0]
        conn.close()
        table.add_row("SQLite Integration", "[green]PASS[/green]", f"v{sqlite_ver} active & responsive")
    except Exception as e:
        table.add_row("SQLite Integration", "[red]FAIL[/red]", f"Error: {str(e)}")

    # 3. Check .env Configuration Presence
    if ENV_PATH.exists():
        table.add_row("Env File (.env)", "[green]PASS[/green]", "Found config at project root")
    else:
        table.add_row("Env File (.env)", "[yellow]WARNING[/yellow]", "No .env file found; please copy .env.example")

    # 4. Check Model API Keys Status
    model_keys = ["GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
    for key in model_keys:
        val = env_vars.get(key) or os.environ.get(key)
        if not val:
            table.add_row(key, "[yellow]MISSING[/yellow]", "Key not defined in environment/.env")
        elif "your_" in val or "placeholder" in val:
            table.add_row(key, "[yellow]PLACEHOLDER[/yellow]", "Key is still set to placeholder template value")
        else:
            masked = val[:6] + "..." + val[-4:] if len(val) > 10 else "configured"
            table.add_row(key, "[green]CONFIGURED[/green]", f"Masked: {masked}")

    # 5. Check Journal Encryption Symmetric Key Validity
    journal_key = env_vars.get("MITHRANDIR_JOURNAL_KEY") or os.environ.get("MITHRANDIR_JOURNAL_KEY")
    if not journal_key:
        table.add_row("Journal Decrypt Key", "[red]FAIL[/red]", "MITHRANDIR_JOURNAL_KEY not set")
    elif "your_" in journal_key or "placeholder" in journal_key:
        table.add_row("Journal Decrypt Key", "[yellow]PLACEHOLDER[/yellow]", "Key is still the default template value")
    else:
        try:
            # Fernet key must be a 32 url-safe base64-encoded bytes key
            Fernet(journal_key.encode())
            table.add_row("Journal Decrypt Key", "[green]PASS[/green]", "Valid base64 symmetric Fernet key")
        except Exception as e:
            table.add_row("Journal Decrypt Key", "[red]INVALID[/red]", f"Error during key validation: {str(e)}")

    console.print(table)
    console.print(Panel(
        "[bold green]System check complete![/bold green] Keep maintaining clean state and secure journals. ⚡️",
        title="🛡️ Diagnostic Status",
        expand=False
    ))


if __name__ == "__main__":
    app()
