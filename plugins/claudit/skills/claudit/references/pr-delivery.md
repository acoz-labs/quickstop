# Safe selected-fix delivery

An audit does not authorize a PR or consumer edits. Honor explicit existing
local/PR authorization; otherwise ask once with concrete selected fixes and delivery
choices. Do not apply edits and then decide how to isolate them.

## Local edits

Reread targets before each edit, record the narrow diff and preserve unrelated
staged/untracked work. Do not stage, stash, reset, checkout over, or commit consumer
files as part of local delivery. If an overlapping concurrent edit prevents a
safe update, report it without reverting anyone's work. Personal scope requires
explicitly covered authorization and is never eligible for a PR.

## PR delivery

1. Check Git and `gh` availability, current branch and the intended authenticated
   identity/repository. Read repository delivery instructions. Verify the chosen
   remote base exists and includes the current HEAD; if the consumer has unpublished
   commits, explain that a PR against that base would include unrelated commits and
   choose an appropriate isolated base before proceeding. Do not push consumer
   commits as an incidental audit action. Never change global credentials/identity.
2. Before any edits, run the helper `prepare-pr --root "<consumer root>"
   --destination "<new external worktree path>" --branch "claudit/<unique-name>"
   "<selected shareable path>" ...`. It records HEAD, branch, index/worktree state,
   and authorized paths, creates an isolated worktree, and returns a receipt.
   Other dirty/staged/untracked files in the consumer remain untouched. Already
   modified selected files are reported as excluded from the isolated baseline.
   Independently apply the selected fix to clean HEAD; retain the consumer file
   untouched. If the fix depends on uncommitted context, report that conflict and
   resolve a separate local-edit outcome. Never copy the whole dirty file to the PR.
3. Apply **only selected project changes** in the new worktree. Personal/local
   settings, local instructions, auto-memory, authentication, historical mixed
   decisions and private findings/reasons are excluded. A new shared decision
   file requires explicit sharing authorization and sanitized content.
4. Run relevant syntax/native validation without executing untrusted components.
   Run `verify-pr "<receipt>"`. Inspect `git diff <recorded-head>` and untracked
   candidates in the isolated worktree for secrets, personal content and unrelated
   edits. The helper enforces path selection, not semantic privacy. If consumer
   state changed concurrently, inspect and report it; never restore its snapshot.
5. Stage only the selected reviewed paths **in the isolated worktree**, never
   `git add .`, and inspect the staged diff. Verify the exact staged name list is
   a subset of the receipt paths. Commit using the actual configured identity.
   Re-run `verify-pr` after committing (it checks against recorded HEAD), and
   inspect the commit contents/base range before push.
6. Push only the new branch and create the PR against the verified remote base.
   Use a temporary UTF-8 body file with `gh pr create --body-file` so literal
   newlines and shell text survive safely. Include problem, selected behavior,
   actual checks and material limitations. Do not publish the full personal audit
   report. Additional comments/messages require authorization; no automatic
   inline-review-comment storm is part of delivery.
7. Return actual PR URL and head. Preserve worktree/receipt on failure or while
   review needs them, stating the failed stage and recovery command. Inspect live
   remote/PR state before retrying so a transient response cannot duplicate a PR.
   Clean up only task-created resources after confirming work is safely retained
   and no longer needed. Do not reset, stash/pop or switch the consumer branch.

A failed push or PR does not justify moving the isolated changes into consumer
files without authorization. Report retained branch/worktree and the next action.
