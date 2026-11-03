# Decision: the sync job queue stays in SQLite

We're keeping the Ferrylog sync job queue in SQLite, in WAL mode on the sync host, instead of moving it to the shared Postgres cluster. It is simpler to run and handles today's peak of about 40 jobs a minute with plenty of room. The cost is that the queue only works on one host, so if sync ever needs a second worker machine, we move the queue to Postgres first.

Decided on 3 November by Dana (sync lead), with Marco (platform), Ines (SRE) and Theo (backend).

## Why

- Since WAL mode was turned on last month, the queue has had no locking errors and no pages in four weeks. Hourly file-copy backups already cover it.
- A benchmark on the sync host reached 2,000 jobs a minute before it strained, about 50 times today's peak.
- Postgres would add a network hop to every enqueue and a two-week wait for a new database. Platform prefers stateful data in Postgres but didn't insist.

## When to revisit

The capacity plan says one host is enough until roughly 500 jobs a minute, which could come next year if the enterprise tier launches. Sync already runs on a single host for other reasons, so the queue doesn't add a new single point of failure.
