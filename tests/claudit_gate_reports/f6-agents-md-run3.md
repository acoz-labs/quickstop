# Claudit: csvsum

**Intent:** csvsum is a small, standard-library-only Python tool that sums one numeric column of a CSV file. Agents maintain it (per `AGENTS.md`). The check is `bin/check`, which runs the unittest suite, and releases are manual: bump the version in `pyproject.toml`, add a `CHANGELOG.md` entry, and tag. Assumed from the repository; correct me if wrong.

## Grades

- **Correctness: A** (confidence: high). The scan found no defects. `AGENTS.md` is loaded directly and `bin/check` exists and is documented.
- **Alignment: A** (confidence: medium). `AGENTS.md` is 7 lines and holds only what the repo doesn't already say (the check, the layout, the no-dependencies rule, the release steps).
- **Coverage: C** (confidence: high). Two baseline items are missing: `bin/check` isn't pre-approved, and the "run `bin/check` before done" rule is prose only.

## Top changes

2 changes are worth making: the setup is otherwise small and healthy, and there are no skills, MCP servers or CI to assess.

1. **Pre-approve `bin/check`** (Coverage, effort S)
   Problem: `.claude/settings.json` has no `permissions.allow` rule for `bin/check`, so every run of the check prompts for approval.
   Why: agents run this check before every change, so a prompt each time slows the main loop.
   Change: create `.claude/settings.json` with:
   ```json
   {"permissions": {"allow": ["Bash(bin/check)"]}}
   ```
   Source: [Permission rule syntax](https://code.claude.com/docs/en/permissions)

2. **Enforce the check with a Stop hook** (Coverage, effort S)
   Problem: `AGENTS.md:3` says to run `bin/check` before reporting done, but nothing enforces it. No Stop hook exists, so Claude can finish without running the tests.
   Why: agents drive this repo, so a hook gives the rule a guarantee that prose can't.
   Change: add this to `.claude/settings.json`:
   ```json
   {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/stop-check.sh"}]}]}}
   ```
   Create `.claude/hooks/stop-check.sh` and run `chmod +x` on it:
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

- Optional: the release steps in `AGENTS.md` could become a project skill if you release often. At 3 steps, the current prose is fine.
- Optional: `/insights` can show recurring friction once you have some session history.

---
Claude Code 2.1.314; catalog 2026-10-29.
Docs: the index was read live, and no new pages are waiting to be assessed.
Scope: project only. User settings, managed settings, `~/.claude.json` and installed plugins were not inspected.
Dismissed findings: 0.
Read-only run: nothing was written.