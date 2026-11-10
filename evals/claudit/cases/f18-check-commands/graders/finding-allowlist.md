---
type: regex
pattern: '(?=[\s\S]*\n[0-9]+\.[ \t][ \t]*`package\.json:9`(?:(?!\n[0-9]+\.[ \t]|\n#{1,6}[ \t]|\n---)[\s\S])*?(?:Bash\(bun\ run\ test\)))(?=[\s\S]*\n[0-9]+\.[ \t][ \t]*`package\.json:9`(?:(?!\n[0-9]+\.[ \t]|\n#{1,6}[ \t]|\n---)[\s\S])*?(?:Bash\(bun\ run\ lint\)))(?=[\s\S]*\n[0-9]+\.[ \t][ \t]*`package\.json:9`(?:(?!\n[0-9]+\.[ \t]|\n#{1,6}[ \t]|\n---)[\s\S])*?(?:Bash\(bun\ run\ check\)))(?=[\s\S]*\n[0-9]+\.[ \t][ \t]*`package\.json:9`(?:(?!\n[0-9]+\.[ \t]|\n#{1,6}[ \t]|\n---)[\s\S])*?(?:Bash\(bun\ run\ typecheck\)))'
weight: 1
---
A numbered item cites `package.json:9` and holds `Bash\(bun\ run\ test\)` and `Bash\(bun\ run\ lint\)` and `Bash\(bun\ run\ check\)` and `Bash\(bun\ run\ typecheck\)`: the scan's `allowlist` finding ("No `permissions.allow` rule in `.claude/settings.json` covers `bun run test`, `bun run lint`, `bun run check` and `bun run typecheck`, so every run of them asks first.").

Script-graded and built from the scan of the scaffolded fixture by `tests/claudit_graders.py` (rebuild with
`python3 tests/claudit_graders.py --write`); the pattern is `finding_pattern` in `bin/claudit-eval`, which also checks
real-repository reports.
