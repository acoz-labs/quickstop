---
type: regex
pattern: '(?=[\s\S]*\n[0-9]+\.[ \t][ \t]*`CLAUDE\.md:5`(?:(?!\n[0-9]+\.[ \t]|\n#{1,6}[ \t]|\n---)[\s\S])*?(?:exit 2))'
weight: 1
---
A numbered item cites `CLAUDE.md:5` and holds `exit 2`: the scan's `stop-hook` finding ("`CLAUDE.md:5` says "Run `bin/check` before you report any change as done: it runs `bin/lint` over `src/` and `tests/`, then the unit tests with `python -m unittest`, and it exits n", but no Stop hook ").

Script-graded and built from the scan of the scaffolded fixture by `tests/claudit_graders.py` (rebuild with
`python3 tests/claudit_graders.py --write`); the pattern is `finding_pattern` in `bin/claudit-eval`, which also checks
real-repository reports.
