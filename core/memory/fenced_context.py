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

def get_fenced_context(
    query: Optional[str] = None,
    category: Optional[str] = None,
    token_budget: int = 4000,
    similarity_threshold: float = 0.0
) -> str:
    """
    Query the durable memory layer for relevant memories and playbook rules,
    then compile them into an XML-fenced block suitable for ingestion by the LLM.
    Prunes results dynamically based on a token budget and a similarity threshold.
    
    Args:
        query: Search string to filter memories and playbook topics.
        category: Category string to filter memories (e.g. 'journal', 'investing', etc.).
        token_budget: Maximum allowed estimated tokens (1 token approx 4 characters).
        similarity_threshold: Minimum similarity score for semantic search results.
        
    Returns:
        XML string enclosed in <recalled_context> tags.
    """
    logger.info(f"Retrieving fenced context (query: {query}, category: {category}, budget: {token_budget}, threshold: {similarity_threshold})")
    
    manager = MemoryManager()
    
    # 1. Retrieve and filter memories
    if query:
        # Fetch semantic search results (which include a 'similarity' score)
        vector_results = manager.semantic_search_memories(query=query, category=category, limit=5)
        # Filter vector results by similarity threshold
        vector_results = [m for m in vector_results if m.get("similarity", 0.0) >= similarity_threshold]
        
        # Fetch keyword search results
        fts_results = manager.search_memories(query=query, category=category)
        
        # Merge and deduplicate by memory ID
        seen_ids = set()
        memories = []
        for m in vector_results:
            if m["id"] not in seen_ids:
                seen_ids.add(m["id"])
                memories.append(m)
        for m in fts_results:
            if m["id"] not in seen_ids:
                seen_ids.add(m["id"])
                m["similarity"] = m.get("similarity", 0.8)  # Default high similarity for keyword matches
                memories.append(m)
        
        # Sort merged memories: primary by similarity score descending, secondary by timestamp/id descending
        memories.sort(key=lambda x: (x.get("similarity", 0.0), x.get("timestamp", ""), x.get("id", 0)), reverse=True)
    else:
        memories = manager.search_memories(query=None, category=category)
        memories.sort(key=lambda x: (x.get("timestamp", ""), x.get("id", 0)), reverse=True)
    
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

    # 3. Construct XML string incrementally with token budget pruning
    current_text = "<recalled_context>\n</recalled_context>"
    base_tokens = len(current_text) // 4
    used_tokens = base_tokens
    
    final_memories = []
    final_playbooks = []
    
    # Add memories that fit in the budget
    for m in memories:
        m_id = m["id"]
        cat = escape_xml(m["category"])
        ts = escape_xml(m["timestamp"])
        content = escape_xml(m["content"])
        
        meta_attrs = ""
        if m["metadata"]:
            meta_str = ", ".join(f"{k}={v}" for k, v in m["metadata"].items())
            meta_attrs = f" metadata=\"{escape_xml(meta_str)}\""
            
        memory_xml = (
            f"    <memory id=\"{m_id}\" category=\"{cat}\" timestamp=\"{ts}\"{meta_attrs}>\n"
            f"      {content}\n"
            f"    </memory>\n"
        )
        memory_tokens = len(memory_xml) // 4
        
        if used_tokens + memory_tokens <= token_budget:
            final_memories.append(memory_xml)
            used_tokens += memory_tokens
        else:
            logger.info(f"Memory ID {m_id} pruned due to token budget constraint.")
            
    # Add playbook topics that fit in the budget
    for p in matched_playbooks:
        topic = escape_xml(p["topic"])
        updated_at = escape_xml(p["updated_at"])
        summary = escape_xml(p["summary"])
        
        rules_xml = ""
        for rule in p["rules"]:
            escaped_rule = escape_xml(rule)
            rules_xml += f"        <rule>{escaped_rule}</rule>\n"
            
        playbook_xml = (
            f"    <topic name=\"{topic}\" updated_at=\"{updated_at}\">\n"
            f"      <summary>{summary}</summary>\n"
            f"      <rules>\n"
            f"{rules_xml}"
            f"      </rules>\n"
            f"    </topic>\n"
        )
        playbook_tokens = len(playbook_xml) // 4
        
        if used_tokens + playbook_tokens <= token_budget:
            final_playbooks.append(playbook_xml)
            used_tokens += playbook_tokens
        else:
            logger.info(f"Playbook topic '{p['topic']}' pruned due to token budget constraint.")

    # Construct final formatted XML context
    lines = ["<recalled_context>"]
    
    if final_memories:
        lines.append("  <memories>")
        for m_xml in final_memories:
            lines.append(m_xml.rstrip())
        lines.append("  </memories>")
    else:
        lines.append("  <memories />")
        
    if final_playbooks:
        lines.append("  <playbook>")
        for p_xml in final_playbooks:
            lines.append(p_xml.rstrip())
        lines.append("  </playbook>")
    else:
        lines.append("  <playbook />")
        
    lines.append("</recalled_context>")
    
    xml_context = "\n".join(lines)
    logger.info(f"Retrieved {len(final_memories)} memories and {len(final_playbooks)} playbook topics after budget-based pruning.")
    return xml_context
