---
type: regex
pattern: '^(?=[\s\S]*(?:"matcher"\s*:\s*\[|\bmatcher\b[^\n]{0,120}\b(?:array|list)\b|\b(?:array|list)\b[^\n]{0,120}\bmatcher\b|\bmatcher\b[^\n]{0,120}\bstring\b))(?=[\s\S]*(?:"matcher"\s*:\s*"[^"\n]*\b(?:Edit|Write)\b[^"\n]*"|["\x60]\^?\(?(?:Edit\|Write|Write\|Edit)\b|["\x60](?:Edit,\s?Write|Write,\s?Edit)["\x60]))'
flags: i
weight: 1
---
The fixture's `.claude/settings.json` has a `PostToolUse` hook group with `"matcher": ["Edit", "Write"]`. A hook `matcher` is a string (exact names separated by `|` or `,`, or a regular expression), not a JSON array, so this hook is invalid and will not fire as intended.

Script-graded (case-insensitive): the report shows the array (`"matcher": [`) or puts `matcher` and "array" or "list" on one line within 120 characters, and gives a string matcher: `"matcher": "<...Edit or Write...>"`, or a quoted or backticked `Edit|Write`, `Write|Edit` (optionally `^(`-prefixed), `Edit,Write` or `Write, Edit`.
