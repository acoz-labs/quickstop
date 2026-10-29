"""Offline checks for the Claudit eval runner, its scaffold and the suite layout."""
import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
import unittest.mock

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'bin/claudit-eval'
SCAFFOLD = ROOT / 'evals/claudit/scaffold.sh'
PLUGIN = ROOT / 'plugins/claudit'
CANONICAL = "    prompt: Review this project's Claude Code setup and tell me what to improve."
GRADER_KEYS = {'type', 'weight', 'pattern', 'flags', 'match', 'target', 'focus', 'arm', 'criteria'}

loader = importlib.machinery.SourceFileLoader('claudit_eval', str(RUNNER))
spec = importlib.util.spec_from_loader('claudit_eval', loader)
ce = importlib.util.module_from_spec(spec)
loader.exec_module(ce)


def tree(root):
    root = Path(root)
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob('*')) if path.is_file()}


def minimal_env(home):
    return {'PATH': f'{Path(sys.executable).parent}{os.pathsep}/usr/bin:/bin', 'HOME': str(home)}


class Temp(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()


class ScaffoldTests(Temp):
    def scaffold(self, fixture, suite_script=SCAFFOLD):
        workspace, home = self.base / 'workspace', self.base / 'home'
        workspace.mkdir()
        home.mkdir(exist_ok=True)
        result = subprocess.run(['env', '-i', *[f'{k}={v}' for k, v in minimal_env(home).items()],
                                 'bash', str(suite_script), str(fixture)],
                                cwd=workspace, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return workspace, home

    def write(self, path, text='x\n'):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def test_maps_names_and_commits_once_with_minimal_env(self):
        fixture = self.base / 'fixture'
        self.write(fixture / 'dot-claude/settings.json', '{}\n')
        self.write(fixture / 'CLAUDE.md.fixture', '# Project\n')
        self.write(fixture / 'dot-claude/dot-hidden/AGENTS.md.fixture')
        self.write(fixture / 'src/dot-gitignore')
        self.write(fixture / 'src/plain.py')
        workspace, _ = self.scaffold(fixture)
        files = {str(p.relative_to(workspace)) for p in workspace.rglob('*')
                 if p.is_file() and '.git' not in p.relative_to(workspace).parts[:1]}
        self.assertEqual(files, {'.claude/settings.json', 'CLAUDE.md', '.claude/.hidden/AGENTS.md',
                                 'src/.gitignore', 'src/plain.py'})
        log = subprocess.run(['git', 'log', '--format=%an <%ae> %s'], cwd=workspace,
                             capture_output=True, text=True, check=True).stdout.splitlines()
        self.assertEqual(log, ['Eval Fixture <fixture@example.invalid> Fixture'])
        status = subprocess.run(['git', 'status', '--porcelain'], cwd=workspace,
                                capture_output=True, text=True, check=True).stdout
        self.assertEqual(status, '')

    def test_refuses_missing_fixture(self):
        workspace = self.base / 'workspace'
        workspace.mkdir()
        result = subprocess.run(['bash', str(SCAFFOLD), str(self.base / 'missing')], cwd=workspace,
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(workspace.iterdir()), [])

    def test_rejects_segments_that_map_to_dot_paths_before_copying(self):
        for name in ('dot-', 'dot-.', 'dot-.fixture'):
            with self.subTest(name=name):
                fixture, workspace = self.base / name / 'fixture', self.base / name / 'workspace'
                self.write(fixture / 'README.md')
                self.write(fixture / 'sub' / name / 'x.txt')
                workspace.mkdir()
                result = subprocess.run(['bash', str(SCAFFOLD), str(fixture)], cwd=workspace,
                                        env=minimal_env(self.base), capture_output=True, text=True)
                self.assertEqual(result.returncode, 65)
                self.assertIn(f"segment '{name}'", result.stderr)
                self.assertEqual(list(workspace.iterdir()), [])

    def test_relocates_seed_cache_into_home(self):
        suite = self.base / 'suite'
        suite.mkdir()
        shutil.copy2(SCAFFOLD, suite / 'scaffold.sh')
        old = '/old/seed/root'
        cache = suite / 'seed-home/.cache/claudit'
        record = {'claims': [{'text': 't'}], 'sources': [
            {'id': 'settings', 'content_path': f'{old}/v2/research/b/settings.md'},
            {'id': 'other', 'content_path': '/elsewhere/kept.md'}]}
        self.write(cache / 'v2/x.json', json.dumps(record))
        self.write(cache / 'v2/topics/t.json', json.dumps({'sources': [{'content_path': f'{old}/v2/research/t.md'}]}))
        self.write(cache / 'v2/research/b/settings.md', '# Settings\n')
        self.write(cache / '.seed-root', old)
        fixture = self.base / 'fixture'
        self.write(fixture / 'README.md')
        _, home = self.scaffold(fixture, suite / 'scaffold.sh')
        new = (home / '.cache/claudit').resolve()
        self.assertFalse((new / '.seed-root').exists())
        moved = json.loads((new / 'v2/x.json').read_text())
        self.assertEqual(moved['sources'][0]['content_path'], f'{new}/v2/research/b/settings.md')
        self.assertEqual(moved['sources'][1]['content_path'], '/elsewhere/kept.md')
        self.assertEqual(moved['claims'], record['claims'])
        topic = json.loads((new / 'v2/topics/t.json').read_text())
        self.assertEqual(topic['sources'][0]['content_path'], f'{new}/v2/research/t.md')
        self.assertTrue((new / 'v2/research/b/settings.md').is_file())


class RunTests(Temp):
    """Dry runs against a synthetic suite in a copied repo layout, so results never land in the checkout."""

    def setUp(self):
        super().setUp()
        self.repo = self.base / 'repo'
        (self.repo / 'bin').mkdir(parents=True)
        shutil.copy2(RUNNER, self.repo / 'bin/claudit-eval')
        suite = self.repo / 'evals/claudit'
        (suite / 'results/old').mkdir(parents=True)
        (suite / 'results/old/result.json').write_text('{}')
        shutil.copy2(SCAFFOLD, suite / 'scaffold.sh')
        for name in ('alpha', 'beta'):
            case = suite / 'cases' / name
            (case / 'fixture').mkdir(parents=True)
            (case / 'fixture/README.md').write_text('hi\n')
            (case / 'case.yaml').write_text(f'name: {name}\ncontext:\n    scaffold_script: scaffold.sh\n'
                                            f'execution:\n{CANONICAL}\n    max_turns: 5\n')
        self.tmp = self.base / 'tmp'
        self.tmp.mkdir()

    def run_cli(self, *args):
        env = dict(os.environ, TMPDIR=str(self.tmp), CLAUDIT_EVAL_NO_PYTHON_COPY='1')
        return subprocess.run([sys.executable, str(self.repo / 'bin/claudit-eval'), *args],
                              env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL)

    def dry_run(self, arm, *extra):
        result = self.run_cli('run', '--arm', arm, '--model', 'claude-test', '--max-cost-usd', '1.5',
                              '--dry-run', *extra)
        self.assertEqual(result.returncode, 0, result.stderr)
        scratch = Path(re.search(r'^Scratch: (.+)$', result.stdout, re.MULTILINE).group(1))
        self.assertTrue(scratch.is_relative_to(self.tmp.resolve()))
        command = re.search(r'^Command: (.+)$', result.stdout, re.MULTILINE).group(1)
        return scratch, command, result

    def prompts(self, scratch):
        return {path.parent.name: [line for line in path.read_text().split('\n') if 'prompt:' in line]
                for path in (scratch / 'plugin/evals/cases').glob('*/case.yaml')}

    def assert_common(self, scratch, command):
        for flag in ('--model claude-test', '--max-cost-usd 1.5', '--trust-plugin', '--scaffold', '--no-publish',
                     '--ablation none', '--judge-model claude-haiku-5-5', '--allow-tools Bash', '--threshold 0'):
            self.assertIn(flag, command)
        self.assertIn(f'claude plugin eval {scratch / "plugin"} ', command)
        self.assertFalse((scratch / 'plugin/evals/results').exists())
        self.assertTrue(os.access(scratch / 'plugin/evals/scaffold.sh', os.X_OK))
        self.assertEqual(sorted(p.name for p in (self.repo / 'evals/claudit/results').iterdir()), ['old'])

    def test_claudit_arm_copies_plugin_byte_for_byte(self):
        scratch, command, result = self.dry_run('claudit', '--plugin', str(PLUGIN), '--case', 'alpha')
        plugin = tree(scratch / 'plugin')
        evals = {k: v for k, v in plugin.items() if k.startswith('evals/')}
        self.assertEqual({k: v for k, v in plugin.items() if not k.startswith('evals/')}, tree(PLUGIN))
        self.assertTrue(evals)
        self.assertEqual(self.prompts(scratch), {name: ['    prompt: "/claudit:claudit --read-only"']
                                                 for name in ('alpha', 'beta')})
        self.assertIn('--case alpha', command)
        self.assertIn('no research cache', result.stderr)
        self.assert_common(scratch, command)

    def test_claudit_arm_quotes_custom_invoke_and_copies_seed(self):
        seed = self.base / 'seed'
        (seed / 'v2').mkdir(parents=True)
        (seed / 'v2/core-config.json').write_text('{}')
        scratch, command, _ = self.dry_run('claudit', '--plugin', str(PLUGIN), '--invoke', '/claudit:claudit "x": y',
                                           '--seed-cache', str(seed))
        self.assertEqual(self.prompts(scratch)['alpha'], ['    prompt: "/claudit:claudit \\"x\\": y"'])
        cache = scratch / 'plugin/evals/seed-home/.cache/claudit'
        self.assertEqual((cache / '.seed-root').read_text(), str(seed.resolve()))
        self.assertTrue((cache / 'v2/core-config.json').is_file())
        self.assert_common(scratch, command)

    def test_no_plugin_arms_use_stub_manifest(self):
        for arm, prompt in (('plain', CANONICAL), ('doctor', '    prompt: /doctor')):
            with self.subTest(arm=arm):
                scratch, command, _ = self.dry_run(arm)
                plugin = tree(scratch / 'plugin')
                self.assertEqual([k for k in plugin if not k.startswith('evals/')], ['.claude-plugin/plugin.json'])
                self.assertEqual(json.loads((scratch / 'plugin/.claude-plugin/plugin.json').read_text()),
                                 ce.STUB_MANIFEST)
                self.assertEqual(self.prompts(scratch), {'alpha': [prompt], 'beta': [prompt]})
                self.assertFalse((scratch / 'plugin/evals/seed-home').exists())
                self.assert_common(scratch, command)

    def test_requires_model_and_positive_cost(self):
        for args in (('--max-cost-usd', '1'), ('--model', 'm'), ('--model', 'm', '--max-cost-usd', '0'),
                     ('--model', 'm', '--max-cost-usd', '-1'), ('--model', 'm', '--max-cost-usd', 'inf'),
                     ('--model', 'm', '--max-cost-usd', 'nan')):
            with self.subTest(args=args):
                result = self.run_cli('run', '--arm', 'plain', '--dry-run', *args)
                self.assertEqual(result.returncode, 2)
        self.assertEqual(list(self.tmp.iterdir()), [])

    def test_plugin_with_own_evals_uses_the_suite(self):
        plugin = self.base / 'own-evals'
        shutil.copytree(PLUGIN, plugin)
        (plugin / 'evals/cases/bundled').mkdir(parents=True)
        (plugin / 'evals/bundled.txt').write_text('mine\n')
        scratch, command, result = self.dry_run('claudit', '--plugin', str(plugin))
        self.assertIn('bundled evals/ were replaced', result.stdout)
        self.assertFalse((scratch / 'plugin/evals/bundled.txt').exists())
        self.assertEqual(sorted(self.prompts(scratch)), ['alpha', 'beta'])
        self.assert_common(scratch, command)

    def test_run_fails_when_no_result_is_written(self):
        fake = self.base / 'fake-bin'
        fake.mkdir()
        for code, expected in (('0', 1), ('3', 3)):
            with self.subTest(code=code):
                (fake / 'claude').write_text(f'#!/bin/sh\nexit {code}\n')
                (fake / 'claude').chmod(0o755)
                env = dict(os.environ, TMPDIR=str(self.tmp), CLAUDIT_EVAL_NO_PYTHON_COPY='1',
                           PATH=f'{fake}{os.pathsep}{os.environ.get("PATH", "")}')
                result = subprocess.run([sys.executable, str(self.repo / 'bin/claudit-eval'), 'run', '--arm', 'plain',
                                         '--model', 'm', '--max-cost-usd', '1', '--output-dir', str(self.base / 'out')],
                                        env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL)
                self.assertEqual(result.returncode, expected, result.stderr)
                self.assertIn('No result.json', result.stderr)

    def test_refuses_duplicate_or_missing_prompt_line(self):
        case = self.repo / 'evals/claudit/cases/beta/case.yaml'
        for text in (f'{CANONICAL}\n{CANONICAL}\n', 'execution:\n    prompt: something else\n'):
            with self.subTest(text=text):
                case.write_text(text)
                result = self.run_cli('run', '--arm', 'plain', '--model', 'm', '--max-cost-usd', '1', '--dry-run')
                self.assertEqual(result.returncode, 1)
                self.assertIn('beta/case.yaml', result.stderr)
        self.assertEqual(list(self.tmp.iterdir()), [])

    def test_refuses_seed_or_plugin_on_no_plugin_arm_and_symlinked_plugin(self):
        result = self.run_cli('run', '--arm', 'doctor', '--model', 'm', '--max-cost-usd', '1', '--dry-run',
                              '--seed-cache', str(self.base))
        self.assertEqual(result.returncode, 1)
        plugin = self.base / 'linked'
        (plugin / '.claude-plugin').mkdir(parents=True)
        (plugin / '.claude-plugin/plugin.json').write_text('{}')
        (plugin / 'link').symlink_to(plugin / '.claude-plugin/plugin.json')
        result = self.run_cli('run', '--arm', 'claudit', '--model', 'm', '--max-cost-usd', '1', '--dry-run',
                              '--plugin', str(plugin))
        self.assertEqual(result.returncode, 1)
        self.assertIn('symlinks', result.stderr)
        self.assertEqual(list(self.tmp.iterdir()), [])


class SeedValidationTests(Temp):
    def test_stale_or_empty_seed_is_rejected_after_relocation(self):
        scratch = self.base / 'scratch'
        shutil.copytree(PLUGIN, scratch / 'plugin')
        (scratch / 'plugin/evals').mkdir()
        shutil.copy2(SCAFFOLD, scratch / 'plugin/evals/scaffold.sh')
        cache = scratch / 'plugin/evals/seed-home/.cache/claudit'
        (cache / 'v2').mkdir(parents=True)
        (cache / '.seed-root').write_text('/old/root')
        path = f'{Path(sys.executable).parent}{os.pathsep}/usr/bin:/bin'
        original = ce.claude_version
        ce.claude_version = lambda: '2.1.312 (Claude Code)'
        self.addCleanup(setattr, ce, 'claude_version', original)
        with self.assertRaisesRegex(ce.Failure, 'not fresh'):
            with unittest.mock.patch('sys.stdout'):
                ce.validate_seed(scratch, Path(sys.executable), path)


class SeedCommandTests(Temp):
    def test_scopes_bash_to_the_helper_and_writes_to_the_cache(self):
        plugin, target = self.base / 'plugin', self.base / 'cache'
        args = types.SimpleNamespace(model='m', max_cost_usd=2.0)
        command = ce.seed_command(plugin, target, args)
        runtime = str((plugin / 'scripts/runtime.py').resolve())
        self.assertNotIn('Bash', command)
        rules = [item for item in command if item.startswith('Bash(')]
        self.assertEqual(rules[0], 'Bash(claude --version)')
        for helper in ('status', 'fetch', 'cache-put', 'cache-fail', 'topic-fail'):
            self.assertIn(f'Bash(python3 {runtime} {helper}:*)', rules)
            self.assertIn(f'Bash(python3 "{runtime}" {helper}:*)', rules)
        for refused in ('decision-save', 'prepare-pr', 'discover', 'verify-pr', 'identity'):
            self.assertFalse([rule for rule in rules if f' {refused}' in rule], refused)
        self.assertFalse([rule for rule in rules if rule.endswith(('runtime.py:*)', 'runtime.py":*)'))])
        self.assertIn(f'Edit(/{target}/**)', command)
        self.assertNotIn('Write', ' '.join(command[command.index('--allowedTools'):]))
        prompt = command[command.index('--append-system-prompt') + 1]
        self.assertIn(f'python3 "{runtime}"', prompt)
        for tool in ('Read', 'Grep', 'Glob', 'Task', 'Agent'):
            self.assertIn(tool, command)



def run_record(cost, judge, seconds, graders, error=None, skipped=()):
    return {'score': 0.5, 'passed': True, 'turns': 3, 'costUsd': cost, 'judgeCostUsd': judge,
            'durationSeconds': seconds, 'startedAt': '2026-10-29T00:00:00Z', 'error': error,
            'tracePath': '/private/tmp/e-1/trace.jsonl', 'skippedPaidGraders': list(skipped),
            'graders': [{'name': name, 'passed': passed, 'weight': 1, 'explanation': 'see /abs/path',
                         'withOnly': False, 'scored': scored} for name, passed, scored in graders]}


RESULT = {
    'schemaVersion': 1, 'claudeVersion': '2.1.312', 'startedAt': '2026-10-29T00:00:00Z', 'durationSeconds': 100.0,
    'costUsd': 1.25, 'partial': False, 'suite': {'dir': '/private/tmp/claudit-eval-x/plugin/evals'},
    'aggregates': {},
    'cases': [
        {'name': 'f1', 'dir': '/private/tmp/claudit-eval-x/plugin/evals/cases/f1', 'graders': [], 'aggregates': {},
         'arms': {'with': [
             run_record(0.4, 0.05, 30, [('finding-a', True, True), ('finding-b', False, True),
                                        ('structure-x', True, True), ('no-invented-y', False, True)]),
             run_record(0.6, 0.15, 50, [('finding-a', True, True), ('finding-b', True, True),
                                        ('structure-x', False, True), ('no-invented-y', True, True)],
                        error='timeout', skipped=('finding-c',)),
         ]}},
        {'name': 'f2', 'dir': '/abs/f2', 'graders': [], 'aggregates': {},
         'arms': {'with': [run_record(0.1, 0.0, 10, [('finding-z', False, False), ('structure-x', True, True)])]}},
    ]}


class SummaryTests(Temp):
    def test_counts_costs_and_has_no_absolute_paths(self):
        summary = ce.summarize(RESULT, arm='claudit', model='m', judge_model='j')
        f1, f2 = summary['cases']
        self.assertEqual((f1['case'], f1['runs'], f1['findings_hit'], f1['findings_total'], f1['hit_rate']),
                         ('f1', 2, 3, 4, 0.75))
        self.assertEqual((f1['structure_passed'], f1['structure_total'], f1['false_defects']), (1, 2, 1))
        self.assertEqual((f1['errors'], f1['skipped_paid_graders']), (1, 1))
        self.assertAlmostEqual(f1['agent_cost_usd'], 1.0)
        self.assertAlmostEqual(f1['agent_cost_usd_mean'], 0.5)
        self.assertAlmostEqual(f1['judge_cost_usd'], 0.2)
        self.assertAlmostEqual(f1['wall_seconds_mean'], 40.0)
        self.assertEqual((f2['findings_total'], f2['hit_rate'], f2['structure_passed']), (1, 0.0, 1))
        totals = summary['totals']
        self.assertEqual((totals['runs'], totals['findings_hit'], totals['findings_total'], totals['false_defects'],
                          totals['false_defect_runs']), (3, 3, 5, 1, 1))
        self.assertAlmostEqual(summary['agent_plus_judge_cost_usd'], 1.3)
        self.assertEqual((summary['total_cost_usd'], summary['claude_version'], summary['model'],
                          summary['judge_model'], summary['partial'], summary['duration_seconds']),
                         (1.25, '2.1.312', 'm', 'j', False, 100.0))
        self.assertNotIn('/', json.dumps(summary))
        table = ce.markdown(summary)
        self.assertIn('| f1 | 2 | 3/4 | 75% | 1/2 | 1 (1) |', table)
        self.assertIn('| TOTAL | 3 |', table)

    def test_cli_reads_result_file(self):
        path = self.base / 'result.json'
        path.write_text(json.dumps(RESULT))
        result = subprocess.run([sys.executable, str(RUNNER), 'summarize', str(path), '--arm', 'plain'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"arm": "plain"', result.stdout)
        self.assertIn('| TOTAL |', result.stdout)
        path.write_text('not json')
        result = subprocess.run([sys.executable, str(RUNNER), 'summarize', str(path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)

    def test_pools_passes_of_one_arm(self):
        summary = ce.summarize(ce.merge_results([RESULT, RESULT]))
        self.assertEqual([row['case'] for row in summary['cases']], [row['case'] for row in ce.summarize(RESULT)['cases']])
        self.assertEqual((summary['totals']['runs'], summary['totals']['findings_hit'], summary['totals']['findings_total']),
                         (6, 6, 10))
        self.assertEqual((summary['total_cost_usd'], summary['duration_seconds'], summary['claude_version']),
                         (2.5, 200.0, '2.1.312'))


def case_with(graders, *runs):
    return {'name': 'c', 'graders': [{'name': name} for name in graders], 'arms': {'with': list(runs)}}


def passes(**graders):
    return run_record(0.1, 0.0, 1, [(name.replace('_', '-'), passed, True) for name, passed in graders.items()])


class CountingTests(unittest.TestCase):
    def test_false_defects_do_not_double_count_the_catch_all(self):
        both = passes(no_invented_defects=False, no_invented_import=False, no_invented_stop_matcher=True)
        alone = passes(no_invented_defects=False, no_invented_import=True)
        two = passes(no_invented_defects=False, no_invented_import=False, no_invented_stop_matcher=False)
        clean = passes(no_invented_defects=True, no_invented_import=True)
        for record, expected in ((both, 1), (alone, 1), (two, 2), (clean, 0)):
            with self.subTest(expected=expected):
                row = ce.case_summary(case_with([], record))
                self.assertEqual((row['false_defects'], row['false_defect_runs']), (expected, int(expected > 0)))
        row = ce.case_summary(case_with([], both, alone, two, clean))
        self.assertEqual((row['false_defects'], row['false_defect_runs']), (4, 3))

    def test_errored_and_unscored_runs_stay_in_the_denominator(self):
        good = run_record(0.1, 0.0, 1, [('finding-a', True, True), ('finding-b', True, True),
                                        ('finding-c', True, False), ('structure-x', True, True)], skipped=('finding-c',))
        errored = run_record(0.0, 0.0, 1, [], error='crashed')
        row = ce.case_summary(case_with(['finding-a', 'finding-b', 'finding-c', 'structure-x'], good, errored))
        self.assertEqual((row['findings_hit'], row['findings_total'], row['hit_rate']), (2, 6, 0.3333))
        self.assertEqual((row['structure_passed'], row['structure_total']), (1, 2))
        self.assertEqual((row['errors'], row['skipped_paid_graders']), (1, 1))


def identified(model, plugin_version='4.0.0'):
    return dict(RESULT, suite={'dir': '/abs', 'modelOverride': model, 'judgeModel': 'claude-haiku-5-5',
                               'plugins': [{'name': 'claudit', 'version': plugin_version, 'path': '/abs/claudit'}]})


class PoolingTests(unittest.TestCase):
    def test_pooled_summary_carries_model_judge_and_plugin(self):
        summary = ce.summarize(ce.merge_results([identified('sonnet'), identified('sonnet')]), 'claudit', 'sonnet')
        self.assertEqual((summary['model'], summary['judge_model'], summary['plugins'], summary['claude_version']),
                         ('sonnet', 'claude-haiku-5-5', ['claudit@4.0.0'], '2.1.312'))
        self.assertNotIn('/', json.dumps(summary))
        self.assertIn('plugins: claudit@4.0.0', ce.markdown(summary))

    def test_refuses_to_pool_or_label_mismatched_results(self):
        other_judge = identified('sonnet')
        other_judge['suite'] = dict(other_judge['suite'], judgeModel='claude-sonnet-5-5')
        for other in (identified('opus'), identified('sonnet', '4.0.1'), dict(identified('sonnet'), claudeVersion='9'),
                      other_judge):
            with self.subTest(other=other['suite'], version=other['claudeVersion']):
                with self.assertRaises(ce.Failure):
                    ce.merge_results([identified('sonnet'), other])
        with self.assertRaisesRegex(ce.Failure, 'model'):
            ce.summarize(identified('sonnet'), model='opus')


def frontmatter(path):
    text = path.read_text()
    match = re.match(r'---\n(.*?)\n---\n', text, re.DOTALL)
    if not match:
        return None
    return {line.split(':', 1)[0].strip() for line in match.group(1).splitlines()
            if line.strip() and not line.startswith((' ', '\t', '-', '#'))}


class SuiteStructureTests(unittest.TestCase):
    def test_cases_follow_the_suite_contract(self):
        cases = sorted(path for path in (ROOT / 'evals/claudit/cases').glob('*') if path.is_dir())
        if not cases:
            self.skipTest('no Claudit eval cases yet')
        self.assertTrue(os.access(SCAFFOLD, os.X_OK))
        for case in cases:
            with self.subTest(case=case.name):
                text = (case / 'case.yaml').read_text()
                self.assertEqual(text.split('\n').count(CANONICAL), 1)
                self.assertRegex(text, r'(?m)^\s+scaffold_script: scaffold\.sh\s*$')
                self.assertTrue(os.access(case / 'scaffold.sh', os.X_OK))
                fixture = case / 'fixture'
                self.assertTrue(fixture.is_dir())
                for path in fixture.rglob('*'):
                    self.assertFalse(path.name.startswith('.'), f'real dotfile in fixture: {path}')
                    self.assertNotIn(path.name, ('CLAUDE.md', 'AGENTS.md'), f'live instruction file: {path}')
                    self.assertFalse(path.is_symlink(), path)
                graders = sorted((case / 'graders').glob('*.md'))
                self.assertLessEqual(set(ce.STRUCTURE), {grader.stem for grader in graders})
                if case.name.startswith('f4-'):
                    self.assertIn('no-invented-defects', {grader.stem for grader in graders})
                for grader in graders:
                    self.assertTrue(grader.stem.startswith(('finding-', 'structure-', 'no-invented-')), grader.name)
                    keys = frontmatter(grader)
                    self.assertIsNotNone(keys, f'{grader.name}: missing frontmatter')
                    self.assertLessEqual(keys, GRADER_KEYS, grader.name)


if __name__ == '__main__':
    unittest.main()
