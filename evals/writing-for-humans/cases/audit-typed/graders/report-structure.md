---
type: regex
pattern: '^(?=[\s\S]*\brewr(?:ite|ites|itten|ote|iting)\b)(?=[\s\S]*\b(?:kept|flag|flags|flagged|flagging)\b)'
flags: i
weight: 1
---
The final report has the parts `skills/writing-audit/SKILL.md:65` requires: what was rewritten (or, review-only, the proposed rewrites, `:61`), and what was kept and flagged. Case-insensitive: a form of "rewrite" and one of "kept" or "flag(s/ged/ging)", anywhere in the report. It checks the report's shape, not the quality of the rewrites.
