---
type: regex
pattern: '(?:^|\n)#{2,3}[ \t]+Declined by the project[^\n]*(?=(?:(?!\n#{1,2}[ \t])[\s\S])*?\x60?docs/decisions\.md:3\b)(?=(?:(?!\n#{1,2}[ \t])[\s\S])*?\x60?docs/decisions\.md:4\b)'
weight: 1
---
The report lists each decline under "Declined by the project" with its source line: `docs/decisions.md:3`, `docs/decisions.md:4`.

Script-graded (case-sensitive): a `##` or `###` heading "Declined by the project", then, before the next `#` or `##` heading, each `path:line` (optionally backticked).
