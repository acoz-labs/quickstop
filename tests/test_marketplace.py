import importlib.machinery
import importlib.util
import json
from pathlib import Path
import subprocess
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
            path = f'plugins/{harness}/{name}'
            plugin['targets'][harness] = {'path': path, 'format': fmt, 'acceptance': f'docs/acceptance/{name}-{harness}.md'}
            manifest = {'name': name, 'version': '1.0.0', 'description': 'Fixture', 'license': 'MIT'}
            if fmt == 'agent-plugin':
                manifest['$schema'] = 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json'
            if fmt == 'pi-package':
                manifest['pi'] = {'skills': ['./skills']}
                self.write(path + '/skills/hello/SKILL.md', '---\nname: hello\ndescription: Fixture skill\n---\nReport a synthetic greeting.')
            self.write(path + '/' + module.FORMATS[harness][fmt], manifest)
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

    def test_claude_only_does_not_leak_to_codex(self):
        self.assertEqual(module.validate(self.root, 'HEAD'), 1)
        codex = json.loads((self.root / '.agents/plugins/marketplace.json').read_text())
        self.assertEqual(codex['plugins'], [])
        claude = json.loads((self.root / '.claude-plugin/marketplace.json').read_text())
        self.assertEqual([p['name'] for p in claude['plugins']], ['sample'])

    def test_codex_only_and_mixed_support_without_parity(self):
        self.add_plugin('codex-only', {'codex': 'agent-plugin'})
        self.add_plugin('both', {'claude-code': 'claude-plugin', 'codex': 'codex-plugin'})
        self.generate()
        claude = json.loads((self.root / '.claude-plugin/marketplace.json').read_text())
        codex = json.loads((self.root / '.agents/plugins/marketplace.json').read_text())
        self.assertEqual([p['name'] for p in claude['plugins']], ['sample', 'both'])
        self.assertEqual([p['name'] for p in codex['plugins']], ['codex-only', 'both'])
        self.assertEqual(codex['plugins'][0]['source']['path'], './plugins/codex/codex-only')
        self.assertEqual(codex['plugins'][0]['policy']['installation'], 'AVAILABLE')
        self.assertEqual(module.validate(self.root, 'HEAD'), 3)

    def test_shared_package_can_explicitly_support_two_harnesses(self):
        plugin = self.catalog['plugins'][0]
        path = plugin['targets']['claude-code']['path']
        plugin['targets']['codex'] = {'path': path, 'format': 'codex-plugin', 'acceptance': 'docs/acceptance/sample-codex.md'}
        self.write(path + '/.codex-plugin/plugin.json', {'name': 'sample', 'version': '1.0.0', 'description': 'Fixture'})
        self.write('docs/acceptance/sample-codex.md', '# Codex\nExercise the shared fixture package.')
        self.generate()
        self.assertEqual(module.validate(self.root), 1)

    def test_independent_package_versions(self):
        self.add_plugin('both', {'claude-code': 'claude-plugin', 'codex': 'codex-plugin'})
        self.generate(); self.commit()
        self.write('plugins/codex/both/new.md', 'New Codex payload')
        self.update_version('codex', '1.0.1', 'both')
        self.generate('HEAD')
        self.assertEqual(module.validate(self.root, 'HEAD'), 2)
        self.write('plugins/claude-code/both/new.md', 'New Claude payload')
        with self.assertRaisesRegex(module.Invalid, 'higher version'):
            module.validate(self.root, 'HEAD')

    def test_invalid_base_fails(self):
        with self.assertRaises(module.Invalid):
            module.validate(self.root, 'does-not-exist')

    def test_unbumped_tracked_and_untracked_payload_fail(self):
        self.write('plugins/claude-code/sample/new.md', 'New payload')
        with self.assertRaisesRegex(module.Invalid, 'higher version'):
            module.validate(self.root, 'HEAD')
        self.git('add', '.')
        with self.assertRaisesRegex(module.Invalid, 'higher version'):
            module.validate(self.root, 'HEAD')

    def test_readme_is_versioned_and_downgrade_fails(self):
        self.write('plugins/claude-code/sample/README.md', 'Updated')
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
        with self.assertRaises(module.Invalid):
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
        target['path'] = 'plugins/claude-code/sample'
        (self.root / target['path'] / 'link').symlink_to('/tmp')
        with self.assertRaises(module.Invalid): self.generate()

    def test_output_symlink_is_not_followed(self):
        path = self.root / '.agents/plugins/marketplace.json'
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
        self.write('plugins/claude-code/sample/.codex-plugin/plugin.json', {'name': 'sample', 'version': '1.0.0'})
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

    def test_portable_schema_required(self):
        plugin = self.add_plugin('portable', {'codex': 'agent-plugin'})
        path = plugin['targets']['codex']['path'] + '/plugin.json'
        value = json.loads((self.root / path).read_text()); value.pop('$schema'); self.write(path, value)
        with self.assertRaises(module.Invalid): self.generate()

    def test_malformed_frontmatter_and_missing_skill_fail(self):
        path = 'plugins/claude-code/sample/skills/broken/SKILL.md'
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
        old = self.root / target['path']; new = self.root / 'plugins/sample'
        old.rename(new); target['path'] = 'plugins/sample'
        self.generate('HEAD')
        self.assertEqual(module.validate(self.root, 'HEAD'), 1)

    def test_pi_only_and_all_three_targets(self):
        self.add_plugin('pi-only', {'pi': 'pi-package'})
        self.add_plugin('all-three', {'claude-code': 'claude-plugin', 'codex': 'agent-plugin', 'pi': 'pi-package'})
        self.generate()
        guide = (self.root / 'docs/pi-packages.md').read_text()
        self.assertIn('pi install ./plugins/pi/pi-only', guide)
        self.assertIn('pi install ./plugins/pi/all-three', guide)
        self.assertNotIn('pi install ./plugins/claude-code/sample', guide)
        codex = json.loads((self.root / '.agents/plugins/marketplace.json').read_text())
        self.assertEqual([p['name'] for p in codex['plugins']], ['all-three'])
        self.assertEqual(module.validate(self.root, 'HEAD'), 3)
        self.commit()
        self.write('plugins/pi/all-three/README.md', 'Pi-only change')
        self.update_version('pi', '1.0.1', 'all-three')
        self.generate('HEAD')
        self.assertEqual(module.validate(self.root, 'HEAD'), 3)

    def test_pi_invalid_resources_fail(self):
        self.add_plugin('pi-only', {'pi': 'pi-package'})
        path = 'plugins/pi/pi-only/package.json'
        original = json.loads((self.root / path).read_text())
        for resources in ({}, {'skills': 'skills'}, {'skills': ['./missing']}, {'skills': ['./../outside']}, {'skills': ['./skills/*']}):
            self.write(path, dict(original, pi=resources))
            with self.assertRaises(module.Invalid): self.generate()

    def test_pi_recursive_and_file_skills_validate_frontmatter(self):
        self.add_plugin('pi-only', {'pi': 'pi-package'})
        self.write('plugins/pi/pi-only/skills/nested/hello/SKILL.md', 'invalid metadata')
        with self.assertRaises(module.Invalid): self.generate()

    def test_undeclared_pi_manifest_fails(self):
        self.write('plugins/claude-code/sample/package.json', {'pi': {'skills': ['./skills']}})
        with self.assertRaisesRegex(module.Invalid, 'undeclared native manifest'): self.generate()

    def test_portable_overlay_and_assets_are_checked(self):
        plugin = self.add_plugin('portable', {'codex': 'agent-plugin'})
        path = plugin['targets']['codex']['path']
        overlay = path + '/.codex-plugin/plugin.json'
        self.write(overlay, {'name': 'portable', 'version': '1.0.0', 'skills': './skills'})
        self.write(path + '/skills/hello/SKILL.md', '---\nname: hello\ndescription: Fixture\n---\nHello')
        self.generate()
        self.assertEqual(module.validate(self.root), 2)
        self.write(overlay, {'name': 'portable', 'version': '2.0.0'})
        with self.assertRaises(module.Invalid): self.generate()
        self.write(overlay, {'interface': {'logo': './../outside.png'}})
        with self.assertRaises(module.Invalid): self.generate()
        self.write(overlay, {'interface': {'screenshots': ['./assets/missing.png']}})
        with self.assertRaises(module.Invalid): self.generate()

    def test_malformed_resource_types_fail_before_writes(self):
        path = 'plugins/claude-code/sample/.claude-plugin/plugin.json'
        original = json.loads((self.root / path).read_text())
        before = {name: (self.root / name).read_bytes() for name in module.OUTPUTS}
        for key, value in [('skills', 42), ('skills', {'path': './../outside'}), ('skills', None),
                           ('agents', True), ('hooks', 42), ('hooks', {'path': './../outside'}),
                           ('mcpServers', True), ('mcpServers', {'server': 'wrong'}), ('apps', [])]:
            self.write(path, dict(original, **{key: value}))
            with self.assertRaises(module.Invalid): self.generate()
            self.assertEqual({name: (self.root / name).read_bytes() for name in module.OUTPUTS}, before)

    def test_legitimate_inline_claude_hooks_and_mcp_are_retained(self):
        path = 'plugins/claude-code/sample/.claude-plugin/plugin.json'
        data = json.loads((self.root / path).read_text())
        data.update(hooks={'hooks': {'SessionStart': []}}, mcpServers={'fixture': {'command': 'fixture-server'}})
        self.write(path, data)
        self.generate()
        self.assertEqual(module.validate(self.root), 1)

    def test_codex_resource_types_differ_from_claude(self):
        self.add_plugin('codex-only', {'codex': 'codex-plugin'})
        path = 'plugins/codex/codex-only/.codex-plugin/plugin.json'
        original = json.loads((self.root / path).read_text())
        for key, value in [('skills', []), ('hooks', {'hooks': {}}), ('agents', []), ('mcpServers', [])]:
            self.write(path, dict(original, **{key: value}))
            with self.assertRaises(module.Invalid): self.generate()
