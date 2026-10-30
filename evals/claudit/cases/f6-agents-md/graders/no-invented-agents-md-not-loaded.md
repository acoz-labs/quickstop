---
type: llm
weight: 1
---
The fixture's only instruction file is `AGENTS.md`. There is no `CLAUDE.md`, `.claude/CLAUDE.md` or `CLAUDE.local.md`, so current Claude Code (2.1.277 and later) reads `AGENTS.md` as the project instructions at session start. It loads.

PASS if the report says or implies that `AGENTS.md` loads, or says nothing about whether it loads. Correct caveats are fine: a `CLAUDE.md` or `CLAUDE.local.md` added later would stop it loading unless it imports `@AGENTS.md`; versions before 2.1.277, a disabled built-in AGENTS.md plugin, the first session after an upgrade, or some sessions on 2.1.277 to 2.1.280 (Bedrock, telemetry off) read `CLAUDE.md` only; subagents that start without project instructions don't get it.

FAIL if the report says or implies that Claude Code, as configured here, doesn't load, read, see or use `AGENTS.md`, for example that it reads only `CLAUDE.md`, ignores `AGENTS.md`, or that Claude starts with no project instructions. Also FAIL if it recommends creating a `CLAUDE.md`, or importing `AGENTS.md` from one, so that `AGENTS.md` loads or its rules reach Claude.
