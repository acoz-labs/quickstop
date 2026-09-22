# Native setup for Claude Code

## Install and verify

After the accepted release is listed in Quickstop, add the marketplace with `claude plugin marketplace add acoz-labs/quickstop`, then run `claude plugin install writing-for-humans@quickstop`. The native default scope is user; use `--scope project` or `--scope local` deliberately when appropriate. Before publication, developers can load the package with `claude --plugin-dir /absolute/path/to/package` in an isolated configuration.

Node.js 22 or later must be available as `node` to hook commands. SessionStart delivers the core at startup, resume, clear, fork and compaction; SubagentStart delivers it directly to subagents. Ordinary prompts do not inject another full copy. The package does not select or override an output style. Preserve existing styles and coding instructions.

Use `claude plugin list` to verify installation and enablement, and `/hooks` to inspect hooks. Enable an installed disabled plugin with `claude plugin enable writing-for-humans@quickstop`; use the native command at the intended scope instead of editing settings JSON. Start a new session after changing installation. Ask a fictional writing question and assess understanding and factual preservation; hook discovery alone is insufficient. Invoke writing-setup for diagnosis if needed.

Use `claude plugin update writing-for-humans@quickstop` for an accepted update and restart. `claude plugin disable writing-for-humans@quickstop` disables it; `claude plugin uninstall writing-for-humans@quickstop` removes it. Existing conversation context can retain earlier guidance, so verify disabling in a fresh session. No global instruction copy or output-style change needs removal.

For a rerun, inspect existing state before installing again; do not create a second registration at another scope. Verify upgraded or disabled behavior in a fresh session. If runtime files are missing, reinstall the accepted artifact through the native mechanism. Do not patch installed files: that changes the artifact and may invalidate native trust. Record untested resume/compaction/subagent paths as unverified.
