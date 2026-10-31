---
type: regex
pattern: '(?:^|\n)#{2,3}[ \t]+Declined by the project[^\n]*(?=(?:(?!\n#{1,2}[ \t])[\s\S])*?\x60?docs/decisions\.md:3\b)(?=(?:(?!\n#{1,2}[ \t])[\s\S])*?\x60?docs/decisions\.md:5\b)'
weight: 1
---
The report lists both declines under "Declined by the project" with their source lines (issue #174 requirement 4): `docs/decisions.md:3` retires Claude Code hooks and `docs/decisions.md:5` declines an eval campaign.

Script-graded (case-sensitive): a `##` or `###` heading "Declined by the project", then, before the next `#` or `##` heading, each `path:line` (optionally backticked).
