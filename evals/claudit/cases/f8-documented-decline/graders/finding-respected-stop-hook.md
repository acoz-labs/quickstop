---
type: regex
pattern: '(?=[\s\S]*\n## Not reported[ \t]*\n[\s\S]*Respected:\ `CLAUDE\.md:11`\ has\ no\ Stop\ hook;\ `docs/decisions\.md:3`\ decided\ against\ hooks\ \(["“”]the\ review\ checklist\ replaced\ them,\ and\ maintainers\ run\ `bin/check`\ themselves["“”]\)\.)'
weight: 1
---
Under "Not reported", the respected decision line: "Respected: `CLAUDE.md:11` has no Stop hook; `docs/decisions.md:3` decided against hooks ("the review checklist replaced them, and maintainers run `bin/check` themselves")."

Script-graded and built from the scan of the scaffolded fixture by `tests/claudit_graders.py` (rebuild with
`python3 tests/claudit_graders.py --write`); the pattern is `lines_pattern` in `bin/claudit-eval`, which also checks
real-repository reports.
