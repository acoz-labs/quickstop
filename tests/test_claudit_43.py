"""Claudit 4.3 scan checks (issue #193): stale facts, human gates, opt-in git hooks, the always-loaded table,
subagent-only skills, duplication, declarative lists, scope, per-user dismissals and the `deep` subcommand."""
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
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
        # All of one file's stale facts are one change, and Alignment can't be A while one stands.
        items = [i for i in result['plan']['items'] if i['kind'] == 'stale']
        self.assertEqual([(i['title'], len(i['finding_ids'])) for i in items], [('Fix the stale facts in CLAUDE.md', 4)])
        self.assertEqual(result['grades']['alignment']['letter'], 'B')
        self.assertEqual(result['grades']['alignment']['items'], [items[0]['n']])
        self.assertEqual(result['grades']['correctness']['letter'], 'C')

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
        self.assertEqual(found['change'], 'Ask before merge, deploy and release')
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
        self.assertEqual(found['change'], 'Ask before deploy and release')
        self.assertIn("deploy or release system's own approval", found['fix'])

    def test_no_person_a_question_or_history_is_no_gate(self):
        self.write('CLAUDE.md', '# x\n- Merge when CI is green.\n- Should a human approve each release?\n'
                   '- Releases no longer need a maintainer sign-off.\n')
        self.assertNotIn('gate-ask', self.ids(self.scan()))


class GitHooks(Project):
    def test_opt_in_hooks_get_a_session_start_hook(self):
        self.write('CLAUDE.md', '# x\n')
        self.write('CONTRIBUTING.md', 'Run `git config core.hooksPath .githooks` once after cloning.\n')
        found = self.finding(self.scan(), 'git-hooks')
        self.assertIn('"SessionStart"', found['fix'])
        self.assertIn('git config core.hooksPath .githooks', found['fix'])
        self.write('.pre-commit-config.yaml', 'repos: []\n')
        os.unlink(os.path.join(self.root, 'CONTRIBUTING.md'))
        self.assertIn('command -v pre-commit', self.finding(self.scan(), 'git-hooks')['fix'])

    def test_enabled_or_declined_hooks_are_respected(self):
        self.write('CLAUDE.md', '# x\n')
        self.write('.pre-commit-config.yaml', 'repos: []\n')
        self.write('.claude/settings.json', {'hooks': {'SessionStart': [{'hooks': [
            {'type': 'command', 'command': 'pre-commit install'}]}]}})
        self.assertNotIn('git-hooks', self.ids(self.scan()))
        os.unlink(os.path.join(self.root, '.claude/settings.json'))
        self.write('CLAUDE.md', '# x\nWe retired pre-commit hooks because CI runs the same checks.\n')
        self.assertNotIn('git-hooks', self.ids(self.scan()))


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
        self.assertEqual(found['change'], 'Hide .claude/skills/schema-rules/SKILL.md from the skill listing')
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
    def test_three_copies_are_one_change_with_paraphrases(self):
        self.write('CLAUDE.md', '# x\n\n%s\n' % RULE)
        self.write('docs/contributing.md', '# C\n\n%s\n' % RULE)
        self.write('.claude/agents/migrator.md', '---\nname: migrator\ndescription: M.\n---\n%s\n' % RULE)
        self.write('docs/architecture.md', '# A\n\nHand edits to files in `migrations/` are not allowed; always '
                   'create a new migration with `bin/migrate new`.\n')
        result = self.scan()
        found = self.finding(result, 'duplicate')
        self.assertEqual(result['duplicates'][0]['copies'],
                         ['CLAUDE.md:3', '.claude/agents/migrator.md:5', 'docs/contributing.md:3'])
        self.assertEqual(result['duplicates'][0]['paraphrases'], ['docs/architecture.md:3'])
        self.assertEqual(found['problem'], 'One rule is copied word for word into 3 files, `CLAUDE.md:3`, '
                         '`.claude/agents/migrator.md:5` and `docs/contributing.md:3`: "%s" It is paraphrased in '
                         '`docs/architecture.md:3`.' % RULE)

    def test_two_copies_or_one_symlinked_file_are_not_a_finding(self):
        self.write('AGENTS.md', '# x\n\n%s\n' % RULE)
        os.symlink('AGENTS.md', os.path.join(self.root, 'CLAUDE.md'))
        self.write('docs/contributing.md', '# C\n\n%s\n' % RULE)
        result = self.scan()
        self.assertNotIn('duplicate', self.ids(result))
        self.assertEqual(result['duplicates'][0]['copies'], ['CLAUDE.md:3', 'docs/contributing.md:3'])


class DeclarativeLists(Project):
    def test_principles_are_not_a_procedure(self):
        self.write('CLAUDE.md', '# x\nThe principles in `docs/principles.md` hold for every change.\n')
        self.write('docs/principles.md', '# Design principles\n\n1. The public API is stable.\n'
                   '2. Errors are values; the library never panics.\n3. The standard library is the only dependency.\n'
                   '4. Counting is deterministic.\n5. Reading time is rounded up.\n')
        result = self.scan()
        self.assertEqual(result['signals']['procedure_docs'], [])
        self.assertEqual(result['optional'], [])

    def test_imperative_steps_and_sequence_words_count(self):
        self.write('CLAUDE.md', '# x\n')
        self.write('docs/release.md', '# Release\n1. Bump the version.\n2. **Tag** the commit.\n'
                   '3. The changelog is then published.\n4. Push the tag.\n5. Announce it.\n')
        self.assertEqual([d['path'] for d in self.scan()['signals']['procedure_docs']], ['docs/release.md'])

    def test_translations_and_reference_pages_are_not_procedures(self):
        steps = ''.join('%d. Run step %d.\n' % (n, n) for n in range(1, 6))
        self.write('CLAUDE.md', '# x\n')
        self.write('i18n/de/pages/whats-new.md', '# Neu\n' + steps)
        self.write('docs/reference/cli.md', '# CLI\n' + steps)
        self.assertEqual(self.scan()['signals']['procedure_docs'], [])


class Scope(Project):
    def test_files_above_the_repo_and_symlinks(self):
        repo = os.path.join(self.root, 'repo')
        os.makedirs(repo)
        Path(self.root, 'CLAUDE.md').write_text('# Workspace\nBuild with `bin/legacy-build`.\n')
        Path(self.root, 'AGENTS.md').write_text('# Agents\n')
        Path(repo, 'AGENTS.md').write_text('# tide\n')
        os.symlink('AGENTS.md', os.path.join(repo, 'CLAUDE.md'))
        result = cl.Scan(repo, False, cl.load_catalog(), '2.1.316').run()
        self.assertEqual(result['scope']['above'], ['../CLAUDE.md', '../AGENTS.md'])
        self.assertEqual(result['scope']['lines'], [
            'Outside the repo, not graded: `../CLAUDE.md` and `../AGENTS.md` above the repo; `../CLAUDE.md` loads '
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
        lines = cl.Scan(repo, False, cl.load_catalog(), '2.1.316').run()['scope']['lines']
        self.assertTrue(lines[1].endswith('; import it with `@AGENTS.md` from a `CLAUDE.md` in the repo.'), lines)


class Dismissals(Project):
    def test_per_user_by_default_and_shared_on_request(self):
        self.write('CLAUDE.md', '# x\n')
        self.write('tsconfig.json', '{}')
        data = os.path.join(self.root, 'data')
        before = set(os.listdir(self.root))
        code, out, _ = self.cli('dismiss', '--root', self.root, '--data', data, '--id', 'lsp', '--reason', 'no')
        self.assertEqual(code, 0)
        self.assertTrue(out['path'].startswith('${CLAUDE_PLUGIN_DATA}/dismissed/'))
        self.assertFalse(os.path.exists(os.path.join(self.root, '.claude')))  # nothing written in the project
        self.assertEqual(set(os.listdir(self.root)) - before, {'data'})
        result = cl.Scan(self.root, False, cl.load_catalog(), '2.1.312', data_dir=data).run()
        self.assertEqual([(d['id'], d['stored']) for d in result['dismissed']], [('lsp', out['path'])])
        self.assertEqual(result['footer_lines'], ['Dismissed: 1 (stored in `%s`).' % out['path']])
        self.assertIn('lsp', self.ids(self.scan()))  # another user (no data folder) still sees it
        code, out, _ = self.cli('dismiss', '--shared', '--root', self.root, '--id', 'lsp', '--reason', 'team')
        self.assertEqual(out['path'], '.claude/claudit-dismissed.json')
        self.assertNotIn('lsp', self.ids(self.scan()))

    def test_no_data_folder_and_no_shared_is_an_error(self):
        code, out, _ = self.cli('dismiss', '--root', self.root, '--id', 'lsp', '--reason', 'no',
                                env={'CLAUDE_PLUGIN_DATA': ''})
        self.assertEqual(code, 2)
        self.assertIn('pass --data, or --shared', out['error'])


FAKE_CLAUDE = r'''#!/bin/sh
if [ "$1" = doctor ]; then
  printf 'Claude Code doctor\n\nInvalid settings\n- %s/.claude/settings.json \342\200\272 hooks.Stop: must be an array\n' "$PWD"
  printf '  Suggested fix: x\n\nNo installation issues found.\n'
  exit 0
fi
printf '%s\n' "$@" > "$FAKE_ARGS"
case "$FAKE_MODE" in
  fail) printf 'Not logged in\n' >&2; exit 1 ;;
  *) printf '{"result":"1. A stale line","total_cost_usd":0.2,"is_error":false,"permission_denials":[{"t":1}]}' ;;
esac
'''


class Deep(Project):
    def run_deep(self, mode='ok'):
        bindir = os.path.join(self.root, 'fakebin')
        os.makedirs(bindir)
        Path(bindir, 'claude').write_text(FAKE_CLAUDE)
        os.chmod(os.path.join(bindir, 'claude'), stat.S_IRWXU)
        args, record = os.path.join(self.root, 'args'), os.path.join(self.root, 'record.jsonl')
        code, out, _ = self.cli('deep', '--root', self.root, '--max-budget-usd', '0.4',
                                env={'PATH': bindir + ':/usr/bin:/bin', 'FAKE_ARGS': args, 'FAKE_MODE': mode,
                                     'CLAUDIT_DEEP_RECORD': record})
        return code, out, Path(args).read_text().split('\n') if os.path.exists(args) else [], record

    def test_nested_prompt_audit_is_read_only_and_recorded(self):
        code, out, args, record = self.run_deep()
        self.assertEqual(code, 0)
        self.assertEqual(out['prompt_audit']['status'], 'ran')
        self.assertEqual(out['prompt_audit']['report'], '1. A stale line')
        self.assertEqual((out['prompt_audit']['cost_usd'], out['prompt_audit']['permission_denials']), (0.2, 1))
        self.assertEqual(args[:2], ['-p', '/doctor prompt-audit .'])
        for flag in ('--setting-sources', 'project', '--disallowedTools', 'Edit', 'Write', 'NotebookEdit',
                     'Skill(claudit:claudit)', '--strict-mcp-config', '--no-session-persistence', '--max-budget-usd'):
            self.assertIn(flag, args)
        self.assertEqual(out['claude_doctor']['line'],
                         'claude doctor: 1 invalid setting: ./.claude/settings.json › hooks.Stop: must be an array.')
        self.assertEqual(json.loads(Path(record).read_text())['cost_usd'], 0.2)

    def test_a_failed_nested_run_is_reported_not_raised(self):
        code, out, _, _ = self.run_deep('fail')
        self.assertEqual(code, 0)
        self.assertEqual(out['prompt_audit']['status'], 'could not run: exit 1, Not logged in')
        self.assertEqual(out['prompt_audit']['report'], '')

    def test_no_claude_on_path(self):
        code, out, _ = self.cli('deep', '--root', self.root, env={'PATH': '/usr/bin:/bin'})
        self.assertEqual(code, 0)
        self.assertTrue(out['prompt_audit']['status'].startswith('could not run'))
        self.assertEqual(out['claude_doctor']['status'], 'unavailable')


if __name__ == '__main__':
    unittest.main()
