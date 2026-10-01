"""Behavioral regression checks for Claudit, using isolated synthetic consumers."""
import concurrent.futures
import contextlib
import datetime as dt
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

RUNTIME = Path(__file__).resolve().parents[1] / 'plugins/claudit/scripts/runtime.py'
spec = importlib.util.spec_from_file_location('claudit_runtime', RUNTIME)
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.cache = self.base / 'cache'
        self.home = self.base / 'home'
        self.home.mkdir()
        self.config = self.home / '.claude'
        self.project = self.base / 'project'
        self.project.mkdir()
        self.env = patch.dict(os.environ, {'CLAUDIT_CACHE_DIR': str(self.cache)}, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)

    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value) if not isinstance(value, str) else value)
        return path

    def bundle(self, domain='core-config', host='2.1.287'):
        class Response(io.BytesIO):
            def geturl(self):
                return self.url
        def opener(request, timeout):
            result = Response(b'> ## Documentation Index\n> Fetch index\n\n# Actual source\n\n## Behavior\nActual content\n')
            result.url = request.full_url
            return result
        result = r.fetch(self.cache, domain, host, opener)
        bundle = r.read_json(result['bundle'])
        research = self.write(Path(result['research_output']), {
            'claims': [{'text': 'Observed source behavior', 'source_ids': [s['id']], 'section': 'Behavior'} for s in bundle['sources']], 'gaps': [], 'limitations': []})
        return result['bundle'], research

    def seed(self, domain='core-config', host='2.1.287'):
        bundle, research = self.bundle(domain, host)
        return r.commit_cache(self.cache, bundle, research)

    def cli(self, *args):
        return subprocess.run([sys.executable, str(RUNTIME), *args], text=True, capture_output=True, env={**os.environ, 'CLAUDIT_CACHE_DIR': str(self.cache)})

    def git(self, *args, root=None):
        return subprocess.check_output(['git', '-C', str(root or self.project), *args], stderr=subprocess.DEVNULL).decode().strip()

    def repo(self):
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Synthetic Test')
        self.git('config', 'user.email', 'synthetic@example.invalid')
        self.write(self.project / 'CLAUDE.md', '# Project\n\nExisting conventions\n')
        self.write(self.project / 'other.txt', 'original\n')
        self.git('add', 'CLAUDE.md', 'other.txt')
        self.git('commit', '-m', 'fixture')

    def test_status_cli_default_is_nonmutating_and_unknown_domain_fails(self):
        result = self.cli('status', '--host-version', '2.1.287 (Claude Code)')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([x['state'] for x in json.loads(result.stdout)], ['missing'] * 3)
        self.assertFalse(self.cache.exists())
        self.assertNotEqual(self.cli('status', '--host-version', '2.1.287', 'typo').returncode, 0)

    def test_single_domain_first_use_and_upgrade_preserve_others(self):
        self.seed('core-config', '2.1.100')
        old = (self.cache / 'v2/core-config.json').read_bytes()
        self.seed('ecosystem')
        result = self.cli('status', '--host-version', '2.1.287', 'ecosystem', 'core-config')
        self.assertEqual([x['state'] for x in json.loads(result.stdout)], ['fresh', 'stale'])
        self.assertEqual((self.cache / 'v2/core-config.json').read_bytes(), old)
        self.assertEqual(r.domain_state(self.cache, 'optimization', '2.1.287')['state'], 'missing')

    def test_sources_are_progressively_readable_and_integrity_checked(self):
        bundle, research = self.bundle()
        data = r.read_json(bundle)
        self.assertNotIn('content', data['sources'][0])
        self.assertIn('\n# Actual source\n', Path(data['sources'][0]['content_path']).read_text())
        Path(data['sources'][0]['content_path']).write_text('changed')
        with self.assertRaises(ValueError):
            r.commit_cache(self.cache, bundle, research)

    def test_failed_research_preserves_last_good_and_reports_degraded(self):
        self.seed()
        original = (self.cache / 'v2/core-config.json').read_bytes()
        def fail(*args, **kwargs):
            raise OSError('network unavailable')
        result = r.fetch(self.cache, 'core-config', '2.1.287', fail)
        self.assertFalse(result['commit_allowed'])
        self.assertEqual((self.cache / 'v2/core-config.json').read_bytes(), original)
        self.assertEqual(r.domain_state(self.cache, 'core-config', '2.1.287')['state'], 'degraded')
        data = json.loads(self.cli('knowledge', '--host-version', '2.1.287', 'core-config').stdout)[0]
        self.assertIsNotNone(data['knowledge'])
        self.assertEqual(data['state'], 'degraded')

    def test_partial_or_unsupported_synthesis_cannot_replace_last_good(self):
        self.seed()
        original = (self.cache / 'v2/core-config.json').read_bytes()
        bundle, research = self.bundle()
        self.write(research, {'claims': [{'text': 'Unsupported', 'source_ids': ['imaginary'], 'section': 'none'}], 'gaps': []})
        with self.assertRaises(ValueError):
            r.commit_cache(self.cache, bundle, research)
        self.assertEqual((self.cache / 'v2/core-config.json').read_bytes(), original)

    def test_concurrent_domains_and_same_domain_newer_wins(self):
        bundles = [self.bundle(d) for d in r.DOMAINS]
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            outcomes = list(executor.map(lambda args: r.commit_cache(self.cache, *args), bundles))
        self.assertEqual({x['domain'] for x in outcomes}, set(r.DOMAINS))
        self.assertTrue(all(r.domain_state(self.cache, d, '2.1.287')['state'] == 'fresh' for d in r.DOMAINS))
        older = self.bundle()
        newer = self.bundle()
        r.commit_cache(self.cache, *newer)
        self.assertEqual(r.commit_cache(self.cache, *older)['status'], 'superseded')

    def test_legacy_and_history_never_deleted(self):
        legacy = self.write(self.cache / 'core-config.md', 'old memory')
        self.assertEqual(r.domain_state(self.cache, 'core-config', '2.1.287')['state'], 'stale')
        self.seed()
        previous = (self.cache / 'v2/core-config.json').read_bytes()
        self.seed()
        self.assertEqual(legacy.read_text(), 'old memory')
        self.assertIn(previous, [p.read_bytes() for p in (self.cache / 'v2/history').glob('*.json')])

    def test_malformed_records_are_corrupt_not_tracebacks(self):
        self.seed()
        path = self.cache / 'v2/core-config.json'
        original = r.read_json(path)
        for mutation in ('timestamp', 'url', 'source_count', 'claims', 'no_timezone'):
            with self.subTest(mutation=mutation):
                value = json.loads(json.dumps(original))
                if mutation == 'timestamp': value['fetched_at'] = None
                if mutation == 'url': value['sources'][0]['url'] = None
                if mutation == 'source_count': value['sources'] = value['sources'][:1]
                if mutation == 'claims': value['claims'] = [None]
                if mutation == 'no_timezone': value['fetched_at'] = '2026-10-01T12:00:00'
                self.write(path, value)
                result = self.cli('status', '--host-version', '2.1.287', 'core-config')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)[0]['state'], 'corrupt')
        self.write(self.cache / 'v2/core-config.attempt.json', {'status': 'failed', 'at': None})
        self.assertEqual(r.domain_state(self.cache, 'core-config', '2.1.287')['state'], 'degraded')

    def test_ttl_missing_and_corrupt_states_agree_for_status_knowledge(self):
        self.seed()
        path = self.cache / 'v2/core-config.json'
        record = r.read_json(path)
        record['fetched_at'] = r.stamp(r.now() - dt.timedelta(days=8))
        self.write(path, record)
        self.assertEqual(r.domain_state(self.cache, 'core-config', '2.1.287')['state'], 'stale')
        path.unlink()
        for command in ('status', 'knowledge'):
            self.assertEqual(json.loads(self.cli(command, '--host-version', '2.1.287', 'core-config').stdout)[0]['state'], 'missing')
        path.write_text('{')
        self.assertEqual(r.domain_state(self.cache, 'core-config', '2.1.287')['state'], 'corrupt')

    def test_discovery_scopes_mcp_redaction_memory_and_critical_budget(self):
        self.repo()
        self.write(self.home / '.claude.json', {'secret': 'DO-NOT-EXPOSE', 'mcpServers': {'personal': {'command': 'node', 'args': ['PRIVATE'], 'env': None}}, 'projects': {str(self.project): {'mcpServers': {'local': {'type': 'http', 'url': 'https://private/?token=SECRET'}}}}})
        self.write(self.project / '.mcp.json', {'mcpServers': {'shared': {'type': 'http', 'url': 'https://private'}}})
        self.write(self.config / 'settings.json', {'autoMemoryDirectory': str(self.home / 'custom-memory')})
        self.write(self.project / 'nested/AGENTS.md', 'conditional fallback')
        self.write(self.project / 'nested/.claude/rules/testing.md', 'conditional rule')
        for i in range(15): self.write(self.project / f'area{i}/CLAUDE.md', 'nested')
        data = r.discover(self.project, self.home, self.config, self.base / 'managed', limit=5)
        self.assertEqual({m['scope'] for m in data['mcp']}, {'user', 'local', 'project'})
        self.assertNotIn('DO-NOT-EXPOSE', json.dumps(data))
        self.assertNotIn('PRIVATE', json.dumps(data))
        self.assertNotIn('token=SECRET', json.dumps(data))
        self.assertTrue(data['coverage']['omitted'])
        omitted_paths = {x['path'] for x in data['coverage']['omitted']}
        self.assertIn(str(self.project / 'nested/AGENTS.md'), omitted_paths)
        self.assertIn(str(self.project / 'nested/.claude/rules/testing.md'), omitted_paths)
        self.assertTrue(any(f['path'] == str(self.project / '.mcp.json') for f in data['files']))
        self.assertTrue(any(f['path'] == str(self.home / 'custom-memory/MEMORY.md') for f in data['files']))

    def test_project_only_never_reads_personal_sources(self):
        self.repo()
        self.write(self.config / 'settings.json', {'model': 'private'})
        self.write(self.project / '.claude/settings.local.json', {'model': 'local-private'})
        reads = []
        actual = r.read_json
        def read(path):
            reads.append(str(path))
            return actual(path)
        with patch.object(r, 'read_json', side_effect=read):
            data = r.discover(self.project, self.home, self.config, self.base / 'managed', scope='project')
        self.assertFalse(any(str(self.home) in p or 'settings.local' in p for p in reads))
        self.assertFalse(any(f['scope'] in ('user', 'personal', 'local') for f in data['files']))

    def test_non_git_auto_global_and_explicit_directory_scope(self):
        self.write(self.project / 'CLAUDE.md', 'directory instructions')
        auto = r.discover(self.project, self.home, self.config, self.base / 'managed')
        self.assertEqual(auto['scope'], 'global')
        self.assertIsNone(auto['git_root'])
        self.assertFalse(any(f['path'] == str(self.project / 'CLAUDE.md') for f in auto['files']))
        explicit = r.discover(self.project, self.home, self.config, self.base / 'managed', scope='project')
        self.assertTrue(any(f['path'] == str(self.project / 'CLAUDE.md') for f in explicit['files']))

    def test_config_override_and_plugin_component_add_replace_merge(self):
        self.repo()
        config = self.base / 'custom'
        self.write(config / '.claude.json', {'mcpServers': {'override': {'command': 'node'}}})
        root = self.base / 'plugin'
        self.write(root / 'commands/old.md', 'supported')
        self.write(root / 'custom/new.md', 'command')
        self.write(root / 'skills/a/SKILL.md', 'skill')
        self.write(root / 'extra/b/SKILL.md', 'skill')
        self.write(root / 'hooks/hooks.json', {'hooks': {}})
        self.write(root / '.claude-plugin/plugin.json', {'name': 'fixture', 'commands': './custom', 'skills': './extra', 'hooks': {'hooks': {}}})
        components = r.plugin_components(root)
        self.assertTrue(any(c.get('path') == str(root / 'custom') for c in components))
        self.assertFalse(any(c.get('path') == str(root / 'commands') for c in components))
        self.assertEqual(len([c for c in components if c['kind'] == 'skills']), 2)
        self.assertEqual(len([c for c in components if c['kind'] == 'hooks']), 2)
        (root / '.claude-plugin/plugin.json').unlink()
        self.assertTrue(any(c.get('path') == str(root / 'commands') for c in r.plugin_components(root)))
        data = r.discover(self.project, self.home, config, self.base / 'managed')
        self.assertEqual(data['mcp'][0]['name'], 'override')

    def test_decisions_separate_scopes_paths_projects_and_preserve_legacy(self):
        a = r.identity('local', self.project, self.project / '.claude/settings.local.json', 'security', 'issue')
        b = r.identity('project', self.project, self.project / '.claude/settings.json', 'security', 'issue')
        self.assertNotEqual(a, b)
        self.assertNotEqual(b, r.identity('project', self.project, self.project / 'nested/.claude/settings.json', 'security', 'issue'))
        destination = self.cache / 'decisions-v2.json'
        entry = self.base / 'entry.json'
        for project in ('projectA', 'projectB'):
            self.write(entry, {'fingerprint': a, 'action': 'accepted', 'project_id': project})
            r.decision_save(destination, entry)
        self.assertEqual(len(r.decisions_read(destination)['decisions']), 2)
        with self.assertRaises(ValueError): r.decision_save(self.project / 'shared.json', entry, shared=True)
        legacy = self.write(self.project / '.claude/claudit-decisions.json', {'schema_version': 1, 'decisions': [{'fingerprint': 'ambiguous'}]})
        original = legacy.read_bytes()
        self.assertEqual(r.decisions_read(legacy)['decisions'], [])
        self.assertTrue(r.decisions_read(legacy)['legacy_unmatched'])
        self.assertEqual(legacy.read_bytes(), original)
        self.assertFalse(r.personal_path('src/projects/CLAUDE.md'))
        self.assertFalse(r.personal_path('docs/memory/CLAUDE.md'))

    def test_malformed_decisions_do_not_overwrite(self):
        destination = self.write(self.cache / 'decisions-v2.json', {'schema_version': 2, 'decisions': [None]})
        original = destination.read_bytes()
        with self.assertRaises(ValueError): r.decisions_read(destination)
        self.assertEqual(destination.read_bytes(), original)

    def prepare(self, paths=None):
        return r.prepare_pr(self.project, self.base / 'delivery', 'claudit/test', paths or ['CLAUDE.md'])

    def test_isolated_delivery_preserves_staged_dirty_same_file_and_untracked(self):
        self.repo()
        self.write(self.project / 'CLAUDE.md', '# User draft\n')
        self.git('add', 'CLAUDE.md')
        self.write(self.project / 'CLAUDE.md', '# More unstaged user draft\n')
        self.write(self.project / 'other.txt', 'unrelated edit\n')
        self.write(self.project / 'untracked.txt', 'private work\n')
        before = r.consumer_snapshot(self.project)
        receipt = self.prepare()
        self.assertEqual(receipt['dirty_targets_excluded'], ['CLAUDE.md'])
        self.write(Path(receipt['worktree']) / 'CLAUDE.md', '# Project\n\nSelected fix\n')
        self.assertEqual(r.verify_pr(receipt['receipt'])['status'], 'verified')
        self.git('add', 'CLAUDE.md', root=receipt['worktree'])
        self.git('commit', '-m', 'selected fix', root=receipt['worktree'])
        self.assertEqual(r.verify_pr(receipt['receipt'])['status'], 'verified')
        self.assertEqual(r.consumer_snapshot(self.project), before)

    def test_delivery_rejects_extra_personal_and_symlink_paths(self):
        self.repo()
        with self.assertRaises(ValueError): self.prepare(['.claude/settings.local.json'])
        receipt = self.prepare()
        worktree = Path(receipt['worktree'])
        self.write(worktree / 'extra.txt', 'unselected')
        with self.assertRaises(ValueError): r.verify_pr(receipt['receipt'])
        (worktree / 'extra.txt').unlink()
        (worktree / 'CLAUDE.md').unlink()
        (worktree / 'CLAUDE.md').symlink_to(self.project / 'CLAUDE.md')
        with self.assertRaises(ValueError): r.verify_pr(receipt['receipt'])

    def test_delivery_detects_untracked_content_race_and_unicode_paths(self):
        self.repo()
        name = 'étrange\nfile.md'
        self.write(self.project / name, 'original')
        self.git('add', name)
        self.git('commit', '-m', 'unicode fixture')
        self.write(self.project / 'untracked.txt', 'before')
        receipt = self.prepare([name])
        self.write(Path(receipt['worktree']) / name, 'selected change')
        self.assertEqual(r.verify_pr(receipt['receipt'])['paths'], [name])
        self.write(self.project / 'untracked.txt', 'after')
        with self.assertRaises(ValueError): r.verify_pr(receipt['receipt'])

    def test_future_or_corrupt_cache_can_recover(self):
        self.seed()
        path = self.cache / 'v2/core-config.json'
        record = r.read_json(path)
        record['fetched_at'] = r.stamp(r.now() + dt.timedelta(days=365))
        self.write(path, record)
        self.assertEqual(r.domain_state(self.cache, 'core-config', '2.1.287')['state'], 'stale')
        self.assertEqual(self.seed()['status'], 'committed')
        self.assertEqual(r.domain_state(self.cache, 'core-config', '2.1.287')['state'], 'fresh')

    def test_retained_source_loss_is_not_fresh(self):
        self.seed()
        record = r.read_json(self.cache / 'v2/core-config.json')
        Path(record['sources'][0]['content_path']).write_text('tampered')
        self.assertEqual(r.domain_state(self.cache, 'core-config', '2.1.287')['state'], 'corrupt')
        Path(record['sources'][0]['content_path']).unlink()
        self.assertEqual(r.domain_state(self.cache, 'core-config', '2.1.287')['state'], 'corrupt')

    def test_global_omits_project_plugin_and_malformed_mcp_stays_unknown(self):
        self.repo()
        self.write(self.config / 'plugins/installed_plugins.json', {'plugins': {'private-project': [{'scope': 'project', 'projectPath': str(self.project), 'installPath': str(self.base / 'plugin')}]}})
        global_data = r.discover(self.project, self.home, self.config, self.base / 'managed', scope='global')
        self.assertEqual(global_data['plugins'], [])
        self.write(self.project / '.mcp.json', {'mcpServers': []})
        data = r.discover(self.project, self.home, self.config, self.base / 'managed', scope='project')
        self.assertTrue(any('Invalid mcpServers' in g for g in data['coverage']['gaps']))

    def test_outside_plugin_paths_and_project_symlinks_never_read(self):
        self.repo()
        private = self.write(self.home / 'private.json', {'autoMemoryDirectory': str(self.home / 'secret-memory')})
        (self.project / '.claude').mkdir()
        (self.project / '.claude/settings.json').symlink_to(private)
        root = self.base / 'plugin'
        self.write(root / '.claude-plugin/plugin.json', {'name': 'fixture', 'commands': '../home/private.json'})
        self.write(self.config / 'plugins/installed_plugins.json', {'plugins': {'fixture': [{'scope': 'user', 'installPath': str(root)}]}})
        data = r.discover(self.project, self.home, self.config, self.base / 'managed')
        self.assertFalse(any(f['path'] == str(private) for f in data['files']))
        target = next(f for f in data['files'] if f['path'] == str(self.project / '.claude/settings.json'))
        self.assertEqual(target['state'], 'symlink')
        self.assertFalse(any('secret-memory' in f['path'] for f in data['files']))

    def test_committed_extra_file_cannot_be_masked_by_worktree_deletion(self):
        self.repo()
        receipt = self.prepare()
        worktree = Path(receipt['worktree'])
        self.write(worktree / 'CLAUDE.md', 'selected')
        self.write(worktree / 'unselected.txt', 'unselected')
        self.git('add', 'CLAUDE.md', 'unselected.txt', root=worktree)
        self.git('commit', '-m', 'mixed commit', root=worktree)
        (worktree / 'unselected.txt').unlink()
        with self.assertRaises(ValueError): r.verify_pr(receipt['receipt'])

    def test_shared_write_rejects_existing_private_records(self):
        private = {'fingerprint': r.identity('local', self.project, self.project / '.claude/settings.local.json', 'security', 'issue'), 'project_id': 'private-project', 'action': 'accepted'}
        destination = self.write(self.project / 'shared.json', {'schema_version': 2, 'decisions': [private]})
        original = destination.read_bytes()
        entry = self.write(self.base / 'entry.json', {'fingerprint': r.identity('project', self.project, self.project / 'CLAUDE.md', 'security', 'issue'), 'action': 'accepted'})
        with self.assertRaises(ValueError): r.decision_save(destination, entry, shared=True)
        self.assertEqual(destination.read_bytes(), original)

    def test_consumer_branch_switch_at_same_head_is_detected(self):
        self.repo()
        receipt = self.prepare()
        self.git('checkout', '-b', 'other-branch')
        with self.assertRaises(ValueError): r.verify_pr(receipt['receipt'])

    def test_concurrent_synthesis_outputs_are_issued_and_isolated(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            pairs = list(executor.map(lambda _: self.bundle(), range(2)))
        self.assertNotEqual(pairs[0][1], pairs[1][1])
        for bundle, research in pairs:
            self.assertEqual(Path(research), Path(bundle).parent / 'synthesis.json')
            self.assertIn(r.commit_cache(self.cache, bundle, research)['status'], ('committed', 'superseded'))
        shared = self.write(self.base / 'shared-research.json', r.read_json(pairs[0][1]))
        with self.assertRaisesRegex(ValueError, 'research_output'):
            r.commit_cache(self.cache, pairs[0][0], shared)
        with self.assertRaisesRegex(ValueError, 'research_output'):
            r.commit_cache(self.cache, pairs[0][0], pairs[1][1])

    def test_limited_valid_synthesis_retains_limits_but_fatal_gaps_preserve_last_good(self):
        bundle, research = self.bundle()
        synthesis = r.read_json(research)
        limits = ['Linked provider page outside supplied sources was not reviewed',
                  'Account-specific feature availability is unknown']
        synthesis['limitations'] = limits
        self.write(research, synthesis)
        self.assertEqual(r.commit_cache(self.cache, bundle, research)['status'], 'committed')
        state = r.domain_state(self.cache, 'core-config', '2.1.287')
        self.assertEqual(state['state'], 'fresh')
        self.assertEqual(state['limitations'], limits)
        knowledge = json.loads(self.cli('knowledge', '--host-version', '2.1.287', 'core-config').stdout)[0]
        self.assertEqual(knowledge['knowledge']['limitations'], limits)
        before = (self.cache / 'v2/core-config.json').read_bytes()
        for field, values in (('gaps', ['Required supplied memory source is unreadable']),
                              ('gaps', [None]), ('limitations', 'not a list'),
                              ('limitations', [None])):
            newer_bundle, newer_research = self.bundle()
            invalid = r.read_json(newer_research)
            invalid[field] = values
            self.write(newer_research, invalid)
            with self.assertRaises(ValueError):
                r.commit_cache(self.cache, newer_bundle, newer_research)
            self.assertEqual((self.cache / 'v2/core-config.json').read_bytes(), before)

    def test_discovery_loads_scoped_decisions_without_other_project_leakage_or_writes(self):
        self.repo()
        def entry(scope, path, project_id=None, label='applicable'):
            value = {'fingerprint': r.identity(scope, self.project, self.project / path, 'security', 'issue'),
                     'action': 'rejected', 'reason': label}
            if project_id: value['project_id'] = project_id
            return value
        project_record = entry('project', 'CLAUDE.md', str(self.project))
        local_record = entry('local', '.claude/settings.local.json', str(self.project))
        user_record = entry('user', '.claude/settings.json')
        unrelated = entry('project', 'CLAUDE.md', str(self.base / 'other-project'), 'UNRELATED-PRIVATE-REASON')
        self.write(self.cache / 'decisions-v2.json', {'schema_version': 2, 'decisions': [project_record, local_record, user_record, unrelated]})
        self.write(self.project / '.claude/claudit-decisions-shared-v2.json', {'schema_version': 2, 'decisions': [entry('project', 'CLAUDE.md', label='shared decision')]})
        self.write(self.project / '.claude/claudit-decisions.json', {'schema_version': 1, 'decisions': [{'fingerprint': 'ambiguous', 'reason': 'LEGACY-PRIVATE-REASON'}]})
        def snapshot():
            return {str(p): p.read_bytes() for p in self.base.rglob('*') if p.is_file()}
        before = snapshot()
        for scope, expected in (('comprehensive', ['project', 'local', 'user', 'project']),
                                ('project', ['project', 'project']), ('global', ['user'])):
            with self.subTest(scope=scope):
                data = r.discover(self.project, self.home, self.config, self.base / 'managed', scope=scope)
                context = data['decision_context']
                actual = [json.loads(item['record']['fingerprint'])[0] for item in context['decisions']]
                self.assertEqual(actual, expected)
                self.assertNotIn('UNRELATED-PRIVATE-REASON', json.dumps(data))
                self.assertNotIn('LEGACY-PRIVATE-REASON', json.dumps(data))
                self.assertLess(list(data).index('decision_context'), list(data).index('files'))
                self.assertEqual(snapshot(), before)
        comprehensive = r.discover(self.project, self.home, self.config, self.base / 'managed')
        self.assertEqual(sum(s['legacy_unmatched_count'] for s in comprehensive['decision_context']['stores']), 1)

    def test_decision_context_matches_main_worktree_and_applicable_plugin_identity(self):
        self.repo()
        main = self.base / 'main-root'
        plugin_root = self.base / 'installed-plugin'
        entries = []
        for scope, namespace, label in (('local', str(main), 'main-worktree'),
                                         ('plugin', str(plugin_root), 'applicable-plugin'),
                                         ('plugin', 'other-plugin', 'excluded-plugin')):
            entries.append({'fingerprint': r.identity(scope, self.project, self.project / 'CLAUDE.md', 'security', 'issue'),
                            'project_id': namespace, 'action': 'accepted', 'reason': label})
        self.write(self.cache / 'decisions-v2.json', {'schema_version': 2, 'decisions': entries})
        context = r.decision_context(self.cache, self.project, main, 'comprehensive', [{'name': 'plugin', 'root': str(plugin_root)}])
        self.assertEqual([x['record']['reason'] for x in context['decisions']], ['main-worktree', 'applicable-plugin'])
        self.write(self.cache / 'decisions-v2.json', '{bad')
        context = r.decision_context(self.cache, self.project, main, 'comprehensive', [])
        self.assertEqual(context['stores'][0]['state'], 'corrupt')
        self.assertTrue(context['gaps'])
        self.assertEqual(context['decisions'], [])

    def test_denied_fetch_failure_receipt_preserves_existing_knowledge(self):
        self.seed()
        record = self.cache / 'v2/core-config.json'
        before = record.read_bytes()
        denied = self.cli('cache-fail', 'core-config', 'official source fetch denied by host permissions')
        self.assertEqual(denied.returncode, 0, denied.stderr)
        self.assertEqual(record.read_bytes(), before)
        status = json.loads(self.cli('status', '--host-version', '2.1.287', 'core-config').stdout)[0]
        self.assertEqual(status['state'], 'degraded')
        self.assertIn('denied by host permissions', status['last_failure'])


if __name__ == '__main__':
    unittest.main()
