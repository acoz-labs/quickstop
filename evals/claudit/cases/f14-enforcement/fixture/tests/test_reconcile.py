import unittest

from ledgerline import reconcile


class ReconcileTests(unittest.TestCase):
    def test_matching_ledgers(self):
        self.assertEqual(reconcile([('a', 100)], [('a', 100)]), [])

    def test_difference(self):
        self.assertEqual(reconcile([('a', 100)], [('a', 90), ('b', 5)]), [('a', 100, 90), ('b', None, 5)])


if __name__ == '__main__':
    unittest.main()
