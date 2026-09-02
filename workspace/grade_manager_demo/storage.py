"""Storage module for persisting grades to CSV."""

import csv
from pathlib import Path


class Storage:
    def __init__(self, filepath="grades.csv"):
        self.filepath = Path(filepath)

    def save(self, grades):
        """Save grades to CSV file."""
        with open(self.filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["student", "grade"])
            for name, grade_list in grades.items():
                for grade in grade_list:
                    writer.writerow([name, grade])

    def load(self):
        """Load grades from CSV file."""
        grades = {}
        if not self.filepath.exists():
            return grades
        
        with open(self.filepath, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            for row in reader:
                if len(row) >= 2:
                    name = row[0]
                    grade_str = row[1]
                    grade = int(grade_str) if '.' not in grade_str else float(grade_str)
                    if name not in grades:
                        grades[name] = []
                    grades[name].append(grade)
        
        return grades
