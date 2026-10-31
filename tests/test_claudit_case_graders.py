"""Claudit 4.1 script graders that follow each case's scan: plan items, footer, grade explanations, declines.

The plan-items grader of every case is built from the scan of that case's scaffolded fixture, so the committed
pattern is the deterministic plan. Rebuild them after changing a fixture or the plan rules:

    python3 tests/test_claudit_case_graders.py --write
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_claudit import cl  # noqa: E402
from test_claudit_eval import ce  # noqa: E402
from test_claudit_eval_graders import js_verdicts, regex_grader, verdict  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / 'evals/claudit/cases'
SCAFFOLD_ENV = dict(os.environ, GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)

plan_items_pattern, declined_pattern = ce.plan_items_pattern, ce.declined_pattern
FOOTER = ce.footer_pattern(cl.VERSION)
GRADE_RAISE = ce.GRADE_RAISE
COVERAGE_A = r'(?:^|\n)[ \t]*[-*][ \t]+\*\*Coverage: A\*\*'
DECLINE_FREE = r"(?:^|\n)(?![^\n]*\b(?:not|no|don[\x27’]t|doesn[\x27’]t|never|won[\x27’]t|declined|retired|instead of)\b)" \
               r"[^\n]*\b(?:add|adding|create|creating|enforce|enforcing|set up|setting up|introduce|wire|consider)\b" \
               r"[^\n]{0,80}(?:\bhooks?\b|claude plugin eval|\bevals?\b|\beval (?:suite|campaign|cases?)\b)"
FIXTURE_STEMS = 'deploy-steps|release-report|sample-repo|sample-runbook|missing-guide|sample-plugin'
FIXTURE_FREE = (r'(?:^|\n)(?=[^\n]*(?:%s))(?=[^\n]*(?:\bskills?\b|SKILL\.md|\bprocedures?\b|\bbroken\b|\bstale\b'
                r'|\bmissing\b|n[\x27’]t exist|\bnot exist|\bimport\b|plugin validate|plugin eval|\blsp\b'
                r'|code[- ]intelligence|\bdeny\b|\bhooks?\b|\ballow))') % FIXTURE_STEMS


GRADER = """---
type: regex
pattern: '{pattern}'
{flags}{match}weight: 1
---
{doc}
"""
DOCS = {
    'structure-plan-items': (
        'The Top changes section holds exactly the plan the scan decides for this fixture (Claudit 4.1, issue #174 '
        'requirement 1): {plan}.\n\nScript-graded (case-insensitive), built from the scan by '
        '`tests/test_claudit_case_graders.py`. Each item is a column-0 line `N. **<title>**` (or `N)`, bold around '
        'the number, or a `###`/`####` heading) numbered from 1 in order, with the title word for word; a word with '
        'a dot or slash may be backticked. No other column-0 numbered line may appear in the section, which ends at '
        'the next `#` or `##` heading, a `---` rule or the end of the report. With no items the first non-blank line '
        'says "No changes worth making".'),
    'structure-footer': (
        'The footer gives the Claudit version and the audited commit (issue #174 requirement 6).\n\nScript-graded '
        '(case-sensitive): after a `---` rule, a line has "Claudit {version}; audited commit " then 40 hex '
        'characters (optionally backticked). The exact commit isn\'t compared, because the eval host owns the '
        'workspace\'s history.'),
    'structure-grade-raise': (
        'Every grade below A says which plan items would raise it (issue #174 requirement 5).\n\nScript-graded '
        '(case-insensitive, must not match): a grade line `- **Correctness|Alignment|Coverage: B-F**` with no '
        '"item N" or "items N" (optionally `#N`) later on that line fails.'),
    'structure-coverage-a': (
        'Coverage is A: {why}\n\nScript-graded (case-sensitive): a grade line `- **Coverage: A**`.'),
    'structure-declined': (
        'The report lists both declines under "Declined by the project" with their source lines (issue #174 '
        'requirement 4): `docs/decisions.md:3` retires Claude Code hooks and `docs/decisions.md:5` declines an eval '
        'campaign.\n\nScript-graded (case-sensitive): a `##` or `###` heading "Declined by the project", then, '
        'before the next `#` or `##` heading, each `path:line` (optionally backticked).'),
    'no-invented-declined-recommendation': (
        'The project retired Claude Code hooks and declined an eval campaign, so the report must not recommend '
        'either (issue #174 requirement 4).\n\nScript-graded (case-insensitive, must not match). A line fails when '
        'it has add, adding, create, creating, enforce, enforcing, "set up", "setting up", introduce, wire or '
        'consider, then within 80 characters "hook(s)", `claude plugin eval`, "eval(s)" or "eval suite/campaign/'
        'case(s)". Lines with not, no, don\'t, doesn\'t, never, won\'t, declined, retired or "instead of" are '
        'skipped, so quoting the decline or saying it won\'t be recommended passes.'),
    'no-invented-fixture-findings': (
        'The eval grader, golden report and fixture repository are test data (issue #174 requirement 3), so the '
        'report raises no finding on them.\n\nScript-graded (case-sensitive, must not match): a line that names '
        'one of `' + FIXTURE_STEMS.replace('|', '`, `') + '` and also says skill(s), `SKILL.md`, procedure(s), '
        'broken, stale, missing, "doesn\'t exist"/"not exist", import, plugin validate, plugin eval, lsp, code '
        'intelligence, deny, hook(s) or allow... fails. Mentioning the test data without a finding passes.'),
}


def write_grader(case, name, pattern, flags='', match='', **doc):
    text = GRADER.format(pattern=pattern.replace("'", "''"), flags='flags: %s\n' % flags if flags else '',
                         match='match: %s\n' % match if match else '', doc=DOCS[name].format(**doc))
    (CASES / case / 'graders' / (name + '.md')).write_text(text)


def scaffold_scan(case, workdir):
    """Scaffold a case as the eval host does and scan it."""
    target = (Path(workdir) / case)
    target.mkdir()
    target = target.resolve()
    subprocess.run(['bash', str(CASES / case / 'scaffold.sh')], cwd=target, check=True, env=SCAFFOLD_ENV,
                   capture_output=True)
    ceiling, cl.Scan.ceiling = cl.Scan.ceiling, str(target)  # instruction files above the temp dir don't count
    try:
        return cl.Scan(str(target), True, cl.load_catalog(), '2.1.316').run()
    finally:
        cl.Scan.ceiling = ceiling


def case_graders(case, scan):
    """(name, pattern, flags, match, doc fields) for each scan-derived grader of a case."""
    titles = [item['title'] for item in scan['plan']['items']]
    plan = ', '.join('%d. %s' % (n, t) for n, t in enumerate(titles, 1)) or 'no items ("No changes worth making")'
    out = [('structure-plan-items', plan_items_pattern(titles), 'i', '', {'plan': plan}),
           ('structure-footer', FOOTER, '', '', {'version': cl.VERSION}),
           ('structure-grade-raise', GRADE_RAISE, 'i', 'not_contains', {})]
    if case == 'f7-fixture-noise':
        out.append(('no-invented-fixture-findings', FIXTURE_FREE, '', 'not_contains', {}))
    if case == 'f8-documented-decline':
        refs = ['%s:%d' % (d['path'], d['line']) for d in scan['declined']]
        out += [('structure-declined', declined_pattern(refs), '', '', {}),
                ('structure-coverage-a', COVERAGE_A, '', '', {'why': 'the declined hooks and eval campaign are not gaps.'}),
                ('no-invented-declined-recommendation', DECLINE_FREE, 'i', 'not_contains', {})]
    if case == 'f9-clean':
        out.append(('structure-coverage-a', COVERAGE_A, '', '', {'why': 'nothing is missing.'}))
    return out


def report(titles, grades=('A', 'A', 'A'), summary=None, footer=None, declined='', extra=''):
    summary = summary or ('%d changes are worth making.' % len(titles) if titles else
                          'No changes worth making: the scan found no defects or gaps.')
    items = ''.join('%d. **%s** (Coverage, effort S)\n   Problem: x.\n   Change:\n   ```json\n   {}\n   ```\n'
                    '   Source: [Permission rule syntax](https://code.claude.com/docs/en/permissions)\n\n' % (n, t)
                    for n, t in enumerate(titles, 1))
    lines = '\n'.join('- **%s: %s** (confidence: high). %s' % (name, letter, 'Fine.' if letter == 'A' else
                                                               'Item 1 would raise it to A.')
                      for name, letter in zip(('Correctness', 'Alignment', 'Coverage'), grades))
    footer = footer or 'Claudit %s; audited commit %s' % (cl.VERSION, 'a' * 40)
    return ('# Claudit: x\n\n**Intent:** x. Assumed from the repository; correct me if wrong.\n\n## Grades\n\n%s\n\n'
            '## Top changes\n\n%s\n\n%s%s## Also worth knowing\n\n- Optional: run `/doctor`.%s\n\n---\n%s\n'
            'Claude Code 2.1.316; catalog 2026-10-29.\n' % (lines, summary, items, declined, extra, footer))


@unittest.skipUnless(shutil.which('git') and shutil.which('bash'), 'git and bash needed to scaffold fixtures')
class CaseGraders(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.scans = {case.name: scaffold_scan(case.name, cls.tmp.name)
                     for case in sorted(CASES.iterdir()) if case.is_dir()}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_committed_graders_follow_the_scan(self):
        for case, scan in self.scans.items():
            for name, pattern, flags, match, _ in case_graders(case, scan):
                with self.subTest(case=case, grader=name):
                    grader = regex_grader(CASES / case / 'graders' / (name + '.md'))
                    self.assertEqual(grader['pattern'], pattern, 'rebuild with --write')
                    self.assertEqual(grader.get('flags', ''), flags)
                    self.assertEqual(grader.get('match', ''), match)

    def test_expected_plans(self):
        plans = {case: [i['title'] for i in scan['plan']['items']] for case, scan in self.scans.items()}
        self.assertEqual(plans['f7-fixture-noise'], ['Add a skill for docs/release.md'])
        self.assertEqual(plans['f8-documented-decline'], [])
        self.assertEqual(plans['f9-clean'], [])
        self.assertEqual(len(plans['f3-misconfigured']), 6)
        for case in ('f7-fixture-noise', 'f8-documented-decline', 'f9-clean'):
            self.assertEqual(self.scans[case]['grades']['correctness']['letter'], 'A')
        self.assertEqual(self.scans['f8-documented-decline']['grades']['coverage']['letter'], 'A')
        self.assertEqual(self.scans['f9-clean']['grades']['coverage']['letter'], 'A')
        self.assertEqual([(d['feature'], d['path'], d['line']) for d in self.scans['f8-documented-decline']['declined']],
                         [('stop-hook', 'docs/decisions.md', 3), ('plugin-eval', 'docs/decisions.md', 5)])

    def checks(self):
        """(case, grader, report, expected verdict) for every scan-derived grader."""
        out = []
        for case, scan in self.scans.items():
            titles = [i['title'] for i in scan['plan']['items']]
            graders = {name: regex_grader(CASES / case / 'graders' / (name + '.md'))
                       for name, _, _, _, _ in case_graders(case, scan)}
            plan = graders['structure-plan-items']
            out += [(case, plan, report(titles), True),
                    (case, plan, report(titles).replace('**%s**' % titles[0], '**%s**' % titles[0].replace(
                        'docs/', '`docs/').replace('.md', '.md`')) if titles else report(titles), True),
                    (case, plan, report(titles + ['Add a Stop hook']), False),
                    (case, plan, report(titles[1:] if titles else ['Add a Stop hook']), False)]
            if len(titles) > 1:
                out.append((case, plan, report(list(reversed(titles))), False))
            if titles:
                out.append((case, plan, report(titles).replace('1. **', '1. **Please ', 1), False))
                out.append((case, plan, report(titles).replace('**%s**' % titles[0], '**%s now**' % titles[0], 1),
                            False))
            footer = graders['structure-footer']
            out += [(case, footer, report(titles), True),
                    (case, footer, report(titles, footer='`Claudit %s; audited commit %s`' % (cl.VERSION, 'b' * 40)),
                     True),
                    (case, footer, report(titles, footer='Claudit %s; not a git repo' % cl.VERSION), False),
                    (case, footer, report(titles, footer='Claudit 4.0.1; audited commit %s' % ('a' * 40)), False),
                    (case, footer, report(titles, footer='Claudit %s; audited commit abc123' % cl.VERSION), False)]
            raise_ = graders['structure-grade-raise']
            out += [(case, raise_, report(titles, grades=('A', 'C', 'B')), True),
                    (case, raise_, report(titles).replace('**Coverage: A** (confidence: high). Fine.',
                                                          '**Coverage: B** (confidence: high). One gap.'), False),
                    (case, raise_, report(titles).replace('**Coverage: A** (confidence: high). Fine.',
                                                          '**Coverage: C** (confidence: high). Items #1 and #2.'),
                     True)]
            if 'structure-coverage-a' in graders:
                out += [(case, graders['structure-coverage-a'], report(titles), True),
                        (case, graders['structure-coverage-a'], report(titles, grades=('A', 'A', 'B')), False)]
            if case == 'f8-documented-decline':
                section = ('## Declined by the project\n\n- **Hooks** (`docs/decisions.md:3`): "Claude Code hooks were '
                           'retired."\n- **Plugin evals** (`docs/decisions.md:5`): "deliberately has no eval '
                           'campaign;"\n\n')
                declined, free = graders['structure-declined'], graders['no-invented-declined-recommendation']
                out += [(case, declined, report([], declined=section), True),
                        (case, declined, report([], declined=section.replace(':5', '')), False),
                        (case, declined, report([], extra='\n- docs/decisions.md:3 and docs/decisions.md:5'), False),
                        (case, free, report([], declined=section), True),
                        (case, free, report([], extra='\n- Hooks were retired, so I don\'t recommend adding one.'),
                         True),
                        (case, free, report([], extra='\n- Consider adding a Stop hook that runs `bin/check`.'), False),
                        (case, free, report([], extra='\n- Add evals and run `claude plugin eval` before release.'),
                         False)]
            if case == 'f7-fixture-noise':
                free = graders['no-invented-fixture-findings']
                out += [(case, free, report(titles), True),
                        (case, free, report(titles, extra='\n- Test data in `tests/fixtures/sample-repo/` and '
                                                          '`tests/golden/release-report.md` is excluded.'), True),
                        (case, free, report(titles, extra='\n- Add a skill for `tests/golden/release-report.md`.'),
                         False),
                        (case, free, report(titles, extra='\n- `tests/fixtures/sample-repo/CLAUDE.md` has a broken '
                                                          'import.'), False),
                        (case, free, report(titles, extra='\n- `deploy-steps.md` is a procedure with no skill.'),
                         False)]
        return out

    def test_graders_pass_and_fail(self):
        for case, grader, text, want in self.checks():
            with self.subTest(case=case, pattern=grader['pattern'][:40], want=want):
                self.assertEqual(verdict(grader, text), want, text)

    @unittest.skipUnless(shutil.which('node'), 'node not installed')
    def test_javascript_engine_agrees(self):
        checks = self.checks()
        self.assertEqual(js_verdicts([[g['pattern'], g.get('flags', ''), g.get('match', ''), t]
                                      for _, g, t, _ in checks]), [want for _, _, _, want in checks])


def write_all():
    with tempfile.TemporaryDirectory() as tmp:
        for case in sorted(p.name for p in CASES.iterdir() if p.is_dir()):
            for name, pattern, flags, match, doc in case_graders(case, scaffold_scan(case, tmp)):
                write_grader(case, name, pattern, flags, match, **doc)
                print('wrote %s/graders/%s.md' % (case, name))


if __name__ == '__main__':
    if sys.argv[1:] == ['--write']:
        write_all()
    else:
        unittest.main()
