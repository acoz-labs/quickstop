import unittest

from labelmaker.label import render


class RenderTests(unittest.TestCase):
    def test_box(self):
        self.assertTrue(render('Ada', '1 Mill Lane').startswith('+'))

    def test_rate(self):
        self.assertTrue(render('Ada', '1 Mill Lane').endswith('standard: 3.95'))


if __name__ == '__main__':
    unittest.main()
