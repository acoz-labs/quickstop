---
type: llm
weight: 1
---
The fixture has `docs/release-procedure.md`, a ten-step numbered release procedure that agents are told to follow, but it is only a plain doc: no skill exists and CLAUDE.md does not even reference it.

PASS only if the report (1) identifies the release procedure in `docs/release-procedure.md` (by path or as "the release procedure doc") as a repeated, agent-followed workflow that is not packaged as a skill, and (2) recommends turning it into a project skill, for example `.claude/skills/release/SKILL.md` with `name`/`description` frontmatter (optionally keeping or linking the doc). A slash command under `.claude/commands/release.md` is also acceptable, since commands and skills are the same mechanism.

FAIL if the report only suggests "consider adding skills" without naming the release procedure, or only suggests linking the doc from CLAUDE.md or importing it with `@docs/release-procedure.md`.
