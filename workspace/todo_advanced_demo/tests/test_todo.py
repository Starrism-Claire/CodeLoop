"""Tests for the Todo application."""

import json
import os
import tempfile
import unittest
from datetime import datetime, date

from todo_app.models import Task, Priority, Status
from todo_app.storage import Storage
from todo_app.manager import TodoManager
from todo_app.utils import parse_date, format_task


class TestTaskModel(unittest.TestCase):
    """Tests for the Task data model."""

    def test_create_task_defaults(self):
        task = Task(title="Test task")
        self.assertEqual(task.title, "Test task")
        self.assertEqual(task.description, "")
        self.assertEqual(task.priority, Priority.MEDIUM)
        self.assertEqual(task.status, Status.PENDING)
        self.assertIsNone(task.due_date)
        self.assertEqual(task.tags, [])
        self.assertEqual(task.project, "")
        self.assertIsNotNone(task.id)
        self.assertIsNotNone(task.created_at)

    def test_create_task_with_all_fields(self):
        task = Task(
            title="Important task",
            description="Do this now",
            priority=Priority.HIGH,
            due_date=date(2025, 12, 31),
            tags=["urgent", "work"],
            project="ProjectX",
        )
        self.assertEqual(task.title, "Important task")
        self.assertEqual(task.description, "Do this now")
        self.assertEqual(task.priority, Priority.HIGH)
        self.assertEqual(task.due_date, date(2025, 12, 31))
        self.assertEqual(task.tags, ["urgent", "work"])
        self.assertEqual(task.project, "ProjectX")

    def test_task_to_dict_and_from_dict(self):
        task = Task(
            title="Roundtrip",
            description="Test serialization",
            priority=Priority.LOW,
            status=Status.IN_PROGRESS,
            due_date=date(2025, 6, 15),
            tags=["test"],
            project="ProjA",
        )
        d = task.to_dict()
        restored = Task.from_dict(d)
        self.assertEqual(restored.id, task.id)
        self.assertEqual(restored.title, task.title)
        self.assertEqual(restored.description, task.description)
        self.assertEqual(restored.priority, task.priority)
        self.assertEqual(restored.status, task.status)
        self.assertEqual(restored.due_date, task.due_date)
        self.assertEqual(restored.tags, task.tags)
        self.assertEqual(restored.project, task.project)

    def test_task_empty_title_raises(self):
        with self.assertRaises(ValueError):
            Task(title="")

    def test_task_title_whitespace_only_raises(self):
        with self.assertRaises(ValueError):
            Task(title="   ")


class TestStorage(unittest.TestCase):
    """Tests for JSON file storage."""

    def setUp(self):
        self.tmpfile = tempfile.NamedTemporaryFile(
            suffix=".json", delete=False
        )
        self.tmpfile.close()
        self.storage = Storage(self.tmpfile.name)

    def tearDown(self):
        os.unlink(self.tmpfile.name)

    def test_save_and_load(self):
        tasks = [Task(title="A"), Task(title="B")]
        self.storage.save(tasks)
        loaded = self.storage.load()
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0].title, "A")
        self.assertEqual(loaded[1].title, "B")

    def test_load_empty_file(self):
        loaded = self.storage.load()
        self.assertEqual(loaded, [])

    def test_load_nonexistent_file(self):
        os.unlink(self.tmpfile.name)
        storage = Storage(self.tmpfile.name)
        loaded = storage.load()
        self.assertEqual(loaded, [])


class TestTodoManager(unittest.TestCase):
    """Tests for the TodoManager business logic."""

    def setUp(self):
        self.tmpfile = tempfile.NamedTemporaryFile(
            suffix=".json", delete=False
        )
        self.tmpfile.close()
        self.manager = TodoManager(self.tmpfile.name)

    def tearDown(self):
        os.unlink(self.tmpfile.name)

    def test_add_task(self):
        task = self.manager.add_task("My task")
        self.assertEqual(task.title, "My task")
        self.assertEqual(len(self.manager.tasks), 1)

    def test_add_task_empty_title_raises(self):
        with self.assertRaises(ValueError):
            self.manager.add_task("")

    def test_get_task(self):
        task = self.manager.add_task("Find me")
        found = self.manager.get_task(task.id)
        self.assertEqual(found.id, task.id)

    def test_get_task_not_found(self):
        with self.assertRaises(KeyError):
            self.manager.get_task("nonexistent-id")

    def test_update_task(self):
        task = self.manager.add_task("Original")
        self.manager.update_task(task.id, title="Updated", priority=Priority.HIGH)
        updated = self.manager.get_task(task.id)
        self.assertEqual(updated.title, "Updated")
        self.assertEqual(updated.priority, Priority.HIGH)

    def test_update_nonexistent_raises(self):
        with self.assertRaises(KeyError):
            self.manager.update_task("bad-id", title="Nope")

    def test_complete_task(self):
        task = self.manager.add_task("Finish me")
        self.manager.complete_task(task.id)
        completed = self.manager.get_task(task.id)
        self.assertEqual(completed.status, Status.COMPLETED)

    def test_complete_nonexistent_raises(self):
        with self.assertRaises(KeyError):
            self.manager.complete_task("bad-id")

    def test_delete_task(self):
        task = self.manager.add_task("Delete me")
        self.manager.delete_task(task.id)
        self.assertEqual(len(self.manager.tasks), 0)

    def test_delete_nonexistent_raises(self):
        with self.assertRaises(KeyError):
            self.manager.delete_task("bad-id")

    def test_filter_by_project(self):
        self.manager.add_task("T1", project="A")
        self.manager.add_task("T2", project="B")
        self.manager.add_task("T3", project="A")
        result = self.manager.filter_tasks(project="A")
        self.assertEqual(len(result), 2)
        self.assertTrue(all(t.project == "A" for t in result))

    def test_filter_by_status(self):
        t1 = self.manager.add_task("T1")
        t2 = self.manager.add_task("T2")
        self.manager.complete_task(t1.id)
        result = self.manager.filter_tasks(status=Status.PENDING)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, t2.id)

    def test_filter_by_priority(self):
        self.manager.add_task("T1", priority=Priority.HIGH)
        self.manager.add_task("T2", priority=Priority.LOW)
        result = self.manager.filter_tasks(priority=Priority.HIGH)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].priority, Priority.HIGH)

    def test_filter_by_tag(self):
        self.manager.add_task("T1", tags=["python", "web"])
        self.manager.add_task("T2", tags=["python"])
        self.manager.add_task("T3", tags=["java"])
        result = self.manager.filter_tasks(tags=["python"])
        self.assertEqual(len(result), 2)

    def test_sort_by_due_date(self):
        self.manager.add_task("Later", due_date=date(2025, 12, 1))
        self.manager.add_task("Sooner", due_date=date(2025, 6, 1))
        self.manager.add_task("No date")
        result = self.manager.filter_tasks(sort_by="due_date")
        # Tasks with due dates should come first, sorted ascending
        self.assertEqual(result[0].title, "Sooner")
        self.assertEqual(result[1].title, "Later")
        self.assertEqual(result[2].title, "No date")

    def test_sort_by_priority(self):
        self.manager.add_task("Low", priority=Priority.LOW)
        self.manager.add_task("High", priority=Priority.HIGH)
        self.manager.add_task("Med", priority=Priority.MEDIUM)
        result = self.manager.filter_tasks(sort_by="priority")
        priorities = [t.priority for t in result]
        self.assertEqual(priorities, [Priority.HIGH, Priority.MEDIUM, Priority.LOW])

    def test_persistence(self):
        self.manager.add_task("Persistent task", project="P1")
        # Create a new manager with the same file
        manager2 = TodoManager(self.tmpfile.name)
        self.assertEqual(len(manager2.tasks), 1)
        self.assertEqual(manager2.tasks[0].title, "Persistent task")
        self.assertEqual(manager2.tasks[0].project, "P1")


class TestUtils(unittest.TestCase):
    """Tests for utility functions."""

    def test_parse_date_valid(self):
        d = parse_date("2025-12-31")
        self.assertEqual(d, date(2025, 12, 31))

    def test_parse_date_invalid(self):
        self.assertIsNone(parse_date("not-a-date"))

    def test_parse_date_empty(self):
        self.assertIsNone(parse_date(""))

    def test_format_task_contains_title(self):
        task = Task(title="Formatted task")
        output = format_task(task)
        self.assertIn("Formatted task", output)


if __name__ == "__main__":
    unittest.main()
