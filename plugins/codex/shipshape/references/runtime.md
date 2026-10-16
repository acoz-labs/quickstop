# Runtime obligations

The canonical public guide is Quickstop's `workflows/shipshape` at the guide
commit recorded for this run. These compact obligations are sufficient at runtime;
they do not import organization tooling or replace the consumer's local rules.

The assignment and stronger repository rules bound all effects. Existing
`.sdlc/config.json` remains authoritative. Read-only tasks produce proposals only.
Pin and record exact spec, config, package digest, guide, harness and required
tool revisions. No automatic enrollment or upgrade. Missing capabilities block.

Implementation needs independent fresh-context executing review on the current
head. Correct findings internally, then re-review changed bytes. Reviewer fixes
need another reviewer. Account separation is attribution, not execution proof.
Two correction rounds precede replan. Approval alone cannot establish readiness.

Reuse trusted `bin/sdlc-evidence`, `bin/sdlc review`, exact-head conditional merge,
`bin/sdlc audit`, and `bin/sdlc-release` nomination/acceptance/gate procedures
where the consumer already has them. This package neither installs these tools
nor copies gate logic. If they are required and absent, wait. The trusted adapter
independently validates receipts and authority before any effect, and records
actual process/session provenance. JSON fields cannot authenticate a role.

After merge, retain the actual merged candidate and immutable artifact. Acceptance
and publication remain separate independently executed responsibilities. A helper
decision or valid schema proves no scenario ran. Reconcile uncertain operations
before another effect, preserve bounded handoffs and explicit stopping points.

Reviewer preflight requires clean tracked and untracked source bytes. Keep run
fixtures and handoffs outside that checkout. Author work in progress is allowed,
but HEAD does not identify it: the trusted adapter must bind exact working bytes
to evidence and the candidate independently reviewed. Result schema 2 records
every required command as executed with integer exit, or not-run with reason and
no exit. Preserve partial proof when blocked or interrupted; never invent success.

Git inspection uses platform /usr/bin/git, strips inherited Git variables and bounds each call to ten seconds. Reviewer preflight compares raw tracked bytes and index entries with the committed tree, without filters or status caches. It rejects assume-unchanged, skip-worktree, sparse configuration, submodules, filters, normalization configuration, symlinks and unsupported modes; ignored/untracked files also prevent a clean reviewer checkout. Author work in progress is permitted. No consumer config or index is normalized. This advisory inspection is not a hostile-repository sandbox or protection against concurrent filesystem changes.
