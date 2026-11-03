# Notes: partner export failure

- The night of 30 Oct is the run that starts 2026-10-31T02:00Z (the job runs at 02:00 UTC for the previous day).
- Failed both nights since. Last good run 2026-10-30T02:00Z.
- Dependabot PR #412 bumped parquet-writer 2.8.4 -> 3.0.1, merged 30 Oct 16:20 UTC.
- parquet-writer 3.0 changelog: "Default row_group_size raised from 10,000 to 1,000,000 rows for better compression."
- Our export config never set row_group_size, so we got the new default.
- Rows are buffered per row group before writing. 100x the rows per group -> memory climbs until the 2 GiB container limit.
- Repro locally: with row_group_size=10000 on 3.0.1, peak RSS 615 MiB, run completes. With default, OOM at ~1.9 GiB.
- Fix drafted on branch fix/export-row-groups: one line in config/export.yaml.
- Change freeze is on until 7 Nov. Deploying during the freeze needs sign-off from the person who owns the export (the asker).
- Harbor Analytics gets the file daily. Their monthly reconciliation runs Friday 6 Nov on whatever files they have.
- Raising the memory limit to 8 GiB would also work but costs a bigger node class and only hides the change.
