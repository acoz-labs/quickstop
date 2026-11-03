# /doctor

I couldn't finish this health check. The sandbox blocked every command that touches your home directory, and I can't ask for approval in this session. No files were changed.

## Summary
The checked-in guidance here is small and lean, so there is little to clean up. I couldn't check your installation, your user settings, or your usage history. I'm not guessing at those results.

## What I could check
| Component | Scope | Est. resident tokens | Verdict |
|---|---|---|---|
| `CLAUDE.md` (two import lines) | project | ~11 | lean, keep |
| `AGENTS.md` (2,777 chars) | project, imported | ~700 | keep. It is almost all directives and etiquette that the code can't show. |
| `docs/repository.md` (5,303 chars) | project, imported | ~1.3k | keep, with one optional trim below |

- **Combined size (check 6):** about 8.1k chars (est. 2k tokens) is always loaded. That is far below the large-file warning threshold of about 40k chars.
- **Settings file:** `.claude/settings.json` parses, and it sets no `defaultMode` or hooks, so nothing in the project overrides a user-level default mode.
- **MCP servers:** there is no `.mcp.json`, so there are no project MCP servers.
- **Agents and skills:** the project has no `.claude/agents` or `.claude/skills` directories, so nothing there can be malformed or collide.
- **Optional trim (check 3):** the "Layout and tracking" section in `docs/repository.md` partly repeats what `ls` shows. I'd keep it, because the generated-versus-hand-edited notes are useful and the saving would be under 300 est. tokens.
- **Migration (check 4):** nothing needs moving. The Local verification section applies repo-wide, and the prohibitions must stay always-loaded.

## What I couldn't check
- **Check 0 (installation health):** duplicate installs, PATH, and whether `~/.claude.json` and user settings parse.
- **Checks 1 and 6 (unused extensions and user-level context):** I couldn't read the usage counters or transcripts.
- **Check 2 (local memory files):** I couldn't read `~/.claude/CLAUDE.md` or `CLAUDE.local.md` to compare them with the checked-in files.
- **Check 5 (slow hooks):** I couldn't read transcript hook timings.
- **Check 7 (version currency):** `claude --version` needed approval.
- **Checks 8 and 9 (permissions):** I couldn't see your user-level `defaultMode`, and I had no denial data. I'm proposing no permission changes, because I won't widen permissions without evidence.
- **Check 10 (the `/usage` rows):**
- [Redacted in this copy: /doctor quoted the operator's own `/usage` figures here. The full report is in the factory's retained results.]

## To finish the rest
Re-run `/doctor` in a session where home-directory reads are permitted, or approve the blocked commands when prompted. I'd then run the full report and the two confirmation questions: one for cleanup, and a separate one for permissions.

# /doctor prompt-audit .

# Prompt audit: `.`

**Assumptions**
- **Scope:** the whole working directory.
- **Target model:** the model running this audit (Sonnet 5.5). `plugins/claudit/` files that pin `model: sonnet` are audited against Sonnet 5.5.
- **Excluded:** `.claude/settings.json` (it can hold secrets), and anything outside the repo, including `~/.claude`.
- **Read:** `CLAUDE.md`, `AGENTS.md`, `docs/repository.md`, `plugins/claudit/agents/auditor.md` and `plugins/claudit/skills/claudit/SKILL.md`. I did not read `references/apply.md`, `docs/operations/*.md` or `evals/` (the eval fixture files are test data, not prompts).
- **Verified by reading file lists:** `scripts/check-plugin-versions.sh`, `docs/{catalog,delivery,marketplace,plugin-development}.md` and `.python-version` (3.11.15) exist. `bin/container` does not, and `docs/repository.md` says so itself.
- **Git history:** I did not run `git blame`, so no finding below is dated by history.

## Summary
Nothing here needs a high-confidence change. The surface is mostly current: no pressure language, no dated scaffolds, no contradictions between files. Only a few items are worth a look:
- **History narration:** `docs/repository.md` has lines that describe past events instead of the current rule.
- **Possible mismatch:** `SKILL.md` allows two `claudit.py` subcommands in its frontmatter but also tells the model to run a third.
- **Rule outside the files:** the repo's "no generated-tool trailers" rule conflicts with the commit attribution this session was given. It is not in any audited file.

**Counts**
- **Group 1 (dated prompt text):** 0
- **Group 2 (instruction files):** 2 medium, 1 low
- **Group 3 (tool descriptions):** not applicable
- **Group 4 (request config):** not applicable. No request-building code is in scope. The `auditor` agent roster has one agent and nothing redundant.

## Findings (highest confidence first)

**1. History narrative in the verification section** (medium)
- **Location:** `docs/repository.md:42-43`
- **Evidence:** "The initial compatibility run also passed on Python 3.9.6; release evidence uses the pinned runtime, not the system default."
- **Pattern:** Group 2, history narratives. It also duplicates line 35, which already says `bin/sdlc check` passes on 3.9.6.
- **Why obsolete:** "initial run" records one past event. The rule that matters ("release evidence uses the pinned runtime") is already implied by lines 28-37.
- **Action:** `rewrite` to keep only the rule.

**2. Retired-hook archaeology** (medium)
- **Location:** `docs/repository.md:63-67`
- **Evidence:** "Repository push hooks and Claude shell-match hooks have been retired… Existing clones with the old installed pre-push hook may remove that specific hook after inspecting it; do not replace personal hooks."
- **Pattern:** Group 2, history narratives and migration-relative phrasing ("have been retired").
- **Why obsolete:** The text is a diff against an earlier setup. The current rule is "clean-checkout evidence is the verification gate".
- **Action:** `rewrite` to state the current rule. The advice for old clones only matters to contributors who have that hook, so drop it unless they are still around. That is a call for you to make, and the reason for medium confidence.

**3. `dismiss` is not in the skill's allowed tools** (low)
- **Location:** `plugins/claudit/skills/claudit/SKILL.md:5` and `:200`
- **Evidence:** `allowed-tools` lists `claudit.py scan *` and `claudit.py new-pages *`. Step 6 tells the model to run `claudit.py dismiss …`.
- **Pattern:** Group 2, instruction mismatch.
- **Why it may be fine:** `dismiss` writes a file, so leaving it unlisted may be deliberate (it prompts the user). I can't tell without the author's intent.
- **Action:** `flag`. The author should confirm whether the prompt is intended.

**4. Commit attribution rule differs from this session's instruction** (low)
- **Location:** `docs/repository.md:15-16`
- **Evidence:** "retain honest author/committer attribution without generated-tool trailers."
- **Pattern:** Group 2, cross-source conflict. The other source is the session's attribution reminder, not an audited file.
- **Action:** `flag`. The repository rule takes precedence, and I would follow it when committing here. No edit is proposed.

## Left alone
- `AGENTS.md:41` offers `bin/container bin/ci` "where supported", and `docs/repository.md:39-41` explains that this repo has none. That is an explained override, not a conflict, and the hedge is accurate.
- The escalation list and the "do not require product-owner approval" bullets in `AGENTS.md` are reasoned constraints and stay.
- `auditor.md` and `SKILL.md` have no emphasis or step-script problems. Their numbered steps cover genuinely ordered work and exact commands.

## Proposed diff
Only findings 1 and 2 qualify (medium confidence, concrete action). I have not applied anything.

```diff
--- a/docs/repository.md
+++ b/docs/repository.md
@@ (line 42-43)
-The initial compatibility run also passed on Python 3.9.6; release evidence uses
-the pinned runtime, not the system default.
+Release evidence uses the pinned runtime, not the system default.
@@ (line 63-67; wording to be confirmed against the full paragraph)
-Repository push hooks and Claude shell-match hooks have been retired; clean-checkout evidence
-is the verification gate. Existing clones with the old installed pre-push hook
-may remove that specific hook after inspecting it; do not replace personal hooks.
+Clean-checkout evidence is the verification gate; the repository installs no push
+or shell-match hooks. Do not replace personal hooks.
```

I didn't see lines 62-63 or 67 in full, so check the rewrite against the whole paragraph, including the `scripts/check-plugin-versions.sh` sentence, before taking it.
