from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / 'bin/validate-solution-plans'
VALID = """# Plan: Export CSV

## Issue

Refs #42. Users can export their report as CSV.

## Files that change

The report exporter and its tests.

## Order of work

1. Add the exporter. 2. Wire the button.

## Risks

Large reports could time out.

## Proof

Unit tests for quoting; export a 10k-row report.

## Rollback

Revert the PR; no data changes.
"""

class ChangePlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.folder = self.root / 'docs/changes/42-export-csv'
        self.folder.mkdir(parents=True)
    def tearDown(self):
        self.tmp.cleanup()
    def run_validator(self, plan=None):
        if plan is not None:
            (self.folder / 'plan.md').write_text(plan)
        return subprocess.run([str(VALIDATOR), str(self.root)], capture_output=True, text=True)

    def test_valid_plan_passes(self):
        result = self.run_validator(VALID)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Change plans valid (1)', result.stdout)
    def test_issue_may_be_a_full_url_or_cross_repo_reference(self):
        for link in ('https://github.com/acme/app/issues/42', 'acme/app#42'):
            with self.subTest(link=link):
                result = self.run_validator(VALID.replace('Refs #42', 'Refs ' + link))
                self.assertEqual(result.returncode, 0, result.stderr)
    def test_missing_section_fails(self):
        result = self.run_validator(VALID.replace('## Rollback', '## Notes'))
        self.assertEqual(result.returncode, 1)
        self.assertIn("docs/changes/42-export-csv: missing section 'Rollback'", result.stderr)
    def test_empty_section_fails(self):
        result = self.run_validator(VALID.replace('Large reports could time out.', ''))
        self.assertEqual(result.returncode, 1)
        self.assertIn("empty section 'Risks'", result.stderr)
    def test_headings_inside_code_fences_are_not_sections(self):
        skeleton = 'Revert the PR. A skeleton for later plans:\n\n```markdown\n## Risks\n\n## Proof\n```\n\n~~~\n## Issue\n~~~\n'
        result = self.run_validator(VALID.replace('Revert the PR; no data changes.\n', skeleton))
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.run_validator(VALID.replace('## Rollback\n\nRevert the PR; no data changes.\n',
                                                  '```\n## Rollback\n\nRevert the PR.\n```\n'))
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing section 'Rollback'", result.stderr)
    def test_missing_issue_link_fails(self):
        for issue in ('Refs the export issue.', 'See PR-42 and the C# exporter.', 'Pull https://github.com/acme/app/pull/42'):
            with self.subTest(issue=issue):
                result = self.run_validator(VALID.replace('Refs #42.', issue))
                self.assertEqual(result.returncode, 1)
                self.assertIn('Issue section does not link an issue', result.stderr)
    def test_folder_without_plan_fails(self):
        result = self.run_validator()
        self.assertEqual(result.returncode, 1)
        self.assertIn('missing plan.md', result.stderr)
    def test_template_folder_and_absent_changes_directory_are_ignored(self):
        self.folder.rmdir()
        self.folder.parent.rmdir()
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stderr)
        template = self.root / 'docs/changes/_template'
        template.mkdir(parents=True)
        (template / 'plan.md').write_text('# Plan: TITLE\n')
        self.assertEqual(self.run_validator().returncode, 0)
    def test_shipped_template_has_every_section_and_stays_short(self):
        text = (ROOT / 'docs/changes/_template/plan.md').read_text()
        for name in ('Issue', 'Files that change', 'Order of work', 'Risks', 'Proof', 'Rollback'):
            self.assertIn('\n## ' + name + '\n', text)
        self.assertLess(len(text.splitlines()), 40)

if __name__ == '__main__':
    unittest.main()
