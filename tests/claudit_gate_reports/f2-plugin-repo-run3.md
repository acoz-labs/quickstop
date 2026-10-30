# Claudit: changelog-helper

**Intent:** This repo ships the `changelog-helper` Claude Code plugin and marketplace entry. It has one skill, `skills/changelog-entry/`, with a standard-library Python script that drafts Keep a Changelog entries from commits. A person drives the work through pull requests. CI and CONTRIBUTING.md both run `python3 -m unittest discover -s tests`, and each user-visible change bumps the plugin version. Assumed from the repository; correct me if wrong.

## Grades

- **Correctness: C** (confidence: high). CLAUDE.md points at `docs/architecture.md`, which doesn't exist.
- **Alignment: B** (confidence: medium). CLAUDE.md is short and matches how work is done, but one of its two doc pointers is dead.
- **Coverage: C** (confidence: high). Nothing validates or evaluates the plugin, and the test command isn't pre-approved.

## Top changes

4 changes are worth making.

1. **Fix the dead `docs/architecture.md` reference** (Correctness, effort S)
   Problem: CLAUDE.md line 10 sends Claude to `docs/architecture.md` before it changes the skill, script or marketplace entry. That file doesn't exist; `docs/` only holds `style.md`. Claude will look for it, fail, and work without the context the file was meant to give.
   Why: The file was meant to explain how the skill, script and marketplace entry fit together. Without it Claude edits those pieces blind.
   Change: Remove the reference, or write the file.
   ```diff
   -- For how the skill, script and marketplace entry fit together, see
   -  docs/architecture.md before changing any of them.
   ```
   Source: [Write effective instructions](https://code.claude.com/docs/en/memory)

2. **Run `claude plugin validate .` in CI and document it** (Coverage, effort S)
   Problem: Nothing in CLAUDE.md, README, CONTRIBUTING.md or `ci.yml` validates `.claude-plugin/plugin.json` or `marketplace.json`. A manifest error would only show up when someone installs the plugin.
   Why: The repo's product is the plugin, and the unit tests don't cover the manifests.
   Change:
   ```yaml
   # .github/workflows/ci.yml, add as a step
         - name: Validate plugin
           run: claude plugin validate .
   ```
   Also add `claude plugin validate .` to the Test line in CLAUDE.md and to CONTRIBUTING.md. The CI runner needs the `claude` CLI installed first.
   Source: [plugin validate](https://code.claude.com/docs/en/plugins/cli-reference)

3. **Pre-approve the test command** (Coverage, effort S)
   Problem: `.claude/` is empty, so there is no `permissions.allow` rule for the documented test command. Every test run prompts.
   Why: Tests are the main check in this repo, so Claude should be able to run them without prompting.
   Change: create `.claude/settings.json`
   ```json
   {"permissions": {"allow": ["Bash(python3 -m unittest)", "Bash(python3 -m unittest discover -s tests)"]}}
   ```
   Source: [Permission rule syntax](https://code.claude.com/docs/en/permissions)

4. **Add evals for the skill** (Coverage, effort M)
   Problem: There is no `evals/` directory, and `claude plugin eval` isn't documented anywhere. Nothing measures whether `changelog-entry` triggers on the right prompts or produces good entries.
   Why: The skill is the whole product. The unit tests cover the script, not how Claude uses the skill.
   Change: add `evals/` cases for `changelog-entry`, then run `claude plugin eval` as a release gate or in CI.
   Source: [Test plugins with evals](https://code.claude.com/docs/en/plugin-evals)

## Also worth knowing

- Optional: the Test line in CLAUDE.md duplicates CONTRIBUTING.md and the README. That's fine at 11 lines, but keep the three in sync.

---
Claude Code 2.1.314, catalog 2026-10-29.
Docs: llms.txt index read live; no pages fetched.
New in Claude Code, not yet assessed: none.
Scope: project only; managed settings, user settings and installed plugins not visible.
Dismissed: 0.