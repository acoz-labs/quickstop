---
type: regex
pattern: '^(?=[\s\S]*(?:"matcher"\s*:\s*\[|\bmatcher\b[^\n]{0,120}\b(?:array|list|strings?)\b|\b(?:array|list)\b[^\n]{0,120}\bmatcher\b))(?=[\s\S]*(?:"matcher"\s*:\s*"[^"\n]*\b(?:Edit|Write)\b[^"\n]*"|["\x60]\^?\(?(?:Edit\|Write|Write\|Edit)\b|["\x60](?:Edit,\s?Write|Write,\s?Edit)["\x60]))'
flags: i
weight: 1
---
The fixture's `.claude/settings.json` has a `PostToolUse` hook group with `"matcher": ["Edit", "Write"]`. A hook `matcher` is a string (exact names separated by `|` or `,`, or a regular expression), not a JSON array, so this hook is invalid and will not fire as intended.

Script-graded (case-insensitive). The diagnosis: the report shows the array (`"matcher": [`), or one line has `matcher` followed within 120 characters by "array", "list", "string" or "strings", or "array" or "list" followed within 120 characters by `matcher`. The fix: `"matcher": "<…Edit or Write…>"`, or a quote or backtick, then optionally `^(`, then `Edit|Write` or `Write|Edit`, or a quoted or backticked `Edit,Write`/`Write, Edit`. Both are needed.
