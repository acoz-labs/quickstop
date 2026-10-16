import json
from pathlib import Path
import subprocess
import sys
import unittest
import tempfile
import hashlib
import os
import re
import shutil
import runpy
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'plugins/codex/shipshape/scripts/shipshape.py'


class ShipshapeTests(unittest.TestCase):
    def test_copied_package_runs_contained_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            installed = Path(directory) / 'installed'
            shutil.copytree(CLI.parents[1], installed)
            consumer = Path(directory) / 'consumer'
            consumer.mkdir()
            actual = subprocess.run([sys.executable, str(installed / 'examples/run.py')],
                                    cwd=consumer, capture_output=True, text=True)
            self.assertEqual(actual.returncode, 0, actual.stdout + actual.stderr)
            self.assertEqual(json.loads(actual.stdout)['synthetic'], 'passed')

    def test_missing_options_are_json(self):
        actual = self.invoke('contract', 'check')
        self.assertEqual(actual.returncode, 2)
        self.assertTrue(actual.stdout.strip(), actual.stderr)
        self.assertEqual(json.loads(actual.stdout)['class'], 'invalid-policy')

    def test_deep_json_is_structured(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'nested.json'
            path.write_text('[' * 2000 + '0' + ']' * 2000)
            actual = self.invoke('result', 'check', '--contract', path, '--result', path)
            self.assertEqual(actual.returncode, 2, actual.stderr)
            self.assertEqual(json.loads(actual.stdout)['class'], 'invalid-policy')

    def invoke(self, *args):
        return subprocess.run([sys.executable, str(CLI), *map(str, args)], capture_output=True, text=True)

    def save(self, path, value):
        path.write_text(json.dumps(value))
        return path

    def fixture(self, directory):
        root = Path(directory) / 'consumer'
        root.mkdir()
        (root / '.sdlc').mkdir()
        (root / '.sdlc/config.json').write_text('{"delivery_profile":"artifact","validation":["bin/ci"]}')
        digest = hashlib.sha256((root / '.sdlc/config.json').read_bytes()).hexdigest()
        subprocess.run(['git', 'init', '-q', str(root)], check=True)
        subprocess.run(['git', '-C', str(root), 'add', '.sdlc/config.json'], check=True)
        subprocess.run(['git', '-C', str(root), '-c', 'user.name=Synthetic Fixture', '-c',
                        'user.email=fixture@example.invalid', 'commit', '-qm', 'Synthetic fixture'], check=True,
                       env=dict(os.environ, GIT_AUTHOR_NAME='Synthetic Fixture', GIT_AUTHOR_EMAIL='fixture@example.invalid',
                                GIT_COMMITTER_NAME='Synthetic Fixture', GIT_COMMITTER_EMAIL='fixture@example.invalid'))
        subprocess.run(['git', '-C', str(root), 'remote', 'add', 'origin', 'https://github.com/example/project.git'], check=True)
        head = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
        contract = dict(schema=1, run='fixture', attempt='one', generation=1,
                        repository='example/project', issue=152, base=head, head=head,
                        spec='1' * 64, config=digest, package='2' * 64, guide='3' * 40,
                        harness='4' * 64, role='author', process='worker-a', session='session-a',
                        scope=['src/example.py'], constraints=['no network'],
                        commands=['bin/ci'], effects=['proposal'], limits=['checkpoint'],
                        capabilities=[], stop=None, tools=[dict(path=sys.executable,
                        sha256=hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest())])
        return root, contract

    def test_origin_rejects_foreign_host(self):
        with tempfile.TemporaryDirectory() as directory:
            root, contract = self.fixture(directory)
            subprocess.run(['git', '-C', str(root), 'remote', 'set-url', 'origin',
                            'https://attacker.invalid/example/project.git'], check=True)
            cp = self.save(Path(directory) / 'contract.json', contract)
            actual = self.invoke('contract', 'check', '--repo-root', root, '--contract', cp)
            self.assertEqual(actual.returncode, 2, actual.stdout)
            self.assertEqual(json.loads(actual.stdout)['reason'], 'origin repository drift')

    def test_contract_requires_actual_repo_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root, contract = self.fixture(directory)
            nested = root / 'nested'
            nested.mkdir()
            shutil.copytree(root / '.sdlc', nested / '.sdlc')
            cp = self.save(Path(directory) / 'contract.json', contract)
            actual = self.invoke('contract', 'check', '--repo-root', nested, '--contract', cp)
            self.assertEqual(actual.returncode, 2, actual.stdout)
            self.assertEqual(json.loads(actual.stdout)['reason'], 'repository root drift')

    def test_github_origin_forms_and_authority_regressions(self):
        with tempfile.TemporaryDirectory() as directory:
            root, contract = self.fixture(directory)
            cp = self.save(Path(directory) / 'contract.json', contract)
            observations = self.save(Path(directory) / 'observations.json',
                                     {k: contract[k] for k in ('spec', 'package', 'guide', 'harness')})
            def check(origin, expected):
                subprocess.run(['git', '-C', str(root), 'remote', 'set-url', 'origin', origin], check=True)
                actual = self.invoke('contract', 'check', '--repo-root', root, '--contract', cp,
                                     '--observations', observations)
                self.assertEqual(actual.returncode, expected, (origin, actual.stdout, actual.stderr))
            for prefix in ('https://github.com/', 'ssh://git@github.com/', 'git@github.com:'):
                for suffix in ('', '.git'):
                    with self.subTest(prefix=prefix, suffix=suffix):
                        check(prefix + 'example/project' + suffix, 0)
            for origin in (
                    'https://user:secret@github.com/example/project.git',
                    'https://git@github.com/example/project.git',
                    'https://github.com:443/example/project.git',
                    'ssh://git@github.com:22/example/project.git',
                    'ssh://user@github.com/example/project.git',
                    'ssh://git:secret@github.com/example/project.git',
                    'https://github.com.attacker.invalid/example/project.git',
                    'ssh://git@github.com.attacker.invalid/example/project.git',
                    'git@github.com.attacker.invalid:example/project.git',
                    'https://github.com@attacker.invalid/example/project.git',
                    'http://github.com/example/project.git',
                    'git://github.com/example/project.git'):
                with self.subTest(origin=origin):
                    check(origin, 2)

    def test_origin_identity_must_match(self):
        with tempfile.TemporaryDirectory() as directory:
            root, contract = self.fixture(directory)
            contract['repository'] = 'other/project'
            cp = self.save(Path(directory) / 'contract.json', contract)
            actual = self.invoke('contract', 'check', '--repo-root', root, '--contract', cp)
            self.assertEqual(actual.returncode, 2, actual.stdout)

    def test_base_must_be_real_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            root, contract = self.fixture(directory)
            contract['base'] = 'f' * 40
            cp = self.save(Path(directory) / 'contract.json', contract)
            actual = self.invoke('contract', 'check', '--repo-root', root, '--contract', cp)
            self.assertEqual(actual.returncode, 2, actual.stdout)

    def test_base_must_be_ancestor(self):
        with tempfile.TemporaryDirectory() as directory:
            root, contract = self.fixture(directory)
            tree = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD^{tree}'], capture_output=True, text=True, check=True).stdout.strip()
            orphan = subprocess.run(['git', '-C', str(root), '-c', 'user.name=Synthetic Fixture', '-c',
                                     'user.email=fixture@example.invalid', 'commit-tree', tree, '-m', 'Unrelated fixture'],
                                    capture_output=True, text=True, check=True,
                                    env=dict(os.environ, GIT_AUTHOR_NAME='Synthetic Fixture', GIT_AUTHOR_EMAIL='fixture@example.invalid',
                                             GIT_COMMITTER_NAME='Synthetic Fixture', GIT_COMMITTER_EMAIL='fixture@example.invalid')).stdout.strip()
            contract['base'] = orphan
            cp = self.save(Path(directory) / 'contract.json', contract)
            actual = self.invoke('contract', 'check', '--repo-root', root, '--contract', cp)
            self.assertEqual(actual.returncode, 2, actual.stdout)

    def test_contract_preflight(self):
        with tempfile.TemporaryDirectory() as directory:
            root, contract = self.fixture(directory)
            path = self.save(Path(directory) / 'contract.json', contract)
            result = self.invoke('contract', 'check', '--repo-root', root, '--contract', path)
            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)['reason'], 'trusted observations required')

    def test_delivery_profile_required(self):
        with tempfile.TemporaryDirectory() as directory:
            root, contract = self.fixture(directory)
            config = root / '.sdlc/config.json'
            config.write_text('{"validation":["bin/ci"]}')
            contract['config'] = hashlib.sha256(config.read_bytes()).hexdigest()
            cp = self.save(Path(directory) / 'contract.json', contract)
            actual = self.invoke('contract', 'check', '--repo-root', root, '--contract', cp)
            self.assertEqual(actual.returncode, 2, actual.stdout)

    def test_missing_config_waits(self):
        with tempfile.TemporaryDirectory() as directory:
            root, contract = self.fixture(directory)
            (root / '.sdlc/config.json').unlink()
            cp = self.save(Path(directory) / 'contract.json', contract)
            actual = self.invoke('contract', 'check', '--repo-root', root, '--contract', cp)
            self.assertEqual(actual.returncode, 3, actual.stdout)

    def test_consumer_path_does_not_select_git(self):
        with tempfile.TemporaryDirectory() as directory:
            root, contract = self.fixture(directory)
            cp = self.save(Path(directory) / 'contract.json', contract)
            actual = subprocess.run([sys.executable, str(CLI), 'contract', 'check', '--repo-root', str(root), '--contract', str(cp)],
                                    env=dict(os.environ, PATH=str(Path(directory) / 'empty')), capture_output=True, text=True)
            self.assertEqual(actual.returncode, 3, actual.stdout)
        self.assertEqual(json.loads(actual.stdout)['reason'], 'trusted observations required')

    def test_observed_spec_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root, contract = self.fixture(directory)
            cp = self.save(Path(directory) / 'contract.json', contract)
            observed = {key: contract[key] for key in ('spec', 'package', 'guide', 'harness')}
            observed['spec'] = 'f' * 64
            op = self.save(Path(directory) / 'observations.json', observed)
            actual = self.invoke('contract', 'check', '--repo-root', root, '--contract', cp, '--observations', op)
            self.assertEqual(actual.returncode, 2, actual.stdout)
            self.assertEqual(json.loads(actual.stdout)['reason'], 'observation drift: spec')

    def test_observation_comparator_regressions(self):
        with tempfile.TemporaryDirectory() as directory:
            root, contract = self.fixture(directory)
            cp = self.save(Path(directory) / 'contract.json', contract)
            observed = {key: contract[key] for key in ('spec', 'package', 'guide', 'harness')}
            op = self.save(Path(directory) / 'observations.json', observed)
            args = ('contract', 'check', '--repo-root', root, '--contract', cp, '--observations', op)
            self.assertEqual(self.invoke(*args).returncode, 0)
            for key in ('package', 'guide', 'harness'):
                with self.subTest(key=key):
                    self.save(op, dict(observed, **{key: 'f' * len(observed[key])}))
                    actual = self.invoke(*args)
                    self.assertEqual(json.loads(actual.stdout)['reason'], 'observation drift: ' + key)
            for malformed in ([], None, {'spec': {}}, dict(observed, harness=[])):
                self.save(op, malformed)
                self.assertEqual(self.invoke(*args).returncode, 2)

    def test_contract_rejects_policy_mutations(self):
        with tempfile.TemporaryDirectory() as directory:
            root, contract = self.fixture(directory)
            mutations = [('schema', 2), ('head', 'main'), ('base', ''), ('spec', ''),
                         ('package', ''), ('guide', ''), ('harness', ''), ('issue', True),
                         ('scope', ['../escape']), ('effects', ['merge']), ('commands', []),
                         ('unexpected', True), ('config', '0' * 64)]
            for key, value in mutations:
                with self.subTest(key=key):
                    changed = dict(contract, **{key: value})
                    path = self.save(Path(directory) / 'contract.json', changed)
                    result = self.invoke('contract', 'check', '--repo-root', root, '--contract', path)
                    self.assertEqual(result.returncode, 2, result.stdout)

    def test_missing_tool_and_stop_wait(self):
        with tempfile.TemporaryDirectory() as directory:
            root, contract = self.fixture(directory)
            for change in [dict(tools=[dict(path='/nonexistent-tool', sha256='0' * 64)]),
                           dict(stop='paused'), dict(capabilities=['independent-reviewer'])]:
                path = self.save(Path(directory) / 'contract.json', dict(contract, **change))
                result = self.invoke('contract', 'check', '--repo-root', root, '--contract', path)
                self.assertEqual(result.returncode, 3, result.stdout)

    def test_unknown_action_fails_closed(self):
        result = subprocess.run([sys.executable, str(CLI), 'launch'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertTrue(result.stdout.strip(), 'CLI must emit a structured policy rejection')
        self.assertEqual(json.loads(result.stdout)['class'], 'invalid-policy')

    def result_fixture(self, contract):
        return dict(schema=2, contract=hashlib.sha256(json.dumps(contract, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
                    role=contract['role'], process=contract['process'], session=contract['session'],
                    author_process='other-process' if contract['role'] == 'reviewer' else contract['process'],
                    author_session='other-session' if contract['role'] == 'reviewer' else contract['session'],
                    outcome='passed', commands=[dict(command='bin/ci', status='executed', exit=0)],
                    evidence=[dict(locator='evidence/commands.log', sha256='5' * 64)],
                    findings=[], next_action='independent-review', limits=contract['limits'], effects=contract['effects'])

    def test_blocked_not_run_persists(self):
        with tempfile.TemporaryDirectory() as directory:
            root, c = self.fixture(directory)
            r = self.result_fixture(c)
            r.update(schema=2, outcome='blocked', commands=[dict(command='bin/ci', status='not-run', reason='interrupted')])
            cp = self.save(Path(directory) / 'contract.json', c)
            rp = self.save(Path(directory) / 'result.json', r)
            args = ('handoff', 'write', '--repo-root', root, '--contract', cp, '--result', rp,
                    '--handoff-root', directory, '--output', 'handoff')
            for decision in ('persisted', 'replayed'):
                actual = self.invoke(*args)
                self.assertEqual(actual.returncode, 0, actual.stdout)
                self.assertEqual(json.loads(actual.stdout)['decision'], decision)

    def test_scope_root_alias(self):
        with tempfile.TemporaryDirectory() as directory:
            _, c = self.fixture(directory)
            helper = runpy.run_path(str(CLI))
            for path in ('./', '././', 'a/..', '/root', 'C:/root', 'a\\b'):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    helper['contract_policy'](dict(c, scope=[path]))
            for path in ('src/file', './src/./file', 'src//file'):
                helper['contract_policy'](dict(c, scope=[path]))

    def test_json_fifo_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            fifo = Path(directory) / 'input'
            os.mkfifo(fifo)
            try:
                r = subprocess.run([sys.executable, str(CLI), 'result', 'check', '--contract', str(fifo), '--result', str(fifo)], capture_output=True, text=True, timeout=1)
            except subprocess.TimeoutExpired:
                self.fail('JSON FIFO blocks before bounded read')
            self.assertEqual(r.returncode, 2, r.stdout)

    def test_digest_fifo_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            fifo = Path(directory) / 'tool'
            os.mkfifo(fifo)
            code = "import runpy; runpy.run_path(" + repr(str(CLI)) + ")['digest'](" + repr(str(fifo)) + ")"
            try:
                r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, timeout=1)
            except subprocess.TimeoutExpired:
                self.fail('digest FIFO blocks')
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('regular file', r.stderr)

    def test_reviewer_dirty_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root, c = self.fixture(directory)
            c['role'] = 'reviewer'
            cp = self.save(Path(directory) / 'contract.json', c)
            op = self.save(Path(directory) / 'observations.json', {k:c[k] for k in ('spec','package','guide','harness')})
            args = ('contract','check','--repo-root',root,'--contract',cp,'--observations',op)
            self.assertEqual(self.invoke(*args).returncode, 0)
            (root / 'untracked').write_text('product')
            r = self.invoke(*args)
            self.assertEqual(r.returncode, 2, r.stdout)

    def test_partial_and_malformed_result_controls(self):
        with tempfile.TemporaryDirectory() as directory:
            root, c = self.fixture(directory)
            c['commands'] = ['first', 'second']
            helper = runpy.run_path(str(CLI))
            r = self.result_fixture(c)
            r.update(outcome='failed', commands=[dict(command='first', status='executed', exit=1),
                                                 dict(command='second', status='not-run', reason='interrupted')])
            helper['result_check'](c, r)
            cp = self.save(Path(directory) / 'contract.json', c)
            rp = self.save(Path(directory) / 'result.json', r)
            args = ('handoff','write','--repo-root',root,'--contract',cp,'--result',rp,
                    '--handoff-root',directory,'--output','partial')
            self.assertEqual(self.invoke(*args).returncode, 0)
            self.assertEqual(self.invoke(*args).returncode, 0)
            for change in (dict(outcome='passed'), dict(commands=[]), dict(schema=1),
                           dict(commands=list(reversed(r['commands']))),
                           dict(commands=[dict(command='first', exit=0), r['commands'][1]]),
                           dict(commands=[dict(command='first', status='executed', exit=True), r['commands'][1]]),
                           dict(commands=[r['commands'][0], dict(command='second', status='not-run', reason='')]),
                           dict(commands=[r['commands'][0], dict(command='second', status='not-run', reason='stop', exit=0)]),
                           dict(commands=[r['commands'][0], dict(command='second', status='unknown', reason='stop')])):
                with self.subTest(change=change), self.assertRaises(ValueError):
                    helper['result_check'](c, dict(r, **change))
            r['commands'][0]['exit'] = 0
            helper['result_check'](c, dict(r, outcome='blocked'))
            r['commands'][1] = dict(command='second', status='executed', exit=0)
            helper['result_check'](c, dict(r, outcome='passed'))

    def test_regular_reader_controls_and_descriptor_race(self):
        helper = runpy.run_path(str(CLI))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            regular = root / 'data'
            regular.write_text('{}')
            link = root / 'link'
            link.symlink_to(regular)
            fifo = root / 'fifo'
            os.mkfifo(fifo)
            for path in (root, Path('/dev/null'), link):
                with self.subTest(path=path), self.assertRaises((ValueError, OSError)):
                    helper['load'](path)
            self.assertEqual(helper['digest'](link, follow=True), hashlib.sha256(b'{}').hexdigest())
            regular.write_bytes(b'x' * 65537)
            with self.assertRaises(ValueError):
                helper['load'](regular)
            with regular.open('wb') as stream:
                stream.truncate(256 * 1024 * 1024 + 1)
            with self.assertRaises(ValueError):
                helper['digest'](regular)
            regular.write_text('{}')
            real_open = os.open
            # The path is regular, but open returns the replaced FIFO descriptor.
            def replaced(path, flags):
                return real_open(fifo, flags)
            for reader in (helper['load'], helper['digest']):
                with patch.object(os, 'open', side_effect=replaced), self.assertRaisesRegex(ValueError, 'regular file'):
                    reader(regular)
            # Reverse race: opened regular bytes win over the now-FIFO pathname.
            def regular_fd(path, flags):
                fd = real_open(regular, flags)
                regular.unlink()
                os.mkfifo(regular)
                return fd
            with patch.object(os, 'open', side_effect=regular_fd):
                self.assertEqual(helper['load'](regular), {})

    def test_dirty_roles_controls(self):
        with tempfile.TemporaryDirectory() as directory:
            root, c = self.fixture(directory)
            cp = Path(directory) / 'contract.json'
            op = self.save(Path(directory) / 'observations.json', {k:c[k] for k in ('spec','package','guide','harness')})
            args = ('contract','check','--repo-root',root,'--contract',cp,'--observations',op)
            config = root / '.sdlc/config.json'
            original = config.read_bytes()
            for staged in (False, True):
                config.write_bytes(original + b' ')
                if staged:
                    subprocess.run(['git','-C',str(root),'add','.sdlc/config.json'], check=True)
                c['config'] = hashlib.sha256(config.read_bytes()).hexdigest()
                for role, expected in (('reviewer',2), ('author',0)):
                    self.save(cp, dict(c, role=role))
                    actual = self.invoke(*args)
                    self.assertEqual(actual.returncode, expected, actual.stdout)
            # Untracked author WIP is also representable.
            (root / 'new-product').write_text('wip')
            self.save(cp, dict(c, role='author'))
            self.assertEqual(self.invoke(*args).returncode, 0)

    def test_author_provenance_cannot_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            _, contract = self.fixture(directory)
            cp = self.save(Path(directory) / 'contract.json', contract)
            result = self.result_fixture(contract)
            result['author_process'] = 'unrelated-author'
            rp = self.save(Path(directory) / 'result.json', result)
            actual = self.invoke('result', 'check', '--contract', cp, '--result', rp)
            self.assertEqual(actual.returncode, 2, actual.stdout)

    def test_result_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            _, contract = self.fixture(directory)
            result = self.result_fixture(contract)
            cp = self.save(Path(directory) / 'contract.json', contract)
            rp = self.save(Path(directory) / 'result.json', result)
            actual = self.invoke('result', 'check', '--contract', cp, '--result', rp)
            self.assertEqual(actual.returncode, 0, actual.stdout + actual.stderr)
            mutations = [dict(contract='0' * 64), dict(schema=1), dict(process='imposter'),
                         dict(commands=[dict(command='bin/ci', status='executed', exit=1)]), dict(findings=['blocker']),
                         dict(evidence=[]), dict(effects=['merge']), dict(unknown=True)]
            for change in mutations:
                with self.subTest(change=change):
                    self.save(rp, dict(result, **change))
                    self.assertEqual(self.invoke('result', 'check', '--contract', cp, '--result', rp).returncode, 2)

    def test_reviewer_process_and_session_separation(self):
        with tempfile.TemporaryDirectory() as directory:
            _, contract = self.fixture(directory)
            contract['role'] = 'reviewer'
            cp = self.save(Path(directory) / 'contract.json', contract)
            result = self.result_fixture(contract)
            for key, value in [('author_process', contract['process']), ('author_session', contract['session'])]:
                rp = self.save(Path(directory) / 'result.json', dict(result, **{key: value}))
                actual = self.invoke('result', 'check', '--contract', cp, '--result', rp)
                self.assertEqual(actual.returncode, 2, actual.stdout)

    def event_fixture(self):
        state = dict(schema=1, generation=1, identity='a' * 64, head='a' * 40,
                     base='b' * 40, seen=[], rounds=0, uncertain=False)
        event = dict(schema=1, generation=1, identity=state['identity'], head=state['head'],
                     base=state['base'], key='review-1', kind='review')
        snapshot = dict(schema=1, generation=1, identity=state['identity'], head=state['head'],
                        base=state['base'], enrolled=True, assigned=True, draft=False,
                        closed=False, merged_sha=None, review_head=None, blockers=False,
                        approval=False, independent=False, gate=False, authority=False, stop=None)
        return state, event, snapshot

    def decide(self, directory, state, event, snapshot):
        sp = self.save(Path(directory) / 'state.json', state)
        ep = self.save(Path(directory) / 'event.json', event)
        gp = self.save(Path(directory) / 'snapshot.json', snapshot)
        return self.invoke('event', 'decide', '--state', sp, '--event', ep, '--github-snapshot', gp)

    def test_acceptance_key_binds_integrated_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            state, event, snapshot = self.event_fixture()
            event['kind'] = 'merged'
            snapshot.update(closed=True, merged_sha='c' * 40)
            first = json.loads(self.decide(directory, state, event, snapshot).stdout)
            self.assertEqual(first['decision'], 'acceptance-handoff')
            self.assertEqual(first['candidate'], 'c' * 40)
            self.assertEqual(first['effects'], [])
            state['seen'] = [first['key']]
            event['key'] = 'another-delivery'
            same = json.loads(self.decide(directory, state, event, snapshot).stdout)
            self.assertEqual(same['decision'], 'duplicate')
            self.assertEqual(same['key'], first['key'])
            self.assertEqual(same['effects'], [])
            snapshot['merged_sha'] = 'd' * 40
            changed = json.loads(self.decide(directory, state, event, snapshot).stdout)
            self.assertEqual(changed['decision'], 'acceptance-handoff')
            self.assertNotEqual(changed['key'], first['key'])
            self.assertEqual(changed['candidate'], 'd' * 40)
            self.assertEqual(changed['effects'], [])

    def test_event_delivery_ids_do_not_define_work(self):
        with tempfile.TemporaryDirectory() as directory:
            state, event, snapshot = self.event_fixture()
            first = json.loads(self.decide(directory, state, event, snapshot).stdout)
            self.assertIn('key', first)
            state['seen'] = [first['key']]
            event['key'] = 'different-delivery'
            second = json.loads(self.decide(directory, state, event, snapshot).stdout)
            self.assertEqual(second['key'], first['key'])
            self.assertEqual(second['decision'], 'duplicate')

    def test_event_key_is_order_invariant_and_revision_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            state, event, snapshot = self.event_fixture()
            first = json.loads(self.decide(directory, state, event, snapshot).stdout)
            reordered = dict(reversed(list(snapshot.items())))
            self.assertEqual(json.loads(self.decide(directory, state, event, reordered).stdout)['key'], first['key'])
            for key, value in [('head', 'd' * 40), ('base', 'e' * 40), ('identity', 'f' * 64), ('generation', 2)]:
                with self.subTest(key=key):
                    changed = dict(snapshot, **{key: value})
                    output = json.loads(self.decide(directory, state, event, changed).stdout)
                    self.assertNotEqual(output['key'], first['key'])
                    self.assertEqual(output['decision'], 'reconcile')

    def test_event_malformed_inputs_regression(self):
        with tempfile.TemporaryDirectory() as directory:
            state, event, snapshot = self.event_fixture()
            for changed in (dict(event, kind='unknown'), dict(event, schema=2), dict(event, kind={}),
                            dict(event, generation=True), dict(event, head=[]), dict(event, key={})):
                actual = self.decide(directory, state, changed, snapshot)
                self.assertEqual(actual.returncode, 2, actual.stdout + actual.stderr)
                self.assertEqual(json.loads(actual.stdout)['class'], 'invalid-policy')

    def test_handoff_recovery_and_boundary_regressions(self):
        with tempfile.TemporaryDirectory() as directory:
            root, contract = self.fixture(directory)
            cp = self.save(Path(directory) / 'contract.json', contract)
            rp = self.save(Path(directory) / 'result.json', self.result_fixture(contract))
            output = Path(directory) / 'handoff'
            args = ('handoff', 'write', '--repo-root', root, '--contract', cp, '--result', rp,
                    '--handoff-root', directory, '--output', 'handoff')
            output.mkdir()
            for interrupted in ('.lock', '.pending-interrupted'):
                sentinel = output / interrupted
                sentinel.write_text('operator recovery required')
                actual = self.invoke(*args)
                self.assertEqual(actual.returncode, 2, actual.stdout)
                self.assertEqual(sentinel.read_text(), 'operator recovery required')
                self.assertFalse((output / 'g1.json').exists())
                sentinel.unlink()  # Synthetic operator recovery; helper never steals.
            self.assertEqual(self.invoke(*args).returncode, 0)
            result = self.result_fixture(contract)
            result['next_action'] = 'conflicting replay'
            self.save(rp, result)
            self.assertEqual(self.invoke(*args).returncode, 2)
            self.save(rp, self.result_fixture(contract))
            for anchor, relative in [(root, 'handoff'), (Path(directory), 'consumer'),
                                     (Path(directory), '../escape'), (Path(directory), str(output))]:
                actual = self.invoke('handoff', 'write', '--repo-root', root, '--contract', cp, '--result', rp,
                                     '--handoff-root', anchor, '--output', relative)
                self.assertEqual(actual.returncode, 2, actual.stdout)
            link = Path(directory) / 'output-link'
            link.symlink_to(output, target_is_directory=True)
            actual = self.invoke('handoff', 'write', '--repo-root', root, '--contract', cp, '--result', rp,
                                 '--handoff-root', directory, '--output', 'output-link')
            self.assertEqual(actual.returncode, 2, actual.stdout)
            actual = self.invoke('handoff', 'write', '--repo-root', root, '--contract', cp, '--result', rp,
                                 '--handoff-root', link, '--output', 'child')
            self.assertEqual(actual.returncode, 2, actual.stdout)

    def test_event_contradictory_merge_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            state, event, snapshot = self.event_fixture()
            snapshot['merged_sha'] = 'c' * 40
            actual = self.decide(directory, state, event, snapshot)
            self.assertEqual(actual.returncode, 2, actual.stdout)

    def test_event_blockers_need_independent_review(self):
        with tempfile.TemporaryDirectory() as directory:
            state, event, snapshot = self.event_fixture()
            snapshot.update(blockers=True, review_head=state['head'])
            actual = self.decide(directory, state, event, snapshot)
            self.assertEqual(json.loads(actual.stdout)['decision'], 'blocked')

    def test_event_review(self):
        with tempfile.TemporaryDirectory() as directory:
            state, event, snapshot = self.event_fixture()
            # Fresh assigned head
            actual = self.decide(directory, state, event, snapshot)
            self.assertEqual(actual.returncode, 0, actual.stdout)
            output = json.loads(actual.stdout)
            self.assertEqual(output["decision"], 'review')
            self.assertEqual(output["effects"], [])

    def test_event_draft(self):
        with tempfile.TemporaryDirectory() as directory:
            state, event, snapshot = self.event_fixture()
            snapshot["draft"] = True
            actual = self.decide(directory, state, event, snapshot)
            self.assertEqual(actual.returncode, 0, actual.stdout)
            output = json.loads(actual.stdout)
            self.assertEqual(output["decision"], 'ignore')
            self.assertEqual(output["effects"], [])

    def test_event_unenrolled(self):
        with tempfile.TemporaryDirectory() as directory:
            state, event, snapshot = self.event_fixture()
            snapshot["enrolled"] = False
            actual = self.decide(directory, state, event, snapshot)
            self.assertEqual(actual.returncode, 0, actual.stdout)
            output = json.loads(actual.stdout)
            self.assertEqual(output["decision"], 'ignore')
            self.assertEqual(output["effects"], [])

    def test_event_unassigned(self):
        with tempfile.TemporaryDirectory() as directory:
            state, event, snapshot = self.event_fixture()
            snapshot["assigned"] = False
            actual = self.decide(directory, state, event, snapshot)
            self.assertEqual(actual.returncode, 0, actual.stdout)
            output = json.loads(actual.stdout)
            self.assertEqual(output["decision"], 'ignore')
            self.assertEqual(output["effects"], [])

    def test_event_informational(self):
        with tempfile.TemporaryDirectory() as directory:
            state, event, snapshot = self.event_fixture()
            event["kind"] = "informational"
            actual = self.decide(directory, state, event, snapshot)
            self.assertEqual(actual.returncode, 0, actual.stdout)
            output = json.loads(actual.stdout)
            self.assertEqual(output["decision"], 'ignore')
            self.assertEqual(output["effects"], [])

    def test_event_correction(self):
        with tempfile.TemporaryDirectory() as directory:
            state, event, snapshot = self.event_fixture()
            snapshot.update(blockers=True, independent=True, review_head=state["head"])
            actual = self.decide(directory, state, event, snapshot)
            self.assertEqual(actual.returncode, 0, actual.stdout)
            output = json.loads(actual.stdout)
            self.assertEqual(output["decision"], 'correct')
            self.assertEqual(output["effects"], [])

    def test_event_replan(self):
        with tempfile.TemporaryDirectory() as directory:
            state, event, snapshot = self.event_fixture()
            state["rounds"] = 2
            snapshot.update(blockers=True, independent=True, review_head=state["head"])
            actual = self.decide(directory, state, event, snapshot)
            self.assertEqual(actual.returncode, 0, actual.stdout)
            output = json.loads(actual.stdout)
            self.assertEqual(output["decision"], 'replan')
            self.assertEqual(output["effects"], [])

    def test_event_stale_review(self):
        with tempfile.TemporaryDirectory() as directory:
            state, event, snapshot = self.event_fixture()
            snapshot.update(approval=True, review_head="f" * 40)
            actual = self.decide(directory, state, event, snapshot)
            self.assertEqual(actual.returncode, 0, actual.stdout)
            output = json.loads(actual.stdout)
            self.assertEqual(output["decision"], 'review')
            self.assertEqual(output["effects"], [])

    def test_event_approval_insufficient(self):
        with tempfile.TemporaryDirectory() as directory:
            state, event, snapshot = self.event_fixture()
            snapshot.update(review_head=state["head"], approval=True)
            actual = self.decide(directory, state, event, snapshot)
            self.assertEqual(actual.returncode, 0, actual.stdout)
            output = json.loads(actual.stdout)
            self.assertEqual(output["decision"], 'blocked')
            self.assertEqual(output["effects"], [])

    def test_event_merge_recommendation(self):
        with tempfile.TemporaryDirectory() as directory:
            state, event, snapshot = self.event_fixture()
            snapshot.update(review_head=state["head"], approval=True, independent=True, gate=True, authority=True)
            actual = self.decide(directory, state, event, snapshot)
            self.assertEqual(actual.returncode, 0, actual.stdout)
            output = json.loads(actual.stdout)
            self.assertEqual(output["decision"], 'merge-ready')
            self.assertEqual(output["effects"], [])

    def test_event_acceptance(self):
        with tempfile.TemporaryDirectory() as directory:
            state, event, snapshot = self.event_fixture()
            snapshot.update(merged_sha="c" * 40, closed=True)
            actual = self.decide(directory, state, event, snapshot)
            self.assertEqual(actual.returncode, 0, actual.stdout)
            output = json.loads(actual.stdout)
            self.assertEqual(output["decision"], 'acceptance-handoff')
            self.assertEqual(output["effects"], [])

    def test_event_closed_unmerged(self):
        with tempfile.TemporaryDirectory() as directory:
            state, event, snapshot = self.event_fixture()
            snapshot["closed"] = True
            actual = self.decide(directory, state, event, snapshot)
            self.assertEqual(actual.returncode, 0, actual.stdout)
            output = json.loads(actual.stdout)
            self.assertEqual(output["decision"], 'stop')
            self.assertEqual(output["effects"], [])

    def test_event_uncertain(self):
        with tempfile.TemporaryDirectory() as directory:
            state, event, snapshot = self.event_fixture()
            state["uncertain"] = True
            actual = self.decide(directory, state, event, snapshot)
            self.assertEqual(actual.returncode, 0, actual.stdout)
            output = json.loads(actual.stdout)
            self.assertEqual(output["decision"], 'reconcile')
            self.assertEqual(output["effects"], [])

    def test_event_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            state, event, snapshot = self.event_fixture()
            event["generation"] = 2
            actual = self.decide(directory, state, event, snapshot)
            self.assertEqual(actual.returncode, 0, actual.stdout)
            output = json.loads(actual.stdout)
            self.assertEqual(output["decision"], 'reconcile')
            self.assertEqual(output["effects"], [])

    def test_event_new_head(self):
        with tempfile.TemporaryDirectory() as directory:
            state, event, snapshot = self.event_fixture()
            snapshot["head"] = "d" * 40
            actual = self.decide(directory, state, event, snapshot)
            self.assertEqual(actual.returncode, 0, actual.stdout)
            output = json.loads(actual.stdout)
            self.assertEqual(output["decision"], 'reconcile')
            self.assertEqual(output["effects"], [])

    def test_event_new_base(self):
        with tempfile.TemporaryDirectory() as directory:
            state, event, snapshot = self.event_fixture()
            snapshot["base"] = "d" * 40
            actual = self.decide(directory, state, event, snapshot)
            self.assertEqual(actual.returncode, 0, actual.stdout)
            output = json.loads(actual.stdout)
            self.assertEqual(output["decision"], 'reconcile')
            self.assertEqual(output["effects"], [])

    def test_event_new_spec_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            state, event, snapshot = self.event_fixture()
            snapshot["identity"] = "b" * 64
            actual = self.decide(directory, state, event, snapshot)
            self.assertEqual(actual.returncode, 0, actual.stdout)
            output = json.loads(actual.stdout)
            self.assertEqual(output["decision"], 'reconcile')
            self.assertEqual(output["effects"], [])

    def test_event_wait_paused(self):
        with tempfile.TemporaryDirectory() as directory:
            state, event, snapshot = self.event_fixture()
            snapshot["stop"] = 'paused'
            actual = self.decide(directory, state, event, snapshot)
            self.assertEqual(actual.returncode, 3, actual.stdout)
            output = json.loads(actual.stdout)
            self.assertEqual(output["decision"], "wait")
            self.assertEqual(output["reason"], 'paused')
            self.assertEqual(output["effects"], [])

    def test_event_wait_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            state, event, snapshot = self.event_fixture()
            snapshot["stop"] = 'stop'
            actual = self.decide(directory, state, event, snapshot)
            self.assertEqual(actual.returncode, 3, actual.stdout)
            output = json.loads(actual.stdout)
            self.assertEqual(output["decision"], "wait")
            self.assertEqual(output["reason"], 'stop')
            self.assertEqual(output["effects"], [])

    def test_event_wait_quota(self):
        with tempfile.TemporaryDirectory() as directory:
            state, event, snapshot = self.event_fixture()
            snapshot["stop"] = 'quota'
            actual = self.decide(directory, state, event, snapshot)
            self.assertEqual(actual.returncode, 3, actual.stdout)
            output = json.loads(actual.stdout)
            self.assertEqual(output["decision"], "wait")
            self.assertEqual(output["reason"], 'quota')
            self.assertEqual(output["effects"], [])

    def test_event_wait_offline(self):
        with tempfile.TemporaryDirectory() as directory:
            state, event, snapshot = self.event_fixture()
            snapshot["stop"] = 'offline'
            actual = self.decide(directory, state, event, snapshot)
            self.assertEqual(actual.returncode, 3, actual.stdout)
            output = json.loads(actual.stdout)
            self.assertEqual(output["decision"], "wait")
            self.assertEqual(output["reason"], 'offline')
            self.assertEqual(output["effects"], [])

    def test_event_wait_revoked(self):
        with tempfile.TemporaryDirectory() as directory:
            state, event, snapshot = self.event_fixture()
            snapshot["stop"] = 'revoked'
            actual = self.decide(directory, state, event, snapshot)
            self.assertEqual(actual.returncode, 3, actual.stdout)
            output = json.loads(actual.stdout)
            self.assertEqual(output["decision"], "wait")
            self.assertEqual(output["reason"], 'revoked')
            self.assertEqual(output["effects"], [])

    def test_durable_handoff(self):
        with tempfile.TemporaryDirectory() as directory:
            root, contract = self.fixture(directory)
            cp = self.save(Path(directory) / 'contract.json', contract)
            rp = self.save(Path(directory) / 'result.json', self.result_fixture(contract))
            output = Path(directory) / 'handoff'
            args = ('handoff', 'write', '--repo-root', root, '--contract', cp, '--result', rp, '--handoff-root', directory, '--output', 'handoff')
            actual = self.invoke(*args)
            self.assertEqual(actual.returncode, 0, actual.stdout + actual.stderr)
            original = (output / 'g1.json').read_bytes()
            self.assertEqual(self.invoke(*args).returncode, 0)
            self.assertEqual((output / 'g1.json').read_bytes(), original)
            contract['generation'] = 2
            self.save(cp, contract)
            self.save(rp, self.result_fixture(contract))
            self.assertEqual(self.invoke(*args).returncode, 0)
            contract['generation'] = 1
            self.save(cp, contract)
            self.save(rp, self.result_fixture(contract))
            self.assertEqual(self.invoke(*args).returncode, 2)
            contract['generation'] = 3
            contract['attempt'] = 'unrelated'
            self.save(cp, contract)
            self.save(rp, self.result_fixture(contract))
            self.assertEqual(self.invoke(*args).returncode, 2)

    def test_handoff_rejects_unsafe_destinations(self):
        with tempfile.TemporaryDirectory() as directory:
            root, contract = self.fixture(directory)
            cp = self.save(Path(directory) / 'contract.json', contract)
            rp = self.save(Path(directory) / 'result.json', self.result_fixture(contract))
            link = Path(directory) / 'link'
            link.symlink_to(root, target_is_directory=True)
            for output in [root / 'handoff', Path('link/handoff'), Path('a/../escape')]:
                actual = self.invoke('handoff', 'write', '--repo-root', root, '--contract', cp, '--result', rp, '--handoff-root', directory, '--output', output)
                self.assertEqual(actual.returncode, 2, actual.stdout)
            self.assertFalse((root / 'handoff').exists())

    def test_handoff_duplicate_prior_keys_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root, contract = self.fixture(directory)
            cp = self.save(Path(directory) / 'contract.json', contract)
            rp = self.save(Path(directory) / 'result.json', self.result_fixture(contract))
            args = ('handoff', 'write', '--repo-root', root, '--contract', cp, '--result', rp,
                    '--handoff-root', directory, '--output', 'handoff')
            self.assertEqual(self.invoke(*args).returncode, 0)
            previous = Path(directory) / 'handoff/g1.json'
            previous.write_text(previous.read_text()[:-1] + ',"contract":' + json.dumps(contract) + '}')
            contract['generation'] = 2
            self.save(cp, contract)
            self.save(rp, self.result_fixture(contract))
            actual = self.invoke(*args)
            self.assertEqual(actual.returncode, 2, actual.stdout)

    def test_handoff_descendant_cannot_enter_consumer(self):
        with tempfile.TemporaryDirectory() as directory:
            root, contract = self.fixture(directory)
            cp = self.save(Path(directory) / 'contract.json', contract)
            rp = self.save(Path(directory) / 'result.json', self.result_fixture(contract))
            actual = self.invoke('handoff', 'write', '--repo-root', root, '--contract', cp, '--result', rp,
                                 '--handoff-root', directory, '--output', 'consumer/handoff')
            self.assertEqual(actual.returncode, 2, actual.stdout)
            self.assertFalse((root / 'handoff').exists())

    def test_handoff_all_prior_records_must_be_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            root, contract = self.fixture(directory)
            cp = Path(directory) / 'contract.json'
            rp = Path(directory) / 'result.json'
            args = ('handoff', 'write', '--repo-root', root, '--contract', cp, '--result', rp,
                    '--handoff-root', directory, '--output', 'handoff')
            for generation in (1, 2):
                contract['generation'] = generation
                self.save(cp, contract)
                self.save(rp, self.result_fixture(contract))
                self.assertEqual(self.invoke(*args).returncode, 0)
            (Path(directory) / 'handoff/g1.json').write_text('{"schema":2}')
            contract['generation'] = 3
            self.save(cp, contract)
            self.save(rp, self.result_fixture(contract))
            actual = self.invoke(*args)
            self.assertEqual(actual.returncode, 2, actual.stdout)

    def test_handoff_record_count_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            root, contract = self.fixture(directory)
            cp = self.save(Path(directory) / 'contract.json', contract)
            rp = self.save(Path(directory) / 'result.json', self.result_fixture(contract))
            output = Path(directory) / 'handoff'
            output.mkdir()
            for generation in range(1, 66):
                previous = dict(contract, generation=generation)
                self.save(output / ('g' + str(generation) + '.json'),
                          dict(contract=previous, result=self.result_fixture(previous)))
            contract['generation'] = 66
            self.save(cp, contract)
            self.save(rp, self.result_fixture(contract))
            actual = self.invoke('handoff', 'write', '--repo-root', root, '--contract', cp, '--result', rp,
                                 '--handoff-root', directory, '--output', 'handoff')
            self.assertEqual(actual.returncode, 2, actual.stdout)
            self.assertIn('record limit', json.loads(actual.stdout)['reason'])

    def test_handoff_nonregular_prior_does_not_block(self):
        with tempfile.TemporaryDirectory() as directory:
            root, contract = self.fixture(directory)
            cp = self.save(Path(directory) / 'contract.json', contract)
            rp = self.save(Path(directory) / 'result.json', self.result_fixture(contract))
            output = Path(directory) / 'handoff'
            output.mkdir()
            os.mkfifo(output / 'g1.json')
            try:
                actual = subprocess.run([sys.executable, str(CLI), 'handoff', 'write', '--repo-root', str(root),
                                         '--contract', str(cp), '--result', str(rp), '--handoff-root', directory,
                                         '--output', 'handoff'], capture_output=True, text=True, timeout=2)
            except subprocess.TimeoutExpired:
                self.fail('nonregular prior record blocked bounded handoff')
            self.assertEqual(actual.returncode, 2, actual.stdout + actual.stderr)
            self.assertIn('regular file', json.loads(actual.stdout)['reason'])

    def test_portable_contained_package(self):
        package = CLI.parents[1]
        self.assertTrue((package / 'plugin.json').is_file(), 'native manifest required')
        manifest = json.loads((package / 'plugin.json').read_text())
        self.assertEqual(set(manifest), {'$schema', 'name', 'version', 'description', 'license'})
        self.assertEqual(manifest['$schema'], 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json')
        self.assertEqual((manifest['name'], manifest['version'], manifest['license']), ('shipshape', '0.1.0', 'MIT'))
        self.assertIsInstance(manifest['description'], str)
        self.assertTrue(manifest['description'].strip())
        for path in package.rglob('*'):
            self.assertFalse(path.is_symlink(), path)
        self.assertEqual({p.name for p in (package / 'skills').iterdir()}, {'shipshape', 'shipshape-implement', 'shipshape-review'})
        for skill in (package / 'skills').glob('*/SKILL.md'):
            source = skill.read_text()
            self.assertTrue(source.startswith('---\nname: ' + skill.parent.name + '\n'))
            self.assertRegex(source, r'\ndescription: .+\n---\n')
            for target in re.findall(r'\]\(([^)]+)\)', source):
                resolved = (skill.parent / target).resolve()
                self.assertTrue(resolved.is_relative_to(package.resolve()))
                self.assertTrue(resolved.is_file(), target)
        self.assertTrue((package / 'README.md').is_file())
        self.assertTrue((package / 'LICENSE').read_text().startswith('MIT License'))

    def test_package_mutations_use_existing_validator(self):
        validator = runpy.run_path(str(ROOT / 'bin/check-marketplace'))
        catalog = json.loads((ROOT / 'catalog.json').read_text())
        plugin = next(p for p in catalog['plugins'] if p['name'] == 'shipshape')
        target = plugin['targets']['codex']
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / target['path']
            package.parent.mkdir(parents=True)
            shutil.copytree(CLI.parents[1], package)
            acceptance = root / target['acceptance']
            acceptance.parent.mkdir(parents=True)
            acceptance.write_text('Synthetic acceptance procedure, pending')
            manifest_path = package / 'plugin.json'
            original = manifest_path.read_text()

            def check():
                manifest = validator['package_manifest'](root, plugin, 'codex', target)
                # Exact candidate subset, not a claim to implement upstream schema.
                if set(manifest) != {'$schema', 'name', 'version', 'description', 'license'}:
                    raise ValueError('unexpected candidate portable fields')

            check()
            for mutation in (dict(json.loads(original), unexpected=True),
                             {k: v for k, v in json.loads(original).items() if k != 'version'},
                             dict(json.loads(original), skills='./../../../outside')):
                with self.subTest(mutation=mutation):
                    manifest_path.write_text(json.dumps(mutation))
                    with self.assertRaises(ValueError):
                        check()
            manifest_path.write_text(original)
            skill = package / 'skills/shipshape/SKILL.md'
            source = skill.read_text()
            skill.write_text('Missing frontmatter')
            with self.assertRaises(ValueError):
                check()
            skill.write_text(source)
            outside = root / 'outside'
            outside.write_text('outside package')
            (package / 'references/escape').symlink_to(outside)
            with self.assertRaises(ValueError):
                check()

    def test_nested_input_types_are_structured_regression(self):
        with tempfile.TemporaryDirectory() as directory:
            root, contract = self.fixture(directory)
            cp = Path(directory) / 'contract.json'
            rp = Path(directory) / 'result.json'
            for key in contract:
                self.save(cp, dict(contract, **{key: {}}))
                actual = self.invoke('contract', 'check', '--repo-root', root, '--contract', cp)
                self.assertEqual(actual.returncode, 2, (key, actual.stdout, actual.stderr))
                self.assertEqual(json.loads(actual.stdout)['class'], 'invalid-policy')

    def test_prior_result_schema_blocks_generation_advance(self):
        with tempfile.TemporaryDirectory() as directory:
            root, contract = self.fixture(directory)
            output = Path(directory) / 'handoff'
            output.mkdir()
            prior = self.save(output / 'g1.json', dict(contract=contract, result={}))
            original = prior.read_bytes()
            contract['generation'] = 2
            cp = self.save(Path(directory) / 'contract.json', contract)
            rp = self.save(Path(directory) / 'result.json', self.result_fixture(contract))
            actual = self.invoke('handoff', 'write', '--repo-root', root, '--contract', cp,
                                 '--result', rp, '--handoff-root', directory, '--output', 'handoff')
            self.assertEqual(actual.returncode, 2, actual.stdout)
            self.assertEqual(prior.read_bytes(), original)
            self.assertFalse((output / 'g2.json').exists())

    def test_prior_filename_generation_must_match(self):
        with tempfile.TemporaryDirectory() as directory:
            root, contract = self.fixture(directory)
            output = Path(directory) / 'handoff'
            output.mkdir()
            prior = self.save(output / 'g2.json', dict(contract=contract, result=self.result_fixture(contract)))
            original = prior.read_bytes()
            contract['generation'] = 3
            cp = self.save(Path(directory) / 'contract.json', contract)
            rp = self.save(Path(directory) / 'result.json', self.result_fixture(contract))
            actual = self.invoke('handoff', 'write', '--repo-root', root, '--contract', cp,
                                 '--result', rp, '--handoff-root', directory, '--output', 'handoff')
            self.assertEqual(actual.returncode, 2, actual.stdout)
            self.assertEqual(json.loads(actual.stdout)['reason'], 'prior generation mismatch')
            self.assertEqual(prior.read_bytes(), original)
            self.assertFalse((output / 'g3.json').exists())

    def test_prior_record_size_and_schema_regressions(self):
        with tempfile.TemporaryDirectory() as directory:
            root, contract = self.fixture(directory)
            cp = self.save(Path(directory) / 'contract.json', contract)
            rp = self.save(Path(directory) / 'result.json', self.result_fixture(contract))
            output = Path(directory) / 'handoff'
            output.mkdir()
            prior = output / 'g1.json'
            for corrupt in ('x' * 65537, '{}', 'null', '{',
                            json.dumps(dict(contract=contract, result={})),
                            json.dumps(dict(contract=dict(contract, schema=2), result=self.result_fixture(contract)))):
                prior.write_text(corrupt)
                actual = self.invoke('handoff', 'write', '--repo-root', root, '--contract', cp, '--result', rp,
                                     '--handoff-root', directory, '--output', 'handoff')
                self.assertEqual(actual.returncode, 2, actual.stdout + actual.stderr)
                self.assertEqual(json.loads(actual.stdout)['class'], 'invalid-policy')
                self.assertEqual(prior.read_text(), corrupt)
            self.save(cp, contract)
            result = self.result_fixture(contract)
            for key in result:
                self.save(rp, dict(result, **{key: {}}))
                actual = self.invoke('result', 'check', '--contract', cp, '--result', rp)
                self.assertEqual(actual.returncode, 2, (key, actual.stdout, actual.stderr))
                self.assertEqual(json.loads(actual.stdout)['class'], 'invalid-policy')

    def test_guide_candidate_coherence(self):
        catalog = json.loads((ROOT / 'catalog.json').read_text())
        candidates = [p for p in catalog['plugins'] if p['name'] == 'shipshape']
        self.assertEqual(len(candidates), 1, 'candidate must be declared without advertisement')
        self.assertEqual(candidates[0]['targets'], {'codex': dict(format='agent-plugin', path='plugins/codex/shipshape', acceptance='docs/acceptance/shipshape.md')})
        guide = (ROOT / 'workflows/shipshape/README.md').read_text()
        baseline = subprocess.run(['git', '-C', str(ROOT), 'show', 'cd7346a33eca33a45f232d17db2e1804d573dccf:workflows/shipshape/README.md'], capture_output=True, text=True, check=True).stdout
        first_prompt = lambda source: source.split('```text\n', 1)[1].split('```', 1)[0]
        self.assertEqual(first_prompt(guide), first_prompt(baseline))
        self.assertIn('Guide-only adoption remains valid', guide)
        acceptance = (ROOT / 'docs/acceptance/shipshape.md').read_text()
        for criterion in ('plugin-installation', 'assigned-plugin-scenarios', 'consumer-state-boundaries', 'issue-criteria'):
            self.assertIn(criterion, acceptance)
        self.assertIn('pending', acceptance)
        for path in ('releases.json', '.agents/plugins/marketplace.json', '.claude-plugin/marketplace.json', 'docs/pi-packages.md'):
            original = subprocess.run(['git', '-C', str(ROOT), 'show', 'cd7346a33eca33a45f232d17db2e1804d573dccf:' + path], capture_output=True, check=True).stdout
            self.assertEqual((ROOT / path).read_bytes(), original, path)

    def test_four_document_package_coherence(self):
        for name in ('README.md', 'process.md', 'adapt.md', 'examples.md'):
            with self.subTest(document=name):
                source = (ROOT / 'workflows/shipshape' / name).read_text()
                self.assertIn('Guide-only adoption', source)
                self.assertIn('handoff', source.lower())
        protocol = (CLI.parents[1] / 'references/operator.md').read_text()
        self.assertIn('Coherence matrix', protocol)
        self.assertIn('--handoff-root', protocol)
        self.assertIn('--observations', protocol)
        self.assertIn('examples/run.py', protocol)

    def test_ambiguous_and_oversized_json_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            _, contract = self.fixture(directory)
            cp = self.save(Path(directory) / 'contract.json', contract)
            rp = Path(directory) / 'result.json'
            result = self.result_fixture(contract)
            payload = json.dumps(result)
            for malformed in [payload[:-1] + ', "schema": 1}',
                              json.dumps(dict(result, next_action='x' * 70000)),
                              json.dumps(dict(result, effects=[{}]))]:
                with self.subTest(size=len(malformed)):
                    rp.write_text(malformed)
                    actual = self.invoke('result', 'check', '--contract', cp, '--result', rp)
                    self.assertEqual(actual.returncode, 2, actual.stdout + actual.stderr)
                    self.assertEqual(json.loads(actual.stdout)['class'], 'invalid-policy')


class GitInspectionTests(ShipshapeTests):
    def test_rr1_callbacks_and_inherited_git(self):
        with tempfile.TemporaryDirectory() as directory:
            root, c = self.fixture(directory)
            c["role"] = "reviewer"
            marker = Path(directory) / "marker"
            hook = Path(directory) / "hook"
            hook.write_text("#!/bin/sh\n/usr/bin/touch " + str(marker) + "\n")
            hook.chmod(0o700)
            subprocess.run(["git", "-C", str(root), "config", "core.fsmonitor", str(hook)], check=True)
            before = [(root / ".git" / name).read_bytes() for name in ("config", "index")]
            helper = runpy.run_path(str(CLI))
            observed = {k:c[k] for k in ("spec", "package", "guide", "harness")}
            for inherited in ({}, {"GIT_CONFIG_COUNT":"1", "GIT_CONFIG_KEY_0":"core.fsmonitor", "GIT_CONFIG_VALUE_0":str(hook)},
                              {"GIT_CONFIG_PARAMETERS":"'core.fsmonitor=" + str(hook) + "'"}):
                with patch.dict(os.environ, inherited):
                    self.assertEqual(helper["contract_check"](root, c, observed)["class"], "success")
                self.assertFalse(marker.exists(), "Git inspection executed consumer callback")
            self.assertEqual(before, [(root / ".git" / name).read_bytes() for name in ("config", "index")])

    def test_rr2_hidden_source_flags(self):
        for flag in ("--assume-unchanged", "--skip-worktree"):
            with self.subTest(flag=flag), tempfile.TemporaryDirectory() as directory:
                root, c = self.fixture(directory)
                source = root / "source.py"
                source.write_text("original\n")
                subprocess.run(["git", "-C", str(root), "add", "source.py"], check=True)
                subprocess.run(["git", "-C", str(root), "-c", "user.name=Fixture", "-c", "user.email=f@example.invalid", "commit", "-qm", "source"], check=True)
                c["head"] = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
                subprocess.run(["git", "-C", str(root), "update-index", flag, "source.py"], check=True)
                source.write_text("modified\n")
                before = [(root / ".git" / name).read_bytes() for name in ("config", "index")]
                helper = runpy.run_path(str(CLI))
                observed = {k:c[k] for k in ("spec", "package", "guide", "harness")}
                self.assertEqual(helper["contract_check"](root, c, observed)["class"], "success")
                c["role"] = "reviewer"
                with self.assertRaises(ValueError):
                    helper["contract_check"](root, c, observed)
                self.assertEqual(before, [(root / ".git" / name).read_bytes() for name in ("config", "index")])

    def test_rr_uncertainty_and_inspection_controls(self):
        with tempfile.TemporaryDirectory() as directory:
            root, c = self.fixture(directory)
            c["role"] = "reviewer"
            helper = runpy.run_path(str(CLI))
            observed = {k:c[k] for k in ("spec", "package", "guide", "harness")}
            real_run = subprocess.run
            with patch.dict(os.environ, {"GIT_DIR":"/nonexistent", "GIT_INDEX_FILE":"/nonexistent", "GIT_WORK_TREE":"/nonexistent", "GIT_CONFIG_COUNT":"0", "PATH":directory}), patch("subprocess.run", wraps=real_run) as calls:
                self.assertEqual(helper["contract_check"](root, c, observed)["class"], "success")
            commands = [call.args[0] for call in calls.call_args_list]
            for command in ("rev-parse", "remote", "ls-files", "ls-tree", "cat-file", "merge-base", "config"):
                self.assertTrue(any(command in args for args in commands), command)
            for call in calls.call_args_list:
                self.assertEqual(call.args[0][0], "/usr/bin/git")
                self.assertEqual(call.kwargs["timeout"], 10)
                self.assertNotIn("GIT_INDEX_FILE", call.kwargs["env"])
            for key, value in (("core.sparseCheckout", "true"), ("core.autocrlf", "true"),
                               ("filter.fixture.clean", "/nonexistent"), ("submodule.fixture.path", "module")):
                original = (root / ".git/config").read_bytes()
                subprocess.run(["git", "-C", str(root), "config", key, value], check=True)
                before = [(root / ".git" / name).read_bytes() for name in ("config", "index")]
                with self.assertRaises(ValueError):
                    helper["contract_check"](root, c, observed)
                self.assertEqual(before, [(root / ".git" / name).read_bytes() for name in ("config", "index")])
                (root / ".git/config").write_bytes(original)
