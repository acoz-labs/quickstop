# A year of linting migrations at Orchard Health

Source: https://orchardhealth.example.org/engineering/lint-your-migrations
Author: Jonah Bellweather, database lead, Orchard Health (a clinic booking service)
Published: 2026-03-03

We added an open-source migration linter, lockcheck, to CI in 2025. It flagged
23 migrations in the first year, 19 of them real problems: mostly plain index
builds and type changes on large tables. Setup took an afternoon. We also set
`lock_timeout` on all migrations; three deploys failed fast on it instead of
stalling the site. We did not set up rehearsals: our database holds patient
data, and copying it into a test environment was a non-starter.
