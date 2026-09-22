# Plugin development

Start from an assigned outcome and the shared SDLC. Declare only the harnesses
that the plugin actually supports; parity is optional. Follow the
[catalog and package contract](marketplace.md) for native formats and layouts.
Create a self-contained package for each distinct target, or explicitly share
one package root when both harnesses should receive and execute those bytes.

Choose a lowercase kebab-case plugin name and refuse to overwrite an existing
package when creating a new one. Keep components at the native package root,
not inside manifest metadata directories. Add only components needed by the
assigned feature; document effects and prerequisites.

Add the plugin and its supported targets to `catalog.json`, with native format,
package path and a real acceptance procedure for each target. Native manifests
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
for each declared harness and synthetic data. Verify referenced resources resolve from the installed
plugin, not just the source checkout. Cache writes, consumer edits, network use
and external PR delivery need tests appropriate to the change and assigned scope.
Never report static manifest checks as those scenario results.

Changes to distributed bytes require a higher version for each affected package;
generated native listings derive that version. Unchanged separate harness
packages do not need synchronized version bumps. Repository-only maintenance does not
require a Claudit version bump. Use [artifact delivery](delivery.md) for actual
plugin publication; do not infer a release from an implementation PR alone.

## Plugin review checklist

Apply these checks to the assigned change; record findings by severity with
paths, evidence and user impact.

- Confirm every advertised harness loads its declared components, and
  referenced resources resolve inside the distributed payload.
- Check that supported targets and native listings agree, and that unsupported
  harnesses are not advertised.
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
