---
type: regex
pattern: '^(?![\s\S]*\n[0-9]+\.[ \t][ \t]*(?!`CLAUDE\.md:13`|`CLAUDE\.md:14`))(?=(?:(?!\n[0-9]+\.[ \t][ \t]*`CLAUDE\.md:13`)[\s\S])*(?:\n[0-9]+\.[ \t][ \t]*`CLAUDE\.md:13`(?:(?!\n[0-9]+\.[ \t][ \t]*`CLAUDE\.md:13`)[\s\S])*){1}(?![\s\S]))(?![\s\S]*\n[0-9]+\.[ \t][ \t]*`CLAUDE\.md:13`(?:(?!(?:exit 2))(?:(?!\n[0-9]+\.[ \t]|\n#{1,6}[ \t]|\n---)[\s\S]))*(?=\n[0-9]+\.[ \t]|\n#{1,6}[ \t]|\n---|(?![\s\S])))(?=(?:(?!\n[0-9]+\.[ \t][ \t]*`CLAUDE\.md:14`)[\s\S])*(?:\n[0-9]+\.[ \t][ \t]*`CLAUDE\.md:14`(?:(?!\n[0-9]+\.[ \t][ \t]*`CLAUDE\.md:14`)[\s\S])*){1}(?![\s\S]))(?![\s\S]*\n[0-9]+\.[ \t][ \t]*`CLAUDE\.md:14`(?:(?!(?:Bash\(gh\ pr\ merge\ \*\)))(?:(?!\n[0-9]+\.[ \t]|\n#{1,6}[ \t]|\n---)[\s\S]))*(?=\n[0-9]+\.[ \t]|\n#{1,6}[ \t]|\n---|(?![\s\S])))'
weight: 1
---
The numbered items are exactly the scan's findings, one to one: `CLAUDE.md:13` (stop-hook), `CLAUDE.md:14` (gate-ask). An invented item, an item with no citation or a second item at an expected citation fails.

Script-graded and built from the scan of the scaffolded fixture by `tests/claudit_graders.py` (rebuild with
`python3 tests/claudit_graders.py --write`); the pattern is `findings_pattern` in `bin/claudit-eval`, which also checks
real-repository reports.
