---
type: llm
weight: 1
---
The fixture has a `.claudeignore` file listing `.env`, `.env.*`, `secrets/` and `coverage/`. Claude Code does not read `.claudeignore`, so it has no effect and those files are not protected. The fixture has no `permissions.deny` rules.

PASS only if the report (1) identifies that `.claudeignore` is not honoured by Claude Code / has no effect, and (2) recommends moving its entries into `permissions.deny` rules in `.claude/settings.json`, such as `Read(./.env)`, `Read(./.env.*)` and `Read(./secrets/**)`, or removing the file. Recommending deny rules plus the sandbox for OS-level enforcement is also acceptable.

FAIL if the report treats `.claudeignore` as working, suggests adding more entries to it, or names the problem without a fix.
