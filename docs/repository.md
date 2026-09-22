# Quickstop repository

Quickstop is a public Claude Code plugin marketplace maintained by acoz-labs.
Its only shipped plugin is Claudit 3.0.0. Keep the marketplace at
`.claude-plugin/marketplace.json` and distributable files under `plugins/<name>/`.
Repository authoring tools in `.claude/` are not plugin payloads.

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

`bin/ci` runs managed conformity, optional-plan validation, marketplace structure
checks and regression tests. `--base` additionally rejects changed plugin bytes
without a strictly higher stable version. Supply the actual pre-change commit;
an unavailable base is an error, never a reason to skip validation. All distributed
files, including README changes, count as bytes. Marketplace and plugin versions
must agree; update displayed README versions when publishing.

Use the host's `claude plugin validate .` and
`claude plugin validate ./plugins/claudit` when available. These supplement local
checks and do not prove the audit's runtime behavior. Acceptance scenarios belong
in [delivery](delivery.md). Inspect current host documentation for unfamiliar
components instead of treating the lightweight local validator as a complete
upstream schema implementation.

`scripts/check-plugin-versions.sh BASE` remains a compatibility wrapper. Repository
push hooks and Claude shell-match hooks have been retired; clean-checkout evidence
is the verification gate. Existing clones with the old installed pre-push hook
may remove that specific hook after inspecting it; do not replace personal hooks.

## Layout and tracking

- `plugins/claudit/`: consumer skills, agents and their shared references.
- `.claude/skills/`: concise repository-only Smith and Hone shortcuts.
- `bin/`, `tests/`: portable delivery tools and real marketplace regressions.
- `docs/`: development, delivery and maintained investigation findings.
- `.sdlc/`: managed standard identity and repository-specific artifact profile.

[Project 40](https://github.com/orgs/acoz-labs/projects/40) uses Inbox, Ready,
In Progress, Review, Release, Done, Blocked and Parked. Plans are proportional;
future product choices remain to be made with the owner. Actions are opt-in on
trusted self-hosted runners. Local independent proof is the default.
