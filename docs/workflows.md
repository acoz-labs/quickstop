# Workflows in Quickstop

A workflow is a practical guide that a person and their agent can adapt to a
project. It describes decisions, responsibilities, useful artifacts and evidence
of completion. Plugins extend a harness; workflows help people choose and establish
working practices. Keep those expectations separate in listings and instructions.

## Authoring

Put each workflow in `workflows/<name>/` with a readable `README.md` entry point.
Link it from `workflows/README.md` and the repository's introduction. Use ordinary
Markdown and relative links, with supporting files only when they make the guide
easier to use. There is no required file count, native package manifest, installer
or workflow runtime.

Explain the problem, audience, circumstances where the guide helps, and when
adoption would add needless process. Include an agent-facing starting prompt,
then enough concrete guidance for the agent to inspect the existing environment,
identify gaps and make the smallest authorized adaptation. Preserve user boundaries
and applicable repository rules. Document actual limitations rather than claiming
a guide can enforce independent review, permissions or a successful release.

Use wholly fictional examples. Never copy private project histories, personal
experiences, credentials, machine conventions or inaccessible private references
into public material. Keep process instructions in plain language; a memorable
name does not require metaphors for every step.

## Review and publication

Guidance that changes agent authority or working policy gets independent review
under the code lane, even when its implementation is Markdown. Ordinary editorial
corrections follow the documentation lane. Review the full entry-to-adoption path,
relative links, privacy boundary and adaptation to different project constraints.
Exercise representative examples and distinguish a document walkthrough from a
real agent execution or native harness test.

Workflow publication is a reviewed repository change, verified at its merged
revision. It is not a plugin artifact release and must not alter native indexes,
plugin bytes or version numbers merely to advertise a guide. A stable `main` link
is convenient for discovery; cite a full commit when an adoption decision needs
a reproducible reference. Updating the guide does not silently update consumers'
local adaptations. Correct a published guide through a reviewed change or revert;
retain the earlier revision for provenance.

## Keeping Shipshape current

Shipshape draws on the practices used to maintain Quickstop. Its portable guidance
lives in `workflows/shipshape/`; Quickstop's actual operating contract remains
[software delivery](operations/sdlc.md). Neither replaces the other: the former is
an adaptable public guide, the latter governs this repository.

When delivery practices change, review whether the rationale, adoption guidance
and examples need to change too. Update the public guide deliberately when those
lessons generalize. Do not copy organization-specific scripts, accounts or approval
requirements into it, and do not automatically rewrite anyone's adopted workflow.
