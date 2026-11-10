# Claudit

Claudit lists what is wrong in a project's Claude Code setup that `/doctor` won't
tell you, each finding with its file, real line and exact fix, and can apply the
fixes you pick. A clean project gets "Nothing found".

**Run `/doctor prompt-audit` first.** It checks instruction files for
contradictions and wording, which Claudit doesn't. Claudit checks the facts those
files state against the repository.

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
/claudit:claudit                  # list the findings, then offer to apply fixes
/claudit:claudit --read-only      # list the findings only
```

Asking Claude to audit or check the Claude Code setup also invokes it.

## What it checks

Every finding comes from Claudit's scan script, so the same tree gives the same
findings. The model only words each finding, and may leave one out when the
repository's own text explains it, quoting that text under "Not reported". It never
adds one.

- **Stale references**: paths, files, folders, scripts and commands named in the
  repository's instruction files, imports, skills, subagents and commands that don't
  exist (package.json scripts, Makefile and justfile targets, `bin/` and `scripts/`
  files), undeclared dependencies, and `@` imports that don't resolve.
- **History lines**: sentences that tell what happened (a past run, "has been
  retired", a dated event, a past version) instead of what holds now. The fix keeps
  the current fact and moves only the dated detail to a changelog or decision record.
- **Gates nothing enforces**: a merge, deploy, release, publish or push to main the
  instructions say needs a person, with no ask or deny rule. The fix is an exact ask
  rule, with the note that branch protection (or the deploy system's approval) is the
  real gate.
- **Must-run rules with no hook**: "always run `bin/ci` before you finish" with no
  Stop hook gets a hook script, unless the project documents a decision against hooks.
- **The check command**: detected from `package.json`, a Makefile or justfile, `bin/`
  and `scripts/`, Python, Go and Rust markers and CI, with an exact allow rule when no
  rule covers it.
- **Scope**: only files inside the git root are checked, by their real paths through
  symlinks. Files loaded from above get one line, and a `CLAUDE.md` above that stops
  the repository's `AGENTS.md` loading is flagged.
- **Always loaded**: a table of what loads into every session, in words and estimated
  tokens. It is a finding only past a limit the docs state.
- **Skills and subagents**: names referenced as skills or subagents that don't exist,
  and a skill only a subagent reads that is still in the skill listing.
- **Copies**: a rule copied word for word into three or more files.

Not checked: user and managed settings, settings validity (invalid JSON, hook
syntax, ignored values; `/doctor` reports those), server-side branch protection, and
contradictions or wording (`/doctor prompt-audit`). One settings fact is used: a
project `defaultMode` of `bypassPermissions`, which Claude Code ignores in project
settings, doesn't count as a replacement for allow rules (see Decisions below).

Claudit 5 doesn't grade, rank or recommend features, skills or procedures.

## The report

````markdown
# Claudit: shop

2 findings.

1. `CLAUDE.md:5` No allow rule in `.claude/settings.json` covers `bin/ci`, so every
   run of it asks first.
   Fix:
   ```json
   {"permissions": {"allow": ["Bash(bin/ci)"]}}
   ```
   Source: [Permission rule syntax](https://code.claude.com/docs/en/permissions)
2. `docs/repository.md:44` ...

## Not reported

- Respected: `CLAUDE.md:7` has no Stop hook; `docs/decisions.md:3` decided against hooks ("CI is the gate").

## Always loaded

| File | What | Loads | Words | Tokens (est.) |
...

---
Not checked: user and managed settings, settings validity, server-side branch protection.
Run `/doctor prompt-audit` for contradictions and wording.
Claudit 5.0.0; audited commit <sha>
````

The footer's last line gives the version and the audited commit (or "not a git
repo"), so a report can be reproduced.

## Rules

- **Only commands written as calls are pre-approved.** Which test runner or check a
  project uses is read from every mention. Which exact calls the allow rule suggests
  come only from these forms, and nothing else:
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
- **Stale facts.** Paths, folders, scripts and commands named in the in-repo
  instruction files, skills, subagents and commands must exist: package.json
  scripts (`npm run x`, `bun run x`), Makefile and justfile targets, `bin/` and
  `scripts/` files. A backticked dependency in a sentence that names a manifest
  (`pyproject.toml`, `package.json`, ...) must be declared there, and a skill or
  subagent named as "the `x` skill" must exist (not checked when the project enables a
  plugin, which can supply them). Each missing one is its own finding on its own line.
  A name in a line that says it isn't there ("provides no `bin/container`") or is
  conditional ("where supported") is not stale.
- **History lines.** A sentence in the instruction files, their imports, skills,
  subagents or the docs they say to read that tells what happened (a past run that
  passed, something that "has been retired", a dated event, a past version) is a
  finding on its line. A past verb in a relative clause or a condition ("the last
  release that passed", "if the build failed") and a date used as a name ("a
  2026-07-28 server") are not history. Decision records are skipped, and so are docs
  pages that are history pages by name or first heading (changelogs, release notes,
  migration and upgrade guides, what's-new, deprecations and breaking-changes pages);
  instruction files, imports, skills, subagents and commands never are. The fix keeps
  what holds now, restating a retirement in the present tense ("Shipshape is
  retired") with any status the sentence gives ("is kept for reference only"), and
  moves only the date or the account of the run to a changelog or decision record.
  A history line is never read as a decision: only a decision record does that.
- **Human gates.** A sentence in the loaded instructions where a person must approve
  a merge, deploy, release, publish or push to main, with no ask or deny rule for its
  command, is a finding: the exact `Bash(<command> *)` ask rule, plus the plain
  statement that branch protection (or the deploy system's approval) is the real gate
  and a client-side rule can be got around. The command is the one the sentence or the
  instructions name, a `bin/` or `scripts/` file named for the verb, or `gh pr merge`
  and `git push`.
- **Must-run rules.** A line in the instructions that says always or must run a check
  command (or "before you report" it), with no Stop, SubagentStop or TaskCompleted
  hook, gets a Stop hook that runs the exact documented call and blocks finishing
  until it passes.
- **Documented limits only.** CLAUDE.md over 200 lines; a skill's `description` plus
  `when_to_use` over 1,536 characters; custom subagent descriptions over 15,000 tokens.
  A skill only a subagent reads (by path or `skills:`), named nowhere else as one to
  run, without `disable-model-invocation: true` is a finding. Sizes are in words and
  estimated tokens.
- **Copies.** A sentence of 8 or more words copied word for word into three or more
  files (instruction files, skills, subagents, docs, script strings) is one finding,
  cited at each copy's real line; two copies are left alone, and so is text shared
  only by subagent, skill or command prompts, which each load in their own context. A
  script string is cited by the script's own line. A file is generated only when its
  first lines say so ("Generated from ...", "DO NOT EDIT") or `.gitattributes` marks it
  `linguist-generated`; text it shares with the script that writes it is one source.
  Paraphrases are not matched.
- **Test data isn't configuration.** A directory name is split into words at
  punctuation and case changes, compared case-insensitively, with trailing digits
  dropped. A name with test or tests as a whole word is a test directory (`tests`,
  `e2e-tests`, `tests_old`, `TestCases`); one with fixture(s), testdata, golden(s),
  snapshot(s), cassette(s), eval(s) or grader(s) is a data directory (`fixtures`,
  `__snapshots__`, `golden-files`, `evals-v2`). A word inside a word doesn't count
  (`testimonials`, `attest`, `latest`), and reports, results or data alone aren't
  data (`docs/reports` is scanned). Files below a test or data directory, or inside an
  eval case (a directory with `case.yaml`), are data. They are never read as
  instructions, check commands or decision records. A plugin root (a
  directory holding `.claude-plugin/` or `.codex-plugin/`) is never data because of its
  own name, so `plugins/test-runner` is scanned. Symlinks are judged by their target
  too, and a test directory's own `CLAUDE.md` is still an instruction file. Anything
  else the tests load can be dismissed.
- **Decisions.** A documented decision against hooks or pre-approved commands holds
  back the matching finding, listed under "Not reported" as respected with its file,
  line and reason. Claudit reads the loaded team instructions, the Markdown files they
  link and the README. A sentence decides against hooks or pre-approved commands only
  when the feature itself is named as a bare noun with at most an article, owner or
  kind ("Claude Code hooks", "the allowlist", "Stop hooks"):
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
- **A contradicted decision doesn't hold a finding back.** The finding stays, citing
  both the decision and the evidence, only when one of the decision's reason clauses
  is one of these as a whole, word for word up to case, quotes and backticks, and the
  evidence exists:

  | Decided against | Stated reason | Evidence |
  |---|---|---|
  | Hooks | hooks (or Claude Code hooks, Stop hooks, a hook, they, it) can't, cannot or are unable to block, stop or prevent Claude from stopping or finishing | [Stop](https://code.claude.com/docs/en/hooks): exit code 2 keeps Claude working |
  | Hooks, pre-approved commands | there is or are no (or the project has no) check, check command or script, tests or test suite (to run), or there is nothing to check or run | the `path:line` of a documented check command, or the check script |
  | Pre-approved commands | any reason, while project settings set `defaultMode` to `bypassPermissions` or `auto` | [A value you set is ignored](https://code.claude.com/docs/en/settings): Claude Code 2.1.257 and later ignore it in project settings |

  Any other wording holds the finding back, including the same reason with a limit or
  aside ("can't block Claude from finishing in CI"), and so does a reason that rests
  only on best practice.

## How it works

- `skills/claudit/scripts/claudit.py` scans the project. It is read-only and needs
  only the standard library of Python 3.9 or later. It also reports which
  instruction files load (`CLAUDE.md`, `AGENTS.md` or both).
- Each finding cites a docs page by URL and heading from a short map in the script,
  checked against the live docs when a release is built. Nothing is downloaded or
  fetched during an audit.
- The skill runs on Sonnet: one scan, then the report.

## State and writes

Claudit keeps no cache. An audit writes nothing at all. It writes only when you apply
fixes, or when you ask it not to repeat a finding: that is stored for you alone in
the plugin's data folder (`${CLAUDE_PLUGIN_DATA}/dismissed/<repository key>.json`), or
with `--shared` in `.claude/claudit-dismissed.json` for the whole team. The audit
reads both, and the footer says where its dismissals came from.

## Requirements

Tested with Claude Code 2.1.318. `python3` 3.9 or later. Git for branch delivery and
`gh` for pull requests.

## Upgrading from 4.x

5.0.0 is a breaking change to the report; see the [changelog](CHANGELOG.md). The
grades, the ranked plan, feature and skill recommendations, the Intent paragraph,
`--deep`, `--user`, the docs fetch and the `auditor` subagent are gone. Dismissals of
the checks that remain keep working, because their ids haven't changed.

MIT licensed; see [LICENSE](LICENSE).
