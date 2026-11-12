import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

REPO = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader('check_skills', str(REPO / 'bin/check-skills'))
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)

FIXTURES = REPO / 'tests/fixtures/skills'
SKIP_BOTH = {module.SKIP_SKILLS_REF: '1', module.SKIP_CLAUDE_VALIDATE: '1'}


def rules(text):
    return [rule for _, rule, _ in module.lint_text(text)]


class LintTests(unittest.TestCase):
    def test_claude_only_fixture_has_one_finding_per_rule_with_lines(self):
        findings = module.lint_text((FIXTURES / 'claude-only-skill/SKILL.md').read_text())
        self.assertEqual([(line, rule) for line, rule, _ in findings], [
            (4, 'frontmatter-field'), (9, 'argument-substitution'), (10, 'shell-injection'),
            (11, 'plugin-variable'), (12, 'tool-name'), (13, 'output-style'), (14, 'hook')])
        for _, _, message in findings:
            self.assertIn('Fix: ', message)

    def test_portable_fixture_is_clean(self):
        self.assertEqual(module.lint_text((FIXTURES / 'portable-skill/SKILL.md').read_text()), [])

    def test_every_listed_frontmatter_field_fails_and_spec_fields_pass(self):
        for field in ('argument-hint', 'model', 'disable-model-invocation', 'disallowed-tools', 'user-invocable'):
            self.assertEqual(rules(f'---\nname: x\n{field}: y\n---\nBody\n'), ['frontmatter-field'], field)
        spec = '---\n' + ''.join(f'{f}: v\n' for f in module.SPEC_FIELDS) + 'metadata:\n  model: nested is fine\n---\n'
        self.assertEqual(rules(spec), [])

    def test_frontmatter_values_are_not_scanned(self):
        self.assertEqual(rules('---\nname: x\ndescription: Uses $ARGUMENTS and `Read`\nallowed-tools: Bash(git:*) Read\n---\n'), [])

    def test_plain_english_passes(self):
        for line in (
                'Read the file the user names.', 'Write a summary.', 'Edit the draft.', 'Task: triage issues.',
                'Grep the logs.', '## Skill overview', 'Agent Skills work in any agent tool.', 'Bash is a shell.',
                'Use bash to list files.', 'Read (or skim) the file.', 'A git pre-commit hook may reject it.',
                'React hooks are fine.', 'Match the output style of the report.', 'It costs $10, or $1.50.',
                'Press Stop.', 'Send a Notification.', 'The reading tool works.', 'Run `git status`.',
                'Write it as you would say it.', 'Pay in US$ or EUR.', 'Escape it as \\$1 in sed.',
                'Agent tools differ by vendor.', 'Task tools like Jira help.', 'Edit tools such as Vim work.',
                'Edit(s) are welcome.', 'Read(me) first.', 'See the Grep(1) manual.'):
            self.assertEqual(rules(line), [], line)

    def test_disguised_forms_fail(self):
        cases = {
            '`$ARGUMENTS`': 'argument-substitution', 'Use ${ARGUMENTS}.': 'argument-substitution',
            'First: $ARGUMENTS[0]': 'argument-substitution', 'Name $1 here.': 'argument-substitution',
            'File: $0': 'argument-substitution',
            'Branch !`git branch`': 'shell-injection', '```!\ngit status\n```': 'shell-injection',
            'Open $CLAUDE_PLUGIN_ROOT/x': 'plugin-variable', 'See ${CLAUDE_PLUGIN_DATA}/db': 'plugin-variable',
            'Cd ${CLAUDE_PROJECT_DIR}': 'plugin-variable',
            'Run Bash(git status).': 'tool-name', 'Allow Bash(git:*).': 'tool-name', 'Call Task(subagent).': 'tool-name', 'Use ` Read ` here.': 'tool-name', 'Call the Task tool.': 'tool-name',
            'Use the Edit and Write tools.': 'tool-name', 'Then AskUserQuestion.': 'tool-name',
            'Fetch with WebFetch': 'tool-name', 'Track it in TodoWrite.': 'tool-name',
            'See output-styles/x.md': 'output-style', 'Run /output-style.': 'output-style',
            'Set outputStyle.': 'output-style', 'Use the `concise` output style.': 'output-style',
            'Add a PostToolUse entry.': 'hook', 'Edit hooks/hooks.json.': 'hook', '{"hooks": {}}': 'hook',
            'On SessionStart, say hi.': 'hook',
        }
        for text, rule in cases.items():
            self.assertEqual(rules(text), [rule], text)

    def test_one_finding_per_rule_per_line(self):
        self.assertEqual(rules('$1 and $2 and $ARGUMENTS'), ['argument-substitution'])
        self.assertEqual(rules('$1 then `Read`'), ['argument-substitution', 'tool-name'])


class Repo:
    """A temporary copy of the files bin/check-skills reads."""

    def __init__(self, test):
        temp = tempfile.TemporaryDirectory()
        test.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for name in ('catalog.json', 'skills-check.json'):
            shutil.copy(REPO / name, self.root / name)
        shutil.copytree(REPO / 'plugins', self.root / 'plugins')
        shutil.copytree(FIXTURES, self.root / 'tests/fixtures/skills')

    def config(self, change):
        path = self.root / 'skills-check.json'
        value = json.loads(path.read_text())
        change(value)
        path.write_text(json.dumps(value))


class ExemptionTests(unittest.TestCase):
    def test_real_skills_pass_with_the_exemption(self):
        code, out, skipped = module.run(Repo(self).root, SKIP_BOTH)
        self.assertEqual(code, 0, out)
        self.assertIn('Skills lint: 2 skill(s) clean', out)
        self.assertTrue(any(line.startswith('Skills check skips writing-for-humans') for line in out))

    def test_removing_the_exemption_fails_both_writing_for_humans_skills(self):
        repo = Repo(self)
        repo.config(lambda c: c['claude_code_only'].pop('writing-for-humans'))
        code, out, _ = module.run(repo.root, SKIP_BOTH)
        self.assertEqual(code, 1)
        for skill in ('writing-audit', 'writing-style'):
            self.assertTrue(any(line.startswith(f'plugins/writing-for-humans/skills/{skill}/SKILL.md:') for line in out), skill)

    def test_stale_or_unexplained_exemptions_fail(self):
        for change, message in ((lambda c: c['claude_code_only'].update(gone='reason'), 'stale exemption'),
                                (lambda c: c['claude_code_only'].update({'writing-for-humans': ' '}), 'needs a reason')):
            repo = Repo(self)
            repo.config(change)
            with self.assertRaisesRegex(module.Invalid, message):
                module.run(repo.root, SKIP_BOTH)

    def test_repository_text_avoids_the_retired_phrasing(self):
        # Issue 214's acceptance grep, built in parts so this file doesn't match it.
        retired = re.compile('claude code' + r'[- ]only|' + 'claude code' + ' plugin marketplace', re.IGNORECASE)
        excluded = ('docs/archive/', 'docs/changes/', 'plugins/writing-for-humans/')
        files = subprocess.run(['git', 'ls-files'], cwd=REPO, check=True,
                               capture_output=True, text=True).stdout.splitlines()
        hits = [name for name in files if not name.startswith(excluded) and (REPO / name).is_file()
                and retired.search((REPO / name).read_text(errors='ignore'))]
        self.assertEqual(hits, [])


def git(*args, cwd):
    return subprocess.run(['git', *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


VALIDATOR = '''import fakedep
def validate(path):
    return ['fixture error'] if 'argument-hint' in (path / 'SKILL.md').read_text() else []
'''


class SkillsRefTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.temp = Path(temp.name)
        upstream = self.temp / 'upstream'
        package = upstream / 'skills-ref/src/skills_ref'
        package.mkdir(parents=True)
        (package / '__init__.py').write_text(VALIDATOR)
        git('init', '-q', cwd=upstream)
        git('config', 'uploadpack.allowAnySHA1InWant', 'true', cwd=upstream)
        git('add', '.', cwd=upstream)
        git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture', cwd=upstream)
        wheel = self.temp / 'fakedep-1.0-py3-none-any.whl'
        with zipfile.ZipFile(wheel, 'w') as archive:
            archive.writestr('fakedep.py', '')
        self.pin = {
            'repository': upstream.as_uri(), 'commit': git('rev-parse', 'HEAD', cwd=upstream),
            'folder': 'skills-ref', 'tree': git('rev-parse', 'HEAD:skills-ref', cwd=upstream),
            'wheels': [{'url': wheel.as_uri(), 'sha256': hashlib.sha256(wheel.read_bytes()).hexdigest()}]}
        self.repo = Repo(self)
        self.repo.config(lambda c: c.update(skills_ref=self.pin))
        patcher = patch.dict(os.environ, XDG_CACHE_HOME=str(self.temp / 'cache'))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.cache = self.temp / 'cache/quickstop/skills-ref' / self.pin['commit']

    def run_check(self):
        return module.run(self.repo.root, {module.SKIP_CLAUDE_VALIDATE: '1'})

    def test_fetches_once_then_runs_from_the_cache(self):
        code, out, _ = self.run_check()
        self.assertEqual(code, 0, out)
        self.assertIn(f"skills-ref {self.pin['commit'][:12]}: 2 skill(s) valid", out)
        self.assertTrue(self.cache.is_dir())
        with patch.object(module, 'fetch', side_effect=AssertionError('fetched again')):
            self.assertEqual(self.run_check()[0], 0)
        self.assertEqual(list(self.cache.rglob('__pycache__')), [])

    def test_validator_errors_fail_the_check(self):
        self.repo.config(lambda c: c['claude_code_only'].clear())
        code, out, _ = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn('plugins/writing-for-humans/skills/writing-style: skills-ref: fixture error', out)

    def test_wrong_pins_fail_and_leave_no_cache(self):
        for key, value in (('commit', '0' * 40), ('tree', '0' * 40)):
            with self.subTest(key=key):
                self.repo.config(lambda c: c['skills_ref'].update({key: value}))
                code, out, _ = self.run_check()
                self.assertEqual(code, 1)
                self.assertIn(module.SKIP_SKILLS_REF, out[-1])
                self.repo.config(lambda c: c.update(skills_ref=self.pin))
        self.repo.config(lambda c: c['skills_ref']['wheels'][0].update(sha256='0' * 64))
        code, out, _ = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn('does not match its pinned sha256', out[-1])
        parent = self.temp / 'cache/quickstop/skills-ref'
        self.assertEqual(list(parent.iterdir()) if parent.exists() else [], [])

    def test_a_cache_another_run_created_first_counts_as_success(self):
        module.fetch(self.pin, self.cache)
        module.fetch(self.pin, self.cache)
        self.assertEqual(sorted(p.name for p in self.cache.parent.iterdir()), [self.pin['commit']])

    def test_a_changed_cache_file_fails_the_next_run(self):
        self.assertEqual(self.run_check()[0], 0)
        for path in (self.cache / 'fakedep-1.0-py3-none-any.whl', self.cache / 'skills-ref/src/skills_ref/__init__.py'):
            with self.subTest(path=path.name):
                original = path.read_bytes()
                path.write_bytes(original + b'\n')
                code, out, _ = self.run_check()
                self.assertEqual(code, 1)
                self.assertIn(f'Delete {self.cache}', out[-1])
                path.write_bytes(original)

    def test_a_validator_that_passes_everything_is_refused(self):
        self.repo.config(lambda c: c['claude_code_only'].clear())
        source = self.temp / 'upstream/skills-ref/src/skills_ref/__init__.py'
        source.write_text('import fakedep\ndef validate(path):\n    return []\n')
        upstream = self.temp / 'upstream'
        git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qam', 'no-op', cwd=upstream)
        pin = dict(self.pin, commit=git('rev-parse', 'HEAD', cwd=upstream), tree=git('rev-parse', 'HEAD:skills-ref', cwd=upstream))
        self.repo.config(lambda c: c.update(skills_ref=pin))
        code, out, _ = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn('cannot be trusted', out[-1])

    def test_tree_hash_matches_git(self):
        self.assertEqual(module.tree_hash(self.temp / 'upstream/skills-ref'), self.pin['tree'])


FAKE_CLAUDE = '''#!/bin/sh
printf '%s|%s|%s|%s|%s\\n' "$*" "$HOME" "$CLAUDE_CONFIG_DIR" "$DISABLE_AUTOUPDATER" "${ANTHROPIC_API_KEY:-none}" >> "$CALLS"
exit "${FAKE_EXIT:-0}"
'''


class ClaudeValidateTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.bin = Path(temp.name) / 'bin'
        self.bin.mkdir()
        self.calls = Path(temp.name) / 'calls'
        self.repo = Repo(self)

    def run_check(self, **env):
        with patch.dict(os.environ, PATH=str(self.bin), CALLS=str(self.calls), ANTHROPIC_API_KEY='secret', **env):
            return module.run(self.repo.root, {module.SKIP_SKILLS_REF: '1'})

    def test_runs_strict_without_credentials_in_a_removed_temporary_home(self):
        claude = self.bin / 'claude'
        claude.write_text(FAKE_CLAUDE)
        claude.chmod(0o755)
        code, out, _ = self.run_check()
        self.assertEqual(code, 0, out)
        calls = [line.split('|') for line in self.calls.read_text().splitlines()]
        self.assertEqual([c[0] for c in calls], [f'plugin validate --strict {p}' for p in (
            self.repo.root, self.repo.root / 'plugins/claudit', self.repo.root / 'plugins/writing-for-humans',
            self.repo.root / 'plugins/sotsog')])
        for _, home, config, autoupdater, key in calls:
            self.assertEqual((config, autoupdater, key), (home + '/.claude', '1', 'none'))
            self.assertFalse(Path(home).exists())
        self.assertIn('claude plugin validate --strict: marketplace and 3 plugin(s) valid', out)

    def test_a_failing_validation_fails_the_check(self):
        claude = self.bin / 'claude'
        claude.write_text(FAKE_CLAUDE)
        claude.chmod(0o755)
        code, out, _ = self.run_check(FAKE_EXIT='1')
        self.assertEqual(code, 1)

    def test_missing_claude_fails_and_names_its_own_skip_variable(self):
        code, out, _ = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn(module.SKIP_CLAUDE_VALIDATE, out[-1])
        self.assertNotIn(module.SKIP_SKILLS_REF, out[-1])


class OutputTests(unittest.TestCase):
    def test_each_variable_skips_only_its_check_and_skips_print_last(self):
        repo = Repo(self)
        for skip, other in ((module.SKIP_SKILLS_REF, 'claude plugin validate'), (module.SKIP_CLAUDE_VALIDATE, 'skills-ref')):
            env = {k: v for k, v in os.environ.items() if k not in SKIP_BOTH}
            env.update({skip: '1', 'PATH': '/nonexistent', 'XDG_CACHE_HOME': str(repo.root / 'no-cache')})
            if skip == module.SKIP_CLAUDE_VALIDATE:
                env['PATH'] = os.environ['PATH']
                # Point the pin at a repository that doesn't exist, so skills-ref fails offline.
                repo.config(lambda c: c['skills_ref'].update(repository=(repo.root / 'missing').as_uri()))
            result = subprocess.run([sys.executable, str(REPO / 'bin/check-skills'), '--root', str(repo.root)],
                                    env=env, capture_output=True, text=True)
            lines = result.stdout.splitlines()
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertTrue(lines[-1].startswith('SKIPPED: ') and skip in lines[-1], lines)
            self.assertTrue(any(line.startswith(other) and 'failed' in line for line in lines[:-1]), lines)


if __name__ == '__main__':
    unittest.main()
