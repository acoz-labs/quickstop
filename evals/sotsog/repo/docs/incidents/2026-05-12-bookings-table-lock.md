# Incident 2026-05-12: bookings locked for 11 minutes

**What happened.** The 1.14 deploy ran migration `0019_bookings_branch_index`,
which created an index on `bookings (branch_id, starts_at)` with a plain
`CREATE INDEX`. That locks the table against writes until the index is built.
On 18 million rows it took 11 minutes, during opening hours. Every booking
attempt in that time timed out, and branch staff took bookings on paper.

**Why we didn't see it coming.** Tests run migrations against an empty
database, where the index builds instantly. Nobody checked how long it would
take on production data.

**What we did.** Nothing structural yet. We noted that `CREATE INDEX
CONCURRENTLY` would have avoided the lock.
