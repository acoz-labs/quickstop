# Changelog

## 5.0.0

A breaking change to the report: Claudit is now a thin checker. It lists only what
its scan script finds, each with its file, real line and exact fix, or "Nothing
found", and recommends running `/doctor prompt-audit` for contradictions and
wording.

Kept: stale paths, commands, dependencies and imports; history lines, whose fix now
keeps the current fact and moves only the dated detail; gates and must-run rules
nothing enforces; the check command's allow rule; scope and symlinks; the
always-loaded table, a finding only past a documented limit; missing skill and
subagent names and subagent-only skills in the listing; rules copied word for word
into three or more files. Decisions against hooks or pre-approved commands are
respected unless a fact contradicts their stated reason. Dismissals keep working.

Removed: the Correctness, Alignment and Coverage grades and the ranked plan; the
procedure detector and every "add a skill or feature" recommendation; the feature
catalog and its Coverage baseline and profiles; the settings-validity checks, which
`/doctor` reports; paraphrase matching; the Intent paragraph; `--deep`, `--user` and
the docs fetch; the `auditor` subagent.

Why: the 4.3.0 and 4.3.1 gates showed the script checks held up on every real
repository tested, while the model-judged grades and skill advice did not
([#193](https://github.com/acoz-labs/quickstop/issues/193),
[#207](https://github.com/acoz-labs/quickstop/issues/207)).
