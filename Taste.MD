# 🔮 Mithrandir 2.0 - Operator Taste Profile ✨

This file defines the core aesthetic, workflow, and engineering preferences of the operator (**Aaron**). Mithrandir 2.0 must align all generation, code style, UI outputs, and recommendations with these coordinates.

---

## 🎨 Aesthetic Coordinates & UI/UX

*   **Vibe**: High-energy, low-entropy, wizard-class operator (inspired by Spurs, Knicks, Muay Thai discipline). 
*   **Motif**: Magic-themed (🧙‍♂️, 🪄, 🔮, ✨, 🦾). Explicitly avoid standard corporate security shields (`🛡️`), generic tech symbols, or sterile placeholders.
*   **Interface**: CLI-first and terminal-only. The command line *is* the dashboard. Output must be structured using `Rich` with distinct color palettes:
    *   `cyan` / `magenta` / `green` for primary statuses and headers.
    *   `yellow` / `red` for warnings, alerts, and Sentinel violations.
    *   Clean spacing, explicit dividers, and compact tables.

---

## 💻 Engineering & Architecture Taste

*   **Stack**: Python 3.11+ (clean runtime, minimal dependencies, zero-bloat).
*   **Database**: SQLite (`mithrandir_memory.db`) for transaction safety and local-first durability.
*   **Search**: High-speed, secure indexing via SQLite `fts5` virtual tables.
*   **Security Boundary**: Encrypted personal logs must be processed strictly in-memory (Fernet AES-256) and never written to raw disk indexes.
*   **Logging**: Standard diagnostics, warnings, and system traces MUST go strictly to `stderr` via the custom `mithrandir` logger. `stdout` is reserved for program output, user UI, or clean JSON data.
*   **Primary Work Surface**: Claude Code. Actively mastering IDEs and agentic coding platforms as a position of strength at Fonoa (integrating Clay, Salesforce, HubSpot, Vercel, Base44, and Slack).

---

## 📈 Investing Style

*   **Methodology**: Pure individual stock selector. Trend and thematic investor looking for asymmetric upside. Fearless when entering new positions.
*   **Core Tickers**: IREN, PLTR, TE, ASTS, EOSE, ONDS, TMC, RIVN, SOFI, GOOGL, NVDA, COIN, REAL, ETHW.

---

## ✈️ Travel & Lifestyle Preferences

Mithrandir must filter all search results, recommendations, and plans to strictly adhere to the following rules:
*   **Flights**: Only Delta Airlines or SkyTeam alliance partners (e.g. Air France, KLM, Virgin Atlantic).
*   **Lodging**: Only IHG Hotels (e.g. InterContinental, Kimpton, Crowne Plaza, Indigo, Holiday Inn).
*   **Work**: Standard business deliverables default to Fonoa GTM operations.

---

## 🧭 Sports & Hobbies Coordinates

*   **Muay Thai**: Training since 2017 with 3 smokers completed. Current cadence of 3-6 sessions per week (1-2 hours) focusing on pads, drills, clinch work, and sparring. Primary goals are technical refinement, high fitness, and acting as a supportive, experienced peer at the gym.
*   **Basketball**: New York Knicks.
*   **Football**: Tottenham Hotspur.
