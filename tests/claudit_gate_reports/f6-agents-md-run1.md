# Claudit: csvsum

**Intent:** csvsum is a small, standard-library-only Python CLI that sums one numeric column of a CSV file. Agents maintain it. The only check is `bin/check`, which runs the unit tests, and AGENTS.md says to run it before reporting a change as done. A release is a manual `pyproject.toml` version bump, a `CHANGELOG.md` entry and a `vX.Y.Z` tag. Assumed from the repository; correct me if wrong.

## Grades

- **Correctness: A** (confidence: high). The scan found no defects, and `AGENTS.md` loads directly (7 lines, no `CLAUDE.md` is present).
- **Alignment: A** (confidence: high). The instructions are short and hold only things Claude can't infer from the repo. Every path and command they name exists.
- **Coverage: C** (confidence: high). The check is documented, but nothing pre-approves it, and the "run `bin/check`" rule is prose only.

## Top changes

2 changes are worth making: the setup is otherwise small and healthy, and there are no skills, MCP servers or secrets that would justify more.

1. **Pre-approve `bin/check`** (Coverage, effort S)
   Problem: `.claude/settings.json` doesn't exist, so no allow rule covers `bin/check` and every run prompts.
   Why: Agents maintain this repo and run `bin/check` constantly, so each prompt interrupts them.
   Change: create `.claude/settings.json`:
   ```json
   {"permissions": {"allow": ["Bash(bin/check)"]}}
   ```
   Source: [Permission rule syntax](https://code.claude.com/docs/en/permissions)

2. **Enforce the check with a Stop hook** (Coverage, effort S)
   Problem: `AGENTS.md:3` says to run `bin/check` before reporting done, but no hook enforces it, so Claude can skip it.
   Why: A Stop hook makes the rule a guarantee, so no change is reported done with failing tests.
   Change: add this to `.claude/settings.json`:
   ```json
   {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/stop-check.sh"}]}]}}
   ```
   Then create `.claude/hooks/stop-check.sh` and run `chmod +x` on it:
   ```bash
   #!/usr/bin/env bash
   # Block finishing until the check passes.
   input=$(cat)
   case "$input" in *'"stop_hook_active":true'*|*'"stop_hook_active": true'*) exit 0 ;; esac
   cd "$CLAUDE_PROJECT_DIR" || exit 0
   if ! out=$(bin/check 2>&1); then
     printf '%s\n' "bin/check failed:" "$out" | tail -n 60 >&2
     exit 2
   fi
   ```
   Source: [Enforce the check with a Stop hook](https://code.claude.com/docs/en/best-practices)

## Also worth knowing

- Optional: the release steps are three lines in `AGENTS.md`. If releases become frequent or error-prone, move them into a `/release` skill.
- Optional: `python -m unittest` appears in `pyproject.toml` as a second check command. `bin/check` already wraps it, so no action is needed.

---
Claude Code 2.1.314 · catalog 2026-10-29
Docs: index read live. No new pages since the last assessment.
Scope: project only. User settings, managed settings, `~/.claude.json` and installed plugins were not inspected.
`--read-only`: nothing was written.