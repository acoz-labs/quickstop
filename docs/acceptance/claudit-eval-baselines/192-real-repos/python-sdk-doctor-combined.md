# /doctor

**Summary:** I could only run part of the health check. Commands that read `~/.claude.json`, `~/.claude/settings.json`, the transcripts and `claude --version` need approval, and this session didn't grant it. I made no changes. Where the data wasn't readable, I haven't guessed.

| Component | Type | Scope | Uses (total) | Used in window? | Est. resident tokens | Verdict |
|---|---|---|---|---|---|---|
| `CLAUDE.md` (just `@AGENTS.md`) | memory | project | n/a | n/a | ~3 | keep |
| `AGENTS.md` (8,714 chars) | memory | project | n/a | n/a | ~2.2k | keep, already lean |
| `test-quality` | skill | project | not readable | not readable | small | keep, referenced by `AGENTS.md` |
| `.claude/commands/` (one entry, not inspected) | commands | project | not readable | not readable | small | not judged |

I scanned no transcript window.

**Check 0 – setup health:**
- Project `.claude/` has no `agents/` directory, so there are no agent definitions to break or collide.
- Not verified: installs and PATH, whether `~/.claude.json` and the settings files parse, and the skill frontmatter.
- To finish these, run `claude doctor` in a terminal. Or approve the read-only commands and re-run `/doctor`.

**Check 1 – unused extensions:** I couldn't read the usage counters or transcripts, so I have no verdicts. I don't want to recommend disabling things on missing data.

**Check 2 – local CLAUDE.md dedup:** I didn't compare `~/.claude/CLAUDE.md` or `CLAUDE.local.md`. `CLAUDE.local.md` wasn't checked either.

**Check 3 – trim derivable content:**
- `AGENTS.md` is about 2.2k est. tokens, far below the ~40,000-character warning threshold.
- Its content is mostly gotchas, non-default conventions and directives: `--frozen`, `uv add` for dynamic dependencies, the coverage and pragma rules, the API-compatibility policy, and the encoding rule.
- It is already lean, so nothing to cut.

**Check 4 – lazy loading:** I'm not proposing any migration. The Coverage section is the only task-specific part, and it is short. The rules it holds apply to every test, so they should stay always-loaded.

**Check 5 – slow hooks:** No data. I couldn't read the settings, and the transcripts are unscanned.

**Check 6 – context:** The only resident weight I could measure is `AGENTS.md` at about 2.2k est. tokens. Run `/context` for the live figure.

**Check 7 – version:** I couldn't run `claude --version`, so I haven't compared against the latest release.

**Check 8 – auto mode:** I couldn't read `permissions.defaultMode`, so I'm proposing nothing.

**Check 9 – denied read-only commands:** No transcript data, so no allow rules.

**Check 10 – /usage findings:**
- [Redacted in this copy: /doctor quoted the operator's own `/usage` figures here. The full report is in the factory's retained results.]

I have nothing to confirm, so I'm not asking either question. If you approve read access to `~/.claude.json`, `~/.claude/settings.json` and `~/.claude/projects`, I'll re-run checks 0 to 2 and 5 to 9. I'd only read the specific keys each check needs.

# /doctor prompt-audit .

# Prompt audit: `.`

## Assumptions

- **Scope:** the whole repository's prompt surface. Files outside the repo (`~/.claude/`) were not touched.
- **Target model:** Claude Sonnet 5.5, the model running this audit. The repo has no Claude API code and no model pin.
- **Mode:** non-interactive, report and proposed diff only. Nothing was edited.

## Inventory

- `CLAUDE.md` (1 line, `@AGENTS.md` import)
- `AGENTS.md` (166 lines)
- `.claude/skills/test-quality/SKILL.md` (150 lines)
- `.claude/commands/review-pr.md` (118 lines)
- Not read, by rule: `.claude/settings*.json`, `.mcp.json`.

## Summary

The surface is mostly in good shape. Almost every prohibition carries its reason, the rules are real constraints (100% coverage, `--frozen`, API-compatibility contract), and the two files that overlap on testing rules agree. I verified the paths, commands and CI facts that `AGENTS.md` names, and they all resolve:
- `tests/client/test_client.py`, `tests/client/test_stdio.py` and `src/mcp/client/stdio.py` exist.
- `src/mcp/__init__.py` defines `__all__`.
- `pyproject.toml` has `fail_under = 100` and the `[tool.hatch.metadata.hooks.uv-dynamic-versioning]` table.
- The CI matrix is 3.11–3.15.
- `scripts/test` sets `PYTHONWARNDEFAULTENCODING=1`.
- `conformance.yml`, `RELEASE.md`, `CONTRIBUTING.md` and `mkdocs.yml` exist.

The two real findings are history narratives in `SKILL.md`. The rest are low-confidence flags.

**Counts by group:** Group 1: 1 medium and 2 low flags. Group 2: 1 medium (history narratives) and 2 low flags. Groups 3 and 4: not applicable, since there are no tool definitions or request code.

## Findings (highest confidence first)

### 1. History narratives and incident archaeology in `SKILL.md` (medium; `rewrite`)

Group 2, "History narratives". The rule is what matters. The anecdote and the figures behind it will go stale.

| Location | Evidence | Why obsolete |
|---|---|---|
| `SKILL.md:42-43` | "bugs (a real stream leak was found this way) that subprocess indirection masks" | Incident reference. The reason survives without it. |
| `SKILL.md:67-69` | "(that discipline is why 529 e2e tests run in ~10 s)" | A hard-coded test count and timing that rot as the suite changes. |
| `SKILL.md:71-72` | "unexplained widenings propagate (one agent used 10 and every later one copied it)" | A single-incident story. |
| `SKILL.md:73-75` | "`elapsed < 0.9` on a ~0.01 s operation — a 90× margin — was still rejected in review" | A review anecdote. The rule ("never assert wall-clock time") stands alone. |
| `SKILL.md:94-95` | "a full review of the e2e suite found two such cases even under this discipline" | An audit-result narrative. |
| `SKILL.md:117-119` | "the observed shortcuts … all surfaced in one oversized 27-test batch" | An incident count. |
| `SKILL.md:145-146` | "'rushing something out the door is not the goal here, explicitly so'" | A quoted past remark. |

The reasons, such as "a sleep guesses at timing" and "review quality scales inversely with batch size", are load-bearing and stay.

### 2. `IMPORTANT:` markers without an adjacent reason (low–medium; `rewrite`, optional)

Group 1a.
- `AGENTS.md:75`: "IMPORTANT: Tests should be fast and deterministic." This is the only one without a "because". `SKILL.md` already explains the reasoning, so plain wording is enough.
- `AGENTS.md:56`: "IMPORTANT: All imports go at the top of the file — inline imports hide dependencies…". This one carries its reason and is a scoped emphasis, so I'd keep it.
- `FORBIDDEN` at `:40` and `:166` encode hard constraints, and `:166` states its exception. Keep both.

### 3. Low-confidence flags (no edits proposed)

- `AGENTS.md:102,106`: "(~23s)" and "(~4s)" are timings that drift. They serve as practical guidance, so leave them unless they become wrong.
- `SKILL.md:142-144`: "Every agent writes notes… what it couldn't decide". Nothing in the repo enforces this. It reads as a process norm, so I can't tie it to a dated pattern.
- `.claude/commands/review-pr.md:3`: "Follow these steps carefully." is mild padding, and Step 5's seven review criteria largely restate defaults. The `gh` commands and the output template are real contract and format-pinning, so keep them. Low confidence.
- `AGENTS.md` and `SKILL.md` restate the same rules: no `Test` classes, anyio, no new pragmas, and the `sleep` guidance. They agree, so this is working redundancy and I left it alone. The "no `anyio.sleep`" rules are consistent: `AGENTS.md` says "avoid" with the time-based-feature exception, and `SKILL.md` says "no sleeps, ever" with the same exception.

## Proposed diff

```diff
--- a/.claude/skills/test-quality/SKILL.md
+++ b/.claude/skills/test-quality/SKILL.md
@@ In-memory / in-process first
   process boundary is itself the thing under test. In-process isn't just faster — it surfaces
-  bugs (a real stream leak was found this way) that subprocess indirection masks.
+  bugs that subprocess indirection masks.
@@ No sleeps, ever
-  Coordinate with `anyio.Event` so the wait ends exactly when the condition holds (that
-  discipline is why 529 e2e tests run in ~10 s). Sole exception: tests *of* time-based
+  Coordinate with `anyio.Event` so the wait ends exactly when the condition holds.
+  Sole exception: tests *of* time-based
   features, with a comment.
@@ fail_after
-  reason; "10 to be safe" is covering up a flake, not fixing one, and
-  unexplained widenings propagate (one agent used 10 and every later one copied it).
+  reason; "10 to be safe" is covering up a flake, not fixing one.
@@ Never assert wall-clock time
-- **Never assert wall-clock time, even with huge margins.** `elapsed < 0.9` on a ~0.01 s
-  operation — a 90× margin — was still rejected in review. `fail_after` bounding a hang is the
-  only timing primitive allowed.
+- **Never assert wall-clock time, even with huge margins.** `fail_after` bounding a hang is
+  the only timing primitive allowed.
@@ Hollow-proof check
   "which assertion proves *this*?" A passing test near a behaviour is not proof of it — a full
-  review of the e2e suite found two such cases even under this discipline.
+  proof of it.
@@ Small chunks
-  ≤5 per agent. Review quality scales inversely with batch size: the observed shortcuts
-  (over-stacked tests, a timing assertion, wrong abstraction level) all surfaced in one
-  oversized 27-test batch.
+  ≤5 per agent. Review quality scales inversely with batch size: over-stacked tests, timing
+  assertions, and wrong abstraction levels slip through large batches.
@@ Quality over speed
-- **Quality over speed is a stated goal, not a preference** ("rushing something out the door is
-  not the goal here, explicitly so"). Don't quietly de-scope agreed work mid-stream;
-  renegotiate scope explicitly.
+- **Quality over speed is a stated goal, not a preference.** Don't quietly de-scope agreed
+  work mid-stream; renegotiate scope explicitly.

--- a/AGENTS.md
+++ b/AGENTS.md
@@ -75
-- IMPORTANT: Tests should be fast and deterministic. Prefer in-memory async execution;
+- Tests should be fast and deterministic. Prefer in-memory async execution;
```

Two cautions on the diff. The `Hollow-proof check` hunk is sketched loosely, so reflow the sentence so it ends at "…is not proof of it." The `AGENTS.md:75` hunk is optional and low–medium confidence, so take or skip it on your own judgment.

I did not run behavioral probes (Step 7). These are wording-only edits to a repo with no eval suite. Before deleting any of this text, grep the repo for the exact strings, in case a test or script matches on them.
