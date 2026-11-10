---
type: regex
pattern: '(?=[\s\S]*\n[0-9]+\.[ \t][ \t]*`AGENTS\.md:3`(?:(?!\n[0-9]+\.[ \t]|\n#{1,6}[ \t]|\n---)[\s\S])*?(?:exit 2))'
weight: 1
---
A numbered item cites `AGENTS.md:3` and holds `exit 2`: the scan's `stop-hook` finding ("`AGENTS.md:3` says "Agents maintain this repository. Run `bin/check` before you report a change as done.", but no Stop hook runs `bin/check`, so nothing makes Claude run it before finishing.").

Script-graded and built from the scan of the scaffolded fixture by `tests/claudit_graders.py` (rebuild with
`python3 tests/claudit_graders.py --write`); the pattern is `finding_pattern` in `bin/claudit-eval`, which also checks
real-repository reports.
