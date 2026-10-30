# Claudit: invoicer

**Intent:** invoicer is a small ESM Node 20+ library for building, totalling and rendering plain-text invoices, with amounts held as integer cents. Work is checked with `npm test` (node --test) and `npm run lint`. A person drives it in interactive sessions, and there is no CI. The one project skill drafts release notes. Assumed from the repository; correct me if wrong.

## Grades

- **Correctness: D** (confidence: high). Three high findings: the `.claudeignore` file isn't read, the hook matcher is a list instead of a string, and `defaultMode` is set to bypass. There are also two mediums: a flat skill file and a `Write(...)` rule that never matches.
- **Alignment: C** (confidence: high). `CLAUDE.md` is 241 lines and mostly restates what the code shows, such as per-function walkthroughs of `src/`. The release-notes skill fits how releases are done, but it never loads.
- **Coverage: C** (confidence: high). Two baseline items are not fully met: the secrets baseline is missing because nothing is denied, and the instructions item is only partial. The check and allowlist items are met.

## Top changes

6 changes are worth making.

1. **Fix the hook matcher** (Correctness, effort S)
   Problem: `.claude/settings.json` sets the PostToolUse `matcher` to the list `["Edit", "Write"]`. A matcher must be a string, so the lint-after-edit hook is dropped.
   Why: The lint hook is the only automatic check on edits to this library.
   Change:
   ```json
   "matcher": "Edit|Write"
   ```
   Source: [Check hooks](https://code.claude.com/docs/en/debug-your-config)

2. **Deny secret reads and delete `.claudeignore`** (Correctness and Coverage, effort S)
   Problem: `.claudeignore` has 3 secret-like entries, but Claude Code doesn't read it. No `permissions.deny` rule covers `.env`, `.env.*` or `secrets/`, so those paths are unprotected.
   Why: The project's secrets protection is currently missing.
   Change:
   ```json
   {"permissions": {"deny": ["Read(./.env)", "Read(./.env.*)", "Read(./secrets/**)"]}}
   ```
   Then run `git rm .claudeignore`.
   Source: [Read and Edit](https://code.claude.com/docs/en/permissions)

3. **Remove `defaultMode: "bypassPermissions"`** (Correctness, effort S)
   Problem: `.claude/settings.json` line 3 sets bypass mode. Since 2.1.257 Claude Code ignores this value in project settings, so it does nothing. Before that version it applied bypass to everyone who opened the repo.
   Why: The setting is dead on current versions and risky on older ones.
   Change: Delete the `"defaultMode"` line. Anyone who wants bypass can set it in `~/.claude/settings.json`.
   Source: [A value you set is ignored](https://code.claude.com/docs/en/settings)

4. **Move the release-notes skill into a skill directory** (Correctness, effort S)
   Problem: `.claude/skills/release-notes.md` is a flat file. Skills load only from `<name>/SKILL.md`, so it never loads.
   Why: It encodes the project's release flow.
   Change:
   ```sh
   mkdir .claude/skills/release-notes && git mv .claude/skills/release-notes.md .claude/skills/release-notes/SKILL.md
   ```
   Source: [Choose where skills load](https://code.claude.com/docs/en/skills)

5. **Replace `Write(src/**)` with `Edit(src/**)`** (Correctness, effort S)
   Problem: `Write(path)` rules never match, so edits under `src/` still prompt.
   Why: Editing `src/` is the main workflow, and this rule was meant to stop those prompts.
   Change:
   ```json
   "Edit(src/**)"
   ```
   Source: [`Write(path)`, `NotebookEdit(path)`, and `Glob(path)` rules never match](https://code.claude.com/docs/en/permissions)

6. **Cut `CLAUDE.md` to what the repo doesn't already say** (Alignment, effort M)
   Problem: `CLAUDE.md` is 241 lines. Most of it is function-by-function narration of five small files, plus a file listing. Claude can read all of that from the code, and the length dilutes the few real rules.
   Why: Short instructions get followed more reliably.
   Change: Keep roughly this, about 15 lines:
   ```md
   # invoicer
   Small ESM library (Node 20+). Amounts are integer cents everywhere.
   - Test: `npm test`; lint: `npm run lint`. Run both before finishing.
   - Entry point `src/index.js` re-exports everything; add new exports there.
   ```
   Source: [Write effective instructions](https://code.claude.com/docs/en/memory)

## Also worth knowing

- Once the matcher is fixed, you could add a Stop hook that runs `npm test`. This is optional and would make the test check automatic.
- `/doctor prompt-audit` can check the trimmed `CLAUDE.md` afterwards.

---
Claude Code 2.1.314; catalog 2026-10-29.
Docs: index read live, with no new pages since the last assessment.
Scope: project only. User settings, managed settings, `~/.claude.json` and plugins were not inspected.
Read-only run: nothing was changed.