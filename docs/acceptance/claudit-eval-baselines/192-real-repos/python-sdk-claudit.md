# Claudit: python-sdk (mcp)

**Intent:** This is the Python SDK for the Model Context Protocol (the `mcp` package). It is a typed library with a docs site and translations under `i18n/`. Work is checked with `./scripts/test` (pytest with 100% branch coverage), `ruff` and `pyright`. Releases follow `RELEASE.md` and a CI matrix. Maintainers and AI agents both contribute: `AGENTS.md` addresses agents, and `claude.yml` runs Claude Code in CI. Contribution rules are in `CONTRIBUTING.md`. Assumed from the repository; correct me if wrong.

## Grades

- **Correctness: A** (confidence: high). There is no `.claude` settings file or hook to misconfigure. The one skill and one command the scan found are well formed.
- **Alignment: A** (confidence: high). `CLAUDE.md` imports `AGENTS.md`, and both load. `AGENTS.md` holds what Claude can't learn from the repo (the `uv --frozen` rule, the coverage bar, API-stability rules) and links the procedure docs.
- **Coverage: D** (confidence: medium). Three baseline items are missing (check-command allowlist, secret deny rule, enforced check), and several procedure docs have no skill. Items 1 to 7 would raise it, plus the items under Also worth knowing.

## Top changes

7 changes are worth making. 23 more are under Also worth knowing.

1. **Pre-approve the check commands** (Coverage, effort S)
   Problem: `.claude/settings.json` doesn't exist, so there is no allow rule for `scripts/test` or `pytest`. Every run prompts for them.
   Why: Contributors run the test suite constantly, and pre-approving it removes the prompts.
   Change:
   ```json
   {"permissions": {"allow": ["Bash(scripts/test)", "Bash(pytest)"]}}
   ```
   `AGENTS.md` tells agents to run `uv run --frozen pytest`. The scan only suggested the two rules above, so consider adding `Bash(uv run --frozen pytest:*)` as well.
   Source: [Permission rule syntax](https://code.claude.com/docs/en/permissions)

2. **Add a skill for docs/client/identity-assertion.md** (Coverage, effort M)
   Problem: The 5-step procedure in `docs/client/identity-assertion.md` has no skill and is not linked from `AGENTS.md`.
   Why: A skill lets Claude load the procedure on demand when it works on identity assertion.
   Change: Create `.claude/skills/identity-assertion/SKILL.md` with `name` and `description` frontmatter that follows the doc's steps. Keep the doc as the source and link it.
   Source: [Put team procedures in skills](https://code.claude.com/docs/en/best-practices)

3. **Add a skill for docs/whats-new.md** (Coverage, effort M)
   Problem: The 15-step `docs/whats-new.md` has no skill and is not linked from `AGENTS.md`.
   Why: Same as item 2.
   Change: Create `.claude/skills/whats-new/SKILL.md` with `name` and `description` frontmatter that follows the doc's steps. Keep the doc as the source and link it.
   Source: [Put team procedures in skills](https://code.claude.com/docs/en/best-practices)

4. **Add a skill for i18n/de/pages/client/identity-assertion.md** (Coverage, effort M)
   Problem: The German translation of the identity-assertion page has no skill.
   Why: Same as item 2. The scan lists this translation as a separate procedure.
   Change: Create `.claude/skills/identity-assertion/SKILL.md` that follows the steps in `i18n/de/pages/client/identity-assertion.md`. This is the same skill path as item 2, so I suggest the translation point back to the English skill instead of being a separate one.
   Source: [Put team procedures in skills](https://code.claude.com/docs/en/best-practices)

5. **Add a skill for i18n/de/pages/whats-new.md** (Coverage, effort M)
   Problem: The German translation of the what's-new page has no skill.
   Why: Same as item 3.
   Change: Create `.claude/skills/whats-new/SKILL.md` that follows the steps in `i18n/de/pages/whats-new.md`. This is the same skill path as item 3, so the same caveat applies.
   Source: [Put team procedures in skills](https://code.claude.com/docs/en/best-practices)

6. **Add a skill for i18n/es/pages/client/identity-assertion.md** (Coverage, effort M)
   Problem: The Spanish translation of the identity-assertion page has no skill.
   Why: Same as item 2.
   Change: Create `.claude/skills/identity-assertion/SKILL.md` that follows the steps in `i18n/es/pages/client/identity-assertion.md`. This is the same skill path as item 2.
   Source: [Put team procedures in skills](https://code.claude.com/docs/en/best-practices)

7. **Add a skill for i18n/es/pages/whats-new.md** (Coverage, effort M)
   Problem: The Spanish translation of the what's-new page has no skill.
   Why: Same as item 3.
   Change: Create `.claude/skills/whats-new/SKILL.md` that follows the steps in `i18n/es/pages/whats-new.md`. This is the same skill path as item 3.
   Source: [Put team procedures in skills](https://code.claude.com/docs/en/best-practices)

Items 4 to 7 are mostly translation duplicates of items 2 and 3. I kept them as the scan gave them, and you can dismiss them.

## Also worth knowing

- **Deny reads of secret paths.** `.env` is gitignored but not covered by a deny rule. Add `{"permissions": {"deny": ["Read(./.env)"]}}` to `.claude/settings.json`. [Read and Edit](https://code.claude.com/docs/en/permissions)
- **Enforce the check with a Stop hook.** The `uv run --frozen` rule (`AGENTS.md:35`) is prose only. The scan suggests a Stop hook at `.claude/hooks/stop-check.sh` that runs `scripts/test` and exits 2 on failure. The suite takes about 23s, so a hook on every stop may be heavy here. [Enforce the check with a Stop hook](https://code.claude.com/docs/en/best-practices)
- **Install a code-intelligence plugin.** The project uses pyright, so install `python-lsp` from the official marketplace (check `/plugin` for the exact name). [Code intelligence plugins](https://code.claude.com/docs/en/plugins/code-intelligence)
- **Optional skills for the linked procedure docs.** All three are linked from the loaded `AGENTS.md`, so a skill is optional:
  - `CONTRIBUTING.md`, as `.claude/skills/contributing/SKILL.md`
  - `RELEASE.md`, as `.claude/skills/release/SKILL.md`
  - `docs/migration.md`, as `.claude/skills/migration/SKILL.md`. `AGENTS.md` says this file is closed to new entries, so a skill adds little.
  
  [Put team procedures in skills](https://code.claude.com/docs/en/best-practices)
- **Skills for the other translations.** The remaining 18 translation skills (fr, hi, ja, ko, pt, ru, tr, uk, zh-hant and zh, each for `whats-new.md` and `client/identity-assertion.md`) are low value, because the translations mirror the English pages.
- **Native checks.** `/doctor prompt-audit` is worth running on the 166-line `AGENTS.md`. `/doctor` will show unused skills and slow hooks, and `/insights` will show recurring friction.

---
Claudit 4.2.0; audited commit af4c6f4db2cd207f44374cd324a12cfbee8d2da6
Claude Code 2.1.317; catalog 2026-10-29
Docs: index read live; no new pages since the last assessment
Scope: project only; user settings, managed settings, `~/.claude.json` and installed plugins were not inspected
Read-only run: nothing was written
