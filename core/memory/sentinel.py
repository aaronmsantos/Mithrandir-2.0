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

    def critique_draft(self, draft_text: str, deal_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Critiques a draft (e.g. email, proposal) against deal facts and playbook rules.
        Runs a 3-tier critique:
          1. Fact Verification (deal attributes matching memory)
          2. Voice & Altitude Register Alignment
          3. Playbook / Win-Formula Compliance
        Provides specific sentence rewrites.
        """
        # 1. Retrieve deal details from memories
        deal_memories = []
        if deal_name:
            deal_memories = self.manager.search_memories(query=deal_name, category="work")
            if not deal_memories:
                deal_memories = self.manager.semantic_search_memories(query=deal_name, category="work", limit=3)
        else:
            all_work = self.manager.search_memories(category="work")
            deal_memories = [m for m in all_work if m.get("metadata", {}).get("type") == "gtm_deal"]

        # Format deal context
        deal_context = ""
        if deal_memories:
            deal_context = "Relevant Deal Memories:\n"
            for m in deal_memories[:3]:
                deal_context += f"- Date: {m['timestamp']} | Content: {m['content']}\n"
        else:
            deal_context = "No specific deal details found in memories.\n"

        # 2. Retrieve playbook rules
        all_playbooks = self.manager.list_playbook_topics()
        relevant_rules = []
        for p in all_playbooks:
            topic_lower = p["topic"].lower()
            if any(kw in topic_lower for kw in ["sales", "work", "gtm", "critique", "general"]):
                relevant_rules.extend(p["rules"])
        
        # Fallback GTM/sales rules if database has none
        if not relevant_rules:
            relevant_rules = [
                "Always verify the champion's name is correct.",
                "Ensure ACV values are accurate and match records.",
                "Maintain professional altitude and voice.",
                "Address customer objections directly and clearly.",
                "State next steps explicitly at the end."
            ]

        rules_formatted = "\n".join([f"- {r}" for r in relevant_rules])

        # 3. Formulate LLM Prompt
        prompt = f"""You are the Mithrandir GTM Sentinel Draft Critique Agent.
Analyze the proposed draft text against the retrieved deal facts and playbook rules.

{deal_context}

Playbook Rules:
{rules_formatted}

Draft Text:
---
{draft_text}
---

Perform a 3-tier critique and output a JSON response containing:
1. Fact Verification: Check if the draft conflicts with the stored deal memories (e.g. incorrect ACV, wrong stage, wrong champion).
2. Voice & Altitude Register Alignment: Assess if the tone and vocabulary align with standard enterprise communication and rules.
3. Playbook Compliance: Check compliance with playbook rules (e.g. missing signature, unaddressed objections, missing next steps).
4. Specific Sentence Rewrites: Identify weak or non-compliant sentences and provide a direct before-and-after rewrite.

Output ONLY a JSON object matching this structure:
{{
  "fact_verification": [
    {{
      "finding": "Description of the fact match or mismatch",
      "severity": "WARNING/INFO/ERROR",
      "is_valid": true/false
    }}
  ],
  "voice_alignment": {{
    "assessment": "Assessment of tone, altitude, and voice register",
    "score": 100,
    "issues": ["Issue 1", "Issue 2"]
  }},
  "playbook_compliance": [
    {{
      "rule": "Rule text",
      "status": "COMPLIANT/NON_COMPLIANT",
      "details": "Explanation of compliance status"
    }}
  ],
  "sentence_rewrites": [
    {{
      "original": "Original sentence from the draft",
      "rewritten": "Improved and corrected sentence",
      "reason": "Why the rewrite is suggested"
    }}
  ]
}}

Ensure that you do not use any dollar sign characters (symbol for dollar) or em-dashes anywhere in your critique or in the output JSON. Return only the raw JSON, with no markdown code block wrappers or other conversational text.
"""
        from core.memory.compactor import _call_llm_api
        response = _call_llm_api(prompt)

        critique_result = None
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
                
                critique_result = json.loads(clean_text)
            except Exception as e:
                logger.error(f"Failed to parse LLM JSON response during draft critique: {e}. Raw: {response}")

        # Fallback local heuristic critique if LLM is offline/fails
        if not critique_result:
            logger.warning("Using local fallback heuristic for draft critique.")
            critique_result = self._run_local_fallback_critique(draft_text, deal_memories, relevant_rules)

        return critique_result

    def _run_local_fallback_critique(
        self, draft_text: str, deal_memories: List[Dict[str, Any]], rules: List[str]
    ) -> Dict[str, Any]:
        """Local heuristic draft critique if LLM is offline or fails."""
        facts_list = []
        issues = []
        compliance = []
        rewrites = []

        draft_lower = draft_text.lower()

        # 1. Fact checks
        for m in deal_memories:
            meta = m.get("metadata", {})
            if meta.get("type") == "gtm_deal":
                deal_name = meta.get("deal_name", "")
                champion = meta.get("champion", "")
                acv = meta.get("acv", "")

                # Check if champion is mentioned
                if champion and champion.lower() not in draft_lower:
                    facts_list.append({
                        "finding": f"Champion '{champion}' is not mentioned in the draft.",
                        "severity": "WARNING",
                        "is_valid": False
                    })
                else:
                    facts_list.append({
                        "finding": f"Champion '{champion}' fact check passed.",
                        "severity": "INFO",
                        "is_valid": True
                    })

                # Check if ACV is mentioned
                if acv and acv.lower() not in draft_lower:
                    facts_list.append({
                        "finding": f"ACV amount '{acv}' is not mentioned in the draft.",
                        "severity": "WARNING",
                        "is_valid": False
                    })

        if not facts_list:
            facts_list.append({
                "finding": "No historical deal memory facts were found to verify against.",
                "severity": "INFO",
                "is_valid": True
            })

        # 2. Voice & Tone
        weak_words = ["just checking", "sorry", "hope you are well", "apologize"]
        for word in weak_words:
            if word in draft_lower:
                issues.append(f"Contains passive/weak posture word: '{word}'")

        voice_score = 90 - (len(issues) * 10)
        voice_score = max(10, min(100, voice_score))

        # 3. Playbook checks
        for r in rules:
            r_lower = r.lower()
            if "always" in r_lower:
                words = r_lower.split("always")
                if len(words) > 1:
                    kw = words[1].strip().split()[0].rstrip(".,")
                    if len(kw) > 2 and kw not in draft_lower:
                        compliance.append({
                            "rule": r,
                            "status": "NON_COMPLIANT",
                            "details": f"Missing required aspect: '{kw}'."
                        })
                    else:
                        compliance.append({
                            "rule": r,
                            "status": "COMPLIANT",
                            "details": "Requirement verified."
                        })

        # 4. Rewrites
        if "just checking" in draft_lower:
            rewrites.append({
                "original": "I am just checking in to see if you had a chance to read it.",
                "rewritten": "Following up to confirm your feedback on the proposal.",
                "reason": "Avoid weak opening, state purpose directly."
            })

        if not compliance:
            compliance.append({
                "rule": "Maintain professional altitude.",
                "status": "COMPLIANT",
                "details": "Tone seems appropriate."
            })

        return {
            "fact_verification": facts_list,
            "voice_alignment": {
                "assessment": "Draft shows standard professional tone with minor areas of weak posture." if issues else "Draft shows good professional altitude and alignment.",
                "score": voice_score,
                "issues": issues
            },
            "playbook_compliance": compliance,
            "sentence_rewrites": rewrites
        }
