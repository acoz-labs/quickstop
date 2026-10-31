---
type: tool_used
tool: Read
input_match: 'output-styles/writing-for-humans\.md'
min: 1
arm: both
weight: 1
---
The audit reads the output style file. Enforces `skills/writing-audit/SKILL.md:25`: when the style's rules are not already present, read `${CLAUDE_PLUGIN_ROOT}/output-styles/writing-for-humans.md`. Eval sessions run with the `default` style (their init record says so), so the rules are never already present here.
