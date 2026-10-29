---
type: llm
weight: 1
---
The fixture's `CLAUDE.md` is about 240 lines, well over the recommended 200-line target, and almost all of it restates the source code function by function (arguments, checks, error messages, examples). Only a few lines carry information the code cannot: the commands (`npm test`, `npm run lint`), Node 20+/ESM, "never store money as a float", "no runtime dependencies", "add a test before changing a tax rate".

PASS only if the report (1) identifies that CLAUDE.md is too long (over ~200 lines) and that it mostly duplicates what the code already says, and (2) recommends cutting it down to what the code can't tell Claude (commands, conventions, rules, gotchas), deleting the function-by-function descriptions or moving any detail worth keeping out of CLAUDE.md (into code comments, a skill, or path-scoped `.claude/rules/`). Splitting it into `@imports` is acceptable only alongside cutting the restated content, since imported files still load into context.

FAIL if the report only says the file is long without noting the code restatement, only suggests reorganising or importing the same content, or does not recommend trimming it.
