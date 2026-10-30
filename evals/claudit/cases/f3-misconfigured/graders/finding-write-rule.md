---
type: regex
pattern: '^(?=[\s\S]*\bWrite\()(?=[\s\S]*(?:\bEdit\((?:\.?/|\*\*/)?src/|(?:^|\n)(?=[^\n]*\bWrite\()(?=[^\n]*(?:\b[Rr]emove|\b[Dd]elete|\b[Dd]rop|\b[Uu]se|\b[Rr]eplace)\b)(?=[^\n]*\bEdit\x60?(?:\s+(?:path\s+)?(?:rules?|permissions?)\b|\())))'
weight: 1
---
The fixture's `.claude/settings.json` has `"Write(src/**)"` in `permissions.allow`. Claude Code checks file permissions against `Edit(...)` and `Read(...)` path rules only; a `Write(path)` rule is accepted but never matches, so this rule does nothing.

Script-graded (case-sensitive): the report names a `Write(` rule and gives the fix. The fix is either an `Edit(src/`, `Edit(./src/`, `Edit(/src/` or `Edit(**/src/` rule, or one line that names `Write(`, says remove, delete, drop, use or replace (also capitalised), and names `Edit` followed by `(` or by "rule(s)", "path rule(s)" or "permission(s)". The grader checks the rule and the fix, not the explanation.
