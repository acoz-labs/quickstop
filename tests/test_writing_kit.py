"""The Claude kit must be self-contained and have no automatic configuration effects."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'plugins/claude-code/writing-for-humans'


class WritingKitTests(unittest.TestCase):
    def test_native_package_is_selectable_and_has_no_executable_components(self):
        manifest = json.loads((PACKAGE / '.claude-plugin/plugin.json').read_text())
        self.assertEqual(manifest['name'], 'writing-for-humans')
        self.assertNotIn('hooks', manifest)
        self.assertNotIn('mcpServers', manifest)
        self.assertFalse((PACKAGE / 'hooks').exists())
        self.assertFalse((PACKAGE / 'runtime').exists())
        self.assertFalse((PACKAGE / 'settings.json').exists())
        style = (PACKAGE / 'output-styles/writing-for-humans.md').read_text()
        frontmatter = style.split('---', 2)[1]
        self.assertIn('keep-coding-instructions: true', frontmatter)
        self.assertNotIn('force-for-plugin: true', frontmatter)
        self.assertEqual({p.name for p in (PACKAGE / 'skills').iterdir()},
                         {'writing-style', 'writing-audit'})

    def test_skill_references_resolve_inside_installed_package(self):
        count = 0
        for skill in (PACKAGE / 'skills').glob('*/SKILL.md'):
            for relative in re.findall(r'`((?:\.\./|references/)[^`]+\.md)`', skill.read_text()):
                target = (skill.parent / relative).resolve()
                self.assertTrue(target.is_relative_to(PACKAGE.resolve()), relative)
                self.assertTrue(target.is_file(), relative)
                count += 1
            self.assertNotIn('~/.claude/', skill.read_text())
        self.assertGreaterEqual(count, 7)

    def test_catalog_has_only_claude_target_for_kit(self):
        catalog = json.loads((ROOT / 'catalog.json').read_text())
        kit = next(p for p in catalog['plugins'] if p['name'] == 'writing-for-humans')
        self.assertEqual(set(kit['targets']), {'claude-code'})
        self.assertFalse((ROOT / 'plugins/codex/writing-for-humans').exists())
        self.assertFalse((ROOT / 'plugins/pi/writing-for-humans').exists())
