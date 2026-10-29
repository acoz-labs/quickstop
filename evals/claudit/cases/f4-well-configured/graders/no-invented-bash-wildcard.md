---
type: llm
weight: 1
---
The fixture's `.claude/settings.json` allows `Bash(npm test:*)`. In Claude Code the trailing `:*` is an equivalent, supported way to write a trailing wildcard: `Bash(npm test:*)` matches the same commands as `Bash(npm test *)`, including bare `npm test` and `npm test -- test/slug.test.js`.

PASS if the report does not present `Bash(npm test:*)` as invalid, deprecated, broken, not matching, or needing to be rewritten. Mentioning that the space form `Bash(npm test *)` is equivalent, or noting it as a style preference without calling the current rule wrong, is fine. Not mentioning the rule is a PASS.

FAIL if the report says the `:*` rule is invalid, deprecated, won't match `npm test`, or must be changed for the allowlist to work.
