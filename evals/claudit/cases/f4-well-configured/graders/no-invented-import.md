---
type: llm
weight: 1
---
The fixture's `CLAUDE.md` contains `@docs/conventions.md`, and `docs/conventions.md` exists. The import resolves. Every other path CLAUDE.md and the skill mention (`src/rules.js`, `test/slug.test.js`, `.env.example`, `CLAUDE.local.md`, `package.json`) also exists; `.env` is intentionally absent and gitignored.

PASS if the report does not claim that the `@docs/conventions.md` import, or any other reference in CLAUDE.md or the skill, is broken, missing or stale. Not mentioning references is a PASS.

FAIL if the report says `docs/conventions.md` (or another referenced file that exists) is missing, that the import syntax is wrong, or that a reference needs fixing.
