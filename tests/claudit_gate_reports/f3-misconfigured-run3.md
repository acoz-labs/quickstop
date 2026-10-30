# Claudit: invoicer

**Intent:** invoicer is a small ESM Node 20+ library for building, totalling and rendering plain-text invoices, with integer-cent amounts. Work is checked with `npm test` (`node --test`) and `npm run lint` (`scripts/lint.js`). There is no CI. A person drives it with Claude interactively, and a release-notes skill drafts changelog entries. Assumed from the repository; correct me if wrong.

## Grades

- **Correctness: F** (confidence: high). The lint hook's matcher is a list, so the hook is dropped. The `Write(src/**)` rule never matches, the release-notes skill sits where it can't load, and `.claudeignore` is not read.
- **Alignment: C** (confidence: high). CLAUDE.md runs 241 lines and mostly restates what the five small source files already show. The skill and hook that fit how work is done are both broken.
- **Coverage: C** (confidence: high). Secret paths have no deny rule, so the secrets baseline item is missing. The instructions item is only partial. The other baseline items are met.

## Top changes

6 changes are worth making.

1. **Fix the hook matcher so the lint hook loads** (Correctness, effort S)
   Problem: `.claude/settings.json` line 11 gives `PostToolUse` a matcher of `["Edit", "Write"]`, which is a list. Hook matchers must be strings, so the lint-after-edit hook is dropped and never runs.
   Why: the project's check is `npm run lint`, and this hook is the only thing that runs it automatically after edits.
   Change:
   ```json
   "matcher": "Edit|Write"
   ```
   Source: [Check hooks](https://code.claude.com/docs/en/debug-your-config)

2. **Deny reads of secret paths and remove `.claudeignore`** (Coverage, effort S)
   Problem: `.claudeignore` lists `.env`, `.env.*` and `secrets/`, but Claude Code doesn't read that file. No `permissions.deny` rule covers those paths, so Claude can read them.
   Why: a deny rule is the mechanism that actually keeps secrets out of context.
   Change:
   ```json
   "deny": ["Read(./.env)", "Read(./.env.*)", "Read(./secrets/**)"]
   ```
   Then run `git rm .claudeignore`.
   Source: [Read and Edit](https://code.claude.com/docs/en/permissions)

3. **Remove `defaultMode: bypassPermissions` from project settings** (Correctness, effort S)
   Problem: `.claude/settings.json` line 3 sets `bypassPermissions`. Since 2.1.257 Claude Code ignores this value in project settings. On earlier versions it skipped all permission prompts for anyone who opened the repo.
   Why: the value does nothing on current versions, and it is unsafe on older ones. Anyone who wants it can set it in their user settings.
   Change: delete the `"defaultMode": "bypassPermissions",` line.
   Source: [A value you set is ignored](https://code.claude.com/docs/en/settings)

4. **Replace `Write(src/**)` with `Edit(src/**)`** (Correctness, effort S)
   Problem: `Write(path)` allow rules never match, so edits under `src/` still prompt.
   Why: `Edit(src/**)` is the rule type that covers file writes in `src/`.
   Change:
   ```json
   "Edit(src/**)"
   ```
   Source: [`Write(path)`, `NotebookEdit(path)`, and `Glob(path)` rules never match](https://code.claude.com/docs/en/permissions)

5. **Move the release-notes skill into a skill directory** (Correctness, effort S)
   Problem: `.claude/skills/release-notes.md` is a flat file. Skills load only from `<name>/SKILL.md`, so the skill never loads. It already has valid frontmatter.
   Why: the skill covers the project's release flow.
   Change:
   ```sh
   mkdir .claude/skills/release-notes && git mv .claude/skills/release-notes.md .claude/skills/release-notes/SKILL.md
   ```
   Source: [Choose where skills load](https://code.claude.com/docs/en/skills)

6. **Cut CLAUDE.md to under 200 lines** (Alignment, effort M)
   Problem: CLAUDE.md is 241 lines. It documents each function's behaviour step by step (for example `toCents` and `formatCents`), and Claude can read that from the code. It also starts with "Read all of it before making any change."
   Why: long instructions use context and bury the few things the repo doesn't show. Keep the commands, the Node 20+ and ESM-only constraint, and the integer-cents convention. Drop the per-function walkthroughs and the file listing.
   Change: reduce CLAUDE.md to roughly 20 lines (title, commands, conventions). Run `/doctor prompt-audit` afterwards to check it.
   Source: [Write effective instructions](https://code.claude.com/docs/en/memory)

## Also worth knowing

- Optional: once the settings are valid, add a Stop hook that runs `npm test`, if you want tests enforced rather than only allowed.
- Optional: add a GitHub Actions workflow that runs `npm test` and `npm run lint`, since there is no CI.
- Optional: run `/insights` after some use to find recurring friction.

---
Claude Code 2.1.314; catalog 2026-10-29.
Docs: index read live; no new pages since the last assessment.
Scope: project only. User settings, managed settings, `~/.claude.json` and installed plugins were not inspected.
Read-only run: nothing was changed.