# Managed repository standard

SDLC template version: `2026.09.21.3`.

The template owns the files enumerated in `.sdlc/managed.json`. Their hashes
identify the installed content. `bin/sdlc check` verifies them.
The `SDLC_VERSION` marker is managed too, so propagation cannot leave the
repository's visible version behind its installed commands and manifest.
When taking ownership of a previously unmanaged marker, automatic updates accept
only an absent file or the exact prior manifest version plus newline. Inspect and
reconcile other content explicitly before applying; local edits are not discarded.
Application configuration lives in `.sdlc/config.json`, outside the managed-file set.
Product instructions, code, tests and deployment commands remain repo-specific.

Use `bin/sdlc apply --source PATH --target PATH` to update an already managed
checkout. Initial adoption requires `--adopt`. Edited managed files cause a
conflict; review and reconcile them rather than overwriting them silently.
A template maintainer updates source files, runs `bin/sdlc stamp`, tests, and
publishes a reviewed version. `bin/sdlc inventory --org ORG` discovers all active
repositories. Cascade every target and reread the live inventory at completion.
For a complete operation use:

```sh
bin/sdlc cascade --source /path/to/reviewed-template --workspace /path/to/cascade --org ORGANIZATION --adopt
# Publish prepared changes through contributor PRs and maintainer review.
bin/sdlc cascade --source /path/to/reviewed-template --workspace /path/to/cascade --org ORGANIZATION --verify
```

The source must be a clean reviewed commit. The receipt tracks every active
repository, source identity, prepared branch or verified published head and
unresolved errors. Preparation is not completion. Verification rereads published
files/modes/config and organization inventory; any failure or newly active repo
keeps the operation incomplete. Reuse the workspace to resume the same source.
No pilot, waves or optional lagging adoption. No unrelated production deployment.

Configuration declares `delivery_profile`, `verification_mode` and `validation`.
The default mode is `local`: independent maintainer receipts satisfy the merge
gate, regardless of runner availability. `required_checks` describes the optional
Actions profile and is enforced only when `verification_mode` is `actions`.
Service/artifact repos declare concrete `acceptance_criteria` and `release_criteria`
with procedures in `docs/delivery.md`. Automated artifact checks may additionally
use `acceptance` commands. Scripted promotion declares real `promotion`,
`release_verification` and `rollback` commands; native/provider runbooks use the
maintainer-attested `sdlc-release record` path. Acceptance and release commands
receive `RELEASE_SHA` and immutable `RELEASE_ARTIFACT`. Hooks must verify the
artifact itself, not just an unrelated healthy service. Missing deployment
capability remains an explicit gap; commands must never be placeholder successes.
Service/artifact profiles keep their real candidate acceptance/release machinery;
non-deployable explicitly means no release target. Missing deployment capability
must be documented as a gap, never disguised as non-deployable to pass a check.
New repositories adopt the standard at creation and join every future cascade.

Personal account names and credentials are never managed template content.
For an artifact whose source predates configuration adoption, the explicit
`retained_candidates` transition is documented in
`docs/operations/local-verification.md`. It binds a reviewed policy revision
separately from original product bytes; it is not a general policy override.
See `docs/operations/sdlc.md` for delegated authority, role separation and the
three workflows. CI and workflow checks are evidence, not substitutes for review.
