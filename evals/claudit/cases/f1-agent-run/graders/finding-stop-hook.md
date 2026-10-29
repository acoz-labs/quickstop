---
type: llm
weight: 1
---
The fixture's CLAUDE.md requires agents to run `bin/ci` before reporting a change as done, but nothing enforces it: there is no `.claude/settings.json` and no hooks.

PASS only if the report (1) identifies that nothing automatically runs the checks when the agent finishes (no Stop hook, or no hook at all, enforcing `bin/ci`), and (2) recommends adding a `Stop` hook in `.claude/settings.json` that runs `bin/ci` (or the lint and tests it wraps) and blocks or reports when it fails. Equivalent enforcement that runs the checks automatically at the end of a turn or task, such as a `SubagentStop`/`TaskCompleted` hook or a prompt/agent-type Stop hook that requires the checks, is acceptable. A `PostToolUse` hook that runs tests after edits is acceptable only if the report presents it as the way to enforce the checks before the agent finishes.

FAIL if the report only recommends "adding hooks" in general, only repeats the CLAUDE.md instruction, or suggests running CI manually or in GitHub Actions without a Claude Code hook.
