---
type: regex
pattern: '^(?=[\s\S]*\bWrite\()(?=[\s\S]*(?:\bEdit\((?:\.?/)?src/|(?:^|\n)(?=[^\n]*\b(?:[Rr]emove|[Dd]elete|[Dd]rop)\b)(?=[^\n]*\bWrite\()(?=[^\n]*\bEdit\b)))'
weight: 1
---
The fixture's `.claude/settings.json` has `"Write(src/**)"` in `permissions.allow`. Claude Code checks file permissions against `Edit(...)` and `Read(...)` path rules only; a `Write(path)` rule is accepted but never matches, so this rule does nothing.

Script-graded: the report names a `Write(` rule and gives the fix, an `Edit(src/...)` rule (also `Edit(./src/...)` or `Edit(/src/...)`), or one line that says to remove, delete or drop the `Write(` rule and names `Edit`.
