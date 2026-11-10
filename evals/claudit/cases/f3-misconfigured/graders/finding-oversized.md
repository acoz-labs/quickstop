---
type: regex
pattern: '(?=[\s\S]*\n[0-9]+\.[ \t][ \t]*`CLAUDE\.md:1`(?:(?!\n[0-9]+\.[ \t]|\n#{1,6}[ \t]|\n---)[\s\S])*?(?:200))'
weight: 1
---
A numbered item cites `CLAUDE.md:1` and holds `200`: the scan's `oversized:CLAUDE.md` finding ("`CLAUDE.md` is 241 lines (1,341 words, about 2,190 tokens), past the documented target of under 200 lines, and it loads in every session.").

Script-graded and built from the scan of the scaffolded fixture by `tests/claudit_graders.py` (rebuild with
`python3 tests/claudit_graders.py --write`); the pattern is `finding_pattern` in `bin/claudit-eval`, which also checks
real-repository reports.
