import json
import os


class TodoList:
    def __init__(self):
        self._tasks = {}  # task_name -> bool (completed)

    def add(self, task):
        if not task or not task.strip():
            raise ValueError("Task cannot be empty")
        if task not in self._tasks:
            self._tasks[task] = False

    def remove(self, task):
        if task not in self._tasks:
            raise ValueError(f"Task '{task}' not found")
        del self._tasks[task]

    def complete(self, task):
        if task not in self._tasks:
            raise ValueError(f"Task '{task}' not found")
        self._tasks[task] = True

    def list_tasks(self):
        return dict(self._tasks)

    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._tasks, f, ensure_ascii=False, indent=2)

    def load(self, path):
        if not os.path.exists(path):
            self._tasks = {}
            return
        with open(path, "r", encoding="utf-8") as f:
            self._tasks = json.load(f)
