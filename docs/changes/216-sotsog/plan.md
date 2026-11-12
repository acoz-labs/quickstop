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
the pointer PR, because promote writes them from an accepted tag. The plan
review ruled that a new candidate entry isn't a description change: promote
reads the catalog at the accepted commit, and `bin/check-marketplace` rejects
a manifest no declared package owns. The entry's description is written in
its final form now; any later change to it goes in a pointer PR.

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
  --max-budget-usd <per-run cap> --setting-sources project,local --strict-mcp-config \
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
  the same access. The model is Sonnet 5.5 for both arms. Effort starts at
  high (its default, set explicitly) and drops to medium for both arms only
  under the go/no-go rule in Spend, which always re-screens at the settings
  the gate will use. Nothing changes after counted results exist.
- The per-run `--max-budget-usd` is the same for both arms: $1.25 for the
  screen, then for the gate at least twice the highest run cost the screen
  measured (see Spend).
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
- **why**: the main reason, from the fixtures. In case 5 the point is the
  deployer's requirement of signed releases with provenance from March 2027,
  so a document that adopts for other reasons fails it and doesn't show the
  flip.
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
- **Outcome**: the recorded outcome is in the case's expected set. The same
  reader serves both arms, and it reads only where a verdict is stated:
  1. The H1 decision line, when it matches the template (`# <idea>:
     <outcome> for <repo or workflow>`); otherwise a verdict right after the
     colon of any other H1 ("# Safe migrations: adopt in part for ...").
  2. Then each decision label in turn: a line whose text starts with
     Decision, Recommendation, Verdict, Conclusion, TL;DR, Bottom line,
     Summary or Short answer and that is a heading, starts in bold, or follows
     the label with a colon or dash, so body text such as "Decision makers
     liked it" isn't a label. The verdict text is what follows the label on
     that line; when that holds no outcome, it's the first sentence of the
     next paragraph. A label with no verdict doesn't stop the search ("##
     Decision drivers" before "## Recommendation"); the first verdict found
     wins.
  3. Only the start of the verdict text counts, after skipping markers,
     punctuation and lead-ins: "my, our or the recommendation is (to)", "I
     or we (would, will) recommend, suggest or propose", "we or I (should,
     will, would, can, must)", "<up to four words> should" ("Lanternhall
     should"), "yes", "to". A negated modal after a subject ("we won't",
     "the team shouldn't") reads as "not". A subject that starts with a
     negative or a hedge ("nobody", "maybe", "perhaps", "whether") is never
     skipped, so "maybe we should adopt" stays unread. The fixed table,
     matched as whole words, longest entry first: "adopt", "adopting",
     "adopted" → adopt; "adapt", "adapting", "adopt in part", "partially
     adopt", "adopt partially", "adopt, partially", "adopt with changes" →
     adapt; "not now", "not yet", "not at this time", "not right now", "hold
     off", "wait", "defer", "deferring", "postpone", "later" → not now; "no",
     "do not adopt", "don't adopt", "not adopt", "not adopting", "not
     adopted", "reject", "decline" → no. Words later in the sentence are
     ignored, so "adopt, with no change to CI" is adopt, and "No: adopting
     would remove review" is no.
  4. No label, or no verdict at any label, is a miss.

  The unit tests cover each shape (H1, `## Recommendation` with the verdict
  in the next paragraph, `Verdict:` inline, a bold label, a `Conclusion`
  heading) and an attacker pass: a qualifier or negation added to every
  allowed form, and an outcome word placed after the verdict start.
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
  curiosity. Called and scored only on runs whose recorded outcome is no or
  not now.
- **Depth, judge half** (the document and the text and role of each cited
  critique and competitor, never the key; called only when the script half
  passes): for each, does the document state what it says, correctly? The
  judge needs the source text to tell. Depth passes when the script half
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
  before the model's first reply, is invalid. It's re-run once, logged.
- A judge call that errors or hits its cap is "not graded" and is retried
  once.
- What's still invalid or ungraded after its retry counts against sotsog and
  in the baseline's favour:
  - for sotsog's own thresholds (every bar's sotsog figure), it's a miss;
  - for the baseline's figures in the strictly-above comparisons (bars 2 and
    3), it's a pass, so a broken judge or a baseline run that never started
    can't hand sotsog a margin it didn't earn.

  The summary reports both counts for each arm: as scored, and how many were
  invalid or ungraded.
- "Above the baseline" means strictly greater, as the issue states and the
  plan review ruled: bar 2 compares sotsog's outcome count with the
  baseline's, bar 3 compares the cold-read item percentages.

**Pass bars**, exactly as the issue fixes them, computed by `summarize`:

| Bar | sotsog needs |
|---|---|
| 1 Structure | 15/15 |
| 2 Outcome | ≥ 14/15 and more than baseline |
| 3 Cold read | ≥ 90% of 45 items (≥ 41) and more than baseline; brief yes in ≥ 5/6 go-case runs |
| 4 Open questions | on its no and not now runs: median 0, none above 1 (no such run at all fails the bar) |
| 5 Case 4 gaps | both gaps named in 3/3 runs |
| 6 Case 5 | outcome in {adopt, adapt} in 3/3 runs |
| 7 Depth | ≥ 14/15 |

Cost and time per run are reported for both arms, not gated.

**Calibration.** Every case gets five hand-written decision documents under
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
- `borderline-fail`: the case's `good` sample with exactly one defect per
  grader it targets, so it sits just below the bar; every other grader is
  expected to pass. Case 1: the critique misstated and the competitor only
  named (depth), a vague trigger and borrowing left unaddressed (open
  questions). Case 2: the brief never says where the lint runs (cold-read
  next, and the brief's "naming the file or step"); the key's next point
  requires that the lint runs in the checks before deploy. Case 3: a true
  reason that isn't the key's (cold-read why), and two holes within the
  borrowing point (open questions). Case 4: "who gains" named with
  substance but the baseline only gestured at (gaps), and two vague triggers
  (open questions). Case 5: the critique misstated and the competitor only
  named (depth), and "how to tell it worked" missing (brief).
- `plain`: shaped like a baseline document, not the template: free headings,
  no comparison table in the template's columns, and the verdict stated a
  different way in each case (`## Recommendation` with the verdict in the
  next paragraph; `Verdict:` inline; a bold "Decision" label; a `##
  Conclusion` heading; an H1 that isn't the template's). Each has an expected
  outcome in its case's set and expected cold-read, brief, open-question,
  depth and gap verdicts; structure is expected to fail. This calibrates the
  graders that score the baseline on what the baseline writes.

The expected verdict for every (case, sample, grader) is in
`calibration/expected.json`. Script graders run on all 25 samples in every
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
  evals/sotsog bin/sotsog-eval tests/test_sotsog_eval.py` is empty, and every result's `CANDIDATE.txt`
  records the suite tree, runner blob, candidate head and tree, plugin tree
  and the extraction write-tree, matching the freeze. `summarize` refuses a
  result whose suite tree or runner blob differs from the freeze.
- No overlap: a unit test greps every file under `plugins/sotsog/` for each
  case's listed fixture terms and fails on any hit.

**Runs and order.** The screen is sotsog at 1 run per case plus 1 baseline
run on case 1, so both arms' costs are measured. Case 1 runs first and alone
in both arms (it also proves the plumbing), then sotsog on cases 2 to 5. The
counted gate (3 runs per case per arm, 30 runs) starts only on a tree the
reviewer has cleared, only if the screen shows every bar could still pass,
and only under the go/no-go rule in Spend. Screen runs are never counted.
Three runs at a time, dropping to one near the stop line (see Spend).

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
  cap would pass the stop line. The stop line is $14, fixed by the requester;
  only a go relayed from case-sotsog through the lead raises it, to $20, and
  $20 is a hard ceiling no flag lifts. It runs three calls at a time while
  the room under the stop line covers three caps, and one at a time after
  that.

**Projection.** Estimates until measured. Judge calls are taken at $0.015
each (the quality eval measured about $0.013), about 4.4 per document. Task
runs use the plan review's expectation for 20 to 30 turns at high effort:
$0.50 to $0.80 per sotsog run and $0.30 to $0.50 per baseline run, so the
midpoints below.

| Stage | What | Estimate |
|---|---|---|
| Judge calibration | 25 documents, ~110 judge calls | $1.65 |
| Re-calibration after a refreeze, if one is needed | the same | $1.65 |
| Screen | 5 sotsog runs, 1 baseline run, judges | $4.05 |
| One re-screen (a skill change, or medium effort) | the same | $4.05 |
| Gate at high effort | 15 baseline runs at $0.40, 15 sotsog at $0.65, judges | $17.75 |

At these estimates the high-effort gate doesn't fit after the screen: about
$5.70 spent leaves $14.30, and $17.75 × 1.25 is $22.20. The rule below
decides on measured numbers, not on this table.

**Go/no-go rule, applied after every screen and re-screen.** Let *spent* be
`cumulative_usd` from the ledger (every screen and re-screen counts), and
*G* the measured gate cost at the screened settings: 15 × the baseline
run's cost + 15 × the mean sotsog run cost + 30 × the mean judge cost per
document.

1. **Fit under the cap.** If spent + 1.25 × G ≤ $20, the gate is possible at
   these settings. If not, and the screen was at high effort, switch both
   arms to medium and re-screen (all five sotsog cases and the baseline on
   case 1), so the screen always measures the settings the gate will use;
   then apply this rule again. If it doesn't fit at medium either, stop and
   report to the lead: no gate starts that can't finish, because a gate cut
   off by the ceiling is incomplete, which means no release.
2. **The $14 pause.** If spent + 1.25 × G would take total spend past $14,
   I stop before starting the counted gate and report the measured numbers
   (spent, per-run means and highest run per arm, G, the settings) to the
   lead. Only a go from case-sotsog, relayed by the lead, lets the gate run
   past $14; with that go the stop line is $20 for the whole gate, so it never
   pauses partway. If the projection stays at or under $14, the gate runs
   with the stop line at $14, as the brief says, and if it reaches $14
   anyway it stops and I report.
3. **Per-run cap.** The gate's `--max-budget-usd` per task run is twice the
   highest run cost the screen measured at the gate's settings, rounded up
   to the next $0.05, the same for both arms. The projection uses means; the
   runner reserves caps, so if it refuses a gate run near the stop line, the
   gate is incomplete and I report it rather than raise anything.

The same rule covers the screen itself: if starting a screen or re-screen
would take projected spend past $14, I stop and report first.

## Files that change

- `plugins/sotsog/`: new package (manifest at 0.1.0, `README.md`, `LICENSE`,
  `skills/sotsog/SKILL.md`, four references).
- `catalog.json`: sotsog's candidate entry. `docs/catalog.md`: regenerated.
- `evals/sotsog/`: `README.md`, `repo/`, `cases/<n>-<name>/` (`prompt.md`,
  `case.json`, `key.json`, `research/`, `calibration/`), `graders.py`,
  `judges/*.md`.
- `bin/sotsog-eval`: runner with `calibrate`, `run`, `grade`, `summarize`;
  the ledger and stop line; `CANDIDATE.txt`. A result folder holds one
  `<case>-<arm>/` folder per case and arm (the gate's at
  `/Users/alfred/factory/retained/quickstop-216/results/gate/`), each run in
  `run-<n>/` with its `record.json` and `attempt-<n>/` evidence.
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
5. Screen (lead told first): case 1 in both arms, then sotsog on cases 2
   to 5. Apply the go/no-go rule to the measured costs, re-screening at
   medium effort if it says so. If a bar looks out of reach, change the skill
   (never the suite) and re-screen the new tree; every re-screen counts
   against the rule.
6. Simplify, docs, open the PR for review, report to the lead with the head
   and tree.
7. After the reviewer clears the tree, apply the go/no-go rule. If the
   gate's projection passes $14, stop and report the measured numbers; run
   the gate (baseline and sotsog, 15 runs each) only on a go from case-sotsog
   relayed by the lead, with the stop line at $20. Otherwise run it with the
   stop line at $14.
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
  baseline will fail it; it's gated for sotsog only. The outcome reader
  handles the common non-template shapes and is calibrated on a
  baseline-shaped document per case before any run. A baseline verdict in a
  shape it doesn't know still scores a miss, and grading can't change after
  results, so this is a known limit of bar 2's comparison.
- **Judge noise.** Calibration includes borderline samples per grader, the
  judges see the least they need, and the comparator never sees the
  document.
- **Cost.** At the costs the plan review expects, the high-effort gate
  doesn't fit and even the medium one may not. The screen measures both
  arms, the go/no-go rule picks the settings or stops before a gate that
  can't finish, and the stop line and per-call caps keep spend under $14
  without a go and under $20 with one. A likely result is a report to the
  lead with measured numbers and no gate.
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
