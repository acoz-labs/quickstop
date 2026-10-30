# Claudit: roman

**Intent:** A small Go library and CLI (`cmd/roman`) that converts integers 1..3999 to Roman numerals and back. Work is checked with `go test ./...`. There is no CI, no procedure docs and no release flow, so a person is most likely driving it interactively. Assumed from the repository; correct me if wrong.

## Grades

- **Correctness: A** (confidence: high). There is no configuration to break. `.claude/` holds only an internal `.cc-writes` directory.
- **Alignment: C** (confidence: medium). Nothing in the setup tells Claude how this project is built or checked, so it has to guess.
- **Coverage: C** (confidence: high). Two baseline items are missing, the instruction file and the pre-approved check command. The code-intelligence plugin is a third, minor gap.

## Top changes

3 changes are worth making. The project is tiny, so there is nothing else to recommend.

1. **Add a short CLAUDE.md** (Coverage, effort S)
   Problem: `CLAUDE.md`, `.claude/CLAUDE.md` and `AGENTS.md` don't exist, so nothing loads. Claude doesn't know the check command or the 1..3999 range.
   Why: A few lines on how to verify a change are enough for a project this size.
   Change:
   ```markdown
   # roman
   Go library plus CLI (`cmd/roman`) converting integers 1..3999 to Roman numerals and back.
   - Check: `go test ./...` (run after every change)
   - Run: `go run ./cmd/roman 1994 MMXXIV`
   ```
   Source: [Write effective instructions](https://code.claude.com/docs/en/memory)

2. **Pre-approve the test command** (Coverage, effort S)
   Problem: `.claude/settings.json` doesn't exist, so no allow rule covers `go test ./...` and every run prompts.
   Why: Claude can run its check without interrupting you.
   Change: create `.claude/settings.json`:
   ```json
   {"permissions": {"allow": ["Bash(go test ./...)"]}}
   ```
   Source: [Permission rule syntax](https://code.claude.com/docs/en/permissions)

3. **Install the Go code-intelligence plugin** (Coverage, effort S)
   Problem: `go.mod` marks this as a typed codebase, but no LSP plugin is enabled. Claude has no type-aware navigation or diagnostics.
   Why: It gives Claude go-to-definition and diagnostics after edits. This is a low-impact change for a codebase this small.
   Change: install `go-lsp` from the official marketplace. Check `/plugin` for the exact name.
   Source: [Code intelligence plugins](https://code.claude.com/docs/en/plugins/code-intelligence)

## Also worth knowing

- Once the test suite grows, a Stop hook that runs `go test ./...` would enforce the check. It isn't worth adding at this size.

---
Claude Code 2.1.314; catalog 2026-10-29.
Docs: the index was read live, and no new pages need assessing.
Scope: project only. User settings, managed settings, `~/.claude.json` and installed plugins were not inspected.
Read-only run: nothing was written.