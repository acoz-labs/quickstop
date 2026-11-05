import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

loader = importlib.machinery.SourceFileLoader('marketplace', str(Path(__file__).resolve().parents[1] / 'bin/check-marketplace'))
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)


class MarketplaceTests(unittest.TestCase):
    def setUp(self):
        # These cases exercise authoring package validation; publication is tested separately.
        patcher = patch.object(module, "load_releases", return_value=None)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.catalog = {'schema': 1, 'name': 'quickstop', 'display_name': 'Test', 'description': 'Fixture catalog', 'plugins': []}
        self.add_plugin('sample', {'claude-code': 'claude-plugin'})
        self.generate()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'commit.gpgsign', 'false')
        self.commit()

    def write(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value) if isinstance(value, dict) else value)

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.root), *args], check=True, capture_output=True)

    def commit(self):
        self.git('add', '.')
        self.git('commit', '-qm', 'fixture')

    def add_plugin(self, name, harnesses):
        plugin = {'name': name, 'description': 'Fixture plugin', 'category': 'Productivity', 'targets': {}}
        self.catalog['plugins'].append(plugin)
        for harness, fmt in harnesses.items():
            path = f'plugins/{name}'
            plugin['targets'][harness] = {'path': path, 'format': fmt, 'acceptance': f'docs/acceptance/{name}.md'}
            manifest = {'name': name, 'version': '1.0.0', 'description': 'Fixture', 'license': 'MIT'}
            self.write(path + '/' + module.FORMATS.get(harness, {}).get(fmt, '.claude-plugin/plugin.json'), manifest)
            self.write(path + '/README.md', 'Fixture readme')
            self.write(path + '/LICENSE', 'Fixture license')
            self.write(plugin['targets'][harness]['acceptance'], f'# {harness} acceptance\nExercise fixture skill in an isolated host.')
        return plugin

    def save_catalog(self):
        self.write('catalog.json', self.catalog)

    def generate(self, base=None):
        self.save_catalog()
        return module.validate(self.root, base=base, write=True)

    def update_version(self, harness, value, name='sample'):
        plugin = next(p for p in self.catalog['plugins'] if p['name'] == name)
        target = plugin['targets'][harness]
        path = target['path'] + '/' + module.FORMATS[harness][target['format']]
        data = json.loads((self.root / path).read_text())
        data['version'] = value
        self.write(path, data)

    def test_claude_index_lists_each_plugin(self):
        self.assertEqual(module.validate(self.root, 'HEAD'), 1)
        claude = json.loads((self.root / '.claude-plugin/marketplace.json').read_text())
        self.assertEqual([p['name'] for p in claude['plugins']], ['sample'])
        self.assertEqual(claude['plugins'][0]['source'], './plugins/sample')
        self.assertEqual(module.OUTPUTS, ('.claude-plugin/marketplace.json', 'docs/catalog.md'))
        for retired in ('.agents/plugins/marketplace.json', 'docs/pi-packages.md'):
            self.assertFalse((self.root / retired).exists())

    def test_codex_and_pi_targets_are_rejected_without_writes(self):
        before = {name: (self.root / name).read_bytes() for name in module.OUTPUTS}
        for harness, fmt in (('codex', 'agent-plugin'), ('codex', 'codex-plugin'), ('pi', 'pi-package')):
            with self.subTest(harness=harness, format=fmt):
                self.catalog['plugins'] = [self.catalog['plugins'][0]]
                self.add_plugin('other', {harness: fmt})
                with self.assertRaisesRegex(module.Invalid, f"other: unsupported target '{harness}'; Quickstop supports only claude-code"):
                    self.generate()
                self.assertEqual({name: (self.root / name).read_bytes() for name in module.OUTPUTS}, before)
        # A second target beside claude-code is refused the same way.
        self.catalog['plugins'] = [self.catalog['plugins'][0]]
        target = self.catalog['plugins'][0]['targets']['claude-code']
        self.catalog['plugins'][0]['targets']['codex'] = dict(target, format='codex-plugin')
        with self.assertRaisesRegex(module.Invalid, "sample: unsupported target 'codex'"):
            self.generate()

    def test_plugins_version_independently(self):
        self.add_plugin('other', {'claude-code': 'claude-plugin'})
        self.generate(); self.commit()
        self.write('plugins/other/new.md', 'New payload')
        self.update_version('claude-code', '1.0.1', 'other')
        self.generate('HEAD')
        self.assertEqual(module.validate(self.root, 'HEAD'), 2)
        self.write('plugins/sample/new.md', 'New payload')
        with self.assertRaisesRegex(module.Invalid, 'higher version'):
            module.validate(self.root, 'HEAD')

    def test_invalid_base_fails(self):
        with self.assertRaises(module.Invalid):
            module.validate(self.root, 'does-not-exist')

    def test_unbumped_tracked_and_untracked_payload_fail(self):
        self.write('plugins/sample/new.md', 'New payload')
        with self.assertRaisesRegex(module.Invalid, 'higher version'):
            module.validate(self.root, 'HEAD')
        self.git('add', '.')
        with self.assertRaisesRegex(module.Invalid, 'higher version'):
            module.validate(self.root, 'HEAD')

    def test_bytecode_cache_is_not_payload(self):
        self.write('plugins/sample/scripts/__pycache__/tool.cpython-311.pyc', 'cache')
        self.write('plugins/sample/scripts/stray.pyc', 'cache')
        self.assertEqual(module.validate(self.root, 'HEAD'), 1)

    def test_readme_is_versioned_and_downgrade_fails(self):
        self.write('plugins/sample/README.md', 'Updated')
        with self.assertRaisesRegex(module.Invalid, 'higher version'):
            module.validate(self.root, 'HEAD')
        self.update_version('claude-code', '0.9.0'); self.generate()
        with self.assertRaisesRegex(module.Invalid, 'downgrade'):
            module.validate(self.root, 'HEAD')

    def test_changed_bytes_with_bump_pass(self):
        self.update_version('claude-code', '1.0.1')
        self.generate('HEAD')
        self.assertEqual(module.validate(self.root, 'HEAD'), 1)

    def test_generated_index_and_table_drift_fail(self):
        for output in module.OUTPUTS:
            original = (self.root / output).read_text()
            self.write(output, original + '\n')
            with self.assertRaisesRegex(module.Invalid, 'index drift'):
                module.validate(self.root)
            self.write(output, original)

    def test_unknown_harness_and_format_fail_without_writes(self):
        before = (self.root / module.OUTPUTS[0]).read_bytes()
        target = self.catalog['plugins'][0]['targets'].pop('claude-code')
        self.catalog['plugins'][0]['targets']['imaginary'] = target
        with self.assertRaises(module.Invalid):
            self.generate()
        self.assertEqual((self.root / module.OUTPUTS[0]).read_bytes(), before)
        self.catalog['plugins'][0]['targets'] = {'claude-code': dict(target, format='codex-plugin')}
        with self.assertRaisesRegex(module.Invalid, "unsupported claude-code format 'codex-plugin'"):
            self.generate()

    def test_empty_support_duplicate_names_and_unknown_fields_fail(self):
        original = json.loads(json.dumps(self.catalog))
        self.catalog['plugins'][0]['targets'] = {}
        with self.assertRaises(module.Invalid): self.generate()
        self.catalog = json.loads(json.dumps(original))
        self.catalog['plugins'].append(self.catalog['plugins'][0].copy())
        with self.assertRaises(module.Invalid): self.generate()
        self.catalog = original
        self.catalog['plugins'][0]['parity'] = True
        with self.assertRaises(module.Invalid): self.generate()

    def test_unsafe_missing_and_symlink_paths_fail(self):
        target = self.catalog['plugins'][0]['targets']['claude-code']
        for path in ('../outside', '/tmp', 'plugins/../outside', 'plugins/missing'):
            target['path'] = path
            with self.assertRaises(module.Invalid): self.generate()
        target['path'] = 'plugins/sample'
        (self.root / target['path'] / 'link').symlink_to('/tmp')
        with self.assertRaises(module.Invalid): self.generate()

    def test_output_symlink_is_not_followed(self):
        path = self.root / 'docs/catalog.md'
        path.unlink()
        destination = self.root / 'sentinel'
        destination.write_text('preserve')
        path.symlink_to(destination)
        with self.assertRaises(module.Invalid): self.generate()
        self.assertEqual(destination.read_text(), 'preserve')

    def test_unregistered_package_and_undeclared_native_manifest_fail(self):
        self.write('plugins/other/README.md', 'Not registered')
        with self.assertRaises(module.Invalid): self.generate()
        (self.root / 'plugins/other/README.md').unlink()
        self.write('plugins/sample/nested/.claude-plugin/plugin.json', {'name': 'nested', 'version': '1.0.0'})
        with self.assertRaisesRegex(module.Invalid, 'undeclared native manifest'): self.generate()

    def test_manifest_name_missing_acceptance_and_component_escape_fail(self):
        target = self.catalog['plugins'][0]['targets']['claude-code']
        path = target['path'] + '/.claude-plugin/plugin.json'
        original = json.loads((self.root / path).read_text())
        self.write(path, dict(original, name='wrong'))
        with self.assertRaises(module.Invalid): self.generate()
        self.write(path, dict(original, skills='./../outside'))
        with self.assertRaises(module.Invalid): self.generate()
        self.write(path, original)
        (self.root / target['acceptance']).unlink()
        with self.assertRaises(module.Invalid): self.generate()

    def test_malformed_frontmatter_and_missing_skill_fail(self):
        path = 'plugins/sample/skills/broken/SKILL.md'
        self.write(path, 'No metadata')
        with self.assertRaises(module.Invalid): self.generate()
        (self.root / path).unlink()
        with self.assertRaises(module.Invalid): self.generate()

    def test_duplicate_json_keys_fail(self):
        self.write('catalog.json', '{"name":"quickstop","name":"hidden"}')
        with self.assertRaises(module.Invalid): module.validate(self.root)

    def test_legacy_claude_catalog_migration_preserves_bytes(self):
        self.git('rm', 'catalog.json'); self.git('commit', '-qm', 'legacy base')
        self.save_catalog()
        self.assertEqual(module.validate(self.root, 'HEAD'), 1)

    def test_moving_unchanged_package_does_not_require_version_bump(self):
        target = self.catalog['plugins'][0]['targets']['claude-code']
        old = self.root / target['path']; new = self.root / 'plugins/renamed'
        old.rename(new); target['path'] = 'plugins/renamed'
        self.generate('HEAD')
        self.assertEqual(module.validate(self.root, 'HEAD'), 1)

    def test_malformed_resource_types_fail_before_writes(self):
        path = 'plugins/sample/.claude-plugin/plugin.json'
        original = json.loads((self.root / path).read_text())
        before = {name: (self.root / name).read_bytes() for name in module.OUTPUTS}
        for key, value in [('skills', 42), ('skills', {'path': './../outside'}), ('skills', None),
                           ('agents', True), ('hooks', 42), ('hooks', {'path': './../outside'}),
                           ('mcpServers', True), ('mcpServers', {'server': 'wrong'})]:
            self.write(path, dict(original, **{key: value}))
            with self.assertRaises(module.Invalid): self.generate()
            self.assertEqual({name: (self.root / name).read_bytes() for name in module.OUTPUTS}, before)

    def test_legitimate_inline_claude_hooks_and_mcp_are_retained(self):
        path = 'plugins/sample/.claude-plugin/plugin.json'
        data = json.loads((self.root / path).read_text())
        data.update(hooks={'hooks': {'SessionStart': []}}, mcpServers={'fixture': {'command': 'fixture-server'}})
        self.write(path, data)
        self.generate()
        self.assertEqual(module.validate(self.root), 1)


class RepositoryTests(unittest.TestCase):
    def test_retired_tool_outputs_and_layouts_are_gone(self):
        root = Path(__file__).resolve().parents[1]
        for retired in ('.agents', 'docs/pi-packages.md', 'plugins/codex', 'plugins/claude-code',
                        'docs/acceptance/shipshape.md', 'tests/test_shipshape.py'):
            self.assertFalse((root / retired).exists(), retired)
        catalog = json.loads((root / 'catalog.json').read_text())
        self.assertEqual({h for p in catalog['plugins'] for h in p['targets']}, {'claude-code'})
        self.assertEqual({p['name']: p['targets']['claude-code']['path'] for p in catalog['plugins']},
                         {p['name']: 'plugins/' + p['name'] for p in catalog['plugins']})


class PinnedPythonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.expected = platform.python_version()

    def interpreter(self, folder, name, target=None):
        path = self.root / folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if target:
            path.symlink_to(target)
        else:
            path.write_text('#!/bin/sh\necho "0.0.0 /elsewhere/python3"\n')
            path.chmod(0o755)
        return path.parent

    def test_finds_the_pinned_version_behind_another_python3(self):
        first = self.interpreter('first', 'python3')
        minor = '.'.join(self.expected.split('.')[:2])
        later = self.interpreter('later', f'python{minor}', sys.executable)
        found = module.find_python(self.expected, f'{first}{os.pathsep}{later}')
        self.assertEqual(Path(found).resolve(), Path(sys.executable).resolve())

    def test_no_matching_version_is_none(self):
        self.assertIsNone(module.find_python(self.expected, str(self.interpreter('only', 'python3'))))

    def test_missing_pin_fails_naming_the_version(self):
        (self.root / 'bin').mkdir()
        shutil.copy(Path(__file__).resolve().parents[1] / 'bin/check-marketplace', self.root / 'bin')
        (self.root / '.python-version').write_text('0.0.1\n')
        result = subprocess.run([sys.executable, str(self.root / 'bin/check-marketplace')], capture_output=True, text=True,
                                env={'PATH': str(self.interpreter('only', 'python3'))})
        self.assertEqual(result.returncode, 1)
        self.assertIn('Python 0.0.1 (pinned in .python-version) not found', result.stderr)
