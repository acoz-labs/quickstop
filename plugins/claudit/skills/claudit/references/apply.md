# Applying selected changes

Apply only the changes the user selected, exactly as shown in the report. Don't
widen a permission, delete a file or touch anything else without asking.

## In place

1. Check `git status --short`. If a file you'll change has uncommitted edits, show
   them and ask before editing it.
2. Make each change with the Edit or Write tool. For JSON settings, keep the
   existing keys and formatting; merge into the existing `permissions` and `hooks`
   objects rather than replacing them.
3. Validate what you changed: parse each JSON file you edited, run
   `claude plugin validate .` on a plugin you edited, and run the project's check
   if a change affects it.
4. Show the resulting `git diff` and say which changes need a restart or `/hooks`
   reload to take effect.

## On a branch with a pull request

1. Confirm `gh auth status` works and the repository has a GitHub remote. If not,
   fall back to in-place and say why.
2. Create an isolated worktree from the default branch so the user's working tree
   and index stay untouched: `git worktree add -b claudit/<short-slug>
   <temporary path outside the repo> origin/<default branch>` (fetch first). If the
   branch name exists, pick another; never reuse or reset it.
3. Apply the selected changes inside the worktree only, validate as above, and
   commit just those paths with a message naming the changes.
4. Push the branch and open the PR with `gh pr create`, listing each change, its
   reason and its source. Report the PR URL.
5. Remove the worktree with `git worktree remove <path>`; keep the branch.

If anything fails after the branch exists, stop, report what was done (branch,
commit, push) and leave it for the user to inspect. Don't retry over it.
