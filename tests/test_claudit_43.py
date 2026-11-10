"""Claudit scan checks from 4.3 kept in 5 (issues #193, #207): stale facts, human gates, the always-loaded table,
subagent-only skills, verbatim duplication, history lines, scope and per-user dismissals."""
import json
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_claudit import Project, cl  # noqa: E402

RULE = 'Never edit files under `migrations/` by hand; create a new one with `bin/migrate new <name>`.'


class StaleFacts(Project):
    def test_missing_scripts_targets_files_and_dependencies(self):
        self.write('CLAUDE.md', '# x\n\n- `npm run lint` checks style; `npm run build` builds.\n'
                   '- `make docs` writes the docs and `make test` runs the tests.\n'
                   '- `bin/release` tags; `bin/check` checks.\n'
                   '- Labels render through `reportlab`; keep it pinned in `pyproject.toml`.\n'
                   '- HTTP goes through `requests`, a dependency in `pyproject.toml`.\n')
        self.write('package.json', {'scripts': {'lint': 'eslint .'}})
        self.write('Makefile', 'test:\n\tpytest\n')
        self.write('bin/check', '#!/bin/sh\n', 0o755)
        self.write('pyproject.toml', '[project]\nname = "x"\ndependencies = ["requests>=2"]\n')
        result = self.scan()
        stale = sorted(i for i in self.ids(result) if i.startswith(('stale-', 'missing-')))
        self.assertEqual(stale, ['stale-command:CLAUDE.md:bin/release', 'stale-command:CLAUDE.md:make docs',
                                 'stale-command:CLAUDE.md:npm run build', 'stale-dep:CLAUDE.md:reportlab'])
        self.assertEqual(self.finding(result, 'stale-dep:CLAUDE.md:reportlab')['problem'],
                         '`reportlab` is not a declared dependency in `pyproject.toml`; `CLAUDE.md:6` names it.')
        # One finding per stale fact, each on its own real line.
        self.assertEqual([(f['id'], f['line']) for f in result['findings'] if f['id'] in stale],
                         [('stale-command:CLAUDE.md:npm run build', 3), ('stale-command:CLAUDE.md:make docs', 4),
                          ('stale-command:CLAUDE.md:bin/release', 5), ('stale-dep:CLAUDE.md:reportlab', 6)])

    def test_one_sentence_per_missing_path(self):
        self.write('CLAUDE.md', '# x\n- `src/app/carriers/` holds one module per carrier.\n'
                   '- Rates load from `config/rates.toml`.\n')
        result = self.scan()
        self.assertEqual(self.finding(result, 'stale-ref:CLAUDE.md:src/app/carriers/')['problem'],
                         '`src/app/carriers/` does not exist; `CLAUDE.md:2` names it.')

    def test_absent_or_conditional_commands_are_not_stale(self):
        self.write('CLAUDE.md', '# x\n\nRun `bin/ci` (or `bin/container bin/ci` where supported).\n'
                   'This repository provides no `bin/container`, so `bin/ci` runs directly.\n'
                   '`bin/old` was removed; it is gone now.\n')
        self.write('bin/ci', '#!/bin/sh\n', 0o755)
        self.assertEqual([i for i in self.ids(self.scan()) if i.startswith('stale')], [])

    def test_skills_and_subagents_are_checked_too(self):
        self.write('CLAUDE.md', '# x\n')
        self.write('.claude/skills/ship/SKILL.md', '---\nname: ship\ndescription: Ship it.\n---\n'
                   'Run `bin/ship` then read `docs/ship-notes.md`; use the `deployer` subagent.\n')
        self.write('.claude/agents/helper.md', '---\nname: helper\ndescription: Helps.\n---\nUse the `ship` skill.\n')
        ids = self.ids(self.scan())
        self.assertIn('stale-command:.claude/skills/ship/SKILL.md:bin/ship', ids)
        self.assertIn('stale-ref:.claude/skills/ship/SKILL.md:docs/ship-notes.md', ids)
        self.assertIn('missing-name:.claude/skills/ship/SKILL.md:deployer', ids)
        self.assertNotIn('missing-name:.claude/agents/helper.md:ship', ids)  # the ship skill exists

    def test_names_are_not_checked_when_a_plugin_is_enabled(self):
        self.write('CLAUDE.md', '# x\nUse the `frontend-design` skill for pages.\n')
        self.assertIn('missing-name:CLAUDE.md:frontend-design', self.ids(self.scan()))
        self.write('.claude/settings.json', {'enabledPlugins': {'design@market': True}})
        self.assertNotIn('missing-name:CLAUDE.md:frontend-design', self.ids(self.scan()))


class Gates(Project):
    CLAUDE = ('# x\n\n- `bin/deploy staging|production` deploys.\n'
              '- Never merge to main without a human approving the pull request (`gh pr merge`).\n'
              '- Never deploy to production without a human go-ahead.\n'
              '- A release needs a human go-ahead before `bin/release` runs.\n')

    def setUp(self):
        super().setUp()
        for name in ('deploy', 'release'):
            self.write('bin/' + name, '#!/bin/sh\n', 0o755)

    def test_prose_gates_get_exact_ask_rules_and_the_real_gate(self):
        self.write('CLAUDE.md', self.CLAUDE)
        result = self.scan()
        found = self.finding(result, 'gate-ask')
        self.assertEqual((found['path'], found['line']), ('CLAUDE.md', 4))
        self.assertTrue(found['problem'].startswith('`CLAUDE.md:4` says a person must approve merge, but no ask or '
                                                    'deny rule covers `gh pr merge`'), found['problem'])
        self.assertIn(json.dumps({'permissions': {'ask': ['Bash(gh pr merge *)', 'Bash(bin/deploy *)',
                                                          'Bash(bin/release *)']}}), found['fix'])
        self.assertIn('Branch protection on `main`', found['fix'])
        self.assertIn('can be got around', found['fix'])
        self.assertEqual([g['command'] for g in result['gates']], ['gh pr merge', 'bin/deploy', 'bin/release'])

    def test_ask_or_deny_rules_close_the_gate(self):
        self.write('CLAUDE.md', self.CLAUDE)
        self.write('.claude/settings.json', {'permissions': {'ask': ['Bash(gh pr merge:*)', 'Bash(bin/deploy *)'],
                                                             'deny': ['Bash(bin/release)']}})
        self.assertNotIn('gate-ask', self.ids(self.scan()))
        self.write('.claude/settings.json', {'permissions': {'ask': ['Bash(gh pr merge *)'],
                                                             'allow': ['Bash(bin/deploy *)']}})
        found = self.finding(self.scan(), 'gate-ask')
        self.assertNotIn('merge', found['problem'])
        self.assertIn('approve deploy', found['problem'])
        self.assertIn('approve release', found['problem'])
        self.assertIn("deploy or release system's own approval", found['fix'])

    def test_no_person_a_question_or_history_is_no_gate(self):
        self.write('CLAUDE.md', '# x\n- Merge when CI is green.\n- Should a human approve each release?\n'
                   '- Releases no longer need a maintainer sign-off.\n')
        self.assertNotIn('gate-ask', self.ids(self.scan()))


class Context(Project):
    def test_always_loaded_table_counts_words_and_tokens(self):
        self.write('CLAUDE.md', '# x\n\nSee [the guide](docs/guide.md) before you start.\n@docs/arch.md\n')
        self.write('docs/arch.md', 'one two three four\n')
        self.write('docs/guide.md', 'guide words here\n')
        self.write('docs/other.md', 'not linked\n')
        self.write('.claude/skills/a/SKILL.md', '---\nname: a\ndescription: Does a thing.\n---\nBody.\n')
        self.write('.claude/skills/b/SKILL.md', '---\nname: b\ndescription: Hidden.\ndisable-model-invocation: true\n---\n')
        self.write('.claude/agents/r.md', '---\nname: r\ndescription: Reviews code.\n---\nPrompt.\n')
        context = self.scan()['context']
        rows = {r['path']: (r['loads'], r['words']) for r in context['rows']}
        self.assertEqual(rows, {'CLAUDE.md': ('every session', 9),
                                'docs/arch.md': ('every session (imported by `CLAUDE.md`)', 4),
                                '.claude/skills/a/SKILL.md': ('every session (skill listing)', 3),
                                '.claude/agents/r.md': ('every session (subagent list)', 2)})
        self.assertEqual([(r['path'], r['loads']) for r in context['likely_read']],
                         [('docs/guide.md', 'likely read, not loaded')])
        self.assertEqual(context['total']['words'], 18)  # the linked guide isn't loaded
        self.assertIn('| `docs/arch.md` |', context['table'])
        self.assertTrue(context['table'].startswith('| File | What | Loads | Words | Tokens (est.) |'))

    def test_limits_from_the_docs_only(self):
        self.write('CLAUDE.md', '# x\n' + 'word ' * 3000 + '\n')
        # 1,000 + 600 characters: each under the 1,536 cap, together over it.
        self.write('.claude/skills/a/SKILL.md', '---\nname: a\ndescription: %s\nwhen_to_use: %s\n---\n'
                   % ('x' * 1000, 'y' * 600))
        ids = self.ids(self.scan())
        self.assertIn('long-description:.claude/skills/a/SKILL.md', ids)
        self.assertFalse([i for i in ids if i.startswith('oversized')])  # 2 lines, however many words

    def test_subagent_only_skill_is_hidden(self):
        self.write('CLAUDE.md', '# x\nUse the `migrator` subagent for schema changes.\n')
        self.write('.claude/skills/schema-rules/SKILL.md', '---\nname: schema-rules\ndescription: Rules.\n---\n- a\n')
        self.write('.claude/agents/migrator.md', '---\nname: migrator\ndescription: Migrates.\n---\n'
                   'Read `.claude/skills/schema-rules/SKILL.md` first.\n')
        found = self.finding(self.scan(), 'visible-skill:.claude/skills/schema-rules/SKILL.md')
        self.assertIn('disable-model-invocation: true', found['fix'])
        self.assertIn('name: schema-rules', found['fix'])
        self.assertEqual(found['line'], 3)  # the description line, which is what loads
        # Preloaded with skills:, disable-model-invocation would stop the preload: move the rules instead.
        self.write('.claude/agents/migrator.md', '---\nname: migrator\ndescription: Migrates.\nskills:\n'
                   '  - schema-rules\n---\nMigrate.\n')
        self.assertIn("into the `migrator` subagent's prompt",
                      self.finding(self.scan(), 'visible-skill:.claude/skills/schema-rules/SKILL.md')['fix'])

    def test_skills_named_elsewhere_or_already_hidden_are_fine(self):
        self.write('CLAUDE.md', '# x\nRun the `schema-rules` skill before a migration.\n')
        self.write('.claude/skills/schema-rules/SKILL.md', '---\nname: schema-rules\ndescription: Rules.\n---\n')
        self.write('.claude/agents/migrator.md', '---\nname: migrator\ndescription: M.\n---\n'
                   'Read .claude/skills/schema-rules/SKILL.md.\n')
        self.assertFalse([i for i in self.ids(self.scan()) if i.startswith('visible-skill')])
        self.write('CLAUDE.md', '# x\n')
        self.write('.claude/skills/schema-rules/SKILL.md', '---\nname: schema-rules\ndescription: Rules.\n'
                   'disable-model-invocation: true\n---\n')
        self.assertFalse([i for i in self.ids(self.scan()) if i.startswith('visible-skill')])


class Duplicates(Project):
    def test_three_verbatim_copies_are_one_finding_and_paraphrases_are_not_matched(self):
        self.write('CLAUDE.md', '# x\n\n%s\n' % RULE)
        self.write('docs/contributing.md', '# C\n\n%s\n' % RULE)
        self.write('.claude/agents/migrator.md', '---\nname: migrator\ndescription: M.\n---\n%s\n' % RULE)
        self.write('docs/architecture.md', '# A\n\nHand edits to files in `migrations/` are not allowed; always '
                   'create a new migration with `bin/migrate new`.\n')
        result = self.scan()
        found = self.finding(result, 'duplicate')
        self.assertEqual(result['duplicates'][0]['copies'],
                         ['CLAUDE.md:3', '.claude/agents/migrator.md:5', 'docs/contributing.md:3'])
        self.assertNotIn('paraphrases', result['duplicates'][0])
        self.assertEqual(found['problem'], 'One rule is copied word for word into 3 files, `CLAUDE.md:3`, '
                         '`.claude/agents/migrator.md:5` and `docs/contributing.md:3`: "%s"' % RULE)
        self.assertEqual((found['path'], found['line']), ('CLAUDE.md', 3))

    def test_copies_only_in_separate_prompts_are_a_template(self):
        for name in ('a', 'b', 'c'):
            self.write('.claude/agents/%s.md' % name, '---\nname: %s\ndescription: R.\n---\n%s\n' % (name, RULE))
        self.write('CLAUDE.md', '# x\n')
        self.assertNotIn('duplicate', self.ids(self.scan()))
        self.write('docs/contributing.md', '# C\n\n%s\n' % RULE)  # a team doc copy is drift again
        self.assertIn('duplicate', self.ids(self.scan()))

    def test_two_copies_or_one_symlinked_file_are_not_a_finding(self):
        self.write('AGENTS.md', '# x\n\n%s\n' % RULE)
        os.symlink('AGENTS.md', os.path.join(self.root, 'CLAUDE.md'))
        self.write('docs/contributing.md', '# C\n\n%s\n' % RULE)
        result = self.scan()
        self.assertNotIn('duplicate', self.ids(result))
        self.assertEqual(result['duplicates'][0]['copies'], ['CLAUDE.md:3', 'docs/contributing.md:3'])


    def test_script_copies_cite_the_file_line(self):
        sentence = 'Pi links local packages, so keep each verified version checkout available.'
        self.write('CLAUDE.md', '# x\n\n%s\n' % sentence)
        self.write('bin/build', '#!/bin/sh\n' + 'x=1\n' * 20 + 'echo "short" "%s"\n' % sentence)
        self.write('docs/install.md', '# I\n\nCommands change settings only when you run them; no package is '
                   'auto-installed.\n')
        self.write('bin/check', '#!/bin/sh\n# These files change only on install, marketplace or settings changes.\n')
        self.write('docs/more.md', '# M\n\nCommands change settings only when you run them; no package is '
                   'auto-installed.\n')
        result = self.scan()
        copies = [tuple(d['copies']) for d in result['duplicates']]
        self.assertIn(('CLAUDE.md:3', 'bin/build:22'), copies)  # the file's line, not the literal's position
        self.assertIn(('docs/install.md:3', 'docs/more.md:3'), copies)
        self.assertEqual(len(copies), 2)  # bin/check's comment shares words, not the sentence

    def test_generated_output_and_its_generator_are_not_copies(self):
        sentence = 'Only accepted targets receive installation commands in the list below.'
        self.write('CLAUDE.md', '# x\n\nThe [generated catalog](docs/catalog.md) lists the plugins.\n')
        self.write('docs/catalog.md', '# Catalog\n\nGenerated from `catalog.json`; do not edit by hand.\n\n%s\n'
                   % sentence)
        self.write('bin/check-marketplace', "#!/usr/bin/env python3\nOUT = 'docs/catalog.md'\nLINES = ['%s']\n"
                   % sentence)
        self.write('.gitattributes', 'uv.lock linguist-generated=true\n*.svg linguist-generated\n')
        self.write('uv.lock', 'x\n')
        result = self.scan()
        self.assertEqual(cl.Scan(self.root, False, '2.1.312').generated(),
                         {'docs/catalog.md': 'docs/catalog.md:3', 'uv.lock': '.gitattributes:1'})
        self.assertEqual(result['duplicates'], [])  # the generator and its output are one source
        self.write('docs/other.md', '# O\n\n%s\n' % sentence)  # a real copy outside them still counts
        found = self.scan()['duplicates']
        self.assertIn('docs/other.md:3', found[0]['copies'])


class History(Project):
    def history(self):
        """The scan's result and its history lines (path, line, form and the rest) in line order."""
        scan = cl.Scan(self.root, False, '2.1.312')
        result = scan.run()
        return result, sorted(scan.history, key=lambda c: (c['path'], c['line']))

    def stale(self):
        return self.history()[1]

    def test_history_narrative_is_a_finding_that_keeps_the_current_fact(self):
        self.write('CLAUDE.md', '# x\n\n@docs/repository.md\n\nAlways run `bin/ci` before you finish.\n')
        self.write('docs/repository.md', '# R\n\nRun `bin/ci`.\nThe initial compatibility run also passed on '
                   'Python 3.9.6; release evidence\nuses the pinned runtime.\n\nThe wrapper remains. Push hooks '
                   'and Claude shell-match hooks\nhave been retired; clean-checkout evidence is the gate.\n'
                   'On 2026-03-02 the docs moved to `docs/`.\nIn version 2.1 the cache was per user.\n'
                   'Hooks are disabled in CI. Old runs may have failed; rerun them.\n')
        self.write('bin/ci', '#!/bin/sh\n')
        self.write('.claude/settings.json', {'permissions': {'allow': ['Bash(bin/ci)']}})
        result, stale = self.history()
        self.assertEqual([(c['path'], c['line'], c['why']) for c in stale], [
            ('docs/repository.md', 4, 'past run'), ('docs/repository.md', 8, 'retirement'),
            ('docs/repository.md', 9, 'dated'), ('docs/repository.md', 10, 'past version')])
        self.assertEqual(stale[1]['not_a_decline'], 'Hooks')
        history = [f for f in result['findings'] if f['kind'] == 'history']
        self.assertEqual([(f['id'], f['line']) for f in history], [
            ('history:docs/repository.md:4', 4), ('history:docs/repository.md:8', 8),
            ('history:docs/repository.md:9', 9), ('history:docs/repository.md:10', 10)])
        self.assertIn('It reads like a decision against hooks, but no decision record says so', history[1]['problem'])
        self.assertIn('"clean-checkout evidence is the gate"', history[1]['fix'])
        self.assertIn('hooks are retired"', history[1]['fix'])
        self.assertEqual(history[0]['fix'], 'Keep what holds now ("release evidence uses the pinned runtime"); move '
                         '"The initial compatibility run also passed on Python 3.9.6" to a changelog or a decision record.')
        # A history line is never a decision, so it holds nothing back.
        self.assertIn('stop-hook', self.ids(result))
        self.assertEqual(result['respected'], [])

    def test_a_status_line_keeps_its_status(self):
        self.write('CLAUDE.md', '# x\n\nIts first workflow, [Shipshape](workflows/shipshape/README.md), was retired on '
                   '2026-11-05 and is kept for reference only.\n\n## Known mistakes\n\n- Builder scripts delete '
                   'exact paths, never globs. A glob delete once killed a running eval.\n')
        self.write('workflows/shipshape/README.md', '# Shipshape\n')
        history = [f for f in self.scan()['findings'] if f['kind'] == 'history']
        self.assertEqual([f['line'] for f in history], [3])  # the lessons list is no history line
        fix = history[0]['fix']
        self.assertEqual(fix, 'Keep what holds now, in the present tense: "Its first workflow, Shipshape, is retired", '
                         'and "is kept for reference only". Move the date (`on 2026-11-05`) to a changelog or a '
                         'decision record.')
        self.assertNotIn('delete', fix.lower())
        self.assertNotIn('cut the sentence', fix.lower())

    def test_present_tense_text_is_no_history(self):
        # Review round 1: relative clauses, conditions, dates that name a protocol version, and migration guides.
        self.write('CLAUDE.md', '# x\n\n@docs/guide.md\n')
        self.write('docs/guide.md', '# Guide\n\nRun the first check that was added to `bin/ci` before pushing.\n'
                   'The last release that passed CI is tagged latest; deploy from it.\n'
                   'Keep the old version string that was used in `plugin.json` until the release is verified.\n'
                   'Tag the build whose first run passed.\nIf the previous build failed, rerun it.\n'
                   'When the last build failed, CI pages the owner.\nOld runs may have failed; rerun them.\n'
                   '`Client(mcp)` negotiates 2026-07-28 against your v2 server.\n'
                   'A 2026-07-28 server answers them with `-32601`.\n'
                   'Since 2026-07-28 servers were required to answer.\n'
                   'Use the version that was released on 2026-03-02.\nHooks are disabled in CI.\n'
                   )
        self.write('bin/ci', '#!/bin/sh\n')
        self.write('CLAUDE.md', '# x\n\n@docs/guide.md\n')
        self.assertEqual(self.stale(), [])

    REMOVED = '`Server.run_sse` has been removed; use `run_http`.\n'

    def test_only_docs_pages_that_are_history_pages_are_skipped(self):
        # Review round 2: a guide by file name or by its first heading is skipped; a topic word is not a guide.
        pages = {'docs/migration-guide.md': '# Notes', 'docs/whats-new.md': '# News', 'docs/upgrading.md': '# Notes',
                 'docs/deprecations.md': '# Notes', 'docs/breaking-changes.md': '# Notes', 'CHANGELOG.md': '# x',
                 'docs/migration.md': '# Migration Guide: v1 to v2', 'docs/v2.md': '# Upgrading to v2',
                 'docs/new.md': "# What's new in v2",
                 # Not history pages: these keep detection.
                 'docs/migrations.md': '# Writing database migrations', 'docs/releases.md': '# Release procedure',
                 'docs/upgrade.md': '# Upgrade dependencies', 'docs/policy.md': '# Deprecation policy',
                 'docs/later.md': '# Notes\n\n# Migration guide'}
        for rel, title in pages.items():
            self.write(rel, '%s\n\n%s' % (title, self.REMOVED))
        self.write('CLAUDE.md', '# x\n\nSee %s.\n' % ', '.join(sorted(pages)))
        result, stale = self.history()
        self.assertEqual(len(result['context']['likely_read']), len(pages))
        self.assertEqual(sorted(c['path'] for c in stale),
                         ['docs/later.md', 'docs/migrations.md', 'docs/policy.md', 'docs/releases.md',
                          'docs/upgrade.md'])

    def test_instruction_files_skills_subagents_and_imports_are_never_skipped(self):
        retired = 'Repository push hooks have been retired; clean-checkout evidence is the verification gate.\n'
        self.write('CLAUDE.md', '# Acme upgrade service\n\n%s\n@docs/migration-guide.md\n' % retired)
        self.write('docs/migration-guide.md', '# Migration guide: v1 to v2\n\n' + self.REMOVED)  # an @-import
        self.write('AGENTS.md', '# db-migrate\n\n%s\n# Deprecation policy\n' % retired)
        self.write('.claude/skills/upgrade-deps/SKILL.md', '---\nname: upgrade-deps\ndescription: Upgrade.\n---\n'
                   '# Migration guide\n\n' + self.REMOVED)
        self.write('.claude/agents/news.md', "---\nname: news\ndescription: News.\n---\n# What's new\n\n"
                   + self.REMOVED)
        self.write('.claude/commands/upgrading.md', '# Upgrading to v2\n\n' + self.REMOVED)
        found = sorted(c['path'] for c in self.stale())
        self.assertEqual(found, ['.claude/agents/news.md', '.claude/commands/upgrading.md',
                                 '.claude/skills/upgrade-deps/SKILL.md', 'AGENTS.md', 'CLAUDE.md',
                                 'docs/migration-guide.md'])

    def test_history_still_found_beside_relative_clauses(self):
        self.write('CLAUDE.md', '# x\n\nPush hooks, which we used for years, have been retired.\n'
                   'The hooks that we had were retired.\nThe first release ran on Python 3.8, which is gone now.\n')
        self.assertEqual([(c['line'], c['why']) for c in self.stale()],
                         [(3, 'retirement'), (4, 'retirement'), (5, 'past run')])

    def test_admonition_text_is_cited_by_its_own_line(self):
        sentence = 'Read the client secret from the environment or a secret manager, never from source control.'
        self.write('CLAUDE.md', '# x\n')
        self.write('docs/a.md', '# A\n\n!!! tip\n    %s\n' % sentence)
        self.write('docs/b.md', '# B\n\n??? note "Secrets"\n    %s\n' % sentence)
        self.assertEqual(self.scan()['duplicates'][0]['copies'], ['docs/a.md:4', 'docs/b.md:4'])

    def test_a_decision_record_replaces_a_history_line(self):
        self.write('CLAUDE.md', '# x\n\nClaude Code hooks were retired.\nDecisions: [docs/decisions.md](docs/decisions.md).\n')
        self.write('docs/decisions.md', '# Decisions\n\n- Claude Code hooks were retired in favour of CI.\n')
        scan = cl.Scan(self.root, False, '2.1.312')
        scan.run()
        declined = [d for d in scan.declines(scan.instructions()) if not d.get('history')]
        self.assertEqual([(d['path'], d['line']) for d in declined], [('docs/decisions.md', 3)])
        self.assertEqual([(c['path'], c['line']) for c in self.stale()], [('CLAUDE.md', 3)])

    def test_a_decision_record_still_declines_and_tells_no_history(self):
        self.write('CLAUDE.md', '# x\n\nDecisions are in [docs/decisions.md](docs/decisions.md).\n')
        self.write('docs/decisions.md', '# Decisions\n\n- Claude Code hooks were retired in favour of the review '
                   'checklist.\n')
        self.write('CHANGELOG.md', '# Changes\n\nThe old cache was removed in 2025.\n')
        scan = cl.Scan(self.root, False, '2.1.312')
        scan.run()
        self.assertEqual([(d['feature'], d['path'], d['line']) for d in scan.declines(scan.instructions())],
                         [('stop-hook', 'docs/decisions.md', 3)])
        self.assertEqual(self.stale(), [])


class Scope(Project):
    def test_files_above_the_repo_and_symlinks(self):
        repo = os.path.join(self.root, 'repo')
        os.makedirs(repo)
        Path(self.root, 'CLAUDE.md').write_text('# Workspace\nBuild with `bin/legacy-build`.\n')
        Path(self.root, 'AGENTS.md').write_text('# Agents\n')
        Path(repo, 'AGENTS.md').write_text('# tide\n')
        os.symlink('AGENTS.md', os.path.join(repo, 'CLAUDE.md'))
        result = cl.Scan(repo, False, '2.1.316').run()
        self.assertEqual(result['scope']['above'], ['../CLAUDE.md', '../AGENTS.md'])
        self.assertEqual(result['scope']['lines'], [
            'Outside the repo, not checked: `../CLAUDE.md` and `../AGENTS.md` above the repo; `../CLAUDE.md` loads '
            'in every session here.',
            "Because `../CLAUDE.md` above the repo loads, the repo's `AGENTS.md` is not read on its own; here it "
            'still loads because `CLAUDE.md` is a symlink to it.',
            '`CLAUDE.md` is a symlink to `AGENTS.md`; the audit reads `AGENTS.md`.'])
        self.assertFalse([i for i in self.ids(result) if 'legacy' in i])  # the parent's files are never graded
        self.assertEqual([i.get('real') for i in result['inventory']['instructions']], ['AGENTS.md'])

    def test_without_the_link_the_line_says_how_to_load_it(self):
        repo = os.path.join(self.root, 'repo')
        os.makedirs(repo)
        Path(self.root, 'CLAUDE.md').write_text('# Workspace\n')
        Path(repo, 'AGENTS.md').write_text('# tide\n')
        lines = cl.Scan(repo, False, '2.1.316').run()['scope']['lines']
        self.assertTrue(lines[1].endswith('; import it with `@AGENTS.md` from a `CLAUDE.md` in the repo.'), lines)


class Dismissals(Project):
    def test_per_user_by_default_and_shared_on_request(self):
        self.write('CLAUDE.md', '# x\n')
        self.write('go.mod', 'module x\n')
        data = os.path.join(self.root, 'data')
        before = set(os.listdir(self.root))
        code, out, _ = self.cli('dismiss', '--root', self.root, '--data', data, '--id', 'allowlist', '--reason', 'no')
        self.assertEqual(code, 0)
        self.assertTrue(out['path'].startswith('${CLAUDE_PLUGIN_DATA}/dismissed/'))
        self.assertFalse(os.path.exists(os.path.join(self.root, '.claude')))  # nothing written in the project
        self.assertEqual(set(os.listdir(self.root)) - before, {'data'})
        result = cl.Scan(self.root, False, '2.1.312', data_dir=data).run()
        self.assertEqual([(d['id'], d['stored']) for d in result['dismissed']], [('allowlist', out['path'])])
        self.assertTrue(result['footer'][-1].endswith('; 1 dismissed (stored in `%s`)' % out['path']))
        self.assertIn('allowlist', self.ids(self.scan()))  # another user (no data folder) still sees it
        code, out, _ = self.cli('dismiss', '--shared', '--root', self.root, '--id', 'allowlist', '--reason', 'team')
        self.assertEqual(out['path'], '.claude/claudit-dismissed.json')
        self.assertNotIn('allowlist', self.ids(self.scan()))

    def test_no_data_folder_and_no_shared_is_an_error(self):
        code, out, _ = self.cli('dismiss', '--root', self.root, '--id', 'lsp', '--reason', 'no',
                                env={'CLAUDE_PLUGIN_DATA': ''})
        self.assertEqual(code, 2)
        self.assertIn('pass --data, or --shared', out['error'])


class DevSetNarrowings(Project):
    """#207 code round 2: each check narrowed on the dev set (five public repositories, CONDITIONS.md), tested with
    the line that motivated it and a near miss that must still be raised. Removing any narrowing fails its test."""

    def stale(self):
        return sorted(i for i in self.ids(self.scan()) if i.startswith(('stale-', 'missing-')))

    def test_another_repository_or_package(self):
        # next.js AGENTS.md:534 and :536: paths in an installed package or another repository.
        self.write('CLAUDE.md', '# x\n\nRead `docs/README.md` inside that installed package first.\n'
                   'In the Turborepo source repository, its template is in `crates/cli/src/guidance.rs`.\n'
                   'Branch PRs are part of the `acme/widgets` repository and run `bin/ci`.\n')
        self.assertEqual(self.stale(), [])
        # Near misses (review round 2): this repository's own root and package.
        self.write('CLAUDE.md', '# x\n\nRun `bin/old-tool` from the root of the repository.\n'
                   'The parser lives in `src/missing/parser.py` in the main package.\n')
        self.assertEqual(self.stale(), ['stale-command:CLAUDE.md:bin/old-tool', 'stale-ref:CLAUDE.md:src/missing/parser.py'])

    def test_placeholders_are_whole_segments(self):
        # sentry tests/AGENTS.md:11-12 and next.js's `test/path/to/test.ts`.
        self.write('CLAUDE.md', '# x\n\n- Code location: `src/sentry/foo/bar.py`\n- Run `test/path/to/test.ts` style paths.\n')
        self.assertEqual(self.stale(), [])
        self.write('CLAUDE.md', '# x\n\n- The menu is in `src/nav-bar.md` and `src/status_bar.py`.\n')
        self.assertEqual(self.stale(), ['stale-ref:CLAUDE.md:src/nav-bar.md', 'stale-ref:CLAUDE.md:src/status_bar.py'])

    def test_placeholder_calls_get_no_rule(self):
        # sentry `pytest tests/...` and deno `cargo test spec::test_name`; `cargo test specs` is a real call.
        self.write('Cargo.toml', '[package]\nname = "x"\n')
        self.write('CLAUDE.md', '# x\n\n```bash\ncargo test spec::test_name\ncargo test specs\n```\n')
        rules = json.loads(self.finding(self.scan(), 'allowlist')['fix'].split(': ', 1)[1])['permissions']['allow']
        self.assertEqual(rules, ['Bash(cargo test specs)'])

    def test_paths_resolve_from_package_roots(self):
        # next.js AGENTS.md:28 (packages/next/) and anthropic-sdk-python CLAUDE.md:115 (src/anthropic/).
        self.write('packages/next/package.json', {'name': 'next'})
        self.write('packages/next/src/cli/next-dev.ts', '')
        self.write('pyproject.toml', '[project]\nname = "anthropic"\n')
        self.write('src/anthropic/__init__.py', '')
        self.write('src/anthropic/lib/foundry.py', '')
        self.write('crates/ty/resources/mdtest/generics/legacy/a.md', '')
        self.write('CLAUDE.md', '# x\n\n- Dev server: `src/cli/next-dev.ts`.\n- Clients live in `lib/foundry.py`.\n'
                   '- Add cases under `generics/legacy/`.\n')
        self.assertEqual(self.stale(), [])
        # Near miss (review round 2): a file under an unrelated folder doesn't make a missing file present.
        self.write('packages/old/config/settings.toml', '')
        self.write('CLAUDE.md', '# x\n\n- Settings load from `config/settings.toml`.\n')
        self.assertEqual(self.stale(), ['stale-ref:CLAUDE.md:config/settings.toml'])

    def test_conditional_words(self):
        # next.js AGENTS.md:48: "(if exists)".
        self.write('CLAUDE.md', '# x\n\n- `turbopack/README.md` (if exists)\n')
        self.assertEqual(self.stale(), [])
        self.write('CLAUDE.md', '# x\n\n- `turbopack/README.md`\n')
        self.assertEqual(self.stale(), ['stale-ref:CLAUDE.md:turbopack/README.md'])

    def test_modules_of_declared_dependencies(self):
        # next.js AGENTS.md:491: Turbopack resolves `react-dom/server.edge`.
        self.write('package.json', {'name': 'x', 'devDependencies': {'react-dom': '19'}})
        self.write('CLAUDE.md', '# x\n\nTurbopack resolves `react-dom/server.edge` here.\n')
        self.assertEqual(self.stale(), [])
        self.write('CLAUDE.md', '# x\n\nTurbopack resolves `widgets/server.edge` here.\n')
        self.assertEqual(self.stale(), ['stale-ref:CLAUDE.md:widgets/server.edge'])

    def test_github_names_on_repository_lines(self):
        # next.js AGENTS.md:277: "where the merge target is `vercel/next.js`".
        self.write('CLAUDE.md', '# x\n\n- Fork PRs where the merge target is `vercel/next.js` need no description.\n')
        self.assertEqual(self.stale(), [])
        self.write('CLAUDE.md', '# x\n\n- The build entry is `vercel/next.js`.\n')
        self.assertEqual(self.stale(), ['stale-ref:CLAUDE.md:vercel/next.js'])

    def test_situational_runs_are_not_the_routine_check(self):
        # ruff AGENTS.md:63: a run inside a purpose ("To run the `file_watching` binary, ... run `x`") is situational.
        self.write('bin/test', '#!/bin/sh\n', 0o755)
        self.write('CLAUDE.md', '# x\n\nTo check file watching on a machine with real events, run `bin/test --watch`.\n')
        rules = json.loads(self.finding(self.scan(), 'allowlist')['fix'].split(': ', 1)[1])['permissions']['allow']
        self.assertEqual(rules, ['Bash(bin/test)'])  # the script found in bin/, not the situational call
        self.write('CLAUDE.md', '# x\n\nOnly run `bin/test --watch` where file events arrive.\n')
        rules = json.loads(self.finding(self.scan(), 'allowlist')['fix'].split(': ', 1)[1])['permissions']['allow']
        self.assertEqual(rules, ['Bash(bin/test)'])
        # Near miss: the routine call is still suggested as written.
        self.write('CLAUDE.md', '# x\n\nRun `bin/test --watch` before you report a change as done.\n')
        rules = json.loads(self.finding(self.scan(), 'allowlist')['fix'].split(': ', 1)[1])['permissions']['allow']
        self.assertEqual(rules, ['Bash(bin/test --watch)'])

    def test_only_scripts_are_duplicate_sources(self):
        # ruff scripts/*.py.lock: the same comment in every lock file is not a copied rule.
        line = '# requires-python is pinned so the resolver picks the same wheels on every machine we use.\n'
        for name in ('a', 'b', 'c'):
            self.write('scripts/%s.py.lock' % name, line)
        self.write('CLAUDE.md', '# x\n')
        self.assertNotIn('duplicate', self.ids(self.scan()))
        for name in ('a', 'b', 'c'):
            self.write('scripts/%s.py' % name, line)
        self.assertIn('duplicate', self.ids(self.scan()))

    def test_must_run_rules_name_the_end_of_the_work(self):
        # sentry AGENTS.md:11 and next.js AGENTS.md:491: how or when to run a command, not a rule to run it at the end.
        self.write('bin/ci', '#!/bin/sh\n', 0o755)
        self.write('CLAUDE.md', '# x\n\nPython commands MUST run `bin/ci` in the virtualenv.\n'
                   'When updating snapshots, always run `bin/ci` with the CI flags.\n')
        self.assertNotIn('stop-hook', self.ids(self.scan()))
        self.write('CLAUDE.md', '# x\n\nYou must run `bin/ci` before every commit.\n')
        self.assertIn('stop-hook', self.ids(self.scan()))
