import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Setup pathing
_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from core.memory.manager import MemoryManager
from core.memory.compactor import _call_llm_api

logger = logging.getLogger("mithrandir")

class DriftSentinel:
    """Audits proposed short-term memory inputs against long-term L2 playbook rules."""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.manager = MemoryManager(db_path)

    def audit_entry(self, category: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Audits a proposed memory entry against relevant L2 playbook rules.
        Returns a list of violation dictionaries if conflicts are detected.
        """
        metadata = metadata or {}
        
        # 1. Map category to L2 Playbook Topic
        # We title case the category to match default playbook topics
        topic = category.strip().title()
        if topic == "Journal":
            topic = "General Operations"
            
        playbook_topic = self.manager.get_playbook_topic(topic)
        if not playbook_topic or not playbook_topic.get("rules"):
            logger.info(f"No L2 playbook rules found for topic '{topic}'. Skipping sentinel audit.")
            return []

        rules = playbook_topic["rules"]
        
        # 2. Format rules for the audit
        rules_formatted = "\n".join([f"- {r}" for r in rules])
        
        prompt = f"""You are the Mithrandir Cognitive Drift Sentinel.
Your job is to audit a proposed memory entry against the established L2 Playbook rules for this topic.
Determine if the proposed entry contradicts, drifts from, or violates any of the rules.

Playbook Rules for topic '{topic}':
{rules_formatted}

Proposed Entry (Category: {category}):
Content: {content}
Metadata: {json.dumps(metadata)}

Evaluate if there is a conflict. Output your evaluation as a JSON object matching this structure:
{{
  "violations": [
    {{
      "rule": "The exact rule text that was violated",
      "justification": "Clear, concise explanation of how the proposed entry conflicts with the rule.",
      "severity": "WARNING"
    }}
  ]
}}
If there are no violations, output:
{{
  "violations": []
}}

Do not include any preamble, conversational text, or markdown code block wrappers. Output only raw JSON.
"""

        # 3. Call LLM
        response = _call_llm_api(prompt)
        if response:
            try:
                # Clean markdown blocks if present
                clean_text = response.strip()
                if clean_text.startswith("```"):
                    lines = clean_text.splitlines()
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    clean_text = "\n".join(lines).strip()
                
                data = json.loads(clean_text)
                violations = data.get("violations", [])
                if violations:
                    logger.warning(f"Sentinel audit detected {len(violations)} playbook rule violations!")
                return violations
            except Exception as e:
                logger.error(f"Sentinel failed to parse LLM JSON output: {e}. Raw: {response}")

        # 4. Local Heuristic Fallback Check (Offline Mode)
        return self._run_local_fallback_audit(content, rules)

    def _run_local_fallback_audit(self, content: str, rules: List[str]) -> List[Dict[str, Any]]:
        """
        Runs a fast local text-match audit if the LLM API is unavailable.
        Checks for negated guidelines or key rule terms.
        """
        logger.info("Executing local fallback keyword-matching audit.")
        violations = []
        content_lower = content.lower()

        for rule in rules:
            rule_lower = rule.lower()
            
            # Simple heuristic: If a rule says "never do X" or "always do X" and content contradicts it
            # e.g., Rule: "Never trade on emotion" -> proposed: "I made a panic buy"
            # We look for keywords like "never", "avoid", "always", "must"
            if "never" in rule_lower:
                # extract action keyword after never
                words = rule_lower.split("never")
                if len(words) > 1:
                    action_keyword = words[1].strip().split(" ")[0].rstrip(".,")
                    # If we find that action keyword in a sentence that implies we DID it
                    if len(action_keyword) > 2 and action_keyword in content_lower:
                        # Check if user says they did it (heuristic check)
                        violations.append({
                            "rule": rule,
                            "justification": f"Local check detected potential execution of restricted action '{action_keyword}'.",
                            "severity": "WARNING"
                        })
            
            elif "always" in rule_lower:
                words = rule_lower.split("always")
                if len(words) > 1:
                    action_keyword = words[1].strip().split(" ")[0].rstrip(".,")
                    if len(action_keyword) > 2 and action_keyword not in content_lower:
                        # If the rule says always do it, and it's not mentioned in the content
                        violations.append({
                            "rule": rule,
                            "justification": f"Local check did not find mention of required action: '{action_keyword}'.",
                            "severity": "WARNING"
                        })

        return violations
