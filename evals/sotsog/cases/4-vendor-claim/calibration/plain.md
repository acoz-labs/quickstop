# Prescient Select and AI test selection for Lanternhall

Lanternhall's CI runs all 310 tests plus lint in about four minutes. Prescient CI's post says AI test selection cuts CI time by up to 90%.

## Conclusion

Not now. There is almost nothing to save on a four-minute run, and the 90% figure comes from the company selling the tool. Nothing changes in CI; look again if a CI run grows past about 30 minutes.

## Notes on the evidence

- The author, Victor Ashdown, is the founder and CEO of Prescient CI, which sells Prescient Select; the post is an advert with a free-trial offer, so the source gains if we adopt.
- The "up to 90%" saving isn't measured against anything: no baseline, no before-and-after, only a customer's quote.
- regression-test-selection-study.md, an independent replication, found suites under 10 minutes save under 2 minutes a run, and learned selectors miss 1% to 4% of failures.
- the-hidden-cost-of-skipping-tests.md argues that a skipped failure is found hours later and costs more than the time saved, so short suites should run everything.
- parallel-test-sharding.md offers sharding as the alternative for a slow suite: it splits tests across machines without skipping any.

Sources read 2026-11-12: link.md, test-selection-at-brightwater.md, regression-test-selection-study.md, the-hidden-cost-of-skipping-tests.md, parallel-test-sharding.md.
