# Lock-safe migrations: adapt for Lanternhall

We'll lint every migration for long-locking statements and give every migration a lock timeout, and rehearse slow migrations on a synthetic production-size database instead of a copy of production. The implementation brief below is ready to hand to whoever does the work. It targets the cause of both outages this year, when migrations locked bookings during opening hours.

Date 2026-11-12. Decided by the maintainers. Sources read: Fernhill Transit's post and five library pages.

## The idea in brief

Before a schema migration reaches production, check it for statements that hold long table locks (a plain `CREATE INDEX`, a column type change that rewrites the table), make it give up quickly if it can't get a lock (a "lock timeout"), and time it against production-size data. Breaking changes go out in two steps ("expand, then contract").

## What the evidence shows

Sound. The mechanism is well understood and independently supported.

- **Who gains:** Fernhill Transit runs buses and sells nothing here; the post names an open-source approach.
- **Measured against:** its own year before: two migration outages in 2025, none in the 140 migrations since; the linter stopped 9.
- **What's missing:** setup and upkeep effort; the privacy cost of copying production.
- **Whose conditions:** a larger in-house team with its own database; the lint and timeout carry over to us, the production-copy rehearsal doesn't.
- **Independent support:** the Database Reliability Working Group's review of 31 postmortems found 22 were long locks a static check would flag and 6 were slow data changes only real volumes show. Orchard Health ran a linter for a year (19 real problems in 23 flags) but refused production copies because of patient data. Ruth Abernathy's critique argues production copies in test are a privacy risk, and recommends synthetic or masked data.

## How it compares with what we do

| Principle | How they do it | How we do it | Fit |
|---|---|---|---|
| Lint migrations for long locks | CI check on each new migration | nothing; tests run migrations on an empty database (CONTRIBUTING.md) | gap |
| Lock timeout on every migration | `SET lock_timeout = '3s'` | none | gap |
| Rehearse on production-size data | restored nightly backup | none; and the IT team forbids copies of production | partly |
| Expand, then contract | two deploys for breaking changes | not written down | partly |

Nothing we rely on is weakened.

## Why this decision

Gains: the two 2026 incidents (an 11-minute lock from a plain index build, a 6-minute lock from a type change) are exactly what a linter flags, and nothing checks migrations today, because tests run them on an empty database. Costs: a few days of setup and a little upkeep, within the six hours a week we have. The case against: a lint can't see slow data changes, and an online schema change tool (Lars Pettersen's alternative) would handle rewrites automatically. But that tool needs extra disk and someone to own it, which we don't have. We adapt rather than adopt because patron data can't leave the production network, so rehearsals use synthetic data.

## Revisit when

- Another migration causes a lock incident despite the lint: add rehearsals for every migration.
- Roll back the lint if it blocks more than one safe migration a month and the rules can't be tuned.

## Implementation brief

**Goal.** No migration can lock `bookings` or `rooms` for more than a few seconds in production.

**In scope:** a migration lint in `bin/check`, a lock timeout in every migration, timed rehearsals on the empty staging server with synthetic data. **Out of scope:** online schema change tools, production copies.

**Changes, in order:**

1. Add `bin/lint-migrations`, a script that reads new files in `migrations/` and fails on: `CREATE INDEX` without `CONCURRENTLY`; `ALTER TABLE ... ALTER COLUMN ... TYPE`; `ADD COLUMN ... NOT NULL` without a default; `ADD CONSTRAINT` without `NOT VALID`. Each failure prints the safe form.
2. Call it from `bin/check`, so CI runs it on every pull request.
3. Require `SET lock_timeout = '3s';` as the first line of every new migration; the lint checks it.
4. Add `bin/rehearse-migration`, which loads a synthetic dataset of 18 million bookings into the staging database and times a migration; document in CONTRIBUTING.md that migrations touching `bookings` or `rooms` are rehearsed and their time noted in the pull request.
5. Document expand-then-contract in CONTRIBUTING.md under Migrations.

**Acceptance criteria:** `bin/check` fails on a test migration with a plain `CREATE INDEX` and passes with `CONCURRENTLY`; it fails on a migration without the lock timeout; the rehearsal script reports a duration on staging.

**How to tell it worked:** no migration-caused lock incident in the next six months; count lint failures per month to see it isn't blocking safe work.

**Verify and roll back:** run `bin/check` on migrations 0019 and 0023, which must fail. To roll back, remove the call from `bin/check`.

**Open risks:** the lint's rules may miss a new kind of lock; the synthetic data may not match real distributions.

## What we're not taking, and why

Rehearsing on a restored production backup: patron names and phone numbers can't leave the production network.

## Sources

- Sam Achterberg, "Migrations that can't lock production" (link.md), read 2026-11-12. Fernhill Transit platform engineer; before-and-after counts, no product to sell.
- Jonah Bellweather, "A year of linting migrations at Orchard Health" (lockcheck-at-orchard-health.md), read 2026-11-12. Measured flags; no rehearsals because of patient data.
- Database Reliability Working Group, "What 31 public postmortems say about schema migrations" (pg-locking-postmortems.md), read 2026-11-12. Independent.
- Ruth Abernathy, "Production copies in test are a privacy incident waiting to happen" (rehearsals-are-a-privacy-risk.md), read 2026-11-12. Critique.
- Lars Pettersen, "Online schema change tools" (online-schema-change-tools.md), read 2026-11-12. Competing approach; consultant.
