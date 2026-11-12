# Pushing straight to main with review after merge: no for Lanternhall

No: we keep required pre-merge review. Nothing changes. Our grant requires a recorded second-person review of every change before deploy, and this idea removes it.

Date 2026-11-12. Decided by the maintainers. Sources: the Quarry Labs post and the library.

## The idea in brief

Push small commits to main, review them after merge, and rely on tests and rollback.

## What the evidence shows

Weak for us.

- **Who gains:** Quarry Labs uses it in hiring.
- **Measured against:** lead time before; bugs weren't tracked before.
- **What's missing:** whether reviews keep happening.
- **Whose conditions:** a startup with no auditor.
- **Independent support:** little. post-merge-review-in-practice.md reports reviews decaying to skims and a team failing an audit for missing review records.

## How it compares with what we do

| Principle | How they do it | How we do it | Fit |
|---|---|---|---|
| Push to main | routine | forbidden by branch protection | conflicts |
| Review after merge | next morning | required before merge, recorded | conflicts |

## Why this decision

The Halvorsen grant (docs/funding.md, section 4.2) requires recorded review before deploy, and the grant funds maintenance. Faster merges aren't worth that. Pairing as review (pair-programming-as-review.md) is an alternative, but only if the auditor accepts it.

## Revisit when

- The grant's review condition changes.

## What we're not taking, and why

All of it, because of the grant.

## Sources

- Quarry Labs post (link.md), read 2026-11-12.
- post-merge-review-in-practice.md, read 2026-11-12.
- pair-programming-as-review.md, read 2026-11-12.
