# Claudit acceptance

Supported target: **Claude Code**. A compatible package parser does not establish
support in another harness. Use the retained package and isolated native
configuration described in [delivery](../delivery.md). Record the exact host,
resolved models, package version/digest, commands, inputs, outputs and observed
file effects. Passing manifest validation alone is not acceptance.

## Isolation and evidence

Use synthetic repositories, a separate home and Claude configuration, and a
working directory outside the operator's instruction-file ancestry. Confirm the
native initialization inventory contains only the intended plugin and built-ins.
Disable unrelated MCP connections, plugin synchronization and hooks where needed
for isolation without replacing the product's own workflow. Keep credentials out
of fixture files, prompts, logs and published evidence. Compare consumer files,
Git index, working tree and decision/cache state before and after each scenario.

Native `claude plugin eval` is useful when available, with local reports and
bounded runs, but its scaffolds do not load project configuration. Supplement it
with direct isolated Claude Code sessions for actual settings and installation
behavior. Graders must inspect actual outputs and file/tool effects; a requested
action, an agent's success claim or matching headings is not evidence it happened.

## Required scenarios

- Install the retained marketplace package and verify all four skills and six
  agents load with their intended models and tools. Inspect component paths from
  the installed payload. Record native validation and inventory results.
- Exercise a project audit, a non-Git global audit, and a nested/worktree project.
  Include user and local MCP entries, a remote HTTP server, a valid command-only
  plugin, a plugin with custom component paths, scoped rules and auto-memory.
  Distinguish static configuration from live connection health and loaded context.
- Audit a valid current configuration and a separate fixture with real defects.
  Compare findings to official source evidence and fixture ground truth. Supported
  defaults, commands, optional manifest metadata, deferred tools and unknown usage
  must not be reported as proven defects. New/unknown fields require verification.
- Exercise large instruction inventories and unreadable or malformed configuration.
  Critical sources must remain visible; skipped content and uncertain effective
  managed/session state must appear as coverage limitations, not healthy results.
  Verify actual score-helper inputs and output: partial or unknown categories
  have no numeric score or weight in the assessed subset, and unknown coverage
  prevents an overall score or letter grade.
- Invoke knowledge, refresh and status for fresh, stale, missing and corrupt cache
  state. Refresh one domain after a host-version change and on first use; a second
  read must reuse it. Other domains retain their own freshness. Concurrent domain
  updates must preserve both results. Missing payloads and invalid metadata must
  never appear fresh.
- Run an actual official-document research refresh. Inspect fetch calls and source
  provenance, not just returned citations. No persistent research-memory reads or
  writes establish freshness. With research unavailable/failed/partial, preserve
  the previous good payload and report degraded coverage; do not mark failed
  research as a successful current refresh. Never delete old agent memory silently.
- Distinguish actual missing required evidence from honest coverage limitations.
  A successful bounded synthesis must preserve and display unread sections and
  account applicability limits. Verify that concurrent fetches have distinct
  synthesis files and that a shared temporary output is rejected at commit time.
- Seed a fresh ecosystem cache without the dedicated output-styles page. Audit a
  synthetic plugin with an output style and verify the orchestrator identifies
  that topic gap, fetches only needed supplemental official pages, synthesizes
  source-backed claims, and rereads coverage before reporting. A second audit
  must reuse fresh supplemental evidence. Baseline records must remain unchanged.
  Exercise an unread relevant section in a retained page: read it without fetching.
  Repeat with no writes/no network and with a failed supplemental fetch; report
  the unresolved topic, preserve last-good evidence and withhold complete grades.
  Separate documented behavior from runtime-observed loading/context usage.
- Run a read-only audit with existing decision records and personal configuration.
  Consumer files and decisions must remain unchanged. Record allowed plugin cache
  effects separately, and honor an explicit no-write request for those too.
- Apply an explicitly selected narrow fix and verify only its intended content
  changes. A declined or unselected recommendation must not be applied. Previously
  authorized work must not require an unnecessary second permission question.
- Record different decisions for identically named files in different scopes and
  directories. Verify exact matching and legacy-record preservation. Personal
  decision content must stay out of the shared project record and PR payload.
- Exercise PR preparation with staged unrelated changes, unstaged edits in the same
  file, untracked files, paths containing spaces and an existing branch. Inspect
  the proposed commit/diff and verify the original index/worktree are preserved.
  Test failure/retry recovery: occupied destinations and existing branches must
  fail before creating refs, and a failure after mutation must retain an inspectable
  recovery receipt. A retry must not overwrite it or discard consumer work.
  Use a local test remote or instrumented GitHub boundary
  unless an actual external test PR is explicitly in scope; label simulated remote
  checks honestly and do not claim them as a real published PR.

## Acceptance and publication

Run repository checks on the exact candidate and compare the retained extracted
package digest. Record every issue criterion and configured delivery criterion
with openable sanitized evidence. A failed behavior returns to implementation;
do not weaken a grader or replace a native scenario with a static assertion.
After publication, install from the advertised marketplace, verify the accepted
package digest and smoke its skills. Retain predecessor version/source and tested
consumer update/recovery instructions. Model-driven audit judgments remain
advisory; document any observed limitations and do not claim universal perfection.
