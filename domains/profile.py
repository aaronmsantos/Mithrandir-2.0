import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from core.memory.manager import MemoryManager

logger = logging.getLogger("mithrandir")

class ProfileDomain:
    """Domain module for managing the operator's professional history, resume, and skills."""
    def __init__(self, db_path: Optional[Path] = None):
        self.manager = MemoryManager(db_path)

    def import_profile(self, file_path: Path) -> int:
        """Reads a professional history text file and stores it in the memory layer."""
        if not file_path.exists():
            raise FileNotFoundError(f"Profile file not found at: {file_path}")
            
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            
        if not content:
            raise ValueError("Profile file is empty.")

        # Save to memories
        metadata = {
            "source_file": file_path.name,
            "type": "professional_history"
        }
        
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
        # Filter for professional history type
        history_memories = [
            m for m in memories 
            if m.get("metadata", {}).get("type") == "professional_history"
        ]
        if history_memories:
            # They are already sorted chronologically descending in search_memories
            return history_memories[0]
        return None
