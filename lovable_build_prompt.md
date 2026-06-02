# 🔮 Mithrandir 2.0: Dashboard Application Build Prompt ✨

This document serves as the canonical builder prompt for visual development platforms (such as Lovable) to generate and modify the Mithrandir 2.0 Web Dashboard.

---

## 🎨 Theme and Styling Guidelines

*   **Vibe**: Retro zen meets electric neon wizardry. High contrast, clean terminal layout, Apple-style precision, and street culture.
*   **Colors**:
    *   **Background**: Deep space dark (HSL 230, 25%, 8% / `#0a0c14`).
    *   **Surface**: Semi-transparent dark glass with blur backdrop (HSLA 230, 22%, 14%, 0.65).
    *   **Cyan**: Neon cyan (HSL 180, 100%, 50% / `#00ffff`) for primary terminal prompts, links, and highlights.
    *   **Magenta**: Neon magenta (HSL 320, 100%, 50% / `#ff00f0`) for section borders, selection states, and accent text.
    *   **Emerald**: Neon emerald (HSL 145, 100%, 50% / `#00ff78`) for positive calculations and secured status badges.
    *   **Yellow**: Neon yellow (HSL 45, 100%, 50% / `#ffd700`) for pacing metrics and warnings.
    *   **Red**: Neon red (HSL 0, 100%, 60% / `#ff3333`) for alerts and needed values.

---

## 🧭 Navigation and Layout Structure

The layout is a single-page responsive dashboard containing:
1.  **Header**: Displaying the retro title logo and navigation links:
    *   CLI Simulator (`#terminal-section`)
    *   Confluence TAA (`#confluence-section`)
    *   Delta Medallion (`#delta-section`)
    *   GTM Blueprint (`#gtm-blueprint-section`)
    *   Operator Coords (`#coords-section`)
2.  **Hero Area**: Styled ASCII art logo displaying the tagline: "RETRO ZEN meets NEON MAGIC".

---

## 🔌 Core Dashboard Sections

### 1. CLI Simulator (`#terminal-section`)
*   **Purpose**: Simulates the Mithrandir 2.0 command-line cockpit.
*   **Features**:
    *   A scrolling terminal output block.
    *   An input field with prompt indicator.
    *   Quick-run spell buttons to execute commands instantly: `doctor`, `chat`, `invest calculate`, `travel status`, `portfolio status`, `memory compact`.
*   **Commands simulated**:
    *   `help`: Lists all valid commands.
    *   `doctor`: Displays SQLite persistence checks (WAL mode, busy_timeout 5000, encryption key status).
    *   `chat`: Displays XML-fenced memories and playbook context.
    *   `invest`: Displays Confluence results from active slider states.
    *   `travel`: Displays YTD Delta qualification pacing metrics.
    *   `portfolio`: Displays parsed statement balances and performance metrics.
    *   `memory compact`: Displays the compaction cycle status.

### 2. Confluence Trading Calculator (`#confluence-section`)
*   **Purpose**: Real-time scoring of individual stock investments.
*   **Controls**: Sliders (1.0 to 10.0 scale) for Macro, Sentiment, and Technical indicators.
*   **Outputs**:
    *   Group averages (Macro, Sentiment, Technical).
    *   Unified Confluence Score (arithmetic average of all indicators).
    *   Dynamic Recommendation Badge:
        *   Score >= 8.0: BUY STRENGTH (Emerald badge)
        *   5.0 <= Score < 8.0: WAIT (Yellow badge)
        *   3.5 <= Score < 5.0: BUY SILENCE (Cyan badge)
        *   Score < 3.5: TRIM STRENGTH (Red badge)

### 3. Delta Medallion Qualification Progress (`#delta-section`)
*   **Purpose**: Track flight pacing progress towards Silver, Gold, Platinum, and Diamond levels.
*   **Inputs**: Number input for Current YTD MQDs (representing financial values in USD).
*   **Outputs**:
    *   Four progress bars (Silver: 6,000 USD, Gold: 12,000 USD, Platinum: 15,000 USD, Diamond: 28,000 USD).
    *   Needed value calculation displaying remaining MQDs to secure each level.
    *   Daily pacing metric calculating required daily MQDs to reach Diamond level relative to December 31, 2026.

### 4. GTM AI OS Blueprint Section (`#gtm-blueprint-section`)
*   **Purpose**: Interactive presentation of the 5 core AI OS architectural patterns.
*   **Controls**: Clickable tabs representing the 5 patterns:
    1.  *Compounding Loop*: Episodic memories compacting into L2 Playbook rules.
    2.  *Drift Sentinel*: Pre-commit compliance validation and draft critiques.
    3.  *Fenced Context*: Hybrid keyword/vector search compression.
    4.  *Crypto Isolation*: AES-256 Fernet encryption isolating journal files from FTS5 catalogs.
    5.  *Model Router*: Multi-LLM failover to local deterministic heuristics.
*   **Interactive Panel**:
    *   **Visual Box**: Renders a styled ASCII sequence flow representing data routing.
    *   **Details Box**: Displays name, descriptive text, and bulleted engineering rules.

### 5. Operator Coordinates Section (`#coords-section`)
*   **Purpose**: Displays operator preferences.
*   *Muay Thai Coordinates*: Cadence, history, targets, and sparring values.
*   *Music Playlist Coordinates*: Preferred hip-hop, hardcore, and electronic artists.
*   *Sports coordinates*: NY Knicks and Tottenham Hotspur status.
