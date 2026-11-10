"""Offline checks for the Claudit 5 scan helper against synthetic projects."""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'plugins/claudit/skills/claudit/scripts/claudit.py'

sys.dont_write_bytecode = True  # importing the helper here must not leave the cache the CLI test checks for
spec = importlib.util.spec_from_file_location('claudit_helper', str(SCRIPT))
cl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cl)

GOOD_SETTINGS = {
    'permissions': {
        'allow': ['Bash(npm test:*)', 'Bash(npm run lint)', 'Write', 'Glob'],
        'deny': ['Read(./.env)', 'Read(./.env.*)'],
    },
    'hooks': {
        'Stop': [{'hooks': [{'type': 'command', 'command': '"$CLAUDE_PROJECT_DIR"/.claude/hooks/stop-check.sh'}]}],
        'PostToolUse': [{'matcher': 'Edit|Write', 'hooks': [{'type': 'command', 'command': 'npm run lint'}]}],
    },
    'env': {'API_TOKEN': 'sk-live-supersecret'},
}
GOOD_CLAUDE = """# Shop

Commands:

- `npm test` runs the suite; `npm test -- <file>` runs one file.
- `npm run lint` checks style.

Always run `npm test` before you report a change as done.
Conventions live in @docs/conventions.md and the code in `src/app.js`.
Secrets go in `.env`, never in code. Email ops@example.com or ping @team.
"""


def tree(root):
    root = Path(root)
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file()}


class Project(unittest.TestCase):
    """Builds synthetic projects in a temporary directory."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = os.path.realpath(self._tmp.name)
        # A CLAUDE.md above the system temp directory must not change what these projects load.
        ceiling = mock.patch.object(cl.Scan, 'ceiling', self.root)
        ceiling.start()
        self.addCleanup(ceiling.stop)

    def write(self, rel, content='', mode=None):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not isinstance(content, str):
            content = json.dumps(content, indent=2)
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(content)
        if mode:
            os.chmod(path, mode)

    def well_configured(self):
        self.write('CLAUDE.md', GOOD_CLAUDE)
        self.write('CLAUDE.local.md', '# My notes\n')
        self.write('.gitignore', 'node_modules/\n.env\nCLAUDE.local.md\n')
        self.write('docs/conventions.md', '# Conventions\n\nUse small modules.\n')
        self.write('src/app.js', 'module.exports = {};\n')
        self.write('package.json', {'scripts': {'test': 'node --test', 'lint': 'eslint .'}})
        self.write('.claude/settings.json', GOOD_SETTINGS)
        self.write('.claude/hooks/stop-check.sh', '#!/bin/sh\nnpm test\n', 0o755)
        self.write('.claude/skills/review/SKILL.md', '---\nname: review\ndescription: Review a change.\n---\nSteps.\n')

    def scan(self, version='2.1.312'):
        return cl.Scan(self.root, False, version).run()

    def ids(self, result):
        return [f['id'] for f in result['findings']]

    def finding(self, result, fid):
        matches = [f for f in result['findings'] if f['id'] == fid]
        self.assertEqual(len(matches), 1, (fid, self.ids(result)))
        return matches[0]

    def cli(self, *args, env=None):
        full = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PATH='/usr/bin:/bin')
        full.update(env or {})
        proc = subprocess.run([sys.executable, str(SCRIPT)] + list(args), capture_output=True, text=True,
                              env=full, timeout=60)
        return proc.returncode, json.loads(proc.stdout), proc.stdout


class WellConfigured(Project):
    def test_nothing_found(self):
        self.well_configured()
        result = self.scan()
        self.assertEqual(self.ids(result), [])
        self.assertEqual(result['summary'], 'Nothing found.')
        self.assertEqual(result['root'], '.')
        self.assertIn('Run `/doctor prompt-audit` for contradictions and wording.', result['footer'])
        self.assertIn('Not checked: user and managed settings, settings validity, server-side branch protection.',
                      result['footer'])

    def test_every_finding_has_a_real_line_a_fix_and_a_doc(self):
        self.write('CLAUDE.md', '@missing.md\nSee `docs/gone.md`.\n' + 'x\n' * 210)
        self.write('.claude/settings.json', {'permissions': {'allow': ['Write(src/**)'], 'defaultMode': 'auto'}})
        self.write('go.mod', 'module x\n')
        result = self.scan()
        self.assertEqual(sorted(self.ids(result)), ['allowlist', 'broken-import:CLAUDE.md:missing.md',
                                                    'oversized:CLAUDE.md', 'stale-ref:CLAUDE.md:docs/gone.md'])
        self.assertEqual(result['summary'], '4 findings.')
        sources = [{'url': u, 'heading': h} for u, h in cl.DOCS.values()]
        for f in result['findings']:
            self.assertEqual(set(f), {'id', 'kind', 'path', 'line', 'problem', 'fix', 'source'}, f['id'])
            self.assertIn(f['source'], sources, f['id'])
            lines = Path(self.root, f['path']).read_text().splitlines()
            self.assertLessEqual(f['line'], len(lines), f['id'])
            self.assertTrue(f['problem'] and f['fix'], f['id'])
        self.assertEqual(self.finding(result, 'stale-ref:CLAUDE.md:docs/gone.md')['line'], 2)
        self.assertEqual(self.finding(result, 'allowlist')['path'], 'go.mod')

    def test_removed_checks_never_appear(self):
        """Grades, the plan, skill and feature advice and settings validity are gone in Claudit 5."""
        self.write('CLAUDE.md', '# x\n\nSee [the release](docs/release.md).\n')
        self.write('docs/release.md', '# Release procedure\n\n' + ''.join('%d. Run step %d\n' % (n, n) for n in range(1, 7)))
        self.write('.claudeignore', '.env\n')
        self.write('.env', 'SECRET=1\n')
        self.write('tsconfig.json', '{}')
        self.write('.claude-plugin/plugin.json', {'name': 'p'})
        self.write('.claude/skills/notes.md', 'x\n')
        self.write('.claude/hooks.json', '{}')
        self.write('.claude/settings.json', {'permissions': {'allow': ['Write(src/**)'], 'defaultMode': 'bypassPermissions'},
                                             'hooks': {'PostToolUse': [{'matcher': ['Edit'], 'hooks': []}]},
                                             'mcpServers': {}, 'autoMode': {}})
        result = self.scan()
        gone = ('procedure-skill', 'lsp', 'plugin-validate', 'plugin-eval', 'claudeignore', 'secret-deny', 'flat-skill',
                'hooks-file', 'write-rule', 'default-mode', 'auto-mode', 'mcp-location', 'matcher-type',
                'no-instructions', 'undocumented-checks', 'git-hooks', 'invalid-json', 'wrong-type', 'too-large')
        self.assertFalse([i for i in self.ids(result) if i.split(':')[0] in gone], self.ids(result))
        for key in ('grades', 'plan', 'baseline', 'profiles', 'signals', 'optional', 'declined', 'handoffs',
                    'catalog_version', 'stale_candidates'):
            self.assertNotIn(key, result)


class Correctness(Project):
    def test_symlinked_claude_md_is_audited_once(self):
        self.write('AGENTS.md', '# x\n\nSee `docs/missing.md`.\n@gone.md\n')
        os.symlink('AGENTS.md', os.path.join(self.root, 'CLAUDE.md'))
        result = self.scan()
        self.assertEqual([i['path'] for i in result['inventory']['instructions']], ['CLAUDE.md'])
        self.assertEqual(sorted(self.ids(result)),
                         ['broken-import:CLAUDE.md:gone.md', 'stale-ref:CLAUDE.md:docs/missing.md'])

    def test_fixture_instruction_files_are_not_audited(self):
        self.write('CLAUDE.md', '# x\n')
        self.write('tests/fixtures/broken/CLAUDE.md', '@missing.md\n')
        self.write('pkg/CLAUDE.md', '# nested\n')
        paths = [i['path'] for i in self.scan()['inventory']['instructions']]
        self.assertEqual(paths, ['CLAUDE.md', 'pkg/CLAUDE.md'])

    def test_skill_named_like_a_build_dir_is_walked(self):
        self.write('.claude/skills/build/helper.sh', 'echo\n')
        self.write('.claude/skills/dist/SKILL.md', '---\nname: dist\ndescription: d\n---\n')
        self.write('.claude/skills/dist/node_modules/x/SKILL.md', '')
        dirs = cl.Scan(self.root, False, 'unknown').dirs
        self.assertIn('.claude/skills/build', dirs)
        self.assertNotIn('.claude/skills/dist/node_modules', dirs)

    def test_dependency_dirs_under_skills_are_still_pruned(self):
        self.write('skills/node_modules/dep/CLAUDE.md', '@missing.md\n')
        self.write('skills/vendor/CLAUDE.md', '@missing.md\n')
        self.write('skills/.git/CLAUDE.md', '@missing.md\n')
        self.write('skills/coverage/SKILL.md', '---\nname: coverage\ndescription: d\n---\n')
        scan = cl.Scan(self.root, False, 'unknown')
        self.assertEqual({d for d in scan.dirs if d.startswith('skills/')}, {'skills/coverage'})
        self.assertFalse([i for i in self.ids(self.scan()) if i.startswith('broken-import')])

    def test_oversized_instructions(self):
        self.write('CLAUDE.md', '# x\n' + 'line\n' * 205)
        self.write('AGENTS.md', 'a\n' * 300)
        ids = self.ids(self.scan())
        self.assertIn('oversized:CLAUDE.md', ids)
        self.assertNotIn('oversized:AGENTS.md', ids)
        self.write('CLAUDE.md', '@AGENTS.md\n')
        result = self.scan()
        finding = self.finding(result, 'oversized:AGENTS.md')
        self.assertEqual((finding['line'], finding['source']['heading']), (1, 'Write effective instructions'))
        self.assertIn('300 lines', finding['problem'])

    def test_imports(self):
        self.write('docs/real.md', '# real\n@../missing-nested.md\n')
        self.write('node_modules/@scope/pkg/index.js', '')
        self.write('CLAUDE.md', '\n'.join([
            '@docs/real.md', 'See @docs/gone.md for more.', 'Mail team@example.com.', 'Use @types/node and @acme/ui.',
            'Inline `@docs/inline.md` is code.', '```', '@docs/fenced.md', '```', 'Ping @alice.', '']))
        result = self.scan()
        broken = sorted(i for i in self.ids(result) if i.startswith('broken-import'))
        self.assertEqual(broken, ['broken-import:CLAUDE.md:docs/gone.md', 'broken-import:docs/real.md:../missing-nested.md'])
        self.assertEqual(self.finding(result, broken[0])['line'], 2)

    def test_imports_are_followed_and_loaded(self):
        self.write('bin/ci', '', 0o755)
        self.write('CLAUDE.md', '@AGENTS.md\n@docs/a.md\n')
        self.write('AGENTS.md', 'one\ntwo\n')
        chain = ['docs/a.md', 'docs/b.md', 'docs/c.md', 'docs/d.md', 'docs/e.md', 'docs/f.md']
        for i, rel in enumerate(chain):
            nxt = '@%s\n' % os.path.basename(chain[i + 1]) if i + 1 < len(chain) else ''
            self.write(rel, nxt + '@a.md\n')
        self.write('docs/e.md', 'Always run `bin/ci` before you report done.\nSee `docs/old/gone.md`.\n@f.md\n')
        result = self.scan()
        inst = {i['path']: (i['kind'], i['loaded']) for i in result['inventory']['instructions']}
        self.assertEqual(inst['docs/e.md'], ('import', True))
        self.assertNotIn('docs/f.md', inst)  # sixth hop: past the five-hop import limit
        self.assertEqual(result['inventory']['instruction_words_loaded'], 2 + 2 + 2 * 4 + 10)  # words, not lines
        self.assertEqual([r['path'] for r in result['inventory']['must_rules']], ['docs/e.md'])
        self.assertIn('stale-ref:docs/e.md:docs/old/gone.md', self.ids(result))
        self.assertEqual([c['command'] for c in result['inventory']['check_commands'] if c['documented']], ['bin/ci'])

    def test_unloaded_agents_md_imports_are_not_loaded(self):
        self.write('CLAUDE.md', '# x\n')
        self.write('AGENTS.md', '@docs/agent.md\n')
        self.write('docs/agent.md', 'a\nb\n')
        result = self.scan()
        inst = {i['path']: i['loaded'] for i in result['inventory']['instructions']}
        self.assertEqual(inst, {'CLAUDE.md': True, 'AGENTS.md': False, 'docs/agent.md': False})
        self.assertEqual(result['inventory']['instruction_words_loaded'], 2)

    def loading(self, version='2.1.312'):
        result = self.scan(version)
        return ({i['path']: i['loaded'] for i in result['inventory']['instructions']},
                result['inventory']['instruction_loading'], [i for i in self.ids(result) if i.startswith('agents-md')])

    def test_agents_md_only_loads(self):
        self.write('AGENTS.md', '# Agents\n')
        loaded, sentence, findings = self.loading()
        self.assertEqual(loaded, {'AGENTS.md': True})
        self.assertTrue(sentence.startswith('Loaded at session start: AGENTS.md (read directly: no CLAUDE.md, '
                                            '.claude/CLAUDE.md or CLAUDE.local.md;'), sentence)
        self.assertNotIn('Not loaded', sentence)
        self.assertEqual(findings, [])
        self.write('.claude/AGENTS.md', '# More\n')
        self.assertEqual(self.loading()[0], {'AGENTS.md': True, '.claude/AGENTS.md': True})

    def test_claude_md_only_loads(self):
        self.write('CLAUDE.md', '# Claude\n')
        loaded, sentence, findings = self.loading()
        self.assertEqual(loaded, {'CLAUDE.md': True})
        self.assertEqual(sentence, 'Loaded at session start: CLAUDE.md. This is the default Project instructions '
                                   'setting; a user-level setting can change it.')
        self.assertEqual(findings, [])

    def test_both_load_only_through_an_import(self):
        self.write('CLAUDE.md', '# Claude\n')
        self.write('AGENTS.md', '# Agents\n')
        loaded, sentence, findings = self.loading()
        self.assertEqual(loaded, {'CLAUDE.md': True, 'AGENTS.md': False})
        self.assertIn("Not loaded: AGENTS.md (CLAUDE.md exists and doesn't import it).", sentence)
        self.assertEqual(findings, ['agents-md-not-loaded:AGENTS.md'])
        self.assertIn('Add "@AGENTS.md" to CLAUDE.md', self.finding(self.scan(), findings[0])['fix'])
        self.write('CLAUDE.md', '# Claude\n@AGENTS.md\n')
        loaded, sentence, findings = self.loading()
        self.assertEqual(loaded, {'CLAUDE.md': True, 'AGENTS.md': True})
        self.assertIn('AGENTS.md (imported by CLAUDE.md)', sentence)
        self.assertEqual(findings, [])

    def test_local_or_dot_claude_instructions_also_stop_agents_md(self):
        self.write('AGENTS.md', '# Agents\n')
        for rel in ('CLAUDE.local.md', '.claude/CLAUDE.md'):
            with self.subTest(rel=rel):
                self.write(rel, '# Mine\n')
                loaded, sentence, findings = self.loading()
                self.assertFalse(loaded['AGENTS.md'])
                self.assertEqual(findings, ['agents-md-not-loaded:AGENTS.md'])
                os.remove(os.path.join(self.root, rel))
        self.write('.claude/CLAUDE.md', '@../AGENTS.md\n')
        self.assertTrue(self.loading()[0]['AGENTS.md'])

    def test_claude_md_above_the_project_stops_agents_md(self):
        self.write('repo/AGENTS.md', '# Agents\n')
        self.write('repo/.claude/settings.json', {})
        for rel in ('CLAUDE.md', '.claude/CLAUDE.md', 'CLAUDE.local.md'):
            with self.subTest(rel=rel):
                self.write(rel, '# Above\n')
                result = cl.Scan(os.path.join(self.root, 'repo'), False, '2.1.312').run()
                above = os.path.join(self.root, rel)
                self.assertEqual({i['path']: i['loaded'] for i in result['inventory']['instructions']}, {'AGENTS.md': False})
                self.assertIn("Not loaded: AGENTS.md (%s exists and doesn't import it)." % above,
                              result['inventory']['instruction_loading'])
                fix = self.finding(result, 'agents-md-not-loaded:AGENTS.md')['fix']
                self.assertEqual(fix, 'Create CLAUDE.md in the project containing "@AGENTS.md"; %s above the project '
                                      'otherwise keeps it from loading.' % above)
                os.remove(above)
        self.write('CLAUDE.md', '# Above\n')
        cl.Scan.ceiling = os.path.join(self.root, 'repo')  # nothing above the ceiling is checked
        result = cl.Scan(os.path.join(self.root, 'repo'), False, '2.1.312').run()
        self.assertEqual({i['path']: i['loaded'] for i in result['inventory']['instructions']}, {'AGENTS.md': True})

    def test_directly_read_agents_md_carries_the_session_caveats(self):
        self.write('AGENTS.md', '# Agents\n')
        sentence = self.loading()[1]
        for caveat in ('user-level setting', 'disabled built-in AGENTS.md plugin', 'first session after upgrading',
                       '2.1.277 to 2.1.280 on Amazon Bedrock or with telemetry off'):
            self.assertIn(caveat, sentence)

    def test_old_claude_code_reads_agents_md_only_through_an_import(self):
        self.write('AGENTS.md', '# Agents\n')
        loaded, sentence, findings = self.loading('2.1.276')
        self.assertEqual(loaded, {'AGENTS.md': False})
        self.assertIn('Loaded at session start: none. Not loaded: AGENTS.md (Claude Code 2.1.276', sentence)
        self.assertIn('2.1.277 or later', self.finding(self.scan('2.1.276'), findings[0])['fix'])
        self.assertEqual(self.loading('2.1.277')[0], {'AGENTS.md': True})
        self.assertEqual(self.loading('unknown')[0], {'AGENTS.md': True})

    def test_no_instruction_file_loads_nothing(self):
        self.assertEqual(self.loading()[:2], ({}, 'No project instruction file exists, so none loads.'))

    def test_stale_references(self):
        self.write('docs/present.md', '# p\n')
        self.write('pkg/README.md', 'See `notes/local.md` and ../docs/present.md.\n')
        self.write('pkg/notes/local.md', '')
        self.write('CLAUDE.md', '\n'.join([
            'Architecture: `docs/architecture.md`; existing docs/present.md.',
            'Bare src/old/thing.py and dir lib/gone/ are stale.',
            'Not paths: https://example.com/a/b.md, `src/**/*.ts`, `<dir>/file.md`, {a}/b.md, ~/x/y.md,',
            '$HOME/a.md, .env, `src/`, ./money.js, owner/repo@v1, dist/out.js, e.g. code.claude.com/docs/x.md',
            '```', 'fenced/never.md', '```', '']))
        stale = sorted(i for i in self.ids(self.scan()) if i.startswith('stale-ref'))
        self.assertEqual(stale, ['stale-ref:CLAUDE.md:docs/architecture.md', 'stale-ref:CLAUDE.md:lib/gone/',
                                 'stale-ref:CLAUDE.md:src/old/thing.py'])

class RuleMatching(unittest.TestCase):
    def test_bash_rule_semantics(self):
        m = cl.bash_rule_matches
        self.assertTrue(m('Bash(npm test)', 'npm test'))
        self.assertFalse(m('Bash(npm test)', 'npm test -- a.js'))
        for rule in ('Bash(npm test:*)', 'Bash(npm test *)', 'Bash(npm test*)'):
            self.assertTrue(m(rule, 'npm test'), rule)
            self.assertTrue(m(rule, 'npm test -- a.js'), rule)
        self.assertFalse(m('Bash(npm test *)', 'npm testing'))
        self.assertFalse(m('Bash(npm run lint:*)', 'npm test'))
        self.assertTrue(m('Bash', 'rm -rf x'))
        self.assertTrue(m('Bash(*)', 'anything'))
        self.assertTrue(m('Bash(./bin/ci)', 'bin/ci'))
        self.assertTrue(m('Bash(bin/ci)', './bin/ci'))
        self.assertFalse(m('Read(bin/ci)', 'bin/ci'))

    def test_read_deny_semantics(self):
        m = cl.read_pattern_matches
        self.assertTrue(m('./.env', '.env'))
        self.assertFalse(m('./.env', 'app/.env'))
        self.assertTrue(m('.env', 'app/.env'))
        self.assertTrue(m('**/.env', 'app/.env'))
        self.assertTrue(m('./.env*', '.env.local'))
        self.assertTrue(m('./secrets/**', 'secrets/x'))
        self.assertTrue(m('**/*.pem', 'keys/a.pem'))
        self.assertFalse(m('./.env', '.env.local'))


class Coverage(Project):
    def test_check_detection(self):
        self.write('CLAUDE.md', '# x\n')
        self.write('bin/ci', '#!/bin/sh\n', 0o755)
        self.write('bin/deploy', '#!/bin/sh\n')
        self.write('scripts/test.sh', '', 0o755)
        self.write('scripts/lint.js', 'console.log(1)\n')  # not executable: run via node, not a command
        self.write('Makefile', 'lint:\n\techo\nbuild:\n\techo\nX := 1\n')
        self.write('pnpm-lock.yaml', '')
        self.write('package.json', {'scripts': {'test': 'echo "Error: no test specified" && exit 1', 'typecheck': 'tsc'}})
        self.write('Cargo.toml', '')
        self.write('pyproject.toml', '[tool.pytest.ini_options]\n')
        result = self.scan()
        commands = [c['command'] for c in result['inventory']['check_commands']]
        self.assertEqual(commands, ['bin/ci', 'scripts/test.sh', 'make lint', 'pnpm run typecheck', 'cargo test', 'pytest'])
        self.assertNotIn('undocumented-checks', self.ids(result))
        allowlist = self.finding(result, 'allowlist')
        self.assertEqual((allowlist['path'], allowlist['line']), ('bin/ci', 1))  # named nowhere: cited where it lives

    def test_python_runner_keeps_its_wrapper(self):
        self.write('pyproject.toml', '[tool.pytest.ini_options]\n')
        self.write('AGENTS.md', '- Cross-version: `uv run --frozen --python 3.11 pytest ...`\n'
                                '- Coverage: `uv run --frozen coverage run -m pytest tests/x.py`\n'
                                '- Framework: `uv run --frozen pytest`\n')
        self.write('.github/workflows/ci.yml', 'jobs:\n  t:\n    steps:\n      - name: Run pytest\n')
        result = self.scan()
        self.assertEqual([c['command'] for c in result['inventory']['check_commands']], ['uv run --frozen pytest'])
        allowlist = self.finding(result, 'allowlist')
        self.assertEqual((allowlist['path'], allowlist['line']), ('AGENTS.md', 3))
        self.assertIn('Bash(uv run --frozen pytest)', allowlist['fix'])

    def test_python_prefers_mentioned_command(self):
        self.write('tests/test_x.py', '')
        self.write('CLAUDE.md', 'Run `python3 -m unittest discover -s tests` to check.\n')
        checks = self.scan()['inventory']['check_commands']
        self.assertEqual([(c['command'], c['args'], c['documented']) for c in checks],
                         [('python3 -m unittest', True, True)])

    def test_executable_scripts_in_loaded_instructions(self):
        self.write('bin/sdlc', '#!/bin/sh\n', 0o755)
        self.write('bin/release', '#!/bin/sh\n', 0o755)
        self.write('bin/notes', 'plain file\n')
        self.write('CLAUDE.md', '@docs/guide.md\n')
        self.write('docs/guide.md', 'Run `bin/sdlc check` and read `bin/notes`.\n')
        self.write('bin/audit', '#!/bin/sh\n', 0o755)
        self.write('AGENTS.md', 'Run `bin/release now` and `bin/audit`.\n')
        result = self.scan()
        checks = [(c['command'], c['args']) for c in result['inventory']['check_commands']]
        self.assertEqual(checks, [('bin/sdlc', True)])
        fix = self.finding(result, 'allowlist')['fix']
        self.assertEqual(json.loads(fix.split(': ', 1)[1]), {'permissions': {'allow': ['Bash(bin/sdlc check)']}})
        self.write('CLAUDE.md', '@docs/guide.md\n@AGENTS.md\n')
        checks = [c['command'] for c in self.scan()['inventory']['check_commands']]
        # Neither a release script nor one whose documented call names no check (it may run anything).
        self.assertEqual(checks, ['bin/sdlc'])

    def test_mentioned_scripts_get_exact_non_mutating_rules(self):
        for name in ('sdlc', 'release', 'check-marketplace'):
            self.write('bin/' + name, '#!/bin/sh\n', 0o755)
        self.write('CLAUDE.md', 'Run `bin/sdlc check`, then `bin/sdlc apply` and `bin/release promote`.\n'
                                'Compare with `bin/sdlc check BASE`.\n'
                                'Also run `bin/check-marketplace --base origin/main` and `bin/check-marketplace --write`.\n')
        result = self.scan()
        rules = json.loads(self.finding(result, 'allowlist')['fix'].split(': ', 1)[1])['permissions']['allow']
        self.assertEqual(rules, ['Bash(bin/sdlc check)', 'Bash(bin/check-marketplace --base origin/main)'])
        self.assertFalse([r for r in rules if '*' in r or 'apply' in r or 'promote' in r or 'write' in r], rules)
        self.assertNotIn('bin/release', [c['command'] for c in result['inventory']['check_commands']])
        self.write('.claude/settings.json', {'permissions': {'allow': [
            'Bash(bin/sdlc check)', 'Bash(bin/check-marketplace --base origin/main)']}})
        result = self.scan()
        self.assertNotIn('allowlist', self.ids(result))

    def test_check_script_with_mutating_flag_gets_no_wildcard(self):
        self.write('bin/ci', '#!/bin/sh\n', 0o755)
        self.write('CLAUDE.md', 'Run `bin/ci` or `bin/ci --fast`; `bin/ci --write` updates snapshots.\n')
        rules = json.loads(self.finding(self.scan(), 'allowlist')['fix'].split(': ', 1)[1])['permissions']['allow']
        self.assertEqual(rules, ['Bash(bin/ci)', 'Bash(bin/ci --fast)'])

    def test_documented_script_arguments_get_exact_rules(self):
        self.write('bin/ci', '#!/bin/sh\n', 0o755)
        self.write('CLAUDE.md', 'Run `bin/ci` or `bin/ci --fix` to rewrite files.\n')
        rules = json.loads(self.finding(self.scan(), 'allowlist')['fix'].split(': ', 1)[1])['permissions']['allow']
        self.assertEqual(rules, ['Bash(bin/ci)'])
        self.write('CLAUDE.md', 'Run `bin/ci --fast`; `bin/ci deploy` and `bin/ci --push` ship it.\n')
        rules = json.loads(self.finding(self.scan(), 'allowlist')['fix'].split(': ', 1)[1])['permissions']['allow']
        self.assertEqual(rules, ['Bash(bin/ci)', 'Bash(bin/ci --fast)'])

    def test_tool_commands_get_exact_non_mutating_rules(self):
        self.write('Makefile', 'test:\n\techo test\ndeploy:\n\techo deploy\n')
        self.write('package.json', {'scripts': {'lint': 'eslint .', 'lint:fix': 'eslint --fix .',
                                                'test:deploy': 'deploy'}})
        self.write('CLAUDE.md', 'Run `make test V=1`, `npm run lint`, `npm run lint:fix` and `npm run test:deploy`.\n')
        rules = json.loads(self.finding(self.scan(), 'allowlist')['fix'].split(': ', 1)[1])['permissions']['allow']
        # A wildcard would allow `make test deploy`; mutating scripts are never suggested.
        self.assertEqual(sorted(rules), ['Bash(make test V=1)', 'Bash(make test)', 'Bash(npm run lint)'])

    def test_mutating_words_ignore_path_arguments(self):
        self.write('bin/test', '#!/bin/sh\n', 0o755)
        self.write('CLAUDE.md', 'Run `bin/test tests/fix_parser.py`.\n')
        rules = json.loads(self.finding(self.scan(), 'allowlist')['fix'].split(': ', 1)[1])['permissions']['allow']
        self.assertEqual(rules, ['Bash(bin/test)', 'Bash(bin/test tests/fix_parser.py)'])
        self.assertTrue(cl.mutating('bin/fix-all') and cl.mutating('npm run lint:fix'))
        self.assertTrue(cl.mutating('bin/lint --fix=src/') and cl.mutating('make test "deploy"'))
        for call in ('bin/test --mode=publish', 'bin/sdlc check --mode=apply', 'make test --file=release.mk',
                     'bin/db migrate'):
            self.assertTrue(cl.mutating(call), call)
        self.assertFalse(cl.mutating('bin/test --shard=1/2') or cl.mutating('bin/test --mode=fast'))

    def test_mutating_flag_values_are_not_suggested(self):
        self.write('bin/sdlc', '#!/bin/sh\n', 0o755)
        self.write('bin/test', '#!/bin/sh\n', 0o755)
        self.write('CLAUDE.md', 'Always run `bin/sdlc check --mode=apply` before you finish.\n'
                                'Run `bin/test --mode=publish` or `bin/test --mode=fast`.\n')
        result = self.scan()
        rules = json.loads(self.finding(result, 'allowlist')['fix'].split(': ', 1)[1])['permissions']['allow']
        self.assertEqual(rules, ['Bash(bin/test)', 'Bash(bin/test --mode=fast)'])
        hook = self.finding(result, 'stop-hook')['fix']
        self.assertNotIn('apply', hook)
        self.assertNotIn('publish', hook)

    def test_script_names_with_spaces_are_not_check_commands(self):
        self.write('bin/test.a b', '#!/bin/sh\n', 0o755)
        self.write('bin/ci', '#!/bin/sh\n', 0o755)
        self.assertEqual([c['command'] for c in self.scan()['inventory']['check_commands']], ['bin/ci'])

    def test_suggested_calls_are_plain(self):
        self.write('bin/test', '#!/bin/sh\n', 0o755)
        self.write('CLAUDE.md', '```sh\nbin/test check `touch pwned`\nbin/test a & b\nbin/test "x"\n'
                                'bin/test $HOME\nbin/test *.py\nbin/test a | b\nbin/test a; b\nbin/test {a,b}\nbin/test (a)\n'
                                'bin/test --shard=1/2\n```\nAlways run `bin/test` before you finish.\n')
        result = self.scan()
        rules = json.loads(self.finding(result, 'allowlist')['fix'].split(': ', 1)[1])['permissions']['allow']
        # `a | b` and `a; b` are split into separate calls, so `bin/test a` is a call of its own.
        self.assertEqual(rules, ['Bash(bin/test)', 'Bash(bin/test a)', 'Bash(bin/test --shard=1/2)'])
        for call in ('bin/test $HOME', 'bin/test *.py', 'bin/test a | b', 'bin/test a; b', 'bin/test {a,b}',
                     'bin/test (a)', 'bin/test `x`', 'bin/test a & b', 'bin/test "x"', "bin/test 'x'", 'bin/test > out'):
            self.assertIsNone(cl.PLAIN_CALL.fullmatch(call), call)
        self.assertTrue(cl.PLAIN_CALL.fullmatch('bin/check-marketplace --base origin/main'))

    def test_repeated_documented_call_gives_one_rule(self):
        self.write('bin/sdlc', '#!/bin/sh\n', 0o755)
        self.write('CLAUDE.md', 'Run `bin/sdlc check`.\n\nBefore merging, run `bin/sdlc check` again.\n')
        rules = json.loads(self.finding(self.scan(), 'allowlist')['fix'].split(': ', 1)[1])['permissions']['allow']
        self.assertEqual(rules, ['Bash(bin/sdlc check)'])

    def test_unread_settings_suppress_settings_coverage(self):
        self.write('bin/ci', '#!/bin/sh\n', 0o755)
        self.write('go.mod', 'module x\n')
        self.write('.env', 'X=1\n')
        self.write('CLAUDE.md', 'Always run `bin/ci` before you report done.\n')
        settings = {'permissions': {'allow': ['Bash(bin/ci)'], 'deny': ['Read(./.env)']},
                    'hooks': {'Stop': [{'hooks': [{'type': 'command', 'command': 'bin/ci'}]}]}}
        self.write('.claude/settings.json', settings)
        self.assertFalse({'allowlist', 'secret-deny', 'stop-hook'} & set(self.ids(self.scan())))
        large = dict(settings, env={'X': 'y' * (cl.MAX_READ + 10)})
        for content, state in ((large, 'too-large'), ('{"permissions": {', 'invalid-json'), ([1, 2], 'not an object')):
            with self.subTest(state=state):
                self.write('.claude/settings.json', content)
                result = self.scan()
                self.assertFalse({'allowlist', 'stop-hook', 'gate-ask'} & set(self.ids(result)), self.ids(result))
                self.assertIn('Not checked: `.claude/settings.json` (%s) could not be read, so the allowlist, ask-rule '
                              'and Stop-hook checks were skipped.' % state, result['footer'])

    def test_allowlist_snippet(self):
        self.write('package.json', {'scripts': {'test': 'jest', 'lint': 'eslint .'}})
        self.write('CLAUDE.md', 'Run `npm test -- <file>` and `./bin/check-all --fast`.\n')
        self.write('bin/check-all', '', 0o755)
        self.write('.claude/settings.json', {'permissions': {'allow': ['Bash(npm test)']}})
        result = self.scan()
        f = self.finding(result, 'allowlist')
        snippet = json.loads(f['fix'].split(': ', 1)[1])
        # Exact calls only: `npm test` is already allowed, and `npm test -- <file>` holds a placeholder.
        self.assertEqual(snippet, {'permissions': {'allow': ['Bash(bin/check-all --fast)']}})
        self.assertEqual([c['command'] for c in result['inventory']['check_commands'] if c['documented']],
                         ['npm test', 'bin/check-all'])
        self.assertEqual((f['path'], f['line']), ('CLAUDE.md', 1))
        self.write('.claude/settings.json', {'permissions': {'allow': []}})
        self.assertIn('`npm test`', self.finding(self.scan(), 'allowlist')['problem'])
        self.write('.claude/settings.json', {'permissions': {'allow': ['Bash(npm test:*)']}})
        self.assertNotIn('`npm test`', self.finding(self.scan(), 'allowlist')['problem'])

    def test_must_rules_need_stop_hook(self):
        self.write('bin/ci', '', 0o755)
        self.write('CLAUDE.md', 'Always run `bin/ci` before you report done.\nNever run `git push --force`.\n'
                                'You must use `snake_case`.\n')
        result = self.scan()
        self.assertEqual([r['line'] for r in result['inventory']['must_rules']], [1])
        f = self.finding(result, 'stop-hook')
        self.assertIn('stop_hook_active', f['fix'])
        self.assertIn('exit 2', f['fix'])
        self.assertIn('if ! out=$(bin/ci 2>&1)', f['fix'])
        self.assertIn('"bin/ci failed:"', f['fix'])
        self.assertEqual((f['path'], f['line']), ('CLAUDE.md', 1))
        self.assertIn('`CLAUDE.md:1` says "Always run `bin/ci` before you report done."', f['problem'])
        self.write('.claude/settings.json', {'hooks': {'TaskCompleted': [{'hooks': [{'type': 'command', 'command': 'true'}]}]}})
        self.assertNotIn('stop-hook', self.ids(self.scan()))

    def test_stop_hook_runs_the_exact_documented_call(self):
        self.write('bin/sdlc', '#!/bin/sh\n', 0o755)
        self.write('CLAUDE.md', 'Always run `bin/sdlc check` before you report done.\n')
        fix = self.finding(self.scan(), 'stop-hook')['fix']
        self.assertIn('if ! out=$(bin/sdlc check 2>&1); then', fix)
        self.assertIn('"bin/sdlc check failed:"', fix)
        self.assertNotIn('$(bin/sdlc 2>&1)', fix)

class Cli(Project):
    def test_scan_is_read_only_and_redacts(self):
        home = os.path.join(self.root, 'home')
        self.root = os.path.join(home, 'project')
        os.makedirs(self.root)
        self.well_configured()
        self.write('.env', 'API_KEY=sk-live-supersecret\n')
        self.write('.mcp.json', {'mcpServers': {'db': {'command': 'db-mcp', 'env': {'DB_PASSWORD': 'hunter2-secret'},
                                                       'headers': {'Authorization': 'Bearer xyz-secret'}}}})
        config = os.path.join(home, '.claude')
        os.makedirs(config)
        with open(os.path.join(config, 'CLAUDE.md'), 'w') as handle:
            handle.write('@~/missing.md\n')
        with open(os.path.join(home, '.claude.json'), 'w') as handle:
            handle.write('{"oauth": "claude-json-secret"}')
        before = tree(home)
        code, result, raw = self.cli('scan', '--root', self.root, '--claude-version', '2.1.312', env={'HOME': home})
        self.assertEqual(code, 0)
        self.assertEqual(tree(home), before)
        self.assertFalse([p for p in Path(home).rglob('*') if p.name == '__pycache__' or p.suffix == '.pyc'])
        self.assertFalse((SCRIPT.parent / '__pycache__').exists())
        for needle in (home, 'supersecret', 'hunter2', 'xyz-secret', 'claude-json-secret'):
            self.assertNotIn(needle, raw)
        # User-level files are out of scope: the footer says so, and ~/.claude/CLAUDE.md is never read.
        self.assertEqual([f['id'] for f in result['findings']], [])
        self.assertNotIn('missing.md', raw)

    def test_dismiss_writes_only_its_file_and_filters(self):
        self.write('go.mod', 'module x\n')
        before = tree(self.root)
        code, out, _ = self.cli('dismiss', '--shared', '--root', self.root, '--id', 'allowlist', '--reason', 'we ask')
        self.assertEqual((code, out['added']), (0, True))
        code, out, _ = self.cli('dismiss', '--shared', '--root', self.root, '--id', 'allowlist', '--reason', 'again')
        self.assertEqual((code, out['added']), (0, False))
        after = tree(self.root)
        self.assertEqual(set(after) - set(before), {'.claude/claudit-dismissed.json'})
        data = json.loads(Path(self.root, '.claude/claudit-dismissed.json').read_text())
        self.assertEqual(data['version'], 1)
        self.assertEqual([(d['id'], d['reason']) for d in data['dismissed']], [('allowlist', 'we ask')])
        result = self.scan()
        self.assertNotIn('allowlist', self.ids(result))
        self.assertEqual([(d['id'], d['reason']) for d in result['dismissed']], [('allowlist', 'we ask')])
        self.assertTrue(result['footer'][-1].endswith('; 1 dismissed (stored in `.claude/claudit-dismissed.json`)'))
        self.write('.claude/claudit-dismissed.json', '{bad')
        result = self.scan()
        self.assertIn('allowlist', self.ids(result))
        self.assertTrue([l for l in result['footer'] if 'claudit-dismissed' in l])
        code, out, _ = self.cli('dismiss', '--shared', '--root', self.root, '--id', 'x', '--reason', 'y')
        self.assertEqual(code, 2)
        self.assertEqual(Path(self.root, '.claude/claudit-dismissed.json').read_text(), '{bad')

    def test_dismiss_never_follows_a_planted_temp_file(self):
        outside = os.path.join(self.root, 'outside.txt')
        self.write('outside.txt', 'keep\n')
        os.makedirs(os.path.join(self.root, '.claude'))
        os.symlink(outside, os.path.join(self.root, '.claude/claudit-dismissed.json.tmp'))
        code, out, _ = self.cli('dismiss', '--shared', '--root', self.root, '--id', 'lsp', '--reason', 'r')
        self.assertEqual((code, out['added']), (0, True))
        self.assertEqual(Path(outside).read_text(), 'keep\n')
        data = json.loads(Path(self.root, '.claude/claudit-dismissed.json').read_text())
        self.assertEqual([d['id'] for d in data['dismissed']], ['lsp'])
        self.assertEqual(sorted(os.listdir(os.path.join(self.root, '.claude'))),
                         ['claudit-dismissed.json', 'claudit-dismissed.json.tmp'])

    def test_dismiss_refuses_symlinked_target_or_folder(self):
        elsewhere = tempfile.TemporaryDirectory()
        self.addCleanup(elsewhere.cleanup)
        target = os.path.join(elsewhere.name, 'victim.json')
        Path(target).write_text('{"version": 1, "dismissed": []}\n')
        os.makedirs(os.path.join(self.root, '.claude'))
        os.symlink(target, os.path.join(self.root, '.claude/claudit-dismissed.json'))
        code, out, _ = self.cli('dismiss', '--shared', '--root', self.root, '--id', 'lsp', '--reason', 'r')
        self.assertEqual(code, 2)
        self.assertIn('refusing', out['error'])
        self.assertEqual(Path(target).read_text(), '{"version": 1, "dismissed": []}\n')
        shutil.rmtree(os.path.join(self.root, '.claude'))
        os.symlink(elsewhere.name, os.path.join(self.root, '.claude'))
        before = tree(elsewhere.name)
        code, out, _ = self.cli('dismiss', '--shared', '--root', self.root, '--id', 'lsp', '--reason', 'r')
        self.assertEqual(code, 2)
        self.assertIn('refusing', out['error'])
        self.assertEqual(tree(elsewhere.name), before)

    def test_dismiss_refuses_when_claude_is_a_file(self):
        self.write('.claude', 'not a directory\n')
        code, out, _ = self.cli('dismiss', '--shared', '--root', self.root, '--id', 'lsp', '--reason', 'r')
        self.assertEqual(code, 2)
        self.assertIn('refusing', out['error'])
        self.assertEqual(Path(self.root, '.claude').read_text(), 'not a directory\n')

    def test_bad_arguments_exit_2_with_json(self):
        for args in (['scan', '--root', os.path.join(self.root, 'nope')], ['bogus'], [],
                     ['scan', '--claude-version', 'latest'], ['scan', '--user'], ['new-pages', '--pages', 'x'],
                     ['deep']):
            code, out, _ = self.cli(*args)
            self.assertEqual(code, 2, args)
            self.assertIn('error', out)

    @unittest.skipUnless(shutil.which('git'), 'git not installed')
    def test_root_resolves_to_git_toplevel(self):
        self.write('CLAUDE.md', 'See `src/app.js`.\n')
        self.write('src/app.js', '')
        self.write('.gitignore', 'CLAUDE.local.md\n')
        self.write('CLAUDE.local.md', '')
        env = dict(os.environ, GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
        subprocess.run(['git', 'init', '-q', self.root], check=True, env=env)
        code, result, _ = self.cli('scan', '--root', os.path.join(self.root, 'src'), '--claude-version', '2.1.312')
        self.assertEqual(code, 0)
        self.assertTrue(result['git'])
        self.assertEqual(self.ids_of(result, 'stale-ref'), [])

    def ids_of(self, result, prefix):
        return [f['id'] for f in result['findings'] if f['id'].startswith(prefix)]


class Package(unittest.TestCase):
    """The 5.0.0 package: one skill that runs only the scan and dismiss calls, no subagent, no feature catalog."""

    PLUGIN = ROOT / 'plugins/claudit'

    def test_inventory(self):
        files = sorted(str(p.relative_to(self.PLUGIN)) for p in self.PLUGIN.rglob('*')
                       if p.is_file() and '__pycache__' not in p.parts)
        self.assertEqual(files, ['.claude-plugin/plugin.json', 'CHANGELOG.md', 'LICENSE', 'README.md',
                                 'skills/claudit/SKILL.md', 'skills/claudit/references/apply.md',
                                 'skills/claudit/scripts/claudit.py'])
        manifest = json.loads((self.PLUGIN / '.claude-plugin/plugin.json').read_text())
        self.assertEqual(manifest['version'], cl.VERSION)
        self.assertIn('## %s' % cl.VERSION, (self.PLUGIN / 'CHANGELOG.md').read_text())

    def test_skill_runs_only_the_scan_and_dismiss(self):
        text = (self.PLUGIN / 'skills/claudit/SKILL.md').read_text()
        head = text.split('\n---\n', 1)[0]
        tools = next(line for line in head.splitlines() if line.startswith('allowed-tools: '))
        self.assertEqual(tools.split(': ', 1)[1].split(' Bash('),
                         ['Read Grep Glob', 'python3 ${CLAUDE_SKILL_DIR}/scripts/claudit.py scan *)',
                          'python3 ${CLAUDE_SKILL_DIR}/scripts/claudit.py dismiss *)'])
        description = next(line for line in head.splitlines() if line.startswith('description: '))
        self.assertLess(len(description), cl.LISTING_CAP)
        for gone in ('WebFetch', '--deep', '--user', 'new-pages', 'auditor', 'catalog.json', 'Grades'):
            self.assertNotIn(gone, text)
        self.assertIn('/doctor prompt-audit', (self.PLUGIN / 'README.md').read_text().split('## Installation')[0])


class Portability(unittest.TestCase):
    def test_source_parses_as_python_39(self):
        source = SCRIPT.read_text(encoding='utf-8')
        ast.parse(source, feature_version=(3, 9))
        self.assertNotIn('removeprefix', source)


if __name__ == '__main__':
    unittest.main()
