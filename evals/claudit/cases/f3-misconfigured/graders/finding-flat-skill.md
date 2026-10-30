---
type: regex
pattern: '^(?=[\s\S]*release-notes\.md)(?=[\s\S]*(?:release-notes/SKILL\.md|release-notes/[^\n]{0,80}SKILL\.md|release-notes\x60?\s+(?:directory|folder|dir)\b[^\n]{0,80}SKILL\.md|SKILL\.md[^\n]{0,40}\b(?:in|inside|under|into)\b[^\n]{0,40}release-notes(?:/|\x60?\s+(?:directory|folder|dir)\b)|\.claude/commands/release-notes\.md))'
weight: 1
---
The fixture has a skill file at `.claude/skills/release-notes.md`. Project skills are discovered as `.claude/skills/<skill-name>/SKILL.md`, so this flat file is not loaded as a skill and `/release-notes` is not available, even though CLAUDE.md tells Claude to use it.

Script-graded (case-sensitive): the report names `release-notes.md` and gives the move in one of these forms, each on one line:
- `release-notes/SKILL.md`
- `release-notes/`, then `SKILL.md` within 80 characters
- `release-notes` (optionally backticked) followed by "directory", "folder" or "dir", then `SKILL.md` within 80 characters
- `SKILL.md`, then "in", "inside", "under" or "into" within 40 characters, then `release-notes/` or "`release-notes` directory/folder/dir" within 40 more
- `.claude/commands/release-notes.md`, where a single-file command works

A lowercase `skill.md` doesn't count. The grader checks the path and the move, not the explanation.
