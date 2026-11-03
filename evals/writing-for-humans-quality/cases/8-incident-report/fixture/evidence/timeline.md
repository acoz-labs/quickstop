# #payments-ops channel export, 1-5 Nov (UTC)

**Sun 1 Nov**
- 11:02 Oskar: Starting MIGRATION-1187, payout batch from batch-02 cron to Ridgeline.
- 11:40 Oskar: Ridgeline job payout-batch created, schedule 0 2 * * *, same as the crontab. Cron entry commented out on batch-02.
- 11:41 Oskar: First run will be tonight 02:00. I'll check it Monday morning.

**Mon 2 Nov**
- 02:00 Ridgeline: payout-batch started.
- 02:41 ledger-close: close complete for 2026-11-01.
- 02:58 Ridgeline: payout-batch succeeded (exit 0).
- 08:15 Oskar: payout-batch first run on Ridgeline green. 2,173 payouts sent. Looks normal.
- 16:30 Femi: Couple of merchants asking where their payout is. Probably bank side, will watch.

**Tue 3 Nov**
- 02:00 Ridgeline: payout-batch started.
- 02:17 ledger-close: close complete for 2026-11-02.
- 02:49 Ridgeline: payout-batch succeeded (exit 0).
- 14:05 Femi: Nine more "missing payout" tickets. All Monday or Tuesday.

**Wed 4 Nov**
- 02:00 Ridgeline: payout-batch started.
- 02:26 ledger-close: close complete for 2026-11-03.
- 02:55 Ridgeline: payout-batch succeeded (exit 0).
- 10:12 Femi: 23 tickets now. This isn't the banks. Can someone look? @Rosa
- 10:20 Rosa: Asking the agent to investigate. Oskar, Priya, please help it with access.
- 12:47 Priya: Close ran late Mon-Wed, month-start invoicing. 02:41, 02:17, 02:26. Normal for the first week of the month.
- 13:30 Oskar: Found it with the agent. Old cron ran a wrapper that waited for close. Ridgeline job doesn't. My miss in the migration.
- 14:30 Oskar: Running catch-up batch for the 96 merchants skipped last night.
- 14:52 Oskar: Catch-up done, 96 paid. Earlier skips were picked up by the next night's batch.
- 18:05 Oskar: Dependency fix deployed to Ridgeline (reviewed). Tonight's run waits for close again.

**Thu 5 Nov**
- 02:00 Ridgeline: payout-batch waiting on ledger-close.
- 02:09 ledger-close: close complete for 2026-11-04.
- 02:09 Ridgeline: payout-batch started.
- 02:51 Ridgeline: payout-batch succeeded (exit 0). 0 skipped.
- 09:40 Femi: First fee claims coming in. Merchants charged overdraft and failed direct debit fees. Do we reimburse?
- 09:52 Rosa: Waiting for the report before deciding.
