---
type: llm
weight: 1
---
The fixture's `.claude/settings.json` has `"Write(src/**)"` in `permissions.allow`. Claude Code checks file permissions against `Edit(...)` and `Read(...)` path rules only; a `Write(path)` rule is accepted but never matches, so this rule does nothing.

PASS only if the report (1) identifies the `Write(src/**)` rule (or "the Write(...) permission rule") as ineffective, never matching, or wrong, and (2) recommends replacing it with an `Edit(src/**)` rule (or otherwise expressing file-write permission with `Edit(...)`). Recommending removal of the rule because file writes are governed by `Edit` rules is also acceptable.

FAIL if the report does not mention the `Write(...)` rule, only calls it "too broad" or a security risk without saying it never matches, or names the problem without the `Edit(...)` fix.
