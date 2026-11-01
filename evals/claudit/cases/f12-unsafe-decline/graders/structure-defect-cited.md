---
type: regex
pattern: '(?=[\s\S]*?(?:^|\n)#{2,3}[ \t]+(?:The )?Top(?: [0-9]+)? changes[^\n]*(?:(?!\n(?:#{3,4}[ \t]+)?(?:\*\*)?[0-9]+[.)][ \t]|\n#{1,2}[ \t]|\n[-*_]{3,}[ \t]*(?:\n|(?![\s\S])))[\s\S])*\n(?:#{3,4}[ \t]+)?(?:\*\*)?1[.)][ \t]+(?:\*\*)?Remove[ \t]+defaultMode[ \t]+from[ \t]+\x60?\.claude/settings\.json\x60?(?:(?!\n(?:#{3,4}[ \t]+)?(?:\*\*)?[0-9]+[.)][ \t]|\n#{1,2}[ \t]|\n[-*_]{3,})[\s\S])*?\n(?![ \t]*(?:[-*][ \t]+)?(?:\*\*)?Source\b)[^\n]*\x60?docs/decisions\.md:3\b)'
flags: i
weight: 1
---
The defect the decline left behind is in the plan and cites the decline (issue #184 requirement 3): 1. Remove defaultMode from .claude/settings.json cites `docs/decisions.md:3`.

Script-graded (case-insensitive): in Top changes, item N with its title word for word, then before the next item or section end a line that isn't a `Source:` line naming the decline's `path:line` (optionally backticked).
