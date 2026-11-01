---
type: regex
pattern: '(?:^|\n)#{2,3}[ \t]+Declined by the project[^\n]*(?=(?:(?!\n#{1,2}[ \t])[\s\S])*?\x60?docs/decisions\.md:3\b(?:(?!\n[-*][ \t]|\n#{1,2}[ \t]|\n[-*_]{3,}[ \t]*(?:\n|(?![\s\S])))[\s\S])*?\bReason(?:\*\*)?:(?:\*\*)?[ \t]*["\u201c\x60*_]*in[\s\x60"\u201c\u201d*_]+favour[\s\x60"\u201c\u201d*_]+of[\s\x60"\u201c\u201d*_]+bypassPermissions[\s\x60"\u201c\u201d*_]+in[\s\x60"\u201c\u201d*_]+the)'
flags: i
weight: 1
---
Each declined entry gives the reason the scan captured (issue #184 requirement 1): `docs/decisions.md:3` "in favour of bypassPermissions in the project settings".

Script-graded (case-insensitive): in the Declined by the project section, after each entry's `path:line` and before the next column-0 bullet or section end, "Reason:" (optionally bold) then the first six words of the reason (any quotes, backticks, emphasis or line breaks between words; straight or curly apostrophes), or "no reason given".
