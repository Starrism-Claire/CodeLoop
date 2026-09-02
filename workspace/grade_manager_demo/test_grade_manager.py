"""Unit tests for grade management system."""

import tempfile
import unittest
from pathlib import Path

from grade_manager import GradeManager


class GradeManagerTests(unittest.TestCase):
    def setUp(self):
        """Create a temporary directory and GradeManager instance for each test."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name) / "grades.csv"
        self.manager = GradeManager(str(self.temp_path))

    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def test_add_student(self):
        """Test adding a student with a grade."""
        self.manager.add_student("Alice", 85)
        self.assertIn("Alice", self.manager.get_all_students())
        self.assertEqual(self.manager.get_student_grades("Alice"), [85])

    def test_remove_student(self):
        """Test removing a student that exists."""
        self.manager.add_student("Bob", 90)
        self.manager.remove_student("Bob")
        self.assertNotIn("Bob", self.manager.get_all_students())

    def test_remove_nonexistent_student_raises_error(self):
        """Test that removing a nonexistent student raises an error."""
        with self.assertRaises(KeyError):
            self.manager.remove_student("NonExistent")

    def test_average_grade_calculation(self):
        """Test that average grade is calculated correctly."""
        self.manager.add_student("Charlie", 80)
        self.manager.update_grade("Charlie", 90)
        self.manager.update_grade("Charlie", 100)
        # Average of 80, 90, 100 should be 90
        self.assertEqual(self.manager.get_average_grade("Charlie"), 90)

    def test_rank_students_by_average_high_to_low(self):
        """Test that students are ranked from high to low average."""
        self.manager.add_student("Alice", 85)
        self.manager.add_student("Bob", 95)
        self.manager.add_student("Charlie", 75)
        
        ranked = self.manager.rank_students_by_average()
        # Should be in order: Bob (95), Alice (85), Charlie (75)
        self.assertEqual(ranked[0][0], "Bob")
        self.assertEqual(ranked[0][1], 95)
        self.assertEqual(ranked[1][0], "Alice")
        self.assertEqual(ranked[1][1], 85)
        self.assertEqual(ranked[2][0], "Charlie")
        self.assertEqual(ranked[2][1], 75)

    def test_storage_persistence(self):
        """Test that grades persist after saving and loading."""
        self.manager.add_student("David", 88)
        self.manager.update_grade("David", 92)
        
        # Create a new manager instance to test loading
        manager2 = GradeManager(str(self.temp_path))
        grades = manager2.get_student_grades("David")
        # Should load as numbers, not strings
        self.assertEqual(len(grades), 2)
        self.assertIsInstance(grades[0], int)
        self.assertEqual(sum(grades) / len(grades), 90)


if __name__ == "__main__":
    unittest.main()
