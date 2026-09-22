# Writing for Humans for Pi

## Install and verify

Install the accepted package using the exact command published in Quickstop's Pi package guide. During isolated development, use `pi install /absolute/path/to/package -l` to install at project scope; omit `-l` only when user-wide installation is intended. The package contains an extension and two skills. Node.js 22 or later is required.

The extension appends the bundled core at before_agent_start, preserving the current chained system prompt. It makes no extra model call and does not rebuild or replace the user's base prompt. Another extension that later discards the chained prompt can remove the guidance; diagnose that conflict rather than silently disabling the other extension.

Use `pi list` to inspect the installed package and the native resource/settings interface to verify its extension and skills are enabled. Start a fresh session and test a fictional writing task. Installation or extension discovery alone does not prove application. Pi's native core does not define a general independent-subagent facility; third-party orchestration must be verified separately and is not implied by main-session acceptance.

For an upgrade, follow the Pi guide to a new, separate detached checkout of the accepted revision and install that package path. Updating the old local path does not select the newly accepted artifact. Disable the extension through native resource settings, or remove the exact installed source with `pi remove SOURCE` using `-l` for a project installation. Start a fresh session to verify removal. No global instruction copy needs cleanup.

## Behavior and boundaries

The bundled core applies automatically to prose after activation. The writing-for-humans skill supplies focused references when useful; writing-setup diagnoses activation and conflicts. Ordinary writing requires no command and makes no extra model call. Handlers read only bundled text, require no network and never modify consumer configuration. Guidance is not a guaranteed rewrite or perfect model compliance.

See the Quickstop release record for tested host/model versions, execution modes and independent acceptance evidence. Do not infer support for untested versions, operating systems or editor integrations. All public examples are independently synthetic. Source is maintained once under src/writing-for-humans; generated packages are self-contained. License: MIT.
