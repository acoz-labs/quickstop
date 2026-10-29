---
type: llm
weight: 1
---
The fixture ships a Claude Code plugin whose only automated checks are Python unit tests of the skill's helper script. There is no eval suite (no `evals/` directory, no `experimental.evals` in `plugin.json`) and nothing runs `claude plugin eval`, so nobody measures whether Claude actually picks up and follows the `changelog-entry` skill.

PASS only if the report (1) identifies that the plugin's behaviour is not evaluated (no eval suite / no `claude plugin eval` in CI or docs), and (2) recommends adding eval cases for the skill (for example under `evals/`) and running them with `claude plugin eval` in CI, a release gate or the documented checks. Recommending `claude plugin eval` with an equivalent eval directory is acceptable.

FAIL if the report only recommends more unit tests, generic "testing the skill manually", or names evals without `claude plugin eval` or an eval suite for the plugin.
