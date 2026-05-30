# 🔮 Mithrandir 2.0

Mithrandir 2.0 is a minimal, low-entropy baseline operating chassis for CLI-first, SQLite-backed autonomous agents. Designed with a robust diagnostic harness, secure journal encryption foundation, and strict standard error logging principles. ⚡️

## 📦 Project Structure

```text
├── .env.example       # API keys and encryption key template
├── Agent.MD           # Architectural and runtime guidelines
├── README.md          # Project documentation (this file)
├── requirements.txt   # Core Python dependencies
└── core/
    └── harness.py     # Initialization, doctor checks, and logging setup
```

## 🚀 Getting Started

### 1. Installation
Clone/navigate to the project and install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Configuration
Copy the environment template:
```bash
cp .env.example .env
```
Open `.env` and fill in your API keys. Generate an encryption key for the journal:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 3. Run the Diagnostic Harness
Mithrandir 2.0 includes a CLI diagnostic doctor command to ensure your environment is fully operational:
```bash
python core/harness.py doctor
```

## 🛠️ Key Philosophy
- **Standard Error Logging:** System logs go to `stderr` only, keeping `stdout` clean for programmatic consumption.
- **SQLite Database Memory:** Local state, session history, and logs are tracked locally in a SQLite database.
- **Low Entropy:** No unnecessary abstractions. Keep the codebase clean, lean, and high-performance.
