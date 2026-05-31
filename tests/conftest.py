import json
import os
import pytest
import core.memory.compactor
import core.memory.manager

@pytest.fixture(autouse=True)
def mock_llm_and_embeddings(monkeypatch):
    """Globally mock LLM calls and embeddings to prevent network calls during tests, while preserving retry/backoff test behavior."""
    
    # 1. Mock get_embedding
    def mocked_get_embedding(text: str):
        return [0.1] * 768
        
    monkeypatch.setattr("core.memory.manager.get_embedding", mocked_get_embedding)
    
    # 2. Mock _call_llm_api
    original_call_llm = core.memory.compactor._call_llm_api
    
    def mocked_call_llm(prompt: str):
        # If in the retry backoff test, delegate to the original function
        if os.environ.get("GEMINI_API_KEY") == "mock-gemini-key":
            return original_call_llm(prompt)
            
        prompt_lower = prompt.lower()
        
        # A. Sentinel / Cognitive Drift check (must be checked first!)
        if "cognitive drift sentinel" in prompt_lower or "playbook rules" in prompt_lower:
            return None
            
        # B. LinkedIn profile parsing
        if "profile parsing" in prompt_lower or "linkedin" in prompt_lower:
            return json.dumps({
                "name": "Aaron Miguel Santos",
                "headline": "GTM Operations Lead at Fonoa",
                "summary": "Experienced GTM Operations Lead.",
                "experience": [{
                    "role": "GTM Operations Lead",
                    "company": "Fonoa",
                    "period": "Jan 2024 - Present",
                    "description": "Lead go-to-market operations."
                }],
                "education": [{
                    "school": "University of Washington",
                    "degree": "Bachelor of Science",
                    "field": "Informatics",
                    "period": "2015 - 2019"
                }],
                "skills": ["Claude Code", "Python", "Git"],
                "languages": ["English", "Spanish"]
            })
            
        # C. Travel confirmation parsing
        if any(kw in prompt_lower for kw in ["travel confirmation", "delta", "hotel", "air france", "klm", "ihg", "airbnb", "united"]):
            carrier = "Delta Airlines"
            flight_number = "DL1284"
            confirmation = "ABCDEF"
            start_date = "2026-06-15"
            end_date = "2026-06-15"
            destination = "JFK to MIA"
            hotel_name = None
            
            if "dl100" in prompt_lower or "dl 100" in prompt_lower or "gdr5cv" in prompt_lower:
                carrier = "Delta Airlines"
                flight_number = "DL100"
                confirmation = "GDR5CV"
                start_date = "2026-06-07"
                destination = "JFK to AMS"
            elif "air france" in prompt_lower:
                carrier = "Air France"
                flight_number = "AF6789"
                confirmation = "AF6789"
                start_date = "2026-06-15"
                destination = "CDG to ATH"
            elif "klm" in prompt_lower:
                carrier = "KLM"
                flight_number = "KLM543"
                confirmation = "KLM543"
                start_date = "2026-06-15"
                destination = "AMS"
            elif "united" in prompt_lower:
                carrier = "United Airlines"
                flight_number = "UA999"
                confirmation = "UAX999"
                start_date = "2026-06-07"
                destination = "JFK to FRA"
            elif "kimpton" in prompt_lower or "ihg" in prompt_lower:
                carrier = None
                flight_number = None
                confirmation = "98765432"
                start_date = "2026-08-01"
                end_date = "2026-08-08"
                destination = "London"
                hotel_name = "Kimpton Fitzroy London"
            elif "airbnb" in prompt_lower:
                carrier = None
                flight_number = None
                confirmation = "HMTR2D9"
                start_date = "2026-09-01"
                end_date = "2026-09-05"
                destination = "Rome"
                hotel_name = "Cozy Apartment Airbnb listing in Rome"
                
            return json.dumps({
                "type": "flight" if carrier else "hotel",
                "destination": destination,
                "start_date": start_date,
                "end_date": end_date,
                "carrier": carrier,
                "flight_number": flight_number,
                "hotel_name": hotel_name,
                "confirmation_code": confirmation,
                "activities": ["Sightseeing"],
                "packing_list": ["Clothes"]
            })
            
        # D. Generic fallback
        return "Mocked LLM Response"
        
    monkeypatch.setattr("core.memory.compactor._call_llm_api", mocked_call_llm)
