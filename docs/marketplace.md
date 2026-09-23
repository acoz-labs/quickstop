# Plugin marketplace contract

This contract covers installable plugins. Read-and-adapt guides follow the
[workflow contribution guide](workflows.md) and stay out of native indexes.

Quickstop separates candidate authoring from accepted native distribution indexes. It does not
translate arbitrary plugin behavior between harnesses. The `quickstop` identity
stays stable. A plugin declares the targets it supports; omitted targets are
unsupported, not an adoption backlog or a parity requirement.

## Sources of truth

`catalog.json` has schema version 1, marketplace presentation and an ordered
`plugins` list. Each plugin declares `name`, `description`, `category` and a
nonempty `targets` map. Each target declares exactly `format`, `path` and
`acceptance`. Unknown fields, harnesses and formats fail validation so spelling
mistakes cannot silently change support. The native manifest owns the package
version; there is no global version forcing unrelated targets to release together.

`releases.json` is the advertised-release lock. Each entry pins a plugin target to
an immutable Git commit, package digest, manifest snapshot and provenance. Candidate
packages in `catalog.json` are not advertised until an accepted entry exists.
The historical Claudit entry preserves previously advertised bytes; its migration
provenance does not claim a new acceptance run. New entries require independently
authenticated SDLC acceptance and a reviewed publication change.

Current candidate declaration example:

```json
{
  "name": "claudit",
  "description": "Audit and optimize Claude Code configuration.",
  "category": "Productivity",
  "targets": {
    "claude-code": {
      "format": "claude-plugin",
      "path": "plugins/claudit",
      "acceptance": "docs/acceptance/claudit.md"
    }
  }
}
```

The acceptance file names the supported harness, meaningful scenarios and how to
retain observations. File existence is checked; an agent independently evaluates
its adequacy and executes it for a release. Declaring a procedure is not proof of
passing runtime acceptance. A native parser accepting another format is also not
proof that a plugin's workflows make sense in that harness.

## Native adapters

| Target | Accepted package format | Generated index |
| --- | --- | --- |
| `claude-code` | `claude-plugin`: `.claude-plugin/plugin.json` | `.claude-plugin/marketplace.json` |
| `codex` | `agent-plugin`: root `plugin.json` with Agent Plugins 1.0 schema; `codex-plugin`: `.codex-plugin/plugin.json` compatibility format | `.agents/plugins/marketplace.json` |
| `pi` | `pi-package`: `package.json` with explicit `pi` resource paths | `docs/pi-packages.md` (individual native install commands) |

`docs/catalog.md` and all native installation projections use the release lock.
All four outputs are checked byte-for-byte, including empty native indexes.
Only locked accepted targets (or the explicit historical Claudit migration)
appear in native listings. Claude and Codex entries use commit-pinned
`git-subdir` sources; editing candidate files does not change the advertised bytes. The empty Codex index prevents Quickstop from
advertising Claudit through its Claude-compatible marketplace file.

Use current [Claude marketplace documentation](https://code.claude.com/docs/en/plugin-marketplaces)
and [OpenAI package documentation](https://developers.openai.com/plugins/build/plugins)
and [Pi package documentation](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/packages.md)
for native host requirements; reviewed September 22, 2026. Portable packages may include an optional Codex compatibility overlay; any
duplicated identity/version must agree and resource paths remain contained.
These adapter checks validate Quickstop's contract, not the complete evolving upstream schemas.

### Pi distribution

Pi uses `pi install PACKAGE_SOURCE`, not either native marketplace JSON format.
Quickstop generates a per-package command list and never writes `.pi/settings.json`
or opts consumers into every package. Follow the generated commands for the selected package: use a separate checkout
at its accepted detached commit, verify its package digest, then install that
local package. Local installs link the directory, so preserve the checkout and
do not reuse it as a development worktree. Updating means installing the new
accepted checkout; removing the package does not itself delete that checkout.
The generated list has no entries until a Pi target is accepted.

A Pi package declares `pi.extensions`, `pi.skills`, `pi.prompts` and/or `pi.themes`
as arrays of existing `./`-relative resources in `package.json`. Quickstop
currently requires explicit paths; Pi's richer glob/exclusion syntax needs
additional validator coverage before using it here. Native package versions
follow the same independent stable-version contract. Add `pi-package` keywords
when publishing to Pi's npm gallery. Actual dependency installation, extension
execution and host behavior require target acceptance; static checks do not
establish them. No npm publication is configured by this repository change. Pi project-local
installs use `-l`; listing/loading project resources requires trusting that
consumer project (for example `pi list --approve` after source review).

## Package layouts

Keep simple packages simple. Claudit retains `plugins/claudit/` and its existing
install identity. A truly shared package may explicitly declare both native
manifests at one package root. Only do this when both harnesses should receive
all of those bytes and the components actually behave correctly in each host.

When targets differ, use separate self-contained packages:

```text
plugins/
  claudit/                       # existing Claude-only package
  claude-code/example/           # example's Claude package (when implemented)
  codex/example/                 # example's Codex package (when implemented)
  pi/example/                    # example's Pi package (when implemented)
src/example/                     # optional shared authoring source, if needed
```

The example directories are patterns, not installed plugins or placeholders.
Catalog target paths select the actual package roots. Paths must stay under
`plugins/`; distinct roots cannot overlap. Every distribution file and native
manifest must belong to a declared package/target. Do not add unused skeletons.

If shared source is worthwhile, give the plugin a deterministic build that copies
its needed content into each package and test regeneration as part of `bin/ci`.
Never depend on `../shared`, symlinks, undeclared host files or consumer-accessible
source directories: a host copies only the package root into its install cache.
The marketplace generator generates indexes, not plugin code or behavior.

## Validation and versions

```sh
bin/check-marketplace --write
bin/check-marketplace
bin/check-marketplace --base PRE_CHANGE_SHA
bin/ci
```

Use the pinned Python described in [repository guidance](repository.md). Generation
validates inputs before writing. Read-only checking never rewrites outputs.
Supply a real base commit: Git failures are errors, not permission to skip checks.
The base comparison supports the prior Claude-only catalog for this migration.

All package files are versioned, including documentation and untracked payloads
in a developer checkout. A changed package requires a higher stable `X.Y.Z`
version; downgrades fail. Separate target packages may version independently.
If targets share one root, changes to that distributed root require every affected
target's version to advance. Moving identical bytes alone does not require a bump.
Updating marketplace descriptions or acceptance docs outside the package does not
change plugin bytes. Removing a candidate declaration does not silently revoke a retained advertised
release. Retire or restore advertised pointers explicitly in the release lock,
with independent review of consumer migration and recovery impact.

## Add a harness

Implement its explicit format validator and native index projection in
`bin/check-marketplace`, document installation and acceptance, and add positive
and adversarial fixtures proving optional support and package boundaries. Extend
the generated catalog columns and delivery criteria as needed. Demonstrate actual
native discovery with an isolated host setup before advertising a real package.
Do not add a generic pass-through format or infer compatibility from filenames.

Pinned native sources currently select packages from this repository.
Externally maintained repositories and registries still require a bounded adapter
change with source verification and same-byte acceptance. This task does not import Mandalore or
move any other project's source or publication authority into Quickstop.
