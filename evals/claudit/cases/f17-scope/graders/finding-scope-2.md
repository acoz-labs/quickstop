---
type: regex
pattern: '(?=[\s\S]*\n---[ \t]*\n[\s\S]*Because\ `\.\./CLAUDE\.md`\ above\ the\ repo\ loads,\ the\ repo''s\ `AGENTS\.md`\ is\ not\ read\ on\ its\ own;\ here\ it\ still\ loads\ because\ `CLAUDE\.md`\ is\ a\ symlink\ to\ it\.)'
weight: 1
---
After the footer rule, the scope line: "Because `../CLAUDE.md` above the repo loads, the repo's `AGENTS.md` is not read on its own; here it still loads because `CLAUDE.md` is a symlink to it."

Script-graded and built from the scan of the scaffolded fixture by `tests/claudit_graders.py` (rebuild with
`python3 tests/claudit_graders.py --write`); the pattern is `lines_pattern` in `bin/claudit-eval`, which also checks
real-repository reports.
