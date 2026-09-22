---
name: writing-audit
description: Audit and adjust the writing a piece of work produced, including workflow artifacts, code comments in the diff, PR descriptions, and unpushed commit messages. Use once draft PRs are open and before they go ready for review, or when asked to audit comments, descriptions, or writing. Running it before the PRs exist leaves their descriptions unaudited.
argument-hint: (no args — audits the artifacts, diff, and PRs for the current branch)
---

# Writing Audit

Within the caller’s authorized scope, audits and ADJUSTS the writing our work leaves behind. This skill is the **procedure**; it does not carry the rules.

## Where the rules live

Resolve all relative paths from this installed skill directory, never the working directory. Read the reference for each surface before auditing it. Do not audit from memory, and do not audit from any summary of the rules, including one in this file.

| Surface | Reference |
|---|---|
| Workflow artifacts | `../writing-style/references/artifacts.md` |
| Questions asked of me | `../writing-style/references/questions.md` |
| Code comments | *(none yet; use the output style's section)* |
| PR descriptions | *(none yet; use the output style's section)* |
| Commit messages | *(none yet; use the output style's section)* |

A surface with no reference falls back to that surface's section in the output style, which is thinner but not nothing. Package maintainers adding a reference update this table and `../writing-style/SKILL.md` in the source repository. An ordinary audit does not edit installed plugin files.

<!-- Don't leave a path here for a file that doesn't exist. A broken pointer
     reads as "load this" and fails silently when the read comes back empty. -->

**The floor is the `writing-for-humans` output style, and this audit is void without it.** It carries rules that live in no reference: the punctuation preferences, the spoken-voice test, personal voice patterns, and the context-independence test that item 1 below leans on entirely. Check whether its rules are already present. If they are not, read `../../output-styles/writing-for-humans.md` directly. Do not change the selected output style. Auditing against the references alone silently drops half the standard.

With the floor confirmed present, the per-surface references are what you still need to load.

**Why this file names no rules.** An audit that carries its own copy of the standard drifts from the standard, and then quietly enforces the older, weaker version. If a rule seems to be missing, suggest the improvement separately from the writing audit. Package maintainers change the reference in the source repository, not this skill; ordinary audits never modify installed references.

## What to audit

### 1. Workflow artifacts

Any durable markdown this work produced for me to read: design notes, triage write-ups, decision records, scratch docs. They get audited first because this is the surface where the damage is worst and least visible.

The failure to hunt for is prose that is terse, precise, correct, and undecipherable to anyone who wasn't in the session. It passes every voice rule, which is why it survives. Run the context-independence test from the output style against every line: an identifier as a sentence's subject, a term coined mid-session used as shared vocabulary, a pointer standing in for what it says, a claim whose stakes are never stated.

The fix is never to delete the citation. Say the thing in plain words, move the `file:line` behind the sentence, leave the evidence intact.

Anything that asks me a question gets checked against `../writing-style/references/questions.md`. Use the optional cold reader within the bounds in `../writing-style/references/cold-reader.md`.

### 2. Code comments we added or modified

Comments we authored in the requested branch diff plus relevant uncommitted changes. Leave unrelated or other authors’ work untouched. Judge each against the code-comments reference if one exists, otherwise the output style's Code comments section, plus any team coding standards. Load them; don't work from a remembered version.

### 3. PR descriptions

For this branch's PRs (`gh pr view`), against the PR-descriptions reference if one exists, otherwise the output style's section. Template sections are structure, not verbosity: where the repo has a PR template, every section stays, with a short `N/A` where it doesn't apply. Tighten the prose inside them; never strip the scaffold.

### 4. Unpushed commit messages

Only if they have not been pushed and history rewriting is already authorized. Otherwise suggest revised wording. Same sources as above. Never rewrite pushed history.

## Out of scope, deliberately

Chat messages and ticket comments are drafted and sent in the moment, with their references loaded at the time, and they leave this branch. They are not part of a change's leftover writing, so they are not swept here. If one needs fixing, that's an edit in the moment, not an audit pass.

## How to act

- **Fix within scope.** Edit local drafts when authorized; a review-only request means report findings without edits. Commit only within existing authorization. Preserve facts, uncertainty, templates, attribution and required trailers.
- **Artifacts** are local files and get corrected directly. If an artifact is wrong about *substance* rather than wording, that's a separate conversation, not this skill. Don't quietly restate a decision while tidying prose.
- **PR descriptions**: draft the improvement and show the old and new versions. Apply it with `gh pr edit --body` only when that external change is already authorized by the user or the governing workflow; otherwise leave the draft for approval.
- **When unsure whether something is load-bearing**, a comment that might carry real context or an artifact line that reads oddly but may be precise for a reason, keep it and flag it in the report. Deleting something you didn't understand is worse than leaving it.
- **Report**: what was deleted, rewritten, and kept-and-flagged; the artifact sections rewritten; the description diffs applied.
