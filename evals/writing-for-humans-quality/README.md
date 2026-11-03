# Writing for Humans quality eval

Writing for Humans exists to make what Claude writes easy to read at human speed:
understood cold, clear without being pedantic, little repetition, concise without
losing clarity. This suite measures that (issue #187). It runs the same seven writing
tasks under three output styles and grades each reply the same way:

| Arm | `outputStyle` | Plugin loaded |
|---|---|---|
| `default` | `default` | no |
| `concise` | `Concise` (built in) | no |
| `writing-for-humans` | `writing-for-humans:writing-for-humans` | yes, a retained copy via `--plugin-dir` |

Only the writing-for-humans arm loads the plugin. Its `writing-style` skill is one
Claude can call, so loading the plugin in the other arms would give them part of the
kit. Every arm is offered the same tools: `Read`, `Glob`, `Grep` and `Skill`.

It is separate from [the regression check](../writing-for-humans/README.md), which
runs with the default style and never judges prose. This suite changes no guidance
and no plugin bytes; the runner copies the plugin into the result dir and loads that
copy.

## How a run works

`bin/writing-for-humans-quality-eval run` calls `claude -p` once per arm, case and
run, from a new empty workspace holding a copy of the case's `fixture/`, on the
normal Claude login:

```sh
claude -p "<prompt.md>" --model <model> --settings '{"outputStyle":"<style>"}' \
  --tools Read,Glob,Grep,Skill --allowedTools Read Glob Grep Skill \
  --output-format stream-json --verbose --max-budget-usd <cap> \
  --setting-sources project,local --strict-mcp-config --no-session-persistence \
  [--plugin-dir <result dir>/plugin]
```

User settings, MCP servers and session files are left out. The environment sets
`CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` and `DISABLE_AUTOUPDATER=1`; the second also stops
the background marketplace refresh, which would otherwise rewrite
`~/.claude/plugins/known_marketplaces.json` during a run. The runner hashes
`~/.claude/settings.json` and `~/.claude/plugins/{installed_plugins,known_marketplaces}.json`
before and after, and a change makes the result incomplete.

### Proof of the active style

Claude Code copies any `outputStyle` value into the session's `init` record, even a
style that doesn't exist, so `init` alone proves nothing. Each run therefore needs two
things:

1. **Preflight, per arm, no model call.** `/output-style` under the same flags lists
   the styles and marks the active one `(current)`. An unknown name gets no marker.
   The preflight must cost $0. Results go to `preflight.json`.
2. **Per run.** The run's `init` record must show the arm's `output_style` and the
   requested model, list `writing-for-humans` at the manifest version from the retained
   copy (writing-for-humans arm), or not list it at all (other arms), and load no MCP
   server. A run that fails this is invalid and doesn't count.

`bin/writing-for-humans-quality-eval preflight` runs just the preflight.

## Cases

Each case directory holds `prompt.md` (the request), `fixture/` (the workspace),
`key.json` (the answer key) and `calibration/good.md` and `bad.md`. Fixtures are
invented. The key gives the reply's correct **claim** (what's true or done), **ask**
(what the reader must decide or do, or `none`) and **stakes** (what changes depending
on the answer).

1. `1-worker-report`: summarise an investigation from logs, notes and a config.
2. `2-design-note`: a decision record from a meeting transcript.
3. `3-pr-description`: a PR description from a diff, flagging an open question.
4. `4-decision-question`: a release step that needs a choice only the user can make.
5. `5-status-update`: resume a work session from its log.
6. `6-factual-answer`: a short answer about a small repository.
7. `7-subagent-handoff`: relay a subagent's raw, identifier-heavy return to the user.
   The subagent's return is a fixture, so every arm relays the same text.

## Graders

What counts as a sentence: fenced code and table rows are left out as structured data.
Each heading, list item and paragraph starts a new unit, and paragraphs split into
sentences at `.`, `?` or `!` followed by a capital, digit or code span (common
abbreviations such as "e.g." don't split). Headings are not sentences.

Model judges (`judges/*.md`; Sonnet, `--system-prompt` replacing Claude Code's, no
tools, JSON schema output):

- **Cold read, opening (main measure).** A reader sees only the opening: the reply up
  to its third sentence, cut to the first 80 words when that is shorter. Headings
  before the third sentence are kept and their words count. The reader writes down
  the claim, ask and stakes. It never sees the key.
- **Cold read, whole.** Another reader does the same with the whole reply.
- A comparator gets the key and both sets of notes, never the reply, and gives
  PASS or FAIL per item. It grades substance, not which label the reader used.
- **Pedantry.** Given the request and the reply, FAIL when the reply explains what a
  competent colleague already knows or pads with process narration and filler.

Script graders (no model):

- **Repeated content:** sentences that repeat an earlier one, either the same words
  (4 or more) or 5-word shingle Jaccard ≥ 0.6. No line is exempt; a quoted or listed
  repeat still counts. Reported as a count.
- **Words:** words outside fenced code. Reported, not pass/fail.
- **Identifier subject:** sentences whose first token is a code span, `file:line`, a
  call, a snake_case or camelCase name, a path or a file name. "The `deliver()`
  function loops" passes; "`deliver()` loops" doesn't. Negated or quoted sentences
  are not exempt.
- **Case 4 question:** one of the first three sentences ends in `?`.

## Calibration

`calibrate` grades every case's good and bad samples. The good sample must pass every
grader: no repeats, no identifier subjects, the case 4 question, 3 of 3 on both cold
reads, and pedantry PASS. The bad sample must fail every one: at least one repeat and
one identifier subject, no early question, an opening that misses the claim and gets
at most 1 of 3, a whole read that gets at most 2 of 3, and pedantry FAIL. Script
graders cost nothing; `--judges` adds the model judges (about $0.35 for all 14
samples). The unit tests run the script half on every `bin/ci`.

## Pass rule and summary

`summarize <result dir>` checks the result against `suite.json`, the suite the run
recorded: every arm and case with `--runs` valid runs, every grader scored, a passing
preflight per arm, and an unchanged guard. Anything short of that is listed as a
problem and the result is not complete. A `--case` or `--arm` run is a subset and
never a baseline; a baseline is a complete result with 3 runs. A run whose judges
failed or hit the budget is reported as not graded, never as a fail.

## Running

Needs Claude Code with a Claude login and Python 3.11+ first in PATH. Every paid
command takes a ceiling for the whole invocation (`--max-cost-usd`), and each call gets
its own `--max-budget-usd` (`--task-max-usd`, default $0.30; `--judge-max-usd`,
default $0.05), never more than what's left. `--ledger <file>` appends the
invocation's spend to a Markdown ledger.

```sh
export PATH="$(mise where python@3.11.15)/bin:$PATH"
bin/writing-for-humans-quality-eval preflight
bin/writing-for-humans-quality-eval calibrate                      # script graders, $0
bin/writing-for-humans-quality-eval calibrate --judges --max-cost-usd 1
bin/writing-for-humans-quality-eval run --model claude-sonnet-5-5 --runs 3 --max-cost-usd 12
bin/writing-for-humans-quality-eval summarize <result dir>
bin/writing-for-humans-quality-eval grade <result dir>             # regrade scripts, $0
bin/writing-for-humans-quality-eval grade <result dir> --judges --max-cost-usd 3
```

A result dir (default `evals/writing-for-humans-quality/results/<UTC timestamp>/`,
git-ignored) holds `CANDIDATE.txt` (head, tree, plugin tree and digest, suite tree,
runner blob), `suite.json`, `settings.json` (model, Claude Code version, flags,
environment), `preflight.json`, `guard.json`, the retained `plugin/`, and per run
`runs/<arm>/<case>/run-<n>/` with `transcript.jsonl`, `init.json`, `output.md`,
`record.json` and `judges/`. `summary.json` and `summary.md` hold the per-arm table.
