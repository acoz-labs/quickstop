# AI test selection: no for Lanternhall

No: we won't adopt AI test selection. Nothing changes in CI. With a four-minute CI run there's almost nothing to save, and the claim comes from the vendor.

Date 2026-11-12. Decided by the maintainers. Sources: the Prescient post and the library.

## The idea in brief

Run only the tests a model predicts a change can break, with a nightly full run.

## What the evidence shows

Weak for short suites.

- **Who gains:** the author is Prescient CI's CEO, selling the product.
- **Measured against:** nothing; "up to 90%" has no baseline.
- **What's missing:** how many failures were missed.
- **Whose conditions:** large suites, unlike our four minutes.
- **Independent support:** regression-test-selection-study.md found suites under 10 minutes save under 2 minutes. The critique in the-hidden-cost-of-skipping-tests.md says skipped failures surface late and cost more than they save.

## How it compares with what we do

| Principle | How they do it | How we do it | Fit |
|---|---|---|---|
| Run predicted tests only | per push | full suite every push | conflicts |
| Nightly full run | yes | full run every push | already have |

## Why this decision

Little to gain, a paid tool, and the risk of missing a bug. Sharding (parallel-test-sharding.md) is the alternative if CI gets slow.

## Revisit when

- CI takes more than 30 minutes.

## What we're not taking, and why

All of it, for now.

## Sources

- Prescient post (link.md), read 2026-11-12.
- regression-test-selection-study.md, read 2026-11-12.
- the-hidden-cost-of-skipping-tests.md, read 2026-11-12.
- parallel-test-sharding.md, read 2026-11-12.
