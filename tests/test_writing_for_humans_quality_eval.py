"""Offline checks for the Writing for Humans quality eval: script graders, calibration samples, style proof,
command isolation, budget, ledger and the summary's completeness rule. Nothing here calls a model."""
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'bin/writing-for-humans-quality-eval'

loader = importlib.machinery.SourceFileLoader('wfh_quality_eval', str(RUNNER))
spec = importlib.util.spec_from_loader('wfh_quality_eval', loader)
q = importlib.util.module_from_spec(spec)
loader.exec_module(q)

CASES = q.load_cases()


class Sentences(unittest.TestCase):
    def test_splits_paragraphs_lists_and_headings(self):
        text = '# Title\n\nFirst one. Second one?\n\n- Item one. Item two.\n1. Numbered.\n'
        self.assertEqual(q.units(text), [('heading', 'Title'), ('sentence', 'First one.'), ('sentence', 'Second one?'),
                                         ('sentence', 'Item one.'), ('sentence', 'Item two.'),
                                         ('sentence', 'Numbered.')])

    def test_abbreviations_decimals_and_files_do_not_split(self):
        text = 'Use a tool, e.g. Grep, to look. Version 3.0 raised it to 1.5x in load.py today. Done.'
        self.assertEqual(q.sentences(text), ['Use a tool, e.g. Grep, to look.',
                                             'Version 3.0 raised it to 1.5x in load.py today.', 'Done.'])

    def test_code_fences_and_tables_are_not_prose(self):
        text = 'Before.\n\n```\nprint("x"). Not prose.\n```\n\n| a | b |\n|---|---|\n| c. | d. |\n\nAfter.'
        self.assertEqual(q.sentences(text), ['Before.', 'After.'])

    def test_blockquotes_and_bold_labels_are_prose(self):
        self.assertEqual(q.sentences('> Quoted line. Second.\n\n**Billing** is half done.'),
                         ['Quoted line.', 'Second.', '**Billing** is half done.'])


class Opening(unittest.TestCase):
    def test_first_three_sentences_with_headings_uncounted(self):
        text = '## Head\n\nOne. Two. Three. Four.'
        self.assertEqual(q.opening(text), 'Head\nOne.\nTwo.\nThree.')

    def test_eighty_word_cap_when_shorter(self):
        long = ' '.join(['word'] * 50) + '. ' + ' '.join(['more'] * 50) + '. End.'
        excerpt = q.opening(long)
        self.assertEqual(len(excerpt.split()), 80)
        self.assertNotIn('End', excerpt)

    def test_short_output_is_whole(self):
        self.assertEqual(q.opening('Only one.'), 'Only one.')


class RepeatedContent(unittest.TestCase):
    def test_exact_repeat(self):
        repeats = q.repeated_content('The queue stays in SQLite. Other news here. The queue stays in SQLite.')
        self.assertEqual(len(repeats), 1)
        self.assertEqual(repeats[0]['jaccard'], 1.0)

    def test_near_duplicate_at_threshold(self):
        # 3 shared shingles of 5 in the union: Jaccard 0.6 exactly.
        text = 'Three clients still use the v1 API. As noted, three clients still use the v1 API.'
        self.assertEqual(len(q.repeated_content(text)), 1)

    def test_below_threshold_is_not_a_repeat(self):
        text = ('The export failed because the row group size changed. '
                'Pinning the row group size fixes the export and keeps memory flat.')
        self.assertEqual(q.repeated_content(text), [])

    def test_case_and_markdown_do_not_hide_a_repeat(self):
        self.assertEqual(len(q.repeated_content('**Deploy the fix tonight.**\n\n- deploy the FIX tonight')), 1)

    def test_repeat_inside_a_quote_or_list_still_counts(self):
        # No line is exempt: quoting or listing a sentence again is still saying it twice.
        self.assertEqual(len(q.repeated_content('Retries stop after five attempts.\n\n> Retries stop after five attempts.')), 1)
        self.assertEqual(len(q.repeated_content('Retries stop after five attempts.\n- Retries stop after five attempts.')), 1)

    def test_short_exact_repeats_are_ignored(self):
        self.assertEqual(q.repeated_content('Yes. No. Yes.'), [])

    def test_repeats_in_code_are_not_prose(self):
        self.assertEqual(q.repeated_content('Run this.\n\n```\nmake test now please ok\nmake test now please ok\n```'), [])

    def test_counts_each_repeating_sentence_once(self):
        text = 'Ship the fix before Friday night. Ship the fix before Friday night. Ship the fix before Friday night.'
        self.assertEqual(len(q.repeated_content(text)), 2)


class Words(unittest.TestCase):
    def test_counts_prose_and_skips_code(self):
        self.assertEqual(q.word_count('Two words.\n\n```\nnot counted at all\n```\n- three more here'), 5)


class IdentifierSubject(unittest.TestCase):
    def assertFlagged(self, sentence):
        self.assertEqual(q.identifier_subjects(sentence), [sentence], sentence)

    def assertClear(self, sentence):
        self.assertEqual(q.identifier_subjects(sentence), [], sentence)

    def test_flags_identifiers_as_subject(self):
        for sentence in ('`PreviewCanvas.ts:18` stretches portrait images.', 'PreviewCanvas.ts:18 stretches them.',
                         'load.py:16 re-raises the error.', '`deliver()` now loops.', 'deliver() now loops.',
                         'row_group_size defaulted to a million.', 'validateRow raises on blank email.',
                         'config/export.yaml never set it.', 'export.yaml never set it.',
                         '**`sync-01`** hosts the file.', '(`notes.md:4`) says so.'):
            self.assertFlagged(sentence)

    def test_list_items_are_sentences(self):
        self.assertEqual(q.identifier_subjects('- `src/cache.py`: changed the TTL.'), ['`src/cache.py`: changed the TTL.'])

    def test_plain_words_and_trailing_citations_pass(self):
        for sentence in ('The preview stretches portrait images (PreviewCanvas.ts:18).',
                         'The `deliver()` function now loops.', 'In `load.py`, the error is re-raised.',
                         'Version 3.0 raised the default.', 'Billing is half done.', 'pdfquill can sign PDFs.',
                         'Northwind Freight sends 40% of traffic.', 'I need your sign-off.', 'Paperforge is AGPL.',
                         '2026-10-31 was the first failed night.'):
            self.assertClear(sentence)

    def test_negated_or_quoted_sentences_are_not_exempt(self):
        self.assertFlagged('`load.py` does not skip blank rows.')
        self.assertEqual(q.identifier_subjects('> `load.py` re-raises the error.'), ['`load.py` re-raises the error.'])


class AskQuestion(unittest.TestCase):
    def test_question_in_first_three_sentences(self):
        self.assertTrue(q.ask_question('Should we delete v1 now? Three clients still use it.'))
        self.assertTrue(q.ask_question('One. Two. **Delete now or wait?**'))

    def test_question_too_late_or_missing(self):
        self.assertFalse(q.ask_question('One. Two. Three. Delete now or wait?'))
        self.assertFalse(q.ask_question('You need to decide whether to delete v1. Three clients use it.'))

    def test_question_mark_inside_a_sentence_is_not_a_question(self):
        self.assertFalse(q.ask_question('The flag `--force?` is odd. Nothing else.'))

    def test_question_in_code_does_not_count(self):
        self.assertFalse(q.ask_question('```\nok?\n```\nOne. Two. Three.'))

    def test_only_case_four_is_graded(self):
        graded = {name for name, case in CASES.items() if 'ask-question' in q.script_grades('A?', case)}
        self.assertEqual(graded, {'4-decision-question'})


class Suite(unittest.TestCase):
    def test_seven_cases_with_keys_prompts_fixtures_and_samples(self):
        self.assertEqual(len(CASES), 7)
        for name, case in CASES.items():
            self.assertEqual(set(case['key']), set(q.ITEMS), name)
            self.assertTrue(case['prompt'], name)
            self.assertTrue(any((case['dir'] / 'fixture').rglob('*')), name)
            for sample in ('good', 'bad'):
                self.assertTrue((case['dir'] / 'calibration' / f'{sample}.md').is_file(), name)

    def test_script_calibration_scores_as_expected(self):
        for name, case in CASES.items():
            for sample in ('good', 'bad'):
                text = (case['dir'] / 'calibration' / f'{sample}.md').read_text()
                for grader, ok, detail in q.calibration_expectations(sample, case, q.script_grades(text, case)):
                    self.assertTrue(ok, f'{name} {sample} {grader}: {detail}')

    def test_good_openings_fit_the_word_cap(self):
        # A good sample must make its point before the cold reader's excerpt is cut.
        for name, case in CASES.items():
            text = (case['dir'] / 'calibration/good.md').read_text()
            self.assertLessEqual(len(q.opening(text).split()), q.OPENING_WORDS, name)
            self.assertTrue(q.opening(text).rstrip().endswith(('.', '?', '!')), name)

    def test_judge_prompts_exist(self):
        for kind in q.SCHEMAS:
            self.assertTrue(q.judge_prompt(kind))

    def test_bad_key_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            case = Path(temp) / 'cases/x'
            (case / 'fixture').mkdir(parents=True)
            (case / 'case.json').write_text('{}')
            (case / 'prompt.md').write_text('p')
            (case / 'key.json').write_text(json.dumps({'claim': 'c', 'ask': ''}))
            with self.assertRaises(q.Failure):
                q.load_cases(temp)


def init(style, model='claude-sonnet-5-5', plugins=(), mcp=()):
    return {'type': 'system', 'subtype': 'init', 'output_style': style, 'model': model, 'plugins': list(plugins),
            'mcp_servers': list(mcp), 'claude_code_version': '2.1.317'}


class StyleProof(unittest.TestCase):
    PLUGIN = {'name': 'writing-for-humans', 'version': '0.3.1', 'path': '/r/plugin', 'source': 'writing-for-humans@inline'}

    def test_each_arm_proves_its_style(self):
        self.assertEqual(q.init_proof(init('default'), 'default', 'claude-sonnet-5-5', '/r/plugin', '0.3.1'), [])
        self.assertEqual(q.init_proof(init('Concise'), 'concise', 'claude-sonnet-5-5', '/r/plugin', '0.3.1'), [])
        self.assertEqual(q.init_proof(init('writing-for-humans:writing-for-humans', plugins=[self.PLUGIN]),
                                      'writing-for-humans', 'claude-sonnet-5-5', '/r/plugin', '0.3.1'), [])

    def test_wrong_style_model_plugin_or_mcp_invalidates(self):
        def problems(record, arm='writing-for-humans'):
            return q.init_proof(record, arm, 'claude-sonnet-5-5', '/r/plugin', '0.3.1')
        self.assertTrue(problems(init('default', plugins=[self.PLUGIN])))
        self.assertTrue(problems(init('writing-for-humans:writing-for-humans', model='claude-opus-5-5',
                                      plugins=[self.PLUGIN])))
        self.assertTrue(problems(init('writing-for-humans:writing-for-humans')))
        self.assertTrue(problems(init('writing-for-humans:writing-for-humans', plugins=[dict(self.PLUGIN, version='0.3.0')])))
        self.assertTrue(problems(init('default', plugins=[self.PLUGIN]), 'default'))
        self.assertTrue(problems(init('Concise', mcp=[{'name': 'x'}]), 'concise'))
        self.assertTrue(problems({}, 'default'))

    def test_preflight_needs_current_marker_not_just_init(self):
        # Claude Code echoes any outputStyle into init, even one that doesn't exist, so init alone is no proof.
        def records(style, listing, cost=0):
            return [init(style), {'type': 'result', 'result': listing, 'total_cost_usd': cost}]
        ok = q.grade_preflight('concise', records('Concise', '- default\n- Concise (current): terse'))
        self.assertTrue(ok['passed'])
        echoed = q.grade_preflight('concise', records('Concise', '- default\n- Concise: terse'))
        self.assertFalse(echoed['passed'])
        paid = q.grade_preflight('default', records('default', '- default (current)', cost=0.01))
        self.assertFalse(paid['passed'])
        wfh = q.grade_preflight('writing-for-humans', records(
            'writing-for-humans:writing-for-humans', '- writing-for-humans:writing-for-humans (current): plain'))
        self.assertTrue(wfh['passed'])


class Commands(unittest.TestCase):
    def test_task_command_isolates_and_caps_every_arm(self):
        case = CASES['1-worker-report']
        for arm, style in q.ARMS.items():
            command = q.task_command(case, arm, 'claude-sonnet-5-5', Path('/r/plugin'), 0.5)
            self.assertEqual(json.loads(command[command.index('--settings') + 1]), {'outputStyle': style})
            for flag in q.ISOLATION:
                self.assertIn(flag, command)
            self.assertEqual(command[command.index('--max-budget-usd') + 1], '0.5000')
            self.assertEqual(command[command.index('--model') + 1], 'claude-sonnet-5-5')
            self.assertEqual(command[command.index('--tools') + 1], 'Read,Glob,Grep,Skill')
            self.assertEqual('--plugin-dir' in command, arm == 'writing-for-humans', arm)

    def test_judge_command_has_no_tools_and_its_own_prompt(self):
        command = q.judge_command('reader', 'msg', 'claude-sonnet-5-5', 0.1)
        self.assertEqual(command[command.index('--tools') + 1], '')
        self.assertEqual(command[command.index('--system-prompt') + 1], q.judge_prompt('reader'))
        self.assertIn('--json-schema', command)
        self.assertIn('--max-budget-usd', command)

    def test_readers_never_see_the_key(self):
        case = CASES['4-decision-question']
        prompts = []

        def fake(kind, prompt, model, budget, cap, path, suite=q.SUITE):
            prompts.append((kind, prompt))
            if kind == 'reader':
                return {'claim': 'c', 'ask': 'a', 'stakes': 's'}, None
            if kind == 'pedantry':
                return {'verdict': 'PASS', 'reason': '', 'evidence': ''}, None
            verdict = {'verdict': 'PASS', 'reason': 'r'}
            return {part: {item: verdict for item in q.ITEMS} for part in ('opening', 'whole')}, None

        text = (case['dir'] / 'calibration/good.md').read_text()
        with mock.patch.object(q, 'run_judge', fake):
            grades, errors = q.judge_output(text, case, 'm', q.Budget(1), 0.1, Path('/nonexistent'))
        self.assertEqual(errors, [])
        self.assertEqual(grades['cold-read-opening']['hits'], 3)
        readers = [p for kind, p in prompts if kind == 'reader']
        self.assertEqual(sorted(readers), sorted([q.reader_prompt(q.opening(text)), q.reader_prompt(text)]))
        for prompt in readers + [p for kind, p in prompts if kind == 'pedantry']:
            self.assertNotIn(case['key']['stakes'], prompt)
        compare = next(p for kind, p in prompts if kind == 'compare')
        self.assertNotIn(text, compare)
        self.assertIn(case['key']['claim'], compare)

    def test_a_failed_judge_leaves_its_grader_unscored(self):
        def fake(kind, *args, **kwargs):
            return (None, 'judge reader failed') if kind == 'reader' else ({'verdict': 'FAIL', 'reason': '', 'evidence': 'x'}, None)
        with mock.patch.object(q, 'run_judge', fake):
            grades, errors = q.judge_output('Text.', CASES['6-factual-answer'], 'm', q.Budget(1), 0.1, Path('/n'))
        self.assertNotIn('cold-read-opening', grades)
        self.assertNotIn('cold-read-whole', grades)
        self.assertFalse(grades['pedantry']['passed'])
        self.assertTrue(errors)


class BudgetAndLedger(unittest.TestCase):
    def test_reservations_never_exceed_the_ceiling(self):
        budget = q.Budget(1.0)
        self.assertEqual(budget.reserve(0.75), 0.75)
        grant = budget.reserve(0.75)
        self.assertAlmostEqual(grant, 0.25)
        self.assertIsNone(budget.reserve(0.75))
        budget.settle(0.75, 0.10)
        self.assertAlmostEqual(budget.reserve(0.75), 0.65)

    def test_ledger_appends_with_running_total(self):
        with tempfile.TemporaryDirectory() as temp:
            ledger = Path(temp) / 'ledger.md'
            ledger.write_text('| time | what | tree | cost USD | cumulative |\n|---|---|---|---|---|\n'
                              '| t | earlier | x | 1.0000 | 1.5000 |\n')
            self.assertAlmostEqual(q.append_ledger(ledger, 'next', 0.25), 1.75)
            self.assertTrue(ledger.read_text().splitlines()[-1].endswith('| 0.2500 | 1.7500 |'))


class Summary(unittest.TestCase):
    def write_result(self, out, arms=('default',), runs=1, drop=(), invalid=(), filtered=False, guard=()):
        cases = {name: CASES[name] for name in ('4-decision-question', '6-factual-answer')}
        (out / 'suite.json').write_text(json.dumps(q.expected_suite(cases, list(arms), runs, filtered)))
        (out / 'preflight.json').write_text(json.dumps([{'arm': arm, 'passed': True} for arm in arms]))
        (out / 'guard.json').write_text(json.dumps({'problems': list(guard)}))
        for arm in arms:
            for name, case in cases.items():
                for n in range(1, runs + 1):
                    if (arm, name, n) in drop:
                        continue
                    directory = out / 'runs' / arm / name / f'run-{n}'
                    directory.mkdir(parents=True)
                    text = (case['dir'] / 'calibration/good.md').read_text()
                    part = {'hits': 3, 'items': {item: True for item in q.ITEMS}}
                    record = {'arm': arm, 'case': name, 'run': n, 'valid': (arm, name, n) not in invalid,
                              'problems': [], 'cost_usd': 0.1, 'duration_seconds': 20.0,
                              'output_style': q.ARMS[arm], 'model': 'claude-sonnet-5-5', 'claude_version': '2.1.317',
                              'script': q.script_grades(text, case),
                              'judges': {'cold-read-opening': part, 'cold-read-whole': part, 'pedantry': {'passed': True}}}
                    (directory / 'record.json').write_text(json.dumps(record))

    def summary(self, **kwargs):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            self.write_result(out, **kwargs)
            return q.summarize(out, write=False)

    def test_complete_result(self):
        summary = self.summary(arms=('default', 'concise'), runs=3)
        self.assertEqual(summary['problems'], [])
        self.assertTrue(summary['baseline'])
        metrics = summary['arms']['default']
        self.assertEqual((metrics['valid_runs'], metrics['opening_hits'], metrics['opening_items']), (6, 18, 18))
        self.assertEqual((metrics['ask_question_passes'], metrics['ask_question_runs']), (3, 3))
        self.assertIn('| default | default | 6 | 18/18 |', q.markdown(summary))

    def test_one_run_is_complete_but_not_a_baseline(self):
        summary = self.summary(runs=1)
        self.assertTrue(summary['complete'])
        self.assertFalse(summary['baseline'])

    def test_missing_invalid_unscored_or_filtered_runs_are_not_complete(self):
        self.assertIn('default 6-factual-answer: 1 valid runs of 2',
                      self.summary(runs=2, drop=[('default', '6-factual-answer', 2)])['problems'])
        summary = self.summary(runs=1, invalid=[('default', '6-factual-answer', 1)])
        self.assertFalse(summary['complete'])
        self.assertIn('default 6-factual-answer: 0 valid runs of 1', summary['problems'])
        self.assertFalse(self.summary(filtered=True)['complete'])
        self.assertFalse(self.summary(guard=['~/.claude/settings.json changed during the run'])['complete'])

    def test_a_missing_grader_is_a_problem(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            self.write_result(out)
            path = out / 'runs/default/6-factual-answer/run-1/record.json'
            record = json.loads(path.read_text())
            del record['judges']['pedantry']
            path.write_text(json.dumps(record))
            problems = q.summarize(out, write=False)['problems']
        self.assertIn('default 6-factual-answer run 1: not graded by pedantry', problems)

    def test_a_missing_preflight_is_a_problem(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            self.write_result(out)
            (out / 'preflight.json').unlink()
            self.assertIn('no preflight.json', q.summarize(out, write=False)['problems'])


if __name__ == '__main__':
    unittest.main()
