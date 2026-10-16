# Shipshape

**From first idea to ready to ship.**

A practical software delivery workflow you and your agents can make your own.
Get your project shipshape: agree on the destination, do the work, and check what
actually arrived.

Shipshape is a guide to adapting working practices, with an optional versioned
[Codex package candidate](../../plugins/codex/shipshape/README.md). Guide-only adoption remains valid.
Start with useful gaps in your process; leave the rest alone. The package is not
yet accepted, published or installable through the accepted native indexes. It is
publicly discoverable in the catalog and supplies no integration service or credentials.

## Start here

Give an agent that can read this repository the following prompt. Adjust the
last sentence if you want it to implement changes as well as propose them.

```text
Read Quickstop's Shipshape workflow at
https://github.com/acoz-labs/quickstop/tree/main/workflows/shipshape,
including its process, adaptation guide and examples. Inspect this project's
existing instructions, contribution process, checks and release practices.
Identify any concrete gaps that Shipshape could help with. Preserve applicable
rules and what already works; do not add duplicate process or mandatory gates.
Recommend the smallest useful adaptation, explain its tradeoffs and how we
would verify it, and call out any capabilities we do not have. If there is no
useful gap, say so. Stop at a reviewable proposal; do not change files, settings,
permissions or external services yet.
```

The proposal boundary belongs to this starter prompt, not to the workflow itself.
For an implementation task, replace its final sentence with a boundary such as:

```text
Implement the useful documentation changes in this repository, run relevant
checks, and prepare a pull request. Stop before merge or publication. If the
adaptation requires configuration or external changes, describe those separately.
```

Adjust that scope to the work you actually want done. A link to Shipshape never
grants authority to publish, send messages, change access, or deploy software.

## What to read

- [The process](process.md): outcomes, proportional planning, implementation,
  review, verification and delivery.
- [Adapt it to your project](adapt.md): inspect first, make minimal changes,
  validate the result and maintain it locally.
- [Fictional examples](examples.md): a small fix, an ambiguous feature and a
  consequential release in three different environments.

## When it helps

Use Shipshape when work stalls between an idea and a clear next action, agents
repeatedly ask for routine approvals, checks do not match the actual risk, or
“done” hides the difference between a code change and a working release.

If your project already handles these well, you may need no changes. A typo
does not need a design document. A documentation correction with no executable
effects usually needs an edit and relevant checks. A risky data migration needs
more preparation, evidence and recovery planning.

## What it can and cannot provide

Shipshape can help an agent reason about and document a delivery process. It
cannot provide credentials, independent reviewers, CI, deployment access, or
enforcement through prose. Name missing capabilities honestly; do not turn them
into fictional passed checks. Native package installation/runtime acceptance is
pending; guide readers use whatever tools they have. Package static checks do
not prove independent execution, native loading or release readiness.

Use a shared pinned role package in separate author/reviewer environments, not
copies per repository. Keep existing `.sdlc/config.json` as the local contract
and preserve stronger rules. No autoadoption or auto-upgrade: record package
digest, guide, harness/tool and configuration revisions per run. Read-only tasks
yield proposals only. Fresh-context independent executing review, correction and
new-head re-review remain mandatory where required; reviewer-written fixes need
another reviewer. Missing tools, auth, reviewer or sandbox blocks progress.
The first public package release waits for full integrated issue acceptance.
Preserve exact revisions and a bounded handoff outside disposable consumer
checkouts. Offline helper recommendations do not grant execution or release
authority; the trusted adapter supplies observations and independent evidence.

Storefront impact: the first fenced starter prompt, summary and proposal-only
next step remain unchanged; this candidate addition needs no receipt refresh.

## Where it comes from

Shipshape distills principles from the maintained
[software delivery standard used by Quickstop](../../docs/operations/sdlc.md).
It is an adaptation guide, not a copy of that organization's operational policy.
You do not need its accounts, repository tooling, project boards or role setup.
The documents here are sufficient to begin.

Quickstop maintains this public guide; each adopting project owns its resulting
local practices. Updates here do not silently change an adopted workflow. See
[maintenance](adapt.md#keep-it-useful) for how to evaluate later revisions.
