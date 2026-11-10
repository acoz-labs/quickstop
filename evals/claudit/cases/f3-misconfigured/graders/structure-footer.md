---
type: regex
pattern: '(?=[\s\S]*\n---[ \t]*\n[\s\S]*Not checked: user and managed settings, settings validity, server-side branch protection\.)(?=[\s\S]*\n---[ \t]*\n[\s\S]*Run `/doctor prompt-audit` for contradictions and wording\.)(?=[\s\S]*\n---[ \t]*\n[\s\S]*Claudit 5\.0\.0; (?:audited commit [0-9a-f]{40}|not a git repo))'
weight: 1
---
After the footer rule: the not-checked line, the `/doctor prompt-audit` line and "Claudit 5.0.0; audited commit <sha>".

Script-graded and built from the scan of the scaffolded fixture by `tests/claudit_graders.py` (rebuild with
`python3 tests/claudit_graders.py --write`); the pattern is `footer_pattern` in `bin/claudit-eval`, which also checks
real-repository reports.
