# Quickstop repository

Quickstop is a home for agent plugins and practical, read-and-adapt workflows.
[Shipshape](../workflows/shipshape/README.md) is its first workflow. Claudit 3.0.0
is advertised for Claude Code. Writing for Humans is a Claude Code-only kit conversion
whose publication state is recorded in the generated catalog. `catalog.json`
declares supported targets; native package manifests own versions. Generated
indexes and package layouts follow [the marketplace contract](marketplace.md).
Plugin creation and review use the shared SDLC and development guide.

`AGENTS.md` and `docs/operations/sdlc.md` define delivery authority and roles.
`CLAUDE.md` imports this guidance for Claude Code. Use conventional commit titles;
retain honest author/committer attribution without generated-tool trailers.
Preserve existing MIT notices. Personal identities and machine setup stay outside
this repository.

## Local verification

Requires Git, Bash and Python **3.11.15**, pinned in `.python-version` (standard
library only; no downloaded Python dependencies). Put that interpreter first in
PATH before running verification; `bin/ci` rejects a different version. With mise:

```sh
export PATH="$(mise where python@3.11.15)/bin:$PATH"
bin/ci
bin/check-marketplace --base origin/main
```

Without mise, install the pinned Python and run the same commands directly.
The initial compatibility run also passed on Python 3.9.6; release evidence uses
the pinned runtime, not the system default.

`bin/ci` runs managed conformity, optional-plan validation, catalog/adapter
checks and regression tests. `--base` additionally rejects changed plugin bytes
without a strictly higher stable version. Supply the actual pre-change commit;
an unavailable base is an error, never a reason to skip validation. All distributed
files, including README changes, count as bytes. Generated listings derive
versions from the native manifests; separate target packages can release independently. Regenerate indexes with
`bin/check-marketplace --write` after changing catalog or manifest metadata.

For a Claude target, use the host's `claude plugin validate .` and
`claude plugin validate ./plugins/claudit` when available. Use the appropriate
native discovery/validation for other declared harnesses. These supplement local
checks and do not prove runtime behavior. Acceptance scenarios belong
in [delivery](delivery.md). Inspect current host documentation for unfamiliar
components instead of treating the lightweight local validator as a complete
upstream schema implementation.

`scripts/check-plugin-versions.sh BASE` remains a compatibility wrapper. Repository
push hooks and Claude shell-match hooks have been retired; clean-checkout evidence
is the verification gate. Existing clones with the old installed pre-push hook
may remove that specific hook after inspecting it; do not replace personal hooks.

## Layout and tracking

- `catalog.json`: ordered plugin catalog and explicit supported targets.
- `plugins/`: self-contained packages; Claudit retains `plugins/claudit/`.
- `workflows/`: ordinary Markdown guides with a browsable entry index; no native installable packages.
- `.claude-plugin/` and `.agents/plugins/`: generated native marketplace indexes.
- `docs/catalog.md`: generated support/version table.
- `docs/pi-packages.md`: generated individual Pi install commands.
- `bin/`, `tests/`: portable delivery tools and real marketplace regressions.
- `docs/`: development, delivery and maintained investigation findings.
- `.sdlc/`: managed standard identity and repository-specific artifact profile.

[Project 40](https://github.com/orgs/acoz-labs/projects/40) uses Inbox, Ready,
In Progress, Review, Release, Done, Blocked and Parked. Plans are proportional;
future product choices remain to be made with the owner. Actions are opt-in on
trusted self-hosted runners. Local independent proof is the default.
