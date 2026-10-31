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
# Final reports from the first 4.0.1 gate run (tree af7bbfb, evals/claudit/results/4.0.1-af7bbfb-live), verbatim.
GATE_REPORTS = Path(__file__).resolve().parent / 'claudit_gate_reports'
SINCE_4_1 = ('structure-plan-items', 'structure-footer', 'structure-grade-raise')


def risky_only_bypass():
    """F3 run 2 with its bypass item saying only "risky", keeping Claudit's own `Source:` citation (review round 4, M4)."""
    lines = (GATE_REPORTS / 'f3-misconfigured-run2.md').read_text().split('\n')
    problem = next(i for i, line in enumerate(lines) if 'ignores this value' in line)
    lines[problem] = '   Problem: It gives everyone who opens the repo full bypass, which is risky.'
    lines[problem + 1] = '   Why: Bypass removes every safety prompt.'
    assert 'Source: [A value you set is ignored]' in lines[problem + 3]
    return '\n'.join(lines)


def gate_report(name, drop=()):
    """A gate report, optionally without the lines that contain any of `drop`."""
    text = (GATE_REPORTS / name).read_text()
    return '\n'.join(line for line in text.split('\n') if not any(part in line for part in drop))


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
FEWER = '2 changes are worth making: the setup already runs checks, denies secrets and enforces tests.\n\n'
FENCED_STEPS = """   ```markdown
1. Read docs/release.md.
2. Bump the version.
3. Tag the release.
## Commands
   ```
"""


def plan(count, lead='', extra='', tail=TAIL):
    return HEAD + lead + ''.join(PLAN_ITEM.format(n=n) + extra for n in range(1, count + 1)) + tail


GRADE = '## Grades\n\n- **Alignment: B** (confidence: medium). %s\n'

# name -> (reports that must pass, reports that must fail)
CORPUS = {
    'structure-plan-length': ([
        plan(3), plan(7), plan(5, tail=''), plan(3, tail='\n---\nfooter'), plan(3).rstrip('\n'),
        plan(3, lead='3 changes are worth making.\n\n'), plan(2, lead=FEWER),
        plan(0, lead='No changes are worth making: every baseline item and profile feature is in place.\n\n'),
        plan(1, lead='Only 1 change is worth making \u2014 everything else is already in place.\n\n'),
        plan(2, lead='Fewer than three changes are worth making here: everything else is already in place.\n\n'),
        plan(1, lead='1 change is worth making. The setup is already well fitted to a project this small.\n\n'),
        plan(3, extra=FENCED_STEPS), plan(2, lead='**' + FEWER.replace(': ', ':** ', 1)),
        HEAD.replace('## Top changes', '## Top changes (ranked)') + PLAN_ITEM.format(n=1) * 3 + TAIL,
        HEAD + ''.join('### %d. Change\nProblem: x.\n\n' % n for n in range(1, 5)) + TAIL,
        HEAD + ''.join('**%d. Change**\nProblem: x.\n\n' % n for n in range(1, 4)) + TAIL,
        HEAD + ''.join('%d) Change\n' % n for n in range(1, 4)) + TAIL,
        # Review round 1 (L2): heading, count-line and list variants that must pass.
        HEAD.replace('## Top changes', '## Top changes:') + PLAN_ITEM.format(n=1) * 3 + TAIL,
        HEAD.replace('## Top changes', '## Top 3 changes') + PLAN_ITEM.format(n=1) * 3 + TAIL,
        HEAD.replace('## Top changes', '## The top changes') + PLAN_ITEM.format(n=1) * 3 + TAIL,
        plan(2, lead='Just 2 changes are worth making: the setup is otherwise sound for a repo this small.\n\n'),
        plan(2, lead='2 changes worth making: the setup is otherwise sound for a repo this small.\n\n'),
        plan(2, lead='*2 changes are worth making:* the setup is otherwise sound for a repo this small.\n\n'),
        plan(2, lead='> 2 changes are worth making: the setup is otherwise sound for a repo this small.\n\n'),
        plan(4, tail='\nWhich should I apply?\n1. All\n2. Only 1 and 2\n3. None\n4. Let me pick\n'),
        plan(3, tail='\n---\n1. footer line that looks numbered\n2. another\n3. a third\n4. a fourth\n5. fifth\n'),
    ], [
        plan(2), plan(8), plan(0), plan(1),
        plan(3, lead=FEWER), plan(3, lead='**' + FEWER.replace(': ', ':** ', 1)),
        plan(2, lead='2 changes are worth making.\n\n'), plan(2, lead='5 changes are worth making.\n\n'),
        plan(2, lead='Only two changes matter here.\n\n'),
        plan(2, extra=FENCED_STEPS),
        plan(2, extra='   1. a sub-step\n   2. another\n'),
        plan(2, tail='   ```json\n1. unclosed fence\n2. still inside\n'),
        HEAD.replace('## Top changes\n\n', '') + PLAN_ITEM.format(n=1) * 3,
        'Here is what I would improve:\n\n1. Add an allowlist.\n2. Add a Stop hook.\n3. Add a skill.\n',
        plan(2, tail='\nWhich should I apply?\n1. All\n2. None\n'),
        plan(2, lead='> 2 changes are worth making.\n\n'),
        HEAD.replace('## Top changes', '## Top changes to skip') + PLAN_ITEM.format(n=1) * 2 + TAIL,
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
        '`.claude/skills/release-notes.md` won\u2019t load. Rename it to `SKILL.md` in a new `release-notes` directory.',
        'Fix `release-notes.md`: put it at `SKILL.md` under a `release-notes` folder in `.claude/skills/`.',
    ], [
        '`.claude/skills/release-notes.md` is a flat file and will not load as a skill.',
        'Move `.claude/skills/release-notes.md` to `.claude/skills/release-notes/skill.md`.',
        'Improve the release-notes skill description so Claude triggers it.',
        'Skills live in `.claude/skills/<name>/SKILL.md`.',
        '`release-notes.md` is fine; your other skill, `.claude/skills/review/SKILL.md`, is good too.',
    ]),
    'finding-write-rule': ([
        'Replace `Write(src/**)` with `Edit(src/**)`: Write rules never match.',
        '```diff\n-      "Write(src/**)",\n+      "Edit(src/**)",\n```',
        'The `Write(...)` rule is never checked; use `Edit(./src/**)`.',
        'Remove the `Write(src/**)` rule; file writes are governed by Edit rules.',
        '`Write(src/**)` never matches. Use `Edit` rules instead.',
        'Replace `Write(src/**)` with `Edit(**/src/**)`.',
        'The `Write(src/**)` allow rule does nothing; replace it with an Edit permission.',
    ], [
        '`Write(src/**)` is too broad and a security risk.',
        '`Write(src/**)` never matches.\nAdd `Edit(.env)` to the deny list.',
        'Allow `Edit(src/**)` for the formatter.',
        '`Write(src/**)` is broad.\nSeparately, consider Edit rules for docs.',
        '`Write(src/**)` is broad; remove it.',
    ]),
    'finding-claudeignore': ([
        '`.claudeignore` has no effect. Add deny rules: `Read(./.env)`, `Read(./.env.*)`, `Read(./secrets/**)`.',
        'Claude Code ignores .claudeignore.\n```json\n{"permissions": {"deny": ["Read(.env)"]}}\n```',
        'Use `Read(**/.env)` in permissions.deny instead of the .claudeignore file.',
        'Delete `.claudeignore`; it is not a Claude Code file.',
        '`.claudeignore` is not a Claude Code file.\n`git rm .claudeignore`',
        '`.claudeignore` does nothing; deny `Read(//repo/.env)` instead.',
        'Claude Code never reads `.claudeignore`. Add `Read(**/.env)` to `permissions.deny`.',
    ], [
        '`.claudeignore` is not read by Claude Code.',
        'Add `coverage/` to `.claudeignore` as well.',
        'Deny secrets: `Read(./.env)` and `Read(./secrets/**)`.',
        # Review round 1 (L1): inventory mention plus the baseline deny change, no diagnosis.
        'Files: `CLAUDE.md`, `.claude/settings.json`, `.claudeignore`, `package.json`.\n'
        '```json\n{"permissions": {"deny": ["Read(./.env)"]}}\n```',
        '`git rm .claudeignore` after you add more entries to it.',
    ]),
    'finding-project-bypass': ([
        'Problem: `.claude/settings.json` sets `permissions.defaultMode` to `bypassPermissions`; Claude Code ignores it '
        'from project settings since 2.1.257.\n   Change: Remove "defaultMode" from .claude/settings.json; users who want '
        'it set it in user settings (~/.claude/settings.json).',
        '`bypassPermissions` has no effect in the committed project file.\n```diff\n   "permissions": {\n-    '
        '"defaultMode": "bypassPermissions",\n```',
        'The defaultMode setting doesn’t take effect at project scope. Delete the defaultMode line.',
        'Take out `defaultMode`: project settings aren’t honoured for bypassPermissions.',
        '`defaultMode: bypassPermissions` only works from user or managed settings, so delete it.',
        'Claude Code skips it there. Remove `defaultMode` from `.claude/settings.json`.',
    ], [
        '`bypassPermissions` is dangerous for everyone who clones the repo; remove `defaultMode`.',
        '`defaultMode` is ignored in project settings; move it to `.claude/settings.local.json`.',
        'Consider whether you need permission prompts at all.',
        '`bypassPermissions` is applied to everyone; delete `defaultMode`.',
    ]),
    'finding-array-matcher': ([
        'The PostToolUse `"matcher": ["Edit", "Write"]` is invalid.\n```json\n"matcher": "Edit|Write"\n```',
        'The hook matcher is an array; use the string `Edit|Write`.',
        '`matcher` must be a string, not a list: "Edit|Write".',
        'Make the PostToolUse matcher the string "Write|Edit".',
        'The matcher is a JSON array; write it as `^(Edit|Write)$`.',
        'Use `"Edit,Write"` instead of the array matcher.',
        'Write the PostToolUse matcher as `"Edit|Write"` (matchers are strings).',
    ], [
        'The PostToolUse matcher is an array and will not fire.',
        'The lint hook runs `npm run lint` on every Edit|Write; make it faster.',
        'Hooks: add a Stop hook that runs `npm test`.',
        'The PostToolUse matcher lists Edit and Write.',
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
        # Review round 1 (M2): true statements the first version failed.
        *(GRADE % t for t in (
            'Your AGENTS.md is not ignored: Claude Code reads it because there is no CLAUDE.md.',
            'AGENTS.md is no longer ignored; since 2.1.277 Claude Code reads it directly.',
            'Claude Code before 2.1.277 doesn\'t read AGENTS.md, but you are on 2.1.314.',
            'A subagent started without project instructions doesn\'t load AGENTS.md.',
        )),
        # More true statements, my own paraphrases.
        'AGENTS.md isn\u2019t read when a `CLAUDE.md` exists, so keep it the only instruction file.',
        'Claude Code reads `AGENTS.md` here; a disabled built-in AGENTS.md plugin would stop that.',
        'AGENTS.md is loaded at session start, and nothing in it is ignored.',
        'The 8-line AGENTS.md loads; Claude Code picks it up without a CLAUDE.md.',
        'Keep AGENTS.md as the single source; Claude Code and Codex both read it.',
        'If you ever add a `CLAUDE.local.md`, import `@AGENTS.md` from it so Claude Code keeps loading it.',
        'First sessions after an upgrade from 2.1.276 can miss AGENTS.md.',
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
        # Review round 1 (M2): wrong claims the first version let through, in a Grades bullet as the reviewer ran them.
        *(GRADE % t for t in (
            'AGENTS.md is not automatically loaded by Claude Code.',
            'Claude Code does not natively read AGENTS.md.',
            'Claude Code doesn\'t recognize AGENTS.md.',
            'AGENTS.md is a convention for Codex and Cursor; Claude Code looks for CLAUDE.md.',
            'When Claude Code starts, it reads CLAUDE.md, not AGENTS.md.',
            'Claude Code ignores AGENTS.md when there is no CLAUDE.md.',
            'Claude Code only picks up CLAUDE.md.',
            'AGENTS.md is skipped by Claude Code.',
            'Without a CLAUDE.md, Claude starts each session with no project instructions.',
            'Create a CLAUDE.md containing `@AGENTS.md` so Claude Code loads your AGENTS.md.',
        )),
        # More wrong claims, my own paraphrases.
        'AGENTS.md is silently ignored by Claude Code.',
        'Claude Code doesn\u2019t look at AGENTS.md at all.',
        'Import AGENTS.md from a new CLAUDE.md so that it loads.',
        'Add a CLAUDE.md with `@AGENTS.md` so the rules reach Claude.',
        'After startup Claude Code reads only CLAUDE.md.',
        'Claude Code uses CLAUDE.md instead of AGENTS.md.',
        'Claude Code skips AGENTS.md.',
    ]),
}

# My own bypass pass after review round 1: (grader, must pass, report).
for name, passes, text in [
    ('structure-plan-length', True, plan(3, tail='') + '\n'),
    ('structure-plan-length', True, plan(7, lead='7 changes are worth making.\n\n')),
    ('structure-plan-length', False, plan(8, lead='8 changes are worth making.\n\n')),
    ('structure-plan-length', True, plan(3, extra='   Is this safe? Yes.\n')),
    ('structure-plan-length', False, plan(2, lead='2 changes are worth making:\nthe setup is sound.\n\n')),
    ('structure-plan-length', True, plan(2, lead='Two changes are worth making - the rest is already in place here.\n\n')),
    ('structure-plan-length', False, plan(2, lead='Only 2 changes are worth making: ok.\n\n')),
    ('finding-flat-skill', True, 'Move release-notes.md to .claude/skills/release-notes/SKILL.md'),
    ('finding-flat-skill', False, 'Move .claude/skills/release-notes.md somewhere skills load.'),
    ('finding-write-rule', True, '```diff\n-"Write(src/**)"\n+"Edit(./src/**)"\n```'),
    ('finding-write-rule', False, 'Edit(src/**) is already allowed.'),
    ('finding-claudeignore', True, '`.claudeignore` isn\u2019t read by Claude Code. Deny with `Read(./.env)`.'),
    ('finding-claudeignore', True, 'Claude Code has no `.claudeignore` support. Use `Read(./secrets/**)` deny rules.'),
    ('finding-claudeignore', False, 'Keep `.claudeignore` as is.\nAdd `Read(./.env)` to deny.'),
    ('finding-project-bypass', True, '`defaultMode` is ignored in project settings.\n```diff\n-  "defaultMode": "bypassPermissions",\n```'),
    ('finding-project-bypass', True, 'Remove `"defaultMode": "bypassPermissions"`: it doesn\u2019t apply from project settings.'),
    ('finding-project-bypass', False, '`defaultMode` is set to `bypassPermissions`. Remove it: it is dangerous.'),
    ('finding-array-matcher', True, 'The matcher `["Edit", "Write"]` is an array.\n```json\n{"matcher": "Edit|Write"}\n```'),
    ('finding-array-matcher', False, '`"matcher": "Edit|Write"` is fine.'),
    ('no-invented-agents-md-ignored', True, 'Claude Code reads AGENTS.md since there is no CLAUDE.md.'),
    ('no-invented-agents-md-ignored', True, 'AGENTS.md: loaded (no CLAUDE.md).'),
    ('no-invented-agents-md-ignored', True, 'A CLAUDE.md is not needed: AGENTS.md is read directly.'),
    ('no-invented-agents-md-ignored', True, 'AGENTS.md is read directly; you do not need a CLAUDE.md that imports it.'),
    ('no-invented-agents-md-ignored', True, 'Don\u2019t add a CLAUDE.md just to load AGENTS.md: it already loads.'),
    ('no-invented-agents-md-ignored', False, 'Claude Code won\u2019t pick up AGENTS.md.'),
    ('no-invented-agents-md-ignored', False, 'Claude does not read AGENTS.md by default.'),
    ('no-invented-agents-md-ignored', False, 'Only CLAUDE.md is read by Claude Code.'),
    ('no-invented-agents-md-ignored', False, 'Claude Code reads CLAUDE.md files; AGENTS.md is for other tools.'),
    ('no-invented-agents-md-ignored', False, 'Add `@AGENTS.md` to a new CLAUDE.md so Claude sees it.'),
    # Review round 2 (L6): a true sentence that must keep passing.
    ('no-invented-agents-md-ignored', True, 'AGENTS.md loads as the project instructions. Claude Code loads CLAUDE.md '
                                            'only when one exists, and there is none.'),
    ('no-invented-agents-md-ignored', True, 'Claude Code reads CLAUDE.md only if it exists; here AGENTS.md loads.'),
    ('no-invented-agents-md-ignored', True, 'Claude Code expects CLAUDE.md or AGENTS.md, and this repo has AGENTS.md.'),
    ('no-invented-agents-md-ignored', True, 'Don\u2019t rename AGENTS.md: Claude Code and Codex both read it.'),
    # Review round 2: wrong claims the reviewer found still passing that the regex now catches.
    *[('no-invented-agents-md-ignored', False, GRADE % text) for text in (
        'Your AGENTS.md instructions never make it into Claude\'s context.',
        'Claude Code expects CLAUDE.md; AGENTS.md is for other tools.',
        'Claude Code doesn\'t know about AGENTS.md.',
        'Because there is no CLAUDE.md, Claude Code has no project instructions.',
        'Rename AGENTS.md to CLAUDE.md so Claude Code reads it.',
        'Symlink CLAUDE.md to AGENTS.md so Claude Code reads it.',
        'Claude Code reads CLAUDE.md, and your project has none.',
    )],
]:
    CORPUS[name][0 if passes else 1].append(text)


# Review round 4: the three graders the first gate run missed on, with the exact run texts.
F2_EVAL_LINES = ('claude plugin eval',)
for name, passes, text in [
    # finding-plugin-eval: evals named as missing, and `claude plugin eval` recommended.
    ('finding-plugin-eval', True, gate_report('f2-plugin-repo-run1.md')),  # judge PASS/FAIL/FAIL
    ('finding-plugin-eval', True, gate_report('f2-plugin-repo-run3.md')),  # judge FAIL/FAIL/FAIL
    ('finding-plugin-eval', False, gate_report('f2-plugin-repo-run1.md', drop=F2_EVAL_LINES)),
    ('finding-plugin-eval', False, gate_report('f2-plugin-repo-run3.md', drop=F2_EVAL_LINES)),
    ('finding-plugin-eval', False, gate_report('f2-plugin-repo-run1.md', drop=('no plugin eval suite', 'no `evals/`'))),
    ('finding-plugin-eval', False, gate_report('f2-plugin-repo-run3.md', drop=('evaluates', 'no `evals/`'))),
    ('finding-plugin-eval', True, 'The plugin has no eval suite.\nAdd `evals/` cases and run `claude plugin eval` in CI.'),
    ('finding-plugin-eval', True, 'Nothing evaluates the skill; use `claude plugin eval` with an `evals/` directory.'),
    ('finding-plugin-eval', True, '`evals/` is missing. Wire `claude plugin eval` into the release checklist.'),
    ('finding-plugin-eval', False, 'Run `claude plugin eval` before each release.'),
    ('finding-plugin-eval', False, 'There is no eval suite for the skill. Add more unit tests.'),
    ('finding-plugin-eval', False, 'There are no evals.\n\nRun `claude plugin validate .` in CI.'),
    ('finding-plugin-eval', False, 'Evals are not set up.\n\n## Also worth knowing\n\n- `claude plugin eval` exists.'),
    # finding-project-bypass: the diagnosis and the fix each within one change item.
    ('finding-project-bypass', True, gate_report('f3-misconfigured-run2.md')),  # regex missed on one line
    ('finding-project-bypass', False, gate_report('f3-misconfigured-run2.md', drop=('Remove `defaultMode', 'Delete the'))),
    ('finding-project-bypass', False, gate_report('f3-misconfigured-run2.md', drop=('ignores this value', 'is ignored]('))),
    ('finding-project-bypass', True, '3. **Remove `defaultMode`**\n   Problem: it sets bypass mode.\n   Why: Claude Code '
                                     'ignores that in project settings.'),
    ('finding-project-bypass', False, '3. **Remove `defaultMode`**\n   Problem: it sets bypass mode.\n\n4. **Fix the '
                                      'matcher**\n   Problem: Claude Code ignores an array matcher.'),
    ('finding-project-bypass', False, '- `defaultMode` is set to bypass.\n- `.claude/settings.json` hooks are ignored.\n'
                                      '- Remove `defaultMode`.'),
    # finding-oversized-claude-md: one change item names CLAUDE.md, its size and a cut.
    ('finding-oversized-claude-md', True, gate_report('f3-misconfigured-run3.md')),  # judge FAIL/FAIL/FAIL
    ('finding-oversized-claude-md', False, gate_report('f3-misconfigured-run3.md', drop=('is 241 lines',))),
    ('finding-oversized-claude-md', False, gate_report('f3-misconfigured-run3.md', drop=('Cut CLAUDE.md', 'Change: reduce',
                                                                                      'Drop the'))),
    ('finding-oversized-claude-md', True, '1. **Trim CLAUDE.md**\n   Problem: CLAUDE.md is over 200 lines and restates the '
                                          'code.\n   Change: delete the per-function sections.'),
    ('finding-oversized-claude-md', True, 'CLAUDE.md (1,240 lines) should be condensed to the commands and rules.'),
    ('finding-oversized-claude-md', False, '1. **Keep CLAUDE.md under 200 lines**\n   Change: trim it as it grows.'),
    ('finding-oversized-claude-md', False, '- CLAUDE.md is 241 lines.\n- Remove `defaultMode` from settings.'),
    ('finding-oversized-claude-md', False, 'CLAUDE.md is 241 lines; that is fine for this project.'),
    # Review round 4: the citation heading is not a diagnosis (M4), and the two wordings the lows found.
    ('finding-project-bypass', False, risky_only_bypass()),
    ('finding-project-bypass', True, risky_only_bypass().replace('Bypass removes every safety prompt.',
                                                                 'Claude Code ignores it in project settings.')),
    ('finding-oversized-claude-md', True, '6. **Shrink CLAUDE.md** (Alignment, effort M)\n   Problem: CLAUDE.md is 241 lines '
                                          'of per-function notes.\n   Change: Move the per-function notes into code comments '
                                          'and keep CLAUDE.md to the commands.'),
    ('finding-oversized-claude-md', True, '6. **Shrink CLAUDE.md**\n   Problem: CLAUDE.md is 241 lines.\n   Change: Replace '
                                          'CLAUDE.md with this 15-line version.'),
    ('finding-oversized-claude-md', False, '6. **Move CLAUDE.md**\n   Problem: CLAUDE.md is 241 lines.\n   Change: Move it to '
                                           '`.claude/CLAUDE.md`.'),
    ('finding-oversized-claude-md', False, 'CLAUDE.md is 241 lines; keep it as is.'),
    ('finding-oversized-claude-md', False, 'CLAUDE.md is 241 lines. Replace the `Write(src/**)` rule with `Edit(src/**)`.'),
    ('finding-plugin-eval', True, 'There is no `evals/` directory.\n\n4. **Gate on evals**\n   Change: adopt '
                                  '`claude plugin eval` as the release gate.'),
    ('finding-plugin-eval', True, 'The skill has no evals.\n\n4. **Add evals**\n   Change: write cases in `evals/` and '
                                  'check them with `claude plugin eval`.'),
    ('finding-plugin-eval', False, 'There are no evals. `claude plugin eval` is not something this repo needs.'),
    # My own bypass pass after review round 4 (citation lines, move/replace/keep cuts, more recommend verbs).
    ("finding-project-bypass", True, "3. **Remove `defaultMode`**\n   Problem: `defaultMode` has no effect in project settings.\n   Change: delete it.\n   Source: [Permission modes](https://x)"),
    ("finding-project-bypass", False, "3. **Remove `defaultMode`**\n   Problem: `bypassPermissions` is dangerous.\n   Change: delete `defaultMode`.\n   Source: [`defaultMode` is ignored in project settings](https://x)"),
    ("finding-project-bypass", True, "3. **Remove `defaultMode`**\n   Source: [docs](https://x)\n   Problem: Claude Code ignores `defaultMode` here.\n   Change: delete it."),
    ("finding-oversized-claude-md", True, "- CLAUDE.md is 241 lines: move the detailed sections out to docs/ and keep CLAUDE.md to the rules."),
    ("finding-oversized-claude-md", True, "- CLAUDE.md is 241 lines; replace it with a shorter version."),
    ("finding-oversized-claude-md", True, "- CLAUDE.md is 241 lines; keep it under 120."),
    ("finding-oversized-claude-md", False, "- CLAUDE.md is 241 lines; move the file to `.claude/CLAUDE.md`."),
    ("finding-oversized-claude-md", False, "- CLAUDE.md is 241 lines; replace `@AGENTS.md` with the real path."),
    ("finding-oversized-claude-md", False, "- CLAUDE.md is 241 lines; keep CLAUDE.md as the single source."),
    ("finding-plugin-eval", True, "No evals cover the skill.\n\n2. **Evals**\n   Change: test the skill with `claude plugin eval`."),
    ("finding-plugin-eval", True, "Nothing measures the skill: there are no evals.\n\n2. **Evals**\n   Change: verify it with `claude plugin eval` before release."),
    ("finding-plugin-eval", False, "2. **Evals**\n   Change: check them with `claude plugin eval`."),
    # My own bypass pass on the three round-4 graders.
    ('finding-plugin-eval', True, '2. **Measure the skill**\n   Problem: the skill is never evaluated.\n   Change: create `evals/changelog-entry/` and run `claude plugin eval .` in CI.'),
    ('finding-plugin-eval', True, 'Coverage: no evals. Add an eval suite under evals/ and gate releases on `claude plugin eval`.'),
    ('finding-plugin-eval', True, 'Problem: The repo lacks an eval directory.\nChange: `claude plugin eval` with cases in `evals/`; run it in CI.'),
    ('finding-plugin-eval', True, 'Without evals, skill regressions slip through. Add `claude plugin eval` to `ci.yml`.'),
    ('finding-plugin-eval', False, 'Evals exist under `evals/`. Run `claude plugin eval` in CI.'),
    ('finding-plugin-eval', False, 'No CI workflow. Run `claude plugin validate .` in CI.'),
    ('finding-plugin-eval', False, 'Optional: someday look at `claude plugin eval`.\nThere are no evals.'),
    ('finding-plugin-eval', False, 'The skill is not tested by `claude plugin evaluate`.'),
    ('finding-project-bypass', True, '### 2. Drop defaultMode\n\nProblem: `bypassPermissions` in `.claude/settings.json` has no effect at project scope.\n\nChange: remove the key.'),
    ('finding-project-bypass', True, '| `.claude/settings.json` | `defaultMode: bypassPermissions` is ignored here; remove it |'),
    ('finding-project-bypass', True, '2. **Project bypass**\n   Problem: `defaultMode` is `bypassPermissions`.\n   ```json\n   {"permissions": {}}\n   ```\n   Why: it is ignored in project settings, so delete `defaultMode`.'),
    ('finding-project-bypass', False, '2. **Project bypass**\n   Problem: `defaultMode` is `bypassPermissions`, which skips every prompt.\n   Change: remove `defaultMode`.'),
    ('finding-project-bypass', False, 'Your `defaultMode` is `bypassPermissions`.\n\nThis is ignored by most teams. Nothing to change.'),
    ('finding-oversized-claude-md', True, '6. **Cut CLAUDE.md**\n   Problem: at 241 lines it repeats the code.\n   ```diff\n-  ## toCents\n   ```\n   Change: delete the function sections.'),
    ('finding-oversized-claude-md', True, '- `CLAUDE.md` is 241 lines, well past the 200-line target; trim it to commands and rules.'),
    ('finding-oversized-claude-md', True, '### Shorten CLAUDE.md\n\nCLAUDE.md has 241 lines. Reduce it to what the code cannot say.'),
    ('finding-oversized-claude-md', False, 'CLAUDE.md is 241 lines.\n\nRemove the `Write(src/**)` rule.'),
    ('finding-oversized-claude-md', False, '- CLAUDE.md: 41 lines; trim the stale section.'),
    ('finding-oversized-claude-md', False, '- README.md is 241 lines; cut it.'),
    # Issue #174 (the 4.0.2 lows from #168): other citation forms and link text never diagnose, and
    # "keep only the commands" is a cut.
    *[('finding-project-bypass', False, risky_only_bypass().replace('   Source: [A value', form + ' [A value'))
      for form in ('   **Source:**', '   - Source:', '   Sources:', '   _Source_:', '   > Source :', '   *Source:*')],
    ('finding-project-bypass', False, '2. **Remove `defaultMode`**\n   Problem: `bypassPermissions` is risky; see '
                                      '[A value you set is ignored](https://code.claude.com/docs/en/settings).\n'
                                      '   Change: delete `defaultMode`.'),
    ('finding-project-bypass', False, '2. **Remove `defaultMode`**\n   Problem: `bypassPermissions` is risky.\n'
                                      '   Change: delete `defaultMode`. Source: [A value you set is ignored]'
                                      '(https://code.claude.com/docs/en/settings)'),
    ('finding-project-bypass', True, '2. **Remove `defaultMode`**\n   Problem: Claude Code ignores `bypassPermissions` '
                                     'here ([A value you set is ignored](https://code.claude.com/docs/en/settings)).\n'
                                     '   Change: delete `defaultMode`.'),
    ('finding-project-bypass', True, risky_only_bypass().replace('   Source: [A value', '   **Source:** [A value').replace(
        'Bypass removes every safety prompt.', 'Claude Code ignores it in project settings.')),
    ('finding-oversized-claude-md', True, '6. **Trim CLAUDE.md** (Alignment, effort M)\n   Problem: CLAUDE.md is 241 '
                                          'lines.\n   Change: keep only the commands and the five rules the code '
                                          'can\'t show.'),
    ('finding-oversized-claude-md', True, '- `CLAUDE.md` is 241 lines; leave just the commands and gotchas.'),
    ('finding-oversized-claude-md', True, '- `CLAUDE.md` is over 200 lines; keep it to only the commands.'),
    ('finding-oversized-claude-md', False, '- `CLAUDE.md` is 241 lines.\n- Keep only the commands in README.md.'),
    ('finding-oversized-claude-md', False, '- `CLAUDE.md` is 241 lines; keep it.'),
]:
    CORPUS.setdefault(name, ([], []))[0 if passes else 1].append(text)


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

    def test_first_gate_reports_pass_every_regex_grader(self):
        # All 18 live reports from tree af7bbfb; the 4 recorded misses were grader false negatives.
        # Graders for 4.1 targets (the scan's plan, footer and grade explanations) postdate them.
        reports = sorted(GATE_REPORTS.glob('*.md'))
        self.assertEqual(len(reports), 18)
        for report in reports:
            case = report.name.rsplit('-run', 1)[0]
            for path in sorted((CASES / case / 'graders').glob('*.md')):
                if 'type: regex' in path.read_text().split('\n---\n', 1)[0] and path.stem not in SINCE_4_1:
                    with self.subTest(report=report.name, grader=path.stem):
                        self.assertTrue(verdict(regex_grader(path), report.read_text()))

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
