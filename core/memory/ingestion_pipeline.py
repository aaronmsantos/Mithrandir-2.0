import csv
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from core.memory.manager import MemoryManager

logger = logging.getLogger("mithrandir")

class GTM_Ingestion_Pipeline:
    """Ingests GTM deals and meeting transcripts into the durable memory layer."""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.manager = MemoryManager(db_path)

    def ingest_csv(self, file_path: Path) -> List[int]:
        """
        Parses GTM deals from a CSV file, extracts key attributes,
        and saves each deal as a memory of category 'work'.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        memory_ids = []
        with open(file_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            
            # Map headers dynamically based on keywords
            deal_name_col = next((h for h in headers if any(k in h.lower() for k in ["deal name", "deal", "opportunity", "company"])), None)
            stage_col = next((h for h in headers if any(k in h.lower() for k in ["stage", "phase", "status", "state"])), None)
            acv_col = next((h for h in headers if any(k in h.lower() for k in ["acv", "annual contract value", "amount", "value", "revenue"])), None)
            champion_col = next((h for h in headers if any(k in h.lower() for k in ["champion", "contact", "key contact", "primary contact"])), None)

            # Fallback to first column for deal name if not found
            if not deal_name_col and headers:
                deal_name_col = headers[0]

            for row in reader:
                deal_name = row.get(deal_name_col, "").strip() if deal_name_col else "Unknown Deal"
                stage = row.get(stage_col, "").strip() if stage_col else "Unknown Stage"
                acv_raw = row.get(acv_col, "").strip() if acv_col else "0"
                champion = row.get(champion_col, "").strip() if champion_col else "Unknown Champion"

                # Clean ACV from any dollar symbol characters or other non-numeric symbols
                acv_clean = acv_raw.replace("USD", "").replace("usd", "").replace(",", "").strip()
                acv_clean = acv_clean.replace(chr(36), "").strip()

                content = (
                    f"GTM Deal: {deal_name}\n"
                    f"Stage: {stage}\n"
                    f"ACV: {acv_clean} USD\n"
                    f"Champion: {champion}"
                )

                metadata = {
                    "type": "gtm_deal",
                    "deal_name": deal_name,
                    "stage": stage,
                    "acv": acv_clean,
                    "champion": champion,
                    "source": "csv_import"
                }

                memory_id = self.manager.add_memory(
                    category="work",
                    content=content,
                    metadata=metadata
                )
                memory_ids.append(memory_id)

        return memory_ids

    def ingest_transcript(self, file_path: Path, deal_name: Optional[str] = None) -> int:
        """
        Parses GTM deal details from a transcript text file using LLM.
        Saves the deal details and next steps as a memory of category 'work'.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Transcript file not found: {file_path}")

        with open(file_path, mode="r", encoding="utf-8") as f:
            transcript_content = f.read()

        from core.memory.compactor import _call_llm_api

        deal_context = f"The target deal name is: {deal_name}." if deal_name else "Extract the deal/company name from the transcript."

        prompt = f"""You are the Mithrandir GTM Ingestion Assistant.
Analyze the following sales call or meeting transcript to extract key deal attributes and next steps.

Context: {deal_context}

Transcript:
{transcript_content}

Output the extracted details as a JSON object matching this structure:
{{
  "deal_name": "Name of the deal/company",
  "stage": "Current sales stage (e.g. Discovery, Proposal, Negotiation)",
  "acv": "Annual Contract Value (approximate amount in USD, output digits only or with USD text, no dollar sign characters)",
  "champion": "Name of the champion or key contact",
  "next_steps": [
    "Next step 1",
    "Next step 2"
  ]
}}

Ensure that you do not use any dollar sign characters (symbol for dollar) or em-dashes in the output JSON. Return only the raw JSON object, without markdown code block wrappers or any conversational text.
"""
        response = _call_llm_api(prompt)
        extracted = None
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
                
                extracted = json.loads(clean_text)
            except Exception as e:
                logger.error(f"Failed to parse LLM JSON response during transcript ingestion: {e}. Raw: {response}")

        # Fallback to local heuristic parsing if LLM is offline or parsing fails
        if not extracted:
            logger.warning("Using local fallback heuristic for transcript ingestion.")
            extracted = self._run_local_fallback_transcript(transcript_content, deal_name)

        # Override deal name if user explicitly provided one and extracted is empty
        if deal_name and (not extracted.get("deal_name") or extracted["deal_name"] == "Unknown"):
            extracted["deal_name"] = deal_name

        # Construct final content
        extracted_deal_name = extracted.get("deal_name") or deal_name or "Unknown Deal"
        stage = extracted.get("stage") or "Unknown Stage"
        acv = str(extracted.get("acv") or "0").replace(chr(36), "").strip()
        champion = extracted.get("champion") or "Unknown Champion"
        next_steps = extracted.get("next_steps") or []

        next_steps_str = "\n".join([f"- {step}" for step in next_steps])
        content = (
            f"GTM Deal: {extracted_deal_name}\n"
            f"Stage: {stage}\n"
            f"ACV: {acv} USD\n"
            f"Champion: {champion}\n"
            f"Next Steps:\n{next_steps_str}"
        )

        metadata = {
            "type": "gtm_deal",
            "deal_name": extracted_deal_name,
            "stage": stage,
            "acv": acv,
            "champion": champion,
            "next_steps": next_steps,
            "source": "transcript_import"
        }

        memory_id = self.manager.add_memory(
            category="work",
            content=content,
            metadata=metadata
        )
        return memory_id

    def _run_local_fallback_transcript(self, text: str, deal_name: Optional[str] = None) -> Dict[str, Any]:
        """Local heuristic parser if LLM fails or is offline."""
        lines = text.splitlines()
        extracted = {
            "deal_name": deal_name or "Unknown",
            "stage": "Discovery",
            "acv": "0",
            "champion": "Unknown",
            "next_steps": []
        }
        
        # Simple heuristics
        for line in lines:
            line_lower = line.lower()
            if "next steps" in line_lower or "next step" in line_lower or "next_step" in line_lower:
                parts = line.split(":")
                if len(parts) > 1 and parts[1].strip():
                    extracted["next_steps"].append(parts[1].strip())
            elif "acv" in line_lower or "annual contract value" in line_lower or "value" in line_lower:
                for word in line.split():
                    clean_word = "".join(c for c in word if c.isdigit())
                    if clean_word:
                        extracted["acv"] = clean_word
                        break
            elif "champion" in line_lower or "contact" in line_lower:
                parts = line.split(":")
                if len(parts) > 1:
                    extracted["champion"] = parts[1].strip()

        # If next steps list is empty, look for bullet points or lists in text
        if not extracted["next_steps"]:
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("- ") or stripped.startswith("* "):
                    step_val = stripped[2:].strip()
                    if step_val:
                        extracted["next_steps"].append(step_val)

        return extracted
