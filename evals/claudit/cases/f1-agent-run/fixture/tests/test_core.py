import unittest

from tallyho import parse_line, tally, winner


class CoreTest(unittest.TestCase):
    def test_parse_line(self):
        self.assertEqual(parse_line(" ana , tea "), ("ana", "tea"))

    def test_parse_line_rejects_malformed(self):
        with self.assertRaises(ValueError):
            parse_line("ana,")

    def test_later_vote_replaces_earlier(self):
        counts = tally(["ana,tea", "bo,coffee", "ana,coffee"])
        self.assertEqual(counts["coffee"], 2)
        self.assertEqual(counts["tea"], 0)

    def test_winner_breaks_ties_alphabetically(self):
        self.assertEqual(winner(tally(["a,tea", "b,coffee"])), "coffee")
        self.assertIsNone(winner(tally([])))


if __name__ == "__main__":
    unittest.main()
