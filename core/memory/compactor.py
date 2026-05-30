import json
import logging
import os
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional
import typer

# Add project root directory to sys.path to allow execution of scripts directly
_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from core.memory.manager import MemoryManager, init_db

# --- Setup Logging ---
logger = logging.getLogger("mithrandir")
logger.setLevel(logging.INFO)

if not logger.handlers:
    stderr_handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter(
        "⚡️ [%(levelname)s] %(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    stderr_handler.setFormatter(formatter)
    logger.addHandler(stderr_handler)
    logger.propagate = False

# --- CLI App Setup ---
app = typer.Typer(help="🛡️ Mithrandir 2.0 Memory Compactor CLI ⚡️")

# --- LLM API Call Helper ---
def _call_llm_api(prompt: str) -> Optional[str]:
    """Call Gemini, OpenAI, or Anthropic REST APIs using urllib to avoid heavy SDK dependencies."""
    gemini_key = os.environ.get("GEMINI_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

    def is_valid(key: Optional[str]) -> bool:
        return bool(key and "placeholder" not in key.lower() and "your_" not in key.lower())

    # 1. Try Gemini
    if is_valid(gemini_key):
        logger.info("Accessing Gemini API for memory compilation...")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"}
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                return res_data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            logger.warning(f"Gemini API invocation failed: {e}")
            
    # 2. Try OpenAI
    if is_valid(openai_key):
        logger.info("Accessing OpenAI API for memory compilation...")
        url = "https://api.openai.com/v1/chat/completions"
        data = {
            "model": "gpt-4o-mini",
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that outputs JSON."},
                {"role": "user", "content": prompt}
            ]
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {openai_key}"
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                return res_data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"OpenAI API invocation failed: {e}")

    # 3. Try Anthropic
    if is_valid(anthropic_key):
        logger.info("Accessing Anthropic API for memory compilation...")
        url = "https://api.anthropic.com/v1/messages"
        data = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 2048,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": anthropic_key,
                "anthropic-version": "2023-06-01"
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                return res_data["content"][0]["text"]
        except Exception as e:
            logger.warning(f"Anthropic API invocation failed: {e}")

    logger.warning("No valid API Key detected or calls failed. Running in deterministic fallback mode.")
    return None

def _parse_llm_json(response_text: str) -> Optional[List[Dict[str, Any]]]:
    """Cleans and parses JSON list from the LLM content block."""
    text = response_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "topics" in data:
            return data["topics"]
        elif isinstance(data, list):
            return data
        return None
    except Exception as e:
        logger.error(f"Failed to decode JSON from LLM: {e}")
        return None

def _run_deterministic_fallback(memories: List[Dict[str, Any]], manager: MemoryManager) -> List[Dict[str, Any]]:
    """
    Deterministic rule-based fallback to extract playbooks and rules from memories
    when LLM access is not available.
    """
    logger.info("Executing deterministic fallback rules extraction...")
    extracted_topics = {}

    # Keywords that suggest a sentence contains an actionable guideline/rule
    actionable_keywords = [
        "must", "should", "always", "never", "ensure", "remember to", 
        "rule:", "insight:", "lesson:", "guideline:", "do not", "avoid"
    ]

    for m in memories:
        category = m["category"]
        content = m["content"]
        
        if not content or len(content.strip()) < 10:
            continue
            
        # Group by Category (representing topic)
        topic = category.strip().title()
        if topic == "Journal":
            topic = "General Operations"
            
        if topic not in extracted_topics:
            extracted_topics[topic] = {
                "summary": f"Compiled rules and insights extracted from category '{category}'.",
                "rules": set()
            }
            
        # Split sentences roughly on periods or newlines
        sentences = []
        for line in content.split("\n"):
            for chunk in line.split("."):
                clean_chunk = chunk.strip()
                if clean_chunk:
                    sentences.append(clean_chunk)

        for s in sentences:
            s_lower = s.lower()
            if any(kw in s_lower for kw in actionable_keywords) and 5 < len(s) < 150:
                rule = s[0].upper() + s[1:]
                if not rule.endswith("."):
                    rule += "."
                extracted_topics[topic]["rules"].add(rule)

    results = []
    for topic, data in extracted_topics.items():
        if data["rules"]:
            existing = manager.get_playbook_topic(topic)
            existing_rules = existing["rules"] if existing else []
            
            # Merge rules while avoiding duplicates (case-insensitive check)
            merged_rules = list(existing_rules)
            for rule in data["rules"]:
                normalized = rule.rstrip(".").lower()
                if not any(r.rstrip(".").lower() == normalized for r in merged_rules):
                    merged_rules.append(rule)
            
            summary = existing["summary"] if existing else data["summary"]
            
            results.append({
                "topic": topic,
                "summary": summary,
                "rules": merged_rules
            })
            
    return results

# --- Memory Compactor Class ---
class MemoryCompactor:
    """Manages the compounding loop: aggregates memories, extracts structured lessons/rules, and upserts them."""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.manager = MemoryManager(db_path)

    def run_compaction(self, limit: int = 50) -> int:
        """
        Runs a compaction cycle:
        1. Fetches recent memories.
        2. Compiles rule candidates (via LLM or deterministic fallback).
        3. Reconciles and upserts them into the playbook table.
        """
        logger.info(f"Executing compaction cycle over the last {limit} memories...")
        
        # 1. Fetch recent memories
        memories = self.manager.search_memories()[:limit]
        if not memories:
            logger.info("No memories found. Aborting compaction loop.")
            return 0
            
        existing_playbook = self.manager.list_playbook_topics()
        
        # Format memories and playbook for the LLM prompt
        memories_formatted = ""
        for m in memories:
            memories_formatted += f"- ID: {m['id']} | Category: {m['category']} | Timestamp: {m['timestamp']}\n  Content: {m['content']}\n"
            
        playbook_formatted = ""
        for p in existing_playbook:
            playbook_formatted += f"- Topic: {p['topic']}\n  Summary: {p['summary']}\n  Rules:\n"
            for r in p["rules"]:
                playbook_formatted += f"    * {r}\n"

        prompt = f"""You are the Mithrandir 2.0 Memory Compactor.
Below is a list of recent memories (recent interaction logs, journals, or events) and the existing playbook topics.
Your job is to analyze the recent memories, extract actionable rules, guidelines, and insights, and reconcile them with the existing playbook.

Recent memories:
{memories_formatted}

Existing Playbook:
{playbook_formatted}

Provide the updated playbook as a JSON object matching the following structure:
{{
  "topics": [
    {{
      "topic": "Topic Name (e.g. Git Best Practices, Investing Strategy)",
      "summary": "A concise, updated summary of the guidelines and lessons learned for this topic.",
      "rules": [
        "Rule 1 (concrete, actionable instruction)",
        "Rule 2 (concrete, actionable instruction)"
      ]
    }}
  ]
}}

Ensure that:
1. Rules are concrete, actionable guidelines (e.g., "Always use git stash before switching branches if there are uncommitted changes"). Avoid vague statements.
2. If a topic already exists in the Existing Playbook, reconcile the old rules with new insights. Do not lose useful old rules, but merge/improve/update them if there is new feedback.
3. Only output valid JSON. Do not include markdown code block wrapper or any other conversational text.
"""
        
        extracted_topics = None
        llm_response = _call_llm_api(prompt)
        if llm_response:
            extracted_topics = _parse_llm_json(llm_response)
            
        if not extracted_topics:
            extracted_topics = _run_deterministic_fallback(memories, self.manager)
            
        if not extracted_topics:
            logger.info("Compactor produced no actionable playbooks.")
            return 0
            
        # 3. Reconcile and upsert into the playbook table
        updated_count = 0
        for item in extracted_topics:
            topic = item.get("topic")
            summary = item.get("summary")
            rules = item.get("rules", [])
            
            if not topic or not summary:
                continue
                
            # Clean rules
            cleaned_rules = []
            seen = set()
            for r in rules:
                norm = r.strip().rstrip(".").lower()
                if norm and norm not in seen:
                    seen.add(norm)
                    cleaned_rules.append(r.strip())
                    
            self.manager.upsert_playbook_topic(topic, summary, cleaned_rules)
            updated_count += 1
            
        logger.info(f"Compaction cycle finished. Updated/Upserted {updated_count} playbook topics.")
        return updated_count

# --- Typer Commands ---
@app.command()
def run(
    limit: int = typer.Option(50, help="Number of recent memories to analyze."),
    db: Optional[str] = typer.Option(None, help="Custom database file path.")
):
    """Run Mithrandir 2.0 Memory Compaction loop."""
    db_path = Path(db) if db else None
    compactor = MemoryCompactor(db_path)
    try:
        updated = compactor.run_compaction(limit=limit)
        print(f"⚡️ Compactor completed successfully. Playbooks updated: {updated}")
    except Exception as e:
        print(f"❌ Error executing compactor: {e}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
