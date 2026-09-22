# Native setup for Pi

## Install and verify

Install the accepted package using the exact command published in Quickstop's Pi package guide. During isolated development, use `pi install /absolute/path/to/package -l` to install at project scope; omit `-l` only when user-wide installation is intended. The package contains an extension and two skills. Node.js 22 or later is required.

The extension appends the bundled core at before_agent_start, preserving the current chained system prompt. It makes no extra model call and does not rebuild or replace the user's base prompt. Another extension that later discards the chained prompt can remove the guidance; diagnose that conflict rather than silently disabling the other extension.

Use `pi list` to inspect the installed package and the native resource/settings interface to verify its extension and skills are enabled. Start a fresh session and test a fictional writing task. Installation or extension discovery alone does not prove application. Pi's native core does not define a general independent-subagent facility; third-party orchestration must be verified separately and is not implied by main-session acceptance.

Resolve relative local package paths shown by `pi list` or stored in settings against the directory containing that scope's settings file. Verify the resolved package, then pass absolute `OLD_SOURCE` and `NEW_SOURCE` paths to native install or remove commands at the intended scope. Do not pass a stored relative path directly to a command run from a different directory.

For an upgrade, follow the Pi guide to a new, separate detached checkout of the accepted revision. Run `pi remove OLD_SOURCE` for the previous installed path, then `pi install NEW_SOURCE` for the verified new path; use `-l` for both commands when replacing a project installation. Keep the old verified checkout available for rollback. Use `pi list` to confirm only the intended version remains registered at that scope, then verify activation in a fresh session. Updating the old local path does not select the newly accepted artifact. Disable the extension through native resource settings, or remove the exact installed source with `pi remove SOURCE` using `-l` for a project installation. Start a fresh session to verify removal. No global instruction copy needs cleanup.

For a rerun, inspect existing state before installing again; do not create a second registration at another scope. Verify upgraded or disabled behavior in a fresh session. If runtime files are missing, reinstall the accepted artifact through the native mechanism. Do not patch installed files: that changes the artifact and may invalidate native trust. Record untested resume/compaction/subagent paths as unverified.
