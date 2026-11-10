---
type: regex
pattern: '(?=[\s\S]*\n[0-9]+\.[ \t][ \t]*`CLAUDE\.md:3`(?:(?!\n[0-9]+\.[ \t]|\n#{1,6}[ \t]|\n---)[\s\S])*?(?:Bash\(bin/ci\)))'
weight: 1
---
A numbered item cites `CLAUDE.md:3` and holds `Bash\(bin/ci\)`: the scan's `allowlist` finding ("No `permissions.allow` rule in `.claude/settings.json` covers `bin/ci`, so every run of it asks first.").

Script-graded and built from the scan of the scaffolded fixture by `tests/claudit_graders.py` (rebuild with
`python3 tests/claudit_graders.py --write`); the pattern is `finding_pattern` in `bin/claudit-eval`, which also checks
real-repository reports.
