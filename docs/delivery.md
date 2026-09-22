# Plugin artifact delivery

Quickstop's delivery profile is **artifact**: consumers install plugin files,
not a hosted service. Repository-only marketplace or SDLC maintenance can complete at reviewed
merge when an issue explicitly preserves plugin payloads. It is not a new Claudit
release and supplies no retrospective runtime acceptance for 3.0.0.

## Candidate and acceptance

For a plugin release, keep the issue open (`Refs #N` on implementation PRs).
From the fixed reviewed merged SHA, retain one source archive with
`git archive --format=tar --output=/private/artifacts/quickstop.tar FULL_SHA`.
A source archive is the actual distributable for the current Markdown/JSON
Claudit package. Future compiled plugins must retain their actual built packages,
not substitute a source archive. Preserve each target package identity and the
exact generated catalog/index revision in the candidate record. Hash it with SHA-256 and record
its commit and target package versions. Store it outside the checkout. Nominate that
exact file and the complete implementation PR set with `bin/sdlc-release` using
the commands in [local verification](operations/local-verification.md).

Independently extract and inspect the retained archive in a temporary directory.
Run the repository checks there. For every advertised target in the release,
follow its `catalog.json` acceptance procedure in an isolated native harness.
Catalog/fixture checks cannot substitute for installing and exercising actual
packages. Record harness version and target package digest independently:

- `plugin-installation`: each advertised target installs from the retained bytes
  and discovers its declared components. Unsupported targets are absent from
  native indexes; no host-compatibility fallback establishes product support.
- `assigned-plugin-scenarios`: actual issue criteria and target-specific workflows
  from its acceptance document; record synthetic inputs and observed outcomes.
- `consumer-state-boundaries`: compare consumer files and state before and after;
  confirm read-only requests and intended write/network/PR boundaries. Use no
  personal configuration or externally sent test PRs without scoped authorization.

For Claudit, use [its Claude Code procedure](acceptance/claudit.md). There is no
Codex or Pi runtime acceptance to perform until a real target for that harness
is introduced. Pi acceptance includes dependency and extension behavior as well
as its linked local-package lifecycle.
For separate packages, acceptance and version changes can be scoped to affected
targets; retained evidence must identify unchanged targets rather than silently
reusing a verdict for changed bytes. A shared-package change affects every target
receiving that root. Release reports must identify results per target even when
they roll up under the shared SDLC criterion identifiers.

Supply the actual observations and openable sanitized evidence for these criteria
and `issue-criteria`; run the independent acceptance receipt and release gate.
A missing host or unavailable scenario is a gap to resolve, not a passing result.

## Publication and verification

The mutable marketplace branch currently makes merged plugin changes available
to consumers before a separate release gate. This is a legacy distribution
limitation, not protected pre-release promotion. Before the first future plugin
release, implement reviewed candidate isolation (for example version-pinned
marketplace sources) so unaccepted payloads cannot become the advertised version.
Do not claim the existing branch model already enforces that boundary. Repository-only catalog maintenance that preserves all plugin bytes does not
constitute a new plugin release. Native index generation is not promotion or an
acceptance gate.

After that prerequisite is resolved and the gate passes, retain an attempt record
and previous advertised version/source before publishing. Attach the retained
archive and checksum to a versioned GitHub Release at the nominated SHA, using
the maintainer identity. Never rebuild or replace existing published assets.
Advertise only the accepted version through the reviewed marketplace mechanism.
Download the asset and install from the published marketplace in an isolated
consumer environment; record:

- `published-byte-identity`: downloaded archive SHA-256 equals the accepted digest
  and the release resolves to the nominated commit.
- `marketplace-installation`: each affected native marketplace loads the same
  accepted target package, installs its intended version and passes relevant
  smoke scenarios. No unsupported target appears in its native listing.
- `recovery-recorded`: previous source/version and recovery steps are retained and
  verified; an initial release is stated explicitly when no predecessor exists.

The current repository intentionally has no generic promotion command. Once actual
publication and verification succeed, use `bin/sdlc-release record` and `finalize`
with the observed release report. Do not invent successful deployment receipts.
After an interruption, inspect existing tags, assets, marketplace references and
attempt records before retrying; never overwrite a different artifact.

## Recovery

Retain old immutable artifacts and source identities. Restore the previously
accepted marketplace reference with a reviewed change; never rewrite a release
or reuse its version for different bytes. Verify a clean install and document
consumer update/reinstall instructions, since cached installations are not changed
by a repository rollback. A fix to published plugin bytes uses a new version and
repeats acceptance. Repository-only regressions use an independently reviewed
revert followed by `bin/ci` and current-head evidence.
