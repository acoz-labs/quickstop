# Claudit: Quickstop

**Intent:** Quickstop is a home for agent plugins (Claudit and Writing for Humans for Claude Code) and read-and-adapt workflows (Shipshape). It generates marketplace indexes and a catalog from native manifests. Work follows an SDLC contract in `docs/operations/sdlc.md`: agents and maintainers author issues and PRs, review independently, and verify with `bin/ci`, `bin/sdlc check` and `bin/check-marketplace --base`. Assumed from the repository; correct me if wrong.

## Grades

- **Correctness: A** (confidence: high). The settings file parses and the three allow rules match the documented check commands. The scan found no defects.
- **Alignment: A** (confidence: high). `CLAUDE.md` is 4 lines and imports `AGENTS.md` and `docs/repository.md`, which are both loaded. Together they come to 135 lines, and they hold the repo-specific commands and rules.
- **Coverage: A** (confidence: high). All applicable baseline checks are met: instructions, check commands and the allowlist. The secrets and Stop-hook checks don't apply. The agent-run, plugin-repo and procedure-docs profiles have no gaps.

## Top changes

No changes worth making: the scan found no defects or gaps; optional items are under Also worth knowing; declined features are under Declined by the project.

## Declined by the project

- **Hooks** (`docs/repository.md:64`): "Repository push hooks and Claude shell-match hooks have been retired; clean-checkout evidence is the verification gate."
  Reason: "clean-checkout evidence is the verification gate"

## Also worth knowing

- **Optional: a skill for `docs/operations/sdlc.md`.** `AGENTS.md:3` already links the doc from the loaded instructions, so Claude can find it. A skill would only help if you want it invoked on demand. To do it, create `.claude/skills/sdlc/SKILL.md` with `name` and `description` frontmatter that follows the doc's steps and links it as the source. Source: [Put team procedures in skills](https://code.claude.com/docs/en/best-practices).
- Native checks Claudit can't run for you: `/doctor prompt-audit` (several instruction files), `/doctor` (unused skills, MCP servers and slow hooks) and `/insights` (recurring friction).

---
Claudit 4.2.0; audited commit 2f2ae099041e86eac6e678cdfa03fe06de53ff1c
Claude Code 2.1.317; catalog 2026-10-29
Docs: index read live; no pages fetched, graded from the shipped catalog.
New in Claude Code, not yet assessed: none.
Scope: project only; user settings, managed settings, `~/.claude.json` and installed plugins not visible.
