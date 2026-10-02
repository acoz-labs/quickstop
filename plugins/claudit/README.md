# Claudit

Claudit audits Claude Code configuration against current official documentation,
then helps apply selected improvements. It also maintains reusable, source-linked
knowledge for later configuration work.

## Installation

From the Quickstop marketplace in Claude Code:

```text
/plugin install claudit@quickstop
```

For local development, load the checkout with
`claude --plugin-dir /path/to/quickstop/plugins/claudit`. The marketplace advertises
only the accepted release; a development checkout can contain a newer candidate.

## Use

```text
/claudit:claudit                        # comprehensive inside Git, global outside Git
/claudit:claudit hooks --read-only      # focused review; no fixes or decisions
/claudit:knowledge ecosystem           # retrieve/refresh one knowledge domain
/claudit:refresh all                   # force fresh official-source research
/claudit:status                        # inspect cache without changing it
```

Natural-language requests to audit or tune Claude Code can also invoke Claudit.
Specify project-only to exclude personal configuration, or explicitly request a
directory audit outside Git. A focus deepens relevant checks without disguising
unassessed areas as a complete audit.

Discovery includes applicable decision history without changing it. Project-only
audits can read matching project decisions from Claudit's internal cache; they
exclude user, local, managed, plugin and unrelated-project decision content.
Ambiguous legacy history remains unmatched rather than silently migrated.

An audit alone does not authorize configuration edits, decision writes or PRs.
`--read-only` ends after the report. Research-cache maintenance is permitted during
ordinary audits; add “no writes, including cache” to use retained evidence only.
Selected fixes honor authorization already given. Personal changes stay local;
authorized PRs use a separate worktree and leave existing consumer edits intact.

## Requirements and current support

Claudit 3.2.1 targets current Claude Code, reviewed with **2.1.287**. It uses native
skills and six Sonnet subagents, including `omitClaudeMd` (available since
2.1.271). Older hosts are not validated by this release. Model aliases resolve
through the host/account; no fixed model-version or speed guarantee is implied.

The packaged helper requires **Python 3.11+**, standard library only. Git is needed
for repository/worktree delivery and `gh` for an authorized GitHub PR. Public
official-documentation access is needed for fresh research. No dependencies are
downloaded and no global host settings are rewritten. Host permissions continue
to govern tool execution and network/write access.

File locking supports POSIX (`fcntl`) and Windows (`msvcrt`). Native acceptance
records identify the actual tested platform; Windows-specific managed policy and
settings-source exceptions remain explicit discovery limitations, not a claim of
native Windows certification. Without an available runtime, Claudit can explain
read-only findings but must report deterministic checks as unverified.

## What changed

- Read-only and offline audits retain their required source-reading, coverage and
  auditor stages. If a real constraint prevents a stage, the report identifies
  the unassessed scope. Unresolved observations are kept out of confirmed defects.

- Audits now check documentation coverage for the actual features under review,
  even when the baseline cache is fresh. Missing pages, such as output styles,
  are fetched and synthesized separately; fresh sources are reused. This is a
  bounded, task-specific check, not an exhaustive crawl or runtime certification.

- Discovery preserves scopes and unknowns, prioritizes critical files, respects
  configuration-directory overrides, extracts redacted MCP metadata and reports
  coverage gaps. Actual plugin component paths and auto-memory candidates replace
  stale assumed locations. Filesystem presence is distinguished from effective
  CLI, trust and managed policy.
- Current permission/hook/plugin rules distinguish confirmed defects from optional
  features. Supported commands and optional manifests are valid. Official plugins
  receive the same checks. Scores are explained heuristics; missing telemetry,
  unused-by-observation tools and JSON file size are not performance defects.
  The read-only scoring helper excludes unassessed categories and withholds an
  overall score or letter grade while material coverage remains unknown.
- Research fetches official source bytes before synthesis. Agents have no persistent
  research memory; source hashes, timestamps and sections support inspection.
  Domain-specific source slices reduce repetition without claiming measured savings.
- Each cache domain has its own host version, source date, atomic record and lock.
  Failed refreshes retain last-good evidence and report degraded status. One-domain
  upgrades work independently. Freshness means cache integrity/provenance, not
  independent semantic verification of the model's summary.
- Decisions use scoped paths and project identities. Legacy ambiguous history is
  preserved unmatched. Personal decisions are not automatically published.
- PR preparation starts from an isolated clean HEAD, even when the consumer has
  staged or uncommitted work. Selected fixes are reapplied independently; snapshots
  and path gates catch accidental inclusion. Exact diff review remains necessary
  for semantic correctness and private free-text content. Failed preparation
  retains recovery state instead of silently deleting branches or consumer work.

## Cache and history

Default cache: `~/.cache/claudit`; override with `CLAUDIT_CACHE_DIR` for isolation.
`v2/<domain>.json` stores claims and source provenance. Source Markdown is retained
under `v2/research`, prior records under `v2/history`, and failed attempt receipts
alongside the domain record. `status` and `knowledge` share freshness logic:
missing, corrupt, stale, degraded or fresh. Seven-day TTL applies to fetched
sources independently for each host/domain.

A fresh record can contain useful verified-source claims alongside explicit
coverage limitations, such as unread sections or unknown account applicability.
Those limitations stay visible in status, knowledge and audits. Audits inspect
relevant retained sections and use `coverage` / `fetch-pages` to obtain missing
pages. Supplemental page records under `v2/topics` retain independent provenance,
failure state and history. A failed page leaves baseline knowledge intact; a
fresh page still does not prove semantic completeness. Explicit no-network or
no-cache-write requests retain the missing evidence as a reported limitation. Missing required
sources or failed research still prevent a successful refresh. Each fetch also
reserves its own synthesis output path to keep concurrent research separate.

Existing `manifest.json`, cached Markdown, research-agent memory and legacy
`claudit-decisions.json` files are never silently deleted. Legacy knowledge is
unverified until a successful fresh fetch replaces that domain's active view.
Private decision history lives in `decisions-v2.json`; sharing project decisions
requires an explicit choice and a sanitized shared-v2 file.

When upgrading from 3.0, ensure Python 3.11+ is available, then run
`/claudit:status` to inspect retained state. `/claudit:refresh all` fetches current
evidence without deleting the old cache or research memory.

See [cache protocol](references/cache-check-protocol.md),
[discovery](references/discovery.md),
[decision history](references/decision-memory-protocol.md) and
[PR delivery](skills/claudit/references/pr-delivery.md) for operational details.
Repository acceptance procedures and retained release evidence establish the
actual tested behavior; package validation alone is not an end-to-end audit test.

## Design

Four skills coordinate six agents: three official-document research agents and
three read-only auditors for global, project and ecosystem configuration.
Research can run concurrently per domain; auditors receive only relevant claims
and configuration slices. Python handles fragile state transitions and isolation;
models interpret source evidence and explain useful changes.

MIT licensed; see [LICENSE](LICENSE).
