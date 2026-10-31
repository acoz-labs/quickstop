---
type: regex
pattern: '(?:^|\n)[-*_]{3,}[ \t]*\n(?:[^\n]*\n)*?[^\n]*\bClaudit 4\.1\.0; audited commit \x60?[0-9a-f]{40}\b'
weight: 1
---
The footer gives the Claudit version and the audited commit (issue #174 requirement 6).

Script-graded (case-sensitive): after a `---` rule, a line has "Claudit 4.1.0; audited commit " then 40 hex characters (optionally backticked). The exact commit isn't compared, because the eval host owns the workspace's history.
