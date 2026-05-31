# 🔮 Mithrandir 2.0 Agent Guidelines ✨

You are operating inside **Mithrandir 2.0**—a local-first, low-entropy operating system and agent control plane built from first principles for Aaron. This workspace is a compounding leverage engine.

---

## 0) Prime Directive 🦾
*   **compounding Leverage**: Ship working outcomes fast with minimal moving parts. Everything you build must increase reusable infrastructure, strengthen local memory, and accelerate execution velocity. Emojis, high-energy vibes, and relentless execution are mandatory. 🎉⚡
*   **Machine English Optimization**: Automatically translate raw, informal human instructions into **Machine English** (a structured, constraint-focused, instruction-dense format) before dispatching tasks to agents or subagents to maximize prompt clarity and LLM parser execution quality.

---

## 1) Stack & Storage Defaults 📦
*   **Runtime**: Python 3.11+ (no heavy compilation, no complex containers, low-entropy).
*   **Database**: SQLite (`mithrandir_memory.db`) for transaction safety and local-first durability.
*   **Search**: SQLite `fts5` virtual table indexing for high-speed content lookup.
*   **CLI Interface**: Typer + Rich (no visual web dashboard bloat; the agent interface *is* the dashboard).
*   **Temporal Traceability**: Every memory entry logged in SQLite has a creation timestamp. Any database backup or exported JSON memory file MUST contain an ISO-8601 formatted timestamp in its filename (e.g. `memories_YYYY-MM-DDTHH-MM-SS.json`) and file header to ensure clean chronological tracking.

---

## 2) Durable Memory & Compounding Loop 🧠
*   **The Log Layer**: All turns, chats, and domain inputs write to the `memories` SQLite table under specific categories (`chat`, `investing`, `travel`, `work`, `projects`).
*   **Security Boundary**: Journal entries (`category = 'journal'`) are encrypted on-disk using AES-256 (Fernet) via `MITHRANDIR_JOURNAL_KEY` in `.env`. They are *never* indexed in FTS5 directly. For searches, decrypt in-memory.
*   **Fenced Context**: Load recalled logs/rules using `core/memory/fenced_context.py` and wrap them in XML fenced blocks (e.g., `<recalled_context>`) to avoid prompt corruption.
*   **Compacting Loop**: Run the compactor (`core/memory/compactor.py`) to digest raw short-term memory traces and upsert key learnings into the `playbook` table, creating a compounding feedback loop that makes Mithrandir smarter over time.

---

## 3) Domain Rules & Directives 🎸

### 📈 Investing (Confluence Framework)
Maintain and run the Confluence Calculator (`domains/investing.py`) which scores 9 sub-indicators (1-10):
1.  **Macro**: Tom Lee stance, CPI/liquidity trend, ETF flows.
2.  **Sentiment**: FinTwit velocity, CNBC amplitude, skeptic flows.
3.  **Technical**: S/R alignment, momentum slope, volume divergence.
*   **Suggestion Engine**:
    *   `Confluence >= 8.0`: 🚀 BUY STRENGTH
    *   `5.0 <= Confluence < 8.0`: ⏳ WAIT
    *   `3.5 <= Confluence < 5.0`: 🤫 BUY SILENCE
    *   `Confluence < 3.5`: ✂️ TRIM STRENGTH

### 📓 Personal (Thoughts & Feelings)
*   Must be stored encrypted via Fernet.
*   The decrypt key resides locally in `.env` and is never committed to git.
*   Provide secure search/list CLI tools to evaluate mood patterns without exposing raw text on disk.

### ✈️ Travel, 👔 Work, 📂 Projects
*   Keep models lightweight and stored as clean JSON metadata in SQLite.
*   Support logging and list queries.
*   **Work (Fonoa)**: Work deliverables, targets, and cadences default to Fonoa operations.
*   **Travel Rules**: Travel planning, itineraries, and recommendations MUST adhere to strict preferences:
    *   **Flights**: Only Delta Airlines or SkyTeam partners (Air France, KLM, Virgin Atlantic, etc.).
    *   **Lodging**: Only IHG Hotels (InterContinental, Kimpton, Crowne Plaza, Holiday Inn, etc.).

---

## 4) Stderr-Only Logging Directive 📯
*   `stdout` belongs strictly to program output, structured JSON, or user-facing Rich UI formatting.
*   All diagnostics, warnings, traces, and model notifications MUST log to `stderr` using the custom `mithrandir` logger.

---

## 5) CLI Commands 🛠️
Use the Typer app to run the suit:
*   `python main.py doctor` — Run diagnostics.
*   `python main.py journal write` / `list` / `search [query]` — Manage thoughts & feelings.
*   `python main.py invest calculate` / `list` — Confluence trading analysis.
*   `python main.py chat [message]` — Agent-first chat with fenced context injection.
*   `python main.py memory compact` — Compact raw logs into playbook rules.
*   `python main.py memory export` — Export database memories to a timestamped JSON file.
*   `python main.py prompt translate [--text "raw instructions"]` — Translate raw text to Machine English.
*   `python main.py travel/work/projects [list/add]` — Domain tracking.

---

## 6) Definition of Done 🏁
1.  Code must be complete, modular, and written to its final location. No `TODO` placeholders.
2.  All imports must handle sys.path additions correctly to allow direct module script runs.
3.  Verify changes by running `PYTHONPATH=. ./.venv/bin/pytest`.
4.  Diagnostics (`python main.py doctor`) must pass cleanly.

---
## 🧭 Profile & Growth Coordinates ⚡️

These coordinates define the customized cognitive layer of Mithrandir:
*   **GTM Engineering Stack (Fonoa)**: Claude Code is the primary tool and work surface. Also utilizes Clay, Salesforce, HubSpot, Vercel, Base44, and Slack. Focuses on consistently improving mastery of IDEs and agentic coding platforms to maintain a position of strength at Fonoa.
*   **Investing Tickers & Strategy**:
    *   **Tickers**: IREN, PLTR, TE, ASTS, EOSE, ONDS, TMC, RIVN, SOFI, GOOGL, NVDA, COIN, REAL, ETHW.
    *   **Style**: Pure individual stocks, trend/thematic investing, searching for asymmetric upside. Fearless when entering new positions.
*   **Muay Thai Practice**:
    *   **Cadence**: 3-6 times per week (1-2 hour sessions covering pads, drills, clinch, and sparring).
    *   **History & Goals**: Training since 2017 with 3 smokers completed. Focuses on fitness, technical refinement, and being an experienced, supportive gym member.
*   **Sports Teams**: Tottenham Hotspur (Football) and NY Knicks (Basketball). Keep in mind these are the operator's primary teams.

---

## 🔮 Next Upgrades (Mithrandir Roadmap)
1.  **[🔥 HIGHEST LEVERAGE] Cognitive Drift Sentinel**: Build an active audit agent that compares new CLI actions/trades/sprints against the L2 Playbook rules, raising alerts on guide violations.
2.  **Live Sentiment & News Ingestors**: Integrate simple feeds to automatically pre-populate Confluence metrics and Tottenham/Knicks updates.
3.  **GTM Git Connector**: Integrate Fonoa repository hooks to auto-update sprint tasks and perform local code reviews directly from the terminal.
