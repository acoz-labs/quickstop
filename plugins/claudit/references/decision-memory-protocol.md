# Scoped decision history

History annotates findings; it never suppresses them or authorizes action. A
read-only audit reads existing stores without creating, migrating or updating any.
Record only an explicit selection, rejection/deferment or successfully applied
fix covered by existing user authorization. Omission or “skip” is not rejection.

## Locations

- Personal: `<cache>/decisions-v2.json`, including user/local/plugin/managed and
  private project decisions. Namespace project records by a stable project key
  (normalized absolute project root) in `project_id` and match only that project.
- Shared: `<project>/.claude/claudit-decisions-shared-v2.json` only when the user
  explicitly wants project decisions shared. Only project-relative, shareable
  targets and sanitized project reasons belong here.
- Historical: `<project>/.claude/claudit-decisions.json` and
  `<cache>/decisions.json`. Read with `decisions-read`; v1 records are returned as
  `legacy_unmatched`. Preserve them unchanged. They mix basenames/scopes and must
  not automatically match, migrate, or be staged/published.

A known project identity can survive a move if explicitly reconciled; do not
silently merge records from unrelated same-named clones. Always load relevant
personal and shared history separately, keeping provenance and unresolved conflicts.

## Mandatory audit read

`discover` returns `decision_context` before the large files map. The orchestrator
must consume it before delegation, not substitute a legacy-only read. It reads
private v2, current-project shared v2, and applicable historical stores without
creating directories, lock files, migrations or decisions. Each store has state,
provenance, applicable/excluded counts and unmatched legacy count. Invalid stores
remain explicit history gaps; records from conflicting applicable stores remain
separate evidence, not a silent winner.

Private project/local records match the full normalized project or main-worktree
root; plugin records match an applicable discovered plugin name or install root.
Records for unrelated project roots are excluded. Global-only excludes project/
local decisions and shared project stores. Project-only may use matching project
decision metadata in Claudit's internal cache but returns no user/local/managed/
plugin records. This does not authorize reading their personal target files.
Historical ambiguous records are counted with provenance, never automatically
matched or forwarded as current scoped decisions. Explicitly scoped history reads
for other purposes can still use `decisions-read <path>`.

## Identity and record

Run `identity <scope> <scope-root> <target-path> <category> <issue-type>` to compute
an escaped JSON tuple of scope, normalized relative path, category and issue type.
Scopes: `project`, `local`, `user`, `managed`, `plugin`. For plugin scope, use the
installed plugin root plus `project_id`/plugin identity in matching context. Distinct
subdirectory files and same-named personal/project files must not collide.
Cross-file findings use an explicit representative file and list related paths.

```json
{
  "fingerprint": "[\"project\",\".claude/settings.json\",\"security\",\"broad-bash-allow\"]",
  "project_id": "/normalized/project/root",
  "action": "accepted",
  "recommendation": "Narrow one observed Bash permission",
  "reason": "User-selected fix",
  "decided_by": "actual git identity or unknown",
  "timestamp": "actual ISO timestamp",
  "context": {"claudit_version":"3.1.0","claude_code_version":"actual detected version","score_impact":15}
}
```

Do not copy example timestamps or identities. Use `decision-save <destination>
<entry-json>`; add `--shared` only for the explicitly selected shared destination.
The helper locks and atomically upserts a v2 store, retaining replaced records in
history. It refuses malformed stores, personal records in shared mode and mixed
legacy publication. Never fall back to overwriting a corrupt store by hand.

Match fingerprint **and** project/plugin identity where applicable. Keep legacy
records visible as unmatched context until the user explicitly disambiguates
scope/path. Flag a matched decision for reevaluation on host-version change,
score impact change >=5, age >90 days, or deferred age >30 days. Previously
accepted issues that recur are regressions; rejected/deferred choices remain
visible with their reasons. History is not evidence that a current defect exists.

Shared records must omit local absolute project IDs, personal paths, secret
values and private reasons before publication. Shared matching uses the containing
repository as project identity. Review the exact proposed diff; schema validation
cannot determine whether free text contains personal information.
