# Claudit: slugsmith

**Intent:** slugsmith is a small, dependency-free ESM library that turns titles into URL slugs and is published to npm. Work is checked with `npm test` (`node --test`) and `npm run lint`. A Stop hook re-runs the tests at the end of each turn. Changes to existing slug output count as breaking and need a major version bump. A person drives it with Claude Code, and the `add-slug-rule` skill covers the one recurring task. Assumed from the repository; correct me if wrong.

## Grades

- **Correctness: A** (confidence: high). The scan reported no findings. The settings, the Stop hook (which guards against loops with `stop_hook_active`) and the skill all load and are valid.
- **Alignment: A** (confidence: high). `CLAUDE.md` is 31 lines and holds only what the repo doesn't show: the rule-ordering gotcha, the semver implications, and the `.env` publish token. The skill's steps match `CLAUDE.md`, `docs/conventions.md` and the real commands.
- **Coverage: A** (confidence: high). All five baseline checks are met or n/a: instructions, a check command, an allowlist for both check commands, a deny on `.env`, and a Stop hook. No profiles matched, so there are no extra feature expectations.

## Top changes

0 changes are worth making: the setup already fits a small single-purpose library. Any further additions would be padding.

## Also worth knowing

- **CI:** The scan found no CI workflow. If you publish from CI, a workflow that runs `npm test` and `npm run lint` on pull requests would back up the local Stop hook. This isn't a Claude Code feature, so it needs no source.
- **`/doctor`:** Run it occasionally to catch unused skills or slow hooks as the setup grows.
- **Deny rules:** `.env` is already denied for Read and Edit. If you add other secret files, such as `.npmrc` with a token, add matching deny rules.

---
Claude Code 2.1.314; catalog 2026-10-29.
Docs: llms.txt index read live; no pages needed beyond it.
New in Claude Code, not yet assessed: nothing.
Scope: project only. User settings, managed settings, `~/.claude.json` and installed plugins were not inspected. Read-only run, so nothing was written.
Dismissed findings: 0.