---
type: regex
pattern: '^(?=[\s\S]*\.claudeignore)(?=[\s\S]*(?:\bRead\((?:\.?/|\*\*/)?(?:\.env|secrets/)|(?:\bgit rm\b|\brm\b|\b(?:remove|delete)\b)[^\n]{0,60}\.claudeignore))'
flags: i
weight: 1
---
The fixture has a `.claudeignore` file listing `.env`, `.env.*`, `secrets/` and `coverage/`. Claude Code does not read `.claudeignore`, so it has no effect and those files are not protected. The fixture has no `permissions.deny` rules.

Script-graded (case-insensitive): the report names `.claudeignore` and gives the fix, a `Read(...)` rule for one of its entries (`Read(./.env)`, `Read(.env.*)`, `Read(**/.env)`, `Read(./secrets/**)` and similar), or a line that says to remove, delete, `rm` or `git rm` the `.claudeignore`.
