# sotsog acceptance

sotsog 0.1.0 ships only if the frozen eval gate in [evals/sotsog](../../evals/sotsog/README.md) passes all seven bars that issue #216 fixes. If any bar fails, there's no release, and the bar table is posted on the issue. This document records how the gate is run and, once it has run, what it found.

## Procedure

1. **Freeze.** Fixtures, answer keys, calibration samples, graders, judge prompts and the runner are frozen before any sotsog run. The proof is an empty `git diff <freeze> <candidate> -- evals/sotsog bin/sotsog-eval`, plus the suite tree and runner blob recorded in every result's `CANDIDATE.txt`.
2. **No overlap.** `tests/test_sotsog_eval.py` greps every file of `plugins/sotsog/` for each case's fixture-specific terms, and fails on any hit.
3. **Calibration.** `bin/sotsog-eval calibrate --judges` must match every expected verdict, on a clean tree with the frozen suite tree and runner blob, before any arm runs.
4. **Screen.** sotsog runs once per case, plus one baseline run on case 1, so both arms' costs are measured. Screens never count.
5. **Go or no-go on spend.** This rule is in `docs/changes/216-sotsog/plan.md`. The gate starts only if its measured projection fits under the $20 cap with 25% margin. A projection past $14 needs a go from the requester first.
6. **Gate.** Both arms run 3 times per case, on a tree the reviewer has cleared, with the same model, effort, tools and per-run cap. `summarize` computes the bars.

Every paid `claude` call carries `--max-budget-usd`. The issue asks for `--max-cost-usd`, but Claude Code 2.1.322 has no such flag. In this repository, `--max-cost-usd` is the runner's ceiling for one whole invocation. Every call sets `DISABLE_AUTOUPDATER=1`.

## Results

Not run yet. This section will record the following:

- Per arm: each bar's result, and the cost and time per run.
- The model and Claude Code version.
- The frozen-suite proof.
- The calibration.
- The spend ledger total.
