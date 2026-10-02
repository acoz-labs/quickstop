# Repository instructions

Follow `docs/operations/sdlc.md` for the shared delivery contract and
`docs/operations/repo-standard.md` for configuration and conformity.

- Agents acting as maintainers or contributors own implementation, independent
  review, acceptance, merge, release verification and receipts, and Project
  board Status moves backed by evidence.
- Maintainers own issues, planning, documentation, review, acceptance and release.
- Contributors author code and code PRs. Another authorized maintainer reviews.
- Do not require product-owner approval for normal design, review findings,
  failed-then-fixed acceptance, flake triage, automated review-bot noise, or
  happy-path release inside an assigned delivery task.
- Escalate only when agents cannot reasonably sign off: an ambiguous product
  preference no experiment settles; missing access, secrets, or capability;
  money or billing; irreversible or high-blast operations (shared force-push,
  production data migration, allowlist or security broadening, deleting others'
  work); or a genuine deadlock after remedies. Report the blocker, evidence,
  attempts, and a recommendation.
- Verification is independent of the author, proves the real artifact, and
  scales to blast radius. CI success alone is not a merge verdict. Separate
  GitHub accounts isolate authorship and receipts; they are not the quality gate.
  Optional Cursor pstack skills may structure that proof where already installed.
- Resolve implementation, design, and acceptance findings internally to the spec.
- Documentation-only work follows write, validate, publish. Code uses a bounded
  issue and PR. Plans are optional and proportional, not a Ready prerequisite.
- SDLC improvements update the template and every active repository in one
  maintenance operation, without pilot stages or deferred adoption waves.
- Use isolated worktrees and clean up completed task workspaces and temporary
  resources under the SDLC workspace-cleanup policy. Preserve active work and
  required evidence; record the reason, responsible role and cleanup trigger for
  anything retained.
- Preserve exact-candidate checks, independent acceptance and release evidence.
- Preserve task stopping points, product boundaries, secrets and honest authorship.
- Keep personal identities and machine/account configuration outside product repos.
- Use existing application patterns. Test meaningful behavior and update durable
  docs. Do not replace repository-specific checks with conformity checks.

## Validation

Run `bin/ci` (or `bin/container bin/ci` where supported). Run `bin/sdlc check`
when changing managed standards. Repository-specific instructions and commands
live in `docs/repository.md` and must not reintroduce superseded workflow gates.
