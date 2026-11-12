# Should Lanternhall adopt per-pull-request release notes?

## Summary

Pikeworth's post describes adding a release-note file to every pull request, typed by kind, checked in CI and compiled at release. I compared it with Lanternhall's repository.

## Recommendation

Don't adopt it: Lanternhall already does all of it. CONTRIBUTING.md requires a news fragment in `changes/` for every pull request that touches `src/` or `migrations/`, typed by file name; `bin/check` fails a pull request without one; and `bin/release` compiles them into CHANGELOG.md. Nothing changes, and no work is needed.

## What else I looked at

- The critique in fragment-fatigue.md warns that the check can turn into box-ticking, with notes like "misc fixes", unless a reviewer reads fragments and trivial changes can skip. Our required review reads every pull request, and docs-only and test-only changes are already exempt.
- conventional-commits-changelogs.md proposes generating the changelog from commit titles instead. That suits developer audiences; our notes are for branch staff, so it would be a step back.
- The Maple Row report and the Harbourline survey (maple-row-fragments-a-year-on.md, harbourline-release-notes-survey.md) support fragments for small teams.

## When to look again

If fragments start reading like box-ticking, or contributors ask for a broader skip rule.

Sources read 2026-11-12: link.md, maple-row-fragments-a-year-on.md, harbourline-release-notes-survey.md, fragment-fatigue.md, conventional-commits-changelogs.md.
