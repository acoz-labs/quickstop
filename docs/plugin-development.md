# Plugin development

Start from an assigned outcome and the shared SDLC. Keep a plugin self-contained
under `plugins/<name>/`; its manifest belongs in `.claude-plugin/plugin.json`
inside that directory. Skills, agents, hooks and server configuration belong at
the plugin root, not inside its manifest directory. Add only components needed
by the assigned feature and document their effects and prerequisites.

Register `./plugins/<name>` in the root marketplace with matching name and stable
`major.minor.patch` version. Keep an accurate README, license and root catalog
entry. Preserve existing license notices; do not copy personal author details into
new templates. A deliberate license change is separate from routine scaffolding.

Smith creates a usable plugin from the issue; Hone reviews concrete findings.
Neither needs a fixed agent fan-out or a numerical quality score. Consult the
current [plugin reference](https://code.claude.com/docs/en/plugins-reference) and
[marketplace guide](https://code.claude.com/docs/en/plugin-marketplaces) for host
requirements. These sources were inspected during September 2026 onboarding;
recheck them when behavior or supported components matter. Copied manuals are
not an authoritative substitute.

Run `bin/ci` and `bin/check-marketplace --base PRE_CHANGE_SHA`. Exercise changed
skills in a temporary consumer repository with a separate Claude configuration
and synthetic data. Verify referenced resources resolve from the installed
plugin, not just the source checkout. Cache writes, consumer edits, network use
and external PR delivery need tests appropriate to the change and assigned scope.
Never report static manifest checks as those scenario results.

Changes to any distributed bytes require a higher plugin and marketplace version
because the host caches plugin versions. Repository-only maintenance does not
require a Claudit version bump. Use [artifact delivery](delivery.md) for actual
plugin publication; do not infer a release from an implementation PR alone.
