---
type: regex
pattern: '^(?![\s\S]*\n[0-9]+\.[ \t][ \t]*(?!`CLAUDE\.md:7`))(?=(?:(?!\n[0-9]+\.[ \t][ \t]*`CLAUDE\.md:7`)[\s\S])*(?:\n[0-9]+\.[ \t][ \t]*`CLAUDE\.md:7`(?:(?!\n[0-9]+\.[ \t][ \t]*`CLAUDE\.md:7`)[\s\S])*){1}(?![\s\S]))(?![\s\S]*\n[0-9]+\.[ \t][ \t]*`CLAUDE\.md:7`(?:(?!(?:Bash\(bin/test\)))(?:(?!\n[0-9]+\.[ \t]|\n#{1,6}[ \t]|\n---)[\s\S]))*(?=\n[0-9]+\.[ \t]|\n#{1,6}[ \t]|\n---|(?![\s\S])))'
weight: 1
---
The numbered items are exactly the scan's findings, one to one: `CLAUDE.md:7` (allowlist). An invented item, an item with no citation or a second item at an expected citation fails.

Script-graded and built from the scan of the scaffolded fixture by `tests/claudit_graders.py` (rebuild with
`python3 tests/claudit_graders.py --write`); the pattern is `findings_pattern` in `bin/claudit-eval`, which also checks
real-repository reports.
