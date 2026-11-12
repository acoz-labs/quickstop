# Ship to main, review after: why Quarry Labs dropped pull request reviews

Source: https://quarrylabs.example.com/blog/ship-to-main
Author: Elena Marsh, head of engineering, Quarry Labs (a 12-person startup making scheduling software for gyms)
Published: 2026-09-23

Our pull requests used to wait a day on average for review. Developers batched
work into bigger branches to avoid the wait, and bigger branches waited even
longer. So in March we stopped requiring reviews before merge.

How it works now:

1. **Everyone pushes small commits straight to main.** No branches longer than
   a few hours, no pull requests for routine work.
2. **Unfinished work hides behind feature flags,** so main is always
   deployable.
3. **Review happens after merge.** Every morning, each developer reads
   yesterday's commits from one colleague and leaves comments; fixes go in as
   new commits.
4. **A strong test suite and fast rollback are the safety net,** not the
   review gate.

Our median time from first commit to production dropped from 26 hours to 3.
Developers say they're happier. We haven't seen more bugs reach customers,
although we didn't track bug counts before the change.
