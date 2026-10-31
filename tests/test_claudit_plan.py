"""Claudit 4.1: the deterministic plan, grades and footer, test-data paths, reachable procedures and declines.

Each rule is the grammar documented in plugins/claudit/README.md ("Same tree, same result"). The Neighbours
classes enumerate the bypasses and near misses of each rule: path variants, case, symlinks, imports, nested
directories, links the loaded instructions don't make, and repositories with no git.
"""
import json
import os
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_claudit import Project, cl  # noqa: E402

STEPS = ''.join('%d. Step %d\n' % (n, n) for n in range(1, 6))
SETTINGS = {'permissions': {'allow': ['Bash(bin/ci)']}}
GIT_ENV = dict(os.environ, GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)


def finding(fid, grade='coverage', severity='medium', path='.'):
    kind = fid.split(':')[0]
    return {'id': fid, 'grade': grade, 'severity': severity, 'path': path,
            'change': cl.CHANGE_TITLES[kind].format(path=path, subject='p')}


class DataPaths(unittest.TestCase):
    def test_data_directories(self):
        for rel in ('evals/claudit/cases/f6/graders/no-invented.md', 'tests/claudit_gate_reports/f3-run1.md',
                    'test/fixtures/a.md', 'src/__fixtures__/a.md', 'pkg/TestData/a.md', 'pkg/testdata/a.md',
                    'a/Fixtures2/x.md', 'a/.fixtures/x.md', 'a/test-data/x.md', 'a/test_reports/x.md',
                    'a/snapshots/x.md', 'a/__snapshots__/x.md', 'a/golden/x.md', 'a/Goldens/x.md',
                    'a/cassettes/x.md', 'a/results/x.md', 'a/Reports/x.md', 'a/b/c/d/e/fixtures/x.md',
                    'TESTS/x.md', 'a/evalCases/x.md', 'a/gate-reports-2026/x.md', 'Tests/unit/x.md'):
            self.assertTrue(cl.data_path(rel), rel)

    def test_neighbouring_names_are_not_data(self):
        for rel in ('docs/operations/sdlc.md', 'docs/latest/release.md', 'docs/contest/x.md',
                    'docs/attestations/x.md', 'docs/reporting/x.md', 'docs/testing/x.md', 'docs/evaluation/x.md',
                    'reports.md', 'fixtures.md', 'tests.md', 'docs/protest/x.md', 'docs/retest-plan.md'):
            self.assertFalse(cl.data_path(rel), rel)

    def test_a_test_directorys_own_claude_md_is_an_instruction_file(self):
        self.assertFalse(cl.data_path('tests/CLAUDE.md', nested_instruction=True))
        self.assertFalse(cl.data_path('packages/api/tests/CLAUDE.md', nested_instruction=True))
        self.assertTrue(cl.data_path('tests/unit/CLAUDE.md', nested_instruction=True))
        self.assertTrue(cl.data_path('fixtures/CLAUDE.md', nested_instruction=True))
        self.assertTrue(cl.data_path('tests/CLAUDE.md'))

    def test_eval_case_directories(self):
        self.assertTrue(cl.data_path('quality/case-a/steps.md', eval_cases=['quality/case-a']))
        self.assertFalse(cl.data_path('quality/case-ab/steps.md', eval_cases=['quality/case-a']))


class FixtureNoise(Project):
    """Requirement 3: test data is never a procedure, instruction or config."""

    def noise(self):
        self.write('CLAUDE.md', '# x\n\nRun `bin/ci`.\n')
        self.write('bin/ci', '#!/bin/sh\n', 0o755)
        self.write('.claude/settings.json', SETTINGS)
        self.write('evals/suite/cases/deploy/graders/deploy-steps.md', '# Deploy grader\n' + STEPS)
        self.write('evals/suite/cases/deploy/case.yaml', 'name: deploy\n')
        self.write('quality/case-x/case.yaml', 'name: x\n')
        self.write('quality/case-x/release-notes.md', '# Release notes\n' + STEPS)
        self.write('tests/claudit_gate_reports/release-report.md', '# Release report\n' + STEPS)
        self.write('tests/fixtures/sample-repo/CLAUDE.md', '@missing.md\nSee `docs/nope.md`.\n')
        self.write('tests/fixtures/sample-repo/docs/runbook.md', '# Runbook\n' + STEPS)
        self.write('tests/fixtures/sample-repo/.claude-plugin/plugin.json', {'name': 'sample'})
        self.write('tests/fixtures/sample-repo/.env', 'TOKEN=x\n')
        self.write('pkg/testdata/go.mod', 'module x\n')
        self.write('spec/golden/sdlc-snapshot.md', '# SDLC\n' + STEPS)

    def test_no_findings_signals_or_inventory_from_test_data(self):
        self.noise()
        result = self.scan()
        self.assertEqual(self.ids(result), [])
        self.assertEqual(result['signals']['procedure_docs'], [])
        self.assertEqual(result['inventory']['plugins'], [])
        self.assertEqual(result['signals']['typed'], [])
        self.assertEqual(result['signals']['secret_paths'], [])
        self.assertEqual([i['path'] for i in result['inventory']['instructions']], ['CLAUDE.md'])
        self.assertNotIn('delivery/SDLC docs present', result['signals']['agent_run'])
        self.assertEqual(result['plan']['items'], [])

    def test_symlinks_into_test_data_or_out_of_the_project(self):
        self.write('CLAUDE.md', '# x\n')
        self.write('tests/fixtures/run.md', '# Runbook\n' + STEPS)
        os.makedirs(os.path.join(self.root, 'docs'))
        os.symlink('../tests/fixtures/run.md', os.path.join(self.root, 'docs/runbook.md'))
        outside = os.path.join(self.root, '..', os.path.basename(self.root) + '-outside.md')
        with open(outside, 'w') as handle:
            handle.write('# Release\n' + STEPS)
        self.addCleanup(os.unlink, outside)
        os.symlink(outside, os.path.join(self.root, 'docs/release.md'))
        self.write('docs/deploy.md', '# Deploy\n' + STEPS)
        result = self.scan()
        self.assertEqual([d['path'] for d in result['signals']['procedure_docs']], ['docs/deploy.md'])

    def test_real_procedures_next_to_test_data_still_count(self):
        self.noise()
        self.write('docs/release.md', '# Release\n' + STEPS)
        self.write('tests/CLAUDE.md', 'Keep tests small.\n')
        result = self.scan()
        self.assertEqual(self.ids(result), ['procedure-skill:docs/release.md'])
        self.assertIn('tests/CLAUDE.md', [i['path'] for i in result['inventory']['instructions']])


class Reachable(Project):
    """Requirement 2: a procedure doc loaded instructions already link is optional, not a change."""

    def procedure(self, rel='docs/operations/sdlc.md', extra=''):
        self.write(rel, '# Software delivery\n' + STEPS + extra)

    def outcome(self, result, rel='docs/operations/sdlc.md'):
        fid = 'procedure-skill:' + rel
        if fid in self.ids(result):
            return 'change'
        return 'optional' if fid in [o['id'] for o in result['optional']] else 'absent'

    def test_backticked_path_in_agents_md(self):
        self.write('AGENTS.md', '# Rules\n\nFollow `docs/operations/sdlc.md` for delivery.\n')
        self.procedure()
        result = self.scan()
        self.assertEqual(self.outcome(result), 'optional')
        self.assertEqual(result['optional'][0]['reason'], 'AGENTS.md:3 links it from the loaded instructions')
        self.assertEqual(result['plan']['items'], [])
        self.assertNotIn('procedure-skill:docs/operations/sdlc.md', [i for g in result['plan']['items']
                                                                    for i in g['finding_ids']])

    def test_link_forms(self):
        forms = ['[delivery](operations/sdlc.md)', '[delivery](./operations/sdlc.md#steps)',
                 '[delivery](<operations/sdlc.md> "title")', 'See [the steps][s].\n\n[s]: operations/sdlc.md',
                 'Read docs/operations/sdlc.md first.', '[d](../docs/operations/sdlc.md?x=1)',
                 '**`docs/operations/sdlc.md`**']
        for form in forms:
            with self.subTest(form=form):
                shutil.rmtree(self.root)
                os.makedirs(self.root)
                self.write('CLAUDE.md', '@docs/repository.md\n')
                self.write('docs/repository.md', '# Repo\n\n%s\n' % form)
                self.procedure()
                self.assertEqual(self.outcome(self.scan()), 'optional')

    def test_encoded_and_symlinked_targets(self):
        self.write('CLAUDE.md', 'See [it](docs/my%20runbook.md) and [that](docs/alias.md).\n')
        self.procedure('docs/my runbook.md')
        self.procedure('docs/release.md')
        os.symlink('release.md', os.path.join(self.root, 'docs/alias.md'))
        result = self.scan()
        self.assertEqual(self.outcome(result, 'docs/my runbook.md'), 'optional')
        self.assertEqual(self.outcome(result, 'docs/release.md'), 'optional')

    @unittest.skipUnless(os.path.exists(os.path.join(os.path.dirname(cl.__file__), 'CLAUDIT.PY')),
                         'case-sensitive file system')
    def test_case_variant_on_a_case_insensitive_file_system(self):
        self.write('CLAUDE.md', 'Follow `Docs/Operations/SDLC.md`.\n')
        self.procedure()
        self.assertEqual(self.outcome(self.scan()), 'optional')

    def test_links_loaded_instructions_do_not_make_are_changes(self):
        cases = {
            'unloaded AGENTS.md': {'CLAUDE.md': '# x\n', 'AGENTS.md': 'Follow `docs/operations/sdlc.md`.\n'},
            'fenced block': {'CLAUDE.md': '```\ncat docs/operations/sdlc.md\n```\n'},
            'nested CLAUDE.md': {'CLAUDE.md': '# x\n', 'docs/CLAUDE.md': 'See `operations/sdlc.md`.\n'},
            'README only': {'CLAUDE.md': '# x\n', 'README.md': 'See `docs/operations/sdlc.md`.\n'},
            'URL': {'CLAUDE.md': 'See https://github.com/o/r/blob/main/docs/operations/sdlc.md.\n'},
            'absolute path': {'CLAUDE.md': 'See [d](/docs/operations/sdlc.md).\n'},
            'other file': {'CLAUDE.md': 'See `docs/operations/sdlc-old.md`.\n'},
            'two hops': {'CLAUDE.md': 'See `docs/index.md`.\n', 'docs/index.md': 'See `operations/sdlc.md`.\n'},
            'escaping link': {'CLAUDE.md': 'See [d](../../docs/operations/sdlc.md).\n'},
        }
        for name, files in cases.items():
            with self.subTest(name):
                shutil.rmtree(self.root)
                os.makedirs(self.root)
                for rel, text in files.items():
                    self.write(rel, text)
                self.procedure()
                self.assertEqual(self.outcome(self.scan()), 'change')

    def test_on_demand_procedures_are_changes(self):
        self.write('AGENTS.md', 'Follow `docs/operations/sdlc.md`.\nRun `docs/release.md` on demand.\n')
        self.procedure(extra='\nAgents should invoke this as a skill on demand.\n')
        self.procedure('docs/release.md')
        self.procedure('docs/deploy.md', extra='\nStaging is available on demand.\n')
        self.write('CLAUDE.md', '@AGENTS.md\nSee `docs/deploy.md`.\n')
        result = self.scan()
        self.assertEqual(self.outcome(result), 'change')
        self.assertEqual(self.outcome(result, 'docs/release.md'), 'change')
        self.assertEqual(self.outcome(result, 'docs/deploy.md'), 'optional')

    def test_skills_cover_or_own_a_doc(self):
        self.write('CLAUDE.md', '# x\n')
        self.procedure('docs/method.md')
        self.write('plugins/p/skills/run/SKILL.md', 'Read [the method](../../../../docs/method.md).\n')
        self.procedure('docs/review.md')
        self.write('.claude/skills/review/SKILL.md', 'Follow docs/review.md.\n')
        self.procedure('docs/fixture-owned.md')
        self.write('tests/fixtures/skills/x/SKILL.md', 'Follow docs/fixture-owned.md.\n')
        result = self.scan()
        docs = {d['path']: d['has_skill'] for d in result['signals']['procedure_docs']}
        self.assertEqual(docs, {'docs/fixture-owned.md': False, 'docs/review.md': True})


class Declines(Project):
    """Requirement 4: a documented decision against a feature is listed, not recommended, not counted."""

    def must_run(self, extra):
        self.write('CLAUDE.md', '@docs/repository.md\n\nAlways run `bin/ci` before you report a change as done.\n')
        self.write('bin/ci', '#!/bin/sh\n', 0o755)
        self.write('.claude/settings.json', SETTINGS)
        self.write('docs/repository.md', '# Repository\n\n' + extra)

    def declined(self, result):
        return [(d['feature'], d['path'], d['line']) for d in result['declined']]

    def test_wrapped_sentence_declines_hooks(self):
        self.must_run('`scripts/check.sh` remains. Repository\npush hooks and Claude shell-match hooks have been '
                      'retired; clean-checkout\nevidence is the gate.\n')
        result = self.scan()
        self.assertEqual(self.declined(result), [('stop-hook', 'docs/repository.md', 4)])
        self.assertEqual(result['declined'][0]['quote'],
                         'Repository push hooks and Claude shell-match hooks have been retired;')
        self.assertEqual(result['declined'][0]['finding_ids'], ['stop-hook'])
        self.assertNotIn('stop-hook', self.ids(result))
        status = {b['id']: b['status'] for b in result['baseline']}
        self.assertEqual(status['enforced'], 'declined')
        self.assertEqual(result['grades']['coverage']['letter'], 'A')

    def test_deliberate_negation_declines_plugin_evals(self):
        self.must_run('- This plugin is advisory, so it deliberately has no eval campaign.\n'
                      '- Hooks were retired in 2025.\n')
        self.write('.claude-plugin/plugin.json', {'name': 'advisor'})
        self.write('skills/advise/SKILL.md', '---\nname: advise\n---\n')
        self.write('README.md', 'Run `claude plugin validate .` in CI.\n')
        result = self.scan()
        self.assertEqual(self.declined(result), [('stop-hook', 'docs/repository.md', 4),
                                                 ('plugin-eval', 'docs/repository.md', 3)])
        self.assertEqual(self.ids(result), [])
        self.assertEqual(result['plan']['summary'], 'No changes worth making: the scan found no defects or gaps; '
                                                    'declined features are under Declined by the project.')
        self.assertEqual(result['grades']['coverage']['letter'], 'A')

    def test_strong_verbs_either_side(self):
        for text in ('We decided against Claude Code hooks.', 'Claude hooks are dropped here.',
                     'We chose not to add hooks for agents.', 'Stop hooks were removed from the setup.',
                     '> Hooks: retired.'):
            with self.subTest(text):
                shutil.rmtree(self.root)
                os.makedirs(self.root)
                self.must_run(text + '\n')
                self.assertEqual([d[0] for d in self.declined(self.scan())], ['stop-hook'])

    def test_near_misses_are_not_declines(self):
        for text in ('If hooks are retired, update the docs.', 'Hooks will be retired next quarter.',
                     'Hooks were retired and later restored.', 'Hooks have not been retired.',
                     'Should we drop hooks?', 'Git pre-commit hooks were removed.', 'There are no hooks yet.',
                     'Hooks could be removed later.', 'Never use hooks that mutate files without review.',
                     'We removed the old release notes, so hooks run on every change now and the CI script stays.',
                     '```\nHooks were retired.\n```'):
            with self.subTest(text):
                shutil.rmtree(self.root)
                os.makedirs(self.root)
                self.must_run(text + '\n')
                result = self.scan()
                self.assertEqual(self.declined(result), [])
                self.assertIn('stop-hook', self.ids(result))

    def test_only_loaded_linked_or_readme_sources_count(self):
        self.must_run('See [delivery](delivery.md).\n')
        self.write('docs/delivery.md', 'Claude Code hooks were retired.\n')
        self.write('docs/other.md', 'We decided against the allowlist.\n')
        self.write('tests/fixtures/repo/README.md', 'LSP was deliberately dropped.\n')
        self.write('README.md', 'Code intelligence plugins were retired.\n')
        result = self.scan()
        self.assertEqual(self.declined(result), [('stop-hook', 'docs/delivery.md', 1), ('lsp', 'README.md', 1)])


class Neighbours(Project):
    """Near misses found in the bypass pass: personal instructions, other tools, contractions and imports."""

    def test_personal_instructions_neither_link_nor_decline(self):
        self.write('CLAUDE.md', '# x\n\nAlways run `bin/ci` before you finish.\n')
        self.write('bin/ci', '#!/bin/sh\n', 0o755)
        self.write('.claude/settings.json', SETTINGS)
        self.write('CLAUDE.local.md', 'Follow `docs/release.md`. Claude Code hooks were retired. @notes.md\n')
        self.write('notes.md', 'See `docs/deploy.md`.\n')
        self.write('docs/release.md', '# Release\n' + STEPS)
        self.write('docs/deploy.md', '# Deploy\n' + STEPS)
        result = self.scan()
        self.assertEqual(result['declined'], [])
        self.assertEqual(result['optional'], [])
        self.assertEqual(sorted(i for i in self.ids(result) if i != 'stop-hook'),
                         ['procedure-skill:docs/deploy.md', 'procedure-skill:docs/release.md'])

    def test_other_tools_and_contractions_are_not_declines(self):
        self.write('CLAUDE.md', '# x\n\nAlways run `bin/ci` before you finish.\n')
        self.write('bin/ci', '#!/bin/sh\n', 0o755)
        self.write('.claude/settings.json', SETTINGS)
        self.write('README.md', 'Cursor skills were removed. Husky hooks were dropped. Hooks weren\u2019t removed. '
                                "Hooks haven't been retired. Codex evals were abandoned.\n")
        self.write('docs/release.md', '# Release\n' + STEPS)
        result = self.scan()
        self.assertEqual(result['declined'], [])
        self.assertIn('stop-hook', self.ids(result))
        self.write('README.md', 'Cursor and Claude Code hooks were both retired.\n')
        self.assertEqual([d['feature'] for d in self.scan()['declined']], ['stop-hook'])

    def test_an_imported_procedure_is_an_instruction_not_a_procedure(self):
        self.write('CLAUDE.md', '@docs/release.md\n')
        self.write('docs/release.md', '# Release\n' + STEPS)
        result = self.scan()
        self.assertEqual(result['signals']['procedure_docs'], [])
        self.assertEqual(result['optional'], [])


class Plan(unittest.TestCase):
    """Requirement 1: which findings become changes, their order and the plan length."""

    def test_rank_group_and_merge(self):
        findings = [finding('allowlist'), finding('lsp', severity='low'),
                    finding('stale-ref:CLAUDE.md:a', 'correctness', path='CLAUDE.md'),
                    finding('stale-ref:CLAUDE.md:b', 'correctness', path='CLAUDE.md'),
                    finding('stale-ref:AGENTS.md:c', 'correctness', path='AGENTS.md'),
                    finding('oversized:CLAUDE.md', 'alignment', path='CLAUDE.md'),
                    finding('secret-deny', path='.claude/settings.json'),
                    finding('claudeignore', 'correctness', 'high', '.claudeignore')]
        plan = cl.plan_of(findings)
        self.assertEqual([(i['n'], i['title'], i['finding_ids']) for i in plan['items']], [
            (1, 'Replace .claudeignore with deny rules', ['claudeignore', 'secret-deny']),
            (2, 'Fix the stale paths in AGENTS.md', ['stale-ref:AGENTS.md:c']),
            (3, 'Fix the stale paths in CLAUDE.md', ['stale-ref:CLAUDE.md:a', 'stale-ref:CLAUDE.md:b']),
            (4, 'Cut CLAUDE.md to what Claude needs', ['oversized:CLAUDE.md']),
            (5, 'Pre-approve the check commands', ['allowlist']),
            (6, 'Install a code-intelligence plugin', ['lsp'])])
        self.assertEqual(plan['summary'], '6 changes are worth making.')
        self.assertEqual(cl.plan_of(list(reversed(findings))), plan)

    def test_secret_deny_alone_is_its_own_item(self):
        plan = cl.plan_of([finding('secret-deny', path='.claude/settings.json')])
        self.assertEqual([i['title'] for i in plan['items']], ['Deny reads of secret paths'])

    def test_length_cap_and_summaries(self):
        many = [finding('procedure-skill:docs/%d.md' % n, path='docs/%d.md' % n) for n in range(9)]
        plan = cl.plan_of(many)
        self.assertEqual(len(plan['items']), 7)
        self.assertEqual([i['finding_ids'] for i in plan['overflow']], [['procedure-skill:docs/7.md'],
                                                                       ['procedure-skill:docs/8.md']])
        self.assertEqual(plan['summary'], '7 changes are worth making. 2 more are under Also worth knowing.')
        self.assertEqual(cl.plan_of(many[:8])['summary'],
                         '7 changes are worth making. 1 more is under Also worth knowing.')
        self.assertEqual(cl.plan_of(many[:3])['summary'], '3 changes are worth making.')
        self.assertEqual(cl.plan_of(many[:2])['summary'],
                         '2 changes are worth making: the scan found no other defects or gaps.')
        self.assertEqual(cl.plan_of(many[:1], optional=[{}])['summary'],
                         '1 change is worth making: the scan found no other defects or gaps; '
                         'optional items are under Also worth knowing.')
        self.assertEqual(cl.plan_of([])['summary'], 'No changes worth making: the scan found no defects or gaps.')

    def test_every_finding_kind_has_a_title(self):
        with open(cl.__file__, encoding='utf-8') as handle:
            kinds = set(cl.re.findall(r"self\.add\('([a-z-]+)", handle.read()))
        self.assertTrue(kinds)
        self.assertEqual(kinds - set(cl.CHANGE_TITLES), set())


class Grades(unittest.TestCase):
    def letters(self, findings, setup=True):
        return {k: (v['letter'], v['items'], v['more']) for k, v in cl.grades_of(cl.plan_of(findings), setup).items()}

    def test_letters_and_raising_items(self):
        self.assertEqual(self.letters([]), {'correctness': ('A', [], 0), 'alignment': ('A', [], 0),
                                            'coverage': ('A', [], 0)})
        self.assertEqual(self.letters([finding('matcher-ignored:s:Stop', 'correctness', 'low', 's')])['correctness'],
                         ('B', [1], 0))
        self.assertEqual(self.letters([finding('stale-ref:C:x', 'correctness', path='C')])['correctness'],
                         ('C', [1], 0))
        self.assertEqual(self.letters([finding('stale-ref:C:x', 'correctness', path='C'),
                                       finding('write-rule:s:W', 'correctness', path='s')])['correctness'],
                         ('D', [1, 2], 0))
        self.assertEqual(self.letters([finding('invalid-json:s', 'correctness', 'high', 's')])['correctness'],
                         ('F', [1], 0))
        self.assertEqual(self.letters([finding('allowlist'), finding('plugin-eval')])['coverage'], ('C', [1, 2], 0))
        bare = self.letters([finding('no-instructions', severity='high'), finding('allowlist')], setup=False)
        self.assertEqual(bare['coverage'], ('F', [1, 2], 0))
        self.assertEqual(bare['alignment'], ('C', [1], 0))

    def test_merged_item_counts_for_both_grades_and_overflow_is_counted(self):
        letters = self.letters([finding('claudeignore', 'correctness', 'high', '.claudeignore'),
                                finding('secret-deny', path='.claude/settings.json')])
        self.assertEqual(letters['correctness'], ('D', [1], 0))
        self.assertEqual(letters['coverage'], ('B', [1], 0))
        many = [finding('procedure-skill:docs/%d.md' % n, path='docs/%d.md' % n) for n in range(9)]
        self.assertEqual(self.letters(many)['coverage'], ('D', list(range(1, 8)), 2))


class Footer(Project):
    def git(self, *args):
        subprocess.run(['git', '-C', self.root] + list(args), check=True, env=GIT_ENV, capture_output=True)

    def test_not_a_git_repo(self):
        self.write('CLAUDE.md', '# x\n')
        self.assertEqual(self.scan()['footer'], 'Claudit %s; not a git repo' % cl.VERSION)

    @unittest.skipUnless(shutil.which('git'), 'git not installed')
    def test_commit_dirty_and_empty(self):
        self.write('CLAUDE.md', '# x\n')
        self.git('init', '-q')
        self.assertEqual(cl.audited(self.root, True), 'Claudit %s; git repo with no commits' % cl.VERSION)
        self.git('-c', 'user.name=t', '-c', 'user.email=t@example.invalid', 'add', '-A')
        self.git('-c', 'user.name=t', '-c', 'user.email=t@example.invalid', '-c', 'commit.gpgsign=false',
                 'commit', '-q', '-m', 'x')
        sha = subprocess.run(['git', '-C', self.root, 'rev-parse', 'HEAD'], capture_output=True, text=True,
                             env=GIT_ENV).stdout.strip()
        code, result, _ = self.cli('scan', '--root', self.root, '--claude-version', '2.1.312')
        self.assertEqual(code, 0)
        self.assertEqual(result['footer'], 'Claudit %s; audited commit %s' % (cl.VERSION, sha))
        self.write('new.md', 'x\n')
        self.assertEqual(cl.audited(self.root, True),
                         'Claudit %s; audited commit %s plus uncommitted changes' % (cl.VERSION, sha))

    def test_version_matches_the_manifest(self):
        manifest = os.path.join(os.path.dirname(cl.__file__), '..', '..', '..', '.claude-plugin', 'plugin.json')
        with open(manifest) as handle:
            self.assertEqual(json.load(handle)['version'], cl.VERSION)


class SameTreeSameResult(Project):
    def test_repeated_scans_agree(self):
        self.write('CLAUDE.md', '# x\n\nAlways run `bin/ci` before you finish.\nSee `docs/gone.md`.\n')
        self.write('bin/ci', '#!/bin/sh\n', 0o755)
        self.write('docs/release.md', '# Release\n' + STEPS)
        self.write('go.mod', 'module x\n')
        first = self.scan()
        for _ in range(3):
            again = self.scan()
            for key in ('plan', 'grades', 'optional', 'declined', 'footer'):
                self.assertEqual(again[key], first[key], key)
        self.assertEqual([i['title'] for i in first['plan']['items']], [
            'Fix the stale paths in CLAUDE.md', 'Pre-approve the check commands', 'Add a skill for docs/release.md',
            'Enforce the check with a Stop hook', 'Install a code-intelligence plugin'])


if __name__ == '__main__':
    unittest.main()
