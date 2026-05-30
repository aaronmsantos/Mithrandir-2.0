import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from core.memory.manager import MemoryManager

logger = logging.getLogger("mithrandir")

class WorkDomain:
    """Domain module for tracking weekly work tasks and deliverables."""
    def __init__(self, db_path: Optional[Path] = None):
        self.manager = MemoryManager(db_path)

    def add_task(
        self,
        task_name: str,
        description: str,
        status: str,
        due_date: str,
        priority: str
    ) -> int:
        """Logs a work task in the durable memory layer."""
        if not task_name:
            raise ValueError("Task name is required.")
        
        content = (
            f"Work Task: {task_name} (Priority: {priority}, Status: {status})\n"
            f"Description: {description}\n"
            f"Due Date: {due_date}"
        )
        
        metadata = {
            "task_name": task_name,
            "description": description,
            "status": status,
            "due_date": due_date,
            "priority": priority
        }
        
        return self.manager.add_memory(
            category="work",
            content=content,
            metadata=metadata
        )

    def list_tasks(self) -> List[Dict[str, Any]]:
        """Lists all work tasks."""
        return self.manager.search_memories(category="work")
