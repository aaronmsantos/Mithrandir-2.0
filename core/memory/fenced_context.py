import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root directory to sys.path to allow execution of scripts directly
_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from core.memory.manager import MemoryManager

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

def escape_xml(text: str) -> str:
    """Escapes special characters for XML compliance."""
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
    )

def get_fenced_context(query: Optional[str] = None, category: Optional[str] = None) -> str:
    """
    Query the durable memory layer for relevant memories and playbook rules,
    then compile them into an XML-fenced block suitable for ingestion by the LLM.
    
    Args:
        query: Search string to filter memories and playbook topics.
        category: Category string to filter memories (e.g. 'journal', 'investing', etc.).
        
    Returns:
        XML string enclosed in <recalled_context> tags.
    """
    logger.info(f"Retrieving fenced context (query: {query}, category: {category})")
    
    manager = MemoryManager()
    
    # 1. Retrieve and filter memories
    memories = manager.search_memories(query=query, category=category)
    
    # 2. Retrieve and filter playbook topics
    all_playbooks = manager.list_playbook_topics()
    matched_playbooks = []
    
    if query:
        q_lower = query.lower()
        for p in all_playbooks:
            topic_match = q_lower in p["topic"].lower()
            summary_match = q_lower in p["summary"].lower()
            rules_match = any(q_lower in rule.lower() for rule in p["rules"])
            
            if topic_match or summary_match or rules_match:
                matched_playbooks.append(p)
    else:
        matched_playbooks = all_playbooks

    # 3. Construct XML string
    lines = ["<recalled_context>"]
    
    # Add memories section
    if memories:
        lines.append("  <memories>")
        for m in memories:
            m_id = m["id"]
            cat = escape_xml(m["category"])
            ts = escape_xml(m["timestamp"])
            content = escape_xml(m["content"])
            
            # Format metadata
            meta_attrs = ""
            if m["metadata"]:
                meta_str = ", ".join(f"{k}={v}" for k, v in m["metadata"].items())
                meta_attrs = f" metadata=\"{escape_xml(meta_str)}\""
                
            lines.append(f"    <memory id=\"{m_id}\" category=\"{cat}\" timestamp=\"{ts}\"{meta_attrs}>")
            lines.append(f"      {content}")
            lines.append("    </memory>")
        lines.append("  </memories>")
    else:
        lines.append("  <memories />")

    # Add playbook section
    if matched_playbooks:
        lines.append("  <playbook>")
        for p in matched_playbooks:
            topic = escape_xml(p["topic"])
            updated_at = escape_xml(p["updated_at"])
            summary = escape_xml(p["summary"])
            
            lines.append(f"    <topic name=\"{topic}\" updated_at=\"{updated_at}\">")
            lines.append(f"      <summary>{summary}</summary>")
            lines.append("      <rules>")
            for rule in p["rules"]:
                escaped_rule = escape_xml(rule)
                lines.append(f"        <rule>{escaped_rule}</rule>")
            lines.append("      </rules>")
            lines.append("    </topic>")
        lines.append("  </playbook>")
    else:
        lines.append("  <playbook />")
        
    lines.append("</recalled_context>")
    
    xml_context = "\n".join(lines)
    logger.info(f"Retrieved {len(memories)} memories and {len(matched_playbooks)} playbook topics.")
    return xml_context
