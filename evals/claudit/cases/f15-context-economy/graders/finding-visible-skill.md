---
type: regex
pattern: '(?=[\s\S]*\n[0-9]+\.[ \t][ \t]*`\.claude/skills/schema\-rules/SKILL\.md:3`(?:(?!\n[0-9]+\.[ \t]|\n#{1,6}[ \t]|\n---)[\s\S])*?(?:disable-model-invocation|subagent.s prompt))'
weight: 1
---
A numbered item cites `.claude/skills/schema-rules/SKILL.md:3` and holds `disable-model-invocation|subagent.s prompt`: the scan's `visible-skill:.claude/skills/schema-rules/SKILL.md` finding ("`schema-rules` is read only by the `migrator` subagent (.claude/agents/migrator.md), but Claude can invoke it, so its description loads in every session.").

Script-graded and built from the scan of the scaffolded fixture by `tests/claudit_graders.py` (rebuild with
`python3 tests/claudit_graders.py --write`); the pattern is `finding_pattern` in `bin/claudit-eval`, which also checks
real-repository reports.
