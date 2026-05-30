import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from core.memory.manager import MemoryManager

logger = logging.getLogger("mithrandir")

class PersonalDomain:
    """Domain module handling personal journal entries.
    
    Journal entries are encrypted on disk via the MemoryManager's Fernet encryptor,
    and decrypted in-memory during search or listing.
    """
    def __init__(self, db_path: Optional[Path] = None):
        self.manager = MemoryManager(db_path)

    def add_journal_entry(self, content: str, mood_score: int) -> int:
        """Adds a journal entry. In-memory the review is decrypted/plain, but it is stored encrypted."""
        if not (1 <= mood_score <= 10):
            raise ValueError("Mood score must be an integer between 1 and 10.")
        
        metadata = {"mood_score": mood_score}
        # The manager.add_memory automatically handles the Fernet encryption for category 'journal'
        memory_id = self.manager.add_memory(
            category="journal",
            content=content,
            metadata=metadata
        )
        logger.info(f"Journal entry stored with memory ID {memory_id}.")
        return memory_id

    def list_journal_entries(self, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves and decrypts journal entries. Optionally filters by a search query."""
        # search_memories automatically decrypts journal entries in memory
        return self.manager.search_memories(query=query, category="journal")
