import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from core.memory.manager import MemoryManager

logger = logging.getLogger("mithrandir")

class TravelDomain:
    """Domain module for tracking travel itineraries and packing lists."""
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
