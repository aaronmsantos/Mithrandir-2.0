# 🔮 Mithrandir 2.0 ✨

Mithrandir 2.0 is a local-first, low-entropy operating system and agent control plane built from first principles. It serves as a compounding leverage engine, combining a robust CLI-first interface, a durable SQLite memory layer with full-text search, and encrypted personal logging.

The system aesthetics are a fusion of clean technical zen, retro video game UI (powered by `Rich`), and skater/hardcore punk culture vibes.

---

## 📦 System Architecture & Directory Layout

```text
├── .env.example            # Environment variables template
├── Agent.MD                # Primary agent guidelines, constraints, and coordinates
├── Taste.MD                # Aesthetic cues and reference tracks
├── README.md               # System documentation (this file)
├── main.py                 # Core CLI entry point (Typer subcommands router)
├── requirements.txt        # Core Python package dependencies
├── core/
│   ├── harness.py          # Environment diagnostics (doctor command) and logging setup
│   ├── prompt_optimizer.py # Text translator for Machine English conversion
│   ├── memory/
│   │   ├── manager.py      # Core SQLite operations, FTS5 virtual table, and Fernet encryption
│   │   ├── compactor.py    # Memory compactor loop to extract L2 Playbook rules
│   │   ├── sentinel.py     # Cognitive drift monitor for pre-commit validation
│   │   └── fenced_context.py # Recalled context formatter wrapping data in XML tags
└── domains/
    ├── investing.py        # Confluence Trading Calculator
    ├── personal.py         # Encrypted Thought Journal
    ├── portfolio.py        # Brokerage Statement PDF Parser & Return Calculator (TWR/CAGR)
    ├── profile.py          # Professional Profile & Agent coordinate sync
    ├── projects.py         # AI Sprint Backlog tasks
    ├── travel.py           # Delta Flight / IHG Hotel itinerary manager & Diamond Medallion tracker
    └── work.py             # Fonoa operations & weekly deliverables
```

---

## 🚀 Setup & Installation

### 1. Environment Activation & Dependencies
Create a virtual environment and install the required dependencies:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment Configuration
Copy the configuration template:
```bash
cp .env.example .env
```
Open `.env` and configure your API keys.

### 3. Generate Your Journal Encryption Key
The Personal Thought Journal requires a base64 symmetric Fernet key. Generate one by running:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
Copy the generated key and assign it to `MITHRANDIR_JOURNAL_KEY` in `.env`.

### 4. Run the Diagnostic Harness
Ensure your environment checks out and is fully operational:
```bash
.venv/bin/python main.py doctor
```

---

## 🛠️ Typer CLI Command Reference

Execute all commands through the central entry point: `.venv/bin/python main.py`.

### 🩺 System & Diagnostics
*   **Run Diagnostics**: Checks environment health, database integrity, and key configurations.
    ```bash
    .venv/bin/python main.py doctor
    ```

### 🤖 Chat & Context Optimization
*   **Chat**: Open an interactive chat session with fenced memory context automatically injected.
    ```bash
    .venv/bin/python main.py chat "How should I optimize my ASTS holdings?"
    ```
*   **Machine English Translator**: Optimize raw instructions into clean, constraint-focused Machine English prompts.
    ```bash
    .venv/bin/python main.py prompt optimize --text "write code for scraping a page"
    ```

### 🧠 Memory Compactor & Exports
*   **Reconcile Playbooks**: Runs the compactor loop to aggregate short-term logs into long-term playbook rules.
    ```bash
    .venv/bin/python main.py memory compact
    ```
*   **Export Memories**: Saves all unencrypted memories to a timestamped JSON file.
    ```bash
    .venv/bin/python main.py memory export
    ```

### 📓 Encrypted Personal Journal
*   **Write Entry**: Add an encrypted entry to the database. Text is encrypted with AES-256 before disk commit.
    ```bash
    .venv/bin/python main.py journal write
    ```
*   **List Entries**: View decrypted logs in-memory. Supports query filtering.
    ```bash
    .venv/bin/python main.py journal list -q "Muay Thai"
    ```
*   **Search**: Full-text search decrypted journal records.
    ```bash
    .venv/bin/python main.py journal search "currensy"
    ```

### 📈 Investing Confluence Calculator
*   **Calculate Score**: Scores a trade candidate (1 to 10 scale) across Macro, Sentiment, and Technical sub-indicators. Output maps to action tiers:
    *   Score >= 8.0: BUY STRENGTH 🚀
    *   5.0 <= Score < 8.0: WAIT ⏳
    *   3.5 <= Score < 5.0: BUY SILENCE 🤫
    *   Score < 3.5: TRIM STRENGTH ✂️
    ```bash
    .venv/bin/python main.py invest calculate
    ```
*   **List Historical Runs**:
    ```bash
    .venv/bin/python main.py invest list
    ```

### 💼 Portfolio Statement Tracker
*   **Ingest Statements**: Recursively scan and parse Apex Clearing statement PDFs.
    ```bash
    .venv/bin/python main.py portfolio ingest --path "/Users/aaronsantos/Downloads"
    ```
*   **Coverage Audit**: Shows statement monthly coverage matrix across brokerage accounts.
    ```bash
    .venv/bin/python main.py portfolio validate
    ```
*   **Balances Status**: Displays latest cash, securities, combined value, and top holdings.
    ```bash
    .venv/bin/python main.py portfolio status
    ```
*   **Monthly Performance Report**: Generates net gains, cash flows, and fees for a target month.
    ```bash
    .venv/bin/python main.py portfolio report --period "2026-04"
    ```
*   **Performance Metrics**: Evaluates CAGR, YTD 2026, and Time-Weighted Returns (TWR).
    ```bash
    .venv/bin/python main.py portfolio performance
    ```

### ✈️ Travel Manager (Delta & IHG Rules)
*   **Add Itinerary**: Log travel plans, activities, and packing lists.
    ```bash
    .venv/bin/python main.py travel add
    ```
*   **Import Confirmation Files**: Import flight/hotel receipts (Delta Airlines, IHG, Airbnb fallbacks). Enriches activities using Anthony Bourdain-inspired local recommendation logic.
    ```bash
    .venv/bin/python main.py travel import "/path/to/incoming/confirmations"
    ```
*   **List Travel Logs**:
    ```bash
    .venv/bin/python main.py travel list
    ```
*   **Status & Medallion Pacing**: Tracks YTD Delta MQD progress toward tiers (Silver, Gold, Platinum, Diamond at 28,000 USD) and calculates daily pacing.
    ```bash
    .venv/bin/python main.py travel status
    ```
*   **Partner Flight MQD Calculator**: Checks potential earnings and MQD-to-Cost ratios for partner flights (distance-based) vs Delta flights (revenue-based).
    ```bash
    .venv/bin/python main.py travel optimize
    ```

### 👔 Work & Projects
*   **Add Work Task**: Log weekly tasks and targets.
    ```bash
    .venv/bin/python main.py work add
    ```
*   **List Work Tasks**:
    ```bash
    .venv/bin/python main.py work list
    ```
*   **Add Project Task**: Log AI Sprint backlog tasks.
    ```bash
    .venv/bin/python main.py projects add
    ```
*   **List Project Tasks**:
    ```bash
    .venv/bin/python main.py projects list
    ```

### 🧭 Profile & Coordinates
*   **Import Experience**: Save professional resumes.
    ```bash
    .venv/bin/python main.py profile import --file "/path/to/resume.md"
    ```
*   **Import LinkedIn Profile**: Ingest LinkedIn text/HTML, parse metadata, and automatically sync Fonoa stack parameters into `Agent.MD`.
    ```bash
    .venv/bin/python main.py profile import-linkedin
    ```
*   **Show Profile**: Displays current profile history.
    ```bash
    .venv/bin/python main.py profile show
    ```

---

## 🧪 Verification & Testing

Execute the test suite to ensure all subsystems are functioning cleanly:
```bash
PYTHONPATH=. ./.venv/bin/python -m pytest
```

---

## 🧠 Key Principles

1.  **Stderr-Only Logging**: System logs and debugging logs must route strictly to `stderr`. `stdout` belongs strictly to program output, structured JSON, or user-facing Rich UI elements.
2.  **Durable Memory**: Memory records are stored permanently in local SQLite. Unencrypted data is indexed in SQLite `fts5` virtual tables for rapid semantic context recall.
3.  **Low Entropy & Zero Bloat**: Code is written with minimal external dependencies. No unnecessary abstractions or unused endpoints are introduced.
