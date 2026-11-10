---
type: regex
pattern: '(?=[\s\S]*\n---[ \t]*\n[\s\S]*`CLAUDE\.md`\ is\ a\ symlink\ to\ `AGENTS\.md`;\ the\ audit\ reads\ `AGENTS\.md`\.)'
weight: 1
---
After the footer rule, the scope line: "`CLAUDE.md` is a symlink to `AGENTS.md`; the audit reads `AGENTS.md`."

Script-graded and built from the scan of the scaffolded fixture by `tests/claudit_graders.py` (rebuild with
`python3 tests/claudit_graders.py --write`); the pattern is `lines_pattern` in `bin/claudit-eval`, which also checks
real-repository reports.
