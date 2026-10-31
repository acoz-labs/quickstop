"""Offline checks for the Writing for Humans eval: graders, host-check grading, runner and scaffold.

Regex graders run as JavaScript regexes inside `claude plugin eval`; these tests run them with
Python's re and, when node is installed, with node too. `tool_used` graders match `input_match`
as an unanchored regex against the tool input's JSON text, which these tests reproduce.
"""
import contextlib
import importlib.machinery
import io
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / 'evals/writing-for-humans'
CASES = SUITE / 'cases'
PLUGIN = ROOT / 'plugins/claude-code/writing-for-humans'
RUNNER = ROOT / 'bin/writing-for-humans-eval'

loader = importlib.machinery.SourceFileLoader('wfh_eval', str(RUNNER))
spec = importlib.util.spec_from_loader('wfh_eval', loader)
we = importlib.util.module_from_spec(spec)
loader.exec_module(we)

SKILLS = ['writing-for-humans:writing-audit', 'writing-for-humans:writing-style', 'simplify']


def init_line(plugins=None, skills=None, tools=None, style='default'):
    """A stream-json init record shaped like Claude Code 2.1.316's (trimmed)."""
    record = {'type': 'system', 'subtype': 'init', 'cwd': '/tmp/e/home/cwd', 'session_id': 's',
              'tools': tools if tools is not None else ['Task', 'Bash', 'Glob', 'Grep', 'Read', 'Skill'],
              'mcp_servers': [], 'model': 'claude-sonnet-5-5', 'permissionMode': 'dontAsk',
              'slash_commands': ['writing-for-humans:writing-audit', 'output-style'], 'output_style': style,
              'agents': ['Explore'], 'skills': skills if skills is not None else SKILLS,
              'plugins': plugins if plugins is not None else [
                  {'name': 'writing-for-humans', 'path': '/tmp/p', 'source': 'writing-for-humans@inline',
                   'version': '0.3.1'},
                  {'name': 'cc-plugin-agents-md', 'path': 'builtin', 'source': 'cc-plugin-agents-md@builtin'}]}
    return json.dumps(record, separators=(',', ':'))


def trace(*first):
    rest = [json.dumps({'type': 'assistant', 'message': {'content': [
        {'type': 'text', 'text': 'skills: writing-for-humans:writing-audit, "plugins":["writing-for-humans"]'}]}})]
    return '\n'.join([*first, *rest]) + '\n'


def grader(path):
    head, _, body = path.read_text().partition('\n---\n')
    fields = {}
    for line in head.splitlines()[1:]:
        key, _, value = line.partition(': ')
        if len(value) > 1 and value[0] == value[-1] == "'":
            value = value[1:-1].replace("''", "'")
        fields[key] = value
    fields['body'] = body
    return fields


def regex_flags(flags):
    return (re.I if 'i' in flags else 0) | (re.M if 'm' in flags else 0)


def matches(fields, text):
    found = re.search(fields['pattern'], text, regex_flags(fields.get('flags', ''))) is not None
    return found != (fields.get('match') == 'not_contains')


def tool_passes(fields, calls):
    """tool_used: count calls of `tool` whose JSON input matches input_match; pass if min <= count <= max."""
    count = sum(1 for name, payload in calls if name == fields['tool']
                and re.search(fields.get('input_match', ''), json.dumps(payload)))
    low = int(fields.get('min', 1))
    high = int(fields['max']) if 'max' in fields else None
    return count >= low and (high is None or count <= high)


REPORT = textwrap.dedent("""\
    ## Writing audit: ttl-decision

    Review-only: no edit authorization, so these are proposed rewrites.

    ### docs/decision-notes.md
    Rewritten: "Went with B" becomes "We kept the 90-second cache lifetime (option B) because ...".
    Kept and flagged: the `a8f2c1` reference may be load-bearing.
    Deleted: nothing.
    """)

# name -> (texts that must pass, texts that must fail)
REGEX_CORPUS = {
    ('audit-typed', 'loads'): ([trace(init_line())], [
        trace(init_line(plugins=[])),
        trace(init_line(skills=['writing-for-humans:writing-style'])),
        trace(init_line(skills=['writing-for-humans:writing-audit'])),
        # Names appear later in the trace but not in the init record.
        trace(init_line(plugins=[], skills=[])),
        trace(init_line().replace('"subtype":"init"', '"subtype":"status"')),
    ]),
    ('audit-not-automatic', 'skill-offered'): ([trace(init_line())], [
        trace(init_line(tools=['Read', 'Glob'])),
        trace(init_line(skills=['writing-for-humans:writing-style'])),
        trace(init_line(tools=[], skills=[])),
    ]),
    ('audit-typed', 'names-draft'): ([REPORT, 'See docs/decision-notes.md.'], [
        'No drafts were found on this branch.', 'decision-notes is fine', 'docs/decision-notesXmd']),
    ('audit-typed', 'report-structure'): ([
        REPORT, 'Proposed rewrite of line 3. Nothing kept.', 'I REWROTE two lines and FLAGGED one.',
        'Rewrites:\n- line 1\n\nFlags:\n- the hash', 'Rewriting the ask; flagging a8f2c1.',
    ], [
        'The draft reads fine.', 'Rewritten: line 1.', 'Kept and flagged: the hash.',
        'overwritten lines; flagpole', 'rewrites.', 'unflagged rewrites',
    ]),
}

READ = 'Read'
ARTIFACTS = '/tmp/e/plugin/skills/writing-style/references/artifacts.md'
STYLE_FILE = '/tmp/e/plugin/output-styles/writing-for-humans.md'
# name -> (call lists that must pass, call lists that must fail)
TOOL_CORPUS = {
    ('audit-typed', 'reads-artifacts-reference'): (
        [[(READ, {'file_path': ARTIFACTS})], [(READ, {'file_path': STYLE_FILE}), (READ, {'file_path': ARTIFACTS})]],
        [[], [(READ, {'file_path': STYLE_FILE})], [('Grep', {'pattern': 'x', 'path': ARTIFACTS})],
         [(READ, {'file_path': '/tmp/e/plugin/skills/writing-style/references/questions.md'})]]),
    ('audit-typed', 'reads-output-style'): (
        [[(READ, {'file_path': STYLE_FILE})]],
        [[], [(READ, {'file_path': ARTIFACTS})], [(READ, {'file_path': '/tmp/e/home/cwd/output-styles/other.md'})],
         [('Bash', {'command': f'cat {STYLE_FILE}'})]]),
    ('audit-typed', 'no-external-action'): (
        [[], [('Bash', {'command': 'git log --oneline main..HEAD'}), ('Bash', {'command': 'git diff main...HEAD'})],
         [('Bash', {'command': 'git show HEAD --stat'})], [('Bash', {'command': 'gh pr view --json body'})],
         [(READ, {'file_path': '/tmp/git commit notes.md'})], [('Bash', {'command': 'git -C . log --oneline'})],
         [('Bash', {'command': 'git --no-pager diff main...HEAD'})], [('Bash', {'command': 'gh api repos/o/r/pulls/1'})],
         [('Bash', {'command': 'git log --grep commit'})]],
        [[('Bash', {'command': 'git commit -m "tidy"'})], [('Bash', {'command': 'git push origin HEAD'})],
         [('Bash', {'command': 'gh pr edit 3 --body "x"'})], [('Bash', {'command': 'gh pr create --fill'})],
         [('Bash', {'command': 'git rebase -i main'})], [('Bash', {'command': 'git reset --soft HEAD~1'})],
         [('Bash', {'command': 'gh pr comment 3 -b x'})], [('Bash', {'command': 'git  commit --amend'})],
         [('Bash', {'command': 'git -C . commit -m x'})], [('Bash', {'command': 'git -c commit.gpgsign=false commit'})],
         [('Bash', {'command': 'git --no-pager push'})], [('Bash', {'command': 'gh api -X PATCH repos/o/r/pulls/1'})],
         [('Bash', {'command': 'gh api --method=POST repos/o/r/issues/1/comments'})],
         [('Bash', {'command': 'gh api repos/o/r/pulls/1 -f body=x'})], [('Bash', {'command': 'gh pr merge 3'})]]),
    ('audit-not-automatic', 'reads-draft'): (
        [[(READ, {'file_path': '/tmp/e/home/cwd/docs/decision-notes.md'})],
         [('Skill', {'skill': 'writing-for-humans:writing-style'}), (READ, {'file_path': 'docs/decision-notes.md'})]],
        [[], [(READ, {'file_path': ARTIFACTS})], [('Grep', {'pattern': 'TTL', 'path': 'docs/decision-notes.md'})],
         [(READ, {'file_path': '/tmp/e/home/cwd/docs/decision-notes-old.md'})]]),
    ('audit-not-automatic', 'not-invoked'): (
        [[], [('Skill', {'skill': 'writing-for-humans:writing-style'})], [(READ, {'file_path': 'docs/writing-audit.md'})]],
        [[('Skill', {'skill': 'writing-for-humans:writing-audit'})], [('Skill', {'skill': 'writing-audit'})],
         [('Skill', {'skill': 'writing-for-humans:writing-audit', 'args': ''})]]),
}

# Each structural grader cites the kit lines it enforces; a drifted line fails here.
CITATIONS = {
    'skills/writing-audit/SKILL.md': {
        4: 'disable-model-invocation: true',
        13: 'Read the reference for each surface before auditing it.',
        17: '| Workflow artifacts | `${CLAUDE_PLUGIN_ROOT}/skills/writing-style/references/artifacts.md` |',
        25: 'If they are not, read `${CLAUDE_PLUGIN_ROOT}/output-styles/writing-for-humans.md` directly.',
        35: 'Any durable markdown this work produced for me to read: design notes',
        53: 'Never rewrite pushed history.',
        61: 'a review-only request means report findings without edits. Commit only within existing authorization.',
        63: 'Apply it with `gh pr edit --body` only when that external change is already authorized',
        65: '**Report**: what was deleted, rewritten, and kept-and-flagged',
    },
}


class GraderTests(unittest.TestCase):
    def graders(self):
        return {(path.parent.parent.name, path.stem): grader(path) for path in sorted(CASES.glob('*/graders/*.md'))}

    def test_every_grader_is_script_graded_and_covered(self):
        graders = self.graders()
        self.assertEqual({fields['type'] for fields in graders.values()}, {'regex', 'tool_used'})
        self.assertEqual(set(graders), set(REGEX_CORPUS) | set(TOOL_CORPUS))

    def test_regex_graders_pass_and_fail_the_corpus(self):
        graders = self.graders()
        for key, (good, bad) in REGEX_CORPUS.items():
            for text in good:
                self.assertTrue(matches(graders[key], text), f'{key} should pass:\n{text}')
            for text in bad:
                self.assertFalse(matches(graders[key], text), f'{key} should fail:\n{text}')

    def test_tool_graders_pass_and_fail_the_corpus(self):
        graders = self.graders()
        for key, (good, bad) in TOOL_CORPUS.items():
            for calls in good:
                self.assertTrue(tool_passes(graders[key], calls), f'{key} should pass: {calls}')
            for calls in bad:
                self.assertFalse(tool_passes(graders[key], calls), f'{key} should fail: {calls}')

    def test_absence_graders_score_in_every_arm(self):
        for key, fields in self.graders().items():
            if fields['type'] == 'tool_used':
                self.assertEqual(fields.get('arm'), 'both', key)
            if fields.get('max') == '0':
                self.assertEqual(fields.get('min'), '0', key)

    @unittest.skipUnless(shutil.which('node'), 'node not installed')
    def test_javascript_engine_agrees(self):
        graders = self.graders()
        checks, expected = [], []
        for key, (good, bad) in REGEX_CORPUS.items():
            fields = graders[key]
            for text, want in [(text, True) for text in good] + [(text, False) for text in bad]:
                checks.append([fields['pattern'], fields.get('flags', ''), fields.get('match', 'contains'), text])
                expected.append(want)
        for key, (good, bad) in TOOL_CORPUS.items():
            fields = graders[key]
            for calls, want in [(calls, True) for calls in good] + [(calls, False) for calls in bad]:
                for name, payload in calls:
                    if name == fields['tool']:
                        checks.append([fields['input_match'], '', 'contains', json.dumps(payload)])
                        expected.append(re.search(fields['input_match'], json.dumps(payload)) is not None)
        script = ("const checks = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
                  "process.stdout.write(JSON.stringify(checks.map(([p, f, m, t]) =>"
                  " new RegExp(p, f).test(t) !== (m === 'not_contains'))));")
        out = subprocess.run(['node', '-e', script], input=json.dumps(checks), capture_output=True, text=True,
                             check=True)
        self.assertEqual(json.loads(out.stdout), expected)

    def test_cited_kit_lines_still_say_what_the_graders_enforce(self):
        for relative, lines in CITATIONS.items():
            text = (PLUGIN / relative).read_text().split('\n')
            for number, needle in lines.items():
                self.assertIn(needle, text[number - 1], f'{relative}:{number}')
        cited = set()
        for fields in self.graders().values():
            cited |= {int(n) for n in re.findall(r'SKILL\.md:(\d+)', fields['body'])}
            cited |= {int(n) for n in re.findall(r'`:(\d+)`', fields['body'])}
        self.assertTrue(cited <= set(CITATIONS['skills/writing-audit/SKILL.md']), cited)
        readme = (SUITE / 'README.md').read_text()
        for name in ('reads-artifacts-reference', 'reads-output-style', 'report-structure', 'no-external-action',
                     'not-invoked'):
            self.assertRegex(readme, rf'`{name}`[^\n]*SKILL\.md:\d+', name)

    def test_cases_use_the_typed_command_only_where_intended(self):
        typed = (CASES / 'audit-typed/case.yaml').read_text()
        plain = (CASES / 'audit-not-automatic/case.yaml').read_text()
        self.assertIn('    prompt: /writing-for-humans:writing-audit\n', typed)
        self.assertNotIn('/writing-for-humans:', plain)
        for text in (typed, plain):
            tools = re.search(r'allowed_tools: \[(.*)\]', text).group(1)
            self.assertNotRegex(tools, r'\b(?:Edit|Write|WebFetch)\b|"Bash"|, Bash\b|\[Bash\b')
        self.assertIn('Skill', re.search(r'allowed_tools: \[(.*)\]', plain).group(1))


def records(*lines):
    return [json.loads(line) for line in lines]


def result_line(text, cost=0):
    return json.dumps({'type': 'result', 'subtype': 'success', 'result': text, 'total_cost_usd': cost})


INSTALLED = [{'name': 'writing-for-humans', 'path': '/tmp/m/writing-for-humans', 'source': 'writing-for-humans@wfh-eval',
              'version': '0.3.1'}]


class HostGradingTests(unittest.TestCase):
    def failed(self, checks):
        return [name for name, ok, _ in checks if not ok]

    def test_load_passes_only_for_the_installed_plugin_at_its_version_with_both_skills(self):
        self.assertEqual(self.failed(we.grade_load(records(init_line(plugins=INSTALLED)), '0.3.1')), [])
        self.assertEqual(self.failed(we.grade_load(records(init_line(plugins=INSTALLED)), '0.3.2')),
                         ['plugin-version'])
        self.assertEqual(self.failed(we.grade_load(records(init_line()), '0.3.1')), ['plugin-installed'])
        self.assertEqual(self.failed(we.grade_load(records(init_line(plugins=INSTALLED, skills=['simplify'])),
                                                   '0.3.1')), ['skill-writing-audit', 'skill-writing-style'])
        self.assertEqual(len(self.failed(we.grade_load([], '0.3.1'))), 5)

    def test_style_selection(self):
        ok = records(result_line('Output style set to writing-for-humans:writing-for-humans'))
        saved = '{\n  "outputStyle": "writing-for-humans:writing-for-humans"\n}\n'
        self.assertEqual(self.failed(we.grade_select(ok, saved)), [])
        self.assertEqual(self.failed(we.grade_select(ok, None)), ['style-saved'])
        self.assertEqual(self.failed(we.grade_select(ok, 'not json')), ['style-saved'])
        refused = records(result_line('Output styles are saved to local settings (.claude/settings.local.json), '
                                      "which this session doesn't load, so the style can't be changed here."))
        self.assertEqual(self.failed(we.grade_select(refused, saved)), ['style-select-command'])

    def test_fresh_session_style(self):
        self.assertEqual(self.failed(we.grade_fresh(records(init_line(style='writing-for-humans:writing-for-humans')))),
                         [])
        self.assertEqual(self.failed(we.grade_fresh(records(init_line()))), ['style-active-fresh-session'])

    def test_unknown_style_control(self):
        unknown = records(result_line('Unknown output style "writing-for-humans:no-such-style". Available styles: default'))
        self.assertEqual(self.failed(we.grade_unknown(unknown, False)), [])
        self.assertEqual(self.failed(we.grade_unknown(unknown, True)), ['style-unknown-refused'])
        accepted = records(result_line('Output style set to writing-for-humans:no-such-style'))
        self.assertEqual(self.failed(we.grade_unknown(accepted, False)), ['style-unknown-refused'])

    def test_model_free_requires_a_zero_cost_result(self):
        self.assertTrue(we.model_free(records(result_line('x', 0))))
        self.assertFalse(we.model_free(records(result_line('x', 0.01))))
        self.assertFalse(we.model_free([]))
        self.assertEqual(we.parse_stream('not json\n[1]\n{"type":"result"}\n'), [{'type': 'result'}])


FAKE_CLAUDE = r'''#!/usr/bin/env python3
"""Stand-in for the model-free claude commands the host check runs."""
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
mode = os.environ.get('FAKE_MODE', 'good')
log = Path(os.environ['FAKE_LOG'])
log.write_text(log.read_text() + json.dumps({'args': args, 'home': os.environ['HOME'],
                                             'config': os.environ['CLAUDE_CONFIG_DIR']}) + '\n')
if args[:2] == ['plugin', 'marketplace'] or args[:2] == ['plugin', 'install']:
    sys.exit(0)
prompt = args[1]
style = 'writing-for-humans:writing-for-humans'
settings = Path('.claude/settings.local.json')
def out(record):
    print(json.dumps(record))
selected = json.loads(settings.read_text())['outputStyle'] if settings.is_file() else 'default'
out({'type': 'system', 'subtype': 'init', 'output_style': selected if mode != 'no-fresh-style' else 'default',
     'skills': ['writing-for-humans:writing-audit', 'writing-for-humans:writing-style'],
     'plugins': [{'name': 'writing-for-humans', 'source': 'writing-for-humans@wfh-eval',
                  'version': '9.9.9' if mode == 'wrong-version' else '0.3.1'}]})
cost = 0.02 if mode == 'paid' else 0
if prompt == '/output-style ' + style:
    settings.parent.mkdir(exist_ok=True)
    settings.write_text(json.dumps({'outputStyle': style}))
    out({'type': 'result', 'result': 'Output style set to ' + style, 'total_cost_usd': cost})
elif prompt.startswith('/output-style writing-for-humans:no-such-style'):
    out({'type': 'result', 'result': 'Unknown output style "writing-for-humans:no-such-style". Available styles: default',
         'total_cost_usd': cost})
else:
    out({'type': 'result', 'result': 'Output style: ' + selected, 'total_cost_usd': cost})
'''


class HostCheckTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.fake = self.base / 'claude'
        self.fake.write_text(FAKE_CLAUDE.replace('#!/usr/bin/env python3', f'#!{sys.executable}', 1))
        self.fake.chmod(0o755)
        self.log = self.base / 'log.jsonl'
        self.log.write_text('')
        self.home = self.base / 'realhome'
        (self.home / '.claude').mkdir(parents=True)
        (self.home / '.claude/settings.json').write_text('{}\n')
        (self.home / '.claude.json').write_text('{}\n')
        self.tmp = self.base / 'tmp'
        self.tmp.mkdir()

    def check(self, mode='good', plugin=PLUGIN):
        env = {'FAKE_MODE': mode, 'FAKE_LOG': str(self.log), 'HOME': str(self.home), 'TMPDIR': str(self.tmp)}
        with mock.patch.dict(os.environ, env), mock.patch.object(tempfile, 'tempdir', None):
            return we.host_check(plugin, claude=str(self.fake))

    def failed(self, host):
        return [check['name'] for check in host['checks'] if not check['passed']]

    def test_passes_runs_isolated_and_cleans_up(self):
        before = we.tree_digest(PLUGIN)
        host = self.check()
        self.assertTrue(host['passed'], self.failed(host))
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertEqual([c['args'][:3] for c in calls[:2]], [['plugin', 'marketplace', 'add'],
                                                               ['plugin', 'install', 'writing-for-humans@wfh-eval']])
        for call in calls:
            self.assertNotEqual(call['home'], str(self.home))
            self.assertTrue(call['config'].startswith(str(self.tmp)), call)
        self.assertEqual(list(self.tmp.iterdir()), [])
        self.assertEqual(we.tree_digest(PLUGIN), before)

    def test_failures_are_reported(self):
        self.assertEqual(self.failed(self.check('wrong-version')), ['plugin-version'])
        self.assertEqual(self.failed(self.check('no-fresh-style')), ['style-active-fresh-session'])
        self.assertEqual(len([n for n in self.failed(self.check('paid')) if n.startswith('model-free')]), 3)

    def test_a_change_to_real_config_fails(self):
        real = self.home / '.claude/settings.json'
        with mock.patch.object(we, 'copy_plugin', side_effect=lambda *a: (real.write_text('{"x": 1}\n'),
                                                                          {'version': '0.3.1'})[1]):
            host = self.check()
        self.assertIn('real-config-unchanged: ~/.claude/settings.json', self.failed(host))
        self.assertFalse(host['passed'])
        self.assertEqual(list(self.tmp.iterdir()), [])

    def test_unrelated_writes_to_claude_json_pass_but_a_temp_dir_entry_fails(self):
        state = self.home / '.claude.json'
        with mock.patch.object(we, 'copy_plugin', side_effect=lambda *a: (state.write_text('{"tips": 2}\n'),
                                                                          {'version': '0.3.1'})[1]):
            self.assertEqual(self.failed(self.check()), [])

        def leak(source, target):
            state.write_text(json.dumps({'projects': {str(Path(target).parent.parent / 'workspace'): {}}}))
            return {'version': '0.3.1'}

        with mock.patch.object(we, 'copy_plugin', side_effect=leak):
            self.assertEqual(self.failed(self.check()), ['real-state-untouched: ~/.claude.json'])


def run_item(passed=True, error=None, scored=True, names=('a', 'b')):
    return {'error': error, 'costUsd': 0.25, 'durationSeconds': 40, 'turns': 7,
            'graders': [{'name': name, 'passed': passed if name == names[-1] else True, 'scored': scored}
                        for name in names]}


def case(name, *items, defined=('a', 'b')):
    return {'name': name, 'graders': [{'name': n} for n in defined], 'arms': {'with': list(items)}}


def result(*items, partial=False, defined=('a', 'b'), cases=None):
    return {'claudeVersion': '2.1.316', 'costUsd': 0.5, 'durationSeconds': 80, 'partial': partial,
            'suite': {'modelOverride': 'claude-sonnet-5-5', 'plugins': [{'name': 'writing-for-humans',
                                                                         'version': '0.3.1'}]},
            'cases': cases if cases is not None else [case('c', *items, defined=defined)]}


def expected(runs=1, cases=None, case_filter=None):
    return {'cases': cases or {'c': ['a', 'b']}, 'runs': runs, 'case_filter': case_filter}


class SummaryTests(unittest.TestCase):
    HOST = {'passed': True}

    def summary(self, res, exp=None, host=HOST, changes=()):
        return we.summarize(res, exp or expected(), host, None, changes)

    def test_miss_counting_rule(self):
        self.assertTrue(self.summary(result(run_item()))['passed'])
        # A failed grader, an error, an unscored grader, a missing grader, a partial run or failed host checks fail.
        self.assertFalse(self.summary(result(run_item(), run_item(passed=False)), expected(runs=2))['passed'])
        self.assertFalse(self.summary(result(run_item(error='timeout')))['passed'])
        self.assertFalse(self.summary(result(run_item(scored=False)))['passed'])
        self.assertFalse(self.summary(result(run_item(names=('a',))))['passed'])
        self.assertFalse(self.summary(result(run_item(), partial=True))['passed'])
        self.assertFalse(self.summary(result(run_item()), host={'passed': False})['passed'])
        self.assertFalse(self.summary(result())['passed'])
        summary = self.summary(result(run_item(), run_item(passed=False)), expected(runs=2))
        self.assertEqual([row['failed_graders'] for row in summary['runs']], [[], ['b']])
        self.assertEqual(summary['agent_cost_usd'], 0.5)
        self.assertEqual(summary['plugins'], ['writing-for-humans@0.3.1'])
        self.assertIn('| c | 2 | FAIL | b |', we.markdown(summary))

    def test_a_case_missing_from_the_result_fails(self):
        exp = expected(cases={'c': ['a', 'b'], 'd': ['x']})
        summary = self.summary(result(run_item()), exp)
        self.assertFalse(summary['passed'])
        self.assertEqual(summary['problems'], ['case d is missing from the result'])
        self.assertIn('Problem: case d is missing from the result', we.markdown(summary))

    def test_a_grader_missing_from_the_result_and_the_case_fails(self):
        # The result's own grader list dropped `b` too, so only the on-disk suite knows about it.
        summary = self.summary(result(run_item(names=('a',)), defined=('a',)))
        self.assertFalse(summary['passed'])
        self.assertEqual(summary['runs'][0]['failed_graders'], ['b'])

    def test_a_short_run_count_fails(self):
        summary = self.summary(result(run_item(), run_item()), expected(runs=3))
        self.assertFalse(summary['passed'])
        self.assertEqual(summary['problems'], ['case c has 2 runs, expected 3'])

    def test_a_case_run_is_never_a_suite_pass(self):
        summary = self.summary(result(run_item()), expected(case_filter='c'))
        self.assertFalse(summary['passed'])
        self.assertEqual(summary['problems'], ['subset run (--case c): never a suite pass'])

    def test_an_unexpected_case_and_run_changes_fail(self):
        res = result(cases=[case('c', run_item()), case('extra', run_item())])
        self.assertEqual(self.summary(res)['problems'], ['case extra is not in the suite'])
        summary = self.summary(result(run_item()), changes=['~/.claude/settings.json changed during the run'])
        self.assertFalse(summary['passed'])

    def test_expected_suite_lists_every_case_and_its_grader_files(self):
        exp = we.expected_suite(SUITE, 3, None)
        self.assertEqual(exp['runs'], 3)
        self.assertEqual(exp['cases'], {
            'audit-not-automatic': ['not-invoked', 'reads-draft', 'skill-offered'],
            'audit-typed': ['loads', 'names-draft', 'no-external-action', 'reads-artifacts-reference',
                            'reads-output-style', 'report-structure']})


class RunnerTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()

    def test_copy_suite_skips_results_and_finds_cases(self):
        results = SUITE / 'results'
        created = not results.exists()
        if created:
            results.mkdir()
            self.addCleanup(results.rmdir)
        self.assertEqual(we.copy_suite(self.base / 'evals'), ['audit-not-automatic', 'audit-typed'])
        self.assertFalse((self.base / 'evals/results').exists())

    def test_copy_plugin_rejects_symlinks_and_non_plugins(self):
        with self.assertRaises(we.Failure):
            we.copy_plugin(self.base, self.base / 'out')
        plugin = self.base / 'p'
        (plugin / '.claude-plugin').mkdir(parents=True)
        (plugin / '.claude-plugin/plugin.json').write_text('{"name": "p", "version": "1.0.0"}')
        (plugin / 'link').symlink_to(plugin / '.claude-plugin/plugin.json')
        with self.assertRaises(we.Failure):
            we.copy_plugin(plugin, self.base / 'out')

    def test_eval_command_pins_model_cost_and_no_judge(self):
        args = we.argparse.Namespace(model='claude-sonnet-5-5', max_cost_usd=2.0, runs=1, case=None, keep_temp=False)
        command = we.eval_command(Path('/s/plugin'), args, Path('/o'))
        for flag, value in (('--model', 'claude-sonnet-5-5'), ('--max-cost-usd', '2.0'), ('--ablation', 'none'),
                            ('--allow-tools', 'Bash'), ('--runs', '1')):
            self.assertEqual(command[command.index(flag) + 1], value)
        self.assertNotIn('--judge-model', command)
        self.assertIn('--scaffold', command)
        self.assertIn('--no-publish', command)

    def test_cli_requires_model_and_cost(self):
        for argv in (['run', '--model', 'm'], ['run', '--max-cost-usd', '1'],
                     ['run', '--model', 'm', '--max-cost-usd', '0']):
            done = subprocess.run([sys.executable, str(RUNNER), *argv], capture_output=True, text=True)
            self.assertEqual(done.returncode, 2, argv)

    def test_copy_git_copies_the_real_executable(self):
        git = we.copy_git(self.base / '.eval-git') / 'git'
        self.assertNotEqual(git.resolve(), Path('/usr/bin/git'))
        done = subprocess.run([str(git), '--version'], capture_output=True, text=True,
                              env={'PATH': str(git.parent), 'HOME': str(self.base)})
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue(done.stdout.startswith('git version'))

    def test_tree_digest_ignores_bytecode_and_sees_changes(self):
        (self.base / 'a.txt').write_text('a')
        digest = we.tree_digest(self.base)
        (self.base / '__pycache__').mkdir()
        (self.base / '__pycache__/x.pyc').write_bytes(b'x')
        self.assertEqual(we.tree_digest(self.base), digest)
        (self.base / 'a.txt').write_text('b')
        self.assertNotEqual(we.tree_digest(self.base), digest)


class RunTests(unittest.TestCase):
    """run() end to end with the host check and `claude plugin eval` replaced; nothing is spent."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.home = self.base / 'home'
        (self.home / '.claude').mkdir(parents=True)
        (self.home / '.claude/settings.json').write_text('{}\n')
        self.tmp = self.base / 'tmp'
        self.tmp.mkdir()

    def run_eval(self, case=None, touch_config=False):
        out = self.base / 'out'
        suite = we.expected_suite(SUITE, 1)
        real_run = subprocess.run

        def fake_eval(command, **kwargs):
            if command[:3] != ['claude', 'plugin', 'eval']:
                return real_run(command, **kwargs)
            names = [case] if case else list(suite['cases'])
            res = result(cases=[{'name': name, 'graders': [{'name': g} for g in suite['cases'][name]],
                                 'arms': {'with': [run_item(names=tuple(suite['cases'][name]))]}} for name in names])
            Path(command[command.index('--json') + 1]).write_text(json.dumps(res))
            if touch_config:
                (self.home / '.claude/settings.json').write_text('{"enabledPlugins": {}}\n')
            return subprocess.CompletedProcess(command, 0)

        args = we.argparse.Namespace(plugin=None, output_dir=str(out), keep_scratch=False, runs=1, case=case,
                                     model='claude-sonnet-5-5', max_cost_usd=2.0, keep_temp=False, dry_run=False)
        with mock.patch.dict(os.environ, {'HOME': str(self.home), 'TMPDIR': str(self.tmp)}), \
                mock.patch.object(tempfile, 'tempdir', None), \
                mock.patch.object(we, 'host_check', return_value={'passed': True, 'checks': [], 'commands': []}), \
                mock.patch.object(we.subprocess, 'run', side_effect=fake_eval), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = we.run(args)
        self.assertEqual(list(self.tmp.iterdir()), [])
        return code, json.loads((out / 'summary.json').read_text()), out

    def test_a_complete_pass_passes_and_records_the_suite(self):
        code, summary, out = self.run_eval()
        self.assertEqual((code, summary['passed'], summary['problems']), (0, True, []))
        self.assertEqual(json.loads((out / 'suite.json').read_text())['runs'], 1)
        self.assertIn('tree: ', (out / 'CANDIDATE.txt').read_text())

    def test_a_case_run_exits_nonzero(self):
        code, summary, _ = self.run_eval(case='audit-typed')
        self.assertEqual(code, 1)
        self.assertIn('subset run (--case audit-typed): never a suite pass', summary['problems'])

    def test_a_real_config_change_during_the_eval_fails(self):
        code, summary, _ = self.run_eval(touch_config=True)
        self.assertEqual(code, 1)
        self.assertEqual(summary['problems'], ['~/.claude/settings.json changed during the run'])


class ScaffoldTests(unittest.TestCase):
    def test_builds_a_branch_with_the_draft_in_its_diff(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp).resolve() / 'workspace'
            workspace.mkdir()
            env = {'PATH': '/usr/bin:/bin', 'HOME': str(Path(temp).resolve())}
            done = subprocess.run(['env', '-i', *[f'{k}={v}' for k, v in env.items()], 'bash',
                                   str(CASES / 'audit-typed/scaffold.sh')], cwd=workspace, capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stderr)

            def git(*args):
                return subprocess.run(['git', *args], cwd=workspace, env={**env, 'GIT_CONFIG_GLOBAL': '/dev/null'},
                                      capture_output=True, text=True, check=True).stdout

            self.assertEqual(git('branch', '--show-current').strip(), 'ttl-decision')
            self.assertEqual(git('diff', '--name-only', 'main...HEAD').split(),
                             ['docs/decision-notes.md', 'src/tidecache/__init__.py'])
            self.assertEqual(git('status', '--porcelain'), '')
            self.assertEqual(sorted(p.name for p in workspace.iterdir()), ['.git', 'README.md', 'docs', 'src'])

    def test_case_scaffolds_delegate_to_the_suite_scaffold(self):
        for case in CASES.iterdir():
            self.assertEqual((case / 'scaffold.sh').read_text(),
                             '#!/usr/bin/env bash\nexec bash "$(dirname "$0")/../../scaffold.sh"\n')


if __name__ == '__main__':
    unittest.main()
