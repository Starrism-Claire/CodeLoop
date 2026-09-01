"""Utility functions for input validation and formatting."""

from datetime import datetime
from typing import Optional


def validate_date(date_str: str) -> str:
    """Validate and normalize a date string to YYYY-MM-DD format.
    
    Accepts: YYYY-MM-DD, YYYY/MM/DD, DD-MM-YYYY, DD/MM/YYYY
    Returns: normalized YYYY-MM-DD string
    Raises: ValueError if the date is invalid
    """
    if not date_str or not date_str.strip():
        raise ValueError("Date cannot be empty.")

    date_str = date_str.strip()
    
    formats = [
        ("%Y-%m-%d", "-"),
        ("%Y/%m/%d", "/"),
        ("%d-%m-%Y", "-"),
        ("%d/%m/%Y", "/"),
    ]

    for fmt, sep in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    raise ValueError(f"Invalid date format: '{date_str}'. Use YYYY-MM-DD format.")


def validate_priority(priority_str: str) -> str:
    """Validate priority string and return normalized value."""
    valid = ["low", "medium", "high", "urgent"]
    normalized = priority_str.lower().strip()
    if normalized not in valid:
        raise ValueError(f"Invalid priority: '{priority_str}'. Choose from: {', '.join(valid)}")
    return normalized


def validate_status(status_str: str) -> str:
    """Validate status string and return normalized value."""
    valid = ["pending", "in_progress", "completed"]
    normalized = status_str.lower().strip().replace("-", "_").replace(" ", "_")
    if normalized not in valid:
        raise ValueError(f"Invalid status: '{status_str}'. Choose from: {', '.join(valid)}")
    return normalized


def parse_tags(tags_str: Optional[str]) -> list:
    """Parse a comma-separated tags string into a list."""
    if not tags_str:
        return []
    return [t.strip() for t in tags_str.split(",") if t.strip()]


def format_task_table(tasks: list) -> str:
    """Format tasks into a readable table-like output."""
    if not tasks:
        return "No tasks found."

    lines = []
    lines.append(f"{'ID':<10} {'Status':<13} {'Priority':<10} {'Due':<12} {'Project':<15} {'Title'}")
    lines.append("-" * 80)

    for task in tasks:
        status_icon = {"pending": "○", "in_progress": "◐", "completed": "●"}.get(task.status.value, "○")
        due = task.due_date or "-"
        overdue_mark = " !" if task.is_overdue() else ""
        
        line = f"{task.id:<10} {status_icon}{task.status.value:<12} {task.priority.value:<10} {due}{overdue_mark:<10} {task.project:<15} {task.title}"
        lines.append(line)
        
        if task.tags:
            lines.append(f"{'':10} Tags: {', '.join(task.tags)}")

    lines.append(f"\nTotal: {len(tasks)} task(s)")
    return "\n".join(lines)
