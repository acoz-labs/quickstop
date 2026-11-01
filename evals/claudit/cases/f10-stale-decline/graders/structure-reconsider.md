---
type: regex
pattern: '(?:^|\n)#{2,3}[ \t]+Declined by the project[^\n]*(?=(?:(?!\n#{1,2}[ \t])[\s\S])*?\x60?docs/decisions\.md:3\b(?:(?!\n[-*][ \t]|\n#{1,2}[ \t]|\n[-*_]{3,}[ \t]*(?:\n|(?![\s\S])))[\s\S])*?\bWorth reconsidering\b(?:(?!\n[-*][ \t]|\n#{1,2}[ \t]|\n[-*_]{3,}[ \t]*(?:\n|(?![\s\S])))[\s\S])*?https://code\.claude\.com/docs/en/hooks)(?=(?:(?!\n#{1,2}[ \t])[\s\S])*?\x60?docs/decisions\.md:4\b(?:(?!\n[-*][ \t]|\n#{1,2}[ \t]|\n[-*_]{3,}[ \t]*(?:\n|(?![\s\S])))[\s\S])*?\bWorth reconsidering\b(?:(?!\n[-*][ \t]|\n#{1,2}[ \t]|\n[-*_]{3,}[ \t]*(?:\n|(?![\s\S])))[\s\S])*?\x60?CLAUDE\.md:5\b)'
flags: i
weight: 1
---
Each declined entry the scan marks gets a Worth reconsidering note citing its evidence (issue #184 requirement 2): `docs/decisions.md:3` cites https://code.claude.com/docs/en/hooks; `docs/decisions.md:4` cites `CLAUDE.md:5`.

Script-graded (case-insensitive): in that entry, "Worth reconsidering" and then, before the entry ends, the evidence URL or `path:line` (optionally backticked).
