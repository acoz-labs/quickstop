# Claudit eval suite

A `claude plugin eval` suite that measures how well a Claude Code setup review
finds planted problems in nine small synthetic repositories. It is Claudit's
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
| `f6-agents-md` | Python package whose only instruction file is `AGENTS.md` | none: `no-invented-agents-md-ignored` (regex) and `no-invented-agents-md-not-loaded` (judge) fail when the report says `AGENTS.md` doesn't load or recommends a `CLAUDE.md` to make it load |
| `f7-fixture-noise` | Python CLI whose eval grader, golden report and fixture repository look like procedures and config | none on test data: `no-invented-fixture-findings` (regex) fails on a finding about them; the one real change is a skill for `docs/release.md` |
| `f8-documented-decline` | Advisory plugin whose `docs/decisions.md` retires hooks and declines an eval campaign | none: `structure-declined` needs both under "Declined by the project" with `docs/decisions.md:3` and `:5`, `no-invented-declined-recommendation` fails if either is recommended, `structure-coverage-a` needs Coverage A |
| `f9-clean` | Small, fully configured Node library | none: "No changes worth making" (`structure-plan-items`) with Coverage A (`structure-coverage-a`) |

Every case also has these `structure-*` regex graders: the report states the
project's intent, gives Correctness, Alignment and Coverage grades, each with a
confidence (Claudit 4.0 targets), and follows the plan-length rule in Claudit's
skill: up to 7 top changes, and fewer than 3 only with a first line such as "2
changes are worth making: <reason>" (a 4.0.1 target). Claudit 4.1 targets add
three more, all script graders:

- `structure-plan-items`: Top changes holds exactly the plan the scan decides for
  the fixture, titles word for word, in order, and nothing else ("No changes worth
  making" when it's empty). `tests/test_claudit_case_graders.py` builds each one
  from the scan of the scaffolded fixture and fails when a committed pattern falls
  behind; rebuild them with `python3 tests/test_claudit_case_graders.py --write`.
- `structure-footer`: the footer names Claudit's version and an audited commit.
- `structure-grade-raise`: every grade below A names the plan items that would
  raise it.

F3's six planted findings (the flat skill's paths and move, `Write(...)`,
`.claudeignore`, project `defaultMode`, the array matcher and the oversized
CLAUDE.md) and F2's missing `claude plugin eval` are regex graders, so they cost
nothing and don't vary with the judge. They need the named defect and the fix, and
some need a not-read, missing or size statement in the same line, sentence or
change item. A report that names both but endorses the defect would still pass.
F6 pairs a regex backstop for common wordings with a judge grader for the rest.
Each grader file states what it matches. `tests/test_claudit_eval_graders.py` runs
every regex grader against reports that must pass and must fail, in Python and,
when node is installed, in JavaScript, the engine `claude plugin eval` uses. Its
fixtures include the 18 final reports from the first 4.0.1 gate run
(`tests/claudit_gate_reports/`).

These still use the model judge, because each needs judgment about what a report
recommends: F1's three findings, F2's `claude plugin validate` and stale
reference, F5's two findings, every F4 `no-invented-*` grader, and F6's
`no-invented-agents-md-not-loaded`.

Fixtures store dotfiles as `dot-*` and instruction files as `*.fixture` so this
repository carries no live Claude Code configuration. `scaffold.sh` maps the
names back, commits the fixture in each run's empty workspace.

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
bin/claudit-eval run --arm claudit --model claude-sonnet-5-5 --max-cost-usd 12
bin/claudit-eval run --arm claudit --web-fetch --model claude-sonnet-5-5 --max-cost-usd 12
bin/claudit-eval run --arm plain --model claude-sonnet-5-5 --max-cost-usd 5
bin/claudit-eval run --arm doctor --model claude-sonnet-5-5 --max-cost-usd 5
```

The 4.0 gate runs the claudit arm twice, with and without `--web-fetch`.

`run` writes `result.json` (full results, including local trace paths),
`summary.json` (path-free metrics), `command.txt` (the exact runner and `claude plugin
eval` command lines) and `reports/<case>-run<N>.md` (each run's final report, read
from its trace) under `evals/claudit/results/<timestamp>-<arm>/` (git-ignored), and
prints a table: findings hit per case, structure graders
passed, F4 false defects, agent and judge cost, and wall time. `summarize
<result.json>` reprints it. `--dry-run` assembles the scratch directory and prints
the eval command without spending anything; `--keep-temp` keeps each run's sandbox and trace
for debugging; without it the runner removes them once the reports are saved. Exit status 2 means the cost
ceiling stopped the eval and the results are partial.

## Real repositories

`headless` audits one repository at one commit the accepted way (#156, #168):
`claude -p` on the normal login with `--plugin-dir` on the candidate bytes,
`--setting-sources project,local`, `--strict-mcp-config`, `--no-session-persistence`,
`--permission-mode default` and `--allowedTools Read Grep Glob`, from a fresh clone
per run under `TMPDIR` (it refuses when an instruction file sits above the clone).

```sh
bin/claudit-eval headless --repo https://github.com/acoz-labs/quickstop.git --sha efc71b7 \
  --plugin <candidate>/plugins/claudit --model claude-sonnet-5-5 --max-budget-usd 0.5 --runs 3 \
  --output-dir <retained>/quickstop-efc71b7
```

Each `run<N>/` keeps `report.md`, the raw JSON, stderr, the scan of the same clone
and `meta.json` with the exact command line, commit, Claude Code version, cost,
wall time and the script checks: the report's plan, grade letters and footer
match the scan, every grade below A names its items, the scan raised nothing on
test data, optional procedures aren't planned, and declines are listed with their
`path:line`. `summary.json` gives the medians. `grade --report R --scan S` runs the
same checks on any saved report.

## Sandbox limits

Inside `claude plugin eval`, Bash runs in an OS sandbox. It can't reach the
network, and it can read only the plugin under test and the run's own home and
workspace, not the host's Python install. So the runner copies the running
interpreter into the scratch plugin (`.eval-python/`) and puts it first in PATH.

Claudit 4.0 reads documentation live with WebFetch. `--web-fetch` (off by
default) allows that on any arm. It adds `WebFetch(domain:code.claude.com)` to
`--allow-tools` and `WebFetch` to `allowed_tools` in each copied `case.yaml`.
Both are needed. With them, WebFetch to `code.claude.com` works inside
`claude plugin eval` 2.1.312. Bash still can't reach the network. Without the
flag, a run has no way to read documentation. `summary.json` records
`web_fetch`, and `summarize` refuses to pool results that differ in it.

The judge (default `claude-haiku-5-5`, `--judge-model`) reads only the final
report. F6's failed `no-invented-*` graders count as false defects in the F6 row,
not F4's; one wrong sentence can fail both of them. Hit rates are model-judged and vary between runs; compare arms with the
same model, judge and run count.
