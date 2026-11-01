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
   against, quoted with their file and line and the reason the project gives (or "no
   reason given"). Claudit doesn't recommend them or count them against Coverage. A
   declined item gets a "Worth reconsidering" note only when Claudit can cite evidence
   that the stated reason no longer holds.
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
- **Only commands written as calls are pre-approved.** Which test runner or check a
  project uses is read from every mention. Which exact calls the allowlist suggests,
  and whether a gap is counted, come only from these forms, and nothing else:
  1. **Code blocks.** Each line of a fenced block with no language or a shell one
     (sh, bash, zsh, shell, powershell, …). In a `console`, `shell-session` or
     `terminal` block, only its prompt lines. Each line of an indented code block
     that doesn't continue a list item.
  2. **Prompt lines.** A line starting with `$ ` or `% `, or `> ` followed only by a
     command and flag or path arguments (`> bin/ci --fast`, not `> bin/ci is slow`).
  3. **List leads.** A list item that starts with a backticked command followed by
     the end of the line, `:`, a dash or `(` ("- `bin/ci`: runs the suite").
  4. **Table cells.** A cell that is exactly one backticked command.
  5. **Instructions.** A backticked command after run, execute, invoke or call
     (directly, after "the command", or after up to four words and with/using/via:
     "Run the tests with `x`"). The run word must start a sentence, clause, list
     item, quote, table cell or label ("Tests: run with `x`"), or follow
     please/then/first/also/always/now/just/next/finally, "make sure to", "remember
     to", "be sure to", or you/we/agents/contributors/maintainers + can/must/should/
     may/need to/have to. A run phrase may wrap onto the next line.
  6. **Labels.** A backticked command after "Commands:", "Checks:", "Test(s):",
     "Usage:", "Verify:", "Validation:", "Lint:" or "Build:".
  7. **Chains.** Commands joined to a counted one by a comma, and, or, then or
     "(or", and a run word coordinated with one ("Execute `a`, invoke `b` or call
     `c`").

  These never count:
  - A run word after never, not, don't, doesn't, avoid or "no need to", with an
    optional ever/even/again/once ("Don't ever run `x`").
  - A run word with will, would, could, might, shall, does, did, "used to" or
    "automatically" earlier in its sentence ("CI will run `x`", "The hook will call
    `x`").
  - Any form whose command is followed by is, was, were, has been, used to, no
    longer, removed, deprecated, obsolete, gone, replaced, broken, don't, never or
    do not, or a table row saying no longer/deprecated/obsolete/removed/is gone/used
    to/don't run/never run/do not run.
  - Headings, and inline code anywhere else ("`bin/ci` finds the pinned Python",
    "use `x`", "CI runs `x`", "Running `x`").

  Mutating calls (`--write`, `apply`, `release`) and placeholder arguments
  (`PRE_CHANGE_SHA`, `<sha>`) are never suggested, and no suggestion uses a
  wildcard. An unlabelled fence counts as commands, so put output in a `text` or
  `console` fence.
- **Procedures already reachable are optional.** A procedure doc that loaded team
  instructions (CLAUDE.md, AGENTS.md or their imports, not the personal
  CLAUDE.local.md) already link, as a Markdown link or a bare or backticked path, is
  reachable, so a skill for it is optional rather than a change. It becomes a change
  when the doc, or the line linking it, says it should be invoked on demand: "on
  demand" together with "skill", "slash command" or "invoke" on the same line. A doc
  a plugin's skill links (a `SKILL.md` under `skills/` beside `.claude-plugin/` or
  `.codex-plugin/`, or in a skill directory the manifest names) is that skill's
  reference material, not a team procedure. A skill elsewhere (`.cursor/skills/`,
  `.agents/skills/`) doesn't count, so the doc is still a procedure with no project
  skill.
- **Test data isn't configuration.** A directory name is split into words at
  punctuation and case changes, compared case-insensitively, with trailing digits
  dropped. A name with test or tests as a whole word is a test directory (`tests`,
  `e2e-tests`, `tests_old`, `TestCases`); one with fixture(s), testdata, golden(s),
  snapshot(s), cassette(s), eval(s) or grader(s) is a data directory (`fixtures`,
  `__snapshots__`, `golden-files`, `evals-v2`). A word inside a word doesn't count
  (`testimonials`, `attest`, `latest`), and reports, results or data alone aren't
  data (`docs/reports` is scanned). Files below a test or data directory, or inside an
  eval case (a directory with `case.yaml`), are data. They are never read as
  procedures, plugin manifests, typed-code markers or secrets. A plugin root (a
  directory holding `.claude-plugin/` or `.codex-plugin/`) is never data because of its
  own name, so `plugins/test-runner` is scanned. Symlinks are judged by their target
  too, and a test directory's own `CLAUDE.md` is still an instruction file. Anything
  else the tests load can be dismissed.
- **Documented declines.** Claudit reads the loaded team instructions, the Markdown
  files they link and the README. A sentence declines a feature (hooks, plugin evals,
  plugin validation, pre-approved commands, procedure skills, code intelligence) only
  when the feature itself is declined, named as a bare noun with at most an article,
  owner or kind ("Claude Code hooks", "the allowlist", "Stop hooks"):
  - as the subject of retired, removed, dropped, declined, abandoned, phased out or
    disabled ("Claude Code hooks were retired", "Hooks: retired");
  - as the object of the same verbs, decided against, chose not to use or add, or
    opted out of, said by "we", "this repository", "the project" or "maintainers";
  - or as a deliberate absence: "no" or "without" the feature in a clause that says
    deliberately, intentionally, on purpose, by design or by choice.

  After the decline (and an optional "in this repository" or "here"), the sentence
  must end or give a reason: "because", "since", "in favour of", ", so", ", and
  replaced them with", "by design", or a clause after ";" or ":". A sentence with an
  exception, limit, partial scope, time limit or reversal anywhere (except, apart
  from, but, only, for now, temporarily, then, back, still, some, most, re-add,
  enable, replaced by, a new one) is never a decline. So a specific instance ("the
  old SessionStart hook was removed"), an item in it ("we removed `rm` from the
  allowlist"), a scope ("disabled in CI", "dropped from CI", "secrets in hooks") or a
  limit ("removed, for now") is not a decline, and the quote is the whole sentence.
  Questions, conditionals, future, negated or reversed sentences ("if", "will be",
  "weren't removed", "restored") don't count, nor do sentences about another tool
  (Git or push hooks, Cursor skills) that don't name Claude.
- **The reason for a decline.** The reason is the rest of the decline's sentence: the
  clause after it (from because, since, in favour of, so or "and replaced them with",
  or after `;` or `:`) and, for a deliberate absence, a clause before it ("The plugin
  is advisory, so it deliberately has no evals", "Because …, we deliberately …"). A
  reason in another sentence isn't read, and a sentence with neither says "no reason
  given".
- **Worth reconsidering, only on evidence.** A declined item gets a note only when one
  of its reason clauses (the clause after the decline, from because, since or so or after
  `;` or `:`, or the clause leading a deliberate absence) is one of these as a whole,
  word for word up to case, quotes and backticks, and the evidence exists:

  | Declined | Stated reason | Evidence |
  |---|---|---|
  | Hooks | hooks (or Claude Code hooks, Stop hooks, a hook, they, it) can't, cannot or are unable to block, stop or prevent Claude from stopping or finishing | [Stop](https://code.claude.com/docs/en/hooks): exit code 2 keeps Claude working |
  | Plugin evals | Claude Code has, offers or provides no (or there is no) way to run evals, or no built-in eval runner | [Test plugins with evals](https://code.claude.com/docs/en/plugin-evals) |
  | Plugin validation | Claude Code has no (or there is no) way to validate plugins, or no built-in plugin validator | [plugin validate](https://code.claude.com/docs/en/plugins/cli-reference) |
  | Code-intelligence plugins | Claude Code has no, doesn't or does not support LSP, language servers or code intelligence | [Code intelligence plugins](https://code.claude.com/docs/en/plugins/code-intelligence) |
  | Procedure skills | skills (or they) can't be shared with the team or through the repository | [Choose where skills load](https://code.claude.com/docs/en/skills) |
  | Hooks, pre-approved commands | there is or are no (or the project has no) check, check command or script, tests or test suite (to run), or there is nothing to check or run | the `path:line` of a documented check command, or the check script |
  | Code-intelligence plugins | the project, repository, code or codebase is untyped, is not typed or has no typed code, or there is no typed code | the typed-code marker (`tsconfig.json:1`, the `[tool.mypy]` line of `pyproject.toml`) |

  A doc row gives no note when the scan's Claude Code is older than the feature's
  minimum version. Any other wording gets no note, including the same reason with a
  limit or aside ("can't block Claude from finishing in CI"), and so does a reason that
  only rests on best practice. The note is advice on the declined item: it is not in
  the plan and changes no grade.
- **Defects a decline left behind stay in the plan.** A decline removes only its own
  Coverage gap. A correctness defect in the declined feature's own configuration (hook
  matchers, hook scripts and hooks files for hooks; `defaultMode`, `autoMode` and
  `Write(...)` rules for pre-approved commands; skill files for procedure skills) is
  planned and graded like any other and cites the decline.

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
