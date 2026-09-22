# Writing for Humans for Codex

## Install and verify

After the accepted release is listed in Quickstop, add the repository marketplace with `codex plugin marketplace add https://github.com/acoz-labs/quickstop.git`, then run `codex plugin add writing-for-humans@quickstop`. Before publication, use a temporary marketplace pointing to the candidate in an isolated Codex home.

Node.js 22 or later must be available as `node`. The Codex compatibility package bundles SessionStart and SubagentStart command hooks. Codex CLI 0.155.1 discovers these hooks from `.codex-plugin/plugin.json`; native fixtures did not expose hooks from the portable root manifest, so this package uses the compatibility format. SessionStart covers startup, resume and compaction according to the host's lifecycle contract. Verify the installed version's actual behavior before relying on a mode.

Installation does not trust hooks. Open `/hooks` in interactive Codex, inspect the bundled command definitions and complete native trust review. Changed definitions require renewed review. Never manufacture trust hashes or bypass review. Use `codex plugin list` and `/hooks` to distinguish installed, enabled and trusted states; then test a fictional writing task. A successful hook does not prove application.

For updates, refresh the marketplace through its native commands and install the accepted version; review changed hooks and start a fresh session. `/hooks` can disable the hooks. `codex plugin remove writing-for-humans@quickstop` removes the plugin and local cache. Earlier session context can retain guidance, so verify removal in a fresh session. No global instruction copy needs cleanup. Organization-managed hook restrictions may prevent automatic activation; report that limitation without overriding them.

## Behavior and boundaries

The bundled core applies automatically to prose after activation. The writing-for-humans skill supplies focused references when useful; writing-setup diagnoses activation and conflicts. Ordinary writing requires no command and makes no extra model call. Handlers read only bundled text, require no network and never modify consumer configuration. Guidance is not a guaranteed rewrite or perfect model compliance.

This candidate is not yet advertised. Native behavior, versions/modes, installation, subagents, compaction and writing evaluation require independent acceptance before release. Do not infer support for untested versions, operating systems or editor integrations. All public examples are independently synthetic. Source is maintained once under src/writing-for-humans; generated packages are self-contained. License: MIT.
