---
type: regex
pattern: '(?:^|\n)(?:[^\n]*\bwhy not\b[^\n]*\b(?:reconsider|revisit)\w*|[^\n]*\b(?:reconsider|revisit)\w*[^\n]*\?[ \t]*(?=\n|(?![\s\S]))|[^\n]*?(?<!not worth )(?<!do not )(?<!does not )(?<!should not )(?<!no need to )(?<!nothing to )(?<!nothing is worth )(?<!nothing here is worth )\b(?:reconsider|revisit)\w*)'
flags: i
match: not_contains
weight: 1
---
No declined entry has evidence that its reason no longer holds, so nothing may be offered for reconsideration (issue #184 requirement 2).

Script-graded (case-insensitive, must not match): any reconsider... or revisit... fails, unless directly after "not worth ", "do not ", "does not ", "should not ", "no need to ", "nothing to ", "nothing is worth " or "nothing here is worth ". A negation elsewhere on the line doesn't exempt it, and a line with "why not" or ending in "?" always fails.
