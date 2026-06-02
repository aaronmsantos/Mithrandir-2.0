# 🔮 GTM AI OS: Technical Architecture Blueprint (Mithrandir 2.0) 🪄

This document details the core architectural layers, patterns, and modules of Mithrandir 2.0. Built from first principles, this GTM AI OS is designed for local-first execution, cryptographic isolation, and low-entropy context recall.

---

## 💿 1. Relational SQLite Memory Engine

The persistence layer runs on SQLite, configured for high-concurrency, local-first operations. The memory database (`mithrandir_memory.db`) contains the following table schemas:

*   **`sessions`**: Tracks active agent interaction sessions.
*   **`memories`**: Stored episodic records across categories (e.g. chat, work, travel, investing, journal). Journal entries are symmetrically encrypted.
*   **`memories_fts`**: FTS5 virtual table for full-text keyword indexing. Crucially, it excludes journal entries to prevent cryptographic leakage.
*   **`memory_embeddings`**: Stores 768-dimension vectors mapped to memories.
*   **`playbook`**: Holds consolidated, structured rules and guidelines grouped by topic, compiled from episodic memories.
*   **`portfolio_statements` & `portfolio_positions`**: Canonical brokerage account status and investment holdings.

### Concurrency and Performance Coordinates:
*   **Journal Mode**: Write-Ahead Logging (WAL) enables multiple reader threads to read concurrent with writer threads.
*   **Synchronous Mode**: Set to NORMAL to balance write throughput with crash resilience, eliminating disk flush bottlenecks.
*   **Congestion Control**: A `busy_timeout` of 5000 milliseconds prevents database locking exceptions during parallel writes.

---

## 🔌 2. EventBus (Event-Driven Communication)

The EventBus provides decoupled, message-based communication between domains (investing, travel, work, portfolio) and the core memory engine. 

### Core Mechanics:
1.  **Publish/Subscribe Protocol**: Domain events (e.g., flight parsed, portfolio updated, trade calculated) publish message payloads to the central EventBus.
2.  **Decoupled Listeners**: The compactor loop and DriftSentinel subscribe to these events asynchronously.
3.  **Audit Pipelines**: When a document ingestion event is fired, the Sentinel automatically intercepts the data packet, performs checking, and logs compliance reports.

---

## 📦 3. Dependency Injection Container

Mithrandir uses a lightweight dependency injection container to manage stateful singletons (such as the database connection pool, LLM model routers, and encryption ciphers) without framework bloat.

### DI Advantages:
*   **Zero Global State**: Dependencies are registered into an IoC (Inversion of Control) container during initial boot.
*   **Test Isolation**: Allows unit tests to override live API model routers with deterministic mock harnesses.
*   **Explicit Wiring**: Every command instantiates from the container, ensuring that file paths, logging handlers, and secret keys are consistently injected.

---

## ⚡ 4. ModelRouter & Fallback Pipeline

The ModelRouter acts as a gateway to external LLMs (Gemini, OpenAI, Anthropic), prioritizing API responsiveness and availability.

```text
               +-----------------------+
               |  ModelRouter Request  |
               +-----------+-----------+
                           |
            +--------------v--------------+
            |  Validate API Key & Status  |
            +--------------+--------------+
                           |
            +--------------v--------------+
            | Primary API: Gemini Flash   |
            +--------------+--------------+
                           | (If offline)
            +--------------v--------------+
            | Secondary API: OpenAI Mini  |
            +--------------+--------------+
                           | (If offline)
            +--------------v--------------+
            | Tertiary API: Anthropic     |
            +--------------+--------------+
                           | (If offline)
            +--------------v--------------+
            | Local Deterministic Parser  |
            +-----------------------------+
```

### Routing Rules:
1.  **API Verification**: Before executing a request, the router validates the presence of non-placeholder keys (e.g. GEMINI_API_KEY).
2.  **Urllib REST Client**: Calls are executed via Python's native urllib package to eliminate heavy SDK packaging overhead.
3.  **Deterministic Fallback**: If all APIs are unreachable, the router invokes local regular expression/keyword heuristics to extract structural JSON coordinates.

---

## 🔑 5. Cryptographic Memory Isolation

Personal journal entries are protected via symmetric AES-256 Fernet encryption, enforcing a strict security boundary between private records and search catalogs.

*   **Encryption Process**: Text content is encrypted in-memory using `MITHRANDIR_JOURNAL_KEY` before it is written to the database.
*   **Decryption Process**: Entries are decrypted on-demand within volatile system memory for presentation.
*   **FTS5 Isolation**: Journal records are never loaded into the SQLite FTS5 table, ensuring no decrypted index remnants are written to the database file.
*   **Search Protocol**: Journal searching runs decrypt-and-match loops strictly in-memory.

---

## 🔍 6. Hybrid Index: FTS5 and Vector Search

Mithrandir implements a hybrid retrieval engine that merges keyword search with semantic understanding.

*   **FTS5 Keyword Match**: Excels at exact phrase, tag, or symbol lookups (e.g., specific stock tickers or flight numbers).
*   **768-Dimension Embeddings**: Text content is vectorized using the Gemini text-embedding-004 model.
*   **Cosine Similarity**: Pure Python arithmetic calculates alignment between query and memory vectors.
*   **Merged Ranking**: Search results are unified and sorted based on semantic score, falling back to chronological order for equal matches.
*   **Fenced Context Contextualizer**: Result clusters are formatted as XML-fenced inputs to keep prompt structures clean and prevent instruction injection.
