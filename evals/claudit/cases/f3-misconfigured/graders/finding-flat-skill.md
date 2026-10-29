---
type: llm
weight: 1
---
The fixture has a skill file at `.claude/skills/release-notes.md`. Project skills are discovered as `.claude/skills/<skill-name>/SKILL.md`, so this flat file is not loaded as a skill and `/release-notes` is not available, even though CLAUDE.md tells Claude to use it.

PASS only if the report (1) identifies that `.claude/skills/release-notes.md` is in the wrong layout and will not load as a skill, and (2) recommends moving it to `.claude/skills/release-notes/SKILL.md`. Moving it to `.claude/commands/release-notes.md` (where a single-file command does work) is also acceptable.

FAIL if the report does not mention the skill's layout, only critiques the skill's content or description, or names the problem without the move.
