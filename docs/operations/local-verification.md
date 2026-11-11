# Portable verification and release

Commands run locally in an isolated checkout; Actions is optional.

## Review a change

The maintainer reads the spec and diff, checks out the exact head in a fresh
worktree, installs pinned dependencies and runs:

```sh
bin/sdlc-evidence run --repo OWNER/REPO --output /private/evidence/run-1
bin/sdlc-evidence publish --receipt /private/evidence/run-1/receipt.json \
  --subject PR_NUMBER --expected-actor MAINTAINER --logs-reviewed \
  --summary SUMMARY
# Submit the actual current-head code review separately.
bin/sdlc review --repo OWNER/REPO --pr PR_NUMBER --expected-actor MAINTAINER
# Merge with the returned exact head as GitHub's expected-head condition.
bin/sdlc audit --repo OWNER/REPO --before PRE_MERGE_SHA --sha MERGED_SHA
```

The actor comes from the caller's private policy, never the repo. Check Git
author and identity before each write, with per-process credentials per role,
never a global account switch or fallback account. Keep operator credentials
from untrusted code.

The runner keeps full logs, exit codes, commit, config, platform, timestamps and
artifact identity, and fails on pipeline errors, changed tracked files or
untracked files. Caches are not hermetic: pin dependencies and use a container
when needed. Containerized checks fail on missing dependencies, never skip
tests.

Keep evidence private, outside the checkout. The publishing agent reads the
logs for host config, credentials and customer data before passing
`--logs-reviewed`. Publishing strips terminal escape codes, such as colours,
and the other control characters GitHub would rewrite, then redacts local
paths, ignoring case:

- the home directory becomes `~`;
- the system temp directory, `TMPDIR`, `/tmp`, `/var/tmp` and `/var/folders`
  (and their resolved forms, such as `/private/tmp`) become `{tmp}`;
- the account name, as a whole word inside any path, becomes `{user}`. A
  short account name such as `ci` also replaces `ci` in unrelated paths.

A prefix counts only where a path starts and ends, so `/home/alice2` is not
`/home/alice`, and `~/tmp` or `${HOME}/tmp` is not `/tmp`. A preceding `.`
still counts as a start, because test runners print progress dots straight
before paths, so a relative `./tmp` becomes `.{tmp}`. The receipt records each log's hash before redaction
(`original_sha256`) and of the posted text (`sha256`); review and audit check
the posted text against `sha256`, so an edit after publishing fails.

Publishing checks everything before its first post. The summary, configured
commands and acceptance report are posted as written, so a home or temp path in
them refuses publishing with nothing posted: change that field and publish
again. An oversized receipt is refused the same way. GitHub authenticates the
publisher, not the execution.

A later failed receipt revokes success; new code needs new verification. Publish
failures; never hide one behind an older success.
[Workspace cleanup](sdlc.md#workspace-cleanup) applies.

## Accept and release an immutable candidate

After merge, build the artifact once from a fixed commit with the real build (a
source archive is no binary) and record its SHA-256. Revalidate if merge changed
the tested bytes. Name every implementation PR:

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
  --summary SUMMARY
bin/sdlc-release gate --repo OWNER/REPO --issue ISSUE --sha FULL_SHA \
  --artifact IMAGE@sha256:DIGEST --expected-actor MAINTAINER
bin/sdlc-release promote --repo OWNER/REPO --issue ISSUE --sha FULL_SHA \
  --artifact IMAGE@sha256:DIGEST --expected-actor MAINTAINER \
  --output /private/evidence/release-1
bin/sdlc-release finalize --receipt /private/evidence/release-1/release.json \
  --expected-actor MAINTAINER --logs-reviewed --summary SUMMARY --close
```

Images go by digest. Files use `sha256:DIGEST` plus `--artifact-file PATH`,
hashed before and after. Hooks get `RELEASE_SHA`, `RELEASE_ARTIFACT` and
`RELEASE_ARTIFACT_FILE` and run those bytes.

The report is JSON with `repo`, `sha`, `artifact` and `scenarios`, each holding
`criterion`, `result` (`passed` or `failed`), `observation` and `evidence`
URLs. Cover every configured criterion and the issue's real scenarios. Open
evidence before attesting. A `failed` receipt revokes readiness. The runner
revalidates at the candidate; `acceptance` commands add checks but never replace
the report, and `true` is no implementation.

The gate binds acceptance to repo, issue spec, PR set, commit, artifact and
config, and excludes PR authors. Changed specs or nominations need new
acceptance. Coverage or an older passing main never permits release.

Promotion deploys the retained artifact unrebuilt, keeps the prior state,
serializes per target and backs up before migrating. Verification confirms the
deployed identity, health and smoke scenarios. Rollback restores prior state
where safe; irreversible changes need a recovery procedure.

Promotion writes a receipt first. After interruption, inspect live state and
`--resume` the same directory, which verifies without redeploying. To redeploy,
reconcile and record first, then use a new directory. `--close` only when
delivery is complete.

For runbook deploys, run the gate, keep a private attempt record, follow the
documented procedure, and report every `release_criteria` result plus
`previous_artifact` (or initial release) and `recovery`. Then:

```sh
bin/sdlc-release record --repo OWNER/REPO --issue ISSUE --sha FULL_SHA \
  --artifact IMAGE@sha256:DIGEST --expected-actor MAINTAINER \
  --report /private/evidence/release-report.json \
  --output /private/evidence/release-1/release.json
```

`record` attests a real deployment, never an invented one. Use one path, not
both.

## Retained candidates built before SDLC adoption

Never rebuild a retained artifact to add config or credit it to a newer commit.
When its source lacks `.sdlc/config.json`, a reviewed default-branch descendant
may add a `retained_candidates` entry (`sha`, `artifact`, `validation`,
`reason`) to the full config. It replaces validation only, never criteria or
authority; no placeholder or conformity-only commands.

Nominate with `--policy-sha FULL_REVIEWED_POLICY_SHA`, keeping the original
`--sha`, artifact and PRs. The gate checks ancestry, reachability, config
absence (an API failure is not absence) and the entry. The policy must be a
same-repo PR merge with independent exact-head approval and local evidence, its
tree equal to that head. Policy and effective config bind to the receipt.

Accept from clean separate checkouts: `--root ORIGINAL_CHECKOUT --policy-root
POLICY_CHECKOUT`. Commands run in the original; modified checkouts or bytes are
refused. Publish via the reviewed same-byte runbook, then `record` and
`finalize`, verifying the downloaded bytes; `promote` refuses. The pinned policy
is immutable; editing it elsewhere rewrites nothing. Replace by renominating
under a reviewed policy; a newer failed acceptance also revokes.

## Optional automation

`SDLC_ACTIONS_ENABLED=true` enables jobs on `self-hosted` and
`trusted-linux-x64` runners only, never silently on paid hosted compute. Keep
fork code off credentialed machines. Without a runner, run the same checks
locally.
