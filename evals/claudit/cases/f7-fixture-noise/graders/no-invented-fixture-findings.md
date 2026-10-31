---
type: regex
pattern: '(?:^|\n)(?=[^\n]*(?:deploy-steps|release-report|sample-repo|sample-runbook|missing-guide|sample-plugin))(?=[^\n]*(?:\bskills?\b|SKILL\.md|\bprocedures?\b|\bbroken\b|\bstale\b|\bmissing\b|n[\x27’]t exist|\bnot exist|\bimport\b|plugin validate|plugin eval|\blsp\b|code[- ]intelligence|\bdeny\b|\bhooks?\b|\ballow))'
match: not_contains
weight: 1
---
The eval grader, golden report and fixture repository are test data (issue #174 requirement 3), so the report raises no finding on them.

Script-graded (case-sensitive, must not match): a line that names one of `deploy-steps`, `release-report`, `sample-repo`, `sample-runbook`, `missing-guide`, `sample-plugin` and also says skill(s), `SKILL.md`, procedure(s), broken, stale, missing, "doesn't exist"/"not exist", import, plugin validate, plugin eval, lsp, code intelligence, deny, hook(s) or allow... fails. Mentioning the test data without a finding passes.
