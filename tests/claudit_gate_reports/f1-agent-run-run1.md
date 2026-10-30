# Claudit: tallyho

**Intent:** tallyho is a small Python library that tallies votes from CSV-like lines and reports a winner. `bin/ci` (lint, then unittest) is the check. Releases follow the 10-step `docs/release-procedure.md`. CLAUDE.md says agents run the repository end to end, so Claude does the work and CI is the gate. Assumed from the repository; correct me if wrong.

## Grades

- **Correctness: A** (confidence: high). The scan found no defects. The only instruction file, CLAUDE.md, loads, and `.claude/` doesn't exist yet, so nothing there can be broken.
- **Alignment: B** (confidence: medium). CLAUDE.md is short and accurate. Its one rule, "run `bin/ci` before you report done", is only advice, and the release procedure lives in a doc that Claude isn't pointed to.
- **Coverage: D** (confidence: high). Three gaps: `bin/ci` isn't pre-approved, nothing enforces the must-run rule, and the release procedure has no skill.

## Top changes

3 changes are worth making.

1. **Enforce `bin/ci` with a Stop hook** (Coverage, effort S)
   Problem: CLAUDE.md:3 says to run `bin/ci` before reporting done, but `.claude/settings.json` and any hook don't exist. Nothing stops an agent from finishing with failing checks.
   Why: Agents drive this repo, so the gate has to hold without a person watching.
   Change: Add to `.claude/settings.json`:
   ```json
   {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/stop-check.sh"}]}]}}
   ```
   Then create `.claude/hooks/stop-check.sh` and `chmod +x` it:
   ```bash
   #!/usr/bin/env bash
   # Block finishing until the check passes.
   input=$(cat)
   case "$input" in *'"stop_hook_active":true'*|*'"stop_hook_active": true'*) exit 0 ;; esac
   cd "$CLAUDE_PROJECT_DIR" || exit 0
   if ! out=$(bin/ci 2>&1); then
     printf '%s\n' "bin/ci failed:" "$out" | tail -n 60 >&2
     exit 2
   fi
   ```
   Source: [Enforce the check with a Stop hook](https://code.claude.com/docs/en/best-practices)

2. **Pre-approve `bin/ci`** (Coverage, effort S)
   Problem: No `permissions.allow` rule covers `bin/ci`, so every run prompts. The Stop hook in change 1 runs the check itself, but Claude's own runs would still prompt.
   Why: An agent-run repo shouldn't stall on its own check.
   Change: Merge into `.claude/settings.json`:
   ```json
   {"permissions": {"allow": ["Bash(bin/ci)"]}}
   ```
   Source: [Permission rule syntax](https://code.claude.com/docs/en/permissions)

3. **Turn the release procedure into a skill** (Coverage, effort M)
   Problem: `docs/release-procedure.md` has 10 numbered steps, but no skill under `.claude/skills/` exists. Claude only finds the procedure if it happens to open the README.
   Why: Releases are a repeatable workflow, and a skill loads on demand without adding to CLAUDE.md.
   Change: Create `.claude/skills/release-procedure/SKILL.md` with `name` and `description` frontmatter (for example, "Use when cutting a tallyho release"). The body follows the steps and links `docs/release-procedure.md` as the source of truth.
   Source: [Put team procedures in skills](https://code.claude.com/docs/en/best-practices)

## Also worth knowing

- `bin/lint.py` and `python -m unittest` are already run by `bin/ci`. Pre-approving them separately is optional, only for running them in isolation.
- Optional: run `/doctor` once hooks and skills exist, to catch slow hooks and unused skills.

---
Claude Code 2.1.314; catalog 2026-10-29.
Docs: index read live; no new pages since the catalog.
Scope: project only; user and managed settings not visible. Read-only run, so nothing was written.
Dismissed: 0.