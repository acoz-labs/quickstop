---
type: regex
target: trace
pattern: '^(?=.*"subtype":"init")(?=.*"tools":\[[^\]]*"Skill")(?=.*"skills":\[[^\]]*"writing-for-humans:writing-audit")'
flags: m
weight: 1
---
The session's init record offers the Skill tool and lists `writing-for-humans:writing-audit`, so `not-invoked` can't pass just because the skill or the tool was missing.
