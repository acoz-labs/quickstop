import unittest

from orchard.stock import level


class LevelTests(unittest.TestCase):
    def test_sum(self):
        self.assertEqual(level([12, -3, 1]), 10)

    def test_rejects_floats(self):
        with self.assertRaises(TypeError):
            level([0.5])


if __name__ == '__main__':
    unittest.main()
