import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from wordfreq import count_words, top_words


class WordFrequencyTests(unittest.TestCase):
    def test_count_words_normalizes_case_and_punctuation(self):
        counts = count_words("Hello, hello! HELLO? world. World")
        self.assertEqual(counts["hello"], 3)
        self.assertEqual(counts["world"], 2)
        self.assertNotIn("Hello,", counts)

    def test_top_words_allows_limit_larger_than_vocabulary(self):
        counts = count_words("red blue red")
        self.assertEqual(top_words(counts, 10), [("red", 2), ("blue", 1)])

    def test_top_words_filters_by_min_count(self):
        counts = count_words("red blue red green green green")
        self.assertEqual(top_words(counts, 10, min_count=2), [("green", 3), ("red", 2)])

    def test_cli_supports_min_count(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.txt"
            path.write_text("Apple apple, banana banana! cherry", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, "main.py", str(path), "--top", "5", "--min-count", "2"],
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("apple\t2", result.stdout)
        self.assertIn("banana\t2", result.stdout)
        self.assertNotIn("cherry", result.stdout)


if __name__ == "__main__":
    unittest.main()
