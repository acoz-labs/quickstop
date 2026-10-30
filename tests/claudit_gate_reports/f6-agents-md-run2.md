# Claudit: csvsum

**Intent:** csvsum is a small, standard-library-only Python tool that sums one numeric column of a CSV file. The code is in `src/csvsum/` and the tests are in `tests/`. `bin/check` runs the unit tests, and `AGENTS.md` says agents maintain the repo and must run `bin/check` before reporting a change done. Releases are manual: bump the version in `pyproject.toml`, add a `CHANGELOG.md` entry, and tag. There is no CI. Assumed from the repository; correct me if wrong.

## Grades

- **Correctness: A** (confidence: high). There are no defects. `AGENTS.md` loads directly, and the `.claude/` directory has no settings to break.
- **Alignment: A** (confidence: medium). `AGENTS.md` is short (7 lines) and holds only what Claude can't infer from the repo. The paths it names exist.
- **Coverage: C** (confidence: high). Two baseline items are missing. `bin/check` isn't pre-approved, and the "run `bin/check`" rule is prose only, with no hook enforcing it.

## Top changes

2 changes are worth making. The project is tiny and the instructions are already good, so anything beyond these would be padding.

1. **Enforce `bin/check` with a Stop hook** (Coverage, effort S)
   Problem: `AGENTS.md:3` says to run `bin/check` before reporting done. Nothing enforces it: `.claude/settings.json` doesn't exist, so Claude can finish with failing tests.
   Why: agents drive this repo, and a Stop hook makes the check a gate instead of a request.
   Change: create `.claude/settings.json`. The allow rule from change 2 can go in the same file.
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

2. **Pre-approve `bin/check`** (Coverage, effort S)
   Problem: there is no `permissions.allow` rule for `bin/check`, so every run prompts.
   Why: the agent runs this command before every completion, so each run would otherwise wait on a prompt.
   Change: in `.claude/settings.json`:
   ```json
   {"permissions": {"allow": ["Bash(bin/check)"]}}
   ```
   Source: [Permission rule syntax](https://code.claude.com/docs/en/permissions)

## Also worth knowing

- Optional: if you add a `CLAUDE.md` later, have it import `@AGENTS.md`. Otherwise it stops `AGENTS.md` from loading.
- Optional: a short release skill in `.claude/skills/` would make the release steps repeatable. At 3 lines of prose they're fine as they are.

---
Claude Code 2.1.314; catalog 2026-10-29.
Docs: the index was read live, and no new pages are pending assessment.
Scope: project only. User and managed settings, `~/.claude.json` and installed plugins were not inspected.
Read-only run: nothing was written. Dismissed findings: 0.