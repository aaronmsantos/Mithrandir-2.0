import logging
import os
import sys
from pathlib import Path
from typing import Optional

# Setup pathing
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from core.memory.compactor import _call_llm_api

logger = logging.getLogger("mithrandir")

def translate_to_machine_english(raw_input: str) -> str:
    """
    Translates raw user input into Machine English:
    A structured, constraint-focused, instruction-dense format optimized for LLM attention.
    Uses LLM API if keys exist; otherwise, compiles using a robust local template.
    """
    if not raw_input or not raw_input.strip():
        return ""

    # System instruction for LLM-based translation
    system_prompt = """You are the Mithrandir 2.0 Machine English Optimizer.
Translate the user's raw instruction into Machine English.
Machine English is a highly structured, instruction-dense, declarative formatting style optimized for agent and subagent parsing.

Guidelines for Machine English:
1. Strip all conversational padding, pleasantries, and fluff.
2. Use clear markdown headers (e.g., [OBJECTIVE], [INPUTS], [CONSTRAINTS], [EXPECTED OUTPUT]).
3. Use imperative verbs (e.g., "Implement", "Extract", "Verify") and list all constraints explicitly as bullet points.
4. Separate code structures, data schemas, or file locations clearly.
5. Focus heavily on correctness, security boundaries, and logging rules.

Raw User Instruction:
"{raw_input}"

Provide only the optimized Machine English prompt in your response, with no conversational preamble or markdown code block fences unless the prompt itself requires them.
"""

    prompt = system_prompt.replace("{raw_input}", raw_input)
    
    # Try calling LLM first
    try:
        response = _call_llm_api(prompt)
        if response and response.strip():
            return response.strip()
    except Exception as e:
        logger.warning(f"Failed to use LLM for prompt optimization, falling back to local template: {e}")

    # Local Template Fallback
    logger.info("Using local template for Machine English compilation.")
    
    # Identify simple headers based on text heuristics
    lines = raw_input.split("\n")
    cleaned_lines = [l.strip() for l in lines if l.strip()]
    
    bullets = ""
    for line in cleaned_lines:
        if line.startswith("-") or line.startswith("*"):
            bullets += f"  {line}\n"
        else:
            bullets += f"  - {line}\n"

    local_compilation = f"""# [MACHINE ENGLISH OBJECTIVE]
Execute the following parsed operator request with high-fidelity performance.

## [CORE PROTOCOL]
- Focus strictly on modular, low-entropy execution blocks.
- Adhere to the Mithrandir 2.0 stderr-only logging policy (standard diagnostics to stderr, only data/outputs to stdout).
- Enforce strict input validation to prevent runtime failure modes.

## [INPUT / SPECIFICATIONS]
{bullets.rstrip()}

## [CONSTRAINTS & EXPECTATIONS]
- Maintain compatibility with Python 3.11+.
- Code modifications must be complete with no temporary placeholder comments.
- Test paths must run locally using pytest.
"""
    return local_compilation
