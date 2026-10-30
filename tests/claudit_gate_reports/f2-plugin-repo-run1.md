# Claudit: changelog-helper

**Intent:** This repo ships the `changelog-helper` Claude Code plugin. It has one skill, `changelog-entry`, with a standard-library Python script, and a marketplace entry. Work is checked with `python3 -m unittest discover -s tests`, which CI also runs on push and pull request. A person drives it, bumping the plugin version for user-visible changes. Assumed from the repository; correct me if wrong.

## Grades

- **Correctness: C** (confidence: high). `CLAUDE.md` points at `docs/architecture.md`, which doesn't exist.
- **Alignment: B** (confidence: medium). `CLAUDE.md` is short and current, and it matches the CI test command. The missing architecture file is the one gap.
- **Coverage: D** (confidence: medium). Test commands aren't pre-approved. Nothing runs `claude plugin validate`, and there is no plugin eval suite.

## Top changes

4 changes are worth making.

1. **Fix the dangling `docs/architecture.md` reference** (Correctness, effort S)
   Problem: `CLAUDE.md` line 10 tells Claude to read `docs/architecture.md` before changing the skill, script or marketplace entry. Only `docs/style.md` exists in `docs/`, so Claude gets a dead pointer on every such change.
   Why: Instructions should point at files that exist. Otherwise Claude wastes turns or guesses.
   Change: replace lines 9-10 in `CLAUDE.md`:
   ```diff
   -- For how the skill, script and marketplace entry fit together, see
   -  docs/architecture.md before changing any of them.
   +- The skill (`skills/changelog-entry/SKILL.md`) calls `scripts/format_entry.py`;
   +  `.claude-plugin/marketplace.json` lists the plugin. Keep all three in sync.
   ```
   Or create `docs/architecture.md`.
   Source: [Write effective instructions](https://code.claude.com/docs/en/memory)

2. **Run `claude plugin validate .` in CI and document it** (Coverage, effort S)
   Problem: Nothing in `CLAUDE.md`, the README or `ci.yml` runs plugin validation, so a malformed manifest or marketplace entry can ship.
   Why: The repo's product is a plugin, and the manifests are the part most likely to break for users.
   Change: add a CI step and a `CLAUDE.md` line:
   ```yaml
         - name: Validate plugin
           run: claude plugin validate .
   ```
   ```
   - Validate: `claude plugin validate .`
   ```
   The CI runner needs the `claude` CLI installed first.
   Source: [plugin validate](https://code.claude.com/docs/en/plugins/cli-reference)

3. **Pre-approve the test command** (Coverage, effort S)
   Problem: `.claude/settings.json` doesn't exist and no allow rule covers `python3 -m unittest`, so every test run prompts.
   Why: Tests are the main check, and Claude should be able to run them without interruption.
   Change: create `.claude/settings.json`:
   ```json
   {"permissions": {"allow": ["Bash(python3 -m unittest)", "Bash(python3 -m unittest discover -s tests)"]}}
   ```
   Source: [Permission rule syntax](https://code.claude.com/docs/en/permissions)

4. **Add a plugin eval suite** (Coverage, effort M)
   Problem: There is no `evals/` directory, so the `changelog-entry` skill's behaviour is never measured.
   Why: Unit tests cover the script but not whether Claude triggers and uses the skill correctly.
   Change: add `evals/` cases for `changelog-entry`, then run `claude plugin eval` as a release gate or in CI.
   Source: [Test plugins with evals](https://code.claude.com/docs/en/plugin-evals)

## Also worth knowing

- Optional: `CLAUDE.md` could mention that the CI test command is `python -m unittest discover -s tests -v`, matching the documented one.

---
Claude Code 2.1.314; catalog 2026-10-29.
Docs: index read live; no pages fetched. Recommendations come from the shipped catalog.
New in Claude Code, not yet assessed: getting-started/overview.
Scope: project only; user and managed settings, `~/.claude.json` and installed plugins were not inspected.
Read-only run: no changes were made.