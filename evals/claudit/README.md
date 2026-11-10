# Claudit eval suite

A `claude plugin eval` suite that measures how well a Claude Code setup review
finds planted problems in nineteen small synthetic repositories. It is Claudit's
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

Each case's expected findings are what the scan raises on the scaffolded fixture;
`tests/test_claudit_graders.py` pins them.

| Case | Fixture | What the report must hold |
|---|---|---|
| `f1-agent-run` | CI script and procedure doc, a must-run rule, no settings | the `bin/ci` allow rule and the Stop hook |
| `f2-plugin-repo` | Repo that ships a Claude Code plugin | the missing `docs/architecture.md` and the check command's allow rule |
| `f3-misconfigured` | Settings defects `/doctor` reports and a 241-line CLAUDE.md | only the CLAUDE.md past the 200-line target |
| `f4-well-configured` | Sensible current setup | Nothing found |
| `f5-bare` | Go source and tests, no Claude config | the `go test ./...` allow rule |
| `f6-agents-md` | Python package whose only instruction file is `AGENTS.md` | the allow rule and the Stop hook |
| `f7-fixture-noise` | Python CLI whose test data looks like procedures and config | Nothing found |
| `f8-documented-decline` | A decision record retires hooks for a review checklist | Nothing found; the decision under "Not reported" as respected |
| `f9-clean` | Small, fully configured Node library | Nothing found |
| `f10-stale-decline` | Decisions whose reasons no longer hold | the allow rule and the Stop hook, each citing the decision and the evidence |
| `f11-valid-decline` | Hooks retired for a review checklist, with a must-run rule | Nothing found; the decision respected with its reason |
| `f12-unsafe-decline` | Allow rules dropped for project `bypassPermissions` | the `bin/test` allow rule, citing the decision and the ignored setting |
| `f13-no-reason-decline` | Hooks retired with no reason, with a must-run rule | Nothing found; the decision respected with "no reason given" |
| `f14-enforcement` | Merge, deploy and release gated on a person only in prose | the three ask rules with branch protection named, and the Stop hook |
| `f15-context-economy` | A subagent-only skill, a rule copied word for word into 3 files and paraphrased in 2 | the visible skill, the verbatim copies, the allow rule and the Stop hook; no paraphrase |
| `f16-stale-facts` | CLAUDE.md names a folder, a file and a dependency that don't exist | each on its own line, and the allow rule |
| `f17-scope` | Repo inside a parent folder with its own `CLAUDE.md` and `AGENTS.md`; its `CLAUDE.md` is a symlink | the three scope lines in the footer, no numbered finding |
| `f18-check-commands` | Check commands only in `package.json` and CI | the exact `bun run` allow rules |
| `f19-declarative-list` | Healthy library with numbered standing principles | Nothing found |

f11 and f13 gained a must-rule line in 5.0.0, so their decisions hold a real finding
back. Fixtures store dotfiles as `dot-*` and instruction files as `*.fixture` so
this repository carries no live Claude Code configuration. `scaffold.sh` maps the
names back and commits the fixture in each run's empty workspace.

## Graders

Every grader is a script (regex) grader built from the scan of the scaffolded
fixture by `tests/claudit_graders.py` (rebuild with `python3 tests/claudit_graders.py
--write`). The patterns are defined once in `bin/claudit-eval`, which checks
real-repository reports with the same rules. They match the report's structure and
the scan's citations and fix tokens, never phrasing:

- `finding-<kind>`: a numbered item that starts with the finding's `path:line` and
  holds its tokens (the exact `Bash(...)` rules of an allow or ask fix, `exit 2` for
  a Stop hook, the missing name for a stale fact, the other copies for a duplicate,
  branch protection for a gate).
- `finding-respected-<kind>`: the respected decision's line under "Not reported".
- `finding-scope-<n>`: each scope line after the footer rule (f17).
- `no-invented-findings`: the numbered items are the scan's findings, one to one.
  Every item starts with one of the scan's citations, each citation has as many
  items as the scan has findings there, and each item holds a token of its findings.
  An invented item, an item with no citation, a second item at an expected citation
  or a dropped item fails.
- `no-invented-prose`: the report holds only the template's parts (title, count
  line, numbered items, "Not reported" bullets, the always-loaded table, the footer
  lines). Advice under the table, in the footer or anywhere else fails.
- `structure-summary`: the count line ("Nothing found." or "<n> findings.").
- `structure-footer`: the not-checked line, the `/doctor prompt-audit` line and the
  version and audited commit.

`finding-*` graders are the hit rate; a failed `no-invented-*` grader is a false
finding. `tests/test_claudit_graders.py` runs every grader on six renderings of each
case's correct report, which must all pass, and on failing controls that change one
thing each (a dropped item, a wrong line, a missing token, an item moved under "Not
reported", a token only in a negated note, the same item twice, an invented item,
an item with no citation, advice under the table and in the footer, a wrong count,
a missing footer, respected or scope line), in Python and in node. A mutation check
drops each part of `no-invented-findings` and each token of a `finding-*` grader and
needs a control to flip.

## Arms

- `plain`: an empty plugin and the prompt "Review this project's Claude Code
  setup and tell me what to improve."
- `doctor`: an empty plugin and the prompt `/doctor`.
- `claudit`: the plugin under test (default `plugins/claudit`) invoked with
  `--invoke` (default `/claudit:claudit --read-only`).
- `doctor-combined` (#192): Claude Code's two built-in reviews, `/doctor` and
  `/doctor prompt-audit .`, run headless outside `claude plugin eval`, because a case
  holds one prompt. Each run scaffolds the case into a fresh
  `<tmp>/claudit-combined-*/home/cwd` (the eval host's layout), runs `claude -p` once
  per prompt with `--setting-sources project --disallowedTools Edit Write NotebookEdit
  --strict-mcp-config --no-session-persistence`, `--model` and a per-call
  `--max-budget-usd`, and grades the two replies as one report with the case's
  script graders. `result.json` has the `claude plugin eval` shape.

## Running

Needs Claude Code with `claude plugin eval` (checked on 2.1.312), a Claude login,
and Python 3.11+ first in PATH (see [repository](../../docs/repository.md)).
Runs use the operator's normal login; the eval host isolates each run's home,
configuration and workspace. Always pin the model and pass a cost ceiling:

```sh
export PATH="$(mise where python@3.11.15)/bin:$PATH"
bin/claudit-eval run --arm claudit --model claude-sonnet-5-5 --max-cost-usd 7.60 --runs 1
bin/claudit-eval summarize evals/claudit/results/<run>/result.json --expect-runs 1
```

`--max-cost-usd` is a ceiling for the whole `claude plugin eval` invocation, checked
before each run starts, not a per-case cap: set it to the number of cases times the
per-case figure, or to what is left of the job's cap if that is lower. A run that
stops at the ceiling is partial (exit status 2). For `doctor-combined`,
`--max-budget-usd` caps each headless call. Every `claude` call the runner makes sets
`DISABLE_AUTOUPDATER=1`.

`run` writes `result.json`, `summary.json` (path-free metrics, with the median cost
and wall time per run), `command.txt` (the exact command lines) and
`reports/<case>-run<N>.md` under `evals/claudit/results/<timestamp>-<arm>/`
(git-ignored), and prints the table. A full-suite run (no `--case`) also checks the
result is the whole suite (every case, `--runs` runs each, every grader in every run)
and exits non-zero when it isn't; `summarize --expect-runs N` applies the same check
to saved results, so a partial run can't read as a pass. `--dry-run` assembles the
scratch directory and prints the eval command without spending anything;
`--keep-temp` keeps each run's sandbox and trace.

## Real repositories

`headless` audits one repository at one commit the accepted way (#156, #168):
`claude -p` on the normal login with `--plugin-dir` on the candidate bytes,
`--setting-sources project,local`, `--strict-mcp-config`, `--no-session-persistence`,
`--permission-mode default` and `--allowedTools Read Grep Glob`, from a fresh clone
per run under `TMPDIR` (it refuses when an instruction file sits above the clone).

```sh
bin/claudit-eval headless --repo https://github.com/acoz-labs/quickstop.git --sha <commit> \
  --plugin <candidate>/plugins/claudit --model claude-sonnet-5-5 --max-budget-usd 0.40 --runs 3 \
  --output-dir <retained>/quickstop-<commit>
```

Each `run<N>/` keeps `report.md`, the raw JSON, stderr, the scan of the same clone
and `meta.json` with the command line, commit, Claude Code version, cost, wall time,
the cited `path:line` list and the script checks: every line the scan cites exists in
the clone; every numbered item starts with a citation, and each is one of the scan's
findings; every scan finding is reported or under "Not reported" with a reason that
cites the repository; the respected lines, the count line and the footer lines are
there; and nothing outside the template. `summary.json` gives the medians. `grade
--report R --scan S` runs the same checks on any saved report. Whether a finding is
right about the repository is the reviewer's call.

## Sandbox limits

Inside `claude plugin eval`, Bash runs in an OS sandbox. It can't reach the
network, and it can read only the plugin under test and the run's own home and
workspace, not the host's Python install. So the runner copies the running
interpreter into the scratch plugin (`.eval-python/`) and puts it first in PATH.

`--web-fetch` (off by default) grants WebFetch to `code.claude.com` on any arm: it
adds `WebFetch(domain:code.claude.com)` to `--allow-tools` and `WebFetch` to
`allowed_tools` in each copied `case.yaml`. Claudit 5 doesn't fetch docs, so its
gate runs without it. `summary.json` records `web_fetch`, and `summarize` refuses
to pool results that differ in it.
