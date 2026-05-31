import json
import logging
import re
import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from html.parser import HTMLParser
from core.memory.manager import MemoryManager

logger = logging.getLogger("mithrandir")

class HTMLTextExtractor(HTMLParser):
    """Parses HTML documents and extracts visible text content, ignoring scripts/styles."""
    def __init__(self):
        super().__init__()
        self.result = []
        self.ignore_stack = []

    def handle_starttag(self, tag, attrs):
        if tag in ["script", "style", "head", "meta", "link"]:
            self.ignore_stack.append(tag)
        elif tag in ["p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6"]:
            self.result.append("\n")

    def handle_endtag(self, tag):
        if tag in ["script", "style", "head", "meta", "link"]:
            if tag in self.ignore_stack:
                self.ignore_stack.remove(tag)
        elif tag in ["p", "div", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6"]:
            self.result.append("\n")

    def handle_data(self, data):
        if not self.ignore_stack:
            self.result.append(data)

    def get_text(self) -> str:
        raw_text = "".join(self.result)
        lines = [line.strip() for line in raw_text.splitlines()]
        return "\n".join([line for line in lines if line])

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
        if re.search(r'<!doctype\s+html|<html\b|<body\b', content, re.IGNORECASE):
            extractor = HTMLTextExtractor()
            extractor.feed(content)
            content = extractor.get_text()
            
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
        carrier_map = {
            "delta": "Delta Airlines",
            "air france": "Air France",
            "klm": "KLM",
            "virgin atlantic": "Virgin Atlantic",
            "aeromexico": "Aeromexico",
            "korean air": "Korean Air",
            "sas": "SAS",
            "scandinavian airlines": "SAS",
            "china eastern": "China Eastern",
            "china airlines": "China Airlines",
            "vietnam airlines": "Vietnam Airlines",
            "saudia": "Saudia",
            "ita airways": "ITA Airways",
            "united": "United Airlines",
            "american": "American Airlines"
        }
        
        for k, v in carrier_map.items():
            if k in content_lower:
                result["carrier"] = v
                break

        # Capture both the prefix and the flight number digits
        flight_match = re.search(
            r'\b(dl|dal|delta|ua|aa|af|klm|vs|am|ke|sk|mu|ci|vn|sv|az)(?:\s+flight)?\s*#?\s*(\d{2,4})\b',
            content_lower
        )
        if flight_match:
            prefix = flight_match.group(1).upper()
            digits = flight_match.group(2)
            
            # Map common prefix abbreviations/names to standard codes
            if prefix in ["DELTA", "DAL", "DL"]:
                std_prefix = "DL"
            else:
                std_prefix = prefix
                
            result["flight_number"] = f"{std_prefix}{digits}"
            
            # Auto-assign carrier if not already detected
            if not result["carrier"]:
                if std_prefix == "DL":
                    result["carrier"] = "Delta Airlines"
                elif std_prefix == "AF":
                    result["carrier"] = "Air France"
                elif std_prefix == "KLM":
                    result["carrier"] = "KLM"
                elif std_prefix == "VS":
                    result["carrier"] = "Virgin Atlantic"
                elif std_prefix == "AM":
                    result["carrier"] = "Aeromexico"
                elif std_prefix == "KE":
                    result["carrier"] = "Korean Air"
                elif std_prefix == "SK":
                    result["carrier"] = "SAS"
                elif std_prefix == "MU":
                    result["carrier"] = "China Eastern"
                elif std_prefix == "CI":
                    result["carrier"] = "China Airlines"
                elif std_prefix == "VN":
                    result["carrier"] = "Vietnam Airlines"
                elif std_prefix == "SV":
                    result["carrier"] = "Saudia"
                elif std_prefix == "AZ":
                    result["carrier"] = "ITA Airways"
                elif std_prefix == "UA":
                    result["carrier"] = "United Airlines"
                elif std_prefix == "AA":
                    result["carrier"] = "American Airlines"
                else:
                    result["carrier"] = "Unknown Carrier"
                    
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
                listing_match = re.search(r'\b([a-z0-9 \t\-]+(?:apartment|loft|house|villa|studio|room|stay|home|cabin|suite|condo)(?:\s+in\s+[a-z \t\-]+)?)\b', content_lower, re.IGNORECASE)
                if listing_match:
                    result["hotel_name"] = f"Airbnb: {listing_match.group(1).strip().title()}"
                else:
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
        loc_match = re.search(r'\b(?:confirmation|locator|record|booking\s*ref|booking\s*id|reservation\s*id|reference|conf\.?)\b[ \t]*(?:number|num|no\.?|code)?[ \t]*:?[ \t]*#?[ \t]*\b([a-z0-9]{6,10})\b', content_lower)
        if loc_match and loc_match.group(1) != "number":
            result["confirmation_code"] = loc_match.group(1).upper()
        else:
            hashtag_match = re.search(r'#([a-z0-9]{6,10})\b', content_lower)
            if hashtag_match:
                result["confirmation_code"] = hashtag_match.group(1).upper()
            else:
                num_match = re.search(r'\b(?:confirmation|booking|reservation)\b[ \t]*(?:number|num|no)?[ \t]*:?[ \t]*#?[ \t]*\b(\d{6,10})\b', content_lower)
                if num_match:
                    result["confirmation_code"] = num_match.group(1)
                
        # 4. Parse Dates
        date_patterns = [
            r'\b(\d{4})-(\d{2})-(\d{2})\b', # YYYY-MM-DD
            r'\b(\d{2})/(\d{2})/(\d{4})\b', # MM/DD/YYYY
            r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{1,2})\b,?\s*\b(\d{4})\b', # Month DD, YYYY
            r'\b(\d{1,2})[\s-](jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s-](\d{4})\b' # DD Month YYYY or DD-Month-YYYY
        ]
        
        found_dates = []
        for pattern in date_patterns:
            matches = re.finditer(pattern, content_lower)
            for m in matches:
                try:
                    if len(m.groups()) == 3:
                        if m.group(1).isdigit() and len(m.group(1)) == 4:
                            d = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                        elif m.group(1).isdigit() and len(m.group(1)) == 2 and not m.group(2).isalpha():
                            # MM/DD/YYYY
                            d = datetime.date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
                        else:
                            # Month parsing (either Month DD, YYYY or DD Month YYYY)
                            months = {"jan":1, "feb":2, "mar":3, "apr":4, "may":5, "jun":6, "jul":7, "aug":8, "sep":9, "oct":10, "nov":11, "dec":12}
                            if m.group(1)[:3].lower() in months:
                                month_num = months[m.group(1)[:3].lower()]
                                d = datetime.date(int(m.group(3)), month_num, int(m.group(2)))
                            else:
                                month_num = months[m.group(2)[:3].lower()]
                                d = datetime.date(int(m.group(3)), month_num, int(m.group(1)))
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
            listing_loc_match = re.search(r'\b(?:apartment|loft|house|villa|studio|room|stay|home|cabin|suite|condo)\s+in\s+([a-z \t\-]{3,20})\b', content_lower, re.IGNORECASE)
            if listing_loc_match:
                result["destination"] = listing_loc_match.group(1).strip().title()
            else:
                known_locations = ["amsterdam", "athens", "paris", "london", "tokyo", "miami", "vancouver", "puerto rico", "thailand", "spain"]
                found_loc = None
                for loc in known_locations:
                    if loc in content_lower:
                        found_loc = loc.title()
                        break
                if found_loc:
                    result["destination"] = found_loc
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

    def import_confirmation_file(self, file_path: Path, audit_callback: Optional[Any] = None) -> int:
        """Parses a travel confirmation file, enriches it, and saves to database."""
        if not file_path.exists():
            raise FileNotFoundError(f"Confirmation file not found at: {file_path}")
            
        if file_path.suffix.lower() == ".pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(file_path)
                text_parts = []
                for page in reader.pages:
                    text_parts.append(page.extract_text() or "")
                content = "\n".join(text_parts).strip()
            except Exception as e:
                raise ValueError(f"Failed to extract text from PDF: {e}")
        else:
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
        
        # Run sentinel audit check if callback is provided
        if audit_callback:
            proceed = audit_callback(travel_content, metadata)
            if not proceed:
                logger.warning(f"Sentinel audit callback rejected entry for file: {file_path.name}")
                return -1
                
        memory_id = self.manager.add_memory(
            category="travel",
            content=travel_content,
            metadata=metadata
        )
        return memory_id

    def import_confirmation_files(self, directory: Optional[Path] = None, audit_callback: Optional[Any] = None) -> List[int]:
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
        for ext in ["*.txt", "*.md", "*.html", "*.pdf"]:
            for file_path in incoming_dir.glob(ext):
                try:
                    logger.info(f"Processing travel confirmation file: {file_path.name}")
                    mem_id = self.import_confirmation_file(file_path, audit_callback)
                    if mem_id == -1:
                        logger.warning(f"File skipped by sentinel check: {file_path.name}")
                        continue
                        
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

    def parse_pdf_mqd_activities(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Parses a Delta Account Activity PDF and extracts flights, card boosts, and headstarts."""
        import pypdf
        reader = pypdf.PdfReader(pdf_path)
        text_parts = []
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
        text = "\n".join(text_parts)
        
        lines = text.splitlines()
        activities = []
        
        months_map = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
        }

        def parse_dt(date_str):
            date_str = date_str.lower().strip()
            match = re.search(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{1,2}),?\s*(\d{4})\b', date_str)
            if match:
                m_name, day, year = match.groups()
                return f"{year}-{months_map[m_name]:02d}-{int(day):02d}"
            return None

        # Transaction/flight boundary headers
        stop_patterns = [
            r'^[A-Z]{3}\s+[A-Z]{3}', # Route
            r'MQD Boost',
            r'MQD Headstart',
            r'Delta SkyMiles',
            r'Delta Amex',
            r'DL\s+Amex',
            r'Uber\s+',
            r'UBER\s+',
            r'Miles Upgrade'
        ]

        def should_stop(line_str):
            for pattern in stop_patterns:
                if re.search(pattern, line_str, re.IGNORECASE):
                    return True
            return False

        idx = 0
        while idx < len(lines):
            line = lines[idx].strip()
            if not line:
                idx += 1
                continue
                
            # 1. Match Flight Route
            route_match = re.match(r'^([A-Z]{3})\s+([A-Z]{3})(?:\s+([A-Z]{2})\s*(\d{1,4}))?$', line)
            if route_match:
                origin, dest, carrier_code, flight_num = route_match.groups()
                
                date = None
                miles = None
                mqds = None
                ticket = None
                is_pending = False
                
                next_idx = idx + 1
                while next_idx < len(lines):
                    l_next = lines[next_idx].strip()
                    if not l_next:
                        next_idx += 1
                        continue
                    if should_stop(l_next):
                        break
                    if not date:
                        dt_check = parse_dt(l_next)
                        if dt_check:
                            date = dt_check
                            if "pending" in l_next.lower():
                                is_pending = True
                    if miles is None:
                        miles_m = re.search(r'([\d,]+)\s*miles', l_next, re.IGNORECASE)
                        if miles_m:
                            miles = int(miles_m.group(1).replace(",", ""))
                    if mqds is None:
                        mqds_m = re.search(r'\$?([\d,]+)\s*mqds', l_next, re.IGNORECASE)
                        if mqds_m:
                            mqds = int(mqds_m.group(1).replace(",", ""))
                    if not ticket:
                        ticket_m = re.search(r'ticket#?\s*(\d+)', l_next, re.IGNORECASE)
                        if ticket_m:
                            ticket = ticket_m.group(1)
                    next_idx += 1
                    
                if date:
                    activities.append({
                        "type": "flight",
                        "origin": origin,
                        "destination": dest,
                        "route": f"{origin} to {dest}",
                        "date": date,
                        "carrier": "Delta Airlines" if (not carrier_code or carrier_code in ["DL", "DL "]) else carrier_code,
                        "flight_number": f"{carrier_code or 'DL'}{flight_num}" if flight_num else None,
                        "miles": miles,
                        "mqds": mqds,
                        "ticket_number": ticket,
                        "status": "Pending" if is_pending else "Posted"
                    })
                    
            # 2. Match Card Headstart
            elif "mqd headstart" in line.lower():
                next_idx = idx + 1
                date = None
                mqds = None
                card_name = line.strip()
                
                while next_idx < len(lines):
                    l_next = lines[next_idx].strip()
                    if not l_next:
                        next_idx += 1
                        continue
                    if should_stop(l_next):
                        break
                    dt_check = parse_dt(l_next)
                    if dt_check:
                        date = dt_check
                    mqds_m = re.search(r'\$?([\d,]+)\s*mqds', l_next, re.IGNORECASE)
                    if mqds_m:
                        mqds = int(mqds_m.group(1).replace(",", ""))
                    next_idx += 1
                    
                if date and mqds:
                    activities.append({
                        "type": "card_headstart",
                        "card_name": card_name,
                        "date": date,
                        "mqds": mqds
                    })
                    
            # 3. Match Card Boost
            elif "mqd boost" in line.lower():
                next_idx = idx + 1
                date = None
                mqds = None
                card_name = line.strip()
                
                while next_idx < len(lines):
                    l_next = lines[next_idx].strip()
                    if not l_next:
                        next_idx += 1
                        continue
                    if should_stop(l_next):
                        break
                    dt_check = parse_dt(l_next)
                    if dt_check:
                        date = dt_check
                    mqds_m = re.search(r'\$?([\d,]+)\s*mqds', l_next, re.IGNORECASE)
                    if mqds_m:
                        mqds = int(mqds_m.group(1).replace(",", ""))
                    next_idx += 1
                    
                if date and mqds:
                    activities.append({
                        "type": "card_boost",
                        "card_name": card_name,
                        "date": date,
                        "mqds": mqds
                    })
                    
            idx += 1
            
        return activities

    def ingest_pdf_activities(self, pdf_path: Path) -> Dict[str, int]:
        """Ingests all parsed PDF flight and card MQD transactions into travel memories."""
        parsed_activities = self.parse_pdf_mqd_activities(pdf_path)
        existing_memories = self.manager.search_memories(category="travel")
        
        enriched_count = 0
        added_count = 0
        
        for act in parsed_activities:
            if act["type"] == "flight":
                # Check for existing flight to enrich
                route = act["route"]
                date = act["date"]
                matched_mem = None
                for mem in existing_memories:
                    mem_meta = mem.get("metadata", {})
                    dest = mem_meta.get("destination", "").lower()
                    start_date = mem_meta.get("start_date", "")
                    
                    route_parts = route.lower().split(" to ")
                    route_match = (route_parts[0] in dest or route_parts[1] in dest or dest in route.lower())
                    date_match = (start_date == date)
                    
                    if route_match and date_match:
                        matched_mem = mem
                        break
                        
                if matched_mem:
                    # Enrich existing
                    mem_id = matched_mem["id"]
                    metadata = matched_mem.get("metadata", {})
                    if "parsed_data" not in metadata:
                        metadata["parsed_data"] = {}
                    
                    # Merge keys
                    metadata["parsed_data"]["miles"] = act.get("miles")
                    metadata["parsed_data"]["mqds"] = act.get("mqds")
                    metadata["parsed_data"]["ticket_number"] = act.get("ticket_number")
                    metadata["parsed_data"]["status"] = act.get("status")
                    
                    # Update database directly
                    import sqlite3
                    conn = sqlite3.connect(self.manager.db_path)
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE memories SET metadata = ? WHERE id = ?",
                        (json.dumps(metadata), mem_id)
                    )
                    conn.commit()
                    conn.close()
                    enriched_count += 1
                else:
                    # Add new historical flight
                    carrier = act["carrier"]
                    flight_num = act["flight_number"]
                    miles_str = f"{act['miles']:,} Miles" if act.get("miles") else "N/A Miles"
                    mqds_str = f"${act['mqds']:,} MQDs" if act.get("mqds") else "N/A MQDs"
                    ticket_str = f"Ticket: {act['ticket_number']}" if act.get("ticket_number") else "No Ticket #"
                    status = act["status"]
                    
                    content = (
                        f"Historical Flight: {route}\n"
                        f"Date: {date}\n"
                        f"Carrier: {carrier} ({flight_num or 'N/A'})\n"
                        f"Status: {status}\n"
                        f"Metrics: {miles_str}, {mqds_str}\n"
                        f"{ticket_str}"
                    )
                    
                    new_meta = {
                        "source_file": pdf_path.name,
                        "type": "historical_flight",
                        "destination": route,
                        "start_date": date,
                        "end_date": date,
                        "activities": [
                            "Explore local neighborhood food markets away from city centers.",
                            "Seek out family-owned, long-running street vendors and tavernas.",
                            "Avoid main tourist plazas and restaurants with English-only photo menus.",
                            "Get lost in residential quarters and talk to neighborhood residents."
                        ],
                        "packing_list": [],
                        "parsed_data": act
                    }
                    self.manager.add_memory(
                        category="travel",
                        content=content,
                        metadata=new_meta
                    )
                    added_count += 1
            else:
                # Card Headstart or Card Boost
                card_name = act["card_name"]
                date = act["date"]
                mqds = act["mqds"]
                act_type = act["type"]
                
                # Check duplicate card boost/headstart
                exists = False
                for mem in existing_memories:
                    mem_meta = mem.get("metadata", {})
                    if (mem_meta.get("type") == act_type and 
                        mem_meta.get("card_name") == card_name and 
                        mem_meta.get("start_date") == date and 
                        mem_meta.get("mqds") == mqds):
                        exists = True
                        break
                        
                if not exists:
                    type_title = "Card Headstart" if act_type == "card_headstart" else "Card Boost"
                    content = f"{type_title}: {card_name}\nDate: {date}\nMQDs: ${mqds:,}"
                    new_meta = {
                        "source_file": pdf_path.name,
                        "type": act_type,
                        "card_name": card_name,
                        "start_date": date,
                        "end_date": date,
                        "mqds": mqds
                    }
                    self.manager.add_memory(
                        category="travel",
                        content=content,
                        metadata=new_meta
                    )
                    added_count += 1
                    
        return {"enriched": enriched_count, "added": added_count}

    def get_ytd_mqd_summary(self, year: Optional[int] = None) -> Dict[str, Any]:
        """Summarizes year-to-date MQD status metrics and progress toward tiers."""
        if year is None:
            year = datetime.date.today().year
            
        mems = self.manager.search_memories(category="travel")
        
        flights_mqds = 0
        headstart_mqds = 0
        boost_mqds = 0
        other_mqds = 0
        
        flights_list = []
        card_items = []
        
        for mem in mems:
            meta = mem.get("metadata", {})
            start_date = meta.get("start_date", "")
            if not start_date or not start_date.startswith(str(year)):
                continue
                
            mem_type = meta.get("type", "")
            parsed_data = meta.get("parsed_data", {})
            
            # Extract MQDs
            val = 0
            if "mqds" in meta:
                val = int(meta["mqds"])
            elif "mqds" in parsed_data:
                val = int(parsed_data["mqds"]) if parsed_data.get("mqds") is not None else 0
            else:
                mqd_match = re.search(r'\$?([\d,]+)\s*mqds', mem.get("content", ""), re.IGNORECASE)
                if mqd_match:
                    val = int(mqd_match.group(1).replace(",", ""))
                    
            if val <= 0:
                continue
                
            if mem_type == "card_headstart":
                headstart_mqds += val
                card_items.append({"type": "Headstart", "name": meta.get("card_name"), "date": start_date, "mqds": val})
            elif mem_type == "card_boost":
                boost_mqds += val
                card_items.append({"type": "Spend Boost", "name": meta.get("card_name"), "date": start_date, "mqds": val})
            elif mem_type in ["historical_flight", "travel_confirmation"] or parsed_data.get("type") == "flight":
                flights_mqds += val
                carrier = parsed_data.get("carrier") or meta.get("carrier") or "Delta Airlines"
                fl_num = parsed_data.get("flight_number") or meta.get("flight_number") or "DL"
                flights_list.append({
                    "route": meta.get("destination") or parsed_data.get("destination") or "Unknown Flight",
                    "date": start_date,
                    "carrier": carrier,
                    "flight_number": fl_num,
                    "mqds": val,
                    "status": parsed_data.get("status") or "Posted"
                })
            else:
                other_mqds += val
                
        total_mqds = flights_mqds + headstart_mqds + boost_mqds + other_mqds
        
        # Thresholds
        tiers = {
            "Silver": 5000,
            "Gold": 10000,
            "Platinum": 15000,
            "Diamond": 28000
        }
        
        progress = {}
        for name, threshold in tiers.items():
            pct = (total_mqds / threshold) * 100
            progress[name] = {
                "threshold": threshold,
                "percentage": min(100.0, pct),
                "needed": max(0, threshold - total_mqds)
            }
            
        # Pacing calculations
        today = datetime.date.today()
        end_of_year = datetime.date(year, 12, 31)
        days_left = max(1, (end_of_year - today).days)
        
        diamond_needed = progress["Diamond"]["needed"]
        daily_pace_required = diamond_needed / days_left
        
        return {
            "year": year,
            "total_mqds": total_mqds,
            "breakdown": {
                "flights": flights_mqds,
                "headstarts": headstart_mqds,
                "boosts": boost_mqds,
                "other": other_mqds
            },
            "flights": sorted(flights_list, key=lambda x: x["date"]),
            "cards": sorted(card_items, key=lambda x: x["date"]),
            "tiers": progress,
            "days_remaining": days_left,
            "daily_pace_required": daily_pace_required
        }

    def calculate_partner_mqd(
        self,
        carrier: str,
        distance: float,
        fare_class: str,
        ticket_price: float
    ) -> Dict[str, Any]:
        """Calculates expected MQD earnings and MQD-to-Cost ratio for flights."""
        carrier_lower = carrier.lower()
        fare_class_upper = fare_class.upper().strip()
        
        is_partner = False
        partner_partners = ["air france", "klm", "virgin atlantic", "aeromexico", "korean air", "af", "kl", "vs", "am", "ke"]
        for p in partner_partners:
            if p in carrier_lower:
                is_partner = True
                break
                
        mqds = 0
        method = ""
        
        if is_partner:
            method = "Distance-based Partner Earning"
            if fare_class_upper in ["J", "C", "D", "I", "Z"]: # Business
                pct = 0.40
            elif fare_class_upper in ["W", "S", "A"]: # Premium Econ
                pct = 0.30
            elif fare_class_upper in ["Y", "B", "M"]: # Full Econ
                pct = 0.25
            elif fare_class_upper in ["U", "K", "H", "L", "Q", "T"]: # Mid Econ
                pct = 0.20
            elif fare_class_upper in ["V", "X", "N", "R", "G"]: # Discount Econ
                pct = 0.10
            else:
                pct = 0.10 # Fallback
                
            mqds = int(distance * pct)
        else:
            method = "Delta Revenue-based Earning"
            base_fare = ticket_price * 0.90
            mqds = int(base_fare)
            
        ratio = mqds / max(1.0, ticket_price)
        
        return {
            "carrier": carrier.title(),
            "distance": distance,
            "fare_class": fare_class_upper,
            "ticket_price": ticket_price,
            "mqds_earned": mqds,
            "mqd_ratio": ratio,
            "method": method,
            "is_optimized": ratio >= 1.0
        }
