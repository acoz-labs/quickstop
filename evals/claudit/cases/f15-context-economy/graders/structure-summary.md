---
type: regex
pattern: '^[ \t\n]*# Claudit: [^\n]+\n(?:[ \t]*\n)*3 findings?\.[ \t]*(?:\n|(?![\s\S]))'
weight: 1
---
The line after the title is "3 findings."

Script-graded and built from the scan of the scaffolded fixture by `tests/claudit_graders.py` (rebuild with
`python3 tests/claudit_graders.py --write`); the pattern is `summary_pattern` in `bin/claudit-eval`, which also checks
real-repository reports.
