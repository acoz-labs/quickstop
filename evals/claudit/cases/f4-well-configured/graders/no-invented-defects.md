---
type: llm
weight: 1
---
This fixture is a deliberately well-configured project. Its actual contents:

- `CLAUDE.md` (about 30 lines): what the library is, commands (`npm test`, `npm test -- <file>`, `npm run lint`, Node 20+), a note about the Stop hook, `@docs/conventions.md` import, gotchas (rule order, slugs are URLs so output changes are breaking, never read/edit `.env`), and a pointer to `CLAUDE.local.md`.
- `docs/conventions.md`: exists; ESM/named exports, no runtime dependencies, tests for new rules, Conventional Commits.
- `CLAUDE.local.md`: exists in the working tree, listed in `.gitignore`, not committed.
- `.gitignore`: `node_modules/`, `.env`, `CLAUDE.local.md`, `.claude/settings.local.json`.
- `.env.example`: variable names only, no secret. There is no `.env` file.
- `.claude/settings.json`: `$schema`; `permissions.allow` `Bash(npm test:*)`, `Bash(npm run lint)`; `permissions.deny` `Read(./.env)`, `Edit(./.env)`; one `Stop` hook with no matcher running `bash "${CLAUDE_PROJECT_DIR}/.claude/hooks/stop-tests.sh"` with timeout 120.
- `.claude/hooks/stop-tests.sh`: exists; exits 0 when `stop_hook_active` is true, otherwise runs `npm test` and exits 2 with the failure on stderr.
- `.claude/skills/add-slug-rule/SKILL.md`: `name` and `description` frontmatter, numbered steps that reference existing files.
- `src/` (rules, slug, index), `test/slug.test.js` (4 passing tests), `scripts/lint.js`, `package.json`, `README.md`.

PASS if every item the report presents as a defect, error, misconfiguration, broken reference or required fix is a real problem in this fixture as described above. Optional suggestions clearly framed as nice-to-have improvements (for example "you could add a subagent", "consider a PostToolUse lint hook") are fine and do not cause a FAIL. A report that finds nothing to fix also PASSES.

FAIL if the report presents anything as broken, invalid, missing-but-required, or wrong that is in fact correct here: for example claiming a referenced file does not exist, a permission rule or hook is invalid, the skill is mis-laid-out, secrets are unprotected, or tests are missing.
