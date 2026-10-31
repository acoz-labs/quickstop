from pathlib import Path
import unittest

from reportcheck import missing_sections

HERE = Path(__file__).parent


class Golden(unittest.TestCase):
    def test_golden_report_is_complete(self):
        self.assertEqual(missing_sections((HERE / 'golden/release-report.md').read_text()), ['Intent', 'Grades'])

    def test_sample_repo_readme_is_not_a_report(self):
        text = (HERE / 'fixtures/sample-repo/docs/sample-runbook.md').read_text()
        self.assertEqual(missing_sections(text), list(('Intent', 'Grades', 'Top changes')))
