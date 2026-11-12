# Pushing straight to main with review after merge: no for Lanternhall

We keep required, recorded review before every merge and won't move to pushing straight to main. Nothing changes in our workflow. Dropping pre-merge review would break the Halvorsen grant's condition that every change is reviewed by a second person with an auditable record, and the grant pays for maintenance.

Date 2026-11-12. Decided by the maintainers. Sources read: Quarry Labs' post and five library pages.

## The idea in brief

Developers push small commits straight to the main branch, hide unfinished work behind feature flags (switches that keep new code off until it's ready), and review each other's commits the morning after merge, relying on tests and fast rollback instead of a review gate.

## What the evidence shows

Weak for our setting. It may suit a small high-trust startup, but the evidence for post-merge review is thin.

- **Who gains:** Quarry Labs uses it to recruit: its careers page sells "no pull request queues".
- **Measured against:** its own lead time before (26 hours to 3), but bug counts weren't tracked before the change, so "no more bugs" has no baseline.
- **What's missing:** any record of whether reviews still happen; costs; failures.
- **Whose conditions:** a 12-person startup with no auditor; we have an audited grant.
- **Independent support:** the Software Delivery Research Group found small changes reviewed quickly deliver as fast as post-merge review and catch more defects, and found no study of post-merge review in audited settings. Aisha Bello's critique reports post-merge review decaying into skimming, and one team bringing pre-merge review back after an auditor found a third of changes had no review record.

## How it compares with what we do

| Principle | How they do it | How we do it | Fit |
|---|---|---|---|
| Push straight to main | no branches for routine work | branch protection forbids it (CONTRIBUTING.md) | conflicts |
| Feature flags | hide unfinished work | short branches merged within two days | doesn't apply |
| Review after merge | daily reading of commits | required approving review before merge, recorded on the pull request | conflicts |
| Tests and rollback as safety net | strong suite, fast rollback | `bin/check` in CI | partly |

Adopting it would remove the recorded pre-merge review that the grant audit relies on (docs/funding.md).

## Why this decision

The gain is faster merges; the user's answers say slow reviews are annoying, not urgent. The cost is the grant: section 4.2 requires review before deploy with an auditable record, and the Foundation audits a sample every year. The strongest case for the idea: our part-time reviews sometimes take a day, and Quarry's lead time fell eightfold. But Kestrel Maps got most of that gain while keeping reviews, by answering review requests within two working hours. Pairing (Grace Lindgren's alternative) counts as review only if the auditor accepts its record, which we have no reason to test.

## Revisit when

- The Halvorsen grant's review condition changes or the grant ends.

## What we're not taking, and why

Pushing to main and review after merge: they break the grant condition. Nothing is borrowed. The one compatible piece, a target time for answering review requests (Kestrel's two working hours), isn't needed now: the maintainers say slow reviews are annoying, not urgent.

## Sources

- Elena Marsh, "Ship to main, review after" (link.md), read 2026-11-12. Quarry Labs head of engineering; uses the practice in hiring. Shows lead time; claims no more bugs without a baseline.
- Software Delivery Research Group, "Does pre-merge review slow teams down?" (delivery-metrics-review.md), read 2026-11-12. Independent academic review.
- Omar Haddad, "Trunk-based development at Kestrel, with reviews kept" (trunk-based-at-kestrel.md), read 2026-11-12.
- Aisha Bello, "Post-merge review: what happens six months in" (post-merge-review-in-practice.md), read 2026-11-12. Critique.
- Grace Lindgren, "Pairing as review" (pair-programming-as-review.md), read 2026-11-12. Competing approach.
