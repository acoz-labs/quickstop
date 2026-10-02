# Contributing

Follow [software delivery](docs/operations/sdlc.md).

Documentation: write, validate and publish; no mandatory delivery issue or plan.
Code: implement a bounded issue, test, open a contributor-authored PR and request
a different authorized maintainer through GitHub PR review requests. Resolve
findings in the PR and re-request review after revisions; obtain current-head
review before merge. Plans are optional.
Maintainers own planning and docs. A different authorized maintainer reviews,
accepts, merges, and delivers. Product-owner approval is not required for
ordinary design, findings, repaired acceptance, flake triage, review-bot
noise, or release inside the assigned task. The quality gate is independent
verification of the real artifact, not a rubber-stamp approval or a green CI
run alone.

PRs explain behavior, validation, documentation impact and applicable release or
rollback details. Use `Refs #N` when the issue stays open through release and
`Closes #N` only when merge completes the documented delivery profile.
