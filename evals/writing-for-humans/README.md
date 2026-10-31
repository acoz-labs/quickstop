# Writing for Humans regression check

A small, fixed check that the Writing for Humans kit still installs, loads, offers its
output style under the documented name, and keeps the writing-audit skill's user-only
contract. It is the kit's release check (issue #172). It checks for **regressions,
not writing quality**: it never judges how good the prose is, and it is not prompt
tuning, model comparison or a growing benchmark (see
[the acceptance record](../../docs/acceptance/writing-for-humans.md)). Keep the
cases fixed; change them only when the kit's documented contract changes.

`bin/writing-for-humans-eval run` does two things, and a suite pass needs both.

## Host checks (free)

`claude plugin eval` sessions load user settings only, from a config dir the
scaffold can't reach, and its `/output-style` command refuses to save a style
there. So style selection is checked outside it, with `claude` commands that never
call a model: install, `/output-style` and the session `init` record are local.
Each command runs with `HOME` and `CLAUDE_CONFIG_DIR` in a new temp dir and costs
$0 (the runner fails a command whose result reports any cost). No login is needed.

1. **Installs and loads.** A copy of the plugin is installed from a throwaway local
   marketplace (`claude plugin marketplace add` and `install`). A fresh session's
   `init` record lists it as `writing-for-humans@wfh-eval` at the manifest version,
   with both skills, `writing-for-humans:writing-audit` and
   `writing-for-humans:writing-style`.
2. **Style selectable under its documented name.** `/output-style
   writing-for-humans:writing-for-humans` (the kit README's command) reports the
   style set and saves it to `.claude/settings.local.json`. A fresh session's `init`
   record then reports that style as active. Control: an unknown name,
   `writing-for-humans:no-such-style`, is refused and saves nothing.

The runner hashes the real `~/.claude/settings.json` and
`~/.claude/plugins/{installed_plugins,known_marketplaces}.json` before and after
the host checks, and again across the whole `run` including the paid eval, and
fails if any changed. Other live Claude sessions rewrite `~/.claude.json` every
few seconds, so a byte comparison of it fails for reasons unrelated to the runner.
Instead the runner fails if that file mentions its temp dir, which is what a leaked
session would add as a project entry. It deletes only the temp dir it created. `bin/writing-for-humans-eval host` runs just
these checks.

## Eval cases (model runs)

Each runs once per suite pass in an empty workspace. `scaffold.sh` builds a small
git repository: the `tidecache` project committed on `main`, then a `ttl-decision`
branch that adds a context-dependent decision note (`docs/decision-notes.md`) and a
cryptic code comment. Eval sessions run with the `default` output style. Every
grader is a script (regex or `tool_used`); there is no model judge.

### `audit-typed`

The prompt is the typed user invocation, `/writing-for-humans:writing-audit`, which is
how the skill is meant to run. No edit tool is granted, so the audit is review-only.

Tools: `Read`, `Glob`, `Grep`, `Bash(git log:*)`, `Bash(git diff:*)`, `Bash(git show:*)`, `Bash(git status:*)`, `Bash(git branch:*)`, `Bash(git rev-parse:*)`.

- `loads`: the session `init` record lists the plugin and both skills.
- `reads-artifacts-reference`: a Read of `skills/writing-style/references/artifacts.md`. Enforces `skills/writing-audit/SKILL.md:13` and the table row at `:17` (read the reference for each surface; the draft is a workflow artifact, `:35`). A pass also shows `${CLAUDE_PLUGIN_ROOT}` expands to a readable file.
- `reads-output-style`: a Read of `output-styles/writing-for-humans.md`. Enforces `skills/writing-audit/SKILL.md:25` (when the style's rules are not present, read the style file); the eval session's style is `default`.
- `names-draft`: the report names `decision-notes.md`.
- `report-structure`: the report says what was rewritten (or would be) and what was kept or flagged. Enforces `skills/writing-audit/SKILL.md:65`, with `:61` for the review-only form. The "deleted" part of `:65` is not required, because a review-only audit deletes nothing.
- `no-external-action`: no Bash call that commits, rebases, resets, pushes or changes a PR, including `git` with global options before the subcommand and writing `gh api` calls. Enforces `skills/writing-audit/SKILL.md:61`, `:53` and `:63`. A denied attempt still fails.

### `audit-not-automatic`

The prompt asks for a writing audit in plain words, without the command.

Tools: `Read`, `Glob`, `Grep`, `Skill`, `Bash(git log:*)`, `Bash(git diff:*)`, `Bash(git show:*)`, `Bash(git status:*)`, `Bash(git branch:*)`, `Bash(git rev-parse:*)`.

- `skill-offered`: the `init` record offers the Skill tool and lists `writing-for-humans:writing-audit`, so the next grader can't pass just because the skill or tool was missing.
- `not-invoked`: no Skill call to `writing-audit`. Enforces `skills/writing-audit/SKILL.md:4` and `docs/acceptance/writing-for-humans.md:32` (a user-only skill Claude never invokes is the expected result; a recorded automatic call is a failure). A refused call still counts as a call.
- `reads-draft`: Claude reads `docs/decision-notes.md`, so it still dealt with the request.

This case exercises the skill's `disable-model-invocation: true` frontmatter
(`SKILL.md:4`): that setting keeps the skill out of what Claude is offered to call,
while the session still lists it as installed. Without that setting Claude could
call the skill for this request, and a call fails the case. It records the outcome
for one prompt and model, not a triggering guarantee.

### Tool grants

Each `Tools:` line is the case's grant: its `allowed_tools`, plus the runner's
`--allow-tools`, which applies to every case. The runner passes only the cases'
`Bash(git …:*)` patterns there, never `Bash` as a whole. A test checks that each
`Tools:` line matches what the case and runner grant.

Claude Code still runs, without any rule, the shell commands it classes as read-only.
In the smoke pass for issue #177 (Claude Code 2.1.316), `ls -R`, `grep -rniE`, `head`
and `git ls-files` ran, while a command list with `cat`, `echo` and `gh pr view` was
refused. Bash stays inside the eval sandbox either way, and `no-external-action` still
fails any commit, push, rebase, reset or PR attempt. Tools that need no permission,
such as `Task` and `ToolSearch`, are offered too; the session's `init` record lists them.

## Pass rule

The runner compares the result with the suite it copied (`suite.json` in the
result dir): every case must be present with `--runs` runs, and every grader file
on disk must have scored in each run. A missing case, a missing grader or a short
run count fails. A `--case` run is a subset and never a suite pass. Each grader is
binary. A case run passes only if every grader scored and passed. An
agent error, timeout, cost-ceiling stop or skipped grader is a failure. A suite pass
needs every host check and every case run to pass. The kit's baseline is 3 of 3
suite passes, each a separate `run`, with no selective retries. The only rerun
allowed is a whole pass after an infrastructure failure before any model turn
(authentication or rate limit), recorded with its cost.

## Running

Needs Claude Code with `claude plugin eval` (checked on 2.1.316), a Claude login for
the eval cases, and Python 3.11+ first in PATH (see
[repository](../../docs/repository.md)). Always pin the model and pass a cost ceiling:

```sh
export PATH="$(mise where python@3.11.15)/bin:$PATH"
bin/writing-for-humans-eval run --model claude-sonnet-5-5 --max-cost-usd 2
```

`run` copies the plugin into a scratch dir with this suite as its `evals/`
(`claude plugin eval` accepts only an eval dir inside the plugin root), so plugin
bytes never change; it also fails the pass if the source plugin's bytes changed
during the run. It writes `CANDIDATE.txt` (head, tree, plugin tree and bytes
digest), `suite.json`, `host.json`, `result.json` and `summary.json` under
`evals/writing-for-humans/results/<UTC timestamp>/` (git-ignored) and prints a table
of each case run, its failed graders and its cost. It exits 0 only when the suite
passes, 2 when the cost ceiling stopped it. `summarize <result dir>` reprints a run;
`--dry-run` assembles the scratch and prints the eval command without running
anything; `--keep-temp` keeps each run's trace.

Inside `claude plugin eval`, Bash runs in a sandbox that reads only the plugin under
test and the run's home and workspace. On macOS, `/usr/bin/git` is an `xcrun` shim
that fails there (it can't write its cache or read the developer tools), so the
runner copies the real git executable into the scratch plugin (`.eval-git/`) and puts
it first in PATH for the cases' read-only git commands.
