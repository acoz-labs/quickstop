"""Script-graded eval checks: each regex grader against reports that must pass and must fail.

The graders run as JavaScript regexes inside `claude plugin eval`. These cases run them with
Python's re (the patterns use the subset both engines share) and, when node is installed,
with node too, so a pattern that behaves differently in the two engines fails here.
"""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / 'evals/claudit/cases'


def regex_grader(path):
    head = path.read_text().split('\n---\n', 1)[0].splitlines()[1:]
    fields = {}
    for line in head:
        key, _, value = line.partition(': ')
        if len(value) > 1 and value[0] == value[-1] == "'":
            value = value[1:-1].replace("''", "'")
        fields[key] = value
    assert fields['type'] == 'regex', path
    return fields


def verdict(grader, text):
    found = re.search(grader['pattern'], text, re.I if 'i' in grader.get('flags', '') else 0) is not None
    return found != (grader.get('match') == 'not_contains')


def js_verdicts(checks):
    script = ("const checks = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
              "process.stdout.write(JSON.stringify(checks.map(([p, f, m, t]) =>"
              " new RegExp(p, f).test(t) !== (m === 'not_contains'))));")
    out = subprocess.run(['node', '-e', script], input=json.dumps(checks), capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


PLAN_ITEM = """{n}. **Change {n}** (Coverage, effort S)
   Problem: `.claude/settings.json` doesn't exist, so every run of `bin/check` prompts.
   Why: checks run on every task.
   Change: create `.claude/settings.json`:
   ```json
   {{"permissions": {{"allow": ["Bash(bin/check)"]}}}}
   ```
   Source: [Permission rule syntax](https://code.claude.com/docs/en/permissions)
"""
HEAD = """# Claudit: csvsum

**Intent:** A small library. Assumed from the repository; correct me if wrong.

## Grades

- **Correctness: A** (confidence: high). No defects.

## Top changes

"""
TAIL = """
## Also worth knowing

- Optional: run `/doctor` now and then.

---
Claude Code 2.1.314, catalog 2026-10-29.
"""
FEWER = 'Fewer than 3 changes are worth making: the setup already runs checks, denies secrets and enforces tests.\n\n'
FENCED_STEPS = """   ```markdown
1. Read docs/release.md.
2. Bump the version.
3. Tag the release.
## Commands
   ```
"""


def plan(count, lead='', extra='', tail=TAIL):
    return HEAD + lead + ''.join(PLAN_ITEM.format(n=n) + extra for n in range(1, count + 1)) + tail


# name -> (reports that must pass, reports that must fail)
CORPUS = {
    'structure-plan-length': ([
        plan(3), plan(7), plan(5, tail=''), plan(3, tail='\n---\nfooter'), plan(3).rstrip('\n'),
        plan(2, lead=FEWER), plan(0, lead=FEWER), plan(1, lead='Fewer than three changes are worth making here — '
                                                               'everything else is already in place.\n\n'),
        plan(3, extra=FENCED_STEPS), plan(2, lead='**' + FEWER.replace(': ', ':** ', 1)),
        HEAD.replace('## Top changes', '## Top changes (ranked)') + PLAN_ITEM.format(n=1) * 3 + TAIL,
        HEAD + ''.join('### %d. Change\nProblem: x.\n\n' % n for n in range(1, 5)) + TAIL,
        HEAD + ''.join('**%d. Change**\nProblem: x.\n\n' % n for n in range(1, 4)) + TAIL,
        HEAD + ''.join('%d) Change\n' % n for n in range(1, 4)) + TAIL,
    ], [
        plan(2), plan(8), plan(0), plan(1),
        plan(3, lead=FEWER), plan(3, lead='**' + FEWER.replace(': ', ':** ', 1)), plan(2, lead='Fewer than 3 changes are worth making.\n\n'),
        plan(2, lead='Only two changes matter here.\n\n'),
        plan(2, extra=FENCED_STEPS),
        plan(2, extra='   1. a sub-step\n   2. another\n'),
        plan(2, tail='   ```json\n1. unclosed fence\n2. still inside\n'),
        HEAD.replace('## Top changes\n\n', '') + PLAN_ITEM.format(n=1) * 3,
        'Here is what I would improve:\n\n1. Add an allowlist.\n2. Add a Stop hook.\n3. Add a skill.\n',
    ]),
    'finding-flat-skill': ([
        # The 4.0.0 verified grader false negative (#156), verbatim.
        '4. **Make the release-notes skill loadable** (Correctness, effort S)\n   Problem: `.claude/skills/release-notes.md`'
        ' is a flat file. Skills load only from `<name>/SKILL.md`, so the skill that `CLAUDE.md` tells Claude to use never '
        'loads.\n   ...\n   `mkdir .claude/skills/release-notes && git mv .claude/skills/release-notes.md '
        '.claude/skills/release-notes/SKILL.md`\n   Source: [Choose where skills load](https://code.claude.com/docs/en/skills)',
        'Move `./.claude/skills/release-notes.md` to `./.claude/skills/release-notes/SKILL.md`.',
        'The flat `release-notes.md` won’t load: move it into `.claude/skills/release-notes/` as `SKILL.md`.',
        'Put `release-notes.md` in a `release-notes` directory with a `SKILL.md` file.',
        'Rename it to SKILL.md inside .claude/skills/release-notes/ (it is now release-notes.md).',
        'Or move `.claude/skills/release-notes.md` to `.claude/commands/release-notes.md`.',
    ], [
        '`.claude/skills/release-notes.md` is a flat file and will not load as a skill.',
        'Move `.claude/skills/release-notes.md` to `.claude/skills/release-notes/skill.md`.',
        'Improve the release-notes skill description so Claude triggers it.',
        'Skills live in `.claude/skills/<name>/SKILL.md`.',
    ]),
    'finding-write-rule': ([
        'Replace `Write(src/**)` with `Edit(src/**)`: Write rules never match.',
        '```diff\n-      "Write(src/**)",\n+      "Edit(src/**)",\n```',
        'The `Write(...)` rule is never checked; use `Edit(./src/**)`.',
        'Remove the `Write(src/**)` rule; file writes are governed by Edit rules.',
    ], [
        '`Write(src/**)` is too broad and a security risk.',
        '`Write(src/**)` never matches.\nAdd `Edit(.env)` to the deny list.',
        'Allow `Edit(src/**)` for the formatter.',
    ]),
    'finding-claudeignore': ([
        '`.claudeignore` has no effect. Add deny rules: `Read(./.env)`, `Read(./.env.*)`, `Read(./secrets/**)`.',
        'Claude Code ignores .claudeignore.\n```json\n{"permissions": {"deny": ["Read(.env)"]}}\n```',
        'Use `Read(**/.env)` in permissions.deny instead of the .claudeignore file.',
        'Delete `.claudeignore`; it is not a Claude Code file.',
        '`git rm .claudeignore`',
    ], [
        '`.claudeignore` is not read by Claude Code.',
        'Add `coverage/` to `.claudeignore` as well.',
        'Deny secrets: `Read(./.env)` and `Read(./secrets/**)`.',
    ]),
    'finding-project-bypass': ([
        'Problem: `.claude/settings.json` sets `permissions.defaultMode` to `bypassPermissions`; Claude Code ignores it '
        'from project settings since 2.1.257.\n   Change: Remove "defaultMode" from .claude/settings.json; users who want '
        'it set it in user settings (~/.claude/settings.json).',
        '`bypassPermissions` has no effect in the committed project file.\n```diff\n   "permissions": {\n-    '
        '"defaultMode": "bypassPermissions",\n```',
        'The defaultMode setting doesn’t take effect at project scope. Delete the defaultMode line.',
        'Take out `defaultMode`: project settings aren’t honoured for bypassPermissions.',
    ], [
        '`bypassPermissions` is dangerous for everyone who clones the repo; remove `defaultMode`.',
        '`defaultMode` is ignored in project settings; move it to `.claude/settings.local.json`.',
        'Consider whether you need permission prompts at all.',
    ]),
    'finding-array-matcher': ([
        'The PostToolUse `"matcher": ["Edit", "Write"]` is invalid.\n```json\n"matcher": "Edit|Write"\n```',
        'The hook matcher is an array; use the string `Edit|Write`.',
        '`matcher` must be a string, not a list: "Edit|Write".',
        'Make the PostToolUse matcher the string "Write|Edit".',
        'The matcher is a JSON array; write it as `^(Edit|Write)$`.',
        'Use `"Edit,Write"` instead of the array matcher.',
    ], [
        'The PostToolUse matcher is an array and will not fire.',
        'The lint hook runs `npm run lint` on every Edit|Write; make it faster.',
        'Hooks: add a Stop hook that runs `npm test`.',
    ]),
    'no-invented-agents-md-ignored': ([
        'Loaded at session start: AGENTS.md (read directly: no CLAUDE.md, .claude/CLAUDE.md or CLAUDE.local.md; adding '
        'one stops that unless it imports this file).',
        '`AGENTS.md` loads as the project instructions because there is no `CLAUDE.md`.',
        'Adding a `CLAUDE.md` would stop `AGENTS.md` loading unless it imports `@AGENTS.md`.',
        'If you add a CLAUDE.local.md, AGENTS.md is no longer read for you.',
        'Once a `CLAUDE.md` exists, Claude Code doesn’t read `AGENTS.md` unless it is imported.',
        'Claude Code reads AGENTS.md directly (2.1.277 and later). It is short and current.',
        "There's no CLAUDE.md, so Claude Code reads AGENTS.md.",
        'Claude Code loads CLAUDE.md or, when there is none, AGENTS.md.',
        '| AGENTS.md | 8 lines | loaded |',
        '```markdown\n@AGENTS.md\n```\nThe `.claudeignore` file is ignored.',
        'AGENTS.md is short (8 lines) and points at files that exist. Nothing is ignored.',
        'AGENTS.md holds shared rules, not Claude-specific ones.',
    ], [
        'Claude Code reads `CLAUDE.md`, not `AGENTS.md`, so these instructions may not load unless a `CLAUDE.md` '
        'imports them.',
        'Claude Code loads `CLAUDE.md`, so the delivery rules may not reach Claude sessions here.',
        '`AGENTS.md` is not loaded by Claude Code.',
        'Your **AGENTS.md** isn’t read by Claude Code.',
        'Claude Code ignores `AGENTS.md`.',
        "Claude Code doesn't read AGENTS.md; add a CLAUDE.md that imports it.",
        'Note: Claude Code only reads CLAUDE.md.',
        'Your AGENTS.md is invisible to Claude Code.',
        '- `AGENTS.md` won’t load in Claude Code sessions',
        'Claude reads CLAUDE.md rather than AGENTS.md.',
        'AGENTS.md has no effect on Claude Code sessions.',
        'AGENTS.md is for Codex, not Claude Code.',
        'Without an import, AGENTS.md is not picked up.',
    ]),
}


class GraderPatternTests(unittest.TestCase):
    def graders(self):
        out = {}
        for name in CORPUS:
            paths = sorted(CASES.glob('*/graders/%s.md' % name))
            self.assertTrue(paths, name)
            texts = {path.read_text() for path in paths}
            self.assertEqual(len(texts), 1, '%s differs between cases' % name)
            out[name] = regex_grader(paths[0])
        return out

    def test_regex_graders_pass_and_fail_the_corpus(self):
        for name, grader in self.graders().items():
            passing, failing = CORPUS[name]
            for text in passing:
                with self.subTest(grader=name, expect='pass', report=text[:80]):
                    self.assertTrue(verdict(grader, text))
            for text in failing:
                with self.subTest(grader=name, expect='fail', report=text[:80]):
                    self.assertFalse(verdict(grader, text))

    def test_patterns_use_only_the_shared_regex_subset(self):
        for name, grader in self.graders().items():
            with self.subTest(grader=name):
                self.assertNotRegex(grader['pattern'], r'\(\?[iPmsx<]|\\[AZz]|\(\?<[=!]')
                self.assertLessEqual(set(grader.get('flags', '')), {'i'})
                self.assertIn(grader.get('match', 'contains'), ('contains', 'not_contains'))

    @unittest.skipUnless(shutil.which('node'), 'node not installed')
    def test_javascript_engine_agrees(self):
        checks, expected = [], []
        for name, grader in self.graders().items():
            for want, texts in zip((True, False), CORPUS[name]):
                for text in texts:
                    checks.append([grader['pattern'], grader.get('flags', ''), grader.get('match', ''), text])
                    expected.append(want)
        self.assertEqual(js_verdicts(checks), expected)

    def test_every_case_grades_plan_length(self):
        for case in sorted(p for p in CASES.iterdir() if p.is_dir()):
            with self.subTest(case=case.name):
                self.assertTrue((case / 'graders/structure-plan-length.md').is_file())


if __name__ == '__main__':
    unittest.main()
