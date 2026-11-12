# AI test selection: not now for Lanternhall

We won't adopt AI test selection or buy Prescient Select now. Nothing changes in CI; we'll look again only if a full CI run grows past about 30 minutes. Our CI takes four minutes, so there's little to save, and the 90% claim comes from the vendor selling the tool, with nothing it was measured against.

Date 2026-11-12. Decided by the maintainers. Sources read: Prescient CI's post and five library pages.

## The idea in brief

Instead of running every test on every push, a model predicts which tests a change could break and runs only those, with a full run every night to catch misses. The post's version is a paid product, Prescient Select.

## What the evidence shows

Sound with caveats for very large suites; weak for short ones like ours.

- **Who gains:** the author, Victor Ashdown, is founder and CEO of Prescient CI, which sells Prescient Select; the post ends with a free-trial offer, and the company just raised money to grow sales.
- **Measured against:** nothing. "Up to 90%" has no baseline or before-and-after; it rests on an unnamed customer CTO's quote.
- **What's missing:** suite sizes, how many failures selection missed, cost of the selection step.
- **Whose conditions:** unstated; independent results say large savings only come from suites of an hour or more.
- **Independent support:** Brightwater Games measured 41% (not 90%) on a 2-hour-10-minute suite, with 7 of 212 failures missed until the nightly run, and wouldn't bother below 30 minutes. A replication study across 25 projects found suites under 10 minutes saved under 2 minutes a run, with learned selectors missing 1% to 4% of failures. Ken Oyelaran's critique: a skipped failure surfaces hours later and costs more than the time saved.

## How it compares with what we do

| Principle | How they do it | How we do it | Fit |
|---|---|---|---|
| Map tests to code | learned from past runs | not needed; all 310 tests run in under two minutes | doesn't apply |
| Run only predicted tests | per push | full suite every push in `bin/check` | conflicts |
| Full run later | nightly | full run on every push | already have |
| Likely failures first | ordered runs | not done | partly |

Adopting it would weaken our protection against shipping booking bugs during opening hours, which matters most to us.

## Why this decision

Gain: at most a minute or two per run. Cost: a paid tool we have no budget for, and missed failures found a day late. The strongest case for it: test suites grow, and the principle of running likely failures first is free. That's why this is "not now" rather than "no". Sharding (the CI Handbook's alternative) would speed a slow suite without skipping tests, if we ever need it.

## Revisit when

- A full CI run takes more than about 30 minutes.

## What we're not taking, and why

Test selection and the product: little to gain on a four-minute run and a real risk of missed failures. Nothing to borrow now.

## Sources

- Victor Ashdown, "Your CI is running 90% too many tests" (link.md), read 2026-11-12. Founder and CEO of the vendor; claims only, no measurements.
- Nadia Kowalczyk, "What test selection actually saved us at Brightwater" (test-selection-at-brightwater.md), read 2026-11-12. Measured against the full suite.
- Empirical Software Engineering Lab, "Regression test selection in practice: a replication study" (regression-test-selection-study.md), read 2026-11-12. Independent.
- Ken Oyelaran, "The hidden cost of skipping tests" (the-hidden-cost-of-skipping-tests.md), read 2026-11-12. Critique.
- CI Handbook contributors, "Speed up CI by sharding, not skipping" (parallel-test-sharding.md), read 2026-11-12. Competing approach.
