# Claudit: tallyho

**Intent:** tallyho is a small Python library (`src/tallyho`, tests under `tests/`). `bin/ci` runs the lint and unittest checks. Agents run the repository end to end, including releases, which follow the 10-step `docs/release-procedure.md` (bump version, update changelog, tag, push). CLAUDE.md requires `bin/ci` to pass before any change is reported as done. Assumed from the repository; correct me if wrong.

## Grades

- **Correctness: A** (confidence: high). The only config file is a 3-line CLAUDE.md that loads, and the scan reported no defects.
- **Alignment: B** (confidence: medium). CLAUDE.md is short and accurate. Two things agents are told to do, running `bin/ci` and following the release procedure, depend on prose alone.
- **Coverage: D** (confidence: high). There are three gaps: no allow rule for `bin/ci`, no Stop hook enforcing it, and no skill for the release procedure.

## Top changes

3 changes are worth making.

1. **Enforce `bin/ci` with a Stop hook** (Coverage, effort S)
   Problem: CLAUDE.md:3 says to run `bin/ci` before reporting done, but nothing enforces it. `.claude/settings.json` and any hook don't exist. An agent can skip the check and stop.
   Why: Agents drive this repo, so a Stop hook makes a failing `bin/ci` block completion.
   Change: add to `.claude/settings.json`:
   ```json
   {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/stop-check.sh"}]}]}}
   ```
   and create `.claude/hooks/stop-check.sh` (`chmod +x`):
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
   Problem: there is no `permissions.allow` rule for `bin/ci`, so every run prompts. The Stop hook also reruns it each turn.
   Why: an agent-run repo shouldn't stall on its own required check.
   Change: in `.claude/settings.json`:
   ```json
   {"permissions": {"allow": ["Bash(bin/ci)"]}}
   ```
   Source: [Permission rule syntax](https://code.claude.com/docs/en/permissions)

3. **Turn the release procedure into a skill** (Coverage, effort M)
   Problem: `docs/release-procedure.md` has 10 numbered steps, and agents cut every release. No skill exists, so Claude only finds the steps if it happens to open the doc.
   Why: a skill makes the release repeatable and invocable by name. The doc stays the source of truth.
   Change: create `.claude/skills/release-procedure/SKILL.md`:
   ```markdown
   ---
   name: release-procedure
   description: Cut a tallyho release (version bump, changelog, tag, push). Use when asked to release or publish a new version.
   ---
   Follow docs/release-procedure.md step by step, in order. Stop at the first failure and report the failing step.
   ```
   Because the procedure pushes and tags, consider adding `disable-model-invocation: true` so it only runs when invoked explicitly.
   Source: [Put team procedures in skills](https://code.claude.com/docs/en/best-practices)

## Also worth knowing

- `bin/lint.py` and `python -m unittest` aren't mentioned in CLAUDE.md. That's fine, because `bin/ci` wraps both. Add them only if agents often need to run them alone.

---
Claude Code 2.1.314; catalog 2026-10-29.
Docs: index read live; no new pages since the catalog.
Scope: project only; user and managed settings, `~/.claude.json` and plugins not inspected.
Read-only run: nothing was written.