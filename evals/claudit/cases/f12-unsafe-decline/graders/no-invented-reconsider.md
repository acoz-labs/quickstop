---
type: regex
pattern: '(?:^|\n)(?![^\n]*\b(?:no|not|nothing|none|never)\b)[^\n]*\b(?:reconsider\w*|revisit\w*)'
flags: i
match: not_contains
weight: 1
---
No declined entry has evidence that its reason no longer holds, so nothing may be offered for reconsideration (issue #184 requirement 2).

Script-graded (case-insensitive, must not match): a line with reconsider... or revisit... and none of no, not, nothing, none or never fails.
