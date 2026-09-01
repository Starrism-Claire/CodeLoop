"""Business logic for task management."""

from typing import List, Optional
from .models import Task, Priority, Status
from .storage import Storage


class TaskManager:
    """Manages task operations: CRUD, filtering, and sorting."""

    def __init__(self, storage: Storage):
        self.storage = storage
        self._tasks: List[Task] = []
        self._load()

    def _load(self) -> None:
        """Load tasks from storage."""
        self._tasks = self.storage.load_tasks()

    def _save(self) -> None:
        """Persist current tasks to storage."""
        self.storage.save_tasks(self._tasks)

    def _find_task(self, task_id: str) -> Optional[Task]:
        """Find a task by its ID."""
        for task in self._tasks:
            if task.id == task_id:
                return task
        return None

    # --- CRUD Operations ---

    def add_task(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
        due_date: Optional[str] = None,
        tags: Optional[List[str]] = None,
        project: str = "default",
    ) -> Task:
        """Create and add a new task."""
        if not title or not title.strip():
            raise ValueError("Task title cannot be empty.")

        task = Task(
            title=title.strip(),
            description=description.strip() if description else "",
            priority=Priority.from_string(priority),
            due_date=due_date,
            tags=[t.strip() for t in tags if t.strip()] if tags else [],
            project=project.strip() if project else "default",
        )
        self._tasks.append(task)
        self._save()
        return task

    def get_task(self, task_id: str) -> Task:
        """Get a task by ID."""
        task = self._find_task(task_id)
        if task is None:
            raise ValueError(f"Task with ID '{task_id}' not found.")
        return task

    def update_task(self, task_id: str, **kwargs) -> Task:
        """Update an existing task's fields."""
        task = self._find_task(task_id)
        if task is None:
            raise ValueError(f"Task with ID '{task_id}' not found.")

        if "title" in kwargs:
            new_title = kwargs["title"].strip()
            if not new_title:
                raise ValueError("Task title cannot be empty.")
            task.title = new_title

        if "description" in kwargs:
            task.description = kwargs["description"].strip()

        if "priority" in kwargs:
            task.priority = Priority.from_string(kwargs["priority"])

        if "due_date" in kwargs:
            task.due_date = kwargs["due_date"]

        if "tags" in kwargs:
            task.tags = [t.strip() for t in kwargs["tags"] if t.strip()]

        if "project" in kwargs:
            task.project = kwargs["project"].strip() if kwargs["project"] else "default"

        if "status" in kwargs:
            task.status = Status.from_string(kwargs["status"])

        from datetime import datetime
        task.updated_at = datetime.now().isoformat()
        self._save()
        return task

    def complete_task(self, task_id: str) -> Task:
        """Mark a task as completed."""
        task = self._find_task(task_id)
        if task is None:
            raise ValueError(f"Task with ID '{task_id}' not found.")
        task.mark_completed()
        self._save()
        return task

    def delete_task(self, task_id: str) -> Task:
        """Delete a task by ID."""
        task = self._find_task(task_id)
        if task is None:
            raise ValueError(f"Task with ID '{task_id}' not found.")
        self._tasks.remove(task)
        self._save()
        return task

    # --- Listing and Filtering ---

    def list_tasks(
        self,
        project: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        tag: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> List[Task]:
        """List tasks with optional filtering and sorting."""
        result = list(self._tasks)

        # Apply filters
        if project:
            result = [t for t in result if t.project.lower() == project.lower()]

        if status:
            status_enum = Status.from_string(status)
            result = [t for t in result if t.status == status_enum]

        if priority:
            priority_enum = Priority.from_string(priority)
            result = [t for t in result if t.priority == priority_enum]

        if tag:
            tag_lower = tag.lower()
            result = [t for t in result if any(t_lower == tag_lower for t_lower in [x.lower() for x in t.tags])]

        # Apply sorting
        if sort_by:
            result = self._sort_tasks(result, sort_by)

        return result

    def _sort_tasks(self, tasks: List[Task], sort_by: str) -> List[Task]:
        """Sort tasks by the given criteria."""
        sort_by = sort_by.lower().strip()

        if sort_by == "due_date":
            # Tasks without due_date go to the end
            return sorted(
                tasks,
                key=lambda t: (t.due_date is None, t.due_date or "9999-12-31"),
            )
        elif sort_by == "due_date_desc":
            return sorted(
                tasks,
                key=lambda t: (t.due_date is None, t.due_date or ""),
                reverse=True,
            )
        elif sort_by == "priority":
            priority_order = {Priority.URGENT: 0, Priority.HIGH: 1, Priority.MEDIUM: 2, Priority.LOW: 3}
            return sorted(tasks, key=lambda t: priority_order.get(t.priority, 99))
        elif sort_by == "priority_desc":
            priority_order = {Priority.URGENT: 0, Priority.HIGH: 1, Priority.MEDIUM: 2, Priority.LOW: 3}
            return sorted(tasks, key=lambda t: priority_order.get(t.priority, 99), reverse=True)
        elif sort_by == "created":
            return sorted(tasks, key=lambda t: t.created_at)
        elif sort_by == "created_desc":
            return sorted(tasks, key=lambda t: t.created_at, reverse=True)
        else:
            raise ValueError(f"Invalid sort criteria: '{sort_by}'. Choose from: due_date, priority, created (with optional _desc suffix)")

    # --- Statistics ---

    def get_stats(self) -> dict:
        """Get task statistics."""
        total = len(self._tasks)
        by_status = {}
        for s in Status:
            by_status[s.value] = len([t for t in self._tasks if t.status == s])
        
        by_priority = {}
        for p in Priority:
            by_priority[p.value] = len([t for t in self._tasks if t.priority == p])

        projects = set(t.project for t in self._tasks)
        overdue = len([t for t in self._tasks if t.is_overdue()])

        return {
            "total": total,
            "by_status": by_status,
            "by_priority": by_priority,
            "projects": sorted(projects),
            "overdue": overdue,
        }

    def get_projects(self) -> List[str]:
        """Get list of all project names."""
        return sorted(set(t.project for t in self._tasks))

    def get_all_tags(self) -> List[str]:
        """Get list of all unique tags."""
        tags = set()
        for t in self._tasks:
            tags.update(t.tags)
        return sorted(tags)
