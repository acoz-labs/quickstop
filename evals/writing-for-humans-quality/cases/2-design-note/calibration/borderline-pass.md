# Job queue decision

We're keeping the sync job queue in SQLite on the sync host rather than moving it to Postgres. That ties the queue to a single host, so if sync ever needs a second worker machine we'll revisit this and move the queue to Postgres.
