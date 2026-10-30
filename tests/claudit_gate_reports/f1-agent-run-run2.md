# Claudit: tallyho

**Intent:** tallyho is a small Python package. `bin/ci` is the check, with `bin/lint.py` and `python -m unittest` behind it. Agents run the repository end to end, including releases. `docs/release-procedure.md` has ten ordered steps for a release: clean tree, CI, version bump in two files, changelog, commit, tag, push, release note. Assumed from the repository; correct me if wrong.

## Grades

- **Correctness: A** (confidence: high). The one instruction file loads and the scan found no defects.
- **Alignment: B** (confidence: medium). `CLAUDE.md` is short and accurate, but its "run `bin/ci`" rule and the release procedure depend on Claude remembering them.
- **Coverage: D** (confidence: high). There is no `.claude/` directory at all, so three gaps are open: the check isn't pre-approved, the must-run rule isn't enforced, and the release procedure has no skill.

## Top changes

3 changes are worth making. Nothing else stood out: the repo is small and has no MCP servers, secrets paths or typed code that the scan flagged.

1. **Enforce `bin/ci` with a Stop hook** (Coverage, effort S)
   Problem: `CLAUDE.md:3` says to run `bin/ci` before reporting any change as done. That is prose only, and no `.claude/settings.json` or hook exists, so nothing stops an agent from finishing with a failing check.
   Why: agents drive this repo, so a Stop hook makes the rule hold on every run.
   Change: add to `.claude/settings.json`:
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
   if ! out=$(bin/ci 2>&1); then
     printf '%s\n' "bin/ci failed:" "$out" | tail -n 60 >&2
     exit 2
   fi
   ```
   Source: [Enforce the check with a Stop hook](https://code.claude.com/docs/en/best-practices)

2. **Turn the release procedure into a skill** (Coverage, effort S)
   Problem: `docs/release-procedure.md` has 10 numbered steps and no skill, so Claude only follows it if it happens to find the doc.
   Why: agents cut every release, and a skill with a description lets Claude load the procedure when a release is requested.
   Change: create `.claude/skills/release-procedure/SKILL.md`:
   ```markdown
   ---
   name: release-procedure
   description: Cut a tallyho release (version bump, changelog, tag, push). Use when asked to release or publish a new version.
   disable-model-invocation: true
   ---
   Follow docs/release-procedure.md step by step, in order. Stop at the first failure and report the failing step.
   ```
   `disable-model-invocation: true` makes it manual-only, so a push and tag happen only when you ask. Drop that line if you want Claude to trigger it on its own.
   Source: [Put team procedures in skills](https://code.claude.com/docs/en/best-practices)

3. **Pre-approve `bin/ci`** (Coverage, effort S)
   Problem: there is no `permissions.allow` rule for `bin/ci`, so every run prompts.
   Why: the check runs on every change, and the Stop hook above would also hit the prompt.
   Change: add to `.claude/settings.json`:
   ```json
   {"permissions": {"allow": ["Bash(bin/ci)"]}}
   ```
   Source: [Permission rule syntax](https://code.claude.com/docs/en/permissions)

## Also worth knowing

- `bin/lint.py` and `python -m unittest` are not in `CLAUDE.md`. That is fine while `bin/ci` wraps them. Mention them only if agents need to run them alone.
- Release steps 9 and 10 push and post externally. Keep `git push` out of the allow list so they still prompt.

---
Claude Code 2.1.314; catalog 2026-10-29.
Docs: index read live; no new pages since the last assessment.
Scope: project only; user and managed settings, `~/.claude.json` and installed plugins not inspected.
Read-only run: nothing was written.