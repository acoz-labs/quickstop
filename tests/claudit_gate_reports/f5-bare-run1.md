# Claudit: roman

**Intent:** A small Go library with a CLI (`cmd/roman`) that converts integers 1..3999 to Roman numerals and back. It has one package, `roman.go`, with tests in `roman_test.go`. The only check is `go test ./...`. There is no CI, no procedure docs and no release flow. A person drives it interactively. Assumed from the repository; correct me if wrong.

## Grades

- **Correctness: A** (confidence: high). There is nothing to get wrong: `.claude/` is empty and the scan found no defects.
- **Alignment: C** (confidence: medium). Nothing is configured, so nothing tells Claude how to check its work here. The project is small enough that very little is needed.
- **Coverage: D** (confidence: high). Three of the five baseline items are missing or unmet: instructions, a documented check, and a pre-approved check command. Secrets and enforcement don't apply, and there's no code-intelligence plugin.

## Top changes

3 changes are worth making.

1. **Add a short CLAUDE.md** (Coverage, effort S)
   Problem: No `CLAUDE.md`, `.claude/CLAUDE.md` or `AGENTS.md` exists, so nothing loads and Claude doesn't know how to verify a change. The README only shows how to run the CLI.
   Why: A one-line check command lets Claude confirm its edits against `roman_test.go` itself.
   Change:
   ```markdown
   # roman
   Go library plus CLI (`cmd/roman`). Valid range is 1..3999.
   Check: `go test ./...` (run it after every change).
   ```
   Source: [Write effective instructions](https://code.claude.com/docs/en/memory)

2. **Pre-approve the test command** (Coverage, effort S)
   Problem: `.claude/settings.json` doesn't exist, so no `permissions.allow` rule covers `go test ./...`. Every test run prompts.
   Why: Claude can run the check without interrupting you.
   Change: create `.claude/settings.json`:
   ```json
   {"permissions": {"allow": ["Bash(go test ./...)"]}}
   ```
   Source: [Permission rule syntax](https://code.claude.com/docs/en/permissions)

3. **Install the Go code-intelligence plugin** (Coverage, effort S)
   Problem: No code-intelligence plugin is enabled, though `go.mod` marks this as a typed codebase. Claude has no type-aware navigation or diagnostics.
   Why: It gives Claude jump-to-definition and compile errors without a full test run. The gain is modest in a codebase this small.
   Change: install `go-lsp` from the official marketplace. Check `/plugin` for the exact name.
   Source: [Code intelligence plugins](https://code.claude.com/docs/en/plugins/code-intelligence)

## Also worth knowing

- Not recommended, because the project is tiny: a Stop hook that runs the tests, subagents, skills and MCP servers.
- Run `/init` instead of writing the `CLAUDE.md` by hand if you want Claude to draft it. Keep what it writes short.

---
Claude Code 2.1.314; Claudit 4.0.1, catalog 2026-10-29.
Docs: index read live; no new pages since the catalog.
Scope: project only. User and managed settings, `~/.claude.json` and installed plugins were not inspected.
Read-only run: no changes were offered or made.