# Architecture

orchard is one Python process. Requests arrive from the shops' reverse proxy and are dispatched by `src/orchard/api.py` to small handler functions, one per route and version. Handlers parse the request, call into the domain modules and return a JSON response; they never touch the database directly, because `db.py` is the only module that knows the schema. This keeps the domain modules testable with an in-memory SQLite database and keeps the SQL in one place.

## Stock

Stock is counted per shop, per supplier SKU, in the smallest unit the shop sells. `stock.py` adds deliveries, subtracts sales reported by the tills and applies manual adjustments from the warehouse tablets. Every operation is a row in the movements table, and the current level is the sum of movements, so the history of any count can be rebuilt. Adjustments carry a reason code from a fixed list; the tablets offer only those codes.

## Deliveries

Suppliers upload a CSV delivery note per delivery. `deliveries.py` checks the header, the column types and the supplier's SKU list, and rejects the whole file on the first error with a message the supplier can act on. Accepted files become delivery lines. `reconcile.py` then matches each delivery line to an open purchase-order line by supplier SKU. A line that delivers less than ordered is short, more than ordered is over, and a different SKU from the supplier's substitution list is a substitution. Unmatched lines are held for a person in the warehouse to review on a tablet.

## Alerts

Each shop has a reorder threshold per SKU. At six every morning, cron runs `python -m orchard.alerts`, which computes the SKUs below threshold for each shop and posts one message per shop to the staff chat. The job uses the same code path as the `/v2/alerts` API route, so the route and the job can't drift apart.

## Migrations

The schema changes only through numbered migration files in `migrations/`. Files in that folder are never changed by hand once written: hand edits to anything in `migrations/` are not allowed, and a new change always gets a fresh migration generated with `bin/migrate new`. Each migration holds the forward and reverse step for one table. After a migration, `bin/migrate bindings` regenerates `src/orchard/generated/`.

## Versions

Every route lives under a version prefix. A version's response shape never changes after release. New fields mean a new version, and old versions stay until no till calls them; the access log shows which versions are still in use.
