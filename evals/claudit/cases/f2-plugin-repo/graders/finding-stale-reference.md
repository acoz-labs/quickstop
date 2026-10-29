---
type: llm
weight: 1
---
The fixture's CLAUDE.md tells Claude to "see docs/architecture.md before changing" the skill, script or marketplace entry, but `docs/architecture.md` does not exist (the only file in `docs/` is `docs/style.md`).

PASS only if the report (1) identifies that CLAUDE.md references `docs/architecture.md` and that this file does not exist, and (2) recommends fixing the reference: either remove it, point it at an existing file, or write the missing `docs/architecture.md`.

FAIL if the report does not name `docs/architecture.md` as missing, or names it without saying what to do about it.
