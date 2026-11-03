---
type: tool_used
tool: Read
input_match: 'skills/writing-style/references/artifacts\.md'
min: 1
arm: both
weight: 1
---
The audit reads the workflow-artifacts reference from the installed plugin. Enforces `skills/writing-audit/SKILL.md:14` ("Read the reference for each surface before auditing it") with the table row at `:18`; the fixture's `docs/decision-notes.md` is a workflow artifact (`:36`). A pass also shows `${CLAUDE_PLUGIN_ROOT}` expanded to a readable path.
