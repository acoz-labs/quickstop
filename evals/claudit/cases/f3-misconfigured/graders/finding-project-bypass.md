---
type: regex
pattern: '^(?=[\s\S]*(?:(?:defaultMode|bypassPermissions)[^\n]{0,300}(?:\bignor\w*|\bno effect\b|\bnot (?:appl\w*|honou?r\w*|read|take effect|used)\b|n[\x27’]t (?:appl\w*|take effect|honou?r\w*|work\w*|used)\b)|(?:\bignor\w*|\bno effect\b|\bnot (?:appl\w*|honou?r\w*|read|take effect|used)\b|n[\x27’]t (?:appl\w*|take effect|honou?r\w*|work\w*|used)\b)[^\n]{0,300}(?:defaultMode|bypassPermissions)))(?=[\s\S]*(?:(?:\bremov\w*|\bdelet\w*|\bdrop\w*|\btake (?:it )?out\b)[^\n]{0,200}(?:defaultMode|bypassPermissions)|(?:defaultMode|bypassPermissions)[^\n]{0,200}(?:\bremov\w*|\bdelet\w*|\bdrop\w*|\btake (?:it )?out\b)|\n[ \t]*-[ \t]*"defaultMode"))'
flags: i
weight: 1
---
The fixture's committed project settings `.claude/settings.json` set `"permissions": {"defaultMode": "bypassPermissions"}`. Claude Code ignores `bypassPermissions` (and `auto`) as `defaultMode` from project or local settings; it takes effect only from user or managed settings, or `--permission-mode` for one session.

Script-graded (case-insensitive): one line names `defaultMode` or `bypassPermissions` and says it is ignored, has no effect, isn't applied, honoured, read or used, or doesn't take effect or work (within 200 characters, either order). And one line says to remove, delete, drop or take out `defaultMode` or `bypassPermissions` (within 120 characters, either order), or a diff line removes `"defaultMode"`.
