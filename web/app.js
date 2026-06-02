document.addEventListener("DOMContentLoaded", () => {
    // --- Interactive State & References ---
    const terminalOutput = document.getElementById("terminal-output");
    const terminalInput = document.getElementById("terminal-cli");
    const spellButtons = document.querySelectorAll(".spell-btn");

    // --- Confluence Sliders References ---
    const sliders = {
        macroPivot: document.getElementById("macro-pivot"),
        macroCpi: document.getElementById("macro-cpi"),
        macroFlows: document.getElementById("macro-flows"),
        sentFintwit: document.getElementById("sent-fintwit"),
        sentCnbc: document.getElementById("sent-cnbc"),
        sentSkeptics: document.getElementById("sent-skeptics"),
        techSr: document.getElementById("tech-sr"),
        techMomentum: document.getElementById("tech-momentum"),
        techVolume: document.getElementById("tech-volume")
    };

    // --- Delta Pacing References ---
    const mqdInput = document.getElementById("current-mqd");

    // --- Core Initialization ---
    initConfluenceCalculator();
    initDeltaMedallionTracker();
    initTerminalSimulator();
    initGtmBlueprint();

    // ==========================================================================
    // 📈 CONFLUENCE CALCULATOR LOGIC
    // ==========================================================================
    function initConfluenceCalculator() {
        // Attach listener to every slider
        Object.keys(sliders).forEach(key => {
            const slider = sliders[key];
            const valDisplay = document.getElementById(slider.id + "-val");
            
            slider.addEventListener("input", () => {
                valDisplay.textContent = parseFloat(slider.value).toFixed(1);
                calculateConfluenceScore();
            });
        });
        
        // Run initial calculation
        calculateConfluenceScore();
    }

    function calculateConfluenceScore() {
        const macroVal = (
            parseFloat(sliders.macroPivot.value) +
            parseFloat(sliders.macroCpi.value) +
            parseFloat(sliders.macroFlows.value)
        ) / 3;

        const sentVal = (
            parseFloat(sliders.sentFintwit.value) +
            parseFloat(sliders.sentCnbc.value) +
            parseFloat(sliders.sentSkeptics.value)
        ) / 3;

        const techVal = (
            parseFloat(sliders.techSr.value) +
            parseFloat(sliders.techMomentum.value) +
            parseFloat(sliders.techVolume.value)
        ) / 3;

        const finalScore = (macroVal + sentVal + techVal) / 3;

        // Update UI displays
        document.getElementById("macro-avg").textContent = macroVal.toFixed(2);
        document.getElementById("sent-avg").textContent = sentVal.toFixed(2);
        document.getElementById("tech-avg").textContent = techVal.toFixed(2);
        document.getElementById("confluence-score").textContent = finalScore.toFixed(2);

        // Signal Tiers Logic
        const badge = document.getElementById("recommendation-badge");
        const descText = document.getElementById("recommendation-text");

        badge.className = "signal-badge"; // Reset classes

        if (finalScore >= 8.0) {
            badge.classList.add("BUY_STRENGTH");
            badge.textContent = "🚀 BUY STRENGTH";
            descText.textContent = "Heavy confluence aligned. Structural breakout supported by strong liquidity flows and high sentiment velocity.";
        } else if (finalScore >= 5.0) {
            badge.classList.add("WAIT");
            badge.textContent = "⏳ WAIT";
            descText.textContent = "Neutral range. Consolidation in progress. Monitor support line validations or volume divergence shifts.";
        } else if (finalScore >= 3.5) {
            badge.classList.add("BUY_SILENCE");
            badge.textContent = "🤫 BUY SILENCE";
            descText.textContent = "Skeptic flow and fear metrics dominant. Accumulate silently in thin order books while support holds.";
        } else {
            badge.classList.add("TRIM_STRENGTH");
            badge.textContent = "✂️ TRIM STRENGTH";
            descText.textContent = "Overextended structure with weakening momentum slopes. Sell into strength to protect operational capital.";
        }
    }

    // ==========================================================================
    // ✈️ DELTA MEDALLION PACING LOGIC
    // ==========================================================================
    function initDeltaMedallionTracker() {
        mqdInput.addEventListener("input", calculateDeltaPacing);
        calculateDeltaPacing();
    }

    function calculateDeltaPacing() {
        const currentMqd = parseFloat(mqdInput.value) || 0;
        
        // Tiers definitions
        const tiers = {
            silver: { name: "Silver Medallion", threshold: 6000, fill: document.querySelector(".silver-fill"), status: document.getElementById("silver-needed") },
            gold: { name: "Gold Medallion", threshold: 12000, fill: document.querySelector(".gold-fill"), status: document.getElementById("gold-needed") },
            platinum: { name: "Platinum Medallion", threshold: 15000, fill: document.querySelector(".platinum-fill"), status: document.getElementById("platinum-needed") },
            diamond: { name: "Diamond Medallion", threshold: 28000, fill: document.querySelector(".diamond-fill"), status: document.getElementById("diamond-needed") }
        };

        // Update Tier Progress Bars
        Object.keys(tiers).forEach(key => {
            const tier = tiers[key];
            const pct = Math.min(100, (currentMqd / tier.threshold) * 100);
            tier.fill.style.width = pct + "%";

            if (currentMqd >= tier.threshold) {
                tier.status.textContent = "Secured! 🎉";
                tier.status.className = "tier-status secured-label";
                tier.status.style.color = "var(--color-neon-emerald)";
            } else {
                const diff = tier.threshold - currentMqd;
                tier.status.textContent = diff.toLocaleString() + " USD needed";
                tier.status.className = "tier-status";
                tier.status.style.color = "var(--color-neon-red)";
            }
        });

        // Pacing Calculations relative to Dec 31, 2026
        const today = new Date();
        const endOfYear = new Date(2026, 11, 31);
        const diffTime = Math.max(0, endOfYear - today);
        const daysRemaining = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) || 1;

        document.getElementById("days-left").textContent = daysRemaining;

        const target = 28000;
        if (currentMqd >= target) {
            document.getElementById("pace-value").textContent = "SECURED 💎";
            document.getElementById("pace-value").style.color = "var(--color-neon-emerald)";
            document.getElementById("mqds-remaining").textContent = "0 USD";
        } else {
            const mqdsLeft = target - currentMqd;
            const pace = mqdsLeft / daysRemaining;
            
            document.getElementById("pace-value").textContent = "USD " + pace.toFixed(2);
            document.getElementById("pace-value").style.color = "var(--color-neon-yellow)";
                        document.getElementById("mqds-remaining").textContent = mqdsLeft.toLocaleString() + " USD";
        }
    }

    // ==========================================================================
    // 🔮 INTERACTIVE TERMINAL SIMULATOR
    // ==========================================================================
    function initTerminalSimulator() {
        terminalInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                const cmd = terminalInput.value.trim();
                if (cmd) {
                    executeCommand(cmd);
                    terminalInput.value = "";
                }
            }
        });

        spellButtons.forEach(btn => {
            btn.addEventListener("click", () => {
                const cmd = btn.getAttribute("data-cmd");
                executeCommand(cmd);
            });
        });
    }

    function writeTerminalLine(text, type = "output") {
        const line = document.createElement("div");
        line.className = "terminal-line " + type;
        line.innerHTML = text;
        terminalOutput.appendChild(line);
        terminalOutput.scrollTop = terminalOutput.scrollHeight;
    }

    function executeCommand(command) {
        writeTerminalLine(command, "command");
        
        // Normalize
        const cleanCmd = command.toLowerCase().trim();
        
        // Simulating processing delay
        setTimeout(() => {
            processCommand(cleanCmd);
        }, 150);
    }

    function processCommand(cmd) {
        if (cmd === "help") {
            writeTerminalLine(`
🔮 Mithrandir 2.0 Command Spells list:
  &bull; <span class='mono-text' style='color:var(--color-neon-cyan)'>doctor</span> &mdash; Run system environment diagnostics checks.
  &bull; <span class='mono-text' style='color:var(--color-neon-cyan)'>chat</span> &mdash; Open interactive chat with fenced SQLite memory context.
  &bull; <span class='mono-text' style='color:var(--color-neon-cyan)'>invest calculate</span> &mdash; Run confluence indicator weights over current state.
  &bull; <span class='mono-text' style='color:var(--color-neon-cyan)'>travel status</span> &mdash; View YTD MQD Delta status metrics and pacing stats.
  &bull; <span class='mono-text' style='color:var(--color-neon-cyan)'>portfolio status</span> &mdash; Brokerage cash balances and compound annual returns.
  &bull; <span class='mono-text' style='color:var(--color-neon-cyan)'>memory compact</span> &mdash; Reconcile short term logs into L2 playbook rules.
  &bull; <span class='mono-text' style='color:var(--color-neon-cyan)'>clear</span> &mdash; Clear terminal screen.
            `);
        } 
        else if (cmd === "doctor") {
            writeTerminalLine(`
⚡️ [INFO] Initiating environment checks...
⚡️ [INFO] Checking Database Path... OK (mithrandir_memory.db found)
⚡️ [INFO] SQLite Journal Mode... WAL (Write-Ahead Logging enabled)
⚡️ [INFO] SQLite Synchronous... NORMAL (Safe concurrent transactions)
⚡️ [INFO] busy_timeout... 5000ms (Congestion avoidance configured)
⚡️ [INFO] Cryptographic Key Status... MITHRANDIR_JOURNAL_KEY loaded (AES-256 Fernet active)
⚡️ [INFO] Vector Search Engine... cosine_similarity math loaded (Ready)
⚡️ [INFO] Diagnostic Harness Status... All systems fully green.
            `);
        } 
        else if (cmd === "chat") {
            const dateStr = new Date().toISOString();
            writeTerminalLine(`
💬 Opening interactive session...
[Injecting recalled context from FTS5 + Semantic Vector search]

&lt;recalled_context&gt;
  &lt;memories&gt;
    - Timestamp: 2026-05-31
      Content: Compounded portfolio statements ingested. Cash balances optimized.
    - Timestamp: 2026-05-24
      Content: Pads training session with Joe Sharpe. Focus on hook-cross-clinch transition flow.
  &lt;/memories&gt;
  &lt;playbook_rules&gt;
    - Always fly Delta airlines or SkyTeam partners.
    - Never trade on emotion; always calculate confluence score.
  &lt;/playbook_rules&gt;
&lt;/recalled_context&gt;

Mithrandir: "Spellbook loaded. Context synced. What project coordinate are we compiling today, Aaron?"
            `);
        } 
        else if (cmd.startsWith("invest")) {
            // Get values from UI
            const score = document.getElementById("confluence-score").textContent;
            const signal = document.getElementById("recommendation-badge").textContent.trim();
            const macro = document.getElementById("macro-avg").textContent;
            const sent = document.getElementById("sent-avg").textContent;
            const tech = document.getElementById("tech-avg").textContent;

            writeTerminalLine("\n" +
"⚡️ Executing Confluence Calculator...\n" +
"Evaluating sub-indicators:\n" +
"  - Macro Averages: " + macro + "\n" +
"  - Sentiment Averages: " + sent + "\n" +
"  - Technical Averages: " + tech + "\n\n" +
"Calculated Confluence Score: <span style='color:var(--color-neon-cyan);font-weight:700'>" + score + "</span>\n" +
"Signal Output: <span style='color:var(--color-neon-magenta);font-weight:700'>" + signal + "</span>\n" +
"Saving confluence calculation run state to database memories... OK (Memory ID logged).\n" +
"            ");
        } 
        else if (cmd.startsWith("travel")) {
            const currentMqdVal = parseFloat(mqdInput.value) || 0;
            const daysText = document.getElementById("days-left").textContent;
            const paceText = document.getElementById("pace-value").textContent;
            
            writeTerminalLine("\n" +
"✈️ YTD Delta Medallion Status (2026)\n" +
"  Total MQDs Secured: <span style='color:var(--color-neon-emerald);font-weight:700'>" + currentMqdVal.toLocaleString() + " USD</span>\n" +
"  Pacing Target (Diamond): 28,000 USD\n" +
"  Remaining Days: " + daysText + " days\n" +
"  Daily Pace Required: <span style='color:var(--color-neon-yellow);font-weight:700'>" + paceText + "</span>\n\n" +
"Ingested Travel Logs:\n" +
"  - DL1284 (JFK to MIA) &mdash; Ingested PDF &mdash; Secured: 1,200 USD MQDs\n" +
"  - KLM543 (JFK to AMS) &mdash; Ingested HTML &mdash; Secured: 980 USD MQDs\n" +
"  - IHG InterContinental (London) &mdash; Ingested Text &mdash; Secured: 1,500 USD MQDs\n" +
"            ");
        } 
        else if (cmd.startsWith("portfolio")) {
            writeTerminalLine(`
💼 Ingesting Apex Clearing statement coordinates...
Deduplicating broker statement records:
  - Active accounts: Brokerage Core #1324
  - Monthly coverage metrics: 100 percent complete
  - Deduplicated overlaps: 14 duplicated transactions pruned.

Operational Balances Status:
  - Cash Balance: 14,850.50 USD
  - Securities Market Value: 105,420.25 USD
  - Net Value: 120,270.75 USD
  - YTD Portfolio CAGR: <span style='color:var(--color-neon-emerald);font-weight:700'>18.42%</span>
  - Portfolio TWR Return: <span style='color:var(--color-neon-emerald);font-weight:700'>21.15%</span>
            `);
        } 
        else if (cmd.startsWith("memory compact")) {
            writeTerminalLine(`
⚡️ Launching Memory Compaction loop...
⚡️ Ingesting episodic database records (last 50 memories)...
⚡️ Accessing Gemini API for L2 Playbook compilation...
⚡️ Compacting raw descriptions... OK (Identified 4 coordinate updates)
⚡️ Reconciling playbook rules... Deduplicated matching nodes.
⚡️ Compaction cycle finished. Playbook updated successfully.
            `);
        } 
        else if (cmd === "clear") {
            terminalOutput.innerHTML = "";
            writeTerminalLine("Terminal history cleared.", "system-msg");
        } 
        else {
            writeTerminalLine("Command spelling '" + cmd + "' not found in grimoire. Type <span style='color:var(--color-neon-cyan)'>help</span> to list active spells.", "error");
        }
    }

    // ==========================================================================
    // 🔮 GTM AI OS BLUEPRINT LOGIC
    // ==========================================================================
    function initGtmBlueprint() {
        const tabs = document.querySelectorAll(".blueprint-tab");
        const visualContainer = document.getElementById("blueprint-visual");
        const detailsContainer = document.getElementById("blueprint-details");

        if (!tabs.length || !visualContainer || !detailsContainer) return;

        const data = {
            "tab-compounding": {
                title: "1. Compounding Loop",
                desc: "Durable memory pattern that compiles episodic, short-term logs into structural playbook rules through background compaction processes.",
                visual: "<div class=\"ascii-flow\">" +
                        "  [ Episodic Memory Logs ]\n" +
                        "             │\n" +
                        "             ▼ (SQLite memories table)\n" +
                        "  [ Compactor Pipeline ]\n" +
                        "             │\n" +
                        "             ▼ (LLM Distillation & Merge)\n" +
                        "  <span class=\"highlight\">[ L2 Playbook Guidelines ]</span>\n" +
                        "             │\n" +
                        "             ▼ (Durable Rule Injection)\n" +
                        "  [ Autonomous System State ]" +
                        "</div>",
                rules: [
                    "<strong>Episodic ingestion:</strong> Stores every chat, investment report, and travel log.",
                    "<strong>Compactor extraction:</strong> Aggregates short-term traces into long-term structures.",
                    "<strong>Rule deduplication:</strong> Minimizes cognitive overload by merging similar playbook rules."
                ]
            },
            "tab-sentinel": {
                title: "2. Cognitive Drift Sentinel",
                desc: "Real-time compliance auditor that intercepts memory updates and critiquing draft communication against the current playbook rules.",
                visual: "<div class=\"ascii-flow\">" +
                        "  [ Proposed Entry / Draft Email ]\n" +
                        "                 │\n" +
                        "                 ▼\n" +
                        "     <span class=\"highlight\">{ DriftSentinel Audit }</span>\n" +
                        "       /                   \\\n" +
                        "      ▼ Compliant           ▼ Drift Detected\n" +
                        "  [ Auto-Commit ]      <span class=\"accent\">[ Operator Alert ]</span>\n" +
                        "  [ Save to DB ]       [ Rewrite Suggestion ]" +
                        "</div>",
                rules: [
                    "<strong>Pre-commit validation:</strong> Halts writes if cognitive drift is detected.",
                    "<strong>Three-tier draft review:</strong> Verifies facts, adjusts voice, and checks playbook compliance.",
                    "<strong>Actionable rewrites:</strong> Provides direct sentence replacements in the CLI."
                ]
            },
            "tab-fenced": {
                title: "3. Fenced Context Recaller",
                desc: "Context synthesizer that performs hybrid search across keywords and vector spaces, dynamically compressing results within a token budget.",
                visual: "<div class=\"ascii-flow\">" +
                        "  [ Raw User Search Query ]\n" +
                        "             │\n" +
                        "     ┌───────┴───────┐\n" +
                        "     ▼ FTS5 Match    ▼ Vector Similarity (768-dim)\n" +
                        "  [ Key Words ]   [ Semantic Clusters ]\n" +
                        "     └───────┬───────┘\n" +
                        "             ▼\n" +
                        "  <span class=\"highlight\">[ Token Budget Pruning ]</span>\n" +
                        "             │\n" +
                        "             ▼ (Format as XML blocks)\n" +
                        "  [ Fenced LLM Context ]" +
                        "</div>",
                rules: [
                    "<strong>FTS5 Search:</strong> Fast indexes for precise keywords and codes.",
                    "<strong>Vector retrieval:</strong> Gemini text-embedding-004 cosine similarity.",
                    "<strong>Budget control:</strong> Keeps prompt context within the token limits."
                ]
            },
            "tab-isolation": {
                title: "4. Cryptographic Memory Isolation",
                desc: "Symmetric security boundary wrapping private logs in-memory using AES-256 Fernet ciphers, completely bypassing disk search catalogs.",
                visual: "<div class=\"ascii-flow\">" +
                        "  [ Plaintext Journal Entry ]\n" +
                        "             │\n" +
                        "             ▼\n" +
                        "  <span class=\"highlight\">{ AES-256 Fernet Encrypt }</span>\n" +
                        "             │\n" +
                        "     ┌───────┴───────┐\n" +
                        "     ▼ Disk Storage  ▼ Search Index\n" +
                        "  [ Encrypted DB ] <span class=\"accent\">[ BYPASSED / ISOLATED ]</span>\n" +
                        "  (Ciphertext)     (No plaintext leak)" +
                        "</div>",
                rules: [
                    "<strong>Fernet encryption:</strong> Base64 encoded AES key in local env files.",
                    "<strong>Index isolation:</strong> Symmetrically encrypted fields are kept out of FTS5 catalogs.",
                    "<strong>In-memory search:</strong> Runs decrypt-and-match loops strictly in-memory."
                ]
            },
            "tab-router": {
                title: "5. Model Router & Fallback Engine",
                desc: "Centralized execution layer that manages API responsiveness across multiple providers with a deterministic fallback pipeline.",
                visual: "<div class=\"ascii-flow\">" +
                        "    [ LLM Prompt Execution ]\n" +
                        "               │\n" +
                        "       ┌───────┼───────┐\n" +
                        "       ▼       ▼       ▼\n" +
                        "    Gemini  OpenAI  Anthropic\n" +
                        "       │       │       │\n" +
                        "       └───────┼───────┘\n" +
                        "               │ (Connection timeout)\n" +
                        "               ▼\n" +
                        "  <span class=\"accent\">[ Local Heuristic Fallback ]</span>\n" +
                        "  (Deterministic Regular Expressions)" +
                        "</div>",
                rules: [
                    "<strong>API validation:</strong> Checks key configurations before dispatching.",
                    "<strong>Urllib engine:</strong> Lightweight native HTTP layer.",
                    "<strong>Self-healing flow:</strong> Restores basic utility via heuristics when offline."
                ]
            }
        };

        function showPattern(tabId) {
            const pattern = data[tabId];
            if (!pattern) return;

            // Render Visual
            visualContainer.innerHTML = pattern.visual;

            // Render Details
            let rulesListHtml = "";
            pattern.rules.forEach(rule => {
                rulesListHtml += "<li>" + rule + "</li>";
            });

            detailsContainer.innerHTML = "<h3>" + pattern.title + "</h3>" +
                                         "<p>" + pattern.desc + "</p>" +
                                         "<ul>" + rulesListHtml + "</ul>";
        }

        tabs.forEach(tab => {
            tab.addEventListener("click", () => {
                tabs.forEach(t => t.classList.remove("active"));
                tab.classList.add("active");
                showPattern(tab.getAttribute("data-tab"));
            });
        });

        // Initialize first pattern
        showPattern("tab-compounding");
    }
});
