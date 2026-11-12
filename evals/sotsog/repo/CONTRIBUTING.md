# Contributing

## The workflow

1. Branch from `main`. Keep branches short: most merge within two days.
2. Open a pull request. CI runs `bin/check` on every push.
3. **Every pull request needs an approving review from a second person before
   it merges, and the review must be recorded on the pull request.** Branch
   protection on `main` enforces this: nobody, maintainers included, can push
   to `main` directly. This is a condition of our grant; see
   [docs/funding.md](docs/funding.md).
4. Squash-merge once CI is green and the review is in.

## Release notes

Every pull request that changes `src/` or `migrations/` adds one news
fragment to `changes/`, named `<pull request number>.<type>.md`, where type is
`feature`, `fix`, `removal` or `security`. Write it for branch staff, not for
developers: what changes for them, in one or two sentences. Documentation-only
and test-only pull requests need no fragment.

`bin/check` fails a pull request that changes `src/` or `migrations/` without
a fragment. At release time, `bin/release` compiles the fragments into
`CHANGELOG.md`, grouped by type, and deletes them.

## Migrations

Schema changes are SQL files in `migrations/`, numbered in order. The
deploy job applies new migrations before starting the new version. Tests run
every migration against an empty database.

## Checks

Run `bin/check` before pushing. It runs the tests, the linter and the
news-fragment check.
