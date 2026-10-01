---
name: refresh
description: Fetch official documentation now and refresh selected Claudit research domains, preserving last-good evidence on failure.
argument-hint: "[domain ...] (ecosystem | core-config | optimization | all)"
---

# Claudit refresh

Parse `$ARGUMENTS` as domain names; empty or `all` means all three. Reject unknown
names rather than treating them as all. Read the
[cache protocol](../../references/cache-check-protocol.md).

Force a new official-source fetch for every requested domain even when fresh.
Use native research agents in parallel in the foreground after their bundles are
available. Read-only sources and Claudit's cache are the only scope of this skill;
never change consumer settings or decision records. Do not use persistent agent
memory, previous output, community snippets or repeated recollection as external
verification. Preserve old research memory files without reading them as current.

Commit successful research independently per domain. Record failures, preserve
last-good evidence, and show a table of actual state, source date and host version
from a final helper `status` call. “Refreshed” applies only to committed domains;
report failed/superseded attempts separately. No assertion of universal currency,
confidence or performance follows from a timestamp alone.
