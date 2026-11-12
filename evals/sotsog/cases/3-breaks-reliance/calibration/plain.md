# Review after merge: should Lanternhall follow Quarry Labs?

**Decision:** No. Keep the required, recorded review before every merge.

Lanternhall's grant from the Halvorsen Civic Foundation (docs/funding.md, section 4.2) requires every change to be reviewed by a second person before deploy, with a record the Foundation can audit; the approving review on each pull request is that record. Pushing straight to main and reviewing afterwards would break that condition, and the grant pays for maintenance. Nothing changes in the workflow.

## What I found

- Quarry Labs' lead time fell from 26 hours to 3, but it never tracked bugs before the change, so its "no more bugs" has no baseline, and its careers page uses the practice to hire.
- post-merge-review-in-practice.md describes post-merge review decaying into skimming, and a team that failed an audit because a third of its changes had no review record.
- pair-programming-as-review.md offers pairing as a faster form of review, which could count if the Foundation accepts the record.
- trunk-based-at-kestrel.md shows most of the speed gain is possible with reviews kept, by answering review requests within two working hours. That isn't adopted here; it can be proposed as its own change.

## When to look again

Only if the grant's review condition changes or the grant ends.

Sources read 2026-11-12: link.md, delivery-metrics-review.md, trunk-based-at-kestrel.md, post-merge-review-in-practice.md, pair-programming-as-review.md.
