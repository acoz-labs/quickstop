"""Offline checks for the Claudit eval runner, its scaffold and the suite layout."""
import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'bin/claudit-eval'
SCAFFOLD = ROOT / 'evals/claudit/scaffold.sh'
TOOLS = '    allowed_tools: [Read, Glob, Grep, Skill, Task, Agent, Bash]'
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
                                            f'execution:\n{CANONICAL}\n{TOOLS}\n    max_turns: 5\n')
        self.tmp = self.base / 'tmp'
        self.tmp.mkdir()
        self.plugin = self.base / 'synthetic-plugin'
        (self.plugin / '.claude-plugin').mkdir(parents=True)
        (self.plugin / '.claude-plugin/plugin.json').write_text('{"name": "synthetic", "version": "1.0.0"}\n')
        (self.plugin / 'skills/demo').mkdir(parents=True)
        (self.plugin / 'skills/demo/SKILL.md').write_text('---\nname: demo\n---\nDemo.\n')

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

    def tools(self, scratch):
        return {path.parent.name: [line for line in path.read_text().split('\n') if 'allowed_tools:' in line]
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
        scratch, command, result = self.dry_run('claudit', '--plugin', str(self.plugin), '--case', 'alpha')
        plugin = tree(scratch / 'plugin')
        evals = {k: v for k, v in plugin.items() if k.startswith('evals/')}
        self.assertEqual({k: v for k, v in plugin.items() if not k.startswith('evals/')}, tree(self.plugin))
        self.assertTrue(evals)
        self.assertEqual(self.prompts(scratch), {name: ['    prompt: "/claudit:claudit --read-only"']
                                                 for name in ('alpha', 'beta')})
        self.assertIn('--case alpha', command)
        self.assertNotIn('WebFetch', command)
        self.assertEqual(self.tools(scratch), {name: [TOOLS] for name in ('alpha', 'beta')})
        self.assert_common(scratch, command)

    def test_claudit_arm_quotes_custom_invoke(self):
        scratch, command, _ = self.dry_run('claudit', '--plugin', str(self.plugin), '--invoke', '/claudit:claudit "x": y')
        self.assertEqual(self.prompts(scratch)['alpha'], ['    prompt: "/claudit:claudit \\"x\\": y"'])
        self.assert_common(scratch, command)

    def test_web_fetch_grants_the_tool_on_every_arm(self):
        for arm in ('plain', 'doctor', 'claudit'):
            with self.subTest(arm=arm):
                extra = ('--plugin', str(self.plugin)) if arm == 'claudit' else ()
                scratch, command, _ = self.dry_run(arm, '--web-fetch', *extra)
                words = shlex.split(command)
                grant = words.index('--allow-tools')
                self.assertEqual(words[grant + 1:grant + 3], ['Bash', 'WebFetch(domain:code.claude.com)'])
                self.assertTrue(words[grant + 3].startswith('--'), words[grant + 3])
                self.assertEqual(self.tools(scratch), {name: [TOOLS[:-1] + ', WebFetch]'] for name in ('alpha', 'beta')})
                self.assert_common(scratch, command)

    def test_no_web_fetch_by_default(self):
        scratch, command, _ = self.dry_run('plain')
        self.assertNotIn('WebFetch', command)
        self.assertEqual(self.tools(scratch), {name: [TOOLS] for name in ('alpha', 'beta')})

    def test_web_fetch_refuses_a_case_without_the_tools_line(self):
        (self.repo / 'evals/claudit/cases/beta/case.yaml').write_text(f'execution:\n{CANONICAL}\n')
        result = self.run_cli('run', '--arm', 'plain', '--model', 'm', '--max-cost-usd', '1', '--dry-run', '--web-fetch')
        self.assertEqual(result.returncode, 1)
        self.assertIn('beta/case.yaml', result.stderr)
        self.assertIn('allowed_tools', result.stderr)
        self.assertEqual(list(self.tmp.iterdir()), [])

    def test_no_plugin_arms_use_stub_manifest(self):
        for arm, prompt in (('plain', CANONICAL), ('doctor', '    prompt: /doctor')):
            with self.subTest(arm=arm):
                scratch, command, _ = self.dry_run(arm)
                plugin = tree(scratch / 'plugin')
                self.assertEqual([k for k in plugin if not k.startswith('evals/')], ['.claude-plugin/plugin.json'])
                self.assertEqual(json.loads((scratch / 'plugin/.claude-plugin/plugin.json').read_text()),
                                 ce.STUB_MANIFEST)
                self.assertEqual(self.prompts(scratch), {'alpha': [prompt], 'beta': [prompt]})
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
        shutil.copytree(self.plugin, plugin)
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

    def test_refuses_plugin_on_no_plugin_arm_and_symlinked_plugin(self):
        result = self.run_cli('run', '--arm', 'doctor', '--model', 'm', '--max-cost-usd', '1', '--dry-run',
                              '--plugin', str(self.plugin))
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


def identified(model, plugin_version='4.0.0', web_fetch=None):
    return dict(RESULT, webFetch=web_fetch, suite={'dir': '/abs', 'modelOverride': model, 'judgeModel': 'claude-haiku-5-5',
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

    def test_summary_records_web_fetch_and_refuses_mixing(self):
        on, off = identified('sonnet', web_fetch=True), identified('sonnet', web_fetch=False)
        summary = ce.summarize(ce.merge_results([on, on]), 'claudit')
        self.assertIs(summary['web_fetch'], True)
        self.assertIn('web fetch: on', ce.markdown(summary))
        self.assertIn('web fetch: off', ce.markdown(ce.summarize(off)))
        self.assertIn('web fetch: -', ce.markdown(ce.summarize(identified('sonnet'))))
        self.assertIs(ce.summarize(identified('sonnet'), web_fetch=True)['web_fetch'], True)
        with self.assertRaisesRegex(ce.Failure, 'web_fetch'):
            ce.merge_results([on, off])
        with self.assertRaisesRegex(ce.Failure, 'web_fetch'):
            ce.merge_results([on, identified('sonnet')])
        with self.assertRaisesRegex(ce.Failure, 'web_fetch'):
            ce.summarize(off, web_fetch=True)


def frontmatter(path):
    text = path.read_text()
    match = re.match(r'---\n(.*?)\n---\n', text, re.DOTALL)
    if not match:
        return None
    return {line.split(':', 1)[0].strip() for line in match.group(1).splitlines()
            if line.strip() and not line.startswith((' ', '\t', '-', '#'))}


FAKE_EVAL = """#!/usr/bin/env python3
import json, os, sys
argv = sys.argv
out = argv[argv.index('--json') + 1]
sandbox = os.path.join(os.environ['FAKE_TMP'], 'e-Ab12Cd')
os.makedirs(os.path.join(sandbox, 'out'))
trace = os.path.join(sandbox, 'out', 'trace.jsonl')
with open(trace, 'w') as handle:
    handle.write(json.dumps({'type': 'assistant', 'message': {'role': 'assistant', 'content': [
        {'type': 'text', 'text': 'thinking aloud'}]}}) + '\\n')
    handle.write(json.dumps({'type': 'result', 'result': '# Claudit: alpha\\n\\nReport text.'}) + '\\n')
run = {'costUsd': 0.1, 'judgeCostUsd': 0, 'durationSeconds': 5, 'graders': [], 'tracePath': trace}
lost = dict(run, tracePath=os.path.join(os.environ['FAKE_TMP'], 'gone', 'trace.jsonl'))
with open(out, 'w') as handle:
    json.dump({'costUsd': 0.2, 'cases': [{'name': 'alpha', 'graders': [], 'arms': {'with': [run, lost]}}]}, handle)
"""


class ReportRetentionTests(RunTests):
    def fake(self, script):
        fake = self.base / 'fake-bin'
        fake.mkdir(exist_ok=True)
        (fake / 'claude').write_text(script)
        (fake / 'claude').chmod(0o755)
        return dict(os.environ, TMPDIR=str(self.tmp), CLAUDIT_EVAL_NO_PYTHON_COPY='1', FAKE_TMP=str(self.tmp),
                    PATH=f'{fake}{os.pathsep}{os.environ.get("PATH", "")}')

    def test_run_keeps_reports_and_command_lines_and_removes_sandboxes(self):
        for keep in (False, True):
            with self.subTest(keep_temp=keep):
                out = self.base / f'out-{keep}'
                args = ['run', '--arm', 'plain', '--model', 'm', '--max-cost-usd', '1', '--output-dir', str(out)]
                result = subprocess.run([sys.executable, str(self.repo / 'bin/claudit-eval'), *args,
                                         *(['--keep-temp'] if keep else [])],
                                        env=self.fake(FAKE_EVAL), capture_output=True, text=True,
                                        stdin=subprocess.DEVNULL)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual((out / 'reports/alpha-run1.md').read_text(), '# Claudit: alpha\n\nReport text.\n')
                self.assertFalse((out / 'reports/alpha-run2.md').exists())
                self.assertIn('no final report text for alpha-run2.md', result.stderr)
                command = (out / 'command.txt').read_text().splitlines()
                self.assertEqual(command[0], 'runner: ' + shlex.join([str(self.repo / 'bin/claudit-eval'), *args,
                                                                      *(['--keep-temp'] if keep else [])]))
                self.assertTrue(command[2].startswith('eval: claude plugin eval '))
                self.assertIn(' --keep-temp ', command[2])
                self.assertEqual((self.tmp / 'e-Ab12Cd').exists(), keep)
                shutil.rmtree(self.tmp / 'e-Ab12Cd', ignore_errors=True)

    def test_final_reply_prefers_the_result(self):
        trace = self.base / 'trace.jsonl'
        trace.write_text('not json\n[1]\n' + json.dumps({'role': 'assistant', 'content': 'plain reply'}) + '\n')
        self.assertEqual(ce.final_reply(trace), 'plain reply')
        trace.write_text(json.dumps({'type': 'assistant', 'message': {'content': [{'type': 'tool_use'},
                                                                                   {'type': 'text', 'text': 'A'}]}})
                         + '\n' + json.dumps({'type': 'result', 'result': ' '}) + '\n')
        self.assertEqual(ce.final_reply(trace), 'A')
        trace.write_text(json.dumps({'type': 'user', 'message': {'role': 'user', 'content': 'q'}}) + '\n')
        self.assertIsNone(ce.final_reply(trace))

    def test_only_the_eval_sandbox_shape_is_removed(self):
        for name in ('e-Ab12Cd', 'keep-me', 'e-toolongname'):
            trace = self.tmp / name / 'out' / 'trace.jsonl'
            trace.parent.mkdir(parents=True)
            trace.write_text(json.dumps({'type': 'result', 'result': 'r'}) + '\n')
            out = self.base / ('out-' + name)
            out.mkdir()
            ce.keep_reports({'cases': [{'name': 'c', 'arms': {'with': [{'tracePath': str(trace)}]}}]}, out, False)
            self.assertEqual((out / 'reports/c-run1.md').read_text(), 'r\n')
            self.assertEqual((self.tmp / name).exists(), name != 'e-Ab12Cd')


def scan_of(root):
    proc = subprocess.run([sys.executable, str(ROOT / 'plugins/claudit' / ce.HELPER), 'scan', '--root', str(root),
                           '--claude-version', '2.1.316'], capture_output=True, text=True,
                          env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    return json.loads(proc.stdout)


def conforming(scan):
    """A report that follows the scan exactly."""
    items = ''.join('%d. **%s** (Coverage, effort S)\n   Problem: x.\n   Change: y.\n   Source: [h](u)\n\n'
                    % (i['n'], i['title']) for i in scan['plan']['items'])
    grades = '\n'.join('- **%s: %s** (confidence: high). %s' % (
        name.capitalize(), g['letter'], 'Fine.' if g['letter'] == 'A' else 'Items %s would raise it.' % ', '.join(
            str(n) for n in g['items'])) for name, g in scan['grades'].items())
    declined = ''.join('- **%s** (`%s:%d`): "%s"\n' % (d['label'], d['path'], d['line'], d['quote'])
                       for d in scan['declined'])
    return ('# Claudit: x\n\n**Intent:** x.\n\n## Grades\n\n%s\n\n## Top changes\n\n%s\n\n%s%s'
            '## Also worth knowing\n\n- Optional.\n\n---\n%s\nClaude Code 2.1.316.\n' % (
                grades, scan['plan']['summary'], items,
                '## Declined by the project\n\n%s\n' % declined if declined else '', scan['footer']))


class GradeTests(Temp):
    def repo(self):
        root = self.base / 'repo'
        (root / 'bin').mkdir(parents=True)
        (root / 'CLAUDE.md').write_text('# r\n\n@docs/repository.md\n\nAlways run `bin/ci` before you finish.\n'
                                        'Follow `docs/operations/sdlc.md`.\n')
        (root / 'docs/operations').mkdir(parents=True)
        (root / 'docs/repository.md').write_text('Claude Code hooks were retired; CI is the gate.\n')
        (root / 'docs/operations/sdlc.md').write_text('# Delivery\n' + ''.join('%d. s\n' % n for n in range(1, 6)))
        (root / 'docs/release.md').write_text('# Release\n' + ''.join('%d. s\n' % n for n in range(1, 6)))
        (root / 'tests/reports').mkdir(parents=True)
        (root / 'tests/reports/run.md').write_text('# Release report\n' + ''.join('%d. s\n' % n for n in range(1, 6)))
        (root / 'bin/ci').write_text('#!/bin/sh\n')
        (root / 'bin/ci').chmod(0o755)
        env = dict(os.environ, GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
        for args in (['init', '-q'], ['add', '-A'], ['-c', 'user.name=t', '-c', 'user.email=t@x.invalid', '-c',
                                                     'commit.gpgsign=false', 'commit', '-q', '-m', 'x']):
            subprocess.run(['git', '-C', str(root), *args], check=True, env=env)
        return root

    @unittest.skipUnless(shutil.which('git'), 'git not installed')
    def test_grade_controls(self):
        scan = scan_of(self.repo())
        self.assertEqual([i['title'] for i in scan['plan']['items']],
                         ['Pre-approve the check commands', 'Add a skill for docs/release.md'])
        helper = ce.load_helper(ROOT / 'plugins/claudit')
        good = conforming(scan)
        checks = ce.grade_report(good, scan, helper)
        self.assertEqual(checks, {'plan_items': True, 'grades': True, 'grade_raise': True, 'footer': True,
                                  'no_test_data_findings': True, 'optional_not_planned': True,
                                  'declined_listed': True})
        bad = {'plan_items': good.replace('1. **Pre-approve', '1. **Allow'),
               'grades': good.replace('**Coverage: C**', '**Coverage: B**'),
               'grade_raise': good.replace('Items 1, 2 would raise it.', 'Two gaps.'),
               'footer': good.replace(scan['footer'], 'Claudit 4.1.0'),
               'declined_listed': good.replace('## Declined by the project', '## Declined')}
        for check, text in bad.items():
            with self.subTest(check=check):
                self.assertNotEqual(text, good)
                self.assertFalse(ce.grade_report(text, scan, helper)[check])
        report, scan_path = self.base / 'report.md', self.base / 'scan.json'
        report.write_text(good)
        scan_path.write_text(json.dumps(scan))
        proc = subprocess.run([sys.executable, str(RUNNER), 'grade', '--report', str(report), '--scan', str(scan_path)],
                              capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertFalse((ROOT / 'plugins/claudit/skills/claudit/scripts/__pycache__').exists())


FAKE_HEADLESS = """#!/usr/bin/env python3
import json, os, sys
if sys.argv[1:] == ['--version']:
    print('2.1.316 (Claude Code)')
    sys.exit(0)
sys.path.insert(0, os.environ['FAKE_TESTS'])
from test_claudit_eval import conforming, scan_of
with open(os.environ['FAKE_ARGS'], 'a') as handle:
    handle.write(json.dumps({'argv': sys.argv[1:], 'cwd': os.getcwd()}) + '\\n')
print(json.dumps({'result': conforming(scan_of(os.getcwd())), 'total_cost_usd': 0.12}))
"""


class HeadlessTests(GradeTests):
    @unittest.skipUnless(shutil.which('git'), 'git not installed')
    def test_fresh_clone_runs_are_recorded_and_graded(self):
        repo = self.repo()
        sha = subprocess.run(['git', '-C', str(repo), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
        fake = self.base / 'fake-bin'
        fake.mkdir()
        (fake / 'claude').write_text(FAKE_HEADLESS)
        (fake / 'claude').chmod(0o755)
        tmp = self.base / 'tmp'
        tmp.mkdir()
        calls = self.base / 'calls.jsonl'
        env = dict(os.environ, PATH=f'{fake}{os.pathsep}{os.environ.get("PATH", "")}', TMPDIR=str(tmp),
                   FAKE_TESTS=str(Path(__file__).resolve().parent), FAKE_ARGS=str(calls), PYTHONDONTWRITEBYTECODE='1',
                   GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
        out = self.base / 'out'
        proc = subprocess.run([sys.executable, str(RUNNER), 'headless', '--repo', str(repo), '--sha', sha,
                               '--plugin', str(ROOT / 'plugins/claudit'), '--model', 'claude-sonnet-5-5',
                               '--max-budget-usd', '0.5', '--runs', '2', '--output-dir', str(out)],
                              capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        summary = json.loads((out / 'summary.json').read_text())
        self.assertEqual((summary['runs'], summary['passed'], summary['median_cost_usd']), (2, 2, 0.12))
        clones = [json.loads(line)['cwd'] for line in calls.read_text().splitlines()]
        self.assertEqual(len(set(clones)), 2)
        for number, clone in enumerate(clones, 1):
            meta = json.loads((out / f'run{number}/meta.json').read_text())
            self.assertEqual(meta['head'], sha)
            self.assertTrue(meta['passed'], meta['checks'])
            self.assertEqual(shlex.split(meta['command']), [
                'claude', '-p', '/claudit:claudit --read-only', '--plugin-dir', str(ROOT / 'plugins/claudit'),
                *ce.HEADLESS_FLAGS, '--model', 'claude-sonnet-5-5', '--max-budget-usd', '0.5'])
            self.assertTrue((out / f'run{number}/report.md').read_text().startswith('# Claudit'))
            self.assertFalse(Path(clone).exists())
        self.assertEqual(list(tmp.iterdir()), [])

    def test_refuses_an_instruction_file_above_the_clone(self):
        tmp = self.base / 'tmp'
        tmp.mkdir()
        (self.base / 'CLAUDE.md').write_text('# above\n')
        proc = subprocess.run([sys.executable, str(RUNNER), 'headless', '--repo', 'x', '--sha', 'y', '--plugin',
                               str(ROOT / 'plugins/claudit'), '--model', 'm', '--max-budget-usd', '1',
                               '--output-dir', str(self.base / 'out')],
                              capture_output=True, text=True, env=dict(os.environ, TMPDIR=str(tmp),
                                                                       PYTHONDONTWRITEBYTECODE='1'))
        self.assertEqual(proc.returncode, 1)
        self.assertIn('is above the clone and would load', proc.stderr)
        self.assertEqual(list(tmp.iterdir()), [])


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
