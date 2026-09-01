"""Storage layer for persisting tasks to disk."""

import json
import os
from typing import List, Optional
from .models import Task


DEFAULT_STORAGE_PATH = os.path.expanduser("~/.todo_app/tasks.json")


class Storage:
    """Handles reading and writing tasks to a JSON file."""

    def __init__(self, filepath: Optional[str] = None):
        self.filepath = filepath or DEFAULT_STORAGE_PATH

    def _ensure_directory(self) -> None:
        """Ensure the directory for the storage file exists."""
        directory = os.path.dirname(self.filepath)
        if directory:
            os.makedirs(directory, exist_ok=True)

    def load_tasks(self) -> List[Task]:
        """Load all tasks from the storage file."""
        if not os.path.exists(self.filepath):
            return []
        
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                return []
            
            tasks = []
            for item in data:
                try:
                    tasks.append(Task.from_dict(item))
                except (KeyError, ValueError) as e:
                    # Skip corrupted entries but could log warning
                    continue
            return tasks
        except (json.JSONDecodeError, IOError):
            return []

    def save_tasks(self, tasks: List[Task]) -> None:
        """Save all tasks to the storage file."""
        self._ensure_directory()
        data = [task.to_dict() for task in tasks]
        
        # Write to temp file first, then rename for atomicity
        temp_path = self.filepath + ".tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, self.filepath)
        except IOError as e:
            # Clean up temp file on failure
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise IOError(f"Failed to save tasks: {e}")

    def clear(self) -> None:
        """Remove the storage file."""
        if os.path.exists(self.filepath):
            os.remove(self.filepath)
