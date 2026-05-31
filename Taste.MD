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

---

## ✈️ Travel & Lifestyle Preferences

Mithrandir must filter all search results, recommendations, and plans to strictly adhere to the following rules:
*   **Flights**: Only Delta Airlines or SkyTeam alliance partners (e.g. Air France, KLM, Virgin Atlantic).
*   **Lodging**: Only IHG Hotels (e.g. InterContinental, Kimpton, Crowne Plaza, Indigo, Holiday Inn).
*   **Work**: Standard business deliverables default to Fonoa operations.

---

## 🧭 Sports & Hobbies Coordinates

*   **Muay Thai**: Hard training, regular schedule, technique refinement, and discipline.
*   **Basketball**: New York Knicks.
*   **Football**: Tottenham Hotspur.
