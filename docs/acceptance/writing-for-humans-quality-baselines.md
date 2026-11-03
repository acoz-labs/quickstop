# Writing for Humans quality baselines (0.3.1)

The current baseline is [the 1.0 re-baseline on the frozen suite](#10-re-baseline-on-the-frozen-suite-189)
(#189: 9 cases, 5 runs). The 1.0 gate is measured against it. The sections up to there
record the first, #187 baseline on the earlier 7-case suite.

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
cost about 1.7 times as much ($0.052 against $0.031). Every reply in every arm passed
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
- **Case 2's ask key is "none", but every reply asks something.** All 9 whole-read
  asks failed, 3 in each arm. Two things in the setup invite an ask. The task offers
  no Write tool, so replies ask the reader to paste the record into the wiki or enable
  Write (default run 1, Concise runs 1 and 3, Writing for Humans runs 1–3). The
  transcript ends with Theo, who was to write it up, saying he's out and asking
  whoever writes it to post it, so replies also ask who owns posting the record
  (default runs 2 and 3, Concise run 2, and alongside the paste request in Concise run 1
  and Writing for Humans runs 1 and 2). Some readers also picked up an optional
  follow-up, such as checking the record's date. The comparator correctly fails these
  against "none". Each arm loses the same 3 whole-read items, so comparisons still
  hold, but absolute whole-read scores are 3 lower than the writing alone would earn.
  Fix this in a later suite version, not by regrading this baseline: offer Write, or
  reword the prompt and transcript so no posting step is left open, or key the ask as
  "post the record to the wiki".
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

## 1.0 re-baseline on the frozen suite (#189)

The suite was fixed and extended for #189, then re-baselined and frozen.
- Case 2's ask is now keyed as posting the record to the wiki.
- Capitalised file names count as identifiers.
- Two long cases were added: 8, an incident report, and 9, a design doc.
- There are 5 runs per case per arm.
- Calibration is enforced before counting.

The 1.0 gate is measured against this section. The sections above are the #187 baseline on the earlier 7-case, 3-run suite; don't compare those numbers with these.

**Result.** On the opening, Writing for Humans 0.3.1 leads Concise by 6 items: 44 against 38 of 135, with Default at 28. Opening stakes are still almost absent: 1 item in 135 for 0.3.1, and none for the other arms.
- Whole-reply reads are level, at 126, 123 and 123.
- 0.3.1 has the fewest sentences led by an identifier: 43, against 46 for Concise and 55 for Default.
- 0.3.1 has no repeated sentences on the long cases.
- 0.3.1 costs about 1.5 times as much per run as Concise ($0.0752 against $0.0488).

The long cases did what they were added for. Replies ran 1,188 to 1,654 median words, and repetition and pedantry each failed at least once.

### Frozen suite

From the merge of this PR, the suite, runner, graders and keys don't change for the rest of #189.

| | |
|---|---|
| Suite tree | `evals/writing-for-humans-quality` = `c8a8bf86b6e3f60a096e784c4feec36dcc64513c` |
| Runner blob | `bin/writing-for-humans-quality-eval` = `f03bee3afd9b36c7329b50bd089a7ea7586b33d2` |
| Judges | `judges/reader.md`, `judges/compare.md`, `judges/pedantry.md` inside the suite tree |
| Task model | `claude-sonnet-5-5` |
| Judge model | `claude-sonnet-5-5`, matched by the runner between calibration and counted runs |
| Claude Code | 2.1.317, recorded and not matched; a later run on another version says so in its summary |

### Candidate and settings

| | |
|---|---|
| Candidate | head `b19cdf3747f22eaaecdebf6b5dde07af2ccb7835`, tree `1d1fe0d5b3be71528ffb5003beee080465a903b2`, clean, no stray suite files |
| Plugin | writing-for-humans 0.3.1, plugin tree `fa2b6e0f0e34e97dcce3f23b161b40e2b365f8c8`, bytes digest `36268ea8…4898` |
| Arms, tools, isolation, environment | as for #187 above: `default`, `Concise` and `writing-for-humans:writing-for-humans`. The plugin loads only in its own arm, from a retained copy. All arms get `Read`, `Glob`, `Grep` and `Skill`, plus `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` and `DISABLE_AUTOUPDATER=1`. `CLAUDE_CODE_SIMPLE_SYSTEM_PROMPT` and `CLAUDE_CODE_SIMPLE` are unset, and effort is not set. |
| Limits | `--max-cost-usd 16` for the run; `--max-budget-usd` 0.30 per task and 0.05 per judge call; 3 concurrent jobs |
| When | 3 November 2026, preflight 19:44 UTC, guard closed 20:06 UTC |

The result dir is not committed: `~/factory/retained/quickstop-189/counted-b19cdf3/`. The calibration is in `~/factory/retained/quickstop-189/calibration-gate/`, and a copy is in the result dir.

### Calibration

The calibration ran on the candidate head, on a clean tree, with no stray files and the Sonnet 5.5 judges. Every sample of every case scored as expected on every grader: **36 of 36 samples, 192 of 192 checks**. It cost $0.8567. The rules are as in the suite README:
- `good` and `borderline-pass` pass every grader.
- `bad` fails every grader.
- `borderline-fail` fails every item whose key isn't `none`, on both reads.

The samples for cases 8 and 9 and the new case 2 samples were written from the keys. Before this run, two case 2 samples failed: one implied the ask, and the other put the ask inside the wiki record, which pedantry flagged. Both were reworded. The run refused to start without this calibration, and summarize checks it.

### Proof of the active style

- **Preflight, $0, per arm.** `/output-style` showed each arm's style as `(current)`, its init record matched, and it cost $0. All three passed.
  - The reviewer ran negative controls through the same path: `outputStyle` `nosuch`, and the plugin style without `--plugin-dir`. In both, init echoes the value but no `(current)` line appears, so the preflight rejects them.
- **Per run.** All 135 init records are valid: each shows the arm's `output_style`, `claude-sonnet-5-5` and Claude Code 2.1.317, with no MCP server.
  - Every writing-for-humans run lists `writing-for-humans` 0.3.1 from the retained copy.
  - No default or Concise run lists the plugin.
  - As in #187, this proves the setting resolved to a loaded style and each run started with it. It doesn't show the prompt reaching the model.
- **Skill use.** The writing-for-humans arm called its `writing-style` skill 20 times, in all 5 runs of cases 1, 2, 8 and 9. The other arms made no `Skill` calls.
- **Guard.** The guard was hashed before and after the run: `~/.claude/settings.json`, `installed_plugins.json`, `plugin-directory-cache-v2.json` and `known_marketplaces.json`. The retained plugin bytes didn't change. One file did; see the guard exception below.

### Guard exception (accepted by the lead)

`summarize` reports this result as not complete for one reason only: `~/.claude/plugins/known_marketplaces.json changed during the run`. Every other check passes.

- **Before and after.** The sha256 was `f71590d0e1e3ec7642f19f8567d909494478a5f4f88446c11444e6ce881228cf` before the run and `b8cd20663b15f68e0460e88d6a4dbb45f7c22bcde4808e864661785684d88bad` after.
- **What changed.** The `lastUpdated` field of the `claude-plugins-official` marketplace entry, now `2026-11-03T19:49:53.839Z`. That falls between the preflight and the guard's close. The marketplace's install directory wasn't touched.
- **What stayed the same.** `settings.json`, `installed_plugins.json` and `plugin-directory-cache-v2.json` are byte-identical.
- **No effect on the arms.** They run with `--setting-sources project,local` and never load that marketplace.
- **Likely writer.** Every eval call ran with `DISABLE_AUTOUPDATER=1`. Three quickstop-192 factory sessions started on the same machine at 19:43–19:44 UTC without it. The writer is most likely one of them, but that can't be proven from the bytes.
- **Why it was accepted.** A re-run would have ended past the $30 cap.
- **Procedure from here.** Every later paid run copies the guarded files into a sidecar folder next to its result dir before the run and diffs them afterwards. That procedure lives outside the frozen runner, so a future trip can show exactly which bytes changed.

### Per arm

| | default | concise | writing-for-humans |
|---|---|---|---|
| Opening cold-read hits (/135) | 28 | 38 | 44 |
| Opening: claim / ask / stakes (/45 each) | 19 / 9 / 0 | 25 / 13 / 0 | 27 / 16 / 1 |
| Whole cold-read hits (/135) | 126 | 123 | 123 |
| Whole: claim / ask / stakes (/45 each) | 45 / 41 / 40 | 45 / 42 / 36 | 45 / 42 / 36 |
| Pedantry passes (/45) | 45 | 44 | 44 |
| Repeated-content count (runs with any) | 2 (2) | 1 (1) | 0 (0) |
| Identifier-subject sentences | 55 | 46 | 43 |
| Case 4 question in first 3 sentences (/5) | 0 | 0 | 2 |
| Cases 8 and 9: repeats (runs with any) | 1 (1) | 1 (1) | 0 (0) |
| Cases 8 and 9: pedantry passes (/10) | 10 | 9 | 9 |
| Cases 8 and 9: median words | 1,456 | 1,316 | 1,497 |
| Median words, all runs | 383 | 307 | 323 |
| Mean task cost per run (USD) | 0.0517 | 0.0488 | 0.0752 |
| Mean task time per run (s) | 19.4 | 16.1 | 21.9 |
| Task cost, all 45 runs (USD) | 2.3257 | 2.1938 | 3.3838 |
| Judge cost, all 45 runs (USD) | 2.0376 | 1.8625 | 1.9809 |
| Skill calls (all tool calls) | 0 (195) | 0 (194) | 20 (237) |
| Valid runs | 45 | 45 | 45 |

Hits are out of 135: 9 cases × 3 items × 5 runs. Costs are list price, taken from each run's own result record.

### Per case

Each cell gives the opening hits and then the whole hits for runs 1–5, the pedantry passes, the median words, and any repeats.

| Case | default | concise | writing-for-humans |
|---|---|---|---|
| 1-worker-report | 0,1,1,1,1 / 3,3,3,3,3; pedantry 5/5; 455 words | 0,0,1,0,1 / 3,3,3,3,3; pedantry 5/5; 321 words | 2,1,1,2,1 / 3,3,3,3,3; pedantry 5/5; 502 words |
| 2-design-note | 1,0,2,2,1 / 3,3,3,3,3; pedantry 5/5; 347 words | 1,2,0,2,1 / 3,3,3,3,3; pedantry 5/5; 292 words | 1,1,2,0,2 / 3,3,3,2,3; pedantry 5/5; 367 words |
| 3-pr-description | 0,1,0,1,1 / 3,3,3,3,3; pedantry 5/5; 390 words | 0,1,1,0,0 / 3,3,3,3,3; pedantry 5/5; 307 words | 1,1,0,0,0 / 3,3,3,3,3; pedantry 5/5; 283 words |
| 4-decision-question | 0,2,1,0,1 / 3,3,3,3,3; pedantry 5/5; 433 words; 1 repeat | 2,2,1,2,2 / 3,3,3,3,3; pedantry 5/5; 312 words | 2,2,2,1,2 / 3,3,3,3,3; pedantry 5/5; 302 words |
| 5-status-update | 0,0,0,0,0 / 3,3,3,3,3; pedantry 5/5; 293 words | 0,0,0,1,0 / 3,3,3,3,3; pedantry 5/5; 228 words | 0,1,0,1,0 / 3,3,3,3,3; pedantry 5/5; 280 words |
| 6-factual-answer | 2,1,2,2,1 / 3,3,3,3,3; pedantry 5/5; 99 words | 2,2,2,2,2 / 2,2,2,2,2; pedantry 5/5; 63 words | 2,2,2,2,2 / 3,2,2,2,2; pedantry 5/5; 89 words |
| 7-subagent-handoff | 1,0,1,0,1 / 1,2,1,1,1; pedantry 5/5; 191 words | 1,1,1,1,1 / 2,1,1,2,2; pedantry 5/5; 117 words | 1,1,1,1,1 / 2,2,2,1,1; pedantry 5/5; 164 words |
| 8-incident-report | 0,0,0,0,0 / 3,3,3,3,3; pedantry 5/5; 1654 words | 1,0,1,0,1 / 3,3,3,3,3; pedantry 5/5; 1354 words | 0,1,1,1,0 / 3,3,3,3,3; pedantry 5/5; 1638 words |
| 9-design-doc | 0,0,0,0,0 / 3,3,3,3,3; pedantry 5/5; 1363 words; 1 repeat | 0,0,0,0,0 / 3,3,3,3,3; pedantry 4/5; 1188 words; 1 repeat | 0,0,0,0,0 / 3,3,3,3,3; pedantry 4/5; 1424 words |

Every arm scored 0 on case 9's opening, and nearly 0 on case 8's. The long replies open with a title and metadata such as status, contributors and dates, so the first 3 sentences rarely reach the point. Bold run-in labels also use up opening sentences in every arm; this is a known limitation, recorded in the suite README.

### 1.0 gate bars from these numbers

Each bar is in the unit that `summary.md` reports.

| Bar | Basis | 1.0 must reach |
|---|---|---|
| Opening cold-read ≥ 1.5 × Concise | Concise 38/135 = 0.2815 per item | ≥ 57/135 (0.4222 per item) |
| Opening stakes above 0 | stakes items in the opening, all arms | ≥ 1/45 |
| Whole cold-read no lower than 0.3.1 | 0.3.1 123/135 | ≥ 123/135 |
| Identifier-led sentences no more than 0.3.1 | 0.3.1 43 | ≤ 43 |
| Repetition on cases 8 and 9 no worse than 0.3.1 | 0.3.1 0 repeats in 10 runs | 0 |
| Pedantry on cases 8 and 9 no worse than 0.3.1 | 0.3.1 9/10 | ≥ 9/10 |
| Median words ≤ Concise × 1.1 | Concise 307 | ≤ 337.7 |
| Mean task cost per run ≤ 0.3.1 | 0.3.1 $0.0752 | ≤ $0.0752 |
| #172 regression suite | `bin/writing-for-humans-eval` | passes |
| Style active in every 1.0 run | preflight `(current)` at $0, plus per-run init, as above | every run valid |

**Screen threshold.** A candidate's screen is 1 run per case in the 1.0 arm only: 9 runs, or 27 opening items. It goes to the full gate only if both hold:
- Its opening reaches 1.5 × 0.2815 = 0.4222 per item, which is at least **12 of 27** opening items (11.4 rounded up). Per run, that's 3 × 0.4222 = 1.27 hits.
- Its opening stakes are above 0.

Screens are recorded separately and never count toward the gate.

### Spend

The cap for #189 is $30 at list price. Every paid invocation is a row in `~/factory/retained/quickstop-189/spend-ledger.md`.

| Part | USD |
|---|---|
| Development calibration (all 9 cases, then case 2 again) | 1.2030 |
| Smoke (cases 2, 8 and 9 × 3 arms × 1 run) | 1.3509 |
| Calibration on the candidate head | 0.8567 |
| Counted re-baseline (135 runs: task 7.9033, judges 5.8810) | 13.7842 |
| **Cumulative** | **17.1948** |

## 1.0 candidate screens (#189; never counted toward the gate)

Each screen is 1 run per case in the 1.0 arm only: 9 runs, 27 opening items. They ran on the frozen suite (`c8a8bf86`, runner `f03bee3a`) with the re-baseline's model, judges and limits. Each had a config sidecar before and after the run, and all three were unchanged. A candidate goes to the full gate only if both hold:
- its opening reaches at least 12 of 27 items
- its opening stakes are above 0

The other columns preview the gate bars at screen size. With 9 runs they are noisy and decide nothing.

| Candidate (plugin tree) | Opening (/27) | Opening stakes (/9) | Whole (/27) | Identifier subjects | Median words | Task $/run | Pedantry (/9) | Cases 8 and 9: repeats, pedantry | Screen $ |
|---|---|---|---|---|---|---|---|---|---|
| A `36ca75f5` | 18 | 5 | 26 | 10 | 291 | 0.0597 | 8 | 0, 2/2 | 0.9174 |
| B `de92b47f` | 17 | 3 | 26 | 1 | 357 | 0.0581 | 9 | 0, 2/2 | 0.9027 |
| C `0e58041f` | 13 | 2 | 26 | 1 | 301 | 0.0546 | 9 | 1, 2/2 | 0.8689 |
| Gate bar, scaled to 9 runs | ≥ 12 | ≥ 1 | ≥ 24.6 | ≤ 8.6 | ≤ 337.7 | ≤ 0.0752 | — | 0, ≥ 9/10 over the gate | — |

- **A** is the first 1.0 style, at 553 tokens. All 10 identifier subjects came from one case 8 reply that listed its evidence files with each file name first.
- **B** is A plus one line: the identifier rule also covers list items, with a generic example. That fixed the identifier count, but replies ran longer in 7 of 9 cases.
- **C** is B with the support after the opening limited to what the reader needs to act on or check the point. That cut the words, but the opening and stakes fell, and a case 9 reply repeated a sentence.

**B goes to the gate.** All three passed the screen. B is the only one that previews no failure on a structural bar: identifiers, repetition and the opening. Its risk is median words. B's 357 is a median of 9 replies against a 337.7 bar, and A, which differs from B by one line, came in at 291.

Every candidate's $0 checks are retained with its screen in `~/factory/retained/quickstop-189/candidate-*/checks.md`:
- the token count (A 553, B 569, C 582 of 1,000)
- the required-content checklist
- the must-not grep
- the fixture-wording grep over 265 names, people and identifiers (empty)

Spend on screens is $2.6890. The cumulative total after them is $19.8849.

## 1.0 gate (#189)

**1.0 passes every gate bar.** The opening cold-read is 70 of 135, against a bar of 57 (1.5 × Concise's 38) and 0.3.1's 44. Opening stakes went from 1 to 12 of 45, and the #172 regression suite passes.

**Candidate.** Plugin tree `44b0451b0801b28d4b1a2e432bf571a05d8e86d7` at head `0087258203a7f71525aada886e8ee16465b47a48` (tree `526308bf…`, clean), version 1.0.0, bytes digest `29a82bc2…3b1e`. It was screened on de92b47f; gated tree differs only by the retry->cache example word and one writing-audit sentence.
- Screened tree: `de92b47f9eda9a811e20d61dc02bba101aeb83c5`.
- Gated tree: `44b0451b0801b28d4b1a2e432bf571a05d8e86d7`.
- The requester accepted B's screen for the gated tree, so it wasn't re-screened.

**Settings.** The frozen suite (`c8a8bf86`, runner `f03bee3a`) with the gate calibration (`calibration-gate`, 36 of 36) and the re-baseline's settings:
- Sonnet 5.5 for the task and the judges, Claude Code 2.1.317
- 5 runs × 9 cases in the 1.0 arm, with `--max-cost-usd 5.5`

**Result.** All 45 runs are valid, and the preflight passed with `(current)` at $0. Every init record shows `writing-for-humans:writing-for-humans`, `claude-sonnet-5-5` and the plugin at 1.0.0 from the retained copy.
- The guard has no problems, and the config sidecar was unchanged before and after.
- `summarize` reports a single problem, "subset run", because the gate runs one arm by design. The other arms are the re-baseline above.

Result dir: `~/factory/retained/quickstop-189/candidate-B2-44b0451b/gate/`. The $0 checks for this tree are in `checks.md` next to it:
- 569 tokens
- the 12-item checklist
- an empty must-not grep
- an empty fixture grep over 265 names, people and identifiers
- "cache" in 0 suite files

### Gate table

| Bar | default | concise | 0.3.1 | 1.0 (`44b0451b`) | Bar value | 1.0 |
|---|---|---|---|---|---|---|
| Opening cold-read ≥ 1.5 × Concise (/135) | 28 | 38 | 44 | 70 | ≥ 57 | **pass** |
| Opening stakes above 0 (/45) | 0 | 0 | 1 | 12 | ≥ 1 | **pass** |
| Whole cold-read no lower than 0.3.1 (/135) | 126 | 123 | 123 | 125 | ≥ 123 | **pass** |
| Identifier-led sentences no more than 0.3.1 | 55 | 46 | 43 | 7 | ≤ 43 | **pass** |
| Repetition on cases 8 and 9 no worse than 0.3.1 | 1 | 1 | 0 | 0 | ≤ 0 | **pass** |
| Pedantry on cases 8 and 9 no worse than 0.3.1 (/10) | 10 | 9 | 9 | 10 | ≥ 9 | **pass** |
| Median words ≤ Concise × 1.1 | 383 | 307 | 323 | 309 | ≤ 337.7 | **pass** |
| Mean task cost per run ≤ 0.3.1 (USD) | 0.0517 | 0.0488 | 0.0752 | 0.0621 | ≤ 0.0752 | **pass** |
| #172 regression suite | — | — | — | Suite: PASS | passes | **pass** |
| Style active in every 1.0 run | — | — | — | preflight `(current)` $0; 45/45 init valid | every run | **pass** |

The #172 suite ran on the same tree with `--max-cost-usd 0.5` and cost $0.2007. Host checks passed, both cases passed (`audit-not-automatic`, `audit-typed`), and the plugin loaded at 1.0.0 (`candidate-B2-44b0451b/regression-172/`).

### 1.0 details

| | 1.0 |
|---|---|
| Opening: claim / ask / stakes (/45 each) | 26 / 32 / 12 |
| Whole: claim / ask / stakes (/45 each) | 45 / 42 / 38 |
| Pedantry passes (/45) | 45 |
| Repeated content (runs with any) | 1 (1), in case 4 run 3 |
| Case 4 question in first 3 sentences (/5) | 1 |
| Cases 8 and 9 median words | 1,228.5 |
| Task cost, all 45 runs / judge cost (USD) | 2.7967 / 1.8897 |
| Mean task time per run (s) | 19.7 |
| Skill calls (all tool calls) | 20 (241) |

| Case | Opening hits, runs 1–5 | Whole hits | Pedantry | Median words |
|---|---|---|---|---|
| 1-worker-report | 3,1,2,1,2 | 3,3,3,3,3 | 5/5 | 396 |
| 2-design-note | 2,2,1,1,0 | 3,3,2,3,3 | 5/5 | 324 |
| 3-pr-description | 2,3,3,2,2 | 3,3,3,3,3 | 5/5 | 328 |
| 4-decision-question | 2,2,3,2,2 | 3,3,3,3,3 | 5/5 | 297 |
| 5-status-update | 0,0,1,2,1 | 3,3,3,3,3 | 5/5 | 251 |
| 6-factual-answer | 2,3,2,2,2 | 2,2,3,2,3 | 5/5 | 103 |
| 7-subagent-handoff | 2,2,2,2,3 | 2,2,1,2,2 | 5/5 | 160 |
| 8-incident-report | 3,1,0,1,0 | 3,3,3,3,3 | 5/5 | 1241 |
| 9-design-doc | 0,1,0,0,0 | 3,3,3,3,3 | 5/5 | 1216 |

The long design doc (case 9) still rarely opens with its point. The gain over 0.3.1 comes mostly from the short and medium cases, and from stakes.

### Spend for #189

| Part | USD |
|---|---|
| Part A (development, smoke, calibration, re-baseline) | 17.1948 |
| `disallowed-tools` probe (2 Haiku calls) | 0.0011 |
| 3 candidate screens | 2.6890 |
| Gate (45 runs) | 4.6864 |
| #172 regression suite | 0.2007 |
| **Cumulative** | **24.7768** of the $30 cap |
