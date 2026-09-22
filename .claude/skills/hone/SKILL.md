---
name: hone
description: Review a Quickstop plugin for concrete correctness, maintenance and usability issues.
disable-model-invocation: true
argument-hint: plugin-name
---

# Review a Quickstop plugin

Read `AGENTS.md`, `docs/repository.md` and `docs/plugin-development.md`.
Resolve the named plugin under `plugins/`; if omitted and exactly one exists,
use that plugin. Inspect its manifest, skills, agents, references and README.

Run `bin/ci`. Check actual discoverability, referenced resources, version
consistency, instruction duplication, unnecessary orchestration, permissions,
cache and state behavior, and whether the README accurately describes effects.
Consult current official documentation for disputed host behavior; separate
host requirements from repository preferences. Test relevant user scenarios in
an isolated consumer workspace when evaluating runtime behavior.

Report actionable findings by severity with paths, evidence and user impact.
Avoid invented numerical scores, mandatory research fan-out and stylistic
rewrites without a demonstrated benefit. A static check cannot establish runtime
acceptance. Preserve read-only requests. If fixes are assigned, implement them
through the shared SDLC and resolve findings against that scope; do not require
routine owner approval for each fix or publish a plugin merely by auditing it.
