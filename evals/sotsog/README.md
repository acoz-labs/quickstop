# sotsog eval

This suite is sotsog's release gate (issue #216). It gives the same task to two
arms: research an outside idea, compare it with a small repository, decide
whether to adopt it, and write the decision to a file. The arms differ only in
whether the sotsog plugin is loaded. The issue fixes seven pass bars, and the
plan in `docs/changes/216-sotsog/plan.md` fixes the design. This README says
how the suite works and how to run it.

| Arm | Plugin |
|---|---|
| `baseline` | none |
| `sotsog` | a retained copy of `plugins/sotsog/` via `--plugin-dir` |

## How a run works

`bin/sotsog-eval run` copies the fixture repository (`repo/`) and the case's
sources (`cases/<case>/research/`) into a new temporary folder. It then calls
`claude -p` from the repository copy, on the normal Claude login:

```sh
claude -p "<prompt.md, with {research} filled in>" --model claude-sonnet-5-5 --effort high \
  --tools Read,Glob,Grep,Write,Edit,Skill --allowedTools Read Glob Grep Write Edit Skill \
  --add-dir <run>/research --output-format stream-json --verbose --max-budget-usd <cap> \
  --setting-sources project,local --strict-mcp-config --no-session-persistence \
  [--plugin-dir <result dir>/plugin]
```

The environment sets `DISABLE_AUTOUPDATER=1` and
`CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`. There's no Bash and no web tool, so the
only sources are local files, the same for both arms. Each prompt names the
user's link and says that `library/` stands in for the web, but it never names
a library file. The prompt also gives the user's answers to likely follow-up
questions, because a headless run has nobody to answer them.

Each run's `init` record must show the model and no MCP server. It must also
list sotsog at the manifest version from the retained copy (sotsog arm) or
not at all (baseline). A run that fails this check, or dies before the model's
first reply, is invalid and is re-run once. The summary counts the sotsog runs
that called the skill. A run that didn't call it still counts, because the
skill has to trigger from its description.

The decision document is the one Markdown file the run added or changed in
the repository copy. A run that writes no such file, or more than one, fails
every grader.

## Cases

All names, teams, products and URLs are invented.

| Case | Idea | Expected outcomes |
|---|---|---|
| `1-already-have` | Release-note fragments in every pull request, which the repository already has | no, adapt |
| `2-real-gap` | Lint migrations for lock-taking statements, after two lock outages | adopt, adapt |
| `3-breaks-reliance` | Push straight to main and review after merge, which breaks the grant's review condition | no |
| `4-vendor-claim` | AI test selection, claimed by its vendor to save 90% with no baseline | adapt, not now, no |
| `5-flip` | Signed releases with build provenance: not now on evidence alone, but the answers add a deployer requirement | adopt, adapt |

Each case folder holds these files:

- `prompt.md`: the request, the sources line and the scripted answers.
- `case.json`: the library file roles (`report`, `critique`, `competitor`,
  `noise`), and the fixture-specific terms that must never appear in the skill.
- `key.json`: the expected outcome set and whether the case expects a go,
  plus the cold-read items `decided`, `why` and `next` (a `point` the
  document must get across, and a `detail` it needn't). Case 4's key adds the
  two planted gaps.
- `research/`: `link.md` and `library/`.
- `calibration/`: the five hand-written samples and `expected.json`.

## Graders

All graders live in `graders.py` and `judges/`, so the same code grades both
arms and the calibration.

Script graders, which cost nothing:

- **Structure:** the template's comparison table (with a valid fit rating in
  every row), an H1 decision line, `## Revisit when`, `## What the evidence
  shows` with all five skeptical-read labels, `## Implementation brief` on
  adopt or adapt and never otherwise, and `## Sources` with a date in every
  item.
- **Outcome:** read from the first of these that gives a verdict:
  1. the template's H1 decision line;
  2. any Decision, Recommendation or Verdict label in the document;
  3. a verdict right after the colon of any other H1;
  4. any Conclusion, Summary, TL;DR, Bottom line or Short answer label.

  A label is a line that is a heading, starts in bold, or has a colon or
  dash after the label word. Its verdict is read from that line or, failing
  that, from the first sentence of the next paragraph.
  - Only the verdict's opening words count, after lead-ins such as "we'll",
    "I'd recommend" or "<Name> should".
  - A negated modal ("won't", "shouldn't") reads as "not".
  - A negative or hedged subject ("nobody", "maybe") keeps the verdict
    unread.
  - Phrases are matched as whole words, longest entry first, so "not now" is
    never read as "no" and "adopt in part" never as "adopt".

  The tests include real verdict lines from the baseline screen.
- **Depth, script half:** the document cites, by file name or exact title, a
  library file, a `critique` and a `competitor`.

Judges, all Sonnet 5.5. Each runs with no tools, with `--system-prompt`
replacing Claude Code's, under its own `--max-budget-usd`, and is retried
once:

- **reader:** sees the document only, and writes down what was decided, why,
  and what happens next.
- **compare:** sees the key and the reader's notes, never the document, and
  gives PASS or FAIL per item.
- **brief** (cases 2 and 5): could an agent start the work from the
  implementation brief alone?
- **open-questions** (when the outcome is no or not now): the questions a cold
  reader would still need answered.
- **depth** (when the script half passes): sees the document and the cited
  critique and competitor files, and decides whether the document states
  what each says.
- **gaps** (case 4): sees the document and the two gaps, and decides whether
  each is named with its substance.

## Calibration

Each case has five samples, written from the prompt, fixtures and key, never
from a run:

- `good` passes every grader.
- `bad` fails every grader that applies.
- `borderline-pass` is thin but complete.
- `borderline-fail` is the good sample with exactly one defect for each
  grader it targets, so it sits just below the bar. Every other grader is
  expected to pass.
- `plain` is shaped like a baseline document, with a different verdict shape
  in each case.

`expected.json` gives the expected verdict per grader. `calibrate` checks the
script graders at $0, and `tests/test_sotsog_eval.py` runs that check in
`bin/ci`. `calibrate --judges` runs the judges too, which is paid. The gate
refuses to start without a passing judge calibration on a clean tree with the
same suite tree and runner blob.

## Spend

Every paid call appends a row to the CSV ledger given by `--ledger`. The row
records the call's cap, its cost and the `cumulative_usd` total. Before each
call, the runner reserves the call's cap. It refuses any call that could take
the ledger total, plus the caps of calls in flight, past `--stop-line`. Near
the line, it waits for the calls in flight to settle, so it runs one call at a
time rather than refusing early. The stop line defaults to $14, and no flag
can raise it past $20. Every paid command also needs `--max-cost-usd`, a
ceiling for that invocation alone; it's a runner option, not a `claude` flag
(Claude Code 2.1.322 has only `--max-budget-usd`, which every call carries).

## Miss rule and bars

- A task run that errors or hits its cap after replying is graded as it
  stands.
- An invalid run, or a judge that still fails after its retry, counts as a
  miss for sotsog's own thresholds. For the baseline's figures in the
  strictly-above comparisons (bars 2 and 3), it counts as a pass.
- `summarize` reports both views per arm. It computes the bars only for a
  `gate` result, and it marks a result incomplete when a run is missing, the
  guard changed, or the suite tree or runner blob differs from `HEAD`.

## Running

```sh
PY="$(mise where python@3.11.15)/bin/python3"
$PY -B bin/sotsog-eval calibrate                                            # script graders, $0
$PY -B bin/sotsog-eval calibrate --judges --max-cost-usd 3 --ledger <ledger.csv> --output-dir <cal dir>
$PY -B bin/sotsog-eval run --stage screen --case 1-already-have --max-cost-usd 3 --ledger <ledger.csv> --output-dir <dir>
$PY -B bin/sotsog-eval run --stage gate --runs 3 --calibration <cal dir> --task-max-usd <cap> \
  --stop-line <line> --max-cost-usd <ceiling> --ledger <ledger.csv> --output-dir <results>/gate
$PY -B bin/sotsog-eval summarize <dir>
$PY -B bin/sotsog-eval grade <dir>                                          # regrade scripts, $0
```

A result dir holds the following:

- `CANDIDATE.txt`: head, tree, extraction write-tree, plugin tree and digest,
  suite tree and runner blob.
- `candidate.json`, `suite.json`, `settings.json` and `guard.json`.
- The retained `plugin/`, plus `calibration.json` for a gate.
- One folder per case and arm (`<case>-<arm>/`). Each run in it has a
  `record.json` and an `attempt-<n>/` folder holding the transcript, init
  record, prompt, workspace changes, the document and the judge records.
- `summary.json` and `summary.md`.
