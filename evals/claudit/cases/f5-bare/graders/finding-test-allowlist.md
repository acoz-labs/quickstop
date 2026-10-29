---
type: llm
weight: 1
---
The fixture has Go tests but no `.claude/settings.json`, so every run of the test command prompts for permission.

PASS only if the report (1) identifies that there is no permissions allowlist for the test command, and (2) recommends adding a project `.claude/settings.json` with a `permissions.allow` rule covering it, such as `Bash(go test *)`, `Bash(go test:*)` or `Bash(go test ./...)` (optionally also `go vet`/`gofmt`/`go build`). Any equivalent allow rule that clearly covers `go test` is acceptable.

FAIL if the report only says "add a settings file" or "configure permissions" without an allow rule for the test command, or does not mention permissions at all.
