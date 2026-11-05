# Maintaining the writing kit

Notes for package maintainers working in the source repository. This file is not part of the automatically loaded output style or skill bodies.

## Adding a reference

The 3 shipped references (workflow artifacts, questions, the cold-reader check) are the ones carrying mechanisms rather than taste. Candidates for later references are code comments, PR descriptions, commit messages, review comments, chat and tickets.

When adding one, update all of these together:

- the new file under `skills/writing-style/references/`
- the `writing-style` references table, its argument hint and its description
- the `writing-audit` surface table

## Keep every path real

Never leave a path in a skill table for a file that doesn't exist. A broken pointer reads as "load this" and fails silently when the read comes back empty. `tests/test_writing_kit.py` checks that every referenced path resolves inside the package.
