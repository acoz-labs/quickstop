---
type: regex
pattern: '(?=[\s\S]*\n## Not reported[ \t]*\n[\s\S]*Respected:\ `CLAUDE\.md:9`\ has\ no\ Stop\ hook;\ `docs/decisions\.md:3`\ decided\ against\ hooks\ \(no\ reason\ given\)\.)'
weight: 1
---
Under "Not reported", the respected decision line: "Respected: `CLAUDE.md:9` has no Stop hook; `docs/decisions.md:3` decided against hooks (no reason given)."

Script-graded and built from the scan of the scaffolded fixture by `tests/claudit_graders.py` (rebuild with
`python3 tests/claudit_graders.py --write`); the pattern is `lines_pattern` in `bin/claudit-eval`, which also checks
real-repository reports.
