---
type: regex
pattern: '(?=[\s\S]*\n---[ \t]*\n[\s\S]*Outside\ the\ repo,\ not\ checked:\ `\.\./CLAUDE\.md`\ and\ `\.\./AGENTS\.md`\ above\ the\ repo;\ `\.\./CLAUDE\.md`\ loads\ in\ every\ session\ here\.)'
weight: 1
---
After the footer rule, the scope line: "Outside the repo, not checked: `../CLAUDE.md` and `../AGENTS.md` above the repo; `../CLAUDE.md` loads in every session here."

Script-graded and built from the scan of the scaffolded fixture by `tests/claudit_graders.py` (rebuild with
`python3 tests/claudit_graders.py --write`); the pattern is `lines_pattern` in `bin/claudit-eval`, which also checks
real-repository reports.
