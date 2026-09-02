"""Student grade management system."""

from storage import Storage


class GradeManager:
    def __init__(self, storage_path="grades.csv"):
        self.storage = Storage(storage_path)
        self.grades = self.storage.load()

    def add_student(self, name, grade):
        """Add a student with their grade."""
        if name not in self.grades:
            self.grades[name] = []
        self.grades[name].append(grade)
        self.storage.save(self.grades)

    def remove_student(self, name):
        """Remove a student from the system."""
        # BUG: No existence check, will crash if student doesn't exist
        del self.grades[name]
        self.storage.save(self.grades)

    def get_student_grades(self, name):
        """Get all grades for a student."""
        return self.grades.get(name, [])

    def get_average_grade(self, name):
        """Get the average grade for a student."""
        grades = self.grades.get(name, [])
        if not grades:
            return 0
        return sum(grades) / len(grades) if len(grades) > 0 else 0

    def get_all_students(self):
        """Get list of all students."""
        return list(self.grades.keys())

    def rank_students_by_average(self):
        """Rank students by average grade from high to low."""
        students_avg = [
            (name, self.get_average_grade(name))
            for name in self.get_all_students()
        ]
        return sorted(students_avg, key=lambda x: x[1], reverse=True)

    def update_grade(self, name, grade):
        """Add an additional grade to a student."""
        if name not in self.grades:
            self.grades[name] = []
        self.grades[name].append(grade)
        self.storage.save(self.grades)
