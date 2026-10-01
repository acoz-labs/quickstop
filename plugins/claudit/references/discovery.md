# Configuration discovery and effective state

The helper returns candidates and provenance, not an emulation of Claude Code's
entire resolver. Read current `core-config`/`ecosystem` evidence before interpreting
unknown fields or changing settings. Preserve unassessed areas in the report.

- User settings/instructions/rules/skills/agents and plugin registries follow
  `CLAUDE_CONFIG_DIR` (default `~/.claude`). MCP user/local state normally resides
  in `~/.claude.json`, or `<CLAUDE_CONFIG_DIR>/.claude.json` with an override. The
  helper emits only selected MCP metadata, never the full authentication file.
- Shared settings and project MCP use the session working directory. Current
  POSIX Git hosts normally place local settings at the main checkout root;
  legacy cwd-local files may also load. Ownership, home-directory repositories,
  Windows, SDK callers and session flags have exceptions: confirm live `/status`
  setting sources before claiming a complete effective merge.
- Managed files are candidates; server-managed settings, MDM/registry sources,
  inline `--settings`, `--setting-sources` and session/environment overrides may
  be unobservable. Managed policy outranks local configuration; lists and
  security-specific fields have specialized merge/deny semantics. Do not flatten
  all settings into one guessed dictionary or “fix” admin-managed content.
- Parent instructions apply outside Git too. Inspect `.claude/CLAUDE.md`,
  `CLAUDE.local.md`, `CLAUDE.md`, applicable `AGENTS.md` fallback behavior, nested
  rules and source `@imports`. Resolve imports relative to their source, follow
  current depth/trust rules, detect cycles, and label excluded/unreadable inputs.
  `claudeMdExcludes` and loading mode affect effective instructions. Descendants
  and path-filtered rules are conditional, not all startup context.
- Auto-memory candidates live under `<config>/projects/<encoded main project>/memory/`.
  Respect `CLAUDE_CODE_PROJECT_DIR_NAME` with `CLAUDE_CONFIG_DIR` and
  `autoMemoryDirectory` overrides. Verify `/memory` for the exact loaded path;
  trust, blockReadsOutsideWorkingDirectories, `autoMemoryEnabled`, managed or
  session overrides may prevent loading. There is no generic `.claude/MEMORY.md`
  project/global-memory convention. Do not read another project's memory.
- Plugin registry entries identify real install roots and installation scopes.
  Inspect default and manifest-declared components with their replace/add/merge
  semantics. Disabled/untrusted state is not proven merely by installation.
  Commands, agents, skills, hooks, MCP, LSP, workflows, output styles, themes,
  monitors, userConfig and Mods are current surfaces where declared; optional
  absence is valid. No marketplace provenance exempts validation.

Critical files are never dropped by the default 200-candidate budget. Remaining
files are ordered by relevance then path, not recency. The helper reports every
omitted candidate. Raise `--limit` for a focused follow-up, or explicitly report
partial coverage. It excludes dependency/build directories and does not follow
recursive symlink directories. A source import into an excluded area needs a
separate scoped read, not a blanket recursive scan.

Prefer read-only native `claude plugin validate --json <root>` for a
candidate when available. Use plugin details/cost observations only when already
installed and authorized; never load an untrusted plugin or launch its MCP/hooks
just to collect audit evidence. Distinguish native errors from warnings; optional metadata warnings are not
defects and strict-mode exit codes alone are not a scoring basis. A native
validation pass is schema evidence, not
proof of runtime correctness. Record host version and validation errors. If native
validation is unavailable, inspect the documented fields and report limitations.
