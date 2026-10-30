import unittest

from csvsum import column_sum


class ColumnSumTests(unittest.TestCase):
    def test_sums_a_column_and_skips_blank_lines(self):
        self.assertEqual(column_sum(['name,amount', 'a,1.5', '', 'b,2'], 'amount'), 3.5)


if __name__ == '__main__':
    unittest.main()
