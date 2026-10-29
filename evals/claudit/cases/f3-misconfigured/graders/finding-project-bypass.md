---
type: llm
weight: 1
---
The fixture's committed project settings `.claude/settings.json` set `"permissions": {"defaultMode": "bypassPermissions"}`. Claude Code ignores `bypassPermissions` (and `auto`) as `defaultMode` from project or local settings; it takes effect only from user or managed settings, or `--permission-mode` for one session. A committed attempt to bypass every prompt for everyone who clones the repo is also a hazard.

PASS only if the report (1) identifies `permissions.defaultMode: "bypassPermissions"` in the project `.claude/settings.json` as a problem because it is ignored at project scope (saying it has no effect from the committed file), and (2) recommends removing it from the project file, optionally saying that anyone who really wants it should set it in their own user settings (`~/.claude/settings.json`), managed settings, or pass `--permission-mode bypassPermissions`.

FAIL if the report only calls bypass mode risky or insecure without saying the project-level setting is ignored, if it treats the setting as active, or if its only fix is moving it to `.claude/settings.local.json` (local scope is ignored too).
