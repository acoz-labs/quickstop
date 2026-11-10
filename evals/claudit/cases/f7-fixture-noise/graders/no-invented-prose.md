---
type: regex
pattern: '^[ \t\n]*# Claudit: [^\n]+\n(?:[ \t]*\n)+(?:Nothing found\.|[0-9]+ findings?\.)[ \t]*\n(?:[ \t]*\n)*(?:[0-9]+\.[ \t][^\n]*\n(?:[ \t]*```[^\n]*\n(?:(?![ \t]*```)[^\n]*\n)*[ \t]*```[ \t]*(?:\n|(?![\s\S]))|[ \t]+(?!```)\S[^\n]*\n|[ \t]*\n)*)*(?:## Not reported[ \t]*\n(?:[ \t]*\n)*(?:- [^\n]*\n(?:[ \t]+\S[^\n]*\n)*(?:[ \t]*\n)*)+)?## Always loaded[ \t]*\n(?:[ \t]*\n)*(?:\|[^\n]*\n)+(?:[ \t]*\n)*---[ \t]*\n(?:Outside the repo, not checked: [^\n]*|Because `[^`\n]+` above the repo loads[^\n]*|`[^`\n]+` is a symlink to `[^`\n]+`; the audit reads [^\n]*|Not checked: [^\n]*|Run `/doctor prompt-audit` for contradictions and wording\.|Claudit [0-9.]+; [^\n]*|Claude Code version unknown[^\n]*|Not a git repository[^\n]*|`[^`\n]+` is not valid; nothing dismissed from it\.)[ \t]*(?:\n(?:Outside the repo, not checked: [^\n]*|Because `[^`\n]+` above the repo loads[^\n]*|`[^`\n]+` is a symlink to `[^`\n]+`; the audit reads [^\n]*|Not checked: [^\n]*|Run `/doctor prompt-audit` for contradictions and wording\.|Claudit [0-9.]+; [^\n]*|Claude Code version unknown[^\n]*|Not a git repository[^\n]*|`[^`\n]+` is not valid; nothing dismissed from it\.)[ \t]*)*[ \t\n]*(?![\s\S])'
weight: 1
---
The report holds only the template's parts (title, count line, numbered items, "Not reported", "Always loaded", the footer lines). Advice or any other prose outside them fails.

Script-graded and built from the scan of the scaffolded fixture by `tests/claudit_graders.py` (rebuild with
`python3 tests/claudit_graders.py --write`); the pattern is `template_pattern` in `bin/claudit-eval`, which also checks
real-repository reports.
