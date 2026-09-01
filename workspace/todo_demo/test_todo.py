import os
import json
import unittest
import tempfile

from todo import TodoList


class TestTodoList(unittest.TestCase):

    def setUp(self):
        self.todo = TodoList()

    # --- add ---
    def test_add_task(self):
        self.todo.add("buy milk")
        tasks = self.todo.list_tasks()
        self.assertIn("buy milk", tasks)
        self.assertFalse(tasks["buy milk"])

    def test_add_multiple_tasks(self):
        self.todo.add("task1")
        self.todo.add("task2")
        tasks = self.todo.list_tasks()
        self.assertEqual(len(tasks), 2)

    # --- remove ---
    def test_remove_task(self):
        self.todo.add("buy milk")
        self.todo.remove("buy milk")
        tasks = self.todo.list_tasks()
        self.assertNotIn("buy milk", tasks)

    def test_remove_nonexistent_task(self):
        with self.assertRaises(ValueError):
            self.todo.remove("nonexistent")

    # --- complete ---
    def test_complete_task(self):
        self.todo.add("buy milk")
        self.todo.complete("buy milk")
        tasks = self.todo.list_tasks()
        self.assertTrue(tasks["buy milk"])

    def test_complete_nonexistent_task(self):
        with self.assertRaises(ValueError):
            self.todo.complete("nonexistent")

    # --- empty task ---
    def test_add_empty_string(self):
        with self.assertRaises(ValueError):
            self.todo.add("")

    def test_add_whitespace_only(self):
        with self.assertRaises(ValueError):
            self.todo.add("   ")

    # --- save / load ---
    def test_save_and_load(self):
        self.todo.add("task1")
        self.todo.add("task2")
        self.todo.complete("task2")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name

        try:
            self.todo.save(path)

            new_todo = TodoList()
            new_todo.load(path)
            tasks = new_todo.list_tasks()
            self.assertEqual(tasks, {"task1": False, "task2": True})
        finally:
            os.unlink(path)

    def test_load_nonexistent_file(self):
        todo = TodoList()
        todo.load("/tmp/nonexistent_todo_file_12345.json")
        self.assertEqual(todo.list_tasks(), {})


if __name__ == "__main__":
    unittest.main()
