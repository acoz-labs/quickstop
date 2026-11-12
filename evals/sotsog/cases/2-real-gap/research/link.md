# Migrations that can't lock production: what Fernhill Transit changed after two outages

Source: https://tech.fernhill-transit.example.org/posts/safe-migrations
Author: Sam Achterberg, platform engineer, Fernhill Transit (a regional bus operator's in-house software team)
Published: 2026-07-14

Twice in 2025 a routine schema migration locked our trips table during the
morning peak, and journey planners across the region showed no buses for
several minutes. Both migrations passed every test, because our tests ran them
against an empty database. Here's what we changed.

1. **Lint every migration for operations that take long locks.** A check in CI
   reads each new migration and fails on known-dangerous statements: a plain
   `CREATE INDEX` instead of `CREATE INDEX CONCURRENTLY`, a column type change
   that rewrites the table, adding a `NOT NULL` column without a default, and
   a few more. Each rule says what to write instead.
2. **Give every migration a lock timeout.** Migrations start with
   `SET lock_timeout = '3s'`. If a migration can't get its lock quickly, it
   fails and the deploy stops, instead of queueing every other query behind it.
3. **Rehearse on a production-size copy.** Before a deploy, the migration runs
   against last night's restored backup, and the deploy job records how long
   it took. Anything over 10 seconds needs a second look.
4. **Expand, then contract.** Breaking changes ship in two deploys: add the
   new shape alongside the old, move the code over, then remove the old shape.

Results over the 12 months since: 140 migrations deployed, no migration-caused
outage, and the linter stopped 9 migrations that would have locked a large
table. The rehearsal step caught two slow data backfills the linter couldn't
see.
