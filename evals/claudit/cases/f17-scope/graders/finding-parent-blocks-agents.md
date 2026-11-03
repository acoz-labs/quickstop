---
type: regex
pattern: '(?:^|\n)(?![ \t]*(?:[-*>][ \t]+)?(?:\*\*|_)?Sources?\b)(?![^\n]*(?:\bwhy[ \t]+not\b|\?(?=[ \t*_"\x60)]|\n|(?![\s\S]))))(?![^\n]*\b(?:does(?:n[\x27’]|[ \t]+not)|won[\x27’]|will[ \t]+not|never|can[\x27’]|cannot|wouldn[\x27’]|would[ \t]+not)[ \t]+(?:\S+[ \t]+)?(?:stop|prevent|block|shadow|suppress|override|mask|affect))(?=[^\n]*(?:\bparent\b|\babove\b|\benclosing\b|\bancestor\w*|\boutside[ \t]+(?:the[ \t]+|this[ \t]+)?(?:repo\w*|project|checkout)|\bcontaining[ \t]+(?:folder|directory)|\.\./|\bhome[ \t]+(?:folder|directory)|~/(?:CLAUDE|AGENTS)\.md|\bup[ \t]+the[ \t]+tree|\bhigher[ \t]+up\b))(?=[^\n]*CLAUDE\.md)(?=[^\n]*AGENTS\.md)(?=[^\n]*(?:\bstops?\b|\bstopping\b|\bprevents?\b|\bblocks?\b|\bshadows?\b|\bsuppress\w*|\boverrid\w*|\bmasks?\b|\b(?:isn[\x27’]t|aren[\x27’]t|won[\x27’]t[ \t]+be|wouldn[\x27’]t[ \t]+be|will[ \t]+not[ \t]+be|would[ \t]+not[ \t]+be|is[ \t]+not|are[ \t]+not|not|never)[ \t]+(?:\S+[ \t]+)?(?:read|loaded|picked[ \t]+up|used)\b|\bno[ \t]+longer[ \t]+(?:read|loaded)\b|\bignored\b|\bskipped\b|\binstead[ \t]+of\b))[^\n]*'
flags: i
weight: 1
---
Claude Code reads `AGENTS.md` directly only when no `CLAUDE.md` loads, and a `CLAUDE.md` in a parent folder counts, so for anyone who has this parent the repo's `AGENTS.md` isn't read on its own (issue #192 F13).

PASS when one line names the parent (as in `finding-parent-noted`), `CLAUDE.md`, `AGENTS.md` and the effect (stops, prevents, blocks, shadows, suppresses, overrides, masks, isn't / won't be / never read, loaded or used, no longer read, ignored, skipped, instead of), unless it says the parent does not (won't, never, can't) stop, prevent, block or affect it.

Script-graded (case-insensitive). The parts, and the controls each must pass and fail, are in `tests/test_claudit_fixture_graders.py`; rebuild with `python3 tests/test_claudit_fixture_graders.py --write`. A line never counts when it is a `Source:` citation line, a question (it has "why not" or a `?` before a space or the line end), or when a negation directly governs the finding ("no ask rule is needed", "not a symlink"; a negation elsewhere on the line doesn't count) or it says the fix is already in place.
