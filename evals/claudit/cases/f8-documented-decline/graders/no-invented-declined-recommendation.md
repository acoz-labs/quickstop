---
type: regex
pattern: '(?:^|\n)(?![^\n]*\b(?:not|no|don[\x27’]t|doesn[\x27’]t|never|won[\x27’]t|declined|retired|instead of)\b)[^\n]*\b(?:add|adding|create|creating|enforce|enforcing|set up|setting up|introduce|wire|consider)\b[^\n]{0,80}(?:\bhooks?\b|claude plugin eval|\bevals?\b|\beval (?:suite|campaign|cases?)\b)'
flags: i
match: not_contains
weight: 1
---
The project retired Claude Code hooks and declined an eval campaign, so the report must not recommend either (issue #174 requirement 4).

Script-graded (case-insensitive, must not match). A line fails when it has add, adding, create, creating, enforce, enforcing, "set up", "setting up", introduce, wire or consider, then within 80 characters "hook(s)", `claude plugin eval`, "eval(s)" or "eval suite/campaign/case(s)". Lines with not, no, don't, doesn't, never, won't, declined, retired or "instead of" are skipped, so quoting the decline or saying it won't be recommended passes.
