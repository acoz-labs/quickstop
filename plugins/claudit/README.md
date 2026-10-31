# Claudit

Claudit grades a project's Claude Code setup against what the project is for, then
recommends the few changes that would improve it most and can apply the ones you pick.

## Installation

From the Quickstop marketplace in Claude Code:

```text
/plugin install claudit@quickstop
```

For local development, load the checkout with
`claude --plugin-dir /path/to/quickstop/plugins/claudit`. The marketplace advertises
only the accepted release; a development checkout can contain a newer candidate.

## Use

```text
/claudit:claudit                  # audit this project, then offer to apply changes
/claudit:claudit hooks            # same, with a deeper look at hooks
/claudit:claudit --read-only      # report only
/claudit:claudit --user           # also check your ~/.claude settings and CLAUDE.md
```

Asking Claude to audit or improve the Claude Code setup also invokes it.

## What you get

1. **Intent**: what the project builds, how work gets done (check and CI commands,
   procedure docs, release flow) and who drives it. Interactive runs ask you to
   confirm or correct it once; headless runs state the assumption.
2. **Three grades**, each a letter with a confidence:
   - **Correctness**: does what's configured work?
   - **Alignment**: does it serve the project's intent?
   - **Coverage**: what's missing that a project like this should have? Graded
     against a baseline every project should meet (a short CLAUDE.md, a check Claude
     can run, routine commands pre-approved, secret paths denied, must-always rules
     enforced by hooks or permissions) plus profiles picked from project signals:
     agent-run repository, plugin or marketplace repository, typed codebase,
     repository with procedure docs.
   A grade below A names the changes that would raise it.
3. **The top changes**, ranked by impact across the three grades, up to seven. Each
   has the reason, the exact diff or command, the doc URL and heading it rests on,
   and the effort. When nothing is worth changing, the report says "No changes worth
   making", which is a valid result with Coverage A.
4. **Declined by the project**: features the project documents a deliberate choice
   against, quoted with their file and line. Claudit doesn't recommend them or count
   them against Coverage.
5. **An offer to apply** the changes you select, in place or on a branch in an
   isolated worktree with a pull request through `gh`.

Process detail stays in a short footer. Its first line gives the Claudit version and
the audited commit (or "not a git repo"), so a report can be reproduced; it also
lists Claude Code documentation pages that are newer than Claudit's feature catalog.

## Same tree, same result

The scan, not the model, decides the grade letters, which findings become changes,
their order and how many there are. The model writes the intent, the explanations
and the diffs. The rules:

- **Plan.** Findings of one kind on one file are one change. Changes are ranked by
  severity (high, medium, low), then grade (Correctness, Alignment, Coverage), then
  finding id. The first seven are the plan; any more go under Also worth knowing.
  Fewer than three come with the reason; the plan is never padded.
- **Grades.** Correctness and Alignment: F for configuration that doesn't load
  (invalid JSON or a hook matcher that isn't a string; Correctness only), D for a high finding or several mediums, C for one medium, B
  for lows only, A for none; a project with no instruction file gets an Alignment
  medium. Coverage: A, B, C or D for 0, 1, 2 or 3 or more gaps, and F with no setup
  at all.
- **Procedures already reachable are optional.** A procedure doc that loaded
  team instructions (CLAUDE.md, AGENTS.md or their imports, not the personal
  CLAUDE.local.md) already link, as a Markdown
  link or a bare or backticked path, is reachable, so a skill for it is optional
  rather than a change. It becomes a change when the doc, or the line linking it,
  says the procedure should be invoked on demand ("on demand" with "skill", "slash
  command" or "invoke" in the doc). A doc that a skill anywhere in the repository
  links (a plugin's skill, for example) is that skill's reference material, not a
  team procedure.
- **Test data isn't configuration.** Files below a directory whose name contains
  one of the words fixture(s), testdata, golden(s), snapshot(s), cassette(s),
  eval(s), grader(s), report(s) or result(s), below a test or tests directory, or
  inside an eval case (a directory with `case.yaml`) are data. They are never read
  as procedures, plugin manifests, typed-code markers or secrets. Names are split
  at punctuation and case changes and compared case-insensitively, so
  `claudit_gate_reports`, `__fixtures__` and `TestData` all count; symlinks are
  judged by their target too. A test directory's own `CLAUDE.md` is still an
  instruction file. Anything else the tests load can be dismissed.
- **Documented declines.** Claudit reads the loaded team instructions, the Markdown
  files they link and the README. A sentence declines a feature (hooks, plugin evals,
  plugin validation, pre-approved commands, procedure skills, code intelligence)
  when a word such as retired, removed, dropped, declined, abandoned, disabled,
  decided against or chose not to sits next to it, or when it is negated ("no eval
  campaign") in a sentence that says the choice is deliberate (deliberately,
  intentionally, by design, by choice, decided, decision, policy). Sentences that
  are questions, conditional, future, negated or reversed ("if", "will be", "weren't
  removed", "restored") don't count, nor do sentences about another tool (Git hooks,
  Cursor skills) that don't name Claude.

## How it works

- `skills/claudit/scripts/claudit.py` scans the project: inventory, project signals,
  and the misconfigurations the docs name (for example `Write(...)` path rules,
  `.claudeignore`, flat skill files, project `bypassPermissions`, array hook
  matchers, oversized CLAUDE.md, broken `@` imports and stale paths). It also
  reports which instruction files load (`CLAUDE.md`, `AGENTS.md` or both), and the
  report takes that from the scan rather than stating it from memory. It is
  read-only and needs only the standard library of Python 3.9 or later.
- `skills/claudit/catalog.json` is the versioned feature catalog: each feature, the
  intent it fits, how to tell it's in use, its doc URL and heading, and its minimum
  Claude Code version. It carries every check and recommendation, so an audit works
  with the docs unreachable.
- Each audit reads `https://code.claude.com/docs/llms.txt` and at most a couple of
  pages live with WebFetch (pre-approved for `code.claude.com` while the skill runs),
  cites the URL and heading for each claim, and lists index pages the catalog
  doesn't know yet.
- One read-only Sonnet `auditor` agent handles cross-file review on large setups;
  small repositories don't use it. The skill itself runs on Sonnet.
- Claudit points you to the native checks it can't run for you: `/doctor`,
  `/doctor prompt-audit`, `/insights` and `/skill-doctor`.

## State and writes

Claudit keeps no cache and writes nothing outside the project. An audit writes
nothing at all. It writes only when you apply changes, or when you ask it not to
repeat a suggestion: that goes in `.claude/claudit-dismissed.json` in the project.

## Requirements

Tested with Claude Code 2.1.312. `python3` 3.9 or later; without it Claudit reads the
files itself at lower confidence. Git for branch delivery and `gh` for pull requests.

## Upgrading from 3.x

4.0 removes the `knowledge`, `refresh` and `status` skills, the three research and
three audit agents, the docs cache and the decision store. Old files under
`~/.cache/claudit` (or `CLAUDIT_CACHE_DIR`) are no longer read; delete them when you
no longer need them. Project `.claude/claudit-decisions*.json` files are ignored.

MIT licensed; see [LICENSE](LICENSE).
