# Release notes in every pull request: no for Lanternhall

We won't take this up, because Lanternhall already works this way: every pull request that changes code carries its own typed release note, CI enforces it, and the release compiles the notes. Nothing changes in how we work.

Date 2026-11-12. Decided by the maintainers. Sources read: Pikeworth's post and five pages from the library.

## The idea in brief

Each pull request adds a small release-note file (a "news fragment") with a type such as feature or fix. CI fails a change that has none, and the release script gathers the files into the changelog. Pikeworth adopted it to stop writing notes by hand the night before a release.

## What the evidence shows

Sound, with caveats. Two independent sources back it, and the main caveat is notes turning into box-ticking.

- **Who gains:** Pikeworth sells bookkeeping software, not release tooling, so it gains little if readers adopt it beyond reputation.
- **Measured against:** its own record before the change: notes on time in 14 of 14 releases after, against 5 of 14 before. "Fewer what-changed questions" is a claim, not counted.
- **What's missing:** the cost to contributors is mentioned but not measured.
- **Whose conditions:** a small product team, close to ours in size.
- **Independent support:** Maple Row reports complete notes and no changelog conflicts after a year; the Harbourline survey found 15 of 17 fragment teams called their notes complete (self-reported). Tobias Lindqvist's critique argues that fragments cause merge conflicts when two pull requests edit the same note file.

The search covered all six library pages; two were noise (a shader tutorial and a paid changelog service).

## How it compares with what we do

| Principle | How they do it | How we do it | Fit |
|---|---|---|---|
| One note file per change | `changelog.d/` file per pull request | `changes/<number>.<type>.md` per pull request (CONTRIBUTING.md) | already have |
| A type per note | type in the file name | feature, fix, removal or security in the file name | already have |
| CI refuses a change without a note | check on application code; docs exempt | `bin/check` fails changes to `src/` or `migrations/` with no fragment; docs and tests exempt | already have |
| The release compiles the notes | release script groups and deletes them | `bin/release` compiles `changes/` into `CHANGELOG.md` and deletes them | already have |

Nothing we do now would be removed or weakened.

## Why this decision

There's nothing to gain: every principle is already in place, and the maintainers know of no problem with the release notes. The strongest case for doing something is the critique, but merge conflicts on fragments have never happened here. There's also a commit-based alternative (conventional-commits-changelogs.md).

## Revisit when

- If our needs change.

## What we're not taking, and why

The practice as a whole.

## Sources

- Dana Okafor, "Stop writing changelogs at release time" (link.md), read 2026-11-12. Pikeworth staff engineer; no tooling to sell. Shows a before-and-after count of on-time releases; claims fewer support questions.
- Priya Venkataraman, "News fragments a year on: what worked at Maple Row" (maple-row-fragments-a-year-on.md), read 2026-11-12. Volunteer maintainer; reports results, not measured.
- Harbourline Research Collective, "How 40 small teams write release notes: survey results" (harbourline-release-notes-survey.md), read 2026-11-12. Independent; self-reported.
- Tobias Lindqvist, "Fragment fatigue" (fragment-fatigue.md), read 2026-11-12. Consultant; critique from two teams.
- conventional-commits-changelogs.md, read 2026-11-12.
