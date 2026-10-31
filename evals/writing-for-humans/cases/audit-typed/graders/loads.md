---
type: regex
target: trace
pattern: '^(?=.*"subtype":"init")(?=.*"plugins":\[[^\]]*"name":"writing-for-humans")(?=.*"skills":\[[^\]]*"writing-for-humans:writing-audit")(?=.*"skills":\[[^\]]*"writing-for-humans:writing-style")'
flags: m
weight: 1
---
The session's init record lists the plugin under test and both of its skills, `writing-for-humans:writing-audit` and `writing-for-humans:writing-style`. All conditions must hold on the one init line.
