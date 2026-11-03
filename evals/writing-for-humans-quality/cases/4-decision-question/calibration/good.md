Should we delete the v1 API in this release, or keep it until the next one? Three clients still used it last week, and Northwind Freight alone sends 40% of v1 traffic, so deleting it on 19 November breaks their shipment sync and two other integrations. Keeping it one more release (about six weeks) gives them time, but leaves the static-token security finding open past its 30 November deadline, which needs your documented risk acceptance.

The other two clients are Pellucid Health (nightly batch and webhook callbacks) and Orchard & Vale (inventory polling). All three were warned in June and September. Northwind's account manager says their migration is "planned for Q1", so even six weeks may not be enough for them.

If you choose to keep v1, I'll draft the risk acceptance with a January date. If you choose to delete it, someone should call Northwind this week.
