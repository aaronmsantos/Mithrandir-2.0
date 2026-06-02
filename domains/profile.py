import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from core.memory.manager import MemoryManager

logger = logging.getLogger("mithrandir")

class ProfileDomain:
    """Domain module for managing the operator's professional history, resume, and skills."""
    def __init__(self, db_path: Optional[Path] = None):
        self.manager = MemoryManager(db_path)

    def parse_linkedin_content(self, content: str) -> Dict[str, Any]:
        """Parses raw LinkedIn copy-pasted text/HTML using LLM if available, else regex fallback."""
        parsed_data = None
        
        # Try LLM-based parsing
        try:
            parsed_data = self._parse_linkedin_content_llm(content)
        except Exception as e:
            logger.warning(f"LLM LinkedIn parser failed: {e}. Falling back to regex parser.")
            
        if not parsed_data:
            parsed_data = self._parse_linkedin_content_fallback(content)
            
        return parsed_data

    def _parse_linkedin_content_llm(self, content: str) -> Optional[Dict[str, Any]]:
        """Call LLM to extract structured profile JSON from raw text."""
        from core.memory.compactor import _call_llm_api
        
        prompt = f"""You are a professional profile parsing agent.
Analyze the following raw LinkedIn profile text/HTML and extract the structured information.

Raw Content:
{content}

Provide the output strictly as a JSON object matching this schema:
{{
  "name": "Full Name",
  "headline": "Current Professional Headline",
  "summary": "Professional summary or About section",
  "experience": [
    {{
      "role": "Job Title",
      "company": "Company Name",
      "period": "Start Date - End Date (e.g. Jan 2024 - Present)",
      "description": "Key achievements and responsibilities"
    }}
  ],
  "education": [
    {{
      "school": "University/School Name",
      "degree": "Degree earned (e.g., Bachelor of Science)",
      "field": "Field of study",
      "period": "Start Date - End Date"
    }}
  ],
  "skills": ["Skill 1", "Skill 2"],
  "languages": ["Language 1", "Language 2"]
}}

Ensure:
1. All fields are filled as accurately as possible based on the raw text.
2. Only output the JSON object. Do not include markdown code block wrapper or any other conversational text.
"""
        response = _call_llm_api(prompt)
        if not response:
            return None
            
        # Clean markdown code block if present
        text = response.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
            
        try:
            return json.loads(text)
        except Exception as e:
            logger.error(f"Failed to decode LLM response as JSON: {e}")
            return None

    def _parse_linkedin_content_fallback(self, content: str) -> Dict[str, Any]:
        """Deterministic regex-based parsing fallback for LinkedIn copy-pasted text."""
        lines = [line.strip() for line in content.split("\n")]
        
        result = {
            "name": "",
            "headline": "",
            "summary": "",
            "experience": [],
            "education": [],
            "skills": [],
            "languages": []
        }
        
        # 1. Heuristic for name and headline (first two non-empty lines)
        non_empty = [l for l in lines if l]
        if non_empty:
            result["name"] = non_empty[0]
            if len(non_empty) > 1:
                result["headline"] = non_empty[1]
                
        # 2. Section separation
        current_section = None
        headers_map = {
            "experience": ["experience", "work history", "employment history", "positions"],
            "education": ["education", "academic history", "schooling"],
            "skills": ["skills", "skills & endorsements", "top skills", "key skills"],
            "summary": ["about", "summary", "professional summary", "bio"],
            "languages": ["languages"]
        }
        
        ignored_headers = [
            "volunteering", "licenses & certifications", "certifications", "recommendations", 
            "interests", "activity", "honors & awards", "organizations", "projects", "publications",
            "people you may know", "you might like", "groups", "companies", "schools", "analytics",
            "received", "given", "top voices", "show all"
        ]
        
        sections_content = {k: [] for k in headers_map.keys()}
        
        def detect_section(line: str) -> Optional[str]:
            l_clean = line.lower().strip().rstrip(":")
            for sec, keywords in headers_map.items():
                if l_clean in keywords:
                    return sec
            return None

        for line in lines:
            detected = detect_section(line)
            if detected:
                current_section = detected
                continue
                
            # Check for ignored sections to reset parsing
            l_clean = line.lower().strip().rstrip(":")
            if l_clean in ignored_headers:
                current_section = None
                continue
                
            if current_section:
                sections_content[current_section].append(line)
                
        # Parse Summary
        result["summary"] = "\n".join([l for l in sections_content["summary"] if l]).strip()
        
        # Parse Skills
        skills_raw = sections_content["skills"]
        skills_list = []
        for s in skills_raw:
            if not s:
                continue
            # Strip bullet characters
            s_cleaned = re.sub(r'^[•\-\*\d\.\s]+', '', s).strip()
            if s_cleaned:
                if "," in s_cleaned and len(s_cleaned) < 1000:
                    skills_list.extend([x.strip() for x in s_cleaned.split(",") if x.strip()])
                else:
                    skills_list.append(s_cleaned)
        result["skills"] = list(dict.fromkeys(skills_list))
        
        # Parse Languages
        languages_raw = sections_content["languages"]
        langs = []
        for l in languages_raw:
            if not l:
                continue
            l_cleaned = re.sub(r'^[•\-\*\d\.\s]+', '', l).strip()
            if l_cleaned:
                if "," in l_cleaned:
                    langs.extend([x.strip() for x in l_cleaned.split(",") if x.strip()])
                else:
                    langs.append(l_cleaned)
        result["languages"] = langs
        
        # Parse Experience (look for date patterns as anchors)
        exp_lines = [l for l in sections_content["experience"] if l]
        date_pattern = re.compile(
            r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December|\d{4})\b'
            r'.*?\s*(?:-|\u2010|\u2011|\u2012|\u2013|\u2014|–|to)\s*.*?'
            r'\b(Present|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December|\d{4})\b',
            re.IGNORECASE
        )
        
        i = 0
        while i < len(exp_lines):
            line = exp_lines[i]
            if date_pattern.search(line):
                role = "Unknown Role"
                company = "Unknown Company"
                period = line
                desc_lines = []
                
                # Check preceding lines for role and company
                if i >= 1:
                    val1 = exp_lines[i-1]
                    if i >= 2:
                        val2 = exp_lines[i-2]
                        role = val2
                        company = val1
                    else:
                        company = val1
                
                # Read ahead for description
                i += 1
                while i < len(exp_lines) and not date_pattern.search(exp_lines[i]):
                    desc_lines.append(exp_lines[i])
                    i += 1
                    
                result["experience"].append({
                    "role": role,
                    "company": company,
                    "period": period,
                    "description": "\n".join(desc_lines).strip()
                })
            else:
                i += 1
                
        # Parse Education
        edu_lines = [l for l in sections_content["education"] if l]
        i = 0
        while i < len(edu_lines):
            line = edu_lines[i]
            if date_pattern.search(line):
                school = "Unknown School"
                degree = "Unknown Degree"
                period = line
                if i >= 1:
                    val1 = edu_lines[i-1]
                    if i >= 2:
                        school = edu_lines[i-2]
                        degree = val1
                    else:
                        school = val1
                
                result["education"].append({
                    "school": school,
                    "degree": degree,
                    "period": period
                })
                i += 1
            else:
                i += 1
                
        return result

    def sync_agent_coordinates(self, profile_data: Dict[str, Any]) -> bool:
        """Syncs the parsed profile data (Fonoa role, new tools/skills) with Agent.MD coordinates."""
        workspace_dir = Path(__file__).resolve().parent.parent
        agent_md_path = workspace_dir / "Agent.MD"
        
        if not agent_md_path.exists():
            logger.warning(f"Agent.MD not found at {agent_md_path}, skipping sync.")
            return False
            
        try:
            with open(agent_md_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Locate the GTM Engineering Stack line
            pattern = r"(\*\s+\*\*GTM Engineering Stack \(Fonoa\)\*\*:\s*)(.*?)(\n)"
            match = re.search(pattern, content)
            if not match:
                logger.warning("Could not find GTM Engineering Stack line in Agent.MD")
                return False
                
            prefix = match.group(1)
            stack_text = match.group(2)
            suffix = match.group(3)
            
            # Extract parsed skills
            profile_skills = profile_data.get("skills", [])
            
            # Common GTM tools/technologies to watch for
            gtm_keywords = {
                "claude code", "clay", "salesforce", "hubspot", "vercel", "base44", "slack",
                "python", "javascript", "typescript", "git", "github", "sqlite", "openai",
                "chatgpt", "gemini", "anthropic", "llm", "automation", "api", "integromat", "make.com",
                "zapier", "postgresql", "sql", "react", "next.js", "node.js"
            }
            
            matched_skills = [
                s for s in profile_skills
                if any(kw in s.lower() for kw in gtm_keywords)
            ]
            
            # Baseline tools
            existing_tools = ["Claude Code", "Clay", "Salesforce", "HubSpot", "Vercel", "Base44", "Slack"]
            
            # Merge lists
            merged_tools = list(existing_tools)
            for skill in matched_skills:
                normalized_skill = skill.lower().strip()
                # Find matching standard formatting if any
                matching_standard = next((t for t in gtm_keywords if t == normalized_skill), skill)
                # Capitalize nicely
                words = matching_standard.split()
                nice_name = " ".join([w.capitalize() if w not in ["com", "js"] else w for w in words])
                if not any(t.lower() == normalized_skill for t in merged_tools):
                    merged_tools.append(nice_name)
                    
            # Build the new sentence
            new_stack_line = (
                f"{prefix}Claude Code is the primary tool and work surface. Also utilizes "
                f"{', '.join(merged_tools[:-1])}, and {merged_tools[-1]}. Focuses on consistently "
                f"improving mastery of IDEs and agentic coding platforms to maintain a position of strength at Fonoa.{suffix}"
            )
            
            new_content = re.sub(pattern, new_stack_line, content)
            
            with open(agent_md_path, "w", encoding="utf-8") as f:
                f.write(new_content)
                
            logger.info("Successfully synchronized coordinates in Agent.MD.")
            return True
        except Exception as e:
            logger.error(f"Error syncing coordinates with Agent.MD: {e}")
            return False

    def import_profile(self, file_path: Optional[Path] = None, raw_content: Optional[str] = None, is_linkedin: bool = False) -> int:
        """Reads a professional history text/markdown/HTML file or raw string and stores it in the memory layer."""
        if file_path:
            if not file_path.exists():
                raise FileNotFoundError(f"Profile file not found at: {file_path}")
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            source = file_path.name
        elif raw_content:
            content = raw_content.strip()
            source = "direct_input"
        else:
            raise ValueError("Must provide either file_path or raw_content.")

        if not content:
            raise ValueError("Profile content is empty.")

        metadata = {
            "source_file": source,
            "type": "linkedin_profile" if is_linkedin else "professional_history",
            "parsed": False
        }

        if is_linkedin:
            try:
                parsed_data = self.parse_linkedin_content(content)
                metadata["parsed"] = True
                metadata["profile_data"] = parsed_data
                self.sync_agent_coordinates(parsed_data)
            except Exception as e:
                logger.error(f"Failed to parse LinkedIn content: {e}")
        
        memory_id = self.manager.add_memory(
            category="profile",
            content=content,
            metadata=metadata
        )
        logger.info(f"Professional profile history successfully imported (Memory ID: {memory_id}).")
        return memory_id

    def get_latest_profile(self) -> Optional[Dict[str, Any]]:
        """Retrieves the most recently imported professional history log."""
        memories = self.manager.search_memories(category="profile")
        if memories:
            # They are already sorted chronologically descending in search_memories
            return memories[0]
        return None
