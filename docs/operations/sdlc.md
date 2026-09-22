# Software delivery

Standard version: `2026.09.21.3`.

## Authority and roles

The product owner supplies desired outcomes and constraints. Once work is
assigned, the maintainer and contributor are delegated authority to shape,
implement, review, accept, merge, release and verify it within that scope.
An explicit stopping point such as planning-only still applies. Routine design
choices, review findings and failed acceptance are resolved internally, not
returned to the owner for another approval. Escalate only a genuine deadlock
requiring unavailable information, access or a change to an explicit constraint.
Report the blocker, evidence, attempted remedies, choices and recommendation;
continue unaffected work. Never weaken criteria or fabricate evidence to proceed.

Maintainers author issues, Project updates, plans, READMEs and durable docs;
contributors author code, tests, scripts and executable configuration. Code PRs
are authored by the contributor and reviewed by a different authorized
maintainer against the current head. Documentation commits may accompany code
in the same PR with honest attribution. Account names, credentials, machine
paths and personal execution instructions are not part of this shared standard.
Another person can comply with their own tools and accounts.

## Documentation and planning

Write, run applicable link/format/build checks, and publish. No mandatory issue,
planning PR, acceptance or release ceremony. A documentation PR is optional unless
repository protection requires it. Routine prose corrections can be published
by a maintainer directly. Proposed behavior must be labeled as proposed.

Classify by effects: executable examples used by automation, workflow files,
agent authority, policy and configuration changes are not ordinary prose. Use
code review for executable changes and standards maintenance for shared policy.
Mixed code/documentation changes follow the code workflow.

## Product code

1. Maintainer prepares a bounded issue: outcome, acceptance criteria, constraints,
   validation and release expectations, and any explicit stopping point.
2. Contributor implements from an isolated branch and tests meaningful behavior.
   Use a plan only when risk or design complexity justifies one. Maintainer owns
   the plan, using contributor findings. A separate planning PR and six-file pack
   are not prerequisites for Ready or implementation.
3. Contributor opens a PR linking the issue and, when ready, requests the
   designated independent maintainer through GitHub's native PR review request.
   Describe behavior, validation,
   documentation impact and rollout/rollback when relevant. Reconcile against
   the issue and any actual plan; explain material deviations. Promote durable
   knowledge and retire completed temporary plans.
4. Maintainer reviews the current code and specification independently. A
   credential switch alone is not a review. Record findings and resolutions.
   Contributors address findings in the same PR and re-request review after
   revisions. Changes after approval require review of the new head. Required repository
   commands pass in a clean checkout. The maintainer independently runs them and
   publishes current-head evidence; an available Actions runner is not required.
5. Maintainer merges and continues through candidate acceptance and release.
   Rejected acceptance returns to implementation, followed by retest and review.
   Do not ask the owner to approve normal transitions.

A finished coding turn starts the handoff; it does not establish acceptance.
Keep review findings, responses and current-head evidence on the PR. For assigned
agent work, the coordinator is responsible for noticing the handoff and continuing
review without another owner prompt. A GitHub review request records assignment;
it does not itself start an agent. Execution hosts may use their own bounded
monitor or notification mechanism, without a mandatory UI or always-on backlog
processor. Interrupted work must be inspected before retrying, and retries must
not create duplicate implementers or lose the owning task.

Meaningful rendered changes require functional, accessibility and visual evidence
appropriate to their impact. Review the actual experience, not screenshots alone.
Use docs/operations/ui-acceptance.md for evidence details where present.

## Acceptance and release

The maintainer performs acceptance separately from contributor tests, against the
issue's criteria and exact candidate. Retain commit, immutable artifact identity,
scenarios, results, reviewer and openable evidence. The code author cannot be the
sole product acceptor. A maintainer or agent may dispatch acceptance and release
workflows; workflow_dispatch does not imply mandatory human attendance.

Service: build once from a fixed merged commit, validate the retained artifact
locally or in a temporary production-like environment, accept, promote that same
artifact, verify production and record the release. Persistent staging is optional.
A moving main branch, coverage percentage or contributor test report alone is not
acceptance. Exercise migrations, configuration, permissions and integrations in an
isolated environment when the change requires it. Never use production data for
destructive acceptance. Retain backup/recovery plans for irreversible migrations. Artifact: validate and nominate the
artifact without fictional staging, accept and publish/verify. Non-deployable:
reviewed merge and checks complete delivery when no release target exists.
Keep release-bearing issues open until their delivery profile is complete.
Use a top-level `Refs #N` for those PRs; `Closes #N` only when merge completes work.

Preserve exact-candidate nomination, issue/implementation-set binding, acceptance
statuses, rollback, resumable deployment receipts and post-release verification.
A retry must inspect existing deployment evidence before repeating a deployment.
Do not reuse an old acceptance verdict for changed bytes. Missing acceptance
capabilities are explicit implementation work, never invented success.
Production and publication within an assigned delivery task need no new owner
sign-off. Live unrelated data migrations remain outside that task's scope.

## Project state

`Inbox -> Ready -> In Progress -> Review -> Release -> Done`

Blocked identifies a real unresolved dependency. Parked is deliberately deferred.
Discovery and design are preparation activities, not compulsory separate states.
Ready requires an executable issue, not a planning PR. Release includes candidate
validation, acceptance and promotion. Failed review/acceptance returns to In
Progress. Preserve the next action and evidence while migrating older states.

## Standards maintenance

Record the adjustment once, update and validate the template, then cascade to
ALL active organization repositories and verify conformity. There are no pilots,
rollout waves or optional adoption backlog. The operation is incomplete while
any active target remains unresolved. Archive status is rechecked at completion.
The template publishes organization defaults as well as managed repository files.

Maintainers author policy/docs; contributors author executable changes in PRs;
maintainers review. The shared decision is sufficient rationale; do not create
recursive discovery, solution-design or product acceptance ceremonies for the
maintenance operation. Repository-specific checks still run. Updating delivery
machinery does not itself authorize an unrelated application deployment.

Maintain one version with repository-specific configuration for stack, commands
and delivery profile. Preserve product content. Conflicts are resolved in this
same task, not silently overwritten or deferred. Generated distributions must
be changed through their authoritative source and publication process.

## Enforcement

Run `bin/sdlc check` for managed-file conformity and `bin/sdlc review` before a
code merge. Review verification uses live GitHub identity, exact head, reviewer
permission and an independent authenticated receipt for all configured commands.
The receipt includes environment, command outcomes and openable sanitized logs.
A changed configuration, stale run, failed latest run or altered log fails the gate.
See `docs/operations/local-verification.md` for portable commands and release flow. Documentation-only changes do not
need code approval. Maintainers still validate documentation and correct scope.
Local execution is the default. Optional Actions run only on explicitly enabled
trusted self-hosted runners; never fall back silently to paid hosted compute.
GitHub authenticates the receipt publisher, not the machine execution. Two account
authorship is not host isolation; use a fresh worktree/container for independent
verification and do not expose operator credentials to untrusted test code.
Use branch protection where supported; post-push audits detect rather than
prevent unauthorized pushes. Record actual enforcement limitations honestly.
Personal execution environments must verify Git authorship and authenticated
identity immediately before writes, with isolated credentials for concurrent
roles and no fallback to an unintended account.

## Historical work

Historical approvals, exceptions and releases remain evidence. This standard
supersedes prior mandatory owner gates and routine engineering self-review for
new work. Existing PRs retain real authorship and receive an eligible independent
review; never rewrite attribution. Preserve open issue/PR links and acceptance
records while transitioning. A historical exception is not authority for a new
candidate.
