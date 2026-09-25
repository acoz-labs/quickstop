# Repository instructions

Follow `docs/operations/sdlc.md` for the shared delivery contract and
`docs/operations/repo-standard.md` for configuration and conformity.

- Maintainers own issues, planning, documentation, review, acceptance and release.
- Contributors author code and code PRs. Another authorized maintainer reviews.
- Resolve implementation, design and acceptance findings internally to the spec.
  Escalate only a genuine deadlock requiring owner input; no routine owner gates.
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
