---
type: regex
pattern: '(?=[\s\S]*\n[0-9]+\.[ \t][ \t]*`CLAUDE\.md:7`(?:(?!\n[0-9]+\.[ \t]|\n#{1,6}[ \t]|\n---)[\s\S])*?(?:Bash\(bin/test\)))'
weight: 1
---
A numbered item cites `CLAUDE.md:7` and holds `Bash\(bin/test\)`: the scan's `allowlist` finding ("No `permissions.allow` rule in `.claude/settings.json` covers `bin/test`, so every run of it asks first. `docs/decisions.md:3` decided against pre-approved commands ("in favour of bypassPermissions in").

Script-graded and built from the scan of the scaffolded fixture by `tests/claudit_graders.py` (rebuild with
`python3 tests/claudit_graders.py --write`); the pattern is `finding_pattern` in `bin/claudit-eval`, which also checks
real-repository reports.
