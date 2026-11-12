# Recommendation: adopt signed releases with build provenance

The Coastline Library Consortium, our only outside deployer, will require signed releases with published build provenance from 1 March 2027 and will verify both on every deploy; without them it stops deploying Lanternhall. So we should sign releases and publish provenance, built in CI, before that date.

## Without that requirement

The evidence alone points to waiting. signing-adoption-report.md found almost nobody verifies signatures for projects with few consumers, and signing-theatre.md argues that signing nobody verifies adds upkeep and protects no one; publishing `SHA256SUMS` over HTTPS, as checksums-over-https.md recommends and as we already do, would be enough. Coastline's policy is what changes the answer: it is the consumer who verifies.

## Plan

Goal: every release from March 2027 is built in CI from its tag, signed, and published with provenance Coastline can verify. Out of scope: commit signing and the network's own deploys.

1. Add `.github/workflows/release.yml`, run on `v*` tags, building the tarball and wheel as `bin/release` does now.
2. Sign both files in that workflow with keyless signing, and publish a signed provenance statement with them on the release page, next to `SHA256SUMS`.
3. Change `bin/release` to compile `changes/`, commit and tag only.
4. Document the one verify command in docs/releases.md.
5. Cut a test release and ask Coastline's IT team to verify it.

Done when Coastline confirms the test release verifies. It worked if the March 2027 release deploys at Coastline without an exception. Roll back by removing the workflow and restoring the build in `bin/release`.

Sources read 2026-11-12: link.md, signing-adoption-report.md, provenance-at-ridgeway.md, signing-theatre.md, checksums-over-https.md.
