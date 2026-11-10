---
type: regex
pattern: '(?=[\s\S]*\n[0-9]+\.[ \t][ \t]*`CLAUDE\.md:14`(?:(?!\n[0-9]+\.[ \t]|\n#{1,6}[ \t]|\n---)[\s\S])*?(?:Bash\(gh\ pr\ merge\ \*\)))(?=[\s\S]*\n[0-9]+\.[ \t][ \t]*`CLAUDE\.md:14`(?:(?!\n[0-9]+\.[ \t]|\n#{1,6}[ \t]|\n---)[\s\S])*?(?:Bash\(bin/deploy\ \*\)))(?=[\s\S]*\n[0-9]+\.[ \t][ \t]*`CLAUDE\.md:14`(?:(?!\n[0-9]+\.[ \t]|\n#{1,6}[ \t]|\n---)[\s\S])*?(?:Bash\(bin/release\ \*\)))(?=[\s\S]*\n[0-9]+\.[ \t][ \t]*`CLAUDE\.md:14`(?:(?!\n[0-9]+\.[ \t]|\n#{1,6}[ \t]|\n---)[\s\S])*?(?:[Bb]ranch protection|deploy or release system))'
weight: 1
---
A numbered item cites `CLAUDE.md:14` and holds `Bash\(gh\ pr\ merge\ \*\)` and `Bash\(bin/deploy\ \*\)` and `Bash\(bin/release\ \*\)` and `[Bb]ranch protection|deploy or release system`: the scan's `gate-ask` finding ("`CLAUDE.md:14` says a person must approve merge, but no ask or deny rule covers `gh pr merge`, so Claude can run it without asking. `CLAUDE.md:15` says a person must approve deploy, but no ask or deny").

Script-graded and built from the scan of the scaffolded fixture by `tests/claudit_graders.py` (rebuild with
`python3 tests/claudit_graders.py --write`); the pattern is `finding_pattern` in `bin/claudit-eval`, which also checks
real-repository reports.
