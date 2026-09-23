# Contributing

Follow [software delivery](docs/operations/sdlc.md).

Documentation: write, validate and publish; no mandatory delivery issue or plan.
Code: implement a bounded issue, test, open a contributor-authored PR and request
a different authorized maintainer through GitHub PR review requests. Resolve
findings in the PR and re-request review after revisions; obtain current-head
review before merge. Plans are optional.
Maintainers own planning and docs, resolve findings with contributors, perform
acceptance and deliver without routine owner approval.

PRs explain behavior, validation, documentation impact and applicable release or
rollback details. Use `Refs #N` when the issue stays open through release and
`Closes #N` only when merge completes the documented delivery profile.

Choose the contribution guide for the thing you are making:

- [Plugins](docs/plugin-development.md): explicitly supported native capabilities.
- [Workflows](docs/workflows.md): practical documentation people and agents adapt.

Agent-authority and workflow-policy changes use independent review even when
written in Markdown. Keep examples fictional and personal/private material out
of this public repository.
