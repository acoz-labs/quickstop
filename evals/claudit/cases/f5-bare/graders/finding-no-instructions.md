---
type: llm
weight: 1
---
The fixture is a small Go module (`roman.go`, `roman_test.go`, `cmd/roman/main.go`) with no Claude Code configuration at all: no `CLAUDE.md`, no `AGENTS.md`, no `.claude/` directory. Nothing records how to build or test it (the README shows only `go run ./cmd/roman`).

PASS only if the report (1) identifies that the project has no project instructions (no `CLAUDE.md`) recording how to build and test it, and (2) recommends adding a concise `CLAUDE.md` (for example by running `/init`) that includes the test command `go test ./...` (and optionally `go vet ./...`, `gofmt`, the CLI entry point, conventions). An `AGENTS.md` imported or read by Claude Code is also acceptable if the report includes the test command.

FAIL if the report only says "add documentation", does not mention a CLAUDE.md (or equivalent project instructions), or recommends one without saying it should record the test command.
