# Claudit: invoicer

**Intent:** invoicer is a small, dependency-free Node 20+ ESM library that builds, totals and renders plain-text invoices. Amounts are integer cents. Work is checked with `npm test` and `npm run lint`. There is no CI. A person drives it with Claude interactively. Assumed from the repository; correct me if wrong.

## Grades

- **Correctness: D** (confidence: high). The scan found three high findings and two mediums. The hook matcher is a list, so the lint hook doesn't load as written. `.claudeignore` is not read. `Write(src/**)` never matches. The release-notes skill is a flat file, so it never loads.
- **Alignment: C** (confidence: high). `CLAUDE.md` is 241 lines, and most of it repeats what the source files already say. The one rule that needs the skill, "Use the release-notes skill", points at a skill that can't load.
- **Coverage: C** (confidence: high). Two of the five baseline items are not fully met. There is no secret deny rule, and the instructions file is oversized. Tests, lint and the allowlist are in place.

## Top changes

6 changes are worth making.

1. **Fix the PostToolUse hook matcher** (Correctness, effort S)
   Problem: In `.claude/settings.json`, the PostToolUse matcher is the list `["Edit", "Write"]`. A matcher must be a string, so the lint-after-edit hook doesn't run as written.
   Why: Running the linter after every edit is how this project catches tabs, trailing whitespace and `console.log` early.
   Change:
   ```json
   "matcher": "Edit|Write"
   ```
   Source: [Check hooks](https://code.claude.com/docs/en/debug-your-config)

2. **Deny secret paths and delete `.claudeignore`** (Correctness and Coverage, effort S)
   Problem: `.claudeignore` lists `.env`, `.env.*` and `secrets/`, but Claude Code doesn't read that file. `.claude/settings.json` has no `deny` rules, so Claude can read all three paths.
   Why: Protecting secrets is a baseline item for any project.
   Change:
   ```json
   {"permissions": {"deny": ["Read(./.env)", "Read(./.env.*)", "Read(./secrets/**)"]}}
   ```
   Then run `git rm .claudeignore`.
   Source: [Read and Edit](https://code.claude.com/docs/en/permissions)

3. **Remove `defaultMode: "bypassPermissions"` from project settings** (Correctness, effort S)
   Problem: `.claude/settings.json` line 3 sets `bypassPermissions`. Current Claude Code ignores this from project settings. On versions before 2.1.257 it applied to everyone who opened the repo, which skips all prompts.
   Why: Safety rules shouldn't depend on which Claude Code version a contributor runs.
   Change: Delete the `"defaultMode"` line. Anyone who wants it can set it in `~/.claude/settings.json`.
   Source: [A value you set is ignored](https://code.claude.com/docs/en/settings)

4. **Move the release-notes skill into a skill directory** (Correctness, effort S)
   Problem: `.claude/skills/release-notes.md` is a flat file. Skills load only from `<name>/SKILL.md`, so `CLAUDE.md`'s "Use the release-notes skill" instruction does nothing.
   Why: Release notes are a documented procedure in this project.
   Change:
   ```sh
   mkdir .claude/skills/release-notes
   git mv .claude/skills/release-notes.md .claude/skills/release-notes/SKILL.md
   ```
   Then add `name: release-notes` and a `description:` to the frontmatter.
   Source: [Choose where skills load](https://code.claude.com/docs/en/skills)

5. **Trim `CLAUDE.md` from 241 lines to about 30** (Alignment, effort M)
   Problem: Lines 12 to 234 describe each function's body in prose. Claude can read that from the five short source files, and it goes stale as the code changes. The file also opens with "Read all of it before making any change".
   Why: Long instructions dilute the few rules that matter.
   Change: Keep only these:
   - Commands: `npm test`, `npm run lint`, and Node 20+ with ESM.
   - Rules: money is integer cents, convert with `toCents` at the boundary, no runtime dependencies, add a test first when changing a tax rate, and use the release-notes skill.
   - The two non-obvious facts: tax rates are basis points, and discounts are applied pro rata before tax.

   Delete the per-file and per-function sections and the layout list. After trimming, `/doctor prompt-audit` can check what remains.
   Source: [Write effective instructions](https://code.claude.com/docs/en/memory)

6. **Change `Write(src/**)` to `Edit(src/**)`** (Correctness, effort S)
   Problem: The allow rule `Write(src/**)` never matches, so edits under `src/` still prompt.
   Why: Edits to `src/` are the routine work here.
   Change:
   ```json
   "Edit(src/**)"
   ```
   Source: [`Write(path)`, `NotebookEdit(path)`, and `Glob(path)` rules never match](https://code.claude.com/docs/en/permissions)

## Also worth knowing

- Optional: add a Stop hook that runs `npm test`, if you want the check enforced and not only documented. There are no "must run" rules today.
- Optional: add a small GitHub Actions workflow that runs `npm test` and `npm run lint`. There is no CI now.
- Optional: run `/insights` after a few weeks to find recurring friction.

---
Claude Code 2.1.314; catalog 2026-10-29.
Docs read live: the docs index only. Nothing new since the last assessment.
Scope: project only. User and managed settings, `~/.claude.json` and installed plugins were not inspected.
Read-only run, so nothing was written.