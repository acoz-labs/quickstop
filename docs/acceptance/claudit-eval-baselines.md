# Claudit eval baselines

Baselines for the [Claudit eval suite](../../evals/claudit/README.md), recorded
for issue #155 on 2026-10-29. Claudit 4.0 (#156) is gated against these numbers.

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

An earlier candidate (plugin tree `421c6c4`, before review) scored 42/42 live and
14/14 offline under the same conditions.

The pooled summaries are `claudit-4.0-live.json`, `claudit-4.0-offline.json` and
`plain-web-fetch.json` in [claudit-eval-baselines/](claudit-eval-baselines/).
