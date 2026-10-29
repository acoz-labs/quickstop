# Claudit eval suite

A `claude plugin eval` suite that measures how well a Claude Code setup review
finds planted problems in five small synthetic repositories. It is Claudit's
release gate (issue #155), not a per-PR check: each full pass spends model budget.
Recorded baselines are in [the baseline record](../../docs/acceptance/claudit-eval-baselines.md).

## Placement

The suite ships in this repository, outside `plugins/claudit/`, so measuring
Claudit doesn't change plugin bytes or need a version bump. `claude plugin eval`
only accepts an eval directory inside the plugin root, so `bin/claudit-eval`
assembles a scratch plugin directory (the plugin under test plus this suite as
its `evals/`) and runs the eval there. Issue #156 (Claudit 4.0) decides whether
the suite moves into the plugin.

## Cases

| Case | Fixture | Planted findings (`finding-*` graders) |
|---|---|---|
| `f1-agent-run` | CI script and procedure doc, minimal CLAUDE.md, no settings | CI allowlist, Stop hook running checks, procedure as a skill |
| `f2-plugin-repo` | Repo that ships a Claude Code plugin | `claude plugin validate`, `claude plugin eval`, stale CLAUDE.md reference |
| `f3-misconfigured` | Misconfigured project | `Write(...)` rule, `.claudeignore`, flat skill file, project `bypassPermissions`, array hook matcher, oversized CLAUDE.md |
| `f4-well-configured` | Sensible current setup | none: `no-invented-*` graders fail when a healthy choice is reported as a defect |
| `f5-bare` | Go source and tests, no Claude config | project instructions, test-command allowlist |

Every case also has four `structure-*` regex graders: the report states the
project's intent and gives Correctness, Alignment and Coverage grades, each with
a confidence. Those are Claudit 4.0 targets.

Fixtures store dotfiles as `dot-*` and instruction files as `*.fixture` so this
repository carries no live Claude Code configuration. `scaffold.sh` maps the
names back, commits the fixture in each run's empty workspace and, when the
runner supplies one, seeds Claudit's research cache into the run's home.

## Arms

- `plain`: an empty plugin and the prompt "Review this project's Claude Code
  setup and tell me what to improve."
- `doctor`: an empty plugin and the prompt `/doctor`.
- `claudit`: the plugin under test (default `plugins/claudit`) invoked with
  `--invoke` (default `/claudit:claudit --read-only`).

## Running

Needs Claude Code with `claude plugin eval` (checked on 2.1.312), a Claude login,
and Python 3.11+ first in PATH (see [repository](../../docs/repository.md)).
Runs use the operator's normal login; the eval host isolates each run's home,
configuration and workspace. Always pin the model and pass a cost ceiling:

```sh
export PATH="$(mise where python@3.11.15)/bin:$PATH"
bin/claudit-eval seed --model claude-sonnet-5-5 --max-cost-usd 5 --out "$TMPDIR/claudit-seed/cache"
bin/claudit-eval run --arm claudit --model claude-sonnet-5-5 --max-cost-usd 12 \
  --seed-cache "$TMPDIR/claudit-seed/cache"
bin/claudit-eval run --arm plain --model claude-sonnet-5-5 --max-cost-usd 5
bin/claudit-eval run --arm doctor --model claude-sonnet-5-5 --max-cost-usd 5
```

`run` writes `result.json` (full results, including local trace paths) and
`summary.json` (path-free metrics) under `evals/claudit/results/<timestamp>-<arm>/`
(git-ignored), and prints a table: findings hit per case, structure graders
passed, F4 false defects, agent and judge cost, and wall time. `summarize
<result.json>` reprints it. `--dry-run` assembles the scratch directory and prints
the eval command without spending anything; `--keep-temp` keeps each run's
transcript for debugging. Exit status 2 means the cost
ceiling stopped the eval and the results are partial.

## Sandbox limits

Inside `claude plugin eval`, Bash runs in an OS sandbox. It can't reach
`code.claude.com`, and it can read only the plugin under test and the run's own
home and workspace, not the host's Python install. So the runner copies the
running interpreter into the scratch plugin (`.eval-python/`) and puts it first
in PATH, and Claudit 3.x can't refresh its research cache during a run.
`seed` builds that cache once, outside the sandbox: it runs `/claudit:refresh all`
with `claude -p` from a throwaway repository, using `--setting-sources
project,local`, `--strict-mcp-config`, an isolated `CLAUDIT_CACHE_DIR`, and writes
allowed only inside the cache. `run --seed-cache` checks that every domain is
fresh after relocation, then copies the cache into each run. A plugin that reads
documentation live (the 4.0 design) will hit the same network limit. #156 has to
account for it.

The judge (default `claude-haiku-5-5`, `--judge-model`) reads only the final
report. Hit rates are model-judged and vary between runs; compare arms with the
same model, judge and run count.
