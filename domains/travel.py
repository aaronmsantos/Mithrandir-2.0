import json
import logging
import re
import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from core.memory.manager import MemoryManager

logger = logging.getLogger("mithrandir")

class TravelDomain:
    """Domain module for tracking travel itineraries, parsing confirmations, and managing lists."""
    def __init__(self, db_path: Optional[Path] = None):
        self.manager = MemoryManager(db_path)

    def add_itinerary(
        self,
        destination: str,
        start_date: str,
        end_date: str,
        activities: List[str],
        packing_list: List[str]
    ) -> int:
        """Adds a travel itinerary memory to the durable memory layer."""
        if not destination or not start_date or not end_date:
            raise ValueError("Destination, start date, and end date are required.")

        content = (
            f"Trip Itinerary to {destination} from {start_date} to {end_date}.\n"
            f"Planned Activities: {', '.join(activities)}\n"
            f"Packing List: {', '.join(packing_list)}"
        )
        
        metadata = {
            "destination": destination,
            "start_date": start_date,
            "end_date": end_date,
            "activities": activities,
            "packing_list": packing_list
        }
        
        return self.manager.add_memory(
            category="travel",
            content=content,
            metadata=metadata
        )

    def list_itineraries(self) -> List[Dict[str, Any]]:
        """Lists all logged itineraries."""
        return self.manager.search_memories(category="travel")

    def parse_travel_confirmation(self, content: str) -> Dict[str, Any]:
        """Parses raw travel confirmations using LLM if available, else regex fallback."""
        parsed_data = None
        try:
            parsed_data = self._parse_travel_confirmation_llm(content)
        except Exception as e:
            logger.warning(f"LLM travel confirmation parser failed: {e}. Falling back to regex.")
            
        if not parsed_data:
            parsed_data = self._parse_travel_confirmation_fallback(content)
            
        return parsed_data

    def _parse_travel_confirmation_llm(self, content: str) -> Optional[Dict[str, Any]]:
        """Extracts structured flight or lodging details using the LLM API."""
        from core.memory.compactor import _call_llm_api
        
        prompt = f"""You are a travel confirmation parsing agent.
Analyze the following raw flight or hotel confirmation text and extract the structured information.

Raw Content:
{content}

Provide the output strictly as a JSON object matching this schema:
{{
  "type": "flight, hotel, or mixed",
  "destination": "Destination city/country (or route like 'JFK to LHR' if flight)",
  "start_date": "Start date in YYYY-MM-DD format",
  "end_date": "End date in YYYY-MM-DD format",
  "carrier": "Airline carrier name (e.g. Delta Airlines) if flight, otherwise null",
  "flight_number": "Flight number (e.g. DL123) if flight, otherwise null",
  "hotel_name": "Hotel name (e.g. InterContinental) if hotel, otherwise null",
  "confirmation_code": "Confirmation number or Record Locator if present, otherwise null",
  "activities": ["Planned activities or suggested local interest points"],
  "packing_list": ["Suggested packing items based on destination/dates"]
}}

Ensure:
1. Dates are parsed accurately.
2. Only output the JSON object. Do not include markdown code block wrapper or any other conversational text.
"""
        response = _call_llm_api(prompt)
        if not response:
            return None
            
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
            logger.error(f"Failed to decode LLM travel response: {e}")
            return None

    def _parse_travel_confirmation_fallback(self, content: str) -> Dict[str, Any]:
        """Deterministic regex-based parsing fallback for travel confirmations."""
        result = {
            "type": "mixed",
            "destination": "Unknown Destination",
            "start_date": None,
            "end_date": None,
            "carrier": None,
            "flight_number": None,
            "hotel_name": None,
            "confirmation_code": None,
            "activities": [],
            "packing_list": []
        }
        
        content_lower = content.lower()
        
        # 1. Detect Carrier & Flight Number
        if "delta" in content_lower:
            result["carrier"] = "Delta Airlines"
        elif "air france" in content_lower:
            result["carrier"] = "Air France"
        elif "klm" in content_lower:
            result["carrier"] = "KLM"
        elif "virgin atlantic" in content_lower:
            result["carrier"] = "Virgin Atlantic"
        elif "united" in content_lower:
            result["carrier"] = "United Airlines"
        elif "american" in content_lower:
            result["carrier"] = "American Airlines"
            
        flight_match = re.search(r'\b(?:dl|dal|delta|ua|aa|af|klm)(?:\s+flight)?\s*#?\s*(\d{2,4})\b', content_lower)
        if flight_match:
            # Default to DL flight if Delta is mentioned
            result["flight_number"] = f"DL{flight_match.group(1)}" if "delta" in content_lower or "dl" in content_lower else flight_match.group(1).upper()
            if not result["carrier"]:
                result["carrier"] = "Delta Airlines" if "dl" in content_lower else "Unknown Carrier"
                
        # 2. Detect Hotel name (specifically checking common IHG brands)
        ihg_hotels = ["intercontinental", "kimpton", "crowne plaza", "holiday inn", "staybridge", "indigo"]
        for h in ihg_hotels:
            if h in content_lower:
                match = re.search(rf'\b([A-Za-z0-9 \t\-]*{h}[A-Za-z0-9 \t\-]*)\b', content_lower, re.IGNORECASE)
                if match:
                    result["hotel_name"] = match.group(1).strip().title()
                else:
                    result["hotel_name"] = h.title()
                break
                
        if not result["hotel_name"]:
            if "airbnb" in content_lower or "air bnb" in content_lower:
                match = re.search(r'\b([A-Za-z0-9 \t\-]*airbnb[A-Za-z0-9 \t\-]*)\b', content_lower, re.IGNORECASE)
                if match:
                    result["hotel_name"] = match.group(1).strip().title()
                else:
                    result["hotel_name"] = "Airbnb"
            else:
                hotel_match = re.search(r'\b([A-Za-z0-9 \t\-]+(?:hotel|resort|inn|lodging|suites))\b', content_lower)
                if hotel_match:
                    result["hotel_name"] = hotel_match.group(1).strip().title()
                
        # Set confirmation type
        if result["carrier"] and result["hotel_name"]:
            result["type"] = "mixed"
        elif result["carrier"]:
            result["type"] = "flight"
        elif result["hotel_name"]:
            result["type"] = "hotel"
            
        # 3. Detect Confirmation Code
        loc_match = re.search(r'\b(?:confirmation|locator|record|booking\s*ref|reference)\b\s*(?:number|num|no|code)?\s*:?\s*#?\s*\b([a-z0-9]{6,10})\b', content_lower)
        if loc_match and loc_match.group(1) != "number":
            result["confirmation_code"] = loc_match.group(1).upper()
        else:
            hashtag_match = re.search(r'#([a-z0-9]{6,10})\b', content_lower)
            if hashtag_match:
                result["confirmation_code"] = hashtag_match.group(1).upper()
            else:
                num_match = re.search(r'\b(?:confirmation|booking|reservation)\b\s*(?:number|num|no)?\s*:?\s*#?\s*\b(\d{6,10})\b', content_lower)
                if num_match:
                    result["confirmation_code"] = num_match.group(1)
                
        # 4. Parse Dates
        date_patterns = [
            r'\b(\d{4})-(\d{2})-(\d{2})\b', # YYYY-MM-DD
            r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{1,2})\b,?\s*\b(\d{4})\b' # Month DD, YYYY
        ]
        
        found_dates = []
        for pattern in date_patterns:
            matches = re.finditer(pattern, content_lower)
            for m in matches:
                try:
                    if len(m.groups()) == 3:
                        if m.group(1).isdigit():
                            d = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                        else:
                            months = {"jan":1, "feb":2, "mar":3, "apr":4, "may":5, "jun":6, "jul":7, "aug":8, "sep":9, "oct":10, "nov":11, "dec":12}
                            month_num = months[m.group(1)[:3]]
                            d = datetime.date(int(m.group(3)), month_num, int(m.group(2)))
                        found_dates.append(d)
                except ValueError:
                    continue
                    
        found_dates = sorted(found_dates)
        if len(found_dates) >= 1:
            result["start_date"] = found_dates[0].isoformat()
            if len(found_dates) >= 2:
                result["end_date"] = found_dates[-1].isoformat()
            else:
                if result["type"] == "flight":
                    result["end_date"] = result["start_date"]
                else:
                    result["end_date"] = (found_dates[0] + datetime.timedelta(days=7)).isoformat()
        else:
            today = datetime.date.today()
            result["start_date"] = today.isoformat()
            result["end_date"] = (today + datetime.timedelta(days=7)).isoformat()
            
        # 5. Destination Heuristic
        route_match = re.search(r'\b([a-z]{3})\s+(?:to|->|—)\s+([a-z]{3})\b', content_lower)
        if route_match:
            result["destination"] = f"{route_match.group(1).upper()} to {route_match.group(2).upper()}"
        else:
            city_match = re.search(r'\b(?:to|flying\s+to|arriving\s+in|trip\s+to)\s+([a-z\s]{3,20})\b', content_lower)
            if city_match:
                city = city_match.group(1).strip().title()
                city_words = city.split()
                clean_city_words = []
                for w in city_words:
                    if w.lower() in ["the", "a", "an", "on", "at", "for", "by", "with", "from"]:
                        break
                    clean_city_words.append(w)
                result["destination"] = " ".join(clean_city_words) if clean_city_words else "Unknown Destination"
                
        return result

    def bourdain_activity_enricher(self, activities: List[str], destination: str) -> List[str]:
        """Suggests Bourdain-inspired local hangouts and off-the-beaten-path experiences."""
        from core.memory.compactor import _call_llm_api
        
        clean_acts = [a.strip() for a in activities if a.strip()]
        
        prompt = f"""You are a travel curation assistant heavily inspired by Anthony Bourdain's travel philosophy.
The operator is planning a trip to: {destination}
Their current list of planned activities or interests: {', '.join(clean_acts) if clean_acts else 'None'}

Please suggest 3-4 authentic, immersive local hangouts, street food hubs, or off-the-beaten-path experiences for this destination.
Avoid tourist traps, major commercial spots, and conventional sightseeing checklists. Provide them as a brief JSON list of strings.

Output strictly a JSON list:
[
  "Suggestion 1 (e.g. Visit the fish market at 5 AM for breakfast at the counter)",
  "Suggestion 2 (e.g. Try local stew at the family-owned taverna in the working-class quarter)"
]

Do not include any preamble or markdown code block wrappers. Output only raw JSON.
"""
        enriched = None
        response = _call_llm_api(prompt)
        if response:
            try:
                clean_text = response.strip()
                if clean_text.startswith("```"):
                    lines = clean_text.splitlines()
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    clean_text = "\n".join(lines).strip()
                enriched = json.loads(clean_text)
            except Exception as e:
                logger.error(f"Failed to parse Bourdain suggestions JSON: {e}")
                
        if not enriched or not isinstance(enriched, list):
            enriched = [
                "Explore local neighborhood food markets away from city centers.",
                "Seek out family-owned, long-running street vendors and tavernas.",
                "Avoid main tourist plazas and restaurants with English-only photo menus.",
                "Get lost in residential quarters and talk to neighborhood residents."
            ]
            
        return list(dict.fromkeys(clean_acts + enriched))

    def import_confirmation_file(self, file_path: Path) -> int:
        """Parses a travel confirmation file, enriches it, and saves to database."""
        if not file_path.exists():
            raise FileNotFoundError(f"Confirmation file not found at: {file_path}")
            
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            
        if not content:
            raise ValueError("Confirmation file is empty.")
            
        data = self.parse_travel_confirmation(content)
        
        # Enrich activities using Bourdain philosophy
        original_acts = data.get("activities", [])
        enriched_acts = self.bourdain_activity_enricher(original_acts, data["destination"])
        data["activities"] = enriched_acts
        
        # Formulate memory content
        type_str = data["type"].title()
        details = []
        if data.get("carrier"):
            details.append(f"Carrier: {data['carrier']}")
        if data.get("flight_number"):
            details.append(f"Flight #: {data['flight_number']}")
        if data.get("hotel_name"):
            details.append(f"Lodging: {data['hotel_name']}")
        if data.get("confirmation_code"):
            details.append(f"Confirmation Code: {data['confirmation_code']}")
            
        travel_content = (
            f"Parsed {type_str} Travel Confirmation for {data['destination']}.\n"
            f"Dates: {data['start_date']} to {data['end_date']}\n"
            f"{', '.join(details)}\n"
            f"Enriched Activities (Bourdain Style): {', '.join(enriched_acts)}\n"
            f"Packing List: {', '.join(data.get('packing_list', []))}"
        )
        
        metadata = {
            "source_file": file_path.name,
            "type": "travel_confirmation",
            "destination": data["destination"],
            "start_date": data["start_date"],
            "end_date": data["end_date"],
            "activities": enriched_acts,
            "packing_list": data.get("packing_list", []),
            "parsed_data": data
        }
        
        memory_id = self.manager.add_memory(
            category="travel",
            content=travel_content,
            metadata=metadata
        )
        return memory_id

    def import_confirmation_files(self, directory: Optional[Path] = None) -> List[int]:
        """Scans the incoming travel directory for confirmation files, parses, and logs them."""
        workspace_dir = Path(__file__).resolve().parent.parent
        incoming_dir = directory or (workspace_dir / "data" / "incoming_travel")
        
        if not incoming_dir.exists():
            incoming_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created incoming travel directory at: {incoming_dir}")
            return []
            
        processed_dir = incoming_dir / "processed"
        processed_dir.mkdir(exist_ok=True)
        
        memory_ids = []
        for ext in ["*.txt", "*.md", "*.html"]:
            for file_path in incoming_dir.glob(ext):
                try:
                    logger.info(f"Processing travel confirmation file: {file_path.name}")
                    mem_id = self.import_confirmation_file(file_path)
                    memory_ids.append(mem_id)
                    
                    # Move to processed directory
                    target_path = processed_dir / file_path.name
                    if target_path.exists():
                        target_path.unlink()
                    file_path.rename(target_path)
                    logger.info(f"Archived processed travel file to: {target_path}")
                except Exception as e:
                    logger.error(f"Failed to process confirmation file '{file_path.name}': {e}")
                    
        return memory_ids
