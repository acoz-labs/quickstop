---
type: regex
pattern: '(?:^|\n)[ \t]*\|(?=[^\n]*\b(?:words?|tokens?)\b)[^\n]*\|[ \t]*\n[ \t]*\|?[ \t]*:?-{3,}[^\n]*(?=(?:\n[ \t]*\|[^\n]*)*?\n[ \t]*\|(?=[^\n]*CLAUDE\.md)(?=[^\n]*\b[0-9])[^\n]*)(?=(?:\n[ \t]*\|[^\n]*)*?\n[ \t]*\|(?=[^\n]*architecture\.md)(?=[^\n]*\b[0-9])[^\n]*)'
flags: i
weight: 1
---
`CLAUDE.md` is 10 lines but about 610 words, because its lines are long, and it imports `@docs/architecture.md` (about 415 words), so about 1,000 words load every session.

PASS when the report has a Markdown table whose header names words or tokens, with a row naming `CLAUDE.md` and a row naming `architecture.md`, each holding a number. The numbers themselves are not checked.

Script-graded (case-insensitive). The parts, and the controls each must pass and fail, are in `tests/test_claudit_fixture_graders.py`; rebuild with `python3 tests/test_claudit_fixture_graders.py --write`. A line never counts when it is a `Source:` citation line, a question (it has "why not" or a `?` before a space or the line end), or when a negation directly governs the finding ("no ask rule is needed", "not a symlink"; a negation elsewhere on the line doesn't count) or it says the fix is already in place.
