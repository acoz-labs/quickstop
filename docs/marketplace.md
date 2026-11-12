# Plugin marketplace contract

This contract covers installable plugins. Read-and-adapt guides follow the
[workflow contribution guide](workflows.md) and stay out of native indexes.

Quickstop is acoz-labs' marketplace of agent plugins and skills. It separates candidate authoring
from the accepted native distribution index. The `quickstop` identity stays
stable.

## Sources of truth

`catalog.json` has schema version 1, marketplace presentation and an ordered
`plugins` list. Each plugin declares `name`, `description`, `category` and a
`targets` map holding exactly one `claude-code` target. The target declares
exactly `format` (`claude-plugin`), `path` and `acceptance`. Unknown fields fail
validation, and any other target or format fails with a message naming the
plugin, so a spelling mistake or a target for another tool cannot slip in. The
native manifest owns the package version; there is no global version forcing
unrelated plugins to release together.

`releases.json` is the advertised-release lock. Each entry pins a plugin's `claude-code` target (its `harness`) to
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

The acceptance file names the meaningful scenarios and how to
retain observations. File existence is checked; an agent independently evaluates
its adequacy and executes it for a release. Declaring a procedure is not proof of
passing runtime acceptance.

## Native adapter

| Target | Accepted package format | Generated index |
| --- | --- | --- |
| `claude-code` | `claude-plugin`: `.claude-plugin/plugin.json` | `.claude-plugin/marketplace.json` |

`docs/catalog.md` and the native index use the release lock. Both outputs are
checked byte-for-byte. Only locked accepted releases (or the explicit historical
Claudit migration) appear in the native listing. Entries use commit-pinned
`git-subdir` sources; editing candidate files does not change the advertised bytes.

Use current [Claude marketplace documentation](https://code.claude.com/docs/en/plugin-marketplaces)
for native host requirements. These adapter checks validate Quickstop's contract,
not the complete evolving upstream schema.

## Package layout

Every plugin is one self-contained package at `plugins/<name>/`, with its
manifest at `.claude-plugin/plugin.json`:

```text
plugins/
  claudit/
  writing-for-humans/
```

Catalog target paths select the package roots. Paths must stay under
`plugins/`; distinct roots cannot overlap. Every distribution file and native
manifest must belong to a declared package. Do not add unused skeletons.

If shared source is worthwhile, give the plugin a deterministic build that copies
its needed content into the package and test regeneration as part of `bin/ci`.
Never depend on `../shared`, symlinks, undeclared host files or consumer-accessible
source directories: a host copies only the package root into its install cache.
The marketplace generator generates indexes, not plugin code or behavior.

## Validation and versions

```sh
bin/check-marketplace --write
bin/check-marketplace --base origin/main
bin/check-marketplace --base PRE_CHANGE_SHA
bin/ci
```

Use the pinned Python described in [repository guidance](repository.md). Generation
validates inputs before writing. Read-only checking never rewrites outputs.
Supply a real base commit: Git failures are errors, not permission to skip checks.
The base comparison also supports the earlier catalog-less Claude marketplace.

All package files are versioned, including documentation and untracked payloads
in a developer checkout. A changed package requires a higher stable `X.Y.Z`
version; downgrades fail. Plugins version independently. Moving identical bytes
alone does not require a bump.
Updating marketplace descriptions or acceptance docs outside the package does not
change plugin bytes. Removing a candidate declaration does not silently revoke a retained advertised
release. Retire or restore advertised pointers explicitly in the release lock,
with independent review of consumer migration and recovery impact.

## Another agent tool

Another agent tool is added only once its plugins can be tested in that tool.
Adding one means a format validator and native index projection in
`bin/check-marketplace`, installation and acceptance docs, and positive and
adversarial fixtures, with native discovery demonstrated in an isolated host
before any package is advertised.

Pinned native sources currently select packages from this repository.
Externally maintained repositories and registries still require a bounded adapter
change with source verification and same-byte acceptance. This task does not import Mandalore or
move any other project's source or publication authority into Quickstop.
