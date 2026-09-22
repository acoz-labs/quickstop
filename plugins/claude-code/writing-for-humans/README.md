# Writing for Humans for Claude Code

## Install and verify

After the accepted release is listed in Quickstop, add the marketplace with `claude plugin marketplace add acoz-labs/quickstop`, then run `claude plugin install writing-for-humans@quickstop`. The native default scope is user; use `--scope project` or `--scope local` deliberately when appropriate. Before publication, developers can load the package with `claude --plugin-dir /absolute/path/to/package` in an isolated configuration.

Node.js 22 or later must be available as `node` to hook commands. SessionStart delivers the core at startup, resume, clear, fork and compaction; SubagentStart delivers it directly to subagents. Ordinary prompts do not inject another full copy. The package does not select or override an output style. Preserve existing styles and coding instructions.

Use `claude plugin list` to verify installation and enablement, and `/hooks` to inspect hooks. Start a new session after changing installation. Ask a fictional writing question and assess understanding and factual preservation; hook discovery alone is insufficient. Invoke writing-setup for diagnosis if needed.

Use `claude plugin update writing-for-humans@quickstop` for an accepted update and restart. `claude plugin disable writing-for-humans@quickstop` disables it; `claude plugin uninstall writing-for-humans@quickstop` removes it. Existing conversation context can retain earlier guidance, so verify disabling in a fresh session. No global instruction copy or output-style change needs removal.

## Behavior and boundaries

The bundled core applies automatically to prose after activation. The writing-for-humans skill supplies focused references when useful; writing-setup diagnoses activation and conflicts. Ordinary writing requires no command and makes no extra model call. Handlers read only bundled text, require no network and never modify consumer configuration. Guidance is not a guaranteed rewrite or perfect model compliance.

See the Quickstop release record for tested host/model versions, execution modes and independent acceptance evidence. Do not infer support for untested versions, operating systems or editor integrations. All public examples are independently synthetic. Source is maintained once under src/writing-for-humans; generated packages are self-contained. License: MIT.
