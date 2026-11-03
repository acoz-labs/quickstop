# Investigation notes: late merchant payouts, 2-4 Nov

Working notes, kept as I went. Asked by Rosa (head of payments operations) on Wed 4 Nov.

- Support (Femi) raised it Wed 4 Nov 10:12: 23 tickets since Monday from merchants saying their payout didn't arrive.
- Payout batch runs nightly at 02:00 UTC. It pays every merchant whose ledger partition is closed for the previous day. Merchants whose partition is still open are skipped and their balance rolls to the next night.
- Ledger close (Priya's team) usually finishes 01:20-01:50 UTC. Month-start invoicing pushes it later.
- Sun 1 Nov: payout batch moved from cron on batch-02 to the Ridgeline scheduler (MIGRATION-1187). Cutover by Oskar.
- The old cron entry ran a wrapper script, not the batch directly. The wrapper polls for the ledger close marker and waits up to 3 hours. See cron-payout-wrapper.sh.
- The Ridgeline job calls the batch binary directly at 02:00 with no dependency. The migration copied the schedule from the crontab line and missed the wait in the wrapper. See ridgeline/payout-batch.job.yaml.
- Ledger close finished after 02:00 on 2, 3 and 4 Nov (02:41, 02:17, 02:26). On those nights the batch ran against a half-closed ledger and skipped every merchant whose partition was still open.
- October had 6 nights where close finished after 02:00. The wrapper waited each time; no late payouts. So the wait was doing real work.
- Skipped: 188 on 2 Nov, 74 on 3 Nov, 96 on 4 Nov. 358 skipped payouts, 312 distinct merchants. 46 merchants were skipped on both 2 and 3 Nov, so they were two days late. Total value delayed: GBP 1,942,610.
- Why no alert: payout-volume alert fires when the nightly count is below 50% of the 7-day average. Worst night was 2 Nov at 92% of normal. Alert never came close.
- Wed 4 Nov 14:30: Oskar ran a manual catch-up batch for the 96 skipped that night. Everyone owed was paid by 14:52.
- Wed 4 Nov 18:05: my fix deployed (fix-ridgeline-depends-on.diff, reviewed by Oskar). Adds depends_on ledger-close with a 3 hour timeout, same as the wrapper.
- Thu 5 Nov: close finished 02:09, batch started 02:09 after the dependency cleared, 0 skipped. Fix works.
- Fee claims: 41 merchants have filed claims for bank fees (overdraft, failed direct debits) they say the late payout caused. Total GBP 3,140. List in fee-claims.csv.
- Payout terms: we reimburse fees caused by our delay at our discretion; if the total for one incident is over GBP 1,000, the head of payments operations has to approve it. Claims need a reply within 7 days of filing. Earliest claims were filed 5 Nov, so the first replies are due Thu 12 Nov.
- Femi says support will decline the claims if there's no approval by then, because they can't promise money that isn't approved.
- Alert threshold: suggest an extra rule on skipped-merchant count (> 20 skipped). Draft in alerts/. Not urgent now the dependency is back; I can ship it next week.
- Not the cause: ledger close itself was fine, just slow; bank file upload worked every night; no data loss; no double payouts (checked the 4 Nov catch-up against the 5 Nov batch).
- MIGRATION-1187 checklist had "copy schedule" and "verify first run" but nothing about what the old entry did besides the schedule.
