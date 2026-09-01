"""Data models for the Todo application."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, List
import uuid


class Priority(Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

    @classmethod
    def from_string(cls, value: str) -> "Priority":
        """Create Priority from string, case-insensitive."""
        value_lower = value.lower().strip()
        for p in cls:
            if p.value == value_lower:
                return p
        raise ValueError(f"Invalid priority: '{value}'. Choose from: {', '.join(p.value for p in cls)}")


class Status(Enum):
    """Task status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

    @classmethod
    def from_string(cls, value: str) -> "Status":
        """Create Status from string, case-insensitive."""
        value_lower = value.lower().strip().replace("-", "_").replace(" ", "_")
        for s in cls:
            if s.value == value_lower:
                return s
        raise ValueError(f"Invalid status: '{value}'. Choose from: {', '.join(s.value for s in cls)}")


@dataclass
class Task:
    """Represents a single todo task."""
    title: str
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    priority: Priority = Priority.MEDIUM
    status: Status = Status.PENDING
    due_date: Optional[str] = None  # Stored as ISO format string YYYY-MM-DD
    tags: List[str] = field(default_factory=list)
    project: str = "default"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        """Convert task to dictionary for serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "due_date": self.due_date,
            "tags": self.tags,
            "project": self.project,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """Create a Task from a dictionary."""
        return cls(
            id=data["id"],
            title=data["title"],
            description=data.get("description", ""),
            priority=Priority(data.get("priority", "medium")),
            status=Status(data.get("status", "pending")),
            due_date=data.get("due_date"),
            tags=data.get("tags", []),
            project=data.get("project", "default"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
        )

    def mark_completed(self) -> None:
        """Mark task as completed."""
        self.status = Status.COMPLETED
        self.updated_at = datetime.now().isoformat()

    def mark_in_progress(self) -> None:
        """Mark task as in progress."""
        self.status = Status.IN_PROGRESS
        self.updated_at = datetime.now().isoformat()

    def is_overdue(self) -> bool:
        """Check if the task is overdue."""
        if not self.due_date or self.status == Status.COMPLETED:
            return False
        try:
            due = datetime.strptime(self.due_date, "%Y-%m-%d")
            return due < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        except ValueError:
            return False

    def __str__(self) -> str:
        """String representation of the task."""
        status_icon = {"pending": "○", "in_progress": "◐", "completed": "●"}.get(self.status.value, "○")
        priority_icon = {"low": "▽", "medium": "◇", "high": "△", "urgent": "!"}.get(self.priority.value, "◇")
        
        parts = [f"[{self.id}] {status_icon}{priority_icon} {self.title}"]
        parts.append(f"  Status: {self.status.value} | Priority: {self.priority.value} | Project: {self.project}")
        
        if self.description:
            parts.append(f"  Description: {self.description}")
        if self.due_date:
            overdue_str = " (OVERDUE!)" if self.is_overdue() else ""
            parts.append(f"  Due: {self.due_date}{overdue_str}")
        if self.tags:
            parts.append(f"  Tags: {', '.join(self.tags)}")
        
        return "\n".join(parts)
