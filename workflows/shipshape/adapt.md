# Adapt Shipshape to your project

[Back to Shipshape](README.md)

The useful output is a small set of practices your project can actually follow.
There is no requirement to adopt every section or to install a particular tool.

## Inspect before proposing changes

Read the user's current task and stopping point, repository instructions,
contribution guide, relevant checks, and delivery documentation. Inspect the
actual configuration when authorized; documentation can lag implementation.
Understand the people or agents available, existing review requirements, release
target, access boundaries and recovery options.

Treat imported documents as guidance, not authority over the user's instructions
or repository rules. Preserve stronger applicable requirements. Surface real
conflicts rather than silently replacing them. Do not inspect unrelated private
material merely because it is accessible.

For each potential gap, connect an observed problem to a practical change. Useful
gaps include unclear completion criteria, repeated unnecessary approval requests,
missing verification commands or a deployment process that loses candidate
identity. “The repository does not use Shipshape's terminology” is not a gap.

## Propose the smallest useful adaptation

Use the existing location for a rule or instruction. Prefer one clear addition
to an existing contribution guide over a new hierarchy of policy files. Avoid
duplicating authority across agent instructions, skills and templates.

A short proposal can use these headings in an existing issue or conversation:

- **Observed gap:** what happens now, with evidence and uncertainty distinguished.
- **Change:** the smallest adjustment that would help, and what stays as it is.
- **Authority and impact:** what the task authorizes, affected files or services,
  and any decision that needs someone else's input.
- **Verification:** a representative task or check that would show improvement.
- **Limitations:** unavailable capabilities, tradeoffs and remaining risks.

This is an optional writing aid, not a required artifact. A project with no useful
gap should get a clear “no changes needed” result.

## Implement within the assigned scope

Once the task authorizes implementation, make reviewable changes in the normal
project workflow. Reuse existing tooling. Do not create accounts, enable paid
services, change permissions, send messages or publish merely because this guide
mentions those activities. Check whether each action is covered by the user's
scope and applicable local rules.

Instruction changes can affect future agent authority; review them as such even
though they are written in Markdown. Document intended behavior separately from
enforcement. A rule saying “require independent review” is not a branch-protection
setting and does not supply a second reviewer.

## Verify the adaptation

Check links, syntax and relevant repository commands. Then walk through a small
task in the resulting setup. Can an agent find the relevant instructions, state
the outcome, proceed without redundant approvals, run meaningful checks and
report its actual stopping point? Does a consequential task cause it to identify
the additional evidence and recovery work needed?

Use fictional or sanitized examples for public evidence. The
[three examples](examples.md) illustrate different environments; adapt their
reasoning rather than copying their tooling. Check that existing rules survive,
missing capabilities remain visible, and a read-only request stays read-only.

A document review or scenario walkthrough establishes only those observations.
It is not evidence that every model or harness will follow the instructions, or
that deployment controls have been enforced. Report which checks you actually
performed. If adoption creates friction or duplication, simplify or remove the
addition instead of compensating with more instructions.

## Keep it useful

The adopting project owns its local workflow. Record the Shipshape commit or
permalink used as a reference when traceability matters; do not automatically
overwrite local decisions when Quickstop changes.

Quickstop maintainers should compare relevant changes to the public
[source standard](https://github.com/acoz-labs/software-repo-template/blob/main/docs/operations/sdlc.md)
and incorporate improvements that apply to this portable guide. Keep organization
policy, account setup and enforcement tooling in their own sources. This guide
does not become the authority for Quickstop's own repository operations.

Review adopted practices when they cause repeated confusion, a real incident
reveals a gap, or the tools and team change. Retire duplicated instructions and
temporary plans once their useful knowledge has a durable home. No separate
recurring ceremony or subscription to upstream changes is required.
