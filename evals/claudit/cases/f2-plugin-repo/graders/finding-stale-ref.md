---
type: regex
pattern: '(?=[\s\S]*\n[0-9]+\.[ \t][ \t]*`CLAUDE\.md:10`(?:(?!\n[0-9]+\.[ \t]|\n#{1,6}[ \t]|\n---)[\s\S])*?(?:docs/architecture\.md))'
weight: 1
---
A numbered item cites `CLAUDE.md:10` and holds `docs/architecture\.md`: the scan's `stale-ref:CLAUDE.md:docs/architecture.md` finding ("`docs/architecture.md` does not exist; `CLAUDE.md:10` names it.").

Script-graded and built from the scan of the scaffolded fixture by `tests/claudit_graders.py` (rebuild with
`python3 tests/claudit_graders.py --write`); the pattern is `finding_pattern` in `bin/claudit-eval`, which also checks
real-repository reports.
