As requested on Wednesday, I investigated the late merchant payouts. First I went through the support tickets, then the channel timeline, then the payout batch log, then the ledger close times, and finally the scheduler configuration. This report sets out what I did and what I found, in the order I found it.

## Background

A payout batch is a scheduled job that sends money owed to merchants in one file to the bank. Cron is a standard Unix tool that runs commands on a schedule. A scheduler such as Ridgeline does the same thing but adds features like retries, logging and dependencies between jobs. A ledger close is the process of finalising the day's accounting entries.

## Investigation

`payout-batch.log` shows partitions in state OPEN on 2, 3 and 4 November. `cron-payout-wrapper.sh` polls for a marker file for up to 3 hours. `ridgeline/payout-batch.job.yaml` has no `depends_on`. ledger-close-durations.csv shows close_finished_utc after 02:00 on those nights. MIGRATION-1187.md says the migration was done on 1 November. Then I checked the alert rule. Then I checked the fee claims.

The batch ran before the ledger close finished on those nights. Some merchants were deferred.

## Fee claims

fee-claims.csv has 41 rows with a total of 3,140. Section 7.3 of the payout terms covers this.

## Summary

To summarise, the batch ran before the ledger close finished on those nights. Let me know if you have any questions or if there's anything else you'd like me to look into.
