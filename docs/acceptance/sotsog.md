# sotsog acceptance

sotsog 0.1.0 ships when `bin/ci` passes with sotsog checked like any other skill and a reviewer has read one sanity run of the final skill and found it sound. There's no scored bar. The comparative eval that was planned as the gate was screened and then dropped by [contract amendment 2](https://github.com/acoz-labs/quickstop/issues/216#issuecomment-6861575600). It's kept on the tag `archive/sotsog-eval-2026-11-13`.

## Release gate

1. **Checks.** `bin/ci` exits 0 with no `SKIPPED:` line. sotsog has no exemption in `skills-check.json`, so it passes the portability lint, skills-ref and `claude plugin validate --strict`.
2. **Sanity run.** One run of the final skill on one case from the archived suite's fixtures, with no judges. A reviewer reads the decision document and confirms all of these:
   - the phases ran;
   - the template's sections are present;
   - phase 2's check of our own side appears ("does it work, or does it only exist?", with the evidence behind each "already have");
   - nothing is broken.

## Why the comparative eval was dropped

sotsog is a workflow. Its results vary by agent tool and model, so one model's numbers against a plain prompt don't certify it, and real use is the better judge. The screens also showed that the comparison couldn't separate the two arms. The no-plugin baseline got 5 of 5 outcomes and 14 of 15 cold-read items. That left bar 3, cold read strictly above the baseline, out of reach for reasons unrelated to the skill.

## Screen results

Model `claude-sonnet-5-5` at high effort, through Claude Code 2.1.322. One run per case and arm. Screens never counted toward the gate.

| Bar | sotsog, latest run per case | Baseline |
|---|---|---|
| 1 Structure | 4/5 (case 2 gave one shared read date for its sources) | 0/5 (the template gates sotsog only) |
| 2 Outcome in the expected set | 5/5 | 5/5 |
| 3 Cold read | 13/15 (87%) | 14/15 (93%) |
| 3 Go-case briefs | 2/2 | 0/2 |
| 4 Open questions on no and not-now runs | 0, 1, 0 | 0, 2, 2 |
| 5 Case 4 names both gaps | yes | yes |
| 6 Case 5 flips to a go | yes | yes |
| 7 Depth | 5/5 | not graded |

The latest runs for cases 1 to 3 come from plugin tree `5bad75b9`, and those for cases 4 and 5 from `4d492aa1`.

The screen reports are on PR #217:
- [the first screen](https://github.com/acoz-labs/quickstop/pull/217#issuecomment-6834733114);
- [the baseline grade and the re-screen of cases 1 and 3](https://github.com/acoz-labs/quickstop/pull/217#issuecomment-6861203892);
- [the re-screen of cases 1 to 3](https://github.com/acoz-labs/quickstop/pull/217#issuecomment-6861386981).

The skill changed between screens:
- adapt now needs one of the idea's own defining principles;
- every borrowed or partly-held item gets a status;
- the "what happens next" sentence must agree with the document.

## Spend

Model spend before the sanity run was $11.21 of the $25 cap, at list price:
- judge calibration, 7 rounds: $6.68;
- screens and re-screens: $4.15;
- the baseline judge grade: $0.38.

Every paid `claude` call carried `--max-budget-usd` and `DISABLE_AUTOUPDATER=1`.

## Sanity run

Run on 2026-11-13: plugin tree `2c4b9b20`, fixture case `1-already-have` from the archive tag, `claude-sonnet-5-5` at high effort, no judges, $0.2292. The outcome was no, and the structure checks passed. The decision document and the notes for the reviewer's read-through are in [the PR comment](https://github.com/acoz-labs/quickstop/pull/217#issuecomment-6861701625). Model spend after it was $11.44. The reviewer's verdict is recorded in the review.
