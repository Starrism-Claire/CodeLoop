import unittest

from sliding_window import max_sliding_window


class SlidingWindowMaximumTests(unittest.TestCase):
    def test_example_case(self):
        self.assertEqual(
            max_sliding_window([1, 3, -1, -3, 5, 3, 6, 7], 3),
            [3, 3, 5, 5, 6, 7],
        )

    def test_single_element_window(self):
        self.assertEqual(max_sliding_window([4, 2, 12, 3], 1), [4, 2, 12, 3])

    def test_window_is_entire_list(self):
        self.assertEqual(max_sliding_window([2, 1, 5, 3], 4), [5])

    def test_handles_duplicates(self):
        self.assertEqual(max_sliding_window([2, 2, 2, 2], 2), [2, 2, 2])

    def test_handles_negative_numbers(self):
        self.assertEqual(max_sliding_window([-7, -8, -6, -5, -9], 2), [-7, -6, -5, -5])

    def test_strictly_increasing_values(self):
        self.assertEqual(max_sliding_window([1, 2, 3, 4, 5], 3), [3, 4, 5])

    def test_strictly_decreasing_values(self):
        self.assertEqual(max_sliding_window([5, 4, 3, 2, 1], 3), [5, 4, 3])

    def test_repeated_maximum_leaves_window(self):
        self.assertEqual(max_sliding_window([9, 9, 1, 2, 9, 3], 3), [9, 9, 9, 9])

    def test_invalid_zero_window_size(self):
        with self.assertRaises(ValueError):
            max_sliding_window([1, 2, 3], 0)

    def test_invalid_window_larger_than_list(self):
        with self.assertRaises(ValueError):
            max_sliding_window([1, 2], 3)

    def test_empty_nums_invalid(self):
        with self.assertRaises(ValueError):
            max_sliding_window([], 1)

    def test_does_not_mutate_input(self):
        nums = [1, 3, 2, 5]
        original = list(nums)

        max_sliding_window(nums, 2)

        self.assertEqual(nums, original)


if __name__ == "__main__":
    unittest.main()
