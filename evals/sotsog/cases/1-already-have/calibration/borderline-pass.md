# Release notes in every pull request: no for Lanternhall

No: we already do this, so nothing needs adopting. Nothing changes in how we work. The only thing to watch is fragments becoming box-ticking.

Date 2026-11-12. Decided by the maintainers. Sources: the Pikeworth post and the library.

## The idea in brief

Every pull request adds its own typed release note, CI checks for it, and the release compiles the notes.

## What the evidence shows

Sound with caveats.

- **Who gains:** Pikeworth doesn't sell the practice.
- **Measured against:** its releases before the change (5 of 14 on time, then 14 of 14).
- **What's missing:** contributor cost isn't measured.
- **Whose conditions:** a small team, like ours.
- **Independent support:** Maple Row reports the same. The critique in fragment-fatigue.md says the check can become box-ticking ("misc fixes") unless reviewers read the notes.

## How it compares with what we do

| Principle | How they do it | How we do it | Fit |
|---|---|---|---|
| Note per change | file per pull request | fragment per pull request in `changes/` | already have |
| Typed notes | type in file name | type in file name | already have |
| CI check | fails without a note | `bin/check` fails without a fragment | already have |
| Release compiles notes | release script | `bin/release` | already have |

## Why this decision

Every principle is already in place and the notes have no known problem. The case against: maybe the notes could be better written, but nothing suggests they're bad. Commit-generated changelogs (conventional-commits-changelogs.md) would read too technical for branch staff.

## Revisit when

- Fragments become box-ticking in review.

## What we're not taking, and why

Nothing; we already have it.

## Sources

- Pikeworth post (link.md), read 2026-11-12.
- maple-row-fragments-a-year-on.md, read 2026-11-12.
- fragment-fatigue.md, read 2026-11-12.
- conventional-commits-changelogs.md, read 2026-11-12.
