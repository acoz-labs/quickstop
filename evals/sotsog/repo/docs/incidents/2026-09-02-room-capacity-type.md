# Incident 2026-09-02: bookings unavailable for 6 minutes

**What happened.** Migration `0023_room_capacity_numeric` changed
`rooms.capacity` from `smallint` to `integer`. The type change rewrote the
`rooms` table and, through a foreign key check, held a lock that blocked new
bookings for 6 minutes during the morning rush.

**Why we didn't see it coming.** Same as the May incident: tests run on an
empty database, and nothing reviews a migration for locks.

**Follow-up.** Second incident of this kind this year. We agreed to look for
a way to catch lock-taking migrations before they reach production.
