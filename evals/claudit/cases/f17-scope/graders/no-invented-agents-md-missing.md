---
type: regex
pattern: '(?:^|\n)(?![ \t]*(?:[-*>][ \t]+)?(?:\*\*|_)?Sources?\b)(?:\bwhy[ \t]+not\b|\b(?:no|not|never|without|nor|none|nothing|don[\x27’]t|doesn[\x27’]t|didn[\x27’]t|wouldn[\x27’]t|haven[\x27’]t|isn[\x27’]t|aren[\x27’]t|won[\x27’]t|needn[\x27’]t|shouldn[\x27’]t|cannot|can[\x27’]t|skip|avoid)[ \t]+(?:[^\s;:!?]*[^\s.,;:!?][ \t]+){0,2}?(?:creat\w*|add\w*|writ\w*|missing|absent)(?:(?![ \t]+(?:and|but|while|whereas|yet)\b)[^\n.,;:!?]|[.,;:!?](?=\S))*(?=[.,;:!?]|[ \t]+(?:and|but|while|whereas|yet)\b|\n|(?![\s\S]))|(?!\b(?:no|not|never|without|nor|none|nothing|don[\x27’]t|doesn[\x27’]t|didn[\x27’]t|wouldn[\x27’]t|haven[\x27’]t|isn[\x27’]t|aren[\x27’]t|won[\x27’]t|needn[\x27’]t|shouldn[\x27’]t|cannot|can[\x27’]t|skip|avoid)[ \t]+(?:[^\s;:!?]*[^\s.,;:!?][ \t]+){0,2}?(?:creat\w*|add\w*|writ\w*|missing|absent)(?:(?![ \t]+(?:and|but|while|whereas|yet)\b)[^\n.,;:!?]|[.,;:!?](?=\S))*(?=[.,;:!?]|[ \t]+(?:and|but|while|whereas|yet)\b|\n|(?![\s\S])))[^\n])*?(?:AGENTS\.md[\x60*"]{0,2}[ \t]+(?:is|was)[ \t]+(?:missing|absent|not[ \t]+present)|AGENTS\.md[\x60*"]{0,2}[ \t]+(?:does[ \t]+not|doesn[\x27’]t|did[ \t]+not|didn[\x27’]t)[ \t]+exist|\b(?:no|missing|without)[ \t]+(?:an?[ \t]+)?[\x60*"]{0,2}AGENTS\.md[\x60*"]{0,2}(?=[ \t]*(?:[.,;:)]|\n|(?![\s\S]))|[ \t]+(?:file|exists|is[ \t]+present|in)\b)|\b(?:create|add|write)\w*[ \t]+(?:an?[ \t]+|the[ \t]+)?(?:missing[ \t]+)?[\x60*"]{0,2}AGENTS\.md)'
flags: i
match: not_contains
weight: 1
---
The repo has an `AGENTS.md` (the real file behind `CLAUDE.md`).

Must not match: a line that says `AGENTS.md` is missing, absent or not present, doesn't exist, "no/missing/without `AGENTS.md`" at the end of a clause or before file/exists/is present/in, or creates, adds or writes an `AGENTS.md`. A negated clause (a negation, up to two words, then create, add, write, missing or absent, to the end of the clause) is skipped, so "no need to create an AGENTS.md" passes while a later claim on the same line still fails; "why not" is never a negation.

Script-graded (case-insensitive). The parts, and the controls each must pass and fail, are in `tests/test_claudit_fixture_graders.py`; rebuild with `python3 tests/test_claudit_fixture_graders.py --write`. A line never counts when it is a `Source:` citation line.
