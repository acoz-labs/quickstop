# Quickstop

The [acoz-labs](https://github.com/acoz-labs) unified marketplace for agentic
plugins. A plugin can support one harness or several. Support is explicit;
feature parity across harnesses is not required.

## Find a plugin

Browse the [plugin catalog](docs/catalog.md) for supported harnesses and package
versions. Today, [Claudit](plugins/claudit) audits and optimizes Claude Code
configuration. It remains **Claude Code-only**, at **3.0.0**.

## Install

### Claude Code

```text
/plugin marketplace add acoz-labs/quickstop
/plugin install claudit@quickstop
```

For local development:

```sh
git clone https://github.com/acoz-labs/quickstop.git
claude --plugin-dir /path/to/quickstop/plugins/claudit
```

### Codex

Quickstop provides a native Codex marketplace index. It currently contains no
plugins because none advertise Codex support yet. The catalog will list eligible
packages as they are added; Claudit is not included through compatibility fallback.

```sh
codex plugin marketplace add acoz-labs/quickstop
```

This registers the marketplace; it does not make unsupported plugins compatible.
Use the harness's plugin browser to install a listed package when one is available.
### Pi

Pi installs individual packages rather than a marketplace index. See the
[Pi package list](docs/pi-packages.md) for generated install commands, run from a
clone of a reviewed Quickstop revision. There are no Pi packages listed yet;
Claudit remains Claude Code-only. Adding Pi support to a future plugin does not
require Claude Code or Codex support.

Additional harnesses join through explicit adapters and acceptance procedures.

## Develop and maintain

- [Repository guidance](docs/repository.md) and [shared SDLC](docs/operations/sdlc.md)
- [Catalog and package structure](docs/marketplace.md)
- [Plugin development and review](docs/plugin-development.md)
- [Artifact delivery and recovery](docs/delivery.md)
- [Project board](https://github.com/orgs/acoz-labs/projects/40)
- [Onboarding investigation](docs/investigation.md)

`catalog.json` declares each plugin's supported targets. Native manifests own
package versions. `bin/check-marketplace --write` generates the native indexes
and browsable catalog; `bin/ci` rejects drift and runs the repository tests.
See repository guidance for the pinned Python runtime.

The repository moved from `acostanzo/quickstop` to `acoz-labs/quickstop`.
The marketplace identity remains `quickstop`, including `claudit@quickstop`.
Existing Claudit files and historical author attribution are preserved.

## License

MIT. Preserve each package's license and attribution.
