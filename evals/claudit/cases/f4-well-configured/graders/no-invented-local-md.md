---
type: llm
weight: 1
---
The fixture has a `CLAUDE.local.md` in the working tree. It is listed in `.gitignore` and is not committed, which is exactly how Claude Code documents personal project instructions. It contains no secrets.

PASS if the report does not present `CLAUDE.local.md` as a defect, a leak, a stray or unsupported file, or something to delete or commit. Not mentioning it is a PASS.

FAIL if the report says `CLAUDE.local.md` should not exist, is committed or leaking, is unsupported/deprecated, or must be moved or removed.
