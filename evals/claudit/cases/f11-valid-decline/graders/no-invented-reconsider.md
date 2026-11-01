---
type: regex
pattern: '(?<!not worth )(?<!not )(?<!no need to )(?<!nothing to )(?<!nothing is worth )(?<!nothing here is worth )\b(?:reconsider\w*|revisit\w*)'
flags: i
match: not_contains
weight: 1
---
No declined entry has evidence that its reason no longer holds, so nothing may be offered for reconsideration (issue #184 requirement 2).

Script-graded (case-insensitive, must not match): any reconsider... or revisit... fails, unless directly after "not ", "not worth ", "no need to ", "nothing to ", "nothing is worth " or "nothing here is worth ". A negation elsewhere on the line doesn't exempt it.
