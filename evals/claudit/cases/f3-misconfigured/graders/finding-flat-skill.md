---
type: regex
pattern: '^(?=[\s\S]*release-notes\.md)(?=[\s\S]*(?:release-notes/SKILL\.md|release-notes/[^\n]{0,80}SKILL\.md|release-notes\x60?\s+(?:directory|folder)[^\n]{0,80}SKILL\.md|SKILL\.md[^\n]{0,40}\b(?:in|inside|under|into)\b[^\n]{0,40}release-notes/|\.claude/commands/release-notes\.md))'
weight: 1
---
The fixture has a skill file at `.claude/skills/release-notes.md`. Project skills are discovered as `.claude/skills/<skill-name>/SKILL.md`, so this flat file is not loaded as a skill and `/release-notes` is not available, even though CLAUDE.md tells Claude to use it.

Script-graded (case-sensitive): the report names `release-notes.md` and gives the move, as `release-notes/SKILL.md` (also split, such as "`.claude/skills/release-notes/` as `SKILL.md`", "a `release-notes` directory with a `SKILL.md`" or "`SKILL.md` inside `.claude/skills/release-notes/`") or as `.claude/commands/release-notes.md`, where a single-file command works. A lowercase `skill.md` doesn't count.
