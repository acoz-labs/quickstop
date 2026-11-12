# Plan: check skills against the Agent Skills spec and drop "Claude Code only"

## Issue

Closes https://github.com/acoz-labs/quickstop/issues/214

Every `bin/ci` run checks each plugin skill against the Agent Skills spec (the
pinned reference validator plus a repository lint for Claude Code-only
features), Writing for Humans is exempt through a repository setting, and the
repository docs describe Quickstop as acoz-labs' marketplace of agent plugins
and skills instead of a Claude Code-only marketplace. No plugin bytes change,
so there is no version bump, tag or pointer PR.

## Decisions

**Where the checks run.** The GitHub CI job (`.github/workflows/ci.yml`) runs
`bin/ci` and stays unchanged. Every run of that job so far has been skipped,
because Actions are opt-in here and the repository variable that enables them
is unset. "CI" here is the clean-checkout `bin/ci` receipt that
`bin/sdlc-evidence` records on the exact head of every PR and that
`bin/sdlc audit` requires before merge. Both paths get the new checks through
`bin/ci`.

**Wording rule.** No new or reworded text in this change contains the phrases
the issue's acceptance grep looks for ("Claude Code only", "Claude Code-only",
"Claude Code plugin marketplace"). New text says "features only Claude Code
supports" or similar. This covers the exemption reason, the lint's messages,
code comments, the `docs/plugin-development.md` rule, the `docs/repository.md`
lessons and the rewording of history in `docs/investigation.md` and
`docs/acceptance/writing-for-humans.md`. The `claude_code_only` JSON key
doesn't match the grep, because underscores aren't spaces or hyphens.

**skills-ref pin.** Upstream repository `github.com/agentskills/agentskills`,
folder `skills-ref`, commit `83021e2be457a9b6679148719c1f6074f0ad975e`
(main on 2026-11-04). The folder's git tree at that commit is
`dc2d22177c5491d688ab4efc9833a622b97822ea`, unchanged since its last edit in
`f130f348`. skills-ref needs four pure-Python packages, pinned to the versions
and wheel sha256 hashes in that commit's `skills-ref/uv.lock`:

| Package | Version | Wheel sha256 |
| --- | --- | --- |
| click | 8.3.1 | `981153a64e25f12d547d3426c367a4857371575ee7ad18df2a6183ab0545b2a6` |
| strictyaml | 1.7.3 | `fb5c8a4edb43bebb765959e420f9b3978d7f1af88c80606c03fb420888f5d1c7` |
| python-dateutil | 2.9.0.post0 | `a8b2bc7bffae282281c8140a97d3aa9c14da0b136dfe83f850eea9a5f7470427` |
| six | 1.17.0 | `4721f391ed90541fddacab5acf947aa0d3dc7d27b2e1e8eda2be8970586c3274` |

**How skills-ref is fetched, using only the standard library and git.** No pip,
no virtual environment, nothing installed into the repository:

1. `git init` a temporary directory, `git fetch --depth 1` the pinned commit by
   its hash, and refuse to continue unless the fetched commit and the
   `skills-ref` tree hash both equal the pins. Git's content addressing makes
   the commit hash a byte pin.
2. Download each wheel with `urllib` from its exact PyPI URL (also from
   `uv.lock`), refuse it unless its sha256 matches, and unzip it with
   `zipfile`.
3. Copy the `skills-ref` folder and the four wheel files, still zipped, into a
   staging folder, then rename it into the cache,
   `${XDG_CACHE_HOME:-~/.cache}/quickstop/skills-ref/<commit>/`. The rename
   happens only after every check passes, so a half-finished or unverified
   download never becomes the cache. If the rename fails because another run
   created the cache first, that counts as success; the check in step 4 still
   applies to what is there.
4. Every time the cache is used, recheck it against the pins in the
   repository: recompute the git tree hash of the cached `skills-ref` folder
   and the sha256 of each cached wheel. A mismatch fails the step and names the
   cache folder to delete; nothing in the cache is trusted only because it was
   checked once.
5. Unzip the wheels and copy `skills-ref/src` into a temporary folder for this
   run, run the validator as `<pinned python> -I -B -c` with `sys.path` set to
   that folder, calling `skills_ref.cli.main` with `validate <skill dir>`, and
   delete the folder afterwards. `-I` keeps the working directory and
   environment variables off the import path, and `-B` stops Python writing
   bytecode (`-I` ignores `PYTHONDONTWRITEBYTECODE`). The repository's pinned
   Python 3.11.15 meets skills-ref's `requires-python >=3.11`.

A probe of exactly this method on 2026-11-12 matched all four hashes, passed
Claudit's skill, and failed both Writing for Humans skills on
`argument-hint`, `disable-model-invocation` and `disallowed-tools`.

**Offline `bin/ci`.** After the first successful fetch, every later run uses
the cache and needs no network. The new skills step runs last in `bin/ci`, so
every existing check has already run and reported before it. If the cache is
missing and the fetch fails, the step fails and names the remedy: rerun with a
network, or set `QUICKSTOP_SKIP_SKILLS_REF=1`. Each tool-backed check has its
own variable, so skipping one never drops the other:
`QUICKSTOP_SKIP_SKILLS_REF=1` skips only skills-ref, and
`QUICKSTOP_SKIP_CLAUDE_VALIDATE=1` skips only `claude plugin validate`. The lint
always runs. A skipped check prints a `SKIPPED: <check> (<variable> is set)`
line, and those lines are the last lines of `bin/ci`'s output, after
everything else, so nobody reading the log can miss them. The variables are
for offline local work. `bin/sdlc-evidence` copies the caller's environment
into its `bin/ci` run, so `docs/repository.md` says that a receipt showing
`SKIPPED` is not a pass and doesn't count as review or acceptance evidence. A
silent skip is not an option: the repository treats an unavailable check as an
error, not a reason to skip validation.

**`claude plugin validate --strict` is in.** On 2026-11-12, Claude Code
2.1.322 ran it under a fresh temporary `HOME` and `CLAUDE_CONFIG_DIR` with no
login and no API key, with `DISABLE_AUTOUPDATER=1`: the marketplace root and
both plugins passed with exit 0, and it wrote only inside the temporary
directory. Its missing-icon notice is advisory and does not change the exit
code. `bin/ci` runs it the same way on the marketplace root and every plugin,
including Writing for Humans (it is Claude Code's own validator, so the
exemption does not apply), and deletes the temporary directory afterwards.
It needs the `claude` command on PATH; when it is missing, the step fails and
names `QUICKSTOP_SKIP_CLAUDE_VALIDATE=1`.

**The exemption setting.** A new repository file, `skills-check.json`, holds
the skills-ref pins and the exemption list:

```json
{
  "schema": 1,
  "skills_ref": { "repository": "...", "commit": "...", "tree": "...", "wheels": [ ... ] },
  "claude_code_only": {
    "writing-for-humans": "Its core is an output style, and its skills use frontmatter fields and plugin variables only Claude Code supports."
  }
}
```

A plugin listed under `claude_code_only` is skipped by checks 1 and 2, and the
output names it and the reason. Every other plugin, including any new one, is
checked. The file fails validation when an exempt name is not in
`catalog.json` (a stale exemption) or the reason is empty. A separate file
keeps the `catalog.json` and `releases.json` schemas unchanged, and nothing
under `plugins/` changes.

## The lint's rules

The lint reads each `plugins/*/skills/*/SKILL.md` outside exempt plugins. Rule 1
reads the frontmatter; rules 2 to 7 read the body. Frontmatter values are not
scanned, because the spec's own `allowed-tools` field legitimately names tools.
Each finding is one line: path, line number, rule name, what was found, why only
Claude Code supports it, and how to write it portably. One finding per rule per
line.

| Rule | Fails on | Portable fix in the message |
| --- | --- | --- |
| `frontmatter-field` | A top-level key other than `name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools` (for example `argument-hint`, `model`, `disable-model-invocation`, `disallowed-tools`) | Remove it, or put tool-specific data under `metadata` |
| `argument-substitution` | `$ARGUMENTS`, `${ARGUMENTS}`, `$ARGUMENTS[n]`, or `$0`-`$9` not followed by a digit or a decimal part | Describe the input in words ("the file the user names") |
| `shell-injection` | `` !`command` `` inline, or a fence opened with ```` ```! ```` | Tell the agent which command to run and why |
| `plugin-variable` | `$CLAUDE_…` or `${CLAUDE_…}` (`CLAUDE_PLUGIN_ROOT`, `CLAUDE_PLUGIN_DATA`, `CLAUDE_SKILL_DIR`, `CLAUDE_PROJECT_DIR` and the rest) | Use a path relative to the skill folder, such as `references/x.md` |
| `tool-name` | A Claude Code tool name used as one: a name followed directly by `(` (`Bash(git *)`), a code span that is exactly a name (`` `Read` ``), a name followed by "tool" or "tools" ("the Edit tool"), or a multi-word name that is never English (`AskUserQuestion`, `WebFetch`, `WebSearch`, `TodoWrite`, `NotebookEdit`, `MultiEdit`, `ExitPlanMode`, `BashOutput`, `KillShell`, `SlashCommand`) anywhere | Say the action in plain words ("read the file", "ask the user") |
| `output-style` | `output-style`, `output-styles`, `outputStyle`, or a code span followed by "output style" (`` `name` output style``) | Put the guidance in the skill or its references |
| `hook` | Claude Code hook event names (`PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `UserPromptSubmit`, `SessionStart`, `SessionEnd`, `SubagentStart`, `SubagentStop`, `PreCompact`, `PermissionRequest`), `hooks.json`, or a `"hooks"` JSON key | State the rule as an instruction, or keep the hook in a plugin exempted in `skills-check.json` |

The single-word tool names checked are `Read`, `Write`, `Edit`, `Bash`, `Glob`,
`Grep`, `Task`, `Agent`, `Skill` and `LS`.

How false positives stay low:

- Matching is case-sensitive and on whole words.
- A single-word tool name trips only in the three tool-shaped forms above, so
  "Read the file", "Write a summary", "Edit the draft", "Task: triage" and
  "## Skill overview" pass.
- The plain words "hook" and "output style" do not trip ("a git pre-commit
  hook", "match the output style of the report"). Only Claude Code's
  identifiers do; the event names `Stop` and `Notification` are left out
  because they are English words.
- Prices with a decimal part or several digits ("$1.50", "$10") pass. A bare
  "$1" is flagged on purpose: Claude Code would substitute it.
- No inline suppression comment exists; a plugin that needs Claude Code
  features is exempted as a whole, by name, with a reason.
- Before the PR, an attacker pass and a false-negative pass: every rule gets
  plain-English phrasings that must pass and disguised forms that must fail
  (tool names in backticks with trailing spaces, variables without braces,
  `$ARGUMENTS` inside code fences), all kept as test cases.

Claudit's skill passes the lint and skills-ref unchanged, so Claudit needs no
exemption.

## Files that change

- New checker (`bin/check-skills`, Python standard library): the lint, the
  skills-ref fetch and run, `claude plugin validate --strict` under a temporary
  home, the exemption handling and the two skip variables. Before validating real
  skills, it runs skills-ref on the two fixture skills and requires the clean
  one to pass and the Claude Code-only one to fail, so a broken or no-op
  validator cannot pass CI.
- New setting (`skills-check.json`): the pins and the Writing for Humans
  exemption described above.
- CI script (`bin/ci`): one new last step, `bin/check-skills`.
- New tests (`tests/test_check_skills.py`) and fixtures
  (`tests/fixtures/skills/portable-skill/SKILL.md`,
  `tests/fixtures/skills/claude-only-skill/SKILL.md`): see Proof. Tests run
  offline: the fetch is tested against a local git repository and local wheel
  files through `file://` URLs, and `claude` is a fake script on PATH.
- Rewording, so that the issue's grep finds nothing outside `docs/archive/`,
  `docs/changes/` and Writing for Humans' package:
  - `README.md`: "Quickstop is a Claude Code plugin marketplace" and the
    plugins row's "for Claude Code" become plain descriptions of agent plugins
    and skills. Install instructions stay Claude Code commands.
  - `catalog.json` description becomes "The acoz-labs marketplace of agent
    plugins and skills.", regenerated into `.claude-plugin/marketplace.json`
    and `docs/catalog.md` with `bin/check-marketplace --write`. The usual rule
    that description changes go in the pointer PR is about plugin releases;
    this change has none.
  - `docs/marketplace.md`: the opening sentence. The single `claude-code`
    target rule stays, since the schema is unchanged.
  - `docs/repository.md`: drop "Quickstop supports no other agent tool" and
    the Claude Code plugins framing. Its "standard library only; no
    downloaded Python dependencies" line changes to say the repository's own
    code is standard-library only while `bin/ci` downloads skills-ref and its
    four dependencies, pinned and hash-checked, into a cache outside the
    repository on first run, and needs `claude` on PATH. Its description of
    `bin/ci`'s healthy output gains the skills check lines. It also gains
    `bin/check-skills`, the cache, the two skip variables, the rule that a
    `SKIPPED` receipt is not a pass, and the lessons from this work.
  - `docs/plugin-development.md`: a short rule that new skills follow the Agent
    Skills spec and that a plugin using features only Claude Code supports
    needs a `skills-check.json` exemption.
  - `docs/investigation.md` and `docs/acceptance/writing-for-humans.md`:
    reword the "Claude Code only" phrasing while keeping the history they
    record.
  - `bin/check-marketplace`: its comment saying Quickstop targets Claude Code
    only.
- Unchanged: everything under `plugins/`, `releases.json`, the schemas,
  `.github/workflows/`, and `AGENTS.md` and `CLAUDE.md` (neither contains the
  phrasing, so the hash pin is untouched).

## Order of work

1. This plan, alone, in a draft PR.
2. Lint, fixtures and the exemption setting, with their tests. `bin/ci` runs
   the lint.
3. skills-ref fetch, cache, recheck and run, with offline tests, then
   `claude plugin validate --strict`, then the two skip variables.
4. Rewording and regenerated indexes.
5. Repository lessons in `docs/repository.md`, a simplify pass, then the PR
   goes ready for review.

Each step leaves `bin/ci` passing.

## Risks

- **Upstream moves or disappears.** The pin is a commit hash, so upstream
  changes never alter what runs. If the commit or a wheel becomes unreachable,
  machines with a cache keep working and new ones fail with a message naming
  the pin; moving the pin is a reviewed one-file change.
- **A future Claude Code version adds a strict warning.** `bin/ci` would then
  fail on a change unrelated to the PR. The failure prints the validator's own
  message, and the fix is to address the warning or to discuss removing the
  step; it is never to add a credential.
- **The self-hosted runner, if Actions are enabled later**, needs git, network
  for the first fetch and `claude` on PATH. Today the job never runs.
- **A false positive blocks a future portable skill.** The rule list, the
  negative controls in the tests and the fix text in each message contain
  this; a real false positive is fixed in the lint, never by exempting the
  plugin.
- **A corrupted or concurrent cache.** The cache is written only after every
  hash check passes, a lost rename race counts as success, and every use
  rechecks the cached files against the pins held in the repository, so a
  changed file fails the run instead of running. Deleting the folder forces a
  fresh, verified fetch.

## Proof

Automated (`tests/test_check_skills.py`, run by `bin/ci`):

- The Claude Code-only fixture produces exactly one finding per rule, at the
  expected line, with the expected rule name; the spec-clean fixture produces
  none. (Acceptance 2, lint half.)
- `bin/check-skills` requires skills-ref to pass the clean fixture and fail
  the Claude Code-only one on every run. (Acceptance 2, validator half.)
- Negative controls from the false-positive list pass; attacker forms fail.
- With the real repository's skills, removing Writing for Humans from a copy
  of `skills-check.json` makes the lint fail with findings in both of its
  skills; restoring it passes. A stale or reasonless exemption fails.
- Fetch: a wrong commit, a wrong tree hash or a wrong wheel hash each fails and
  leaves no cache; a good fetch populates the cache, and a second run makes no
  fetch. A cache that already exists when the rename runs counts as success.
  Changing one byte of a cached wheel or source file fails the next run. The
  validator run leaves no `__pycache__` in the cache.
- `claude plugin validate` is called with `--strict`, `DISABLE_AUTOUPDATER=1`
  and a temporary `HOME` and `CLAUDE_CONFIG_DIR` that are removed afterwards;
  a missing `claude` fails unless `QUICKSTOP_SKIP_CLAUDE_VALIDATE=1` is set.
  Each skip variable skips only its own check, and its `SKIPPED` line comes
  after all other output.

On the real artifact, which the reviewer repeats on a clean checkout of the PR
head:

1. `bin/ci` exits 0, showing skills-ref and `claude plugin validate --strict`
   results and the Writing for Humans exemption line. (Acceptance 1.)
2. In a throwaway worktree, delete the `writing-for-humans` entry from
   `skills-check.json` and run `bin/ci`: it exits non-zero with lint findings
   and skills-ref failures for both Writing for Humans skills. Remove the
   worktree after. (Acceptance 3.)
3. `grep -rin "claude code[- ]only\|claude code plugin marketplace"` over the
   repository, excluding `.git`, `docs/archive/`, `docs/changes/` and
   `plugins/writing-for-humans/`, returns nothing, including in the new files.
   (Acceptance 4.)
4. `bin/check-marketplace --base origin/main` passes and reports no package
   changes; `git diff origin/main -- plugins releases.json` is empty; the
   diff adds no secret, account or paid service. (Acceptance 5.)
5. A second `bin/ci` run with networking off passes from the cache.

## Rollback

Revert the PR's commits on main. Nothing is released, no plugin bytes or
release records change, and no data migrates. The skills-ref cache left in
users' homes is inert; delete `~/.cache/quickstop/skills-ref` to remove it.
