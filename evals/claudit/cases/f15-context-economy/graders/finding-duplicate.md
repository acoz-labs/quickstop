---
type: regex
pattern: '(?=[\s\S]*\n[0-9]+\.[ \t][ \t]*`CLAUDE\.md:6`(?:(?!\n[0-9]+\.[ \t]|\n#{1,6}[ \t]|\n---)[\s\S])*?(?:\.claude/agents/migrator\.md))(?=[\s\S]*\n[0-9]+\.[ \t][ \t]*`CLAUDE\.md:6`(?:(?!\n[0-9]+\.[ \t]|\n#{1,6}[ \t]|\n---)[\s\S])*?(?:docs/contributing\.md))'
weight: 1
---
A numbered item cites `CLAUDE.md:6` and holds `\.claude/agents/migrator\.md` and `docs/contributing\.md`: the scan's `duplicate` finding ("One rule is copied word for word into 3 files, `CLAUDE.md:6`, `.claude/agents/migrator.md:10` and `docs/contributing.md:10`: "Never edit files under `migrations/` by hand; create a new one with `bin/m").

Script-graded and built from the scan of the scaffolded fixture by `tests/claudit_graders.py` (rebuild with
`python3 tests/claudit_graders.py --write`); the pattern is `finding_pattern` in `bin/claudit-eval`, which also checks
real-repository reports.
