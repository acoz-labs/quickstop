# Software delivery

Standard version: `2026.11.05.3`.

Issues, the Project board and in-repo docs coordinate work; chat and local notes
do not replace them.

## Authority and roles

The product owner sets outcomes and constraints. Once work is assigned,
maintainer and contributor agents own its delivery: implementation, independent
review, acceptance, merge, release verification and receipts, and Project Status
moves backed by evidence. An explicit stopping point, such as planning-only,
still holds.

Agents settle design, review findings, failed-then-fixed acceptance, flakes,
review-bot noise and happy-path releases against the spec. Never weaken criteria
or fabricate evidence. Escalate to the owner only for:

- a product preference no experiment or constraint settles;
- access, secrets or a capability agents cannot get;
- money or billing;
- irreversible or high-blast operations: force-pushing shared history, migrating
  production data, broadening an allowlist or security boundary, deleting
  someone else's work;
- a deadlock that remedies did not break.

Report the blocker, evidence, attempts, options and a recommendation; continue
unaffected work.

Maintainers write issues, plans and durable docs. Contributors write code,
tests, scripts and executable config, and author code PRs; docs may ride along
with honest attribution. A different authorized maintainer reviews. Separate
GitHub accounts keep authorship and receipts apart.

## Documentation

Write, run the applicable link, format and build checks, publish. No issue,
plan, acceptance or release is needed, nor a PR unless branch protection
requires one. Label proposed behaviour as proposed. Automation-run examples,
workflows, agent authority, policy and config are not prose: they take code
review, as do mixed code and docs. Shared policy changes in the template.

## Plans

Plan before code for a new feature or user-visible behaviour; a security,
authentication or permission change; a release, storage or data-format change;
a paid eval or gate; or more than about three non-test source files. Docs-only
changes, single-file fixes, dependency bumps and approved posts need none. The
issue records `plan: required` or `plan: not required`.

The plan, `docs/changes/<issue>-<slug>/plan.md` (copy
`docs/changes/_template/plan.md`), is the PR branch's first commit, alone. An
independent maintainer reviews it before code; that is not a code review round.
Update it in the same commit as any departing change; code review checks the
diff against it. The folder stays after ship.

## Product code

1. The maintainer writes a bounded issue: outcome, acceptance criteria,
   constraints, validation, release, any stopping point, plan or not.
2. The contributor builds in an isolated worktree and tests meaningful
   behaviour.
3. The contributor's PR links the issue, covers behaviour, validation, docs,
   rollout, rollback and departures from the issue or plan, updates durable
   docs, and requests native GitHub review.
4. The maintainer reviews the current head against the spec, runs the required
   commands, and publishes findings and evidence on the PR. Fixes and responses
   land in the same PR with a new request; every new head needs new review.
5. The maintainer merges, accepts and releases. Failed acceptance returns to
   implementation, retest and review, not to the owner.

A finished coding turn starts the handoff, not acceptance. The coordinator
notices handoffs unprompted; a review request starts no agent. Inspect
interrupted work before retrying, and never start a second implementer or lose
the owning task.

Rendered changes need functional, accessibility and visual evidence from the
real experience, scaled to impact (`docs/operations/ui-acceptance.md` where
present).

## Agent verification

The author never verifies their own change. Another authorized maintainer proves
the current head, and at release the exact candidate, against the real artifact,
in a fresh worktree or container. A compile, coverage, green CI, `APPROVE` or
account switch is not proof. Scale proof to blast radius:

- doc or comment typo: read the change, run the format check;
- behaviour change: meaningful tests plus the issue's scenario;
- release, migration, permission change or user-visible flow: exercise the
  retained artifact or deployed candidate live, including reachable failure and
  recovery paths.

Record what ran, what you saw and what was not covered. Installed Cursor pstack
skills may structure the proof but are optional. Stacked-PR hosts and
unattended overnight merges are not defaults. Merge the reviewed head with its
receipt (`docs/operations/local-verification.md`).

## Acceptance and release

The maintainer accepts the exact candidate against the issue criteria,
separately from contributor tests, keeping the commit, artifact identity,
scenarios, results, reviewer and openable evidence. The code author cannot be
the sole acceptor.

- Service: build once from a fixed merged commit, validate that artifact locally
  or in a temporary production-like environment, accept, promote it, verify
  production, record the release. Staging is optional.
- Artifact: validate and nominate without fictional staging, accept, publish,
  verify.
- Non-deployable: a reviewed merge plus its receipt completes delivery.

Exercise migrations, config, permissions and integrations in isolation when
relevant, never destructively on production data. Release-bearing PRs say `Refs
#N` and the issue stays open until delivered; `Closes #N` only when merge
finishes the work.

Changed bytes need new acceptance. A missing acceptance capability is work to
do, never invented success. Releases inside an assigned delivery task need no
new owner sign-off; unrelated data migrations are outside it.

## Workspace cleanup

When a PR is merged or closed (or the task ends), remove the task's unneeded
worktrees, review and verification ones included, and temporary resources.
First check PR status, local, untracked and ignored files, unpushed commits, and
use by processes or sessions; a clean `git status` is not enough. Keep
unfinished work, evidence, artifacts and recovery material. Never force past
changes, locks or use. Touch only what the task created.

Remove worktrees with Git; prune only once directories are gone and commits
kept. Delete a local branch only when its commits are merged or kept and no
other task needs it; a closed
PR proves no merge. Report cleanup at closeout, and for anything kept, why, the
owning role and what frees it, with no machine paths in public.

## Project state

`Inbox -> Ready -> In Progress -> Review -> Release -> Done`

The acting maintainer moves Status when the evidence exists. Blocked is a real
dependency; Parked is deliberate deferral. Discovery and design are not states.
Ready needs an executable issue. Failed review or acceptance returns to In
Progress. Migrating old states keeps the next action and evidence.

## Standards maintenance

Record the change once, update and validate the template, cascade to every
active org repository and verify conformity. No pilots or waves: it is
incomplete while any active target is unresolved; recheck archive status at the
end. Repo checks still run. Preserve product content and resolve conflicts in
the same task. Change generated distributions at their source. Maintenance never
authorizes an unrelated deployment.

## Enforcement

Run `bin/sdlc check` for conformity and `bin/sdlc review` before a code merge.
Review checks live identity, exact head, reviewer permission and an independent
receipt for every configured command, with environment, outcomes and sanitized
logs. Changed config, a stale or failed latest run, or an edited log fails. Use
branch protection where supported; audits only detect. Record enforcement gaps.

## Historical work

Past approvals, exceptions and releases stay evidence but authorize no new
candidate. This standard supersedes earlier owner gates and self-review for new
work. Plans already in
`docs/plans/` stay. Existing PRs keep real authorship and get independent
review.
