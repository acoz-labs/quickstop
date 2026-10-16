# Offline helper protocol

Run with Python 3.11 stdlib. From the installed package root:

```sh
python3 scripts/shipshape.py contract check --repo-root CONSUMER --contract contract.json --observations observations.json
python3 scripts/shipshape.py result check --contract contract.json --result result.json
python3 scripts/shipshape.py event decide --state state.json --event event.json --github-snapshot snapshot.json
python3 scripts/shipshape.py handoff write --repo-root CONSUMER --contract contract.json --result result.json --handoff-root TRUSTED_ABSOLUTE_ANCHOR --output relative-attempt
```

Output is JSON. Exit 0 = success of the named advisory check; 2 = invalid-policy;
3 = wait-missing-capability. No command launches, merges, fetches, authenticates,
publishes or executes payload strings. Fixed-argv read-only Git repository-root, origin, HEAD,
commit-type, ancestry and source cleanliness inspection are the only subprocess operations. Tool
paths are read and hashed, never executed. Missing CLI options and malformed
JSON return invalid-policy JSON. Every JSON input and stored record is at most 64 KiB. JSON opens are nonblocking
and no-follow, then fstat the opened descriptor to require a regular file before
a bounded read. Directories, devices, FIFOs, symlinks and oversized input fail.
Digest reads use the same descriptor checks with a 256 MiB limit suitable for
pinned tool binaries; larger tools require a future explicit protocol change.
Config digests refuse symlinks. Tool digests deliberately follow symlinks (for
example a Python launcher) but require the opened target to be regular and bounded.
A replaced pathname cannot substitute for the descriptor inspected and read.
The adapter must keep pinned bytes stable during use; a digest is not a lock.

Contract schema 1 has exactly these fields: `schema`, `run`, `attempt`,
`generation`, `repository`, `issue`, `base`, `head`, `spec`, `config`, `package`,
`guide`, `harness`, `role`, `process`, `session`, `scope`, `constraints`,
`commands`, `effects`, `limits`, `capabilities`, `stop`, `tools`.
Run/attempt/process/session are bounded alphanumeric identifiers with `_`/`-`.
Generation and issue are positive integers; repository is owner/name. Base/head
and guide are full lowercase 40-hex revisions; spec/config/package/harness are
64-hex SHA-256 digests. Role is author or reviewer. Scope uses portable slash-relative paths: no leading slash, colon, backslash,
NUL or any literal '..' component. Empty and '.' components normalize away;
at least one bounded component must remain. './src/./file' is bounded, while
'.', './' and '././' are whole-root scopes and rejected. No glob expansion is
performed. Constraints, commands and limits are nonempty string
lists. Effects currently support only proposal and checkout-edit. Other effects
are unsupported. Capabilities lists missing capabilities; an empty list claims
none missing. Stop is null, paused, stop, quota, offline or revoked. Tools is a
nonempty list of exact objects `{path: ABSOLUTE_PATH, sha256: DIGEST}`.
Preflight requires the resolved Git `rev-parse --show-toplevel` path to equal
the resolved supplied repo root. It supports github.com only, with exactly
`https://github.com/OWNER/REPO[.git]`, `ssh://git@github.com/OWNER/REPO[.git]`
or `git@github.com:OWNER/REPO[.git]` origins. HTTPS userinfo/credentials, SSH
passwords or users other than git, explicit ports, alternate protocols, host
suffixes and enterprise hosts are rejected. GitHub Enterprise support is not
implied. No network Git calls occur. Preflight compares owner/name, real base/head commit
objects and base ancestry, HEAD, config bytes, an existing delivery profile
(service/artifact/non-deployable), nonempty validation command requirements and
required tool bytes. Authentication of observed remote state remains the adapter's responsibility.
Reviewer preflight requires a clean checkout, rejecting staged/unstaged tracked
changes and untracked files (including submodule dirtiness). Keep contracts,
observations and evidence OUTSIDE the reviewer consumer; do not ignore fixtures
to make this pass. Author preflight permits work in progress: HEAD alone does
not identify dirty bytes. The trusted adapter must retain and bind exact author
working bytes, including untracked bytes, to the executing evidence and subsequent
review candidate; preflight cannot attest that identity.
Missing config, Git or pinned tool is wait; changed bytes are invalid. The bounded
`--observations` JSON must have exactly spec/package/guide/harness fields equal
to contract pins. No observations means wait, explicit null is invalid. The
trusted adapter must obtain these observations from the actual retained spec,
package, guide revision and harness, and bind capabilities independently. The
comparator is deterministic; JSON cannot authenticate its claimed provenance.

Result schema 2 has exactly `schema`, `contract`, `role`, `process`, `session`,
`author_process`, `author_session`, `outcome`, `commands`, `evidence`, `findings`,
`next_action`, `limits`, `effects`. Contract is SHA-256 of UTF-8 JSON serialized
with sorted keys and separators `(',', ':')`. This binds every contract field,
including run/attempt/generation and immutable identities. Role/process/session,
limits/effects equal the contract. Reviewer's process AND session differ from
author's. Author results bind author_process/session to their own process/session.
Trusted adapter binds those claims to actual workers; helper cannot.
Outcome is passed/failed/blocked. Commands explicitly represents EVERY required
command in contract order, including interruption and commands never started.
An executed record is exactly {command: STRING, status: "executed", exit: INTEGER};
a not-run record is exactly {command: STRING, status: "not-run", reason: NONEMPTY_STRING}.
Not-run records have no exit; executed records have no reason. Booleans are not
integer exits. Empty/incomplete lists, old schema 1 and status-free records are
rejected; execution is never inferred. Failed/blocked claims preserve partial
proof and not-run reasons in durable handoffs, including replay. Evidence is a
nonempty list of `{locator: STRING, sha256: DIGEST}`; locators and digests are
claims requiring independent inspection. Findings is a string list; next_action
is a nonempty string. Passed requires every command executed with exit 0 and forbids findings, missing capabilities
and stops. Never put secrets, full transcripts or live host identities in examples.

Event/state/snapshot schema 1 share `schema`, `generation`, `identity` (canonical
contract digest), `head`, `base`. State adds `seen` logical keys, `rounds` integer,
`uncertain` boolean. Event adds `key` (bounded delivery identifier, not dedup proof)
and `kind`: review/head/merged/closed/reconcile/informational. Snapshot adds boolean
enrolled/assigned/draft/closed/blockers/approval/independent/gate/authority;
merged_sha/review_head are full revisions or null; stop uses the contract enum.
The trusted integration supplies a fresh authenticated snapshot and gate receipts;
these flags are not GitHub authentication. Unknown fields/schema/actions fail
closed. Identity or generation drift reconciles. Stale review requires review.
Current independent blockers correct, or replan after two rounds; blockers without
independent review remain blocked. Merge-ready requires all
current independent evidence, gate and authority flags. Actual merged_sha becomes
the acceptance candidate. Closed-unmerged stops. Duplicate logical work is ignored.
Uncertain effects reconcile before retry; pause/quota/offline/revocation wait.
The coordinator persists decisions and seen keys; this helper is not a queue.
The returned key is SHA-256 of canonical sorted compact JSON containing snapshot
identity/head/base/generation and phase (the recommended decision before dedup).
For acceptance-handoff it also includes merged_sha, binding the integrated
candidate: another delivery of the same candidate deduplicates, while another
candidate requires a distinct acceptance handoff.
Delivery IDs and object ordering cannot change that key. New head/base/spec or
generation drift explicitly reconciles, then the adapter establishes fresh review
state. Merged snapshots require closed=true. Every decision has stable reason/key
and empty effects; merge-ready is a recommendation, never a release gate.

Handoff writes bounded canonical contract/result records to immutable `gN.json`
files outside the consumer checkout. The operator explicitly supplies a trusted,
absolute, traversal-free, resolved canonical `--handoff-root`, owns its ancestors
and prevents their replacement or mount changes during the operation. Canonical
equality rejects anchor symlink components; this does not authenticate ownership.
The helper opens the anchor by its full path with O_NOFOLLOW, without opening
filesystem/home ancestors. `--output` must be a relative contained descendant;
its existing parents are opened with dir_fd/O_NOFOLLOW. Opened directory inode
identities refuse entry into the consumer, including under an outside anchor.
The trusted coordinator must prevent concurrent consumer/root renames. No
traversal, symlink escapes, unrelated
attempt clobber, conflicting replay or stale generation is allowed. Temporary
exclusive writes, fsync and exclusive hard-link publication precede success.
One trusted coordinator owns a private attempt directory; `.lock` excludes
concurrent writers. After a crash, inspect lock/pending files and existing records
before operator recovery; never automatically steal locks or retry uncertain
effects. No daemon, queue or distributed locking is provided. Retain evidence
outside disposable consumer workspaces, with responsible role and cleanup trigger.
All prior records must have valid bound contract/result schemas, matching attempt
and filename generation; corrupt or oversized prior records fail closed. At most
64 KiB is read per prior record; nonregular records are refused without blocking.
At most
64 generation records are retained per attempt. At the limit, the operator must
inspect and archive evidence under its retention policy before a new attempt;
the helper never deletes old evidence automatically.

From any directory run `python3 /path/to/installed/package/examples/run.py`.
The contained runner resolves `scripts/shipshape.py` relative to its own installed
bytes, creates a disposable real Git consumer with synthetic identity and origin,
and checks preflight, result and handoff replay. It requires Python 3.11 and Git;
it uses no source-repository imports or private configuration. The fixture's
synthetic-check outcome and observations are synthetic claims, not a build run.
Temporary fixture resources self-clean. These are contributor checks, not native
loading, independent review, acceptance or publication proof.

## Coherence matrix

| Guide document | Shared package boundary |
| --- | --- |
| README.md | Exact first starter prompt remains proposal-only; package optional |
| process.md | Distinct review, exact revisions, bounded handoff; local rules govern |
| adapt.md | Guide-only adoption, explicit trusted handoff root; no implicit setup |
| examples.md | Fictional scenarios and synthetic helpers are not acceptance proof |

Limitations: this offline helper authenticates no observations, worker roles or
GitHub flags; it performs no dispatch, gate, native install or runtime discovery.
The adapter must obtain fresh trusted observations and actual independent executed
evidence, reconcile uncertain effects, and use existing repository release gates.
