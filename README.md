# Quickstop

A little convenience store for your agents. Useful plugins, practical workflows,
and a few good additions to the way you work.

Quickstop brings together two kinds of open-source tools from
[acoz-labs](https://github.com/acoz-labs):

| On the shelf | What you get | Get started |
| --- | --- | --- |
| **Plugins** | Installable capabilities for the agents they explicitly support. | [Browse plugins](docs/catalog.md) |
| **Workflows** | Practical guides you and your agent can adapt to your project. | [Read and adapt](workflows/README.md) |

Visit the [Quickstop storefront](https://acoz.dev/projects/quickstop/) for a look around.

## Plugins

[Writing for Humans](plugins/claude-code/writing-for-humans) provides a selectable
writing style and two skills for clearer human-facing communication.
[Claudit](plugins/claudit) audits and improves Claude Code configuration.
Both currently support **Claude Code only**. The [plugin catalog](docs/catalog.md)
records advertised versions and supported harnesses.

A plugin can support one harness or several. Support is explicit; parity is not
required. Quickstop has native distribution patterns for Claude Code, Codex and Pi,
but that does not make every plugin compatible with all three.

### Claude Code

Inside Claude Code:

```text
/plugin marketplace add acoz-labs/quickstop
/plugin install writing-for-humans@quickstop
```

Restart Claude Code, then select `/output-style writing-for-humans:writing-for-humans`.
For Claudit, use `/plugin install claudit@quickstop`. See each package's README
for its setup and usage.

For local plugin development:

```sh
git clone https://github.com/acoz-labs/quickstop.git
claude --plugin-dir /path/to/quickstop/plugins/claudit
```

### Codex

Quickstop provides a native Codex marketplace index. It currently contains no
plugins because none advertise Codex support yet.

```sh
codex plugin marketplace add acoz-labs/quickstop
```

This registers the marketplace. Use the harness's plugin browser to install a
listed package when one is available.

### Pi

Pi installs individual packages. The [Pi package list](docs/pi-packages.md)
contains generated installation instructions; no Pi packages are advertised yet.

## Workflows

**[Shipshape](workflows/shipshape/README.md)** — From first idea to ready to ship.
A practical software delivery workflow you and your agents can make your own.

Read it yourself or give its adoption instructions to your agent. Workflows help
you shape your existing project agreements, tools and habits. They do not install
plugins, run background processes, or require another layer of instructions in a
project that already works well. Adopting a workflow is a deliberate change;
reading a guide alone does not configure anything.

[Browse workflows](workflows/README.md) · [How workflow contributions work](docs/workflows.md)

## Develop and maintain

- [Repository guidance](docs/repository.md) and [shared SDLC](docs/operations/sdlc.md)
- [Plugin catalog and package structure](docs/marketplace.md)
- [Plugin development and review](docs/plugin-development.md)
- [Workflow authoring and review](docs/workflows.md)
- [Publication and recovery](docs/delivery.md)
- [Project board](https://github.com/orgs/acoz-labs/projects/40)

`catalog.json` and `releases.json` govern installable plugins. Native manifests own
package versions; generated indexes advertise accepted releases. Workflow guides
live in `workflows/` and stay out of native plugin indexes. There is no workflow
installer or separate workflow packaging format.

Run `bin/ci` with the pinned Python runtime described in repository guidance.

The repository moved from `acostanzo/quickstop` to `acoz-labs/quickstop`.
The marketplace identity remains `quickstop`; existing package identities and
historical author attribution are preserved.

## License

MIT. Preserve license notices and attribution when adapting the material.
