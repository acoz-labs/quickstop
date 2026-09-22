# Quickstop

A Claude Code plugin marketplace. Home of **claudit** — audit and optimize your Claude Code configuration — maintained by [acoz-labs](https://github.com/acoz-labs).

## Plugins

| Plugin | Problem solved |
|---|---|
| [claudit](plugins/claudit) | Audit and optimise your Claude Code config. Caches current Claude Code ecosystem knowledge for any subsequent agent task. |

## Install

Add quickstop as a plugin marketplace, then install claudit:

```bash
/plugin marketplace add acoz-labs/quickstop
/plugin install claudit@quickstop
```

Or install from a local clone:

```bash
git clone https://github.com/acoz-labs/quickstop.git
claude --plugin-dir /path/to/quickstop/plugins/claudit
```

## Claudit (v3.0.0)

Audit and optimize your Claude Code configuration. Caches current Claude Code ecosystem knowledge so any subsequent agent task — building a skill, configuring an MCP, authoring CLAUDE.md, debugging hooks — can read it via `/claudit:knowledge` instead of re-fetching docs.

- Recursive CLAUDE.md discovery: root, subdirectory, `.claude/rules/`, `CLAUDE.local.md`, and `@import` references
- Automatic scope detection — comprehensive audit inside a git repo, global-only outside
- Research-first: subagents fetch official Anthropic docs before analysis; over-engineering detection is the highest-weighted scoring category
- Decision memory annotates recommendations with past context (team-shared, committable)
- Optional PR delivery with educational inline comments
- Knowledge cache at `~/.cache/claudit/` with version-based + 7-day TTL invalidation, exposed to any agent task via `/claudit:knowledge [domain|all]`

**Commands:** `/claudit`, `/claudit:knowledge`, `/claudit:refresh`, `/claudit:status`

## Using Claudit's Knowledge Cache

Claudit's knowledge cache is general-purpose. Once it's been populated (any `/claudit` or `/claudit:refresh` invocation does this), any agent task that needs current Claude Code ecosystem knowledge can read it via `/claudit:knowledge` instead of re-fetching docs.

| Domain | Covers |
|---|---|
| `ecosystem` | MCP servers, plugins, hooks, skills, sub-agents |
| `core-config` | Settings, permissions, CLAUDE.md, memory system |
| `optimization` | Performance patterns, over-engineering detection |

In a skill or agent prompt, invoke `/claudit:knowledge ecosystem` (or whichever domain you need) and use the output as expert context. The skill checks freshness and auto-refreshes stale domains transparently. If claudit is not installed, fall back to your own research.

```
=== CLAUDIT KNOWLEDGE: ecosystem ===
[cached research content]
=== END CLAUDIT KNOWLEDGE ===

Knowledge source: cache (fresh, fetched 2026-03-22) | Domains: ecosystem
```

Manual refresh: `/claudit:refresh [domain|all]`. Status: `/claudit:status`.

## Development

Start with [repository guidance](docs/repository.md) and the
[shared SDLC](docs/operations/sdlc.md). Run `bin/ci` for local verification.
Plugin creation and review follow the standard issue, contributor PR and
independent maintainer review workflow. Plugin-specific conventions and the
review checklist live in the development guide.

- [Plugin development](docs/plugin-development.md)
- [Artifact delivery and recovery](docs/delivery.md)
- [Onboarding investigation](docs/investigation.md)
- [Project board](https://github.com/orgs/acoz-labs/projects/40)

The public repository moved from `acostanzo/quickstop` to `acoz-labs/quickstop`.
The marketplace name remains `quickstop`, so `claudit@quickstop` is unchanged.
Existing consumers should update their marketplace source to the new owner;
GitHub redirects preserve the previous repository URL. Claudit's existing author
metadata is retained as historical attribution in the unchanged 3.0.0 payload.

## License

MIT
