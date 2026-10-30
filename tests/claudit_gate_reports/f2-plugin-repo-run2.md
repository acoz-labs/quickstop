# Claudit: changelog-helper

**Intent:** This repo ships the `changelog-helper` Claude Code plugin and its marketplace entry. The plugin has one skill, `skills/changelog-entry/`, which drafts Keep a Changelog entries from commits using a standard-library Python script. Work is checked with `python3 -m unittest discover -s tests`, which CI also runs on push and PR. A person drives it, and it releases by bumping `version` in `plugin.json`. Assumed from the repository; correct me if wrong.

## Grades

- **Correctness: C** (confidence: high). `CLAUDE.md` points at `docs/architecture.md`, which doesn't exist. The rest of the config loads fine.
- **Alignment: B** (confidence: medium). `CLAUDE.md` is short and focused on non-obvious rules. The one broken pointer is the exception.
- **Coverage: D** (confidence: high). Three gaps: no allow rule for the test command, no `claude plugin validate` check, and no plugin evals.

## Top changes

4 changes are worth making. There are no more because the setup is otherwise small and sound.

1. **Fix the dangling architecture reference** (Correctness, effort S)
   Problem: `CLAUDE.md` line 10 tells Claude to read `docs/architecture.md` before changing the skill, script or marketplace entry. `docs/` contains only `style.md`, so the file doesn't exist. Claude will look for it and find nothing.
   Why: Instructions should point at files that exist. Otherwise Claude wastes turns or guesses.
   Change: Either delete lines 9–10 or write a short `docs/architecture.md`. Deleting is the simpler fix:
   ```diff
   -- For how the skill, script and marketplace entry fit together, see
   -  docs/architecture.md before changing any of them.
   ```
   Source: [Write effective instructions](https://code.claude.com/docs/en/memory)

2. **Validate the plugin in CI and in the documented checks** (Coverage, effort S)
   Problem: Nothing in `CLAUDE.md`, the README or `.github/workflows/ci.yml` runs `claude plugin validate`. A broken manifest or marketplace entry would ship without anyone noticing.
   Why: The repo's product is the plugin manifest and skill, and unit tests don't cover either.
   Change: Add this step to `ci.yml`, and a second `Validate:` bullet to `CLAUDE.md`:
   ```yaml
         - name: Validate plugin
           run: claude plugin validate .
   ```
   CI will need the Claude Code CLI installed first, for example `npm i -g @anthropic-ai/claude-code`.
   Source: [plugin validate](https://code.claude.com/docs/en/plugins/cli-reference)

3. **Pre-approve the test command** (Coverage, effort S)
   Problem: `.claude/settings.json` doesn't exist, so no allow rule covers `python3 -m unittest`. Every test run prompts.
   Why: The test command is the main check in this repo, and it's read-only.
   Change: Create `.claude/settings.json`:
   ```json
   {"permissions": {"allow": ["Bash(python3 -m unittest)", "Bash(python3 -m unittest discover -s tests)"]}}
   ```
   Source: [Permission rule syntax](https://code.claude.com/docs/en/permissions)

4. **Add evals for the `changelog-entry` skill** (Coverage, effort M)
   Problem: There's no `evals/` directory, and `claude plugin eval` isn't documented or run. Nothing measures whether the skill triggers or produces good entries.
   Why: Unit tests cover the script's formatting. They don't show that Claude picks the skill up or uses it well.
   Change: Add `evals/` cases for `changelog-entry`, such as "a changelog entry for this release" on a fixture repo. Run `claude plugin eval` as a release gate and note it in `CLAUDE.md`.
   Source: [Test plugins with evals](https://code.claude.com/docs/en/plugin-evals)

## Also worth knowing

- CI runs `python -m unittest discover -s tests -v`, while the README and `CLAUDE.md` give the same command without `-v`. They're equivalent, so this is only a note.
- `docs/style.md` exists, so that reference is fine.
- `CONTRIBUTING.md` could carry the validate and eval steps once they exist.

---
Claude Code 2.1.314; catalog 2026-10-29.
Docs: the index was read live, and no pages are new since the last assessment.
Scope: project only. User settings, managed settings, `~/.claude.json`, and installed plugins and marketplaces were not inspected.
Read-only run: nothing was written.