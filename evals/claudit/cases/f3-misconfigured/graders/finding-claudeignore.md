---
type: regex
pattern: '^(?=[\s\S]*(?:\.claudeignore[^\n]{0,200}(?:\bnot\b|n[\x27’]t\b|\bno effect\b|\bnothing\b|\bignor\w*|\bunsupported\b|\bnever\b|\bunused\b|\bno such\b|\bisn\w*t a\b|\binstead of\b|\breplac\w*|\bhas no\b)|(?:\bnot\b|n[\x27’]t\b|\bno effect\b|\bnothing\b|\bignor\w*|\bunsupported\b|\bnever\b|\bunused\b|\bno such\b|\bisn\w*t a\b|\binstead of\b|\breplac\w*|\bhas no\b)[^\n]{0,200}\.claudeignore))(?=[\s\S]*(?:\bRead\((?:\.?/|\*\*/|//[^)\n]*?/)?(?:\.env|secrets/)|(?:\bgit rm\b|\brm\b|\b(?:remove|delete)\b)[^\n]{0,60}\.claudeignore))'
flags: i
weight: 1
---
The fixture has a `.claudeignore` file listing `.env`, `.env.*`, `secrets/` and `coverage/`. Claude Code does not read `.claudeignore`, so it has no effect and those files are not protected. The fixture has no `permissions.deny` rules.

Script-graded (case-insensitive). The diagnosis: one line has `.claudeignore` within 200 characters (either order) of "not", "n't", "no effect", "nothing", ignor..., "unsupported", "never", "unused", "no such", "isn't a", "instead of" or replac.... The fix: a `Read(` rule, optionally with `./`, `/`, `**/` or a `//…/` absolute prefix, for `.env` or `secrets/`; or remove, delete, `rm` or `git rm` within 60 characters before `.claudeignore`. Both are needed.
