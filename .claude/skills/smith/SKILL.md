---
name: smith
description: Create a plugin in the Quickstop marketplace from an assigned outcome.
disable-model-invocation: true
argument-hint: plugin-name
---

# Create a Quickstop plugin

Read `AGENTS.md`, `docs/repository.md` and `docs/plugin-development.md`.
Use the assigned issue and user requirements; ask only for missing decisions that
prevent implementation. Validate a lowercase kebab-case name and refuse to
replace an existing plugin directory.

Create only the components the outcome needs under `plugins/<name>/`. Register
its relative source, name and version in `.claude-plugin/marketplace.json` and
update the root README. Preserve the repository's MIT license and attribution;
an explicitly different license needs a deliberate recorded decision.

Use the current official plugin reference linked in the development guide when
introducing unfamiliar components. Hooks and MCP servers are supported when the
assigned feature needs them; document their effects and configuration. Do not
create unused directories, placeholder servers or copied documentation catalogs.

Implement usable instructions and meaningful checks, run `bin/ci`, and follow
the shared contributor PR and independent acceptance workflow. Report changed
capabilities, checks and remaining limitations. Scaffolding alone is not release.
