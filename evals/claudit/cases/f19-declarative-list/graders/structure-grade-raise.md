---
type: regex
pattern: '(?:^|\n)[ \t]*[-*][ \t]+\*\*(?:Correctness|Alignment|Coverage): [B-F]\*\*(?![^\n]*\bitems?[ \t]+#?[0-9])'
flags: i
match: not_contains
weight: 1
---
Every grade below A says which plan items would raise it (issue #174 requirement 5).

Script-graded (case-insensitive, must not match): a grade line `- **Correctness|Alignment|Coverage: B-F**` with no "item N" or "items N" (optionally `#N`) later on that line fails.
