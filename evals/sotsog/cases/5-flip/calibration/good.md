# Signed releases with build provenance: adopt for Lanternhall

We'll sign every release and publish how it was built, with releases built in CI from their tag, before 1 March 2027. The implementation brief below is ready to hand on. From that date the Coastline Library Consortium requires signed releases with provenance it verifies, or it stops deploying Lanternhall.

Date 2026-11-12. Decided by the maintainers. Sources read: Inês Carvalho's post and five library pages.

## The idea in brief

Each release file is signed by the CI job, with a short-lived certificate tied to the repository ("keyless signing"), and the signature is recorded in a public log. Alongside it, CI publishes "build provenance": a signed statement of which commit and workflow built the file. Users verify both before installing.

## What the evidence shows

Sound, with a caveat: it only protects consumers who verify.

- **Who gains:** Inês Carvalho maintains a free library and sells nothing; reputation at most.
- **Measured against:** a before-and-after story (a tampered mirror copy), not measured; two companies and three packagers now verify.
- **What's missing:** upkeep cost; projects with few consumers.
- **Whose conditions:** a library with about 2 million downloads a month, far more consumers than our two deployers.
- **Independent support:** the Open Supply Chain Observatory found almost nobody verifies signatures for packages with fewer than about 50 consumers. Ridgeway Energy's notes: three days to set up, a day a quarter to keep working, justified because their security team verifies every deploy. Hannah Osei's critique ("signing theatre") says signing without anyone verifying adds upkeep and protects nobody.

On evidence alone, our answer would be "not now": one outside deployer, and nobody verifying. The user's answers change that.

## How it compares with what we do

| Principle | How they do it | How we do it | Fit |
|---|---|---|---|
| Sign every artifact | keyless signing in CI | unsigned; `SHA256SUMS` only (docs/releases.md) | gap |
| Publish build provenance | signed statement per file | none | gap |
| Build only in CI from a tag | CI builds tagged commits | a maintainer runs `bin/release` locally | gap |
| Tell users how to verify | one command in install docs | Coastline checks `SHA256SUMS` | partly |

Nothing we rely on is removed; `SHA256SUMS` stays.

## Why this decision

Coastline's procurement policy requires signed releases with provenance from 1 March 2027, verified on every deploy, and Coastline is our only outside deployer. That makes signing pay off in exactly the way the Observatory describes: a consumer with a policy who verifies. Cost: a few days of setup and about a day a quarter, within our time; the tools are free. The strongest case against: Hannah Osei is right that signing for nobody is theatre, and checksums over HTTPS (Release Craft's alternative) would be enough if Coastline didn't require more. They do.

## Revisit when

- Coastline drops the requirement or stops deploying Lanternhall: keep signing only if the upkeep stays small.
- Roll back to unsigned releases only if signing blocks a release and Coastline agrees to a manual exception.

## Implementation brief

**Goal.** Every Lanternhall release from March 2027 is built in CI from its tag, signed, and published with build provenance Coastline can verify.

**In scope:** a release workflow in CI, keyless signing, provenance, verification docs. **Out of scope:** signing commits, changes to how the network's IT team deploys.

**Changes, in order:**

1. Add `.github/workflows/release.yml`, triggered by a `v*` tag, which builds the tarball and wheel the way `bin/release` does today.
2. In that workflow, sign both files with keyless signing and record the signatures in the public transparency log.
3. Generate and sign a provenance statement for both files in the same workflow, and attach files, signatures, provenance and `SHA256SUMS` to the release page.
4. Change `bin/release` to only compile `changes/`, commit and tag; the build moves to CI.
5. Update docs/releases.md with the new steps and the one command to verify a release.
6. Cut a test release and have Coastline's IT team verify it.

**Acceptance criteria:** a tagged test release in CI produces signed files and provenance; the documented command verifies them; Coastline confirms its verification passes.

**How to tell it worked:** Coastline verifies the March 2027 release without a manual exception, and the next three releases ship on schedule.

**Verify and roll back:** run the verify command on the test release. To roll back, delete the release workflow and restore the build step in `bin/release`.

**Open risks:** the CI provider's signing setup may change and need upkeep.

## What we're not taking, and why

Nothing left out: we take all four principles. `SHA256SUMS` stays for anyone who doesn't verify signatures.

## Sources

- Inês Carvalho, "Sign your releases and publish how they were built" (link.md), read 2026-11-12. Wrenfold maintainer; story, not measured.
- Open Supply Chain Observatory, "Who verifies signatures? Release signing in 2026" (signing-adoption-report.md), read 2026-11-12. Independent.
- Felix Braun, "Adding build provenance to an internal service" (provenance-at-ridgeway.md), read 2026-11-12. Measured setup and upkeep.
- Hannah Osei, "Signing theatre" (signing-theatre.md), read 2026-11-12. Critique.
- Release Craft, "Checksums are enough for most small projects" (checksums-over-https.md), read 2026-11-12. Competing approach.
