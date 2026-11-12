# Plan: sotsog, a portable skill for deciding whether to adopt an outside idea

## Issue

Refs https://github.com/acoz-labs/quickstop/issues/216

Quickstop gains a new plugin, sotsog 0.1.0, whose one skill researches an
outside idea, compares it with the user's repo or workflow and writes a
decision document; it ships only if a frozen, paid eval gate passes all seven
of the issue's bars within $20 of model spend. This PR is the plugin PR. The
pointer PR (`releases.json`, regenerated marketplace index) and the acoz.dev
Quickstop page follow after acceptance and the tag, as the repository's
release takes two PRs.

## Decisions

**Package.** `plugins/sotsog/` exactly as the issue lays it out:
`.claude-plugin/plugin.json` at 0.1.0, `skills/sotsog/SKILL.md` (the seven
phases, under about 300 lines) and four references (`decision-doc.md` with a
filled go and a filled no-go example, `writing.md`, `research.md`,
`comparison.md`), plus `README.md` and an MIT `LICENSE` like the other
plugins. The skill names no tool, argument variable, plugin-root variable or
shell injection; it says "fetch the page", "search the web", "read the
file". Its description triggers on plain requests ("should we adopt X", "is
this worth bringing into our repo", "compare this approach with ours",
"here's a post about how team Y does Z, should we?"). `skills-check.json`
gets no entry, so `bin/check-skills` lints sotsog and runs skills-ref on it.

**Catalog.** The plugin PR adds sotsog's candidate entry to `catalog.json`
(its `claude-code` target, path and acceptance doc) and regenerates
`docs/catalog.md` with `bin/check-marketplace --write`. The advertised entry
in `.claude-plugin/marketplace.json` and the `releases.json` pointer come in
the pointer PR, because promote writes them from an accepted tag. A new
entry isn't a description change to an existing one; if the reviewer reads
the repository rule ("`catalog.json` description changes go in the pointer
PR") as covering it, the entry moves to the pointer PR and nothing else
changes.

**Spend flag.** The issue asks for `--max-cost-usd` on every run. Claude Code
2.1.322 has no such flag (`claude --help` lists only `--max-budget-usd`), so
every paid `claude` call carries `--max-budget-usd`. The acceptance doc says
so. The runner's own whole-invocation ceiling keeps the existing runners'
name, `--max-cost-usd`, and is a runner option, not a `claude` flag.

### Eval design

The suite lives outside the plugin bytes, in `evals/sotsog/`, run by
`bin/sotsog-eval`, following the Writing for Humans quality eval: `claude -p`
from a fresh workspace per run on the normal login, not `claude plugin eval`
(which can't give both arms identical settings with and without the plugin
as simply, and needs scaffold scripts for the fixtures).

**Arms.** Both arms use the same command except for one flag:

```sh
DISABLE_AUTOUPDATER=1 CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 \
claude -p "<prompt.md>" --model claude-sonnet-5-5 --effort high \
  --tools Read,Glob,Grep,Write,Edit,Skill --allowedTools Read Glob Grep Write Edit Skill \
  --add-dir <run>/research --output-format stream-json --verbose \
  --max-budget-usd 1.25 --setting-sources project,local --strict-mcp-config \
  --no-session-persistence [--plugin-dir <result dir>/plugin]
```

- **baseline**: no plugin. Its prompt is the issue's: "Research this idea and
  tell me whether we should adopt it in this repo. Write the decision to a
  file," followed by the case's sources line and scripted answers.
- **sotsog**: `--plugin-dir` on a retained copy of `plugins/sotsog/` taken at
  the candidate tree. Same prompt, word for word. The skill has to trigger
  from its description, as it would for a real user; the summary counts the
  runs where it was loaded, and a run where it wasn't still counts.
- No Bash, no web tools: the only sources are local files, so both arms have
  the same access. Model and effort are fixed now: Sonnet 5.5 at high effort
  (its default, set explicitly). If the first screened run shows the full
  gate can't fit the cap (see Spend), the fallback is medium effort for both
  arms, decided before any counted run and reported to the lead; it's not
  changed after counted results exist.
- Each run's `init` record must show the model, no MCP server, and sotsog at
  0.1.0 from the retained copy (sotsog arm) or no sotsog (baseline). A run
  that fails this is invalid and is re-run once; see the miss rule.

**Prompt shape** (same in both arms, per case `prompt.md`):

1. The request: the baseline sentence above, naming the idea and pointing at
   the user's link.
2. Sources: "There's no web access here. My link is
   `<run>/research/link.md`. The folder `<run>/research/library/` stands in
   for the web: treat it as what a search would find." The prompt never names
   a library file or says which ones matter.
3. Scripted answers: "I can't answer follow-up questions in this session.
   Here are my answers to what you'd likely ask; take them as given, decide,
   and write the decision document." Then three to five numbered answers.

**Fixtures.** One invented, public-safe repository, `evals/sotsog/repo/`,
shared by every case: a small Python command-line service for booking rooms
in a community library network, with a clear workflow in its
`CONTRIBUTING.md`, `docs/decisions/` (two earlier, unrelated decisions, so
every arm has an existing decisions folder and nobody needs to ask where to
write), `changes/` news fragments, a `bin/check` script that runs tests and
lint, a CI config, an incidents folder and a release checklist. Each case
has `research/link.md` (the "user's link", with author, date and URL lines)
and `research/library/` with five to seven short files: two independent
reports, one critique, one competing approach and one or two noise pages.
Every library file starts with a title line; `case.json` records each file's
role (`report`, `critique`, `competitor`, `noise`). All names, teams,
products and URLs are invented under `example.com`/`example.org`.

**Cases and answer keys** (fixed in `key.json` before any sotsog run):

| Case | Idea | Expected outcome set | Why, in the fixtures |
|---|---|---|---|
| 1 `already-have` | Every change carries a release-note fragment | {no, adapt} | The repo already does it (`changes/`, CONTRIBUTING, the check script); adapt only for a minor tweak |
| 2 `real-gap` | Lint migrations for locking operations and rehearse them on a production-size copy | {adopt, adapt} | Two incidents in the repo came from table-locking migrations; nothing checks migrations today |
| 3 `breaks-reliance` | Trunk-based development with direct pushes to main and no required review | {no} | CONTRIBUTING and the funder's grant terms require recorded two-person review on every change |
| 4 `vendor-claim` | AI test selection that "cuts CI time 90%", from the vendor's own blog | {adapt, not now, no} | The author's company sells the tool; no baseline or before-and-after; the repo's CI already takes four minutes |
| 5 `flip` | Signed releases with published build provenance | {adopt, adapt} | On evidence alone it's not now (one downstream user, real upkeep); the scripted answers add that the main deployer requires signed releases with provenance from March 2027 |

Each key also holds the cold-read items, each with a `point` a document must
get across and an optional `detail` it needn't, as in the quality eval:

- **decided**: the outcome and what it covers (for adapt, which principles).
  For a case with two acceptable outcomes, the point is written so that
  either passes.
- **why**: the main reason, from the fixtures.
- **next**: what happens next (a go names the work handed on; a no or not now
  names that nothing changes and what would reopen it).

Case 4's key adds its two planted gaps: **who gains** (the author's company
sells the tool) and **no baseline** (the 90% claim has nothing it was
measured against). `case.json` also lists the case's fixture-specific terms
(invented product, team and tool names) for the overlap check.

Go cases for the brief check are the cases whose key expects a go: 2 and 5,
so 6 runs per arm.

**Graders.** Script graders and judge prompts live in the frozen suite
(`evals/sotsog/graders.py`, `evals/sotsog/judges/*.md`). The runner finds the
decision document as the one Markdown file the run added or changed in the
workspace, outside `research/`. No file, or more than one, fails every
grader for that run.

Script graders, $0:

- **Structure**, pass when all six hold:
  1. a comparison table whose header row is `Principle | How they do it | How
     we do it | Fit`, with at least one row, each Fit cell one of the five
     ratings (already have, partly, gap, conflicts, doesn't apply);
  2. a decision line: the document's H1 matches `# <idea>: <outcome> for
     <repo or workflow>`, with exactly one of adopt, adapt, not now, no;
  3. a `## Revisit when` section with at least one item;
  4. a `## What the evidence shows` section that addresses all five
     skeptical-read questions, each by its label (who gains, measured
     against, what's missing, whose conditions, independent support);
  5. a `## Implementation brief` section when the outcome is adopt or adapt,
     and none when it's no or not now;
  6. a `## Sources` section whose every list item carries a date
     (`YYYY-MM-DD`).
- **Outcome**: the recorded outcome is in the case's expected set. For both
  arms the outcome comes from the H1 decision line when there is one;
  otherwise from the first line that starts with "Decision" or
  "Recommendation" (any heading level, bold or plain). That line is mapped
  with a fixed table: "adopt" → adopt; "adapt", "adopt in part", "partially
  adopt" → adapt; "not now", "defer", "later", "revisit" → not now; "no",
  "do not adopt", "don't adopt", "reject", "decline" → no. A line with no
  match, or with matches for two different outcomes, is a miss; so is a
  negated form of an outcome word ("not adopt" is no, never adopt). The
  table is the same for both arms and is in the unit tests, attacker pass
  included.
- **Depth, script half**: the document cites, by file name or exact title
  line, at least one library file beyond the link, at least one `critique`
  and at least one `competitor`.

Judges, all `claude-sonnet-5-5`, `--system-prompt` replacing Claude Code's,
no tools, `--json-schema` output, `--max-budget-usd 0.10`, seeing only what
each line names:

- **Cold read, reader** (the document only, never the key): writes down
  what was decided, why, and what happens next.
- **Cold read, comparator** (the key and the reader's notes, never the
  document): PASS or FAIL per item (decided, why, next), on substance, not
  wording. Notes that say "none" or "unclear" fail an item.
- **Brief** (the document only; on go-keyed cases): could an agent with no
  other context start the work from the implementation brief alone? Yes or
  no, with reasons. A go-keyed run with no brief scores no.
- **Open questions** (the document only): lists the questions a cold reader
  would still need answered before accepting or acting on the decision,
  counting only questions whose answer the document should hold, not
  curiosity. Scored on runs whose recorded outcome is no or not now.
- **Depth, judge half** (the document and the role list of the case's
  library, never the key): for each cited critique and competitor, does the
  document state what it says, correctly? Depth passes when the script half
  passes and the judge confirms at least one critique and one competitor.
- **Case 4 gaps** (the document and the two gap items): PASS per gap when
  the document names it with its substance (who gains: the vendor's
  commercial stake; baseline: nothing measured against). Naming a topic
  ("possible bias", "limited evidence") fails.

**Miss-counting rule.**

- A run that ends with a task error or hits its `--max-budget-usd` cap is a
  real run: its document (or lack of one) is graded, and every grader it
  fails is a miss.
- A run that fails the `init` check, or dies on an API or network error
  before the model's first reply, is invalid. It's re-run once, logged; a
  second invalid run is a miss on every grader.
- A judge call that errors or hits its cap is "not graded" and is retried
  once; a judge that still can't grade a run is a miss for the sotsog arm and
  is reported, never silently dropped.
- "Above the baseline" means strictly greater, as the issue states: bar 2
  compares sotsog's outcome count with the baseline's, bar 3 compares the
  cold-read item percentages.

**Pass bars**, exactly as the issue fixes them, computed by `summarize`:

| Bar | sotsog needs |
|---|---|
| 1 Structure | 15/15 |
| 2 Outcome | ≥ 14/15 and more than baseline |
| 3 Cold read | ≥ 90% of 45 items (≥ 41) and more than baseline; brief yes in ≥ 5/6 go-case runs |
| 4 Open questions | on its no and not now runs: median 0, none above 1 |
| 5 Case 4 gaps | both gaps named in 3/3 runs |
| 6 Case 5 | outcome in {adopt, adapt} in 3/3 runs |
| 7 Depth | ≥ 14/15 |

Cost and time per run are reported for both arms, not gated.

**Calibration.** Every case gets four hand-written decision documents under
`calibration/`, written from the prompt, fixtures and key, never from a run:

- `good`: passes every grader (structure, outcome, all three cold-read items,
  brief yes on go cases, 0 open questions, depth, both gaps on case 4).
- `bad`: fails every grader that applies (missing sections, outcome outside
  the set, cold-read items missed, brief no, two or more open questions,
  only the link cited, gaps unnamed).
- `borderline-pass`: complete but thin: each point in plain words with little
  detail, one critique and one competitor cited in a sentence each, exactly
  one open question on no-go cases. Must pass every grader, and bar 4's
  "none above 1".
- `borderline-fail`: has the shape but misses the substance: topics without
  points ("there are trade-offs"), a critique cited by name only, a gap named
  as a topic, a brief that says "implement it" with no steps, two open
  questions on no-go cases. Each targeted grader must fail.

The expected verdict for every (case, sample, grader) is in
`calibration/expected.json`. Script graders run on all 20 samples in every
`bin/ci` through `tests/test_sotsog_eval.py`. The judge calibration is one
paid run (`calibrate --judges`) on the frozen tree; every row must match
before any arm runs. A counted run refuses to start without a passing
calibration for the same suite tree and runner blob. The PR reports the
table.

**Freeze.**

- One commit, "test(eval): freeze the sotsog suite", holds `evals/sotsog/`
  (fixtures, prompts, keys, calibration, graders, judge prompts) and
  `bin/sotsog-eval`, before any file of `plugins/sotsog/` exists on the
  branch. If calibration forces a fix before any sotsog run, a new freeze
  commit replaces it and the PR says so; after the first sotsog run, no
  frozen file changes.
- Proof in the PR and the acceptance doc: `git diff <freeze> <head> --
  evals/sotsog bin/sotsog-eval` is empty, and every result's `CANDIDATE.txt`
  records the suite tree, runner blob, candidate head and tree, plugin tree
  and the extraction write-tree, matching the freeze. `summarize` refuses a
  result whose suite tree or runner blob differs from the freeze.
- No overlap: a unit test greps every file under `plugins/sotsog/` for each
  case's listed fixture terms and fails on any hit.

**Runs and order.** Screen sotsog at 1 run per case, case 1 first and alone
(it also proves the plumbing), then cases 2 to 5. The counted gate (3 runs
per case per arm, 30 runs) starts only on a tree the reviewer has cleared,
and only if the screen shows every bar could still pass. Screen runs are
never counted. Three runs at a time.

### Spend

- Ledger: `/Users/alfred/factory/retained/quickstop-216/ledger.csv`, one row
  per paid `claude` call (time, invocation, kind, arm, case, run, its
  `--max-budget-usd`, cost from the result record, `cumulative_usd`).
  Results: `/Users/alfred/factory/retained/quickstop-216/results/<stage>/<case>-<arm>/`,
  one subfolder per finished case-arm, with the run scripts and logs beside
  them. The lead gets both paths before the first paid run, and a message
  before each paid invocation starts.
- The runner reads `cumulative_usd` before every call and won't start one
  when the cumulative total plus the caps of calls in flight plus this call's
  cap would pass the stop line. The stop line is $14 until the lead says go,
  then $20, set by a runner flag; $20 is a hard ceiling no flag lifts. Before
  each invocation the runner also prints its projected cost; if that
  projection would cross $14, I stop and report before starting, so the
  pause never splits an invocation.
- Projection (estimates until measured; the quality eval's Sonnet judge
  calls cost about $0.013 each, and an agentic research run is assumed at
  roughly ten times that eval's $0.05 reply):

| Stage | Calls | Estimate |
|---|---|---|
| Judge calibration, once, plus one retry | 20 documents × ~4.4 judges | $2.60 |
| Screen, 5 sotsog runs plus judges | 5 tasks | $2.10 |
| Gate, baseline (15 runs at ~$0.20) plus judges | 15 tasks | $4.00 |
| Gate, sotsog (15 runs at ~$0.35) plus judges | 15 tasks | $6.25 |
| **Total** | | **$14.95** |
| With 25% margin | | **$18.70** |

  After the first screened run, the projection is redone from measured cost.
  If the full gate with 25% margin no longer fits under $20, I report to the
  lead before any further paid run, with the effort fallback as the
  recommendation. The pause at $14 is expected to fall before the gate; I
  ask for the go with the measured projection then.

## Files that change

- `plugins/sotsog/`: new package (manifest at 0.1.0, `README.md`, `LICENSE`,
  `skills/sotsog/SKILL.md`, four references).
- `catalog.json`: sotsog's candidate entry. `docs/catalog.md`: regenerated.
- `evals/sotsog/`: `README.md`, `repo/`, `cases/<n>-<name>/` (`prompt.md`,
  `case.json`, `key.json`, `research/`, `calibration/`), `graders.py`,
  `judges/*.md`.
- `bin/sotsog-eval`: runner with `calibrate`, `run`, `grade`, `summarize`;
  the ledger and stop line; `CANDIDATE.txt`.
- `tests/test_sotsog_eval.py`: script graders on all calibration samples,
  outcome-table attacker pass, document detection, miss rule, ledger stop
  line, summary completeness, freeze check, fixture-term overlap.
- `.gitignore`: `evals/sotsog/results/`.
- `docs/acceptance/sotsog.md`: per arm, each bar's result, cost and time per
  run, model and Claude Code version, the frozen-suite proof, calibration,
  spend.
- `docs/repository.md`: layout lines for sotsog, its eval and runner, and any
  lesson the lead passes on.

## Order of work

1. This plan, alone, in a draft PR. No code or paid run until plan review
   clears.
2. Suite: the fixture repo, five cases, keys, judge prompts, graders, runner,
   calibration samples and unit tests; `bin/ci` passes. Freeze commit.
3. Paid judge calibration on the frozen tree (lead told first). Fix and
   refreeze if a row misses; no sotsog file exists yet.
4. The plugin and catalog entry; `bin/ci` passes with sotsog linted and
   validated, no exemption; the overlap test passes.
5. Screen: case 1, then cases 2 to 5, one run each (lead told first).
   Redo the projection. If a bar looks out of reach, change the skill (never
   the suite) and screen the new tree.
6. Simplify, docs, open the PR for review, report to the lead with the head
   and tree.
7. After the reviewer clears the tree, ask for the go past $14 with the
   projection, then run the gate: baseline and sotsog, 15 runs each.
8. `summarize`, the acceptance doc, the bar table on the issue and to the
   lead. If any bar fails: no release, and the table is reported as is.

## Risks

- **The same author writes the skill and the suite.** Contained by freezing
  keys, fixtures and graders before the skill exists, the term-overlap test,
  and the reviewer reading the frozen suite before the gate.
- **Strictly above the baseline.** A strong baseline could tie sotsog on
  outcome (both 15/15) and fail bar 2 with nothing wrong in sotsog. The
  issue's wording stands; the plan doesn't reinterpret it.
- **Template-shaped graders.** Structure follows the issue's template, so the
  baseline will fail it; it's gated for sotsog only. Outcome uses one mapping
  for both arms, so the comparison is fair, but a baseline document with an
  unusual decision phrase scores a miss; the summary lists every unmapped
  line so the reviewer can see them.
- **Judge noise.** Calibration includes borderline samples per grader, the
  judges see the least they need, and the comparator never sees the
  document.
- **Cost.** Agentic research runs are the unknown. The first screened run
  measures them; the stop line, per-call caps and the report-before-crossing
  rule keep spend under $20.
- **Headless runs.** The skill asks questions and expects the user to decide;
  the prompt gives the answers and the go-ahead up front, the same for both
  arms. A sotsog run that stops to ask instead of writing the file fails, as
  it should.
- **Shared machine.** Another quickstop job may be running evals; the lead
  staggers paid runs, and the runner only touches its own result folders and
  hashes `~/.claude/settings.json` and `~/.claude/plugins/*.json` around each
  invocation, as the quality eval does.

## Proof

- `bin/ci`, `bin/check-marketplace --base origin/main` and `bin/sdlc check`
  pass at every head, with no `SKIPPED:` line; `bin/check-skills` lints and
  validates sotsog.
- `tests/test_sotsog_eval.py` runs in `bin/ci`: every calibration sample gets
  its expected script verdicts; the outcome table passes its attacker pass
  (qualifiers and negations added to every form); a workspace with zero or two
  new documents fails; the stop line refuses a call that would cross it; a
  summary with a missing run, grader or mismatched suite tree is incomplete.
- The paid calibration table, the screen and the gate result, each with
  `CANDIDATE.txt`, under the retained results folder; the bar table in
  `docs/acceptance/sotsog.md` and on the issue.
- The reviewer can rerun the $0 checks (`bin/sotsog-eval calibrate`,
  `grade <result dir>`, `summarize <result dir>`) on the retained results and
  confirm the freeze diff is empty.

## Rollback

Before release, close the PR; nothing is published. After the plugin PR
merges but before the pointer PR, revert it: no consumer can install sotsog
yet. After the pointer PR, retire the advertised pointer in `releases.json`
through the normal reviewed release change, as the repository did for
Claudit; the 0.1.0 tag stays, as tags are never moved.
