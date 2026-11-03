The export failed because a library upgrade on 30 October made each batch about 100 times larger, and the job ran out of memory. I need your sign-off to deploy a one-line fix during the change freeze. Until it ships, every nightly export fails and Harbor Analytics misses that day's data, and their monthly reconciliation on Friday would run with gaps.

**What happened.** The parquet-writer library went from 2.8.4 to 3.0.1 that afternoon (Dependabot PR #412). Version 3.0 raised its default row group size from 10,000 rows to 1,000,000. Our export config never set that value, so the job picked up the new default, buffered 100 times more rows per group, and was killed at the 2 GiB container limit seven minutes in. The run for the night of 30 October and both runs since wrote nothing (export-worker.log, 31 Oct and 1 Nov).

**The fix.** Setting the row group size back to 10,000 restores the old behaviour. With that setting the new version peaked at 615 MiB locally and finished. The change is ready on the fix/export-row-groups branch. Raising the memory limit to 8 GiB would also work, but it needs a bigger node class and only hides the change.

Reply "go" and I'll deploy it tonight, before the 02:00 UTC run.
