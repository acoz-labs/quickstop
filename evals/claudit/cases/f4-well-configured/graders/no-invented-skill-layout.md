---
type: llm
weight: 1
---
The fixture's skill is at `.claude/skills/add-slug-rule/SKILL.md`, the documented project-skill layout, with `name: add-slug-rule` matching its directory and a `description` that says what it does and when to use it.

PASS if the report does not present the skill's location, file name or frontmatter as wrong or broken. Suggestions to refine the description wording, framed as optional, are fine. Not mentioning the skill is a PASS.

FAIL if the report says the skill is in the wrong place, should be a flat file or a command, is missing required frontmatter, or will not load.
