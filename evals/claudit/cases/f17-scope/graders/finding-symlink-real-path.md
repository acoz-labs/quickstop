---
type: regex
pattern: '(?:^|\n)(?![ \t]*(?:[-*>][ \t]+)?(?:\*\*|_)?Sources?\b)(?![^\n]*(?:\bwhy[ \t]+not\b|\?(?=[ \t*_"\x60)]|\n|(?![\s\S]))))(?![^\n]*\b(?:no|not|never|without|nor|none|nothing|don[\x27’]t|doesn[\x27’]t|didn[\x27’]t|wouldn[\x27’]t|haven[\x27’]t|isn[\x27’]t|aren[\x27’]t|won[\x27’]t|needn[\x27’]t|shouldn[\x27’]t|cannot|can[\x27’]t|skip|avoid)[ \t]+(?:(?:need\w*|requir\w*|ha(?:ve|s)|us(?:e|ing)|rely(?:ing)?[ \t]+on|bother(?:ing)?[ \t]+with|add(?:ing)?|enabl\w*|set(?:ting)?[ \t]+up|configur\w*|turn(?:ing)?[ \t]+on|worth|is|are|be|any|a|an|the|for|of|to|also|really|actually|even|yet|this|that|such)[ \t]+){0,4}[\x60*"(]*(?:\bsymlink\w*|\bsymbolic[ \t]+link|\blinks?[ \t]+to\b|\bpoints?[ \t]+(?:at|to)\b|->|→|\bresolves?[ \t]+to\b|\balias\w*))(?=[^\n]*CLAUDE\.md)(?=[^\n]*AGENTS\.md)(?=[^\n]*(?:\bsymlink\w*|\bsymbolic[ \t]+link|\blinks?[ \t]+to\b|\bpoints?[ \t]+(?:at|to)\b|->|→|\bresolves?[ \t]+to\b|\balias\w*))[^\n]*'
flags: i
weight: 1
---
The repo's `CLAUDE.md` is a symlink to its `AGENTS.md`.

PASS when one line names `CLAUDE.md`, `AGENTS.md` and the link (symlink, symbolic link, links to, points to/at, `->`, an arrow, resolves to, alias), with no negation governing the link word ("not a symlink").

Script-graded (case-insensitive). The parts, and the controls each must pass and fail, are in `tests/test_claudit_fixture_graders.py`; rebuild with `python3 tests/test_claudit_fixture_graders.py --write`. A line never counts when it is a `Source:` citation line, a question (it has "why not" or a `?` before a space or the line end), or when a negation directly governs the finding ("no ask rule is needed", "not a symlink"; a negation elsewhere on the line doesn't count) or it says the fix is already in place.
