---
type: regex
pattern: '(?:^|\n)#{2,3}[ \t]+Declined by the project[^\n]*(?=(?:(?!\n#{1,2}[ \t])[\s\S])*?\x60?docs/decisions\.md:3\b(?:(?!\n[-*][ \t]|\n#{1,2}[ \t]|\n[-*_]{3,}[ \t]*(?:\n|(?![\s\S])))[\s\S])*?\bReason(?:\*\*)?:(?:\*\*)?[ \t]*["\u201c\x60*_]*because[\s\x60"\u201c\u201d*_]+hooks[\s\x60"\u201c\u201d*_]+can[''\u2019]t[\s\x60"\u201c\u201d*_]+block[\s\x60"\u201c\u201d*_]+Claude[\s\x60"\u201c\u201d*_]+from)(?=(?:(?!\n#{1,2}[ \t])[\s\S])*?\x60?docs/decisions\.md:4\b(?:(?!\n[-*][ \t]|\n#{1,2}[ \t]|\n[-*_]{3,}[ \t]*(?:\n|(?![\s\S])))[\s\S])*?\bReason(?:\*\*)?:(?:\*\*)?[ \t]*["\u201c\x60*_]*because[\s\x60"\u201c\u201d*_]+there[\s\x60"\u201c\u201d*_]+is[\s\x60"\u201c\u201d*_]+no[\s\x60"\u201c\u201d*_]+check[\s\x60"\u201c\u201d*_]+command)'
flags: i
weight: 1
---
Each declined entry gives the reason the scan captured (issue #184 requirement 1): `docs/decisions.md:3` "because hooks can't block Claude from finishing"; `docs/decisions.md:4` "because there is no check command".

Script-graded (case-insensitive): in the Declined by the project section, after each entry's `path:line` and before the next column-0 bullet or section end, "Reason:" (optionally bold) then the first six words of the reason (any quotes, backticks, emphasis or line breaks between words; straight or curly apostrophes), or "no reason given".
