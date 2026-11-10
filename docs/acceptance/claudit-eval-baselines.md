# Claudit eval baselines

Baselines for the [Claudit eval suite](../../evals/claudit/README.md), recorded
for issue #155 on 2026-10-29. Claudit 4.0 (#156) is gated against these numbers.

## Claudit 5.0.0 (#207)

Claudit 5.0.0 reports a findings list, not grades, and the suite's graders were
rebuilt as script graders from each fixture's scan, so the tables below (4.x,
graded reports, partly model-judged) don't compare with it. Its gate has fixed bars
instead of a baseline: every expected finding hit in every run, no false finding on
any case, medians at or under $0.15 and 60 s per run, and the real repositories
judged right by the reviewer. Results are posted on issue #207, not committed.

## Conditions

- Claude Code 2.1.312, `claude plugin eval` through `bin/claudit-eval run`.
- Model `claude-sonnet-5-5` for every arm (Claudit's own subagents pin Sonnet);
  judge `claude-haiku-5-5`.
- Three runs per case per arm: one pass with `--runs 1`, then one with `--runs 2`,
  pooled with `bin/claudit-eval summarize`.
- Claudit 3.2.3 (`plugins/claudit` at this commit, unchanged) invoked as
  `/claudit:claudit --read-only`, with a research cache seeded once by
  `bin/claudit-eval seed` (all three domains fresh; $1.33, 223 s). That seed ran
  with Bash unrestricted. The runner's seed now allows Bash only for the helper
  commands a refresh uses; it was verified afterwards (all domains fresh; $1.25,
  275 s). The sandbox
  blocks Claudit's own fetches, so every run used that seeded cache.
- Costs are at list prices as reported by Claude Code. Agent cost excludes the
  judge; the judge column is separate.
- F4 false defects per run: the number of failed targeted `no-invented-*` graders,
  or 1 when only the catch-all `no-invented-defects` failed. That's a lower bound
  on distinct invented defects. Hit-rate denominators are planted findings × runs.
- The path-free pooled summaries are in [claudit-eval-baselines/](claudit-eval-baselines/).
  Regenerate them with `bin/claudit-eval summarize <pass-1 result.json> <pass-2 result.json>`.

## Results (3 runs per case)

| Arm | Planted findings hit | F4 false defects | Structure graders | Agent $ (per run) | Judge $ | Wall s (per run) |
|---|---|---|---|---|---|---|
| Plain prompt, no plugin | 25/42 (60%) | 2 (in 2 runs) | 0/60 | 1.19 (0.079) | 0.040 | 704 (46.9) |
| `/doctor`, no plugin | 10/42 (24%) | 0 | 0/60 | 2.42 (0.162) | 0.040 | 767 (51.1) |
| Claudit 3.2.3 | 17/42 (40%) | 0 | 0/60 | 7.19 (0.480) | 0.057 | 1786 (119.1) |

`/doctor` runs headless: in print mode it is a model-driven installation and
configuration check, not the interactive diagnostic screen. No arm states an
intent with three graded dimensions and confidences; those structure graders are
Claudit 4.0 targets.

### Hit rate per fixture

| Case | Plain | `/doctor` | Claudit 3.2.3 |
|---|---|---|---|
| `f1-agent-run` | 7/9 | 0/9 | 0/9 |
| `f2-plugin-repo` | 4/9 | 3/9 | 3/9 |
| `f3-misconfigured` | 9/18 | 7/18 | 13/18 |
| `f4-well-configured` (false defects) | 2 | 0 | 0 |
| `f5-bare` | 5/6 | 0/6 | 1/6 |

### Per grader (passes out of 3)

| Case | Grader | Plain | `/doctor` | Claudit 3.2.3 |
|---|---|---|---|---|
| f1 | `finding-ci-allowlist` | 3 | 0 | 0 |
| f1 | `finding-procedure-skill` | 3 | 0 | 0 |
| f1 | `finding-stop-hook` | 1 | 0 | 0 |
| f2 | `finding-plugin-eval` | 0 | 0 | 0 |
| f2 | `finding-plugin-validate` | 1 | 0 | 0 |
| f2 | `finding-stale-reference` | 3 | 3 | 3 |
| f3 | `finding-array-matcher` | 2 | 3 | 3 |
| f3 | `finding-claudeignore` | 3 | 0 | 2 |
| f3 | `finding-flat-skill` | 2 | 2 | 3 |
| f3 | `finding-oversized-claude-md` | 2 | 2 | 2 |
| f3 | `finding-project-bypass` | 0 | 0 | 3 |
| f3 | `finding-write-rule` | 0 | 0 | 0 |
| f4 | `no-invented-defects` | 1 | 3 | 3 |
| f4 | `no-invented-secret-deny` | 1 | 3 | 3 |
| f4 | other five `no-invented-*` | 3 each | 3 each | 3 each |
| f5 | `finding-no-instructions` | 3 | 0 | 1 |
| f5 | `finding-test-allowlist` | 2 | 0 | 0 |

## Reading

Claudit 3.2.3 finds the most planted defects on F3 and invents none on F4
(as does `/doctor`), but it finds almost none of the Coverage holes (F1, F5, F2's missing plugin checks): it
audits what is configured, not what the project needs. The plain prompt finds
more holes but invents defects on the well-configured fixture. Nothing finds the
`Write(...)` rule or a missing `claude plugin eval`. #156 sets Claudit 4.0's gate
from these numbers, measured under the same conditions.

Hit rates are judged by a model from the final report and vary between runs.
Compare only runs with the same model, judge and run count.

## Spend

Total for #155 at list prices: about $17.0. The pooled arms above cost $10.94
(agent plus judge: plain $1.23, `/doctor` $2.46, Claudit $7.25). The successful
seed cost $1.33, and two scoped-permission seed checks $2.24. Two failed seed attempts (permission denials) cost $1.25. F1
pipeline debugging cost $0.86, sandbox probes $0.03, and one stopped `/doctor` run
whose results aren't used cost an estimated $0.3.

## Claudit 4.0 gate (#156)

Recorded on 2026-10-29 against the same suite, Claude Code 2.1.312, model
`claude-sonnet-5-5` and judge `claude-haiku-5-5`. Every arm ran as one
`bin/claudit-eval run` pass; no cache was seeded (4.0 has none). The Claudit arms
below ran on the released plugin tree `0939a97d76974df10b5016b2e1f9dfe61d03330d`.
Source: the [final gate result](https://github.com/acoz-labs/quickstop/issues/156#issuecomment-6509034055)
posted on #156, and the [decision](https://github.com/acoz-labs/quickstop/issues/156#issuecomment-6509051261)
that accepted it.

| Arm | Tools granted | Runs per case | Planted findings hit | F4 false defects | Structure graders | Agent $ (per run) | Judge $ | Wall s (per run) |
|---|---|---|---|---|---|---|---|---|
| Claudit 4.0.0, live docs | `Bash`, `WebFetch(domain:code.claude.com)` (`--web-fetch`) | 3 | 41/42 (98%) | 0 | 60/60 | 2.13 (0.142) | 0.041 | 848 (56.5) |
| Claudit 4.0.0, docs unreachable | `Bash` only | 1 | 14/14 (100%) | 0 | 20/20 | 0.46 (0.093) | 0.013 | 168 (33.6) |
| Plain prompt, no plugin | `Bash`, `WebFetch(domain:code.claude.com)` (`--web-fetch`) | 3 | 25/42 (60%) | 3 (in 3 runs) | 0/60 | 1.18 (0.079) | 0.041 | 693 (46.2) |

Claudit was invoked as `/claudit:claudit --read-only`. Every case also lists the
granted tools in its `allowed_tools`. Without `--web-fetch` the live-docs fetch
fails and Claudit grades from its shipped catalog, which is the docs-unreachable
path. Granting the plain prompt the same docs access didn't raise its hit count
(25/42 both times). The bar 4.0 had to beat was the highest baseline, 25/42.

Per fixture, live: F1 9/9, F2 9/9, F3 17/18, F5 6/6. Offline: F1 3/3, F2 3/3,
F3 6/6, F5 2/2. Plain with docs: F1 6/9, F2 4/9, F3 11/18, F5 4/6.

The live arm's one miss is `finding-flat-skill` in F3 run 3 (judge votes PASS,
FAIL, FAIL), although that report names `.claude/skills/release-notes.md` as a flat
file that won't load and gives the `git mv` to `.claude/skills/release-notes/SKILL.md`.
The gate was accepted on that verified grader false negative (#156). A script
grader for F3's structural defects would remove this judge noise.

The pooled summaries are `claudit-4.0-live.json`, `claudit-4.0-offline.json` and
`plain-web-fetch.json` in [claudit-eval-baselines/](claudit-eval-baselines/).

## Suite changes for Claudit 4.0.1 (#168)

F3's six graders (flat skill, `Write(...)`, `.claudeignore`, project
`defaultMode`, array matcher, oversized CLAUDE.md) and F2's `finding-plugin-eval`
are now regex graders instead of the model judge,
every case adds `structure-plan-length`, and `f6-agents-md` adds an `AGENTS.md`-only
fixture with no planted findings. F1 to F5 still plant 42 findings over three runs;
structure graders are five per case. The 4.0.1 gate results are posted on #168,
not recorded here.

## doctor-combined arm and fixtures f14 to f19 (#192)

Issue #192 adds an arm that runs Claude Code's two built-in reviews, `/doctor` and `/doctor prompt-audit .`, and
grades their replies as one report, plus six fixtures. The issue calls them F10 to F15; the suite numbers them f14
to f19 because F10 to F13 were taken:

| Issue | Case |
|---|---|
| F10 enforcement | `f14-enforcement` |
| F11 context economy | `f15-context-economy` |
| F12 stale facts | `f16-stale-facts` |
| F13 scope | `f17-scope` |
| F14 check commands | `f18-check-commands` |
| F15 declarative list | `f19-declarative-list` |

### Conditions

- Model `claude-sonnet-5-5` and judge `claude-haiku-5-5` on every arm, as above.
- Plain prompt: `bin/claudit-eval run --arm plain --web-fetch`, as in #156.
- Claudit 4.2.0: plugin tree `3972b36948dfecb2a9e3e8610290a318b6422a33`, extracted from tag `claudit-v4.2.0`,
  `--web-fetch`, invoked as `/claudit:claudit --read-only`.
- `doctor-combined`: `bin/claudit-eval run --arm doctor-combined`, headless and read-only (see the
  [suite README](../../evals/claudit/README.md#arms)). It runs outside `claude plugin eval`, so its llm graders go to
  the same judge prompt through `claude -p`, not through the eval host. Its throwaway folders are never trusted, so
  Claude Code ignores the fixtures' allow rules, and `/doctor` runs with Bash denied: it can't run `claude --version`
  or read `~/.claude*`, and its reply says so. The results give each arm's permission-denial counts. Counted batches
  run one case at a time, so the cost ceiling can overshoot by at most one run (up to 2 × `--max-budget-usd`
  plus its judge votes).
- `f17-scope` puts the parent's `CLAUDE.md` and `AGENTS.md` in the workspace's parent folder. Under `claude plugin
  eval` (plain and Claudit) that folder is the run's own home, which the eval host also gives a stub `.git`. Under
  `doctor-combined` it is a plain folder. `/context` shows Claude Code loads the parent `CLAUDE.md` in both layouts.
  Even so, the arms see different surroundings, so compare their f17 rows with care.
- `doctor-combined` measured nothing on `f19-declarative-list`. The fixture's Stop hook runs `go test ./...`, and
  in these runs it failed on the run host's toolchain (`mise ERROR No version is set for shim: go`), not on the
  fixture's code. The plain and Claudit f19 reports are full audits. All six calls (3 runs × `/doctor` and `/doctor prompt-audit .`) ended by answering that failure, so no
  graded report holds an audit body. Those cells are marked not measured. Their cost and time are real and stay. The
  runs were not repeated: the same hook would fail again, and $2.53 of the cap was left.
- Hit rates are the mean over runs per case, with the number of runs (n) stated for every arm and case. Rows reused
  from earlier issues name their source, Claude Code version and run count.

### Results

Counted on 2026-11-03. The candidate is tree `8d11231edf1d7236644fdd668ab84f64b7e67681` (head `b3004cd`, a clean
checkout; every run's `CANDIDATE.txt` records the tree, the head and 0 changed paths). The Claudit arm ran plugin tree
`3972b36948dfecb2a9e3e8610290a318b6422a33`, extracted from tag `claudit-v4.2.0`. New runs used Claude Code 2.1.317,
model `claude-sonnet-5-5` and judge `claude-haiku-5-5`. No run errored and every grader scored.

Runs per arm and case (n):

| Arm | f1 to f13 | f14 to f19 | Real repos |
|---|---|---|---|
| Plain prompt (`--web-fetch`) | n=1, new | n=3, new | not run |
| Claudit 4.2.0 (`--web-fetch`) | n=3, reused from the #184 gate (see below) | n=3, new | n=1 each |
| `doctor-combined` | n=1, new | n=3, new | n=1 each |

**Reused rows.** Claudit 4.2.0 on f1 to f13, marked [#184], comes from the #184 release gate: tree
`f632f285f5a60473367b00503befcafa496a0487`, the same plugin tree, Claude Code 2.1.316, `--web-fetch`, n=3 (39
reports). It was regraded at $0 with this candidate's graders. The f1 to f13 grader files are byte-identical between
the two trees, so every grader applies. The 544 regex verdicts were re-run and none of the 39 live reports (nor the 13
offline ones) changed. The llm verdicts are the gate's recorded judge votes. `/doctor` alone from #155 (Claude Code
2.1.312, n=3) is listed only for f1 to f5. Its reports aren't retained, so no grader can be re-run on them, and #155
graded F3 with the judge, which has since moved to regex graders.

Hit rate is the mean over runs of each run's share of the case's `finding-*` graders passed. f4, f6 to f13 and f19
plant no findings: they test false defects and, for Claudit, its report structure. False defects per run count the
failed targeted `no-invented-*` graders, or 1 when only the catch-all `no-invented-defects` failed.

#### Per fixture: hit rate and false defects

| Case | Plain: hit rate | Plain: false defects | Claudit 4.2.0: hit rate | Claudit 4.2.0: false defects | doctor-combined: hit rate | doctor-combined: false defects |
|---|---|---|---|---|---|---|
| `f1-agent-run` | 67% of 3 (n=1) | 0 in 0 of 1 runs (n=1) | 100% of 3 (n=3) [#184] | 0 in 0 of 3 runs (n=3) | 0% of 3 (n=1) | 0 in 0 of 1 runs (n=1) |
| `f2-plugin-repo` | 67% of 3 (n=1) | 0 in 0 of 1 runs (n=1) | 100% of 3 (n=3) [#184] | 0 in 0 of 3 runs (n=3) | 33% of 3 (n=1) | 0 in 0 of 1 runs (n=1) |
| `f3-misconfigured` | 50% of 6 (n=1) | 0 in 0 of 1 runs (n=1) | 100% of 6 (n=3) [#184] | 0 in 0 of 3 runs (n=3) | 33% of 6 (n=1) | 0 in 0 of 1 runs (n=1) |
| `f4-well-configured` | — (no planted findings; n=1) | 1 in 1 of 1 runs (n=1) | — (no planted findings; n=3) [#184] | 0 in 0 of 3 runs (n=3) | — (no planted findings; n=1) | 0 in 0 of 1 runs (n=1) |
| `f5-bare` | 100% of 2 (n=1) | 0 in 0 of 1 runs (n=1) | 100% of 2 (n=3) [#184] | 0 in 0 of 3 runs (n=3) | 0% of 2 (n=1) | 0 in 0 of 1 runs (n=1) |
| `f6-agents-md` | — (no planted findings; n=1) | 2 in 1 of 1 runs (n=1) | — (no planted findings; n=3) [#184] | 0 in 0 of 3 runs (n=3) | — (no planted findings; n=1) | 0 in 0 of 1 runs (n=1) |
| `f7-fixture-noise` | — (no planted findings; n=1) | 0 in 0 of 1 runs (n=1) | — (no planted findings; n=3) [#184] | 0 in 0 of 3 runs (n=3) | — (no planted findings; n=1) | 0 in 0 of 1 runs (n=1) |
| `f8-documented-decline` | — (no planted findings; n=1) | 0 in 0 of 1 runs (n=1) | — (no planted findings; n=3) [#184] | 0 in 0 of 3 runs (n=3) | — (no planted findings; n=1) | 0 in 0 of 1 runs (n=1) |
| `f9-clean` | — (no planted findings; n=1) | 0 in 0 of 1 runs (n=1) | — (no planted findings; n=3) [#184] | 0 in 0 of 3 runs (n=3) | — (no planted findings; n=1) | 0 in 0 of 1 runs (n=1) |
| `f10-stale-decline` | — (no planted findings; n=1) | 0 in 0 of 1 runs (n=1) | — (no planted findings; n=3) [#184] | 0 in 0 of 3 runs (n=3) | — (no planted findings; n=1) | 0 in 0 of 1 runs (n=1) |
| `f11-valid-decline` | — (no planted findings; n=1) | 0 in 0 of 1 runs (n=1; recorded 1, corrected) | — (no planted findings; n=3) [#184] | 0 in 0 of 3 runs (n=3) | — (no planted findings; n=1) | 0 in 0 of 1 runs (n=1) |
| `f12-unsafe-decline` | — (no planted findings; n=1) | 0 in 0 of 1 runs (n=1; recorded 1, corrected) | — (no planted findings; n=3) [#184] | 0 in 0 of 3 runs (n=3) | — (no planted findings; n=1) | 0 in 0 of 1 runs (n=1; recorded 1, corrected) |
| `f13-no-reason-decline` | — (no planted findings; n=1) | 0 in 0 of 1 runs (n=1) | — (no planted findings; n=3) [#184] | 0 in 0 of 3 runs (n=3) | — (no planted findings; n=1) | 0 in 0 of 1 runs (n=1) |
| `f14-enforcement` | 33% of 5 (n=3) | 0 in 0 of 3 runs (n=3) | 20% of 5 (n=3) | 0 in 0 of 3 runs (n=3) | 0% of 5 (n=3) | 0 in 0 of 3 runs (n=3) |
| `f15-context-economy` | 0% of 3 (n=3) | 0 in 0 of 3 runs (n=3) | 0% of 3 (n=3) | 0 in 0 of 3 runs (n=3) | 33% of 3 (n=3) | 0 in 0 of 3 runs (n=3) |
| `f16-stale-facts` | 33% of 3 (n=3) | 0 in 0 of 3 runs (n=3) | 0% of 3 (n=3) | 0 in 0 of 3 runs (n=3) | 56% of 3 (n=3) | 0 in 0 of 3 runs (n=3) |
| `f17-scope` | 22% of 3 (n=3) | 0 in 0 of 3 runs (n=3) | 0% of 3 (n=3) | 0 in 0 of 3 runs (n=3) | 56% of 3 (n=3) | 0 in 0 of 3 runs (n=3; recorded 1 in 1, corrected) |
| `f18-check-commands` | 0% of 1 (n=3) | 0 in 0 of 3 runs (n=3) | 100% of 1 (n=3) | 0 in 0 of 3 runs (n=3) | 0% of 1 (n=3) | 0 in 0 of 3 runs (n=3) |
| `f19-declarative-list` | — (no planted findings; n=3) | 0 in 0 of 3 runs (n=3) | — (no planted findings; n=3) | 0 in 0 of 3 runs (n=3) | not measured: the Stop hook failed on the host toolchain (n=0 of 3 runs) | not measured: the Stop hook failed on the host toolchain (n=0 of 3 runs) |

#### Per fixture: cost and time

Cost is agent plus judge, at list prices as reported by Claude Code. `doctor-combined` runs `/doctor` with Bash
denied (see Conditions); the last column counts both calls' permission denials.

| Case | Plain: $ per run | Plain: s per run | Claudit 4.2.0: $ per run | Claudit 4.2.0: s per run | doctor-combined: $ per run | doctor-combined: s per run | doctor-combined: Bash denials per run |
|---|---|---|---|---|---|---|---|
| `f1-agent-run` | $0.096 (n=1) | 41 s (n=1) | $0.141 (n=3) [#184] | 53 s (n=3) [#184] | $0.479 (n=1) | 76 s (n=1) | 7.0 (n=1) |
| `f2-plugin-repo` | $0.079 (n=1) | 34 s (n=1) | $0.141 (n=3) [#184] | 45 s (n=3) [#184] | $0.470 (n=1) | 63 s (n=1) | 7.0 (n=1) |
| `f3-misconfigured` | $0.078 (n=1) | 19 s (n=1) | $0.151 (n=3) [#184] | 40 s (n=3) [#184] | $0.571 (n=1) | 97 s (n=1) | 7.0 (n=1) |
| `f4-well-configured` | $0.105 (n=1) | 61 s (n=1) | $0.131 (n=3) [#184] | 62 s (n=3) [#184] | $0.511 (n=1) | 82 s (n=1) | 7.0 (n=1) |
| `f5-bare` | $0.079 (n=1) | 26 s (n=1) | $0.132 (n=3) [#184] | 44 s (n=3) [#184] | $0.429 (n=1) | 55 s (n=1) | 6.0 (n=1) |
| `f6-agents-md` | $0.076 (n=1) | 26 s (n=1) | $0.135 (n=3) [#184] | 41 s (n=3) [#184] | $0.454 (n=1) | 62 s (n=1) | 5.0 (n=1) |
| `f7-fixture-noise` | $0.072 (n=1) | 24 s (n=1) | $0.129 (n=3) [#184] | 37 s (n=3) [#184] | $0.483 (n=1) | 66 s (n=1) | 7.0 (n=1) |
| `f8-documented-decline` | $0.061 (n=1) | 17 s (n=1) | $0.127 (n=3) [#184] | 34 s (n=3) [#184] | $0.468 (n=1) | 76 s (n=1) | 7.0 (n=1) |
| `f9-clean` | $0.064 (n=1) | 16 s (n=1) | $0.122 (n=3) [#184] | 33 s (n=3) [#184] | $0.478 (n=1) | 62 s (n=1) | 9.0 (n=1) |
| `f10-stale-decline` | $0.063 (n=1) | 19 s (n=1) | $0.126 (n=3) [#184] | 35 s (n=3) [#184] | $0.430 (n=1) | 64 s (n=1) | 5.0 (n=1) |
| `f11-valid-decline` | $0.058 (n=1) | 16 s (n=1) | $0.126 (n=3) [#184] | 33 s (n=3) [#184] | $0.378 (n=1) | 55 s (n=1) | 8.0 (n=1) |
| `f12-unsafe-decline` | $0.067 (n=1) | 20 s (n=1) | $0.129 (n=3) [#184] | 35 s (n=3) [#184] | $0.377 (n=1) | 50 s (n=1) | 8.0 (n=1) |
| `f13-no-reason-decline` | $0.060 (n=1) | 15 s (n=1) | $0.124 (n=3) [#184] | 33 s (n=3) [#184] | $0.473 (n=1) | 62 s (n=1) | 6.0 (n=1) |
| `f14-enforcement` | $0.075 (n=3) | 18 s (n=3) | $0.133 (n=3) | 34 s (n=3) | $0.465 (n=3) | 48 s (n=3) | 5.3 (n=3) |
| `f15-context-economy` | $0.089 (n=3) | 24 s (n=3) | $0.142 (n=3) | 35 s (n=3) | $0.569 (n=3) | 88 s (n=3) | 7.3 (n=3) |
| `f16-stale-facts` | $0.071 (n=3) | 16 s (n=3) | $0.138 (n=3) | 36 s (n=3) | $0.486 (n=3) | 63 s (n=3) | 5.3 (n=3) |
| `f17-scope` | $0.063 (n=3) | 14 s (n=3) | $0.129 (n=3) | 34 s (n=3) | $0.459 (n=3) | 72 s (n=3) | 6.7 (n=3) |
| `f18-check-commands` | $0.064 (n=3) | 14 s (n=3) | $0.139 (n=3) | 38 s (n=3) | $0.454 (n=3) | 54 s (n=3) | 5.3 (n=3) |
| `f19-declarative-list` | $0.072 (n=3) | 19 s (n=3) | $0.127 (n=3) | 49 s (n=3) | $0.512 (n=3) | 70 s (n=3) | 6.7 (n=3) |

#### Per arm

The `structure-*` graders check Claudit's own report shape (intent, three graded dimensions, plan length, footer), so
the other arms pass only the few that any report can meet.

| Arm | Fixtures | Runs | Mean per-run hit rate | False defects | Total $ | $ per run | s per run | Structure graders |
|---|---|---|---|---|---|---|---|---|
| Plain prompt | f1-f13 | 13 | 71% (runs with findings 4) | 3 (recorded 5, corrected) | $0.96 | $0.074 | 26 | 11% (n=13) |
| Plain prompt | f14-f19 | 18 | 18% (runs with findings 15) | 0 | $1.30 | $0.072 | 17 | 12% (n=18) |
| Claudit 4.2.0 [#184, Claude Code 2.1.316, n=3, regraded at b3004cd] | f1-f13 | 39 | 100% (runs with findings 12) | 0 | $5.14 | $0.132 | 40 | 100% (n=39) |
| Claudit 4.2.0 | f14-f19 | 18 | 24% (runs with findings 15) | 0 | $2.43 | $0.135 | 38 | 98% (n=18) |
| doctor-combined | f1-f13 | 13 | 17% (runs with findings 4) | 0 (recorded 1, corrected) | $6.00 | $0.461 | 67 | 11% (n=13) |
| doctor-combined (f19 not measured) | f14-f19 | 18 | 29% (runs with findings 15) | 0 (recorded 1, corrected) | $8.83 | $0.491 | 66 | 12% (n=18) |

Corrected cells follow comment [6617090931](https://github.com/acoz-labs/quickstop/pull/194#issuecomment-6617090931) (hand-read under the #168 rule); the recorded counts are given beside them. No hit
rate changed. In the `doctor-combined` f14-f19 row, the hit rate is the mean over the 15 runs of f14 to f18 (f19 plants
no findings). False defects, structure, cost and time are over all 18 runs, including the 3 unmeasured f19 runs:
their false-defect and structure verdicts measure nothing, and their cost and time are real.

#### Reused: `/doctor` alone (#155)

| Case | Hit rate | False defects | Source |
|---|---|---|---|
| `f1-agent-run` | 0% of 3 (n=3) | 0 (n=3) | #155, Claude Code 2.1.312; can't be regraded (reports not retained) |
| `f2-plugin-repo` | 33% of 3 (n=3) | 0 (n=3) | #155, Claude Code 2.1.312; can't be regraded (reports not retained) |
| `f3-misconfigured` | 39% of 6 (n=3) | 0 (n=3) | #155, Claude Code 2.1.312; judge-graded then, can't be regraded with today's regex graders |
| `f4-well-configured` | no planted findings (n=3) | 0 (n=3) | #155, Claude Code 2.1.312; can't be regraded (reports not retained) |
| `f5-bare` | 0% of 2 (n=3) | 0 (n=3) | #155, Claude Code 2.1.312; can't be regraded (reports not retained) |

#### Real repositories

Each target ran once per arm, headless and read-only on a fresh clone, Claude Code 2.1.317. Nothing grades these
reports; they are kept as they were written, except that the `/doctor` copies drop its quote of the operator's own
`/usage` figures.

| Repository | Arm | $ | s | Report |
|---|---|---|---|---|
| `acoz-labs/quickstop` @ `2f2ae09` (`origin/main` at run time) | Claudit 4.2.0 | 0.131 | 36 | [report](claudit-eval-baselines/192-real-repos/quickstop-claudit.md) |
| `acoz-labs/quickstop` @ `2f2ae09` | `doctor-combined` | 0.606 | 85 | [report](claudit-eval-baselines/192-real-repos/quickstop-doctor-combined.md) |
| `modelcontextprotocol/python-sdk` @ `af4c6f4` | Claudit 4.2.0 | 0.237 | 52 | [report](claudit-eval-baselines/192-real-repos/python-sdk-claudit.md) |
| `modelcontextprotocol/python-sdk` @ `af4c6f4` | `doctor-combined` | 0.607 | 102 | [report](claudit-eval-baselines/192-real-repos/python-sdk-doctor-combined.md) |

On quickstop, Claudit grades A, A, A with no changes, and `doctor-combined` finds two stale history lines in
`docs/repository.md` (prompt-audit) and can't run most `/doctor` checks without Bash. On python-sdk, six of Claudit's
seven changes are "Add a skill for" documentation pages, four of them translations of the other two.

#### Reading

- On f14 to f19, no arm finds most of the new findings. The mean per-run hit rate is 29% for `doctor-combined`, 24%
  for Claudit 4.2.0 and 18% for the plain prompt. `doctor-combined` leads on context economy (f15), stale facts (f16) and scope (f17),
  Claudit alone allowlists the check (f18), and the plain prompt leads on enforcement (f14).
- On f1 to f13, the reused Claudit 4.2.0 rows hit every planted finding with no false defects. `doctor-combined`
  hits 17% at n=1, and the plain prompt 71% with three false defects (five recorded, two corrected).
- Claudit 4.2.0 proposed a skill for the principles in 3 of 3 f19 runs, each time as an "Optional" note under Also
  worth knowing that calls the list "a 7-step procedure doc". The O1 rule doesn't count notes there, so its 0 on f19
  doesn't mean the behaviour was absent.
- `doctor-combined` costs about $0.48 a run, about 3.6 times Claudit 4.2.0, and takes about 66 s a run.
- These are model runs graded by scripts and a judge. Compare only rows with the same model, judge and n.

Hand-read notes on the false defects. The reviewer's rulings are in comment [6617090931](https://github.com/acoz-labs/quickstop/pull/194#issuecomment-6617090931), and the tables above apply them:
- plain f4: "The `.env` deny rules only cover the Read and Edit tools" is the invented defect `no-invented-secret-deny` targets. Stands.
- plain f6: "Claude Code doesn't read `AGENTS.md`" is the invented defect the two `no-invented-agents-md-*` graders target. Stands.
- plain f11: "Both reasons hold up … I wouldn't revisit either." declines; `no-invented-reconsider` exempts "not
  worth", "do not" and others but not "wouldn't". Corrected to 0.
- plain and `doctor-combined` f12: "The scope is what I'd reconsider" and "you may want to revisit it" are offered for
  the `bypassPermissions` decline, which is f12's unsafe decline. Both corrected to 0.
- `doctor-combined` f17 run 3: "Its pointer to `bin/legacy-build` isn't derivable, so it stays." keeps the line;
  `no-invented-parent-findings` reads "pointer" as the fix word `point\w*`. Corrected to 0.

#### Spend

$22.47 of the $25.00 cap: $21.10 for these runs and $1.37 for the smoke on head `a9fd63c`. case-claudit approved
going past the $17.50 pause to a hard stop at $25.00 for `doctor-combined` f1 to f13 and the real-repo arm; the
regrades cost nothing.
