---
name: status
description: Inspect Claudit cache domain freshness, provenance and failures without fetching or changing anything.
---

# Claudit status

Run `claude --version` and the helper
`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/runtime.py" status --host-version "<actual output>"`.
Use the actual detected version, not the example text. No writes, refreshes,
agent dispatch or network requests belong to this skill. This also excludes output
redirects, tee-to-file and temporary/scratch summaries: consume stdout directly.

Present each domain's state, source date, recorded host version, reasons and preserved limitations. Read
[cache protocol](../../references/cache-check-protocol.md) if interpretation is
needed. Missing files, corruption and failed refreshes affect status; do not infer
freshness from an old manifest alone. For non-fresh domains mention
`/claudit:refresh <domain>` as an available next action, without executing it.
