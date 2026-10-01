---
name: knowledge
description: Retrieve current source-backed Claude Code knowledge for ecosystem, core-config or optimization; refresh stale domains when permitted.
argument-hint: "[domain ...] (ecosystem | core-config | optimization | all)"
---

# Claudit knowledge

Parse `$ARGUMENTS` as domain names; empty or `all` selects all three. Reject unknown
names with the supported choices. Follow the shared
[cache protocol](../../references/cache-check-protocol.md).

Run the helper's `status` for requested domains using the actual host version.
Refresh only non-fresh requested domains, once, using current official source
fetches and the corresponding native research agent. Preserve explicit no-network
or no-write constraints: serve labeled retained evidence instead. Under explicit
no-writes, do not redirect output, use tee-to-file or generate temporary/scratch
JSON/context summaries, even outside the cache. Consume the tool response directly;
use existing per-domain record/source paths and inline relevant claims. No consumer
configuration or decision changes are part of knowledge retrieval.

Run `knowledge` for the same domains. Return concise claims with source links,
fetched date, recorded/current host versions and each domain's actual state and preserved limitations.
Fresh/degraded/stale are distinct. Last-good evidence can be useful after a failed
refresh but is not newly verified. If nothing valid is available, state the gap;
do not invent domain content or imply successful research. Cache freshness does
not establish semantic correctness or measured runtime behavior.

Set `run_in_background: false` explicitly on each research Agent/Task dispatch.
For a denied fetch call, follow the cache protocol's failure-logging/final-status
path without retrying the denied action or requesting redundant approval.
