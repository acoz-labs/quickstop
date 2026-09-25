# Portable verification and release

Local execution is the default. The same commands can run in an isolated checkout
on a development machine or trusted server. A continuously running backlog worker
is not installed by this standard. GitHub hosts issues, PRs, reviews and receipts;
Actions is an optional scheduler, not a delivery prerequisite.

## Review a change

The contributor implements and tests. The maintainer inspects the specification
and diff, checks out the exact PR head in a fresh worktree, installs pinned
dependencies, and independently runs the configured commands:

```sh
bin/sdlc-evidence run --repo OWNER/REPO --output /private/evidence/run-1
# Inspect the retained logs; redact credentials or personal data if present.
bin/sdlc-evidence publish --receipt /private/evidence/run-1/receipt.json \
  --subject PR_NUMBER --expected-actor MAINTAINER --logs-reviewed \
  --summary 'Describe checks, findings, fixes and remaining limits honestly.'
# Submit the actual current-head code review separately.
bin/sdlc review --repo OWNER/REPO --pr PR_NUMBER --expected-actor MAINTAINER
# Merge with the returned exact head as GitHub's expected-head condition.
bin/sdlc audit --repo OWNER/REPO --before PRE_MERGE_SHA --sha MERGED_SHA
```

The actor is supplied by the caller's private execution policy, never hardcoded in
the repository. Verify Git authorship and per-process credentials before writes.
Do not use one global account switch for concurrent roles. A credential switch
alone is not independent review or verification.

The runner retains complete logs, command exit codes, commit and configuration
identity, host platform, timestamps and artifact identity where applicable.
Commands execute with pipeline failure detection. Dirty or changed tracked
content and untracked files fail verification. Ignored dependency/build caches
are not proof of hermetic execution: use pinned dependencies and an isolated
container when the stack needs it. Containerized checks must fail if required
runtime dependencies are absent, never silently skip application tests.

Evidence directories are private and outside the checkout. Publishing requires
explicit log inspection by the acting agent, not owner approval. Published logs
are split into complete linked comments; hashes detect later edits. Original and
sanitized-log hashes are retained separately. Comments inherit repository
visibility: public repository evidence must contain no private host configuration,
credentials, customer data or local account paths. Redact before publication.
GitHub authenticates the maintainer's attestation, not execution itself; this is
procedural enforcement, not cryptographic proof or a protected-branch substitute.

A later failed receipt revokes success on that revision. Updated code requires
new verification and review. Keep failed attempts and publish their outcome; do
not conceal a failure by presenting an earlier successful receipt. Documentation
uses its simpler write/validate/publish lane.

After review or verification, apply the [workspace-cleanup policy](sdlc.md#workspace-cleanup).
Keep required evidence outside disposable worktrees, and record any workspace
retained for a later acceptance or release step with its cleanup trigger.

## Accept and release an immutable candidate

After merge, select a fixed commit and build a retained artifact once. Run the
repository's real artifact-build procedure; a source archive cannot stand in for
a deployable binary or container. Record its SHA-256 identity. If merge changed
the tested bytes, rerun validation at the merged revision before acceptance.
The maintainer declares the complete implementation PR set for the delivery issue:

```sh
bin/sdlc-release nominate --repo OWNER/REPO --issue ISSUE --sha FULL_SHA \
  --artifact IMAGE@sha256:DIGEST --pr IMPLEMENTATION_PR \
  --expected-actor MAINTAINER --output /private/evidence/candidate.json
bin/sdlc-evidence run --repo OWNER/REPO --phase acceptance \
  --artifact IMAGE@sha256:DIGEST --candidate /private/evidence/candidate.json \
  --report /private/evidence/acceptance-report.json \
  --output /private/evidence/acceptance-1
bin/sdlc-evidence publish --receipt /private/evidence/acceptance-1/receipt.json \
  --subject ISSUE --expected-actor MAINTAINER --logs-reviewed \
  --summary 'Acceptance criteria exercised, observed outcomes and evidence.'
bin/sdlc-release gate --repo OWNER/REPO --issue ISSUE --sha FULL_SHA \
  --artifact IMAGE@sha256:DIGEST --expected-actor MAINTAINER
bin/sdlc-release promote --repo OWNER/REPO --issue ISSUE --sha FULL_SHA \
  --artifact IMAGE@sha256:DIGEST --expected-actor MAINTAINER \
  --output /private/evidence/release-1
bin/sdlc-release finalize --receipt /private/evidence/release-1/release.json \
  --expected-actor MAINTAINER --logs-reviewed --summary 'Delivered outcome and verification.' --close
```

Repeat `--pr` for every implementation PR. For a retained file, use
`sha256:DIGEST` and supply `--artifact-file PATH` during acceptance; its bytes are
hashed before and after execution. An OCI image must be addressed by digest.
Acceptance hooks receive `RELEASE_SHA`, `RELEASE_ARTIFACT` and, for files,
`RELEASE_ARTIFACT_FILE`. Run those exact bytes. Browser/visual acceptance can be
performed by the maintainer agent and attached as additional evidence; it does
not imply routine owner attendance. Automated acceptance commands supplement,
not replace, evaluation of the issue's actual product criteria.

Repositories list concrete `acceptance_criteria` in configuration and describe
their execution in `docs/delivery.md`. The maintainer executes those scenarios
and the issue-specific criteria, then supplies a report; this can include browser,
native installation, worker-recovery or temporary-environment observations. The
report shape is:

```json
{
  "repo": "OWNER/REPO",
  "sha": "FULL_COMMIT_SHA",
  "artifact": "sha256:ARTIFACT_DIGEST",
  "scenarios": [
    {
      "criterion": "issue-criteria",
      "result": "passed",
      "observation": "Describe the actual steps and observed behavior.",
      "evidence": ["https://github.com/OWNER/REPO/issues/ISSUE#issuecomment-ID"]
    }
  ]
}
```

Record every configured criterion, plus the actual issue-specific scenarios.
Use `failed` for rejected criteria; publishing that receipt revokes readiness.
An HTTPS URL is a locator, not proof of its contents: the maintainer must open
and inspect the evidence before attesting. The gate checks completeness, identity,
provenance and verdicts; it does not judge a screenshot or product requirement.
The runner always reruns validation at the candidate commit. Optional configured
`acceptance` commands add automated artifact checks; they cannot replace the
required scenario report. No `true` placeholder is an acceptance implementation.

The gate binds acceptance to repository, issue specification, full implementation
set, commit, artifact and configuration. It excludes implementation PR authors
from acceptance and promotion. Changed specifications or nominations require
new acceptance. Persistent staging is optional; temporary isolated instances are
appropriate for service startup, migrations and external integration scenarios.
No release is permitted merely because coverage is high or a different main
revision once passed tests.

Repository promotion hooks deploy the retained artifact without rebuilding it.
They must retain the previous artifact/configuration, serialize promotions to a
target, and prepare required database backups before migration. Verification must
confirm the deployed artifact identity plus application health and relevant
smoke scenarios. Rollback hooks restore the retained prior state where safe;
irreversible data changes require an explicit recovery procedure. Never perform
unrelated production/data changes as part of standards maintenance.

Promotion writes a receipt before side effects. After interruption, inspect live
deployment state and use `--resume` with the same directory: resume verifies the
candidate without redeploying it. If recovery requires another deployment, first
reconcile the previous attempt and record the recovery decision, then use a new
attempt directory. Finalize publishes release evidence and optionally closes the
issue only when its complete delivery scope is satisfied.

Where deployment is an agent-executable runbook rather than a single script,
run the gate first, retain a private attempt record before side effects, and
execute the repository's documented deployment and recovery procedure. Record
the actual results of every configured `release_criteria` in the same report
shape, adding `previous_artifact` (or an explicit initial-release statement) and
`recovery` with the real rollback/restore procedure and evidence. Then use:

```sh
bin/sdlc-release record --repo OWNER/REPO --issue ISSUE --sha FULL_SHA \
  --artifact IMAGE@sha256:DIGEST --expected-actor MAINTAINER \
  --report /private/evidence/release-report.json \
  --output /private/evidence/release-1/release.json
# Inspect evidence and finalize with the command above.
```

`record` is an authenticated maintainer attestation, not a deployment command or
proof inferred from tests. It must never be used to invent a deployment. Do not
run both promotion paths. This supports existing native/provider runbooks without
requiring another deployment service or routine owner approval.

## Retained candidates built before SDLC adoption

Do not rebuild an already retained artifact merely to add delivery configuration,
or claim its binaries came from a newer commit. The normal path always uses the
product source's own configuration. A narrowly scoped transition is available
only when that source has no `.sdlc/config.json`.

In an independently reviewed descendant commit on the same repository's default
branch, add an explicit `retained_candidates` entry to `.sdlc/config.json`:

```json
{
  "retained_candidates": [
    {
      "sha": "FULL_ORIGINAL_SOURCE_SHA",
      "artifact": "sha256:EXACT_RETAINED_DIGEST",
      "validation": ["REPOSITORY_ORIGINAL_FULL_VALIDATION_COMMAND"],
      "reason": "Explain the original suite and why newer SDLC commands cannot run in this source."
    }
  ]
}
```

This is an addition to the complete repository configuration, not a replacement.
The entry may replace only validation commands; all acceptance/release criteria,
delivery authority and other configuration remain those of the pinned policy.
Review the commands against the original product: no placeholder success or
substitution of template conformity for application tests. Policy/configuration
changes use the code-review lane, not documentation-only approval.

Nominate with `--policy-sha FULL_REVIEWED_POLICY_SHA`, preserving the original
`--sha`, artifact and complete implementation PR set. The gate checks policy
ancestry/default-branch reachability, original configuration absence and the
exact entry; API failures are not absence. The policy must be the merge of a
same-repository PR with independent exact-head approval and authenticated local
validation evidence. Its complete tree must equal that reviewed head; merge-time
changes require a newly reviewed policy PR. Nomination retains the policy PR's
number, head, merge and author, and the gate rechecks that provenance and proof.
Both policy identity and effective
configuration are bound to the nomination and acceptance receipt. This is not
permission to override an existing source policy or use moving `main`.

For acceptance, use clean separate checkouts of original source and policy:
pass `--root ORIGINAL_CHECKOUT --policy-root POLICY_CHECKOUT` to the current
`sdlc-evidence run`, plus the saved nomination and scenario report. Commands run
in the original source, not the policy checkout. The runner checks both heads,
origins, policy ancestry and configuration identity, and refuses modified
checkouts or artifact bytes. Keep the evidence directory outside both checkouts.
Tools can be invoked from the reviewed control checkout without copying them
into or dirtying the original source.

Publication uses the repository's reviewed same-byte runbook, followed by
`sdlc-release record` and `finalize`. Generic scripted `promote` intentionally
refuses this transition: newer control scripts cannot silently execute as if
they belonged to the old product checkout. Independently verify the retained
payloads, run the gate, retain an attempt record, execute the actual publisher,
verify downloaded bytes and recovery, then attest the observed results.

The policy is immutable, not automatically refreshed. To replace or revoke a
nomination, issue a new nomination under a reviewed policy and repeat acceptance;
a newer failed acceptance also revokes readiness. Editing a policy elsewhere does
not rewrite an existing pinned decision. Issue-specification changes invalidate
the old nomination. Historical self-review never supplies independent acceptance.

## Optional automation

Explicitly enable `SDLC_ACTIONS_ENABLED=true` only for approved self-hosted
execution. Shared jobs require both `self-hosted` and `trusted-linux-x64` labels;
there is no hosted fallback. Keep untrusted fork code off credential-bearing
machines. Use disposable workers/containers and scoped credentials as appropriate.
Actions artifacts/storage may have separate charges; local execution needs no
Actions minutes. A missing runner does not substitute for a failed test: run the
same checks locally and publish independent evidence instead.

Where the hosting plan cannot enforce private branch protection, premerge checks
and postmerge audits remain procedural/detective controls. Local evidence does not
remove that limitation. A paid protection upgrade is an independent decision.
