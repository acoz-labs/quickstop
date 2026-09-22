import importlib.machinery
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

loader = importlib.machinery.SourceFileLoader('marketplace', str(Path(__file__).resolve().parents[1] / 'bin/check-marketplace'))
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)


class MarketplaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.write('.claude-plugin/marketplace.json', {'name': 'quickstop', 'owner': {'name': 'test'}, 'plugins': [{'name': 'sample', 'source': './plugins/sample', 'version': '1.0.0'}]})
        self.write('plugins/sample/.claude-plugin/plugin.json', {'name': 'sample', 'version': '1.0.0', 'description': 'A test', 'license': 'MIT'})
        self.write('plugins/sample/README.md', 'Sample')
        self.write('plugins/sample/LICENSE', 'Fixture license')
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'commit.gpgsign', 'false')
        self.git('add', '.')
        self.git('commit', '-qm', 'fixture')

    def write(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value) if isinstance(value, dict) else value)

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.root), *args], check=True, capture_output=True)

    def update_version(self, value):
        for name in ('.claude-plugin/marketplace.json', 'plugins/sample/.claude-plugin/plugin.json'):
            content = json.loads((self.root / name).read_text())
            if 'plugins' in content:
                content['plugins'][0]['version'] = value
            else:
                content['version'] = value
            self.write(name, content)

    def test_valid_unchanged_and_new_version(self):
        self.assertEqual(module.validate(self.root, 'HEAD'), 1)
        self.write('plugins/sample/README.md', 'Changed')
        self.update_version('1.0.1')
        self.assertEqual(module.validate(self.root, 'HEAD'), 1)

    def test_invalid_base_fails(self):
        with self.assertRaises(module.Invalid):
            module.validate(self.root, 'does-not-exist')

    def test_unbumped_payload_and_untracked_payload_fail(self):
        self.write('plugins/sample/new.md', 'New payload')
        with self.assertRaises(module.Invalid):
            module.validate(self.root, 'HEAD')
        self.git('add', '.')
        with self.assertRaises(module.Invalid):
            module.validate(self.root, 'HEAD')

    def test_downgrade_fails(self):
        self.update_version('0.9.0')
        with self.assertRaises(module.Invalid):
            module.validate(self.root, 'HEAD')

    def test_mismatched_registration_fails(self):
        path = self.root / '.claude-plugin/marketplace.json'
        data = json.loads(path.read_text())
        data['plugins'][0]['version'] = '2.0.0'
        self.write(str(path.relative_to(self.root)), data)
        with self.assertRaises(module.Invalid):
            module.validate(self.root)

    def test_duplicate_and_escaping_sources_fail(self):
        path = self.root / '.claude-plugin/marketplace.json'
        original = json.loads(path.read_text())
        data = json.loads(path.read_text())
        data['plugins'].append(data['plugins'][0].copy())
        self.write('.claude-plugin/marketplace.json', data)
        with self.assertRaises(module.Invalid):
            module.validate(self.root)
        original['plugins'][0]['source'] = '../outside'
        self.write('.claude-plugin/marketplace.json', original)
        with self.assertRaises(module.Invalid):
            module.validate(self.root)

    def test_symlink_and_unregistered_directory_fail(self):
        (self.root / 'plugins/sample/link').symlink_to('/tmp')
        with self.assertRaises(module.Invalid):
            module.validate(self.root)
        (self.root / 'plugins/sample/link').unlink()
        (self.root / 'plugins/other').mkdir()
        with self.assertRaises(module.Invalid):
            module.validate(self.root)

    def test_missing_skill_entrypoint_fails(self):
        (self.root / 'plugins/sample/skills/broken').mkdir(parents=True)
        with self.assertRaises(module.Invalid):
            module.validate(self.root)

    def test_malformed_frontmatter_fails(self):
        self.write('plugins/sample/skills/broken/SKILL.md', 'No metadata')
        with self.assertRaises(module.Invalid):
            module.validate(self.root)
