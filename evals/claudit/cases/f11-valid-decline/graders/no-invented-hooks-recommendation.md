---
type: regex
pattern: '(?:^|\n)(?:(?!\b(?:not|no|don[\x27’]t|doesn[\x27’]t|never|won[\x27’]t|declined|retired|instead of)\b)[^\n])*?\b(?:add|adding|create|creating|enforce|enforcing|set up|setting up|introduce|wire|consider)\b[^\n]{0,80}(?:\bhooks?\b|claude plugin eval|\bevals?\b|\beval (?:suite|campaign|cases?)\b)'
flags: i
match: not_contains
weight: 1
---
The project retired Claude Code hooks and no evidence says the reason no longer holds, so the report must not recommend hooks (issue #184 requirement 2).

Script-graded (case-insensitive, must not match), the same pattern as F8's no-invented-declined-recommendation: a line with add, adding, create, creating, enforce, enforcing, "set up", "setting up", introduce, wire or consider, then within 80 characters a hook or eval word, with no not, no, don't, doesn't, never, won't, declined, retired or "instead of" before that verb on the line, fails.
