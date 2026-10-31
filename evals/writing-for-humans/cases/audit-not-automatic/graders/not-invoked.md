---
type: tool_used
tool: Skill
input_match: 'writing-audit'
min: 0
max: 0
arm: both
weight: 1
---
Claude does not call the writing-audit skill when asked for an audit in plain words. Enforces the user-only contract: `skills/writing-audit/SKILL.md:4` (`disable-model-invocation: true`), the kit README ("It runs only when you type `/writing-for-humans:writing-audit`") and `docs/acceptance/writing-for-humans.md:32` (a recorded automatic call is a failure). A refused or failed call still counts.
