import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from core.memory.manager import MemoryManager

logger = logging.getLogger("mithrandir")

class ProjectsDomain:
    """Domain module for tracking AI sprint backlogs and project tasks."""
    def __init__(self, db_path: Optional[Path] = None):
        self.manager = MemoryManager(db_path)

    def add_project_task(
        self,
        project_name: str,
        task_name: str,
        complexity: str,
        description: str,
        status: str
    ) -> int:
        """Logs a project/sprint backlog task in the durable memory layer."""
        if not project_name or not task_name:
            raise ValueError("Project name and task name are required.")
        
        content = (
            f"Project: {project_name} | Task: {task_name}\n"
            f"Complexity: {complexity} | Status: {status}\n"
            f"Description: {description}"
        )
        
        metadata = {
            "project_name": project_name,
            "task_name": task_name,
            "complexity": complexity,
            "description": description,
            "status": status
        }
        
        return self.manager.add_memory(
            category="projects",
            content=content,
            metadata=metadata
        )

    def list_project_tasks(self) -> List[Dict[str, Any]]:
        """Lists all project backlog tasks."""
        return self.manager.search_memories(category="projects")
