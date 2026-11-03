# Writing for Humans quality baselines (0.3.1)

This is the first measurement of how readable Claude's replies are under three output
styles, from issue #187. The same 7 writing tasks ran 3 times each under the default
style, the built-in Concise style and Writing for Humans 0.3.1. Each reply was graded
by a cold reader for claim, ask and stakes, by a pedantry judge, and by script graders.
The suite, graders and method are in
[the suite README](../../evals/writing-for-humans-quality/README.md).

**Result.** All three styles scored about the same on the main measure. Opening
cold-read hits were 16/63 for default, 21/63 for Concise and 20/63 for Writing for
Humans. Whole-reply hits were 54, 54 and 55 of 63. No arm stated the stakes in its
opening in any of 21 runs. Writing for Humans is clearly better on one measure: it put
an identifier or `file:line` at the start of 9 sentences, against 23–24 for the
others. It was not shorter than Concise (303 against 286 median words), and its runs
cost about 1.7 times as much (/bin/zsh.052 against /bin/zsh.031). Every reply in every arm passed
pedantry and had no repeated sentences, so on these tasks those two graders don't
separate the arms.

The differences on the main measure are a few items out of 63, and the judges are
noisy near the boundary (see [per-item verdicts](#per-item-verdicts)). Treat a gap of
one or two items as noise, not a ranking.

## Candidate and settings

| | |
|---|---|
| Candidate | head `aca646f5a72037b7ba40cc5bdf99815c2635a565`, tree `e03dbb753c2e3f8c87a54ed7dd7598a4f4d6c9d5`, clean |
| Plugin | writing-for-humans 0.3.1, plugin tree `fa2b6e0f0e34e97dcce3f23b161b40e2b365f8c8`, bytes digest `36268ea8…4898` |
| Suite and runner | suite tree `96d97048d6ffd6123dc1bf7c81ea15dbefabdb2d`, runner blob `f096bf5f192dad4d1eea24b4cfe9a32133eb21f6` |
| Task model | `claude-sonnet-5-5` (init record of every run) |
| Judge model | `claude-sonnet-5-5`, `--system-prompt` replacing Claude Code's, no tools, JSON schema output |
| Claude Code | 2.1.317 (init record of every run, and the preflight) |
| Arms | `outputStyle` `default`, `Concise` and `writing-for-humans:writing-for-humans`, via `--settings` |
| Plugin loading | only in the writing-for-humans arm, from a retained copy via `--plugin-dir`, so the arms differ in the plugin as well as the style |
| Tools | `Read`, `Glob`, `Grep` and `Skill` in every arm |
| Isolation | `--setting-sources project,local --strict-mcp-config --no-session-persistence`, normal login, a new empty workspace per run |
| Environment | `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` and `DISABLE_AUTOUPDATER=1` |
| System prompt variant | Claude Code's standard prompt for `claude-sonnet-5-5`; `CLAUDE_CODE_SIMPLE_SYSTEM_PROMPT` and `CLAUDE_CODE_SIMPLE` unset; effort not set (default). The prompt text itself isn't recorded. |
| Limits | `--max-cost-usd 12` for the run; `--max-budget-usd` 0.30 per task and 0.05 per judge call; 3 concurrent jobs |
| When | 3 November 2026, 16:17 to 16:24 UTC (6 min 44 s wall) |

Result dir (not committed):
`~/factory/retained/quickstop-187/counted-e03dbb753c2e/`. It holds `CANDIDATE.txt`,
`suite.json`, `settings.json`, `preflight.json`, `guard.json`, the retained
`plugin/`, `summary.json`, and per run the transcript, `init.json`, the reply, the
grades and every judge record.

## Proof of the active style

- **Preflight, $0, per arm.** Under the same flags, `/output-style` reported each arm's
  style with `(current)`, the init record showed the same `output_style`, and the
  call cost $0. All three arms passed.
- **Per run.** All 63 init records show the arm's `output_style` and
  `claude-sonnet-5-5` and load no MCP server. Every writing-for-humans run lists
  `writing-for-humans` 0.3.1 from the retained copy, and no default or Concise run
  lists the plugin. All 63 runs are valid.
- **What this proves.** The setting resolved to a loaded style, and every run started
  with it. It doesn't show the style's prompt reaching the model, and no check without
  a model call can. Claude Code copies any `outputStyle` value into init, even an
  unknown one, which is why the `(current)` marker is required too. The replies are
  the indirect evidence: Concise replies are the shortest, and Writing for Humans
  replies have far fewer identifier subjects.
- **Guard.** `~/.claude/settings.json` and all three `~/.claude/plugins/*.json`
  (`installed_plugins`, `known_marketplaces`, `plugin-directory-cache-v2`) were
  byte-identical before and after. The retained plugin bytes didn't change.
- `summarize` reports the result complete and a baseline: 3 arms × 7 cases × 3 valid
  runs, every grader scored, and the recorded suite matching the suite on disk.

## Per arm

| | default | concise | writing-for-humans |
|---|---|---|---|
| Opening cold-read hits (/63) | 16/63 | 21/63 | 20/63 |
| Whole cold-read hits (/63) | 54/63 | 54/63 | 55/63 |
| Pedantry passes (/21) | 21/21 | 21/21 | 21/21 |
| Repeated-content count (runs with any) | 0 (0) | 0 (0) | 0 (0) |
| Identifier-subject sentences | 24 | 23 | 9 |
| Case 4 question in first 3 sentences (/3) | 0/3 | 0/3 | 1/3 |
| Median words | 373 | 286 | 303 |
| Mean task cost per run (USD) | 0.0306 | 0.0312 | 0.0518 |
| Mean task time per run (s) | 9.2 | 8.1 | 10.8 |
| Task cost, all 21 runs (USD) | 0.6422 | 0.6560 | 1.0870 |
| Judge cost, all 21 runs (USD) | 0.8084 | 0.7591 | 0.7690 |
| Skill calls (all tool calls) | 0 (58) | 0 (61) | 6 (74) |
| Valid runs | 21 | 21 | 21 |
| init output_style | `default` | `Concise` | `writing-for-humans:writing-for-humans` |
| Model (init) | claude-sonnet-5-5 | claude-sonnet-5-5 | claude-sonnet-5-5 |
| Claude Code (init) | 2.1.317 | 2.1.317 | 2.1.317 |

Opening and whole hits are out of 63: 7 cases × 3 items × 3 runs. Costs are list price
from each run's own result record. A task run's time is Claude Code's `duration_ms`.

## Per case

Each cell gives the opening hits and whole hits for runs 1–3, the pedantry passes and
the median words.

| Case | default | concise | writing-for-humans |
|---|---|---|---|
| 1-worker-report | 0,0,1 / 3,3,3; pedantry 3/3; 443 words | 0,1,0 / 3,3,3; pedantry 3/3; 311 words | 1,1,0 / 3,3,3; pedantry 3/3; 445 words |
| 2-design-note | 0,0,1 / 2,2,2; pedantry 3/3; 378 words | 1,1,2 / 2,2,2; pedantry 3/3; 348 words | 2,1,1 / 2,2,2; pedantry 3/3; 350 words |
| 3-pr-description | 0,1,0 / 3,3,3; pedantry 3/3; 399 words | 0,0,1 / 3,3,3; pedantry 3/3; 304 words | 1,0,1 / 3,3,3; pedantry 3/3; 303 words |
| 4-decision-question | 1,2,1 / 3,3,3; pedantry 3/3; 411 words | 2,2,1 / 3,3,3; pedantry 3/3; 303 words | 0,1,2 / 3,3,3; pedantry 3/3; 316 words |
| 5-status-update | 0,1,0 / 3,3,3; pedantry 3/3; 287 words | 1,0,0 / 3,3,3; pedantry 3/3; 248 words | 0,0,0 / 3,3,3; pedantry 3/3; 272 words |
| 6-factual-answer | 2,2,2 / 2,2,3; pedantry 3/3; 102 words | 2,2,2 / 2,2,3; pedantry 3/3; 62 words | 2,2,2 / 3,2,2; pedantry 3/3; 102 words |
| 7-subagent-handoff | 1,0,1 / 1,2,2; pedantry 3/3; 192 words | 1,1,1 / 2,2,1; pedantry 3/3; 126 words | 1,1,1 / 2,2,2; pedantry 3/3; 178 words |

## Per-item verdicts

Kept so that a later comparison (such as the 1.0 gate) can see a one-item difference
for what it is. Each cell is claim, ask, stakes for one run.

### Per-item verdicts, cold read opening (claim, ask, stakes; P pass, F fail)

| Case | Run | default | concise | writing-for-humans |
|---|---|---|---|---|
| 1-worker-report | 1 | FFF | FFF | FPF |
| 1-worker-report | 2 | FFF | PFF | PFF |
| 1-worker-report | 3 | PFF | FFF | FFF |
| 2-design-note | 1 | FFF | FPF | PPF |
| 2-design-note | 2 | FFF | PFF | PFF |
| 2-design-note | 3 | PFF | PPF | FPF |
| 3-pr-description | 1 | FFF | FFF | PFF |
| 3-pr-description | 2 | PFF | FFF | FFF |
| 3-pr-description | 3 | FFF | PFF | PFF |
| 4-decision-question | 1 | PFF | PPF | FFF |
| 4-decision-question | 2 | PPF | PPF | PFF |
| 4-decision-question | 3 | PFF | PFF | PPF |
| 5-status-update | 1 | FFF | PFF | FFF |
| 5-status-update | 2 | PFF | FFF | FFF |
| 5-status-update | 3 | FFF | FFF | FFF |
| 6-factual-answer | 1 | PPF | PPF | PPF |
| 6-factual-answer | 2 | PPF | PPF | PPF |
| 6-factual-answer | 3 | PPF | PPF | PPF |
| 7-subagent-handoff | 1 | PFF | PFF | PFF |
| 7-subagent-handoff | 2 | FFF | PFF | PFF |
| 7-subagent-handoff | 3 | PFF | PFF | PFF |

### Per-item verdicts, cold read whole (claim, ask, stakes; P pass, F fail)

| Case | Run | default | concise | writing-for-humans |
|---|---|---|---|---|
| 1-worker-report | 1 | PPP | PPP | PPP |
| 1-worker-report | 2 | PPP | PPP | PPP |
| 1-worker-report | 3 | PPP | PPP | PPP |
| 2-design-note | 1 | PFP | PFP | PFP |
| 2-design-note | 2 | PFP | PFP | PFP |
| 2-design-note | 3 | PFP | PFP | PFP |
| 3-pr-description | 1 | PPP | PPP | PPP |
| 3-pr-description | 2 | PPP | PPP | PPP |
| 3-pr-description | 3 | PPP | PPP | PPP |
| 4-decision-question | 1 | PPP | PPP | PPP |
| 4-decision-question | 2 | PPP | PPP | PPP |
| 4-decision-question | 3 | PPP | PPP | PPP |
| 5-status-update | 1 | PPP | PPP | PPP |
| 5-status-update | 2 | PPP | PPP | PPP |
| 5-status-update | 3 | PPP | PPP | PPP |
| 6-factual-answer | 1 | PPF | PPF | PPP |
| 6-factual-answer | 2 | PPF | PPF | PPF |
| 6-factual-answer | 3 | PPP | PPP | PFP |
| 7-subagent-handoff | 1 | PFF | PPF | PPF |
| 7-subagent-handoff | 2 | PPF | PPF | PPF |
| 7-subagent-handoff | 3 | PPF | PFF | PPF |

### Item totals (opening / whole, out of 21 per arm)

| Item | default | concise | writing-for-humans |
|---|---|---|---|
| claim | 12 / 21 | 14 / 21 | 13 / 21 |
| ask | 4 / 17 | 7 / 17 | 7 / 17 |
| stakes | 0 / 16 | 0 / 16 | 0 / 17 |

## Calibration

Run before the counted runs on tree `51c659b8` (head `dd74e9b`). The suite and judges
there are identical to the candidate's; `aca646f` changed only the README. Every case
has four samples, and every grader scored each as expected: **28 of 28 samples, all
checks as expected**. `good` and `borderline-pass` must pass every grader. `bad` must
fail every one. `borderline-fail` names only the topics, and every item whose key
point isn't `none` must fail on both reads. The borderline samples were written from
the prompts and keys, not from any reply. Calibration judges cost $0.63
(`~/factory/retained/quickstop-187/dev/calibration-r1-2/`).

| Case | Sample | Graders as expected | Detail |
|---|---|---|---|
| 1-worker-report | good | 5/5 | opening 3/3 PPP; whole 3/3 PPP; pedantry PASS |
| 1-worker-report | bad | 5/5 | opening 0/3 FFF; whole 1/3 PFF; pedantry FAIL |
| 1-worker-report | borderline-pass | 5/5 | opening 3/3 PPP; whole 3/3 PPP; pedantry PASS |
| 1-worker-report | borderline-fail | 2/2 | opening FFF; whole FFF |
| 2-design-note | good | 5/5 | opening 3/3 PPP; whole 3/3 PPP; pedantry PASS |
| 2-design-note | bad | 5/5 | opening 1/3 FPF; whole 2/3 PPF; pedantry FAIL |
| 2-design-note | borderline-pass | 5/5 | opening 3/3 PPP; whole 3/3 PPP; pedantry PASS |
| 2-design-note | borderline-fail | 2/2 | opening FPF; whole FPF |
| 3-pr-description | good | 5/5 | opening 3/3 PPP; whole 3/3 PPP; pedantry PASS |
| 3-pr-description | bad | 5/5 | opening 0/3 FFF; whole 1/3 PFF; pedantry FAIL |
| 3-pr-description | borderline-pass | 5/5 | opening 3/3 PPP; whole 3/3 PPP; pedantry PASS |
| 3-pr-description | borderline-fail | 2/2 | opening FFF; whole FFF |
| 4-decision-question | good | 6/6 | opening 3/3 PPP; whole 3/3 PPP; pedantry PASS |
| 4-decision-question | bad | 6/6 | opening 0/3 FFF; whole 2/3 PPF; pedantry FAIL |
| 4-decision-question | borderline-pass | 6/6 | opening 3/3 PPP; whole 3/3 PPP; pedantry PASS |
| 4-decision-question | borderline-fail | 2/2 | opening FFF; whole FFF |
| 5-status-update | good | 5/5 | opening 3/3 PPP; whole 3/3 PPP; pedantry PASS |
| 5-status-update | bad | 5/5 | opening 0/3 FFF; whole 0/3 FFF; pedantry FAIL |
| 5-status-update | borderline-pass | 5/5 | opening 3/3 PPP; whole 3/3 PPP; pedantry PASS |
| 5-status-update | borderline-fail | 2/2 | opening FFF; whole FFF |
| 6-factual-answer | good | 5/5 | opening 3/3 PPP; whole 3/3 PPP; pedantry PASS |
| 6-factual-answer | bad | 5/5 | opening 1/3 FPF; whole 1/3 FPF; pedantry FAIL |
| 6-factual-answer | borderline-pass | 5/5 | opening 3/3 PPP; whole 3/3 PPP; pedantry PASS |
| 6-factual-answer | borderline-fail | 2/2 | opening FPF; whole FPF |
| 7-subagent-handoff | good | 5/5 | opening 3/3 PPP; whole 3/3 PPP; pedantry PASS |
| 7-subagent-handoff | bad | 5/5 | opening 0/3 FFF; whole 1/3 PFF; pedantry FAIL |
| 7-subagent-handoff | borderline-pass | 5/5 | opening 3/3 PPP; whole 3/3 PPP; pedantry PASS |
| 7-subagent-handoff | borderline-fail | 2/2 | opening FFF; whole FFF |

How calibration got there, before any counted run:

- Case 3's stakes key was narrowed to the consequence its ask is about.
- Two good samples (cases 5 and 7) were fixed where they broke the 3-sentence or
  80-word opening.
- After review round 1, keys were split into a required `point` and optional
  `detail`, the borderline samples were added, and case 7's ask was changed to agree
  with its prompt's licence requirement.
- The comparator rubric changed three times: after smoke 1, which ran on the first
  rubric; for the point and detail keys; and after the new borderline calibration
  caught a false pass.

## Known limitations

- **No stakes in any opening.** Opening stakes scored 0/21 in every arm. Replies lead
  with the claim and sometimes the ask, and give consequences later. This is the
  clearest gap a 1.0 style could target. It's also the item that most depends on the
  80-word, 3-sentence cut.
- **Case 2's ask key is "none", but every reply asks something.** The task offers no
  Write tool, so every reply, in every arm, ends by asking the reader to paste the
  record into the wiki or enable Write. The comparator correctly fails that against
  "none". It costs each arm the same 3 whole-read items, so comparisons still hold,
  but absolute whole-read scores are 3 lower than the writing alone would earn. Fix
  this in a later suite version (offer Write, or reword the prompt), not by regrading
  this baseline.
- **Pedantry and repeated content are at the ceiling.** All 63 replies passed pedantry
  and none repeated a sentence. Calibration shows both graders catch clear cases, so
  on these tasks neither separates the arms.
- **The writing-for-humans arm used its skill.** It called
  `writing-for-humans:writing-style` in all 6 runs of cases 1 and 2 (the
  investigation write-up and the decision record, the surfaces its description names),
  and in no other run. The other arms made no `Skill` calls. This is the kit as users
  get it, not the style alone, and it accounts for part of the arm's higher cost and
  tool count (74 calls against 58 and 61).
- **Judge noise (L6).** Boundary verdicts vary, for example an ask that passed on notes
  beginning "No explicit decision is requested, but…". Repeated judge calls on the
  same reply weren't measured. Use the per-item tables above, not the totals alone,
  when comparing versions.
- **Identifier grader exemption (L7).** Capitalised names are exempt so that "Node.js
  is the runtime" passes, but that also lets a capitalised file name through:
  "`**Config.json** is wrong.`" isn't flagged. It's rare in practice and known.
- **One model, one version.** Sonnet 5.5 on Claude Code 2.1.317 only, with default
  effort.

## Spend

The issue's cap was $25 at list price, with a pause at $17.50. Every paid call had a
ceiling, and every paid invocation is a row in
`~/factory/retained/quickstop-187/spend-ledger.md`.

| Part | USD |
|---|---|
| Development and calibration (9 judge calibration runs, 2 smokes, 1 smoke regrade) | 3.3184 |
| Counted run: task runs | 2.3852 |
| Counted run: judges | 2.3365 |
| **Total** | **8.0401** |
