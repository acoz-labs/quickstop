# Plugin development

Start from an assigned outcome and the shared SDLC. Plugins install through
Claude Code's plugin format. Follow the [catalog and package contract](marketplace.md)
for the native format and the `plugins/<name>/` layout.

New skills follow the [Agent Skills spec](https://agentskills.io/specification),
so they work in any agent tool that reads skills. `bin/ci` fails a skill that
uses features only Claude Code supports: frontmatter fields outside the spec,
argument placeholders such as `$ARGUMENTS`, inline shell commands, `CLAUDE_*`
plugin variables, Claude Code tool names, output styles or hooks. A plugin that
needs those features on purpose is named, with the reason, under
`claude_code_only` in `skills-check.json`; never change a package to dodge the
check.

Choose a lowercase kebab-case plugin name and refuse to overwrite an existing
package when creating a new one. Keep components at the native package root,
not inside manifest metadata directories. Add only components needed by the
assigned feature; document effects and prerequisites.

Add the plugin and its `claude-code` target to `catalog.json`, with native format,
package path and a real acceptance procedure. Native manifests
own versions. Candidate declarations alone do not advertise the package.
`releases.json` controls accepted listings; `bin/check-marketplace --write`
regenerates native listings and the support table from those retained pointers. Keep an accurate package README and license; preserve notices.
A deliberate license change is separate from routine scaffolding.

Use the standard contributor workflow for implementation and independent
maintainer review for findings. Consult the
current [plugin reference](https://code.claude.com/docs/en/plugins-reference) and
[marketplace guide](https://code.claude.com/docs/en/plugin-marketplaces) for host
requirements. These sources were inspected during September 2026 onboarding;
recheck them when behavior or supported components matter. Copied manuals are
not an authoritative substitute.

Run `bin/ci` and `bin/check-marketplace --base PRE_CHANGE_SHA`. Exercise changed
capabilities in a temporary consumer repository with an isolated configuration
and synthetic data. Verify referenced resources resolve from the installed
plugin, not just the source checkout. Cache writes, consumer edits, network use
and external PR delivery need tests appropriate to the change and assigned scope.
Never report static manifest checks as those scenario results.

Changes to distributed bytes require a higher version for each affected package;
generated native listings derive that version. Unchanged packages do not need
synchronized version bumps. Repository-only maintenance does not
require a Claudit version bump. Use [artifact delivery](delivery.md) for actual
plugin publication; do not infer a release from an implementation PR alone.

## Plugin review checklist

Apply these checks to the assigned change; record findings by severity with
paths, evidence and user impact.

- Confirm Claude Code loads the plugin's declared components, and
  referenced resources resolve inside the distributed payload.
- Check that the catalog, release lock and native listing agree.
- Check registration, package versions, licensing and whether the README accurately
  describes capabilities, prerequisites and effects.
- Identify duplicated instructions or unnecessary orchestration with a concrete
  maintenance or usability cost; avoid arbitrary scores and stylistic rewrites.
- Exercise permissions, cache freshness/failure behavior and consumer-state
  boundaries relevant to the change, including read-only requests.
- Verify relevant user scenarios in an isolated consumer workspace and distinguish
  runtime observations from static validation.

An audit request alone does not authorize fixes or publication. Assigned fixes
follow the shared SDLC; resolve findings against the issue without adding routine
owner approval gates.
