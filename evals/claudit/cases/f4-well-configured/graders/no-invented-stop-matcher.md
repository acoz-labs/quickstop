---
type: llm
weight: 1
---
The fixture's `Stop` hook group has no `matcher`. That is correct: `Stop` does not support matchers and always fires (a matcher on it would be silently ignored).

PASS if the report does not present the missing matcher on the Stop hook as a defect, and does not recommend adding a matcher to it. Not mentioning it is a PASS.

FAIL if the report says the Stop hook is missing a required matcher, is misconfigured because it has none, or recommends adding one (such as `"*"` or a tool name) as a fix.
