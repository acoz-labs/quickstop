---
type: regex
pattern: '(?:^|\n)(?![ \t]*(?:[-*>][ \t]+)?(?:\*\*|_)?Sources?\b)(?![^\n]*(?:\bwhy[ \t]+not\b|\?(?=[ \t*_"\x60)]|\n|(?![\s\S]))))(?![^\n]*\b(?:if|unless|whether)\b)(?![^\n]*\b(?:no|not|never|without|nor|none|nothing|don[\x27’]t|doesn[\x27’]t|didn[\x27’]t|wouldn[\x27’]t|haven[\x27’]t|isn[\x27’]t|aren[\x27’]t|won[\x27’]t|needn[\x27’]t|shouldn[\x27’]t|cannot|can[\x27’]t|skip|avoid)[ \t]+(?:(?:need\w*|requir\w*|ha(?:ve|s)|us(?:e|ing)|rely(?:ing)?[ \t]+on|bother(?:ing)?[ \t]+with|add(?:ing)?|enabl\w*|set(?:ting)?[ \t]+up|configur\w*|turn(?:ing)?[ \t]+on|worth|is|are|be|any|a|an|the|for|of|to|also|really|actually|even|yet|this|that|such)[ \t]+){0,4}[\x60*"(]*(?:missing|absent|stale|outdated|wrong|incorrect|false|out[ \t]+of[ \t]+date|broken)\b)(?=[^\n]*rates\.toml)(?=[^\n]*(?:\bdo(?:es)?(?:n[\x27’]t|[ \t]+not)[ \t]+exist|\bno[ \t]+longer[ \t]+exists?|\bnon-?existent\b|\bmissing\b|\babsent\b|\bstale\b|\boutdated\b|\bout[ \t]+of[ \t]+date\b|\bwrong\b|\bincorrect\b|\bfalse\b|\bno[ \t]+such\b|\bnot[ \t]+(?:present|found|there)\b|\bnot[ \t]+in[ \t]+(?:the[ \t]+)?(?:repo\w*|tree|project|pyproject)|\bis(?:n[\x27’]t|[ \t]+not)[ \t]+(?:present|there|found|in[ \t]+)|\bnot[ \t]+(?:a[ \t]+)?(?:declared[ \t]+|listed[ \t]+|installed[ \t]+)?dependenc\w*|\b(?:is|are)(?:n[\x27’]t|[ \t]+not)[ \t]+(?:declared|listed|installed)\b|\bnot[ \t]+(?:declared|listed|installed)\b|\b(?:none|neither)\b[^\n]{0,30}\bexists?\b))[^\n]*'
flags: i
weight: 1
---
`CLAUDE.md` says carrier rates load from `config/rates.toml`; the file does not exist (rates are constants in `label.py`).

PASS when one line names `rates.toml` and says it is missing, as for `finding-stale-folder`.

Script-graded (case-insensitive). The parts, and the controls each must pass and fail, are in `tests/test_claudit_fixture_graders.py`; rebuild with `python3 tests/test_claudit_fixture_graders.py --write`. A line never counts when it is a `Source:` citation line, a question (it has "why not" or a `?` before a space or the line end), or when a negation directly governs the finding ("no ask rule is needed", "not a symlink"; a negation elsewhere on the line doesn't count) or it says the fix is already in place.
