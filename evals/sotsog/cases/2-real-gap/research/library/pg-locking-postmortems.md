# What 31 public postmortems say about schema migrations

Source: https://dbreliability.example.org/papers/migration-postmortems-2026
Author: Database Reliability Working Group (independent researchers; no vendor funding)
Published: 2026-06-18

We read 31 public postmortems of outages caused by PostgreSQL schema
migrations. 22 were long locks from statements a static check would have
flagged (index builds, table rewrites, constraint validation). 6 were slow
data changes that only showed up on real data volumes. 3 were application
code that broke against the new schema. Teams that had both a static check and
a timed rehearsal reported no repeat incidents of the first two kinds.
