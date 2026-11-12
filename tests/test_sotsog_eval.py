"""Offline checks for the sotsog eval: script graders, calibration samples, the outcome reader's attacker pass,
the ledger's stop line, the miss rule and the summary's bars. Nothing here calls a model."""
import contextlib
import csv
import io
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import re
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'bin/sotsog-eval'
sys.dont_write_bytecode = True

loader = importlib.machinery.SourceFileLoader('sotsog_eval', str(RUNNER))
spec = importlib.util.spec_from_loader('sotsog_eval', loader)
e = importlib.util.module_from_spec(spec)
loader.exec_module(e)
g = e.g

CASES = g.load_cases()


class Suite(unittest.TestCase):
    def test_five_cases_with_the_planned_keys(self):
        self.assertEqual(list(CASES), ['1-already-have', '2-real-gap', '3-breaks-reliance', '4-vendor-claim', '5-flip'])
        expected = {'1-already-have': ['no', 'adapt'], '2-real-gap': ['adopt', 'adapt'], '3-breaks-reliance': ['no'],
                    '4-vendor-claim': ['adapt', 'not now', 'no'], '5-flip': ['adopt', 'adapt']}
        for name, case in CASES.items():
            self.assertEqual(case['key']['expected'], expected[name])
            self.assertEqual(case['key']['go'], name in ('2-real-gap', '5-flip'))
            self.assertEqual('gaps' in case['key'], name == '4-vendor-claim')
            self.assertEqual(set(case['key']['items']), set(g.ITEMS))

    def test_library_roles_match_the_files(self):
        for case in CASES.values():
            files = sorted(p.name for p in (case['dir'] / 'research/library').glob('*.md'))
            self.assertEqual(sorted(case['library']), files)
            roles = set(case['library'].values())
            self.assertTrue({'report', 'critique', 'competitor', 'noise'} <= roles, case['name'])

    def test_prompts_point_at_the_link_and_library_and_never_name_a_library_file(self):
        for case in CASES.values():
            self.assertIn('{research}/link.md', case['prompt'])
            self.assertIn('{research}/library/', case['prompt'])
            self.assertIn('Write the decision to a file.', case['prompt'])
            for name in case['library']:
                self.assertNotIn(name[:-3], case['prompt'])

    def test_case_5_reason_is_the_deployer_requirement(self):
        why = CASES['5-flip']['key']['items']['why']['point']
        self.assertIn('Coastline', why)
        self.assertIn('1 March 2027', why)
        self.assertIn('1 March 2027', CASES['5-flip']['prompt'])

    def test_skill_text_shares_no_fixture_term(self):
        plugin = ROOT / 'plugins/sotsog'
        if not plugin.is_dir():
            self.skipTest('plugin not written yet (the suite is frozen first)')
        terms = {term for case in CASES.values() for term in case['terms']}
        for path in plugin.rglob('*'):
            if path.is_file():
                text = path.read_text(errors='replace').lower()
                hits = [term for term in terms if term.lower() in text]
                self.assertEqual(hits, [], f'{path.relative_to(ROOT)} uses fixture terms')


class Calibration(unittest.TestCase):
    def test_every_sample_gets_its_expected_script_verdicts(self):
        for name, case in CASES.items():
            expected = e.load_expected(case)
            self.assertEqual(set(expected), set(e.SAMPLES), name)
            for sample in e.SAMPLES:
                document = (case['dir'] / 'calibration' / f'{sample}.md').read_text()
                script = g.script_grades(document, case)
                grades = {'structure': script['structure']['passed'], 'outcome': script['outcome']['passed']}
                rows = g.calibration_rows(case, sample, expected[sample], grades, script, False)
                failed = [r for r in rows if not r['ok']]
                self.assertEqual(failed, [], f'{name} {sample}')

    def test_expectations_cover_exactly_the_judges_each_sample_gets(self):
        for name, case in CASES.items():
            for sample, want in e.load_expected(case).items():
                document = (case['dir'] / 'calibration' / f'{sample}.md').read_text()
                script = g.script_grades(document, case)
                kinds = g.judges_needed(case['key'], script['outcome']['value'], script['depth_script'])
                self.assertEqual('brief' in want, 'brief' in kinds, f'{name} {sample} brief')
                self.assertEqual('open_questions' in want, 'open-questions' in kinds, f'{name} {sample} open questions')
                self.assertEqual('gaps' in want, 'gaps' in kinds, f'{name} {sample} gaps')
                if want['depth']:
                    self.assertIn('depth', kinds)

    def test_plain_samples_use_a_different_verdict_shape_each(self):
        shapes = {name: g.outcome((case['dir'] / 'calibration/plain.md').read_text())[1:]
                  for name, case in CASES.items()}
        self.assertTrue(all(where != 'h1' for where, _ in shapes.values()))
        firsts = [text.split()[0].strip('#*:').lower() for _, text in shapes.values() if text]
        self.assertGreaterEqual(len(set(firsts)), 3)


class Outcome(unittest.TestCase):
    def read(self, text):
        return g.outcome(text)[0]

    def test_template_h1(self):
        self.assertEqual(self.read('# Fragments: no for Lanternhall\n'), 'no')
        self.assertEqual(self.read('# Fragments: not now for Lanternhall\n'), 'not now')
        self.assertEqual(self.read('# Signing: adapt for Lanternhall\n'), 'adapt')

    def test_shapes_a_baseline_writes(self):
        cases = {
            '## Recommendation\n\nWe recommend adopting the lint. It helps.': 'adopt',
            '## Recommendation\n\nDon\'t adopt it: we already do this.': 'no',
            'Verdict: adapt. Take the lint.': 'adapt',
            '**Decision:** No. Keep reviews.': 'no',
            '**Decision**\n\nNot now.': 'not now',
            '## Conclusion\n\nNot now. Little to save.': 'not now',
            '# Recommendation: adopt signed releases\n': 'adopt',
            '- Recommendation: reject.': 'no',
            'Decision - adopt in part': 'adapt',
            'Recommendation: Yes, adopt it.': 'adopt',
        }
        for text, want in cases.items():
            self.assertEqual(self.read(text), want, text)

    def test_round_1_review_table(self):
        cases = {
            '## Recommendation\n\nWe will adopt the lint and lock timeout.': 'adopt',
            "## Decision\n\nWe'll adapt it: lint only.": 'adapt',
            "## Recommendation\n\nI'd recommend adapting the idea.": 'adapt',
            '## Recommendation\n\nLanternhall should adopt a migration lint.': 'adopt',
            '## Recommendation\n\nNot at this time.': 'not now',
            '## Recommendation\n\nHold off for now.': 'not now',
            '## Recommendation\n\nWait until CI passes 30 minutes.': 'not now',
            '## Decision drivers\n\nCost and risk.\n\n## Recommendation\n\nAdopt.': 'adopt',
            '## TL;DR\n\nAdopt the lint.': 'adopt',
            '## Bottom line\n\nNo.': 'no',
            '## Summary\n\nNot now: CI is fast.': 'not now',
            '## Short answer\n\nNot now.': 'not now',
            'Verdict: adopt, partially.': 'adapt',
            "## Recommendation\n\nWe won't adopt it.": 'no',
            "## Recommendation\n\nThe team shouldn't adopt this.": 'no',
            '## Recommendation\n\nMy recommendation is to adopt it.': 'adopt',
            '## Recommendation\n\nI think we should adopt it.': 'adopt',
        }
        for text, want in cases.items():
            self.assertEqual(self.read(text), want, text)

    def test_real_baseline_verdicts(self):
        # Verbatim from the five baseline screen documents (results/baseline-screen, head 6393d8c).
        cases = {
            '# Release notes in every pull request: already in place, change nothing\n\nDate 2026-11-12.\n\n'
            '## Decision\n\nDo not adopt anything new. Lanternhall already does what the post describes,': 'no',
            "# Safe migrations (from Fernhill Transit's post): adopt in part for Lanternhall\n\n"
            'We adopt a migration linter in CI, a lock timeout on every migration, and the': 'adapt',
            "# Pre-merge review: keep it, don't adopt Quarry Labs' ship-to-main\n\n"
            '**Decision: do not adopt.** Keep required pull request reviews on `main`. Attack': 'no',
            '# AI test selection (Prescient Select): do not adopt for Lanternhall\n\n'
            'Date 2026-11-12.\n\n## Decision\n\nDo not adopt AI or predictive test selection. Keep running': 'no',
            '# Signed releases with published build provenance: adopt for Lanternhall\n\n'
            'We will sign every release artifact and publish build provenance for it,': 'adopt',
        }
        for text, want in cases.items():
            self.assertEqual(self.read(text), want, text[:60])

    def test_hedged_or_negative_subjects_stay_unread(self):
        for text in ('Recommendation: nobody should adopt this.', 'Recommendation: maybe we should adopt it.',
                     'Recommendation: perhaps the team should adopt it.', 'Recommendation: we might adopt it.',
                     'Recommendation: whether to adopt is open.'):
            self.assertIsNone(self.read(text), text)

    def test_decision_labels_come_before_summary_labels(self):
        cases = {
            '## Summary\n\nNo team we read regretted it.\n\n## Recommendation\n\nAdopt.': 'adopt',
            '## Summary\n\nAdopting trunk-based development means pushing to main.\n\n## Recommendation\n\nNo.': 'no',
            '## Conclusion\n\nLater sections explain the cost.\n\n## Recommendation\n\nAdopt.': 'adopt',
            '# Monorepos: no clear winner\n\n## Recommendation\n\nAdopt.': 'adopt',
            '## TL;DR\n\nNot now.\n\n## Details\n\nThe suite is fast.': 'not now',
        }
        for text, want in cases.items():
            self.assertEqual(self.read(text), want, text)

    def test_a_label_without_a_verdict_doesnt_stop_the_search(self):
        self.assertEqual(self.read('## Summary\n\nThe post describes a linter.\n\n## Decision\n\nAdapt.'), 'adapt')
        self.assertEqual(g.outcome('## Summary\n\nA post.\n')[1:], ('none', '## Summary'))

    def test_overlapping_entries_match_whole_words_longest_first(self):
        self.assertEqual(g.verdict_outcome('not now'), 'not now')
        self.assertEqual(g.verdict_outcome('no'), 'no')
        self.assertEqual(g.verdict_outcome('No, not now'), 'no')
        self.assertEqual(g.verdict_outcome('not now, then no'), 'not now')
        self.assertEqual(g.verdict_outcome('adopt in part'), 'adapt')
        self.assertEqual(g.verdict_outcome('adopt'), 'adopt')
        self.assertEqual(g.verdict_outcome('partially adopt'), 'adapt')
        self.assertEqual(g.verdict_outcome('not adopt'), 'no')
        self.assertEqual(g.verdict_outcome('not adopting'), 'no')
        self.assertEqual(g.verdict_outcome('not adopted'), 'no')
        self.assertIsNone(g.verdict_outcome('nothing'))
        self.assertIsNone(g.verdict_outcome('nowhere near ready'))
        self.assertIsNone(g.verdict_outcome('adoption is unclear'))

    def test_only_the_start_of_the_verdict_counts(self):
        self.assertEqual(self.read('Recommendation: adopt, with no change to CI.'), 'adopt')
        self.assertEqual(self.read('Recommendation: no: adopting would remove review.'), 'no')
        self.assertIsNone(self.read('Recommendation: it depends; we might adopt it.'))

    def test_attacker_pass(self):
        # A qualifier or negation in front of every allowed form must not read as that form.
        for phrase, outcome in g.VERDICT_PHRASES.items():
            self.assertNotEqual(self.read(f'Recommendation: maybe {phrase}.'), outcome, phrase)
            self.assertIsNone(self.read(f'Recommendation: unclear whether to {phrase}.'), phrase)
        self.assertEqual(self.read('Recommendation: do not adopt.'), 'no')
        self.assertEqual(self.read("Recommendation: don’t adopt."), 'no')

    def test_body_text_is_not_a_label(self):
        self.assertIsNone(self.read('Decision makers liked it.\n\nAdopt.'))
        self.assertIsNone(self.read('Recommendations from the vendor: adopt.'))

    def test_first_label_only_and_code_ignored(self):
        self.assertEqual(self.read('## Decision\n\nNo.\n\n## Recommendation\n\nAdopt.'), 'no')
        self.assertIsNone(self.read('```\nDecision: adopt\n```\n'))

    def test_no_label_is_a_miss(self):
        self.assertIsNone(self.read('We looked at it. Adopt.'))


GOOD = (CASES['1-already-have']['dir'] / 'calibration/good.md').read_text()


class Structure(unittest.TestCase):
    def checks(self, text):
        return g.structure(text)['checks']

    def test_good_passes(self):
        self.assertTrue(g.structure(GOOD)['passed'])

    def test_each_check_fails_alone(self):
        self.assertFalse(self.checks(GOOD.replace('| Fit |', '| Rating |'))['comparison table'])
        self.assertFalse(self.checks(GOOD.replace('| already have |', '| yes |', 1))['comparison table'])
        self.assertFalse(self.checks(GOOD.replace(': no for Lanternhall', ': rejected for Lanternhall'))['decision line'])
        self.assertFalse(self.checks(GOOD.replace('## Revisit when', '## Later'))['revisit when'])
        self.assertFalse(self.checks(GOOD.replace('**Whose conditions:**', '**Context:**'))['skeptical read'])
        self.assertFalse(self.checks(GOOD.replace('read 2026-11-12. Independent; self-reported.',
                                                  'read recently. Independent.'))['sources with dates'])

    def test_brief_only_on_go(self):
        with_brief = GOOD.replace('## Sources', '## Implementation brief\n\nDo it.\n\n## Sources')
        self.assertFalse(self.checks(with_brief)['brief iff go'])
        go = CASES['2-real-gap']['dir'] / 'calibration/good.md'
        text = go.read_text()
        self.assertTrue(self.checks(text)['brief iff go'])
        self.assertFalse(self.checks(text.replace('## Implementation brief', '## Plan'))['brief iff go'])

    def test_nested_source_lines_count_with_their_item(self):
        text = GOOD.replace('- Mei Tanaka, "Generate the changelog from your commits instead" '
                            '(conventional-commits-changelogs.md), read 2026-11-12. Library maintainer; competing approach.',
                            '- Mei Tanaka (conventional-commits-changelogs.md)\n  - read 2026-11-12')
        self.assertTrue(self.checks(text)['sources with dates'])


class Depth(unittest.TestCase):
    case = CASES['1-already-have']

    def test_cites_by_name_stem_or_title(self):
        by_stem = g.depth_script('See fragment-fatigue and conventional-commits-changelogs.md.', self.case)
        self.assertTrue(by_stem['passed'])
        by_title = g.depth_script('"Fragment fatigue: when per-change release notes go wrong" and '
                                  '"Generate the changelog from your commits instead".', self.case)
        self.assertTrue(by_title['passed'])

    def test_needs_a_critique_and_a_competitor(self):
        self.assertFalse(g.depth_script('fragment-fatigue.md only', self.case)['passed'])
        self.assertFalse(g.depth_script('conventional-commits-changelogs.md and fragment-shaders-intro.md',
                                        self.case)['passed'])

    def test_judge_must_confirm_both_roles(self):
        script = g.script_grades(GOOD, self.case)
        both = {'sources': [{'file': 'fragment-fatigue.md', 'described': True, 'reason': ''},
                            {'file': 'conventional-commits-changelogs.md', 'described': True, 'reason': ''}]}
        one = {'sources': [{'file': 'fragment-fatigue.md', 'described': True, 'reason': ''},
                           {'file': 'conventional-commits-changelogs.md', 'described': False, 'reason': ''}]}
        self.assertTrue(g.final_grades(self.case, script, {'depth': both})['depth'])
        self.assertFalse(g.final_grades(self.case, script, {'depth': one})['depth'])
        self.assertIsNone(g.final_grades(self.case, script, {})['depth'])


class Judges(unittest.TestCase):
    def test_needed_judges(self):
        key2, key4 = CASES['2-real-gap']['key'], CASES['4-vendor-claim']['key']
        passed, failed = {'passed': True}, {'passed': False}
        self.assertEqual(g.judges_needed(key2, 'adopt', passed), ['reader', 'compare', 'brief', 'depth'])
        self.assertEqual(g.judges_needed(key2, 'no', failed), ['reader', 'compare', 'brief', 'open-questions'])
        self.assertEqual(g.judges_needed(key4, 'not now', failed), ['reader', 'compare', 'open-questions', 'gaps'])

    def test_comparator_never_sees_the_document_and_reader_never_sees_the_key(self):
        case = CASES['4-vendor-claim']
        prompt = g.compare_prompt(case['key'], {'decided': 'a', 'why': 'b', 'next': 'c'})
        self.assertNotIn('<document>', prompt)
        self.assertNotIn('expected', prompt)
        self.assertNotIn('gaps', prompt)
        self.assertNotIn(case['key']['items']['why']['point'], g.document_prompt('doc'))

    def test_depth_judge_gets_only_cited_critiques_and_competitors(self):
        case = CASES['1-already-have']
        prompt = g.depth_prompt('doc', case, {'fragment-fatigue.md': 'critique', 'maple-row-fragments-a-year-on.md':
                                              'report'})
        self.assertIn('fragment-fatigue.md', prompt)
        self.assertNotIn('maple-row', prompt)
        self.assertNotIn('expected', prompt)

    def test_every_judge_has_a_prompt_and_schema(self):
        for kind in g.SCHEMAS:
            self.assertTrue(g.judge_prompt_text(kind).strip(), kind)

    def test_judge_command_has_no_tools_and_a_budget(self):
        command = e.judge_command('reader', 'x', 'claude-sonnet-5-5', 0.1, g.SUITE)
        self.assertEqual(command[command.index('--tools') + 1], '')
        self.assertIn('--max-budget-usd', command)
        self.assertIn('--system-prompt', command)


class Task(unittest.TestCase):
    def test_arms_differ_only_by_the_plugin(self):
        base = e.task_command('p', 'baseline', 'm', 'high', Path('/plugin'), Path('/r'), 1.25)
        sotsog = e.task_command('p', 'sotsog', 'm', 'high', Path('/plugin'), Path('/r'), 1.25)
        self.assertEqual(sotsog[:len(base)], base)
        self.assertEqual(sotsog[len(base):], ['--plugin-dir', '/plugin'])
        tools = base[base.index('--tools') + 1].split(',')
        self.assertNotIn('Bash', tools)
        self.assertNotIn('WebFetch', tools)
        self.assertEqual(base[base.index('--max-budget-usd') + 1], '1.2500')
        self.assertEqual(base[base.index('--effort') + 1], 'high')
        self.assertEqual(base[base.index('--add-dir') + 1], '/r')

    def test_env_disables_autoupdater(self):
        self.assertEqual(e.claude_env()['DISABLE_AUTOUPDATER'], '1')

    def test_init_proof(self):
        plugin = Path('/tmp/p')
        good = {'model': 'm', 'mcp_servers': [], 'plugins': [{'name': 'sotsog', 'version': '0.1.0', 'path': '/tmp/p'}]}
        self.assertEqual(e.init_proof(good, 'sotsog', 'm', plugin, '0.1.0'), [])
        self.assertTrue(e.init_proof(good, 'baseline', 'm', plugin, '0.1.0'))
        self.assertTrue(e.init_proof(dict(good, plugins=[]), 'sotsog', 'm', plugin, '0.1.0'))
        self.assertTrue(e.init_proof(dict(good, model='other'), 'sotsog', 'm', plugin, '0.1.0'))
        self.assertTrue(e.init_proof({}, 'baseline', 'm', plugin, '0.1.0'))

    def test_changed_documents(self):
        before = {'README.md': 'a', 'docs/x.md': 'b', 'bin/check': 'c'}
        self.assertEqual(e.changed_documents(before, dict(before)), [])
        self.assertEqual(e.changed_documents(before, dict(before, **{'docs/decisions/new.md': 'd'})),
                         ['docs/decisions/new.md'])
        self.assertEqual(e.changed_documents(before, dict(before, **{'README.md': 'z', 'new.md': 'd',
                                                                      'bin/check': 'q'})), ['README.md', 'new.md'])

    def test_no_single_document_fails_every_grader(self):
        case = CASES['4-vendor-claim']
        for documents in ([], ['a.md', 'b.md']):
            grades = e.run_grades({'documents': documents, 'invalid': False}, case)
            self.assertFalse(grades['structure'])
            self.assertFalse(grades['outcome'])
            self.assertEqual(grades['gaps'], {'who_gains': False, 'baseline': False})

    def test_skill_loaded(self):
        call = {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'name': 'Skill',
                                                              'input': {'skill': 'sotsog:sotsog'}}]}}
        self.assertTrue(e.skill_loaded([call]))
        self.assertFalse(e.skill_loaded([]))


def ledger_rows(path):
    with Path(path).open(newline='') as handle:
        return list(csv.DictReader(handle))


class Spend(unittest.TestCase):
    def test_ledger_rows_carry_a_cumulative_total(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'ledger.csv'
            ledger = e.Ledger(path, 14, 'test')
            grant = ledger.reserve(1.0)
            ledger.settle(grant, 0.4, 'task', 'sotsog', '1-already-have', 'run-1')
            grant = ledger.reserve(1.0)
            ledger.settle(grant, 0.3, 'judge reader')
            rows = ledger_rows(path)
            self.assertEqual(list(rows[0]), list(e.LEDGER_FIELDS))
            self.assertEqual([r['cumulative_usd'] for r in rows], ['0.400000', '0.700000'])
            self.assertAlmostEqual(e.Ledger(path, 14, 'next').total(), 0.7)

    def test_stop_line_refuses_a_call_that_could_cross_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'ledger.csv'
            ledger = e.Ledger(path, 14, 'test')
            ledger.settle(ledger.reserve(1.0), 13.0, 'task')
            self.assertIsNone(ledger.reserve(1.25))
            self.assertEqual(ledger.reserve(1.0), 1.0)

    def test_near_the_line_calls_wait_for_those_in_flight(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = e.Ledger(Path(tmp) / 'ledger.csv', 2.0, 'test')
            first = ledger.reserve(1.5)
            got = []
            waiter = threading.Thread(target=lambda: got.append(ledger.reserve(1.0)))
            waiter.start()
            waiter.join(0.2)
            self.assertTrue(waiter.is_alive())
            ledger.settle(first, 0.5, 'task')
            waiter.join(2)
            self.assertEqual(got, [1.0])

    def test_invocation_ceiling(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = e.Ledger(Path(tmp) / 'ledger.csv', 14, 'test', max_cost=1.0)
            ledger.settle(ledger.reserve(0.5), 0.6, 'task')
            self.assertIsNone(ledger.reserve(0.5))
            self.assertEqual(ledger.reserve(0.4), 0.4)

    def test_hard_ceiling(self):
        with self.assertRaises(e.Failure):
            e.Ledger('x.csv', 20.5, 'test')
        with self.assertRaises(Exception):
            e.stop_line('21')
        self.assertEqual(e.stop_line('20'), 20.0)
        self.assertEqual(e.DEFAULT_STOP_LINE, 14.0)

    def test_paid_commands_need_a_ledger(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            e.main(['run', '--stage', 'screen', '--output-dir', '/tmp/never'])


def record(arm, case, run, grades=None, invalid=False):
    r = {'arm': arm, 'case': case, 'run': run, 'invalid': invalid, 'documents': ['d.md'], 'cost_usd': 0.5,
         'duration_seconds': 60}
    if grades is not None:
        r['grades'] = grades
    return r


def perfect(case):
    key = CASES[case]['key']
    grades = {'structure': True, 'outcome': True, 'outcome_value': key['expected'][0],
              'cold_read': {item: True for item in g.ITEMS}, 'depth': True}
    if key['go']:
        grades['brief'] = True
    if key['expected'][0] in ('no', 'not now'):
        grades['open_questions'] = 0
    if 'gaps' in key:
        grades['gaps'] = {gap: True for gap in g.GAPS}
    return grades


class Bars(unittest.TestCase):
    def records(self, sotsog=perfect, baseline=lambda case: None):
        rows = []
        for case in CASES:
            for run in (1, 2, 3):
                rows.append(record('sotsog', case, run, sotsog(case)))
                b = baseline(case)
                rows.append(record('baseline', case, run, b, invalid=b is None))
        return rows

    def bars(self, rows):
        s = e.arm_metrics(rows, CASES, 'sotsog', False)
        b = e.arm_metrics(rows, CASES, 'baseline', True)
        return {bar['bar']: bar['passed'] for bar in e.bars(s, b)}

    def test_invalid_baseline_counts_in_its_favour(self):
        # Every baseline run invalid counts as 15/15, so sotsog can't be strictly above it.
        bars = self.bars(self.records())
        self.assertFalse(bars['2 Outcome'])
        self.assertFalse(bars['3 Cold read'])
        self.assertTrue(bars['1 Structure'])

    def test_all_pass_against_a_weaker_baseline(self):
        def weak(case):
            grades = perfect(case)
            grades['outcome'] = case != '5-flip'
            grades['cold_read'] = {'decided': True, 'why': False, 'next': True}
            return grades
        self.assertTrue(all(self.bars(self.records(baseline=weak)).values()))

    def test_ungraded_sotsog_is_a_miss(self):
        def ungraded_depth(case):
            grades = perfect(case)
            if case in ('1-already-have', '2-real-gap'):
                grades['depth'] = None
            return grades

        def weak(case):
            return dict(perfect(case), outcome=False)
        self.assertFalse(self.bars(self.records(sotsog=ungraded_depth, baseline=weak))['7 Depth'])

    def test_open_questions_bar(self):
        def one_two(case):
            grades = perfect(case)
            if case == '3-breaks-reliance':
                grades['open_questions'] = 2
            return grades
        self.assertFalse(self.bars(self.records(sotsog=one_two))['4 Open questions'])

    def test_summary_incomplete_on_missing_run_or_changed_suite(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / 'suite.json').write_text(json.dumps({'stage': 'gate', 'arms': ['baseline', 'sotsog'], 'runs': 3,
                                                        'cases': list(CASES)}))
            (out / 'candidate.json').write_text(json.dumps(dict(e.frozen_ids(), suite_tree='0' * 40)))
            (out / 'guard.json').write_text(json.dumps({'problems': []}))
            folder = out / '1-already-have-sotsog' / 'run-1'
            folder.mkdir(parents=True)
            (folder / 'record.json').write_text(json.dumps(record('sotsog', '1-already-have', 1,
                                                                  perfect('1-already-have'))))
            summary = e.summarize(out)
            self.assertFalse(summary['complete'])
            self.assertTrue(any('suite_tree' in p for p in summary['problems']))
            self.assertTrue(any('missing 1-already-have baseline run 1' in p for p in summary['problems']))
            self.assertTrue(any('calibration' in p for p in summary['problems']))
            self.assertFalse(summary['passed'])


class Calibrated(unittest.TestCase):
    def passing(self, ids):
        rows = [{'case': name, 'sample': s, 'grader': 'structure', 'ok': True} for name in CASES for s in e.SAMPLES]
        return {'judges': True, 'judge_model': 'claude-sonnet-5-5', 'candidate': dict(ids, clean=True), 'rows': rows}

    def test_calibration_must_match_the_suite_and_pass(self):
        ids = {'suite_tree': 'a', 'runner_blob': 'b', 'clean': True}
        self.assertEqual(e.calibration_problems(self.passing(ids), CASES, ids, 'claude-sonnet-5-5'), [])
        self.assertTrue(e.calibration_problems(self.passing(ids), CASES, dict(ids, suite_tree='c'), 'claude-sonnet-5-5'))
        failing = self.passing(ids)
        failing['rows'][0]['ok'] = False
        self.assertTrue(e.calibration_problems(failing, CASES, ids, 'claude-sonnet-5-5'))
        self.assertTrue(e.calibration_problems(dict(self.passing(ids), judges=False), CASES, ids, 'claude-sonnet-5-5'))
        self.assertTrue(e.calibration_problems(None, CASES, ids, 'claude-sonnet-5-5'))

    def test_gate_refuses_a_partial_run(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(io.StringIO()):
            code = e.main(['run', '--stage', 'gate', '--case', '1-already-have', '--runs', '3', '--max-cost-usd', '1',
                           '--output-dir', str(Path(tmp) / 'out'), '--ledger', str(Path(tmp) / 'l.csv')])
            self.assertEqual(code, 1)
            self.assertFalse((Path(tmp) / 'l.csv').exists())


if __name__ == '__main__':
    unittest.main()
