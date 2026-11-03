312 merchants were paid late on 2–4 November: moving the payout batch to the new scheduler dropped its wait for the ledger close, so on nights the close ran late, it skipped merchants whose ledgers were still open. Please approve reimbursing the bank fees 41 of them have claimed, £3,140 in total. Support must answer the first claims by 12 November and will decline them without your approval.

Everyone owed has now been paid, and the wait has been back in place since 4 November.

## What happened

On 1 November, Oskar moved the nightly payout batch from cron on batch-02 to Ridgeline, as part of retiring that host. The old cron entry didn't start the batch directly. It ran a wrapper that waited up to three hours for the ledger close to finish. The migration copied the schedule and the command but not that wait, and the checklist had no step asking what the old entry did beyond its schedule.

The batch pays every merchant whose ledger partition is closed and defers the rest to the next night. Month-start invoicing pushed the close past 02:00 on three nights in a row (02:41, 02:17 and 02:26), so each of those runs started against a half-closed ledger. October had six late closes too, but the wrapper absorbed them and no one was paid late.

## Impact

- 358 payouts were deferred across the three nights: 188, 74 and 96.
- 312 merchants were affected. 46 of them were deferred on both 2 and 3 November and were two days late; the rest were one day late.
- £1.94 million arrived late in total. No payout was lost or sent twice; the catch-up run was checked against the next night's batch.

## Why we didn't catch it sooner

The only alert on the batch pages when the nightly count falls below half the 7-day average. The worst night still sent 92% of the usual count, so it never came close. Support raised it on 4 November after 23 tickets in three days.

## What's been done

- 4 November, 14:30: Oskar ran a catch-up for the 96 merchants deferred that night. Earlier deferrals had already gone out in the following night's batch.
- 4 November, 18:05: the Ridgeline job now depends on the ledger close, with the same three-hour limit the wrapper had. On 5 November the close finished at 02:09, the batch waited for it, and no one was deferred.

## The fee claims

The 41 claims cover overdraft fees, failed direct debits and similar charges, from £25 to £150 each (fee-claims.csv). Under the payout terms, support can approve up to £1,000 per incident on its own; above that the claims need your sign-off together. Each claim needs a reply within seven days of filing, and the earliest were filed on 5 November.

## Follow-ups

- A second alert that pages when the batch defers more than 20 merchants is drafted. I'll ship it next week; it doesn't need a decision.
- The other two jobs moved in the same migration call their programs directly, so they don't have the same gap.
- Adding "check what the old entry does besides run on schedule" to the migration checklist would have caught this before batch-02's remaining jobs move.
