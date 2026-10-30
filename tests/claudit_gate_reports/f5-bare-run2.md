# Claudit: roman

**Intent:** A small Go library (`roman.go`, with tests) and a CLI (`cmd/roman`) that convert integers 1..3999 to Roman numerals and back. Work is checked with `go test ./...`. There is no CI, procedure docs or release flow, so a person is presumably driving it, with Claude helping. Assumed from the repository; correct me if wrong.

## Grades

- **Correctness: A** (confidence: high). There is no Claude Code configuration, so nothing in it can be broken.
- **Alignment: C** (confidence: medium). Nothing tells Claude how the project is checked or run, so the setup doesn't yet serve the intent.
- **Coverage: D** (confidence: high). Three of the five baseline items are missing or not met: instructions, a documented check and a check allowlist. A code-intelligence plugin is also absent.

## Top changes

3 changes are worth making, and no more: the project is tiny and has no secrets, CI, hooks or skills that would justify further setup.

1. **Add a short CLAUDE.md** (Coverage, effort S)
   Problem: No `CLAUDE.md`, `.claude/CLAUDE.md` or `AGENTS.md` exists, so no instructions load. Claude has to guess the check command, and the baseline "check" item is unmet.
   Why: Claude can verify its own edits and use the CLI correctly.
   Change: Create `CLAUDE.md` (or run `/init` and trim the result):
   ```markdown
   # roman
   - Check: `go test ./...` (run after every change to roman.go)
   - Run the CLI: `go run ./cmd/roman 1994 MMXXIV`
   - Valid range is 1..3999; reject anything outside it.
   ```
   Source: [Write effective instructions](https://code.claude.com/docs/en/memory)

2. **Pre-approve the test command** (Coverage, effort S)
   Problem: `.claude/settings.json` doesn't exist, so no allow rule covers `go test ./...` and each run prompts.
   Why: The check runs without interruption, so Claude can run it after every edit.
   Change: Create `.claude/settings.json`:
   ```json
   {"permissions": {"allow": ["Bash(go test ./...)"]}}
   ```
   Source: [Permission rule syntax](https://code.claude.com/docs/en/permissions)

3. **Install the Go code-intelligence plugin** (Coverage, effort S)
   Problem: `go.mod` marks a typed codebase, but no code-intelligence plugin is enabled. Claude has no type-aware navigation or diagnostics.
   Why: This gives Claude accurate definitions and errors in `roman.go` and `cmd/roman`. It is optional at this size.
   Change: Open `/plugin` and install the Go language-server plugin (`go-lsp`) from the official marketplace. Check the exact name in `/plugin`.
   Source: [Code intelligence plugins](https://code.claude.com/docs/en/plugins/code-intelligence)

## Also worth knowing

- Once `CLAUDE.md` grows, `/doctor prompt-audit` can check it for bloat. It isn't needed yet.

---
Claude Code 2.1.314; catalog 2026-10-29.
Docs: index read live; no pages needed beyond the catalog citations.
New in Claude Code, not yet assessed: none.
Scope: project only; user settings, managed settings, `~/.claude.json` and installed plugins not visible. Read-only run, so nothing was written.