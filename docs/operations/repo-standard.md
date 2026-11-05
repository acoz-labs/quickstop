# Managed repository standard

SDLC template version: `2026.11.05.3`.

The template owns the files in `.sdlc/managed.json`; `bin/sdlc check` verifies
their hashes. That includes the `SDLC_VERSION` marker. `apply` takes over an
unmanaged marker only if it is missing or holds the prior manifest version;
reconcile anything else by hand. Repo config (`.sdlc/config.json`), product
instructions, code, tests and deploy commands stay repo-owned. Accounts,
credentials, machine paths and personal setup are never template content.

## Starters

`.sdlc/starters/` holds repo-owned starters for `CLAUDE.md`,
`docs/repository.md`, `REVIEW.md` and `.claude/settings.json`. `apply` adds one
only where nothing exists and never overwrites. They are outside the manifest,
so each repo edits its own. After a cascade, `bin/check-starters --root PATH
--ref origin/main` checks each target keeps their required parts.

## Updating and cascading

`bin/sdlc apply --source PATH --target PATH` updates a checkout (`--adopt` the
first time); edited managed files conflict for reconciliation. Maintainers edit
sources, run `bin/sdlc stamp` and tests, and publish a reviewed version.
`bin/sdlc inventory --org ORG` lists active repos.

```sh
bin/sdlc cascade --source /path/to/reviewed-template --workspace /path/to/cascade --org ORGANIZATION --adopt
# Publish prepared changes through contributor PRs and maintainer review.
bin/sdlc cascade --source /path/to/reviewed-template --workspace /path/to/cascade --org ORGANIZATION --verify
```

The source must be a clean reviewed commit. The receipt records the source
identity and every active repo's prepared branch or published head and errors.
Preparation is not completion: `--verify` rereads published files, modes, config
and the inventory; a failure or newly active repo leaves it incomplete. Reuse
the workspace to resume. New repos adopt at creation.

## Configuration

Config declares `delivery_profile`, `verification_mode` and `validation`. In the
default `local` mode, independent maintainer receipts with live proof satisfy
the merge gate. `required_checks` applies only in `actions` mode.

Service and artifact repos declare `acceptance_criteria` and `release_criteria`,
described in `docs/delivery.md`, and may add `acceptance` commands. Scripted
promotion declares `promotion`, `release_verification` and `rollback`; manual
runbooks use `sdlc-release record`. Hooks must verify the artifact they receive,
not just a healthy service. Non-deployable means no release target. A missing
deploy capability is a documented gap, never a placeholder or a relabelling.

Artifacts built before configuration use `retained_candidates`
(`docs/operations/local-verification.md`), which pins a reviewed policy
separately from the product bytes; it is no general override.
