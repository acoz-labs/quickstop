---
type: regex
pattern: '^(?=[\s\S]*(?:(?:\bno\b|\bnot\b|n[\x27’]t\b|\bwithout\b|\bmissing\b|\black\w*|\babsent\b|\bnothing\b|\bnever\b|\bnone\b)(?:[^\n.!?;]|[.!?](?=\S)){0,80}?(?:\x60?evals/\x60?|\bevals?\b(?!\x60)|\beval(?:uation)? (?:suite|cases?|directory)\b|\bevaluat\w*)|(?:\x60?evals/\x60?|\bevals?\b(?!\x60)|\beval(?:uation)? (?:suite|cases?|directory)\b|\bevaluat\w*)(?:[^\n.!?;]|[.!?](?=\S)){0,60}?(?:\bno\b|\bnot\b|n[\x27’]t\b|\bwithout\b|\bmissing\b|\black\w*|\babsent\b|\bnothing\b|\bnever\b|\bnone\b)))(?=[\s\S]*(?:(?:\brun\w*|\buse\b|\badd\w*|\bwire\b|\bcall\b|\binvoke\b|\bgate\b|\bCI\b|\bdocument\w*|\brecord\w*)(?:(?!\n[ \t]*\n(?=\S)|\n(?=[0-9]+[.)][ \t]|#|[-*+][ \t]))[\s\S]){0,80}?\x60?claude plugin eval\b(?!uat)|\x60?claude plugin eval\b(?!uat)(?:(?!\n[ \t]*\n(?=\S)|\n(?=[0-9]+[.)][ \t]|#|[-*+][ \t]))[\s\S]){0,80}?(?:\brun\w*|\buse\b|\badd\w*|\bwire\b|\bcall\b|\binvoke\b|\bgate\b|\bCI\b|\bdocument\w*|\brecord\w*)))'
flags: i
weight: 1
---
The fixture ships a Claude Code plugin whose only automated checks are Python unit tests of the skill's helper script. There is no eval suite (no `evals/` directory, no `experimental.evals` in `plugin.json`) and nothing runs `claude plugin eval`, so nobody measures whether Claude actually picks up and follows the `changelog-entry` skill.

Script-graded (case-insensitive). Two things are needed:
- Evals named as missing: one sentence (running to `.`, `!`, `?` or `;` followed by a space, or a line break) has "no", "not", "n't", "without", "missing", lack..., "absent", "nothing", "never" or "none" and, within 80 characters after it (or 60 before it), `evals/`, "eval(s)" (but not the backticked command), "eval/evaluation suite/case(s)/directory" or evaluat....
- `claude plugin eval` recommended: one change item has run..., "use", add..., "wire", "call", "invoke", "gate", "CI", document... or record... within 80 characters of `claude plugin eval` (either order; `claude plugin evaluate` doesn't count). A change item ends where a blank line is followed by a column-0 line, or at a column-0 numbered item, `#` heading or `-`/`*`/`+` bullet, so an item's title, Problem, Why and Change lines and its fenced blocks are one unit.

Only naming the command, only recommending unit tests, or only saying evals are missing fails.
