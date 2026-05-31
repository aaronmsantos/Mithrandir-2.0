# 🔮 MITHRANDIR 2.0: THE SKATER WIZARD CONTROL PLANE 🪄

Mithrandir 2.0 is a local-first, low-entropy agent control plane and cognitive companion. It is a digital spellbook built from first principles for go-to-market operations, tactical asset allocation, and travel qualification hacking. 

By combining a durable SQLite memory engine (running in WAL mode) with FTS5 virtual tables, symmetric AES-256 Fernet encryption, and a CLI-first cockpit (powered by Typer and Rich), Mithrandir 2.0 acts as a compiler for personal growth and system orchestration.

```
                  _   _   _                     _ _     
  /\/\ (_) |_| |__  _ __ __ _ _ __   __| (_)_ __ 
 /    \| | __| '_ \| '__/ _` | '_ \ / _` | | '__|
/ /\/\ \ | |_| | | | | | (_| | | | | (_| | | |   
\/    \/_|\__|_| |_|_|  \__,_|_| |_|\__,_|_|_|   
                                                 
       🛹 RETRO ZEN meets NEON MAGIC 🔋
```

---

## ⚡️ SYSTEM ARCHITECTURE & DIRECTORY LAYOUT 💿

```text
├── .env.example            # Environment variables template
├── Agent.MD                # Primary agent guidelines, constraints, and coordinates
├── Taste.MD                # Aesthetic cues, skate videos, and reference tracks
├── README.md               # System documentation (this file)
├── main.py                 # Core CLI entry point (Typer subcommands router)
├── requirements.txt        # Python package dependencies
├── core/
│   ├── harness.py          # Diagnostics harness (doctor command) and logging setup
│   ├── prompt_optimizer.py # Text translator for Machine English conversion
│   ├── memory/
│   │   ├── manager.py      # SQLite operations, FTS5 index, and Fernet encryption
│   │   ├── compactor.py    # Memory compactor loop to extract L2 Playbook rules
│   │   ├── sentinel.py     # Cognitive drift monitor for pre-commit validation
│   │   └── fenced_context.py # Recalled context formatter wrapping data in XML tags
└── domains/
    ├── investing.py        # Confluence Trading Calculator
    ├── personal.py         # Encrypted Thought Journal
    ├── portfolio.py        # Brokerage Statement PDF Parser & Return Calculator (TWR/CAGR)
    ├── profile.py          # Professional Profile & Agent coordinate sync
    ├── projects.py         # AI Sprint Backlog tasks
    ├── travel.py           # Delta Flight / IHG Hotel confirmation parser & Diamond tracker
    └── work.py             # Deliverables tracker and GTM operations
```

---

## 🚀 SETUP & SPELLCASTING 🛹

### 1. Environment Activation & Dependencies
Activate your virtual workspace and pull down the python dependencies:
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
Open `.env` in your editor and configure your LLM provider API keys (Gemini, OpenAI, or Anthropic).

### 3. Generate Your Journal Encryption Key
The Personal Thought Journal requires a base64 symmetric Fernet key for encrypting local files. Generate one:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
Copy the generated string and set it to `MITHRANDIR_JOURNAL_KEY` in `.env`.

### 4. Run the Diagnostic Harness
Run the doctor diagnostic command to make sure your database and environments are fully configured:
```bash
.venv/bin/python main.py doctor
```

---

## 🛠️ CLI COMMAND REFERENCE 🪄

Execute all commands through the central entry point: `.venv/bin/python main.py`.

### 🩺 System & Diagnostics
*   **Run Diagnostics**: Perform instant environment health checks and database validations.
    ```bash
    .venv/bin/python main.py doctor
    ```

### 🤖 Chat & Context Optimization
*   **Chat Session**: Open an interactive chat with your fenced memory context automatically injected.
    ```bash
    .venv/bin/python main.py chat
    ```
*   **Machine English Translator**: Optimize raw developer ideas into clean, constraint-focused Machine English prompts.
    ```bash
    .venv/bin/python main.py prompt optimize --text "write code for scraping a page"
    ```

### 🧠 Memory Compactor & Exports
*   **Reconcile Playbooks**: Run the compactor loop to compile raw episodic logs into L2 playbook rules.
    ```bash
    .venv/bin/python main.py memory compact
    ```
*   **Export Memories**: Save all unencrypted memories to a timestamped JSON file.
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
*   **Calculate Score**: Scores a trade candidate (1 to 10 scale) across Macro, Sentiment, and Technical indicators:
    *   Score >= 8.0: BUY STRENGTH 🚀
    *   5.0 <= Score < 8.0: WAIT ⏳
    *   3.5 <= Score < 5.0: BUY SILENCE 🤫
    *   Score < 3.5: TRIM STRENGTH ✂️
    ```bash
    .venv/bin/python main.py invest calculate
    ```
*   **List Historical Runs**: View your history of confluence reports.
    ```bash
    .venv/bin/python main.py invest list
    ```

### 💼 Portfolio Statement Tracker
*   **Ingest Statements**: Recursively scan and parse Apex Clearing statement PDFs/CSVs.
    ```bash
    .venv/bin/python main.py portfolio ingest --path "/Users/aaronsantos/Downloads"
    ```
*   **Coverage Audit**: View statement monthly coverage across your brokerage accounts.
    ```bash
    .venv/bin/python main.py portfolio validate
    ```
*   **Balances Status**: Displays latest cash, securities, combined value (in USD), and top holdings.
    ```bash
    .venv/bin/python main.py portfolio status
    ```
*   **Monthly Performance Report**: Generates net gains, cash flows, and fees (in USD) for a target month.
    ```bash
    .venv/bin/python main.py portfolio report --period "2026-04"
    ```
*   **Performance Metrics**: Evaluates CAGR, YTD returns, and Time-Weighted Returns (TWR).
    ```bash
    .venv/bin/python main.py portfolio performance
    ```

### ✈️ Travel Manager (Delta & IHG Rules)
*   **Add Itinerary**: Log travel plans, activities, and packing lists.
    ```bash
    .venv/bin/python main.py travel add
    ```
*   **Import Confirmation Files**: Ingest flight/hotel receipts. Automatically enriches activities using Anthony Bourdain-inspired recommendations.
    ```bash
    .venv/bin/python main.py travel import "/path/to/incoming/confirmations"
    ```
*   **List Travel Logs**: Show all trips, flights, and lodgings.
    ```bash
    .venv/bin/python main.py travel list
    ```
*   **Status & Medallion Pacing**: Track YTD Delta MQD progress toward tiers (Silver, Gold, Platinum, Diamond at USD 28,000) and check your daily pacing.
    ```bash
    .venv/bin/python main.py travel status
    ```
*   **Partner Flight MQD Calculator**: Evaluate potential MQDs and MQD-to-Cost ratios (MQDs earned per USD spent) on partner airlines.
    ```bash
    .venv/bin/python main.py travel optimize
    ```

### 👔 Work & Projects
*   **Add Work Task**: Log weekly tasks and targets for GTM operations.
    ```bash
    .venv/bin/python main.py work add
    ```
*   **List Work Tasks**: View active and completed work tasks.
    ```bash
    .venv/bin/python main.py work list
    ```
*   **Add Project Task**: Log AI Sprint backlog tasks.
    ```bash
    .venv/bin/python main.py projects add
    ```
*   **List Project Tasks**: View backlog items and task complexity.
    ```bash
    .venv/bin/python main.py projects list
    ```

### 🧭 Profile & Coordinates
*   **Import experience**: Import resume MD files.
    ```bash
    .venv/bin/python main.py profile import --file "/path/to/resume.md"
    ```
*   **Import LinkedIn Profile**: Ingest copy-pasted LinkedIn text, parse metadata, and automatically sync your Fonoa stack parameters into `Agent.MD`.
    ```bash
    .venv/bin/python main.py profile import-linkedin
    ```
*   **Show Profile**: Display current professional experiences.
    ```bash
    .venv/bin/python main.py profile show
    ```

---

## 🧪 VERIFICATION & TESTING 🎸

Run the full automated test suite to verify database integrity, encryption isolation, and domain math calculations:
```bash
.venv/bin/python -m pytest
```

---

## 🧠 KEY DESIGN PRINCIPLES 🛹

1.  **Stderr-Only Diagnostics**: Standard error (stderr) is strictly for debugging, warnings, and log messages. Standard output (stdout) belongs entirely to program output, structured JSON, or user-facing Rich UI console tables.
2.  **Symmetric Encryption Isolation**: Personal journal records are encrypted on disk. Symmetrically encrypted fields are kept out of FTS5 search indexes, preventing cryptographic material from leaking onto disk search catalogs.
3.  **Local-First Concurrency**: SQLite with WAL mode is standard. This enables multiple background tools to read and write without blocking the CLI.
4.  **Zero Dependency Bloat**: We write clean, dependency-free Python modules. No heavy external frameworks are permitted unless they serve a core function.

---

## 🛰️ ROADMAP TO AUTONOMY 🔮

*   **Self-Learning**: Automated vector alignment that parses operator overrides ( DriftSentinel bypasses) and dynamically refines L2 playbook guidelines.
*   **Self-Healing**: Automated subprocess linting and pytest verification that catches code deprecation issues, generates code repairs, and commits them.
*   **Self-Optimization**: Sliding-window context compression inside `fenced_context.py` using semantic ranking to keep LLM prompts concise and cost-efficient.
