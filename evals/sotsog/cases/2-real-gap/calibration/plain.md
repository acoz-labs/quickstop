# Fernhill Transit's safe migrations: assessment for Lanternhall

Verdict: adapt. Take the migration lint and the lock timeout, and rehearse on synthetic data instead of a production copy.

## Why

Lanternhall had two outages in 2026 from migrations that locked tables during opening hours: an 11-minute lock from a plain `CREATE INDEX` on `bookings` (May) and a 6-minute lock from a column type change on `rooms` (September). Nothing checks migrations today: tests run them on an empty database. A lint catches exactly these statements; pg-locking-postmortems.md found 22 of 31 public migration outages were of this kind.

We don't take rehearsals on a copy of production: the bookings table holds patron names and phone numbers, the IT team forbids copies outside production, and rehearsals-are-a-privacy-risk.md makes the same point. We also pass on online schema change tools (online-schema-change-tools.md), which need extra disk and an owner.

## Plan

Goal: no migration can hold a long lock on `bookings` or `rooms` in production. Out of scope: production copies and schema change tools.

1. Add `bin/lint-migrations`, failing new files in `migrations/` that use `CREATE INDEX` without `CONCURRENTLY`, `ALTER COLUMN ... TYPE`, or `ADD COLUMN ... NOT NULL` without a default, and printing the safe form.
2. Call it from `bin/check`, so CI runs it on every pull request.
3. Require `SET lock_timeout = '3s';` at the top of every new migration; the lint enforces it.
4. Add `bin/rehearse-migration` to time a migration against 18 million synthetic bookings on the empty staging server; migrations touching `bookings` or `rooms` note their rehearsal time in the pull request.

Done when `bin/check` fails on copies of migrations 0019 and 0023 and passes on their safe forms. It worked if there's no migration lock incident in the next six months; roll back by removing the lint call from `bin/check`.

Sources read 2026-11-12: link.md, lockcheck-at-orchard-health.md, pg-locking-postmortems.md, rehearsals-are-a-privacy-risk.md, online-schema-change-tools.md.
