# Lock-safe migrations: adopt for Lanternhall

We'll lint migrations for locking statements and add a lock timeout to every migration. The brief below hands the work on. It addresses the two lock outages this year.

Date 2026-11-12. Decided by the maintainers. Sources: the Fernhill post and the library.

## The idea in brief

Check migrations for long-locking statements before deploy, and make them fail fast if they can't get a lock.

## What the evidence shows

Sound.

- **Who gains:** Fernhill sells nothing here.
- **Measured against:** its own outages before the change.
- **What's missing:** upkeep cost.
- **Whose conditions:** a bigger team, same database.
- **Independent support:** pg-locking-postmortems.md found most migration outages were locks a static check flags. The critique in rehearsals-are-a-privacy-risk.md says production copies leak personal data, so we skip rehearsals on copies.

## How it compares with what we do

| Principle | How they do it | How we do it | Fit |
|---|---|---|---|
| Lint migrations | CI check | none | gap |
| Lock timeout | every migration | none | gap |
| Rehearse on production copy | nightly backup | not allowed (patron data) | doesn't apply |

## Why this decision

Both 2026 incidents came from migrations that locked tables, and nothing checks migrations today because tests use an empty database. An online schema change tool (online-schema-change-tools.md) is the alternative, but it needs an owner we don't have.

## Revisit when

- A migration still locks a table after this: consider rehearsals on synthetic data.

## Implementation brief

Goal: catch lock-taking migrations before deploy. In scope: lint and lock timeout; out of scope: rehearsals, schema change tools.

1. Write `bin/lint-migrations` to fail new files in `migrations/` that use `CREATE INDEX` without `CONCURRENTLY` or `ALTER COLUMN ... TYPE`.
2. Run it from `bin/check`.
3. Require `SET lock_timeout = '3s';` in every new migration, checked by the lint.

Done when `bin/check` fails on copies of migrations 0019 and 0023. It worked if there's no lock incident in six months. Roll back by removing the lint from `bin/check`.

## Sources

- Fernhill post (link.md), read 2026-11-12.
- pg-locking-postmortems.md, read 2026-11-12.
- rehearsals-are-a-privacy-risk.md, read 2026-11-12.
- online-schema-change-tools.md, read 2026-11-12.
