"""使用标准库 unittest 对 calculator 模块进行测试。"""

import unittest

import calculator


class TestCalculator(unittest.TestCase):
    def test_add(self):
        self.assertEqual(calculator.add(1, 2), 3)
        self.assertEqual(calculator.add(-1, 1), 0)
        self.assertEqual(calculator.add(1.5, 2.5), 4.0)

    def test_sub(self):
        self.assertEqual(calculator.sub(5, 3), 2)
        self.assertEqual(calculator.sub(0, 4), -4)
        self.assertEqual(calculator.sub(2.5, 0.5), 2.0)

    def test_mul(self):
        self.assertEqual(calculator.mul(3, 4), 12)
        self.assertEqual(calculator.mul(-2, 3), -6)
        self.assertEqual(calculator.mul(0, 100), 0)

    def test_div(self):
        self.assertEqual(calculator.div(10, 2), 5)
        self.assertEqual(calculator.div(9, 2), 4.5)
        self.assertEqual(calculator.div(-6, 3), -2)

    def test_div_by_zero(self):
        with self.assertRaises(ValueError):
            calculator.div(1, 0)
        with self.assertRaises(ValueError):
            calculator.div(0, 0)


if __name__ == "__main__":
    unittest.main()
