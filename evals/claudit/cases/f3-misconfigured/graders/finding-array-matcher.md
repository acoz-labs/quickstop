---
type: llm
weight: 1
---
The fixture's `.claude/settings.json` has a `PostToolUse` hook group with `"matcher": ["Edit", "Write"]`. A hook `matcher` is a string (exact names separated by `|` or `,`, or a regular expression), not a JSON array, so this hook is invalid and will not fire as intended.

PASS only if the report (1) identifies the array-valued `matcher` on the PostToolUse lint hook as invalid or not working, and (2) recommends a string matcher such as `"Edit|Write"` (or `"Edit,Write"`, or an equivalent regex string).

FAIL if the report does not mention the matcher's type, only critiques the hook command, or names the problem without the string fix.
