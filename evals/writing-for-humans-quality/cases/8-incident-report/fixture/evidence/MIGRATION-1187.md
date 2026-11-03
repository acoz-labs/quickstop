# MIGRATION-1187: move batch-02 cron jobs to Ridgeline

Owner: Oskar (payments ops). Status: done 2026-11-01.

batch-02 is being retired at the end of November. Every cron entry on it moves to
the Ridgeline scheduler.

## Checklist per job

- [x] Copy the schedule from the crontab line into a Ridgeline job
- [x] Copy the command
- [x] Set owner and failure notifications
- [x] Comment out the cron entry
- [x] Verify the first run succeeds

## Jobs

| Cron entry | Ridgeline job | Moved |
|---|---|---|
| `0 2 * * * /opt/payouts/bin/cron-payout-wrapper.sh` | payout-batch | 2026-11-01 |
| `30 4 * * * /opt/payouts/bin/statement-export` | statement-export | 2026-11-01 |
| `*/15 * * * * /opt/payouts/bin/bank-ack-poll` | bank-ack-poll | 2026-11-01 |

Note: the payout entry calls a wrapper; Ridgeline calls the batch binary directly,
since Ridgeline handles logging and retries itself.
