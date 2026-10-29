import importlib.util
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).parent.parent / "skills/changelog-entry/scripts/format_entry.py"
spec = importlib.util.spec_from_file_location("format_entry", SCRIPT)
format_entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(format_entry)


class FormatEntryTest(unittest.TestCase):
    def test_groups_by_type(self):
        text = format_entry.format_entry(["feat: add tags", "fix(cli): exit code", "docs: typo"])
        self.assertEqual(
            text,
            "### Added\n- add tags\n\n### Fixed\n- exit code\n\n### Changed\n- typo\n",
        )

    def test_empty_input(self):
        self.assertEqual(format_entry.format_entry([]), "")


if __name__ == "__main__":
    unittest.main()
