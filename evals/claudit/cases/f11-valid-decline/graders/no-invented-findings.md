---
type: regex
pattern: '^(?![\s\S]*\n[0-9]+\.[ \t])'
weight: 1
---
The numbered items are exactly the scan's findings, one to one: none. An invented item, an item with no citation or a second item at an expected citation fails.

Script-graded and built from the scan of the scaffolded fixture by `tests/claudit_graders.py` (rebuild with
`python3 tests/claudit_graders.py --write`); the pattern is `findings_pattern` in `bin/claudit-eval`, which also checks
real-repository reports.
