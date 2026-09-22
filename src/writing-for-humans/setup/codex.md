# Native setup for Codex

## Install and verify

After the accepted release is listed in Quickstop, add the repository marketplace with `codex plugin marketplace add https://github.com/acoz-labs/quickstop.git`, then run `codex plugin add writing-for-humans@quickstop`. Before publication, use a temporary marketplace pointing to the candidate in an isolated Codex home.

Node.js 22 or later must be available as `node`. The portable plugin bundles SessionStart and SubagentStart command hooks. SessionStart covers startup, resume and compaction according to the host's lifecycle contract. Verify the installed version's actual behavior before relying on a mode.

Installation does not trust hooks. Open `/hooks` in interactive Codex, inspect the bundled command definitions and complete native trust review. Changed definitions require renewed review. Never manufacture trust hashes or bypass review. Use `codex plugin list` and `/hooks` to distinguish installed, enabled and trusted states; then test a fictional writing task. A successful hook does not prove application.

For updates, refresh the marketplace through its native commands and install the accepted version; review changed hooks and start a fresh session. `/hooks` can disable the hooks. `codex plugin remove writing-for-humans@quickstop` removes the plugin and local cache. Earlier session context can retain guidance, so verify removal in a fresh session. No global instruction copy needs cleanup. Organization-managed hook restrictions may prevent automatic activation; report that limitation without overriding them.

For a rerun, inspect existing state before installing again; do not create a second registration at another scope. Verify upgraded or disabled behavior in a fresh session. If runtime files are missing, reinstall the accepted artifact through the native mechanism. Do not patch installed files: that changes the artifact and may invalidate native trust. Record untested resume/compaction/subagent paths as unverified.
