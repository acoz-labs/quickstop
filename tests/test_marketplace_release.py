"""Synthetic release fixtures; no personal incidents or consumer configuration."""
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


def load(name, filename):
    loader = importlib.machinery.SourceFileLoader(name, str(Path(__file__).resolve().parents[1] / 'bin' / filename))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


m = load('publication_marketplace', 'check-marketplace')
r = load('publication_release', 'marketplace-release')


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'commit.gpgsign', 'false')
        self.target = {'format': 'claude-plugin', 'path': 'plugins/sample', 'acceptance': 'docs/acceptance/sample.md'}
        self.manifest = {'name': 'sample', 'description': 'Synthetic package', 'version': '1.0.0'}
        self.catalog = {'schema': 1, 'name': 'quickstop', 'display_name': 'Quickstop', 'description': 'Synthetic marketplace', 'plugins': [{'name': 'sample', 'description': 'Synthetic package', 'category': 'Productivity', 'targets': {'claude-code': self.target}}]}
        self.write('catalog.json', self.catalog)
        self.write('plugins/sample/.claude-plugin/plugin.json', self.manifest)
        self.write('plugins/sample/README.md', 'Synthetic package')
        self.write('docs/acceptance/sample.md', 'Synthetic acceptance procedure')
        self.write('releases.json', {'schema': 1, 'releases': []})
        self.commit()
        self.sha = self.git('rev-parse', 'HEAD').strip()
        self.record = {'name': 'sample', 'harness': 'claude-code', 'commit': self.sha, 'sha256': m.package_digest(self.root, self.target['path'], self.sha), 'target': self.target, 'manifest': self.manifest, 'provenance': {'kind': 'sdlc-accepted', 'issue': 7, 'artifact': 'sha256:' + 'a' * 64, 'acceptance': 'https://github.com/acoz-labs/quickstop/issues/7#issuecomment-123'}}

    def write(self, path, data):
        path = self.root / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data) if isinstance(data, dict) else data)

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.root), *args], check=True, capture_output=True, text=True).stdout

    def commit(self):
        self.git('add', '.')
        self.git('commit', '-qm', 'Synthetic fixture')

    def publish(self):
        self.write('releases.json', {'schema': 1, 'releases': [self.record]})
        m.validate(self.root, write=True)
        return json.loads((self.root / '.claude-plugin/marketplace.json').read_text())['plugins']

    def test_candidate_is_not_advertised(self):
        m.validate(self.root, write=True)
        self.assertEqual(json.loads((self.root / '.claude-plugin/marketplace.json').read_text())['plugins'], [])

    def test_pin_and_candidate_changes_preserve_accepted_bytes(self):
        plugins = self.publish()
        self.assertEqual(plugins[0]['source']['sha'], self.sha)
        self.write('plugins/sample/README.md', 'Unaccepted rewrite')
        newer = dict(self.manifest, version='2.0.0')
        self.write('plugins/sample/.claude-plugin/plugin.json', newer)
        self.assertEqual(self.publish(), plugins)
        self.assertEqual(self.publish()[0]['version'], '1.0.0')

    def test_digest_includes_names_modes_and_binary_content(self):
        original = m.package_digest(self.root, self.target['path'])
        self.assertEqual(original, self.record['sha256'])
        (self.root / 'plugins/sample/data.bin').write_bytes(bytes(range(256)))
        digest = m.package_digest(self.root, self.target['path'])
        self.assertNotEqual(original, digest)
        (self.root / 'plugins/sample/data.bin').chmod(0o755)
        self.assertNotEqual(digest, m.package_digest(self.root, self.target['path']))

    def test_tampered_digest_refused(self):
        self.record['sha256'] = 'b' * 64
        with self.assertRaisesRegex(m.Invalid, 'digest mismatch'):
            self.publish()

    def test_unaccepted_record_refused(self):
        self.record['provenance']['kind'] = 'rejected'
        with self.assertRaisesRegex(m.Invalid, 'independent acceptance'):
            self.publish()

    def test_legacy_exception_cannot_accept_new_plugin(self):
        self.record['provenance'] = {'kind': 'legacy-preserved'}
        with self.assertRaisesRegex(m.Invalid, 'only preserves'):
            self.publish()

    def test_missing_lock_fails_closed(self):
        (self.root / 'releases.json').unlink()
        with self.assertRaises(m.Invalid):
            m.validate(self.root, write=True)

    def test_rejected_gate_never_changes_lock(self):
        before = (self.root / 'releases.json').read_bytes()
        failure = subprocess.CompletedProcess([], 1, '', 'No independent acceptance')
        with patch.object(r.subprocess, 'run', return_value=failure):
            with self.assertRaisesRegex(r.m.Invalid, 'gate rejected'):
                r.promote(self.root, 'sample', 'claude-code', self.sha, 7, 'sha256:' + 'a' * 64, 'fixture-maintainer')
        self.assertEqual((self.root / 'releases.json').read_bytes(), before)

    def test_restore_previous_pointer(self):
        previous = self.publish()
        old = json.loads(json.dumps(self.record))
        self.write('plugins/sample/README.md', 'Second synthetic version')
        self.manifest['version'] = '1.1.0'
        self.write('plugins/sample/.claude-plugin/plugin.json', self.manifest)
        self.commit()
        self.record['commit'] = self.git('rev-parse', 'HEAD').strip()
        self.record['sha256'] = m.package_digest(self.root, self.target['path'], self.record['commit'])
        self.assertNotEqual(self.publish(), previous)
        self.record = old
        self.assertEqual(self.publish(), previous)

    def test_successful_gate_prepares_exact_pin_and_retry_is_idempotent(self):
        actual_run = subprocess.run
        evidence = {'candidate': {'sha': self.sha, 'artifact': 'sha256:' + 'a' * 64}, 'acceptance': self.record['provenance']['acceptance']}
        def run(args, **kwargs):
            if str(args[0]).endswith('/sdlc-release'):
                return subprocess.CompletedProcess(args, 0, json.dumps(evidence), '')
            return actual_run(args, **kwargs)
        with patch.object(r.subprocess, 'run', side_effect=run):
            r.promote(self.root, 'sample', 'claude-code', self.sha, 7, 'sha256:' + 'a' * 64, 'fixture-maintainer')
            before = (self.root / 'releases.json').read_bytes()
            (self.root / '.claude-plugin/marketplace.json').write_text('interrupted projection')
            r.promote(self.root, 'sample', 'claude-code', self.sha, 7, 'sha256:' + 'a' * 64, 'fixture-maintainer')
            self.assertEqual((self.root / 'releases.json').read_bytes(), before)
        self.assertEqual(json.loads(before)['releases'][0]['commit'], self.sha)

    def test_codex_pin_and_pi_install_command_use_accepted_identity(self):
        codex = dict(self.target, format='agent-plugin')
        pi = dict(self.target, format='pi-package')
        catalog = json.loads(json.dumps(self.catalog))
        catalog['plugins'][0]['targets'] = {'codex': codex, 'pi': pi}
        packages = {('sample', 'codex'): (codex, self.manifest), ('sample', 'pi'): (pi, self.manifest)}
        records = {('sample', 'codex'): dict(self.record, target=codex), ('sample', 'pi'): dict(self.record, target=pi)}
        out = m.projections(catalog, packages, records)
        source = json.loads(out['.agents/plugins/marketplace.json'])['plugins'][0]['source']
        self.assertEqual(source['sha'], self.sha)
        self.assertEqual(source['source'], 'git-subdir')
        self.assertIn('git checkout --detach ' + self.sha, out['docs/pi-packages.md'])
        self.assertIn('--sha256 ' + self.record['sha256'], out['docs/pi-packages.md'])
