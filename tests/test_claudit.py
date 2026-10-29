"""Offline checks for the Claudit 4.0 scan helper against synthetic projects."""
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

    def scan(self, version='2.1.312', user=False):
        return cl.Scan(self.root, False, cl.load_catalog(), version, user).run()

    def ids(self, result, grade=None):
        return [f['id'] for f in result['findings'] if grade is None or f['grade'] == grade]

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
    def test_zero_correctness_findings_and_baseline_met(self):
        self.well_configured()
        result = self.scan()
        self.assertEqual(self.ids(result, 'correctness'), [])
        self.assertEqual(self.ids(result, 'alignment'), [])
        status = {b['id']: b['status'] for b in result['baseline']}
        self.assertEqual(status, {'instructions': 'met', 'check': 'met', 'allowlist': 'met',
                                  'secrets': 'met', 'enforced': 'met'})
        local = [i for i in result['inventory']['instructions'] if i['path'] == 'CLAUDE.local.md'][0]
        self.assertTrue(local['gitignored'])
        self.assertEqual(result['root'], '.')

    def test_every_finding_cites_a_catalog_doc(self):
        self.write('CLAUDE.md', '@missing.md\n' + 'x\n' * 210)
        self.write('.claudeignore', '.env\n')
        self.write('.claude/settings.json', {'permissions': {'allow': ['Write(src/**)'], 'defaultMode': 'auto'}})
        self.write('go.mod', 'module x\n')
        docs = cl.load_catalog()['docs']
        result = self.scan()
        self.assertTrue(result['findings'])
        for f in result['findings']:
            self.assertIn(f['source'], [{'url': d['url'], 'heading': d['heading']} for d in docs.values()], f['id'])
            self.assertTrue(f['source']['url'].startswith('https://code.claude.com/docs/'), f['id'])
            self.assertIn(f['confidence'], ('high', 'medium'))


class Correctness(Project):
    def test_invalid_json_files(self):
        self.write('CLAUDE.md', '# x\n')
        self.write('.claude/settings.json', '{"permissions": {')
        self.write('.mcp.json', '{oops}')
        self.write('plugins/p/.claude-plugin/plugin.json', '[1,')
        result = self.scan()
        for rel in ('.claude/settings.json', '.mcp.json', 'plugins/p/.claude-plugin/plugin.json'):
            f = self.finding(result, 'invalid-json:' + rel)
            self.assertEqual((f['severity'], f['source']), ('high', cl.load_catalog()['docs']['config-causes']))
        states = {s['path']: s['state'] for s in result['inventory']['settings']}
        self.assertEqual(states['.claude/settings.json'], 'invalid-json')

    def test_write_glob_notebook_rules_with_paths(self):
        self.write('.claude/settings.json', {'permissions': {
            'allow': ['Write(src/**)', 'Write', 'Glob', 'Edit(src/**)'],
            'deny': ['Glob(secrets/**)'], 'ask': ['NotebookEdit(nb/*.ipynb)']}})
        result = self.scan()
        ids = [i for i in self.ids(result) if i.startswith('write-rule:')]
        self.assertEqual(sorted(ids), ['write-rule:.claude/settings.json:Glob(secrets/**)',
                                       'write-rule:.claude/settings.json:NotebookEdit(nb/*.ipynb)',
                                       'write-rule:.claude/settings.json:Write(src/**)'])
        self.assertIn('Edit(src/**)', self.finding(result, ids[2])['fix'])
        self.assertIn('Read(secrets/**)', self.finding(result, ids[0])['fix'])
        self.assertEqual(self.finding(result, ids[2])['line'], 4)

    def test_claudeignore_maps_to_deny_rules(self):
        self.write('.claudeignore', '# ignore\n.env.*\nsecrets/\n')
        f = self.finding(self.scan(), 'claudeignore')
        self.assertEqual(f['severity'], 'high')
        self.assertIn('Read(./.env.*)', f['fix'])
        self.assertIn('Read(./secrets/**)', f['fix'])
        self.write('.claudeignore', 'dist/\n')
        self.assertEqual(self.finding(self.scan(), 'claudeignore')['severity'], 'medium')

    def test_skill_layout(self):
        self.write('.claude/skills/notes.md', '# notes\n')
        self.write('.claude/skills/README.md', '# about skills\n')
        self.write('.claude/skills/empty/helper.sh', 'echo\n')
        self.write('.claude/skills/good/SKILL.md', '---\nname: good\ndescription: d\n---\n')
        self.write('.claude-plugin/plugin.json', {'name': 'p'})
        self.write('skills/flat.md', '# flat\n')
        self.write('skills/ok/SKILL.md', '---\nname: ok\n---\n')
        ids = self.ids(self.scan())
        self.assertIn('flat-skill:.claude/skills/notes.md', ids)
        self.assertIn('skill-missing:.claude/skills/empty', ids)
        self.assertIn('flat-skill:skills/flat.md', ids)
        self.assertFalse([i for i in ids if 'good' in i or 'README' in i or 'skills/ok' in i], ids)

    def test_stray_skill_md_does_not_hide_default_skill_dir_defects(self):
        self.write('.claude-plugin/plugin.json', {'name': 'p', 'skills': ['./skills', './extra']})
        for base in ('.claude/skills', 'skills'):
            self.write(base + '/SKILL.md', '# stray\n')
            self.write(base + '/release.md', '# release\n')
            self.write(base + '/deploy/notes.md', '# notes\n')
        self.write('extra/SKILL.md', '---\nname: extra\ndescription: d\n---\n')
        self.write('extra/scripts/run.md', '')
        ids = self.ids(self.scan())
        for base in ('.claude/skills', 'skills'):
            for fid in ('flat-skill:%s/SKILL.md', 'flat-skill:%s/release.md', 'skill-missing:%s/deploy'):
                self.assertIn(fid % base, ids)
        self.assertFalse([i for i in ids if 'extra' in i], ids)

    def test_default_mode_and_auto_mode(self):
        self.write('.claude/settings.local.json', {'permissions': {'defaultMode': 'bypassPermissions'}})
        self.write('.claude/settings.json', {'permissions': {'defaultMode': 'acceptEdits'}, 'autoMode': {}})
        result = self.scan()
        f = self.finding(result, 'default-mode:.claude/settings.local.json')
        self.assertEqual((f['severity'], f['source']), ('high', cl.load_catalog()['docs']['ignored-values']))
        self.assertIn('2.1.257', f['evidence'])
        self.assertNotIn('default-mode:.claude/settings.json', self.ids(result))
        self.assertEqual(self.finding(result, 'auto-mode:.claude/settings.json')['source'], cl.load_catalog()['docs']['settings-index'])
        self.write('.claude/settings.json', {'permissions': {'defaultMode': 'auto'}})
        self.assertIn('default-mode:.claude/settings.json', self.ids(self.scan()))

    def test_default_mode_text_follows_claude_version(self):
        self.write('.claude/settings.json', {'permissions': {'defaultMode': 'bypassPermissions'}})
        old = self.finding(self.scan('2.1.200'), 'default-mode:.claude/settings.json')
        self.assertEqual(old['severity'], 'high')
        self.assertIn('2.1.200 applies it to everyone', old['evidence'])
        self.assertNotIn('; ignored from', old['evidence'])
        unknown = self.finding(self.scan('unknown'), 'default-mode:.claude/settings.json')
        self.assertIn('ignored from project/local settings since 2.1.257', unknown['evidence'])
        before = self.finding(self.scan('2.1.256'), 'default-mode:.claude/settings.json')['evidence']
        self.assertIn('2.1.256 applies it to everyone', before)
        at = self.finding(self.scan('2.1.257'), 'default-mode:.claude/settings.json')['evidence']
        self.assertTrue(at.startswith('permissions.defaultMode is "bypassPermissions"; ignored from'), at)

    def test_wrong_typed_values_are_findings_not_crashes(self):
        cases = [('.claude/settings.json', {'permissions': {'allow': 5}}, 'permissions.allow', 'permission-rules'),
                 ('.claude/settings.json', {'hooks': {'Stop': [{'hooks': 5}]}}, 'hooks.Stop[0].hooks', 'check-hooks'),
                 ('.claude/settings.json', {'hooks': {'PreToolUse': {'matcher': 'Bash'}}}, 'hooks.PreToolUse',
                  'check-hooks'),
                 ('.claude-plugin/plugin.json', {'name': 'p', 'skills': 5}, 'skills', 'plugins')]
        for rel, content, key, doc in cases:
            with self.subTest(key=key):
                self.write(rel, content)
                code, result, _ = self.cli('scan', '--root', self.root, '--claude-version', '2.1.312')
                self.assertEqual(code, 0)
                f = self.finding(result, 'wrong-type:%s:%s' % (rel, key))
                self.assertEqual((f['grade'], f['severity'], f['source']),
                                 ('correctness', 'high', cl.load_catalog()['docs'][doc]))
                self.assertIn('expected', f['evidence'])
                os.remove(os.path.join(self.root, rel))

    def test_manifest_skill_path_naming_one_skill(self):
        self.write('.claude-plugin/plugin.json', {'name': 'p', 'skills': ['./extra/xlsx']})
        self.write('extra/xlsx/SKILL.md', '---\nname: xlsx\ndescription: d\n---\n')
        self.write('extra/xlsx/scripts/run.py', '')
        result = self.scan()
        self.assertFalse([i for i in self.ids(result) if i.startswith(('flat-skill', 'skill-missing'))], self.ids(result))
        self.assertIn('extra/xlsx', result['inventory']['plugins'][0]['skill_dirs'])

    def test_too_large_settings_is_not_invalid(self):
        self.write('.claude/settings.json', json.dumps({'env': {'X': 'y' * (cl.MAX_READ + 10)}}))
        result = self.scan()
        f = self.finding(result, 'too-large:.claude/settings.json')
        self.assertEqual(f['severity'], 'low')
        self.assertFalse([i for i in self.ids(result) if i.startswith('invalid-json')])
        self.assertEqual(result['inventory']['settings'][0]['state'], 'too-large')

    def test_settings_root_must_be_an_object(self):
        for content in ([1, 2], '"str"', 'null'):
            with self.subTest(content=content):
                self.write('.claude/settings.json', content)
                result = self.scan()
                f = self.finding(result, 'wrong-type:.claude/settings.json:(root)')
                self.assertEqual((f['grade'], f['severity']), ('correctness', 'high'))
                self.assertEqual(result['inventory']['settings'][0]['state'], 'ok')

    def test_too_large_mcp_json(self):
        self.write('.mcp.json', json.dumps({'mcpServers': {'db': {'command': 'x' * (cl.MAX_READ + 10)}}}))
        result = self.scan()
        f = self.finding(result, 'too-large:.mcp.json')
        self.assertEqual((f['severity'], f['source']), ('low', cl.load_catalog()['docs']['config-causes']))
        self.assertNotIn('invalid-json:.mcp.json', self.ids(result))
        self.assertEqual(result['inventory']['mcp'], [])

    def test_symlinked_claude_md_is_audited_once(self):
        self.write('AGENTS.md', '# x\n\nSee `docs/missing.md`.\n@gone.md\n')
        os.symlink('AGENTS.md', os.path.join(self.root, 'CLAUDE.md'))
        result = self.scan()
        self.assertEqual([i['path'] for i in result['inventory']['instructions']], ['CLAUDE.md'])
        self.assertEqual(sorted(self.ids(result, 'correctness')),
                         ['broken-import:CLAUDE.md:gone.md', 'stale-ref:CLAUDE.md:docs/missing.md'])

    def test_fixture_instruction_files_are_not_audited(self):
        self.write('CLAUDE.md', '# x\n')
        self.write('tests/fixtures/broken/CLAUDE.md', '@missing.md\n')
        self.write('pkg/CLAUDE.md', '# nested\n')
        paths = [i['path'] for i in self.scan()['inventory']['instructions']]
        self.assertEqual(paths, ['CLAUDE.md', 'pkg/CLAUDE.md'])

    def test_skill_named_like_a_build_dir_is_checked(self):
        self.write('.claude/skills/build/helper.sh', 'echo\n')
        self.write('.claude/skills/dist/SKILL.md', '---\nname: dist\ndescription: d\n---\n')
        self.write('.claude/skills/dist/node_modules/x/SKILL.md', '')
        result = self.scan()
        self.assertIn('skill-missing:.claude/skills/build', self.ids(result))
        self.assertEqual([s['path'] for s in result['inventory']['skills']], ['.claude/skills/dist/SKILL.md'])
        dirs = cl.Scan(self.root, False, {}, 'unknown').dirs
        self.assertIn('.claude/skills/build', dirs)
        self.assertNotIn('.claude/skills/dist/node_modules', dirs)

    def test_dependency_dirs_under_skills_are_still_pruned(self):
        self.write('skills/node_modules/dep/CLAUDE.md', '@missing.md\n')
        self.write('skills/vendor/CLAUDE.md', '@missing.md\n')
        self.write('skills/.git/CLAUDE.md', '@missing.md\n')
        self.write('skills/coverage/SKILL.md', '---\nname: coverage\ndescription: d\n---\n')
        scan = cl.Scan(self.root, False, {}, 'unknown')
        self.assertEqual({d for d in scan.dirs if d.startswith('skills/')}, {'skills/coverage'})
        self.assertFalse([i for i in self.ids(self.scan()) if i.startswith('broken-import')])
        self.write('.claude/skills/vendor/dep/index.js', '')
        self.write('.claude/skills/review/notes.md', 'x\n')
        ids = self.ids(self.scan())
        self.assertNotIn('skill-missing:.claude/skills/vendor', ids)
        self.assertIn('skill-missing:.claude/skills/review', ids)

    def test_misplaced_hooks_and_mcp(self):
        self.write('.claude/hooks.json', {'hooks': {}})
        self.write('hooks.json', {})
        self.write('.claude/mcp.json', {})
        self.write('.claude/settings.json', {'mcpServers': {'x': {'command': 'x'}}})
        ids = self.ids(self.scan())
        for fid in ('hooks-file:.claude/hooks.json', 'hooks-file:hooks.json', 'mcp-location:.claude/mcp.json',
                    'mcp-location:.claude/settings.json'):
            self.assertIn(fid, ids)

    def test_plugin_root_hooks_file_is_not_flagged(self):
        self.write('.claude-plugin/plugin.json', {'name': 'p'})
        self.write('hooks/hooks.json', {'hooks': {}})
        self.write('hooks.json', {})
        self.assertFalse([i for i in self.ids(self.scan()) if i.startswith('hooks-file')])

    def test_hook_matchers(self):
        self.write('.claude/settings.json', {'hooks': {
            'PostToolUse': [{'matcher': ['Edit', 'Write'], 'hooks': []}],
            'Stop': [{'matcher': 'Bash', 'hooks': []}],
            'SubagentStop': [{'matcher': 'reviewer', 'hooks': []}],
            'UserPromptSubmit': [{'hooks': []}, {'matcher': '*', 'hooks': []}],
            'PreToolUse': [{'hooks': []}]}})
        result = self.scan()
        f = self.finding(result, 'matcher-type:.claude/settings.json:PostToolUse')
        self.assertEqual(f['severity'], 'high')
        self.assertIn('"Edit|Write"', f['fix'])
        self.assertEqual(self.finding(result, 'matcher-ignored:.claude/settings.json:Stop')['severity'], 'low')
        ids = self.ids(result)
        self.assertNotIn('matcher-ignored:.claude/settings.json:SubagentStop', ids)
        self.assertFalse([i for i in ids if 'UserPromptSubmit' in i or 'PreToolUse' in i])

    def test_no_matcher_events_come_from_catalog(self):
        catalog = dict(cl.load_catalog(), no_matcher_events=['PreToolUse'])
        self.write('.claude/settings.json', {'hooks': {'PreToolUse': [{'matcher': 'Bash', 'hooks': []}],
                                                       'Stop': [{'matcher': 'Bash', 'hooks': []}]}})
        ids = [f['id'] for f in cl.Scan(self.root, False, catalog, '2.1.312').run()['findings']]
        self.assertIn('matcher-ignored:.claude/settings.json:PreToolUse', ids)
        self.assertNotIn('matcher-ignored:.claude/settings.json:Stop', ids)

    def test_hook_script_paths(self):
        self.write('.claude/hooks/present.sh', '#!/bin/sh\n', 0o755)
        self.write('.claude/settings.json', {'hooks': {'PostToolUse': [{'matcher': 'Edit', 'hooks': [
            {'type': 'command', 'command': '"$CLAUDE_PROJECT_DIR"/.claude/hooks/present.sh'},
            {'type': 'command', 'command': '${CLAUDE_PROJECT_DIR}/.claude/hooks/gone.sh --fast'},
            {'type': 'command', 'command': 'bash ./scripts/missing.sh'},
            {'type': 'command', 'command': 'npx prettier --write'}]}]}})
        ids = [i for i in self.ids(self.scan()) if i.startswith('hook-script')]
        self.assertEqual(sorted(ids), ['hook-script:.claude/settings.json:.claude/hooks/gone.sh',
                                       'hook-script:.claude/settings.json:scripts/missing.sh'])

    def test_oversized_instructions(self):
        self.write('CLAUDE.md', '# x\n' + 'line\n' * 205)
        self.write('AGENTS.md', 'a\n' * 300)
        ids = self.ids(self.scan())
        self.assertIn('oversized:CLAUDE.md', ids)
        self.assertNotIn('oversized:AGENTS.md', ids)
        self.write('CLAUDE.md', '@AGENTS.md\n')
        result = self.scan()
        self.assertEqual(self.finding(result, 'oversized:AGENTS.md')['grade'], 'alignment')
        self.assertEqual([b['status'] for b in result['baseline'] if b['id'] == 'instructions'], ['partial'])

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
        self.assertEqual(result['inventory']['instruction_lines_loaded'], 2 + 2 + 2 * 4 + 3)
        self.assertEqual([r['path'] for r in result['signals']['must_rules']], ['docs/e.md'])
        self.assertIn('stale-ref:docs/e.md:docs/old/gone.md', self.ids(result))
        self.assertEqual(result['signals']['documented_checks'], ['bin/ci'])

    def test_unloaded_agents_md_imports_are_not_loaded(self):
        self.write('CLAUDE.md', '# x\n')
        self.write('AGENTS.md', '@docs/agent.md\n')
        self.write('docs/agent.md', 'a\nb\n')
        result = self.scan()
        inst = {i['path']: i['loaded'] for i in result['inventory']['instructions']}
        self.assertEqual(inst, {'CLAUDE.md': True, 'AGENTS.md': False, 'docs/agent.md': False})
        self.assertEqual(result['inventory']['instruction_lines_loaded'], 1)

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

    def test_user_scope_is_opt_in(self):
        config = os.path.join(self.root, 'config')
        os.makedirs(config)
        with open(os.path.join(config, 'settings.json'), 'w') as handle:
            json.dump({'permissions': {'allow': ['Write(/tmp/**)'], 'defaultMode': 'bypassPermissions'}}, handle)
        os.environ['CLAUDE_CONFIG_DIR'] = config
        self.addCleanup(os.environ.pop, 'CLAUDE_CONFIG_DIR')
        self.assertFalse(self.ids(self.scan(), 'correctness'))
        self.assertIn('user settings not read (project scope)', self.scan()['limits'])
        ids = self.ids(self.scan(user=True))
        self.assertIn('write-rule:config/settings.json:Write(/tmp/**)', ids)
        self.assertFalse([i for i in ids if i.startswith('default-mode')])


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
        self.assertEqual(cl.sample_for('.env*'), '.env')
        self.assertEqual(cl.sample_for('.env.*'), '.env.x')
        self.assertEqual(cl.deny_rule('secrets/'), 'Read(./secrets/**)')


class Coverage(Project):
    def test_no_instructions_lists_checks(self):
        self.write('go.mod', 'module x\n')
        result = self.scan()
        f = self.finding(result, 'no-instructions')
        self.assertEqual((f['grade'], f['severity']), ('coverage', 'high'))
        self.assertIn('go test ./...', f['fix'])
        self.assertEqual({b['id']: b['status'] for b in result['baseline']}['instructions'], 'missing')

    def test_check_detection_and_undocumented(self):
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
        commands = [c['command'] for c in result['signals']['check_commands']]
        self.assertEqual(commands, ['bin/ci', 'scripts/test.sh', 'make lint', 'pnpm run typecheck', 'cargo test', 'pytest'])
        self.assertIn('undocumented-checks', self.ids(result))
        self.assertEqual({b['id']: b['status'] for b in result['baseline']}['check'], 'missing')

    def test_python_prefers_mentioned_command(self):
        self.write('tests/test_x.py', '')
        self.write('CLAUDE.md', 'Run `python3 -m unittest discover -s tests` to check.\n')
        checks = self.scan()['signals']['check_commands']
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
        checks = [(c['command'], c['args']) for c in result['signals']['check_commands']]
        self.assertEqual(checks, [('bin/sdlc', True)])
        fix = self.finding(result, 'allowlist')['fix']
        self.assertEqual(json.loads(fix.split(': ', 1)[1]), {'permissions': {'allow': ['Bash(bin/sdlc check)']}})
        self.write('CLAUDE.md', '@docs/guide.md\n@AGENTS.md\n')
        checks = [c['command'] for c in self.scan()['signals']['check_commands']]
        # Neither a release script nor one whose documented call names no check (it may run anything).
        self.assertEqual(checks, ['bin/sdlc'])

    def test_mentioned_scripts_get_exact_non_mutating_rules(self):
        for name in ('sdlc', 'release', 'check-marketplace'):
            self.write('bin/' + name, '#!/bin/sh\n', 0o755)
        self.write('CLAUDE.md', 'Run `bin/sdlc check`, then `bin/sdlc apply` and `bin/release promote`.\n'
                                'Compare with `bin/sdlc check BASE`.\n'
                                'Also `bin/check-marketplace --base origin/main` and `bin/check-marketplace --write`.\n')
        result = self.scan()
        rules = json.loads(self.finding(result, 'allowlist')['fix'].split(': ', 1)[1])['permissions']['allow']
        self.assertEqual(rules, ['Bash(bin/sdlc check)', 'Bash(bin/check-marketplace --base origin/main)'])
        self.assertFalse([r for r in rules if '*' in r or 'apply' in r or 'promote' in r or 'write' in r], rules)
        self.assertNotIn('bin/release', [c['command'] for c in result['signals']['check_commands']])
        self.write('.claude/settings.json', {'permissions': {'allow': [
            'Bash(bin/sdlc check)', 'Bash(bin/check-marketplace --base origin/main)']}})
        result = self.scan()
        self.assertNotIn('allowlist', self.ids(result))
        self.assertEqual({b['id']: b['status'] for b in result['baseline']}['allowlist'], 'met')

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

    def test_suggested_calls_are_plain(self):
        self.write('bin/test', '#!/bin/sh\n', 0o755)
        self.write('CLAUDE.md', '```sh\nbin/test check `touch pwned`\nbin/test a & b\nbin/test "x"\n'
                                'bin/test --shard=1/2\n```\nAlways run `bin/test` before you finish.\n')
        result = self.scan()
        rules = json.loads(self.finding(result, 'allowlist')['fix'].split(': ', 1)[1])['permissions']['allow']
        self.assertEqual(rules, ['Bash(bin/test)', 'Bash(bin/test --shard=1/2)'])

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
                self.assertFalse({'allowlist', 'secret-deny', 'stop-hook', 'lsp'} & set(self.ids(result)), self.ids(result))
                self.assertIn('.claude/settings.json (%s) not checked; allowlist, secret-deny, stop-hook and lsp '
                              'coverage not judged' % state, result['limits'])
                status = {b['id']: b['status'] for b in result['baseline']}
                self.assertEqual([status[k] for k in ('allowlist', 'secrets', 'enforced')], ['n/a'] * 3)

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
        self.assertEqual(result['signals']['documented_checks'], ['npm test', 'bin/check-all'])
        self.assertEqual({b['id']: b['status'] for b in result['baseline']}['allowlist'], 'partial')
        self.write('.claude/settings.json', {'permissions': {'allow': []}})
        self.assertEqual({b['id']: b['status'] for b in self.scan()['baseline']}['allowlist'], 'missing')
        self.write('.claude/settings.json', {'permissions': {'allow': ['Bash(npm test:*)']}})
        result = self.scan()
        self.assertEqual({b['id']: b['status'] for b in result['baseline']}['allowlist'], 'partial')
        self.assertNotIn('npm test', self.finding(result, 'allowlist')['evidence'].split(': ')[1])

    def test_secret_coverage(self):
        self.write('.env', 'API_KEY=sk-live-supersecret\n')
        self.write('keys/server.pem', '-----BEGIN-----')
        self.write('.env.example', 'API_KEY=\n')
        self.write('.gitignore', '.env*\n!.env.example\n')
        result = self.scan()
        paths = [s['path_or_pattern'] for s in result['signals']['secret_paths']]
        self.assertEqual(paths, ['.env', 'keys/server.pem', '.env*'])
        f = self.finding(result, 'secret-deny')
        self.assertIn('Read(./keys/server.pem)', f['fix'])
        self.write('.claude/settings.json', {'permissions': {'deny': ['Read(./.env*)', 'Read(**/*.pem)']}})
        result = self.scan()
        self.assertNotIn('secret-deny', self.ids(result))
        self.assertEqual({b['id']: b['status'] for b in result['baseline']}['secrets'], 'met')

    def test_must_rules_need_stop_hook(self):
        self.write('bin/ci', '', 0o755)
        self.write('CLAUDE.md', 'Always run `bin/ci` before you report done.\nNever run `git push --force`.\n'
                                'You must use `snake_case`.\n')
        result = self.scan()
        self.assertEqual([r['line'] for r in result['signals']['must_rules']], [1])
        f = self.finding(result, 'stop-hook')
        self.assertIn('stop_hook_active', f['fix'])
        self.assertIn('exit 2', f['fix'])
        self.assertIn('if ! out=$(bin/ci 2>&1)', f['fix'])
        self.assertIn('"bin/ci failed:"', f['fix'])
        self.assertEqual({b['id']: b['status'] for b in result['baseline']}['enforced'], 'missing')
        self.write('.claude/settings.json', {'hooks': {'TaskCompleted': [{'hooks': [{'type': 'command', 'command': 'true'}]}]}})
        result = self.scan()
        self.assertNotIn('stop-hook', self.ids(result))
        self.assertEqual({b['id']: b['status'] for b in result['baseline']}['enforced'], 'met')

    def test_stop_hook_runs_the_exact_documented_call(self):
        self.write('bin/sdlc', '#!/bin/sh\n', 0o755)
        self.write('CLAUDE.md', 'Always run `bin/sdlc check` before you report done.\n')
        fix = self.finding(self.scan(), 'stop-hook')['fix']
        self.assertIn('if ! out=$(bin/sdlc check 2>&1); then', fix)
        self.assertIn('"bin/sdlc check failed:"', fix)
        self.assertNotIn('$(bin/sdlc 2>&1)', fix)

    def test_procedure_docs(self):
        steps = ''.join('%d. Step\n' % n for n in range(1, 6))
        self.write('CLAUDE.md', '# x\n')
        self.write('docs/RELEASE.md', '# Release\n1. a\n2. b\n3. c\n')
        self.write('docs/deploy-guide.md', '# Ship it\n' + steps)
        self.write('docs/notes.md', '# Notes\n1. a\n2. b\n3. c\n')
        self.write('README.md', steps)
        self.write('CHANGELOG.md', steps)
        self.write('tests/fixtures/release.md', '# Release\n' + steps)
        self.write('.claude/skills/ship/SKILL.md', '---\nname: ship\ndescription: Follows docs/deploy-guide.md\n---\n')
        self.write('.claude-plugin/plugin.json', {'name': 'p'})
        self.write('skills/shipped/SKILL.md', '---\nname: shipped\n---\nFollow docs/RELEASE.md and docs/runbook.md.\n')
        self.write('docs/runbook.md', '# Runbook\n1. a\n2. b\n3. c\n')
        self.write('.claude/commands/runbook.md', 'Follow docs/runbook.md.\n')
        result = self.scan()
        docs = {d['path']: d['has_skill'] for d in result['signals']['procedure_docs']}
        self.assertEqual(docs, {'docs/RELEASE.md': False, 'docs/deploy-guide.md': True, 'docs/runbook.md': True})
        self.assertEqual([i for i in self.ids(result) if i.startswith('procedure')], ['procedure-skill:docs/RELEASE.md'])
        self.assertIn('procedure-docs', [p['id'] for p in result['profiles']])

    def test_plugin_repo_checks(self):
        self.write('CLAUDE.md', '# x\n')
        self.write('.claude-plugin/marketplace.json', {'plugins': [{'name': 'p', 'source': './plugins/p'}]})
        self.write('plugins/p/.claude-plugin/plugin.json', {'name': 'p'})
        self.write('plugins/p/skills/a/SKILL.md', '---\nname: a\n---\n')
        result = self.scan()
        self.assertIn('plugin-repo', [p['id'] for p in result['profiles']])
        self.assertIn('claude plugin validate plugins/p', self.finding(result, 'plugin-validate')['fix'])
        self.assertIn('plugin-eval', self.ids(result))
        self.write('.github/workflows/ci.yml', 'steps:\n  - run: claude plugin validate .\n  - run: claude plugin eval plugins/p\n')
        self.write('evals/p/cases/one/case.yaml', 'x: 1\n')
        result = self.scan()
        self.assertEqual(result['signals']['plugin_checks'],
                         {'validate_documented': True, 'eval_documented': True, 'eval_suite': True,
                          'plugins': [{'name': 'p', 'path': 'plugins/p', 'eval_suite': True}]})
        self.assertFalse([i for i in self.ids(result) if i.startswith('plugin-')])

    def test_plugin_eval_suites_per_plugin(self):
        self.write('CLAUDE.md', 'CI runs `claude plugin validate .` and `claude plugin eval`.\n')
        self.write('.claude-plugin/marketplace.json', {'plugins': []})
        for name in ('alpha', 'beta', 'gamma', 'delta'):
            self.write('plugins/%s/.claude-plugin/plugin.json' % name, {'name': name})
        self.write('plugins/codex-only/plugin.json', {'name': 'codex-only'})
        self.write('plugins/alpha/evals/one/case.yaml', 'x: 1\n')
        self.write('evals/beta/cases/one/prompt.md', 'hi\n')
        self.write('plugins/gamma/.claude-plugin/plugin.json', {'name': 'gamma', 'experimental': {'evals': './t'}})
        result = self.scan()
        plugins = result['signals']['plugin_checks']['plugins']
        self.assertEqual([(p['name'], p['eval_suite']) for p in plugins],
                         [('alpha', True), ('beta', True), ('delta', False), ('gamma', True)])
        f = self.finding(result, 'plugin-eval')
        self.assertIn('delta (plugins/delta)', f['evidence'])
        self.assertNotIn('alpha', f['evidence'])
        self.assertEqual(f['path'], 'plugins/delta')
        self.write('plugins/delta/evals/a/case.yaml', 'x: 1\n')
        self.assertNotIn('plugin-eval', self.ids(self.scan()))

    def test_typed_codebase_and_lsp(self):
        self.write('CLAUDE.md', '# x\n')
        self.write('tsconfig.json', '{}')
        result = self.scan()
        self.assertIn('typescript-lsp', self.finding(result, 'lsp')['fix'])
        self.write('.claude/settings.json', {'enabledPlugins': {'typescript-lsp@claude-plugins-official': True}})
        result = self.scan()
        self.assertTrue(result['signals']['lsp_enabled'])
        self.assertNotIn('lsp', self.ids(result))

    def test_agent_run_signals(self):
        self.write('AGENTS.md', 'Agents must run checks.\n')
        self.write('.github/workflows/claude.yml', 'uses: anthropics/claude-code-action@v1\n')
        evidence = [p for p in self.scan()['profiles'] if p['id'] == 'agent-run'][0]['evidence']
        self.assertEqual(evidence, ['AGENTS.md exists', 'AGENTS.md:1 addresses agents',
                                    '.github/workflows/claude.yml runs Claude Code'])


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
        code, result, raw = self.cli('scan', '--root', self.root, '--user', '--claude-version', '2.1.312',
                                     env={'HOME': home})
        self.assertEqual(code, 0)
        self.assertEqual(tree(home), before)
        self.assertFalse([p for p in Path(home).rglob('*') if p.name == '__pycache__' or p.suffix == '.pyc'])
        self.assertFalse((SCRIPT.parent / '__pycache__').exists())
        for needle in (home, 'supersecret', 'hunter2', 'xyz-secret', 'claude-json-secret'):
            self.assertNotIn(needle, raw)
        self.assertIn('broken-import:~/.claude/CLAUDE.md:~/missing.md', [f['id'] for f in result['findings']])
        settings = result['inventory']['settings'][0]['summary']
        self.assertEqual(settings['env'], ['API_TOKEN'])
        self.assertEqual(result['inventory']['mcp'], [{'name': 'db', 'type': 'stdio', 'env': ['DB_PASSWORD'],
                                                       'headers': ['Authorization']}])

    def test_dismiss_writes_only_its_file_and_filters(self):
        self.write('go.mod', 'module x\n')
        before = tree(self.root)
        code, out, _ = self.cli('dismiss', '--root', self.root, '--id', 'lsp', '--reason', 'no LSP here')
        self.assertEqual((code, out['added']), (0, True))
        code, out, _ = self.cli('dismiss', '--root', self.root, '--id', 'lsp', '--reason', 'again')
        self.assertEqual((code, out['added']), (0, False))
        after = tree(self.root)
        self.assertEqual(set(after) - set(before), {'.claude/claudit-dismissed.json'})
        data = json.loads(Path(self.root, '.claude/claudit-dismissed.json').read_text())
        self.assertEqual(data['version'], 1)
        self.assertEqual([(d['id'], d['reason']) for d in data['dismissed']], [('lsp', 'no LSP here')])
        result = self.scan()
        self.assertNotIn('lsp', self.ids(result))
        self.assertEqual([(d['id'], d['reason']) for d in result['dismissed']], [('lsp', 'no LSP here')])
        self.write('.claude/claudit-dismissed.json', '{bad')
        result = self.scan()
        self.assertIn('lsp', self.ids(result))
        self.assertTrue([l for l in result['limits'] if 'claudit-dismissed' in l])
        code, out, _ = self.cli('dismiss', '--root', self.root, '--id', 'x', '--reason', 'y')
        self.assertEqual(code, 2)
        self.assertEqual(Path(self.root, '.claude/claudit-dismissed.json').read_text(), '{bad')

    def test_dismiss_never_follows_a_planted_temp_file(self):
        outside = os.path.join(self.root, 'outside.txt')
        self.write('outside.txt', 'keep\n')
        os.makedirs(os.path.join(self.root, '.claude'))
        os.symlink(outside, os.path.join(self.root, '.claude/claudit-dismissed.json.tmp'))
        code, out, _ = self.cli('dismiss', '--root', self.root, '--id', 'lsp', '--reason', 'r')
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
        code, out, _ = self.cli('dismiss', '--root', self.root, '--id', 'lsp', '--reason', 'r')
        self.assertEqual(code, 2)
        self.assertIn('refusing', out['error'])
        self.assertEqual(Path(target).read_text(), '{"version": 1, "dismissed": []}\n')
        shutil.rmtree(os.path.join(self.root, '.claude'))
        os.symlink(elsewhere.name, os.path.join(self.root, '.claude'))
        before = tree(elsewhere.name)
        code, out, _ = self.cli('dismiss', '--root', self.root, '--id', 'lsp', '--reason', 'r')
        self.assertEqual(code, 2)
        self.assertIn('refusing', out['error'])
        self.assertEqual(tree(elsewhere.name), before)

    def test_dismiss_refuses_when_claude_is_a_file(self):
        self.write('.claude', 'not a directory\n')
        code, out, _ = self.cli('dismiss', '--root', self.root, '--id', 'lsp', '--reason', 'r')
        self.assertEqual(code, 2)
        self.assertIn('refusing', out['error'])
        self.assertEqual(Path(self.root, '.claude').read_text(), 'not a directory\n')

    def test_new_pages(self):
        reviewed = cl.load_catalog()['reviewed_pages']
        pages = ','.join(reviewed[1:]) + ',https://code.claude.com/docs/en/brand-new.md\nwhats-new/2027-w01 ' \
            + 'https://code.claude.com/docs/_llms/ja.txt _llms/fr ' + reviewed[1]
        code, out, _ = self.cli('new-pages', '--pages', pages)
        self.assertEqual(code, 0)
        self.assertEqual(out, {'new_pages': ['brand-new'], 'new_whats_new': ['whats-new/2027-w01'],
                               'missing_from_index': 1})
        code, out, _ = self.cli('new-pages', '--pages', ','.join(reviewed))
        self.assertEqual(out, {'new_pages': [], 'new_whats_new': []})

    def test_bad_arguments_exit_2_with_json(self):
        for args in (['scan', '--root', os.path.join(self.root, 'nope')], ['bogus'], [],
                     ['scan', '--claude-version', 'latest'], ['new-pages', '--pages', ' , ']):
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
        local = [i for i in result['inventory']['instructions'] if i['path'] == 'CLAUDE.local.md'][0]
        self.assertTrue(local['gitignored'])

    def ids_of(self, result, prefix):
        return [f['id'] for f in result['findings'] if f['id'].startswith(prefix)]


class Portability(unittest.TestCase):
    def test_source_parses_as_python_39(self):
        source = SCRIPT.read_text(encoding='utf-8')
        ast.parse(source, feature_version=(3, 9))
        self.assertNotIn('removeprefix', source)


if __name__ == '__main__':
    unittest.main()
