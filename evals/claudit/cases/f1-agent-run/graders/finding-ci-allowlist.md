---
type: llm
weight: 1
---
The fixture is an agent-run Python repo whose CLAUDE.md tells agents to run `bin/ci` before reporting a change as done, but it has no `.claude/settings.json` and so no permission rule for that command; every run of the CI script prompts for approval.

PASS only if the report (1) identifies that there is no permissions allowlist (no `permissions.allow` rule, or no `.claude/settings.json` at all) covering the CI script `bin/ci`, and (2) recommends adding an allow rule for it in project settings, for example `"permissions": {"allow": ["Bash(bin/ci)"]}` or `Bash(bin/ci *)` / `Bash(bin/ci:*)` / `Bash(./bin/ci)` in `.claude/settings.json`. Any equivalent allow rule that clearly covers `bin/ci` is acceptable.

FAIL if the report only says to "configure permissions" or "add a settings file" without tying it to allowing the CI command, if it names the problem without a fix, or if it does not mention the missing allowlist at all.
