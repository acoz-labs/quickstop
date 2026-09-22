# September 2026 onboarding investigation

Scope: move the existing public repository into acoz-labs, adopt the current SDLC
and remove redundant repository machinery. Product iteration planning follows
separately. Source baseline is recorded in issue #116 and its implementation PR.

## Changes justified by inspection

The repository had no AGENTS.md or shared SDLC configuration. CLAUDE.md combined
version instructions, local hook installation and references to separate rules.
The managed AGENTS.md now provides the shared contract; CLAUDE.md imports it and
the repository-specific guide.

Smith and Hone together occupied 795 lines, backed by seven repository research
and audit agents and copied specification/reference material. Those agents were
used by the repository skills, not shipped Claudit entrypoints. The initial onboarding retained concise shortcuts while removing duplicated
supporting agents/manuals and mandatory interactive scoring. Following the
owner's review, the remaining Smith and Hone skills were also retired: ordinary
implementation and independent review already cover their workflows. Their
useful plugin-specific checks now live in `docs/plugin-development.md`, with no
replacement skill or scaffolder. Existing
MIT notices are preserved. Hooks are evaluated by their actual assigned purpose,
not prohibited by the old scaffolder's blanket observability-only rule.

The old shell version check swallowed Git comparison errors, could report no
changes on failure, compared text instead of semantic versions and did not verify
manifest/marketplace equality. Its compatibility path now invokes the tested
validator. New checks reject invalid bases, duplicate registration, source escape,
version mismatch/downgrades and unchanged versions for changed distributed files.
Host validation remains a separate check, not an inferred runtime test.

The tracked scheduled-task lock and duplicate Claude/Git push hooks were
repository-specific local tooling. They are retired in favor of explicit local
checks and durable independent evidence. No consumer's hooks or global settings
are edited by this change.

## Claudit findings for the next planning conversation

Claudit 3.0.0 contains four skills, six agents, shared cache/decision-memory
protocols and skill-specific references. These are product behavior, unlike the
removed repository authoring tools. All files under `plugins/claudit/` are
preserved byte-for-byte in this onboarding change.

Potential investigations, not approved new features or established defects:

- Measure whether research orchestration and the shared knowledge cache reduce
  cost and latency on real audit/refresh workloads.
- Exercise stale-cache, failed-refresh, partial-results and concurrent-write cases;
  examine whether the instruction protocols need executable helpers.
- Test decision-memory and PR-delivery boundaries with synthetic consumer data,
  including read-only audits and cross-repository permissions.
- Review copied known-settings and scoring assumptions against the installed
  host version; optimize for useful findings rather than score changes.
- Resolve candidate isolation before any future plugin-byte release: the legacy
  default-branch marketplace currently advertises merged files immediately.

No runtime acceptance or feature roadmap is claimed by this maintenance work.
Use these findings to shape the next bounded iteration with the owner.

## Unified marketplace follow-up

The owner subsequently assigned Quickstop a broader purpose: the acoz-labs
unified marketplace for agentic plugins. Harness support is now explicit per
plugin; cross-harness parity is optional. `catalog.json`, generated native
indexes and adapter checks replace the earlier assumption that every package is
a Claude Code plugin. Claudit remains Claude Code-only at its existing path and
version. See [the current contract](marketplace.md). This establishes marketplace
patterns, not new Claudit behavior or migration of other projects.
