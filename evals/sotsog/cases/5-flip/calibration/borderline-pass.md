# Signed releases with build provenance: adapt for Lanternhall

We'll sign releases and publish build provenance from CI, before 1 March 2027. The brief below hands the work on. Coastline will require both from that date or stop deploying Lanternhall.

Date 2026-11-12. Decided by the maintainers. Sources: the post and the library.

## The idea in brief

CI signs each release file and publishes a signed record of how it was built.

## What the evidence shows

Sound when consumers verify.

- **Who gains:** the author sells nothing.
- **Measured against:** a story, not numbers.
- **What's missing:** upkeep cost.
- **Whose conditions:** a library with millions of downloads.
- **Independent support:** signing-adoption-report.md found small projects' signatures go unverified. The critique in signing-theatre.md says signing nobody verifies is theatre.

## How it compares with what we do

| Principle | How they do it | How we do it | Fit |
|---|---|---|---|
| Sign artifacts | in CI | unsigned | gap |
| Provenance | published | none | gap |
| Build in CI | from a tag | local `bin/release` | gap |

## Why this decision

Coastline's new policy requires signed releases with provenance it verifies from 1 March 2027, or it stops deploying us. Without that, publishing `SHA256SUMS` over HTTPS (checksums-over-https.md) would do: it catches swapped downloads, though it can't prove who built a file.

## Revisit when

- Coastline drops the requirement.

## Implementation brief

Goal: signed releases with provenance from CI before March 2027. Out of scope: commit signing.

1. Add `.github/workflows/release.yml`, run on `v*` tags, building the tarball and wheel.
2. Sign both with `cosign sign-blob` in keyless mode, add provenance with `actions/attest-build-provenance`, and attach both, with `SHA256SUMS`, to the release page.
3. Cut `bin/release` down to compiling `changes/`, committing and tagging; the build moves to the workflow.
4. Add the verify commands (`cosign verify-blob`, `gh attestation verify`) to docs/releases.md.

Done when a test tag's release verifies with both commands and Coastline confirms. It worked if the March 2027 release deploys at Coastline without an exception. Roll back by removing the workflow.

## What we're not taking, and why

Nothing important; we keep `SHA256SUMS` too.

## Sources

- Carvalho post (link.md), read 2026-11-12.
- signing-adoption-report.md, read 2026-11-12.
- signing-theatre.md, read 2026-11-12.
- checksums-over-https.md, read 2026-11-12.
