# Lanternhall Bookings

Lanternhall books meeting rooms, study rooms and the maker space across the
nine branches of the Tidewater Valley Library Network. Patrons book through the
web form; branch staff use the `lanternhall` command-line tool to manage rooms,
blackout dates and no-shows.

It is a small Python service backed by PostgreSQL 15. The network's IT team
runs the production copy. One other organisation, the Coastline Library
Consortium, deploys its own copy from our monthly release tarballs.

## Size

- About 18 million rows in `bookings`, going back to 2012, and growing by
  roughly 9,000 a day.
- Two part-time maintainers (about six hours a week between them) and a few
  volunteer contributors.
- The test suite has 310 tests and runs in under two minutes; a full CI run,
  lint included, takes about four minutes.

## Working on it

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. The
release process is in [docs/releases.md](docs/releases.md), and past decisions
are in [docs/decisions/](docs/decisions/).
